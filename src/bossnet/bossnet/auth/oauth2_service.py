"""
OAuth2/OIDC Integration Service for Bangladesh Education Data Warehouse
Supports Google, Microsoft Azure AD, and other OIDC providers
"""

import asyncio
import base64
import hashlib
import json
import secrets
import urllib.parse
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlencode

import aiohttp
import jwt
from audit.audit_service import AuditService
from auth.service import AuthService
from config.settings import settings
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat
from fastapi import HTTPException, status
from models.user import UserModel
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy.orm import Session

from database.base import get_db


class OAuthProvider(BaseModel):
    """OAuth provider configuration"""

    name: str
    client_id: str
    client_secret: str
    authorization_url: HttpUrl
    token_url: HttpUrl
    userinfo_url: HttpUrl
    jwks_url: Optional[HttpUrl] = None
    scopes: List[str] = ["openid", "profile", "email"]
    response_type: str = "code"
    grant_type: str = "authorization_code"


class OAuthState(BaseModel):
    """OAuth state for CSRF protection"""

    state: str
    code_verifier: str
    redirect_uri: str
    provider: str
    created_at: datetime
    expires_at: datetime


class OAuthUserInfo(BaseModel):
    """Standardized user info from OAuth providers"""

    sub: str  # Subject identifier
    email: str
    email_verified: bool = False
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    picture: Optional[str] = None
    locale: Optional[str] = None
    provider: str
    raw_data: Dict[str, Any] = {}


class OAuth2Service:
    """OAuth2/OIDC service for authentication"""

    def __init__(self):
        self.auth_service = AuthService()
        self.audit_service = AuditService()
        self.providers = self._load_providers()
        self.states: Dict[str, OAuthState] = {}  # In production, use Redis

    def _load_providers(self) -> Dict[str, OAuthProvider]:
        """Load OAuth provider configurations"""
        providers = {}

        # Google OAuth2
        if hasattr(settings, "GOOGLE_CLIENT_ID") and settings.GOOGLE_CLIENT_ID:
            providers["google"] = OAuthProvider(
                name="Google",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
                token_url="https://oauth2.googleapis.com/token",
                userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
                jwks_url="https://www.googleapis.com/oauth2/v3/certs",
                scopes=["openid", "profile", "email"],
            )

        # Microsoft Azure AD
        if hasattr(settings, "AZURE_CLIENT_ID") and settings.AZURE_CLIENT_ID:
            tenant_id = getattr(settings, "AZURE_TENANT_ID", "common")
            providers["microsoft"] = OAuthProvider(
                name="Microsoft",
                client_id=settings.AZURE_CLIENT_ID,
                client_secret=settings.AZURE_CLIENT_SECRET,
                authorization_url=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize",
                token_url=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
                userinfo_url="https://graph.microsoft.com/v1.0/me",
                jwks_url=f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys",
                scopes=["openid", "profile", "email", "User.Read"],
            )

        return providers

    def generate_pkce_pair(self) -> Tuple[str, str]:
        """Generate PKCE code verifier and challenge"""
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8").rstrip("=")
        code_challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("utf-8")).digest()).decode("utf-8").rstrip("=")
        )
        return code_verifier, code_challenge

    def get_authorization_url(self, provider_name: str, redirect_uri: str) -> Tuple[str, str]:
        """Generate OAuth authorization URL with PKCE"""
        if provider_name not in self.providers:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported OAuth provider: {provider_name}")

        provider = self.providers[provider_name]

        # Generate PKCE parameters
        code_verifier, code_challenge = self.generate_pkce_pair()

        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)

        # Store state information
        oauth_state = OAuthState(
            state=state,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
            provider=provider_name,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=10),
        )
        self.states[state] = oauth_state

        # Build authorization URL
        params = {
            "client_id": provider.client_id,
            "response_type": provider.response_type,
            "scope": " ".join(provider.scopes),
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        # Provider-specific parameters
        if provider_name == "microsoft":
            params["response_mode"] = "query"

        auth_url = f"{provider.authorization_url}?{urlencode(params)}"

        return auth_url, state

    async def exchange_code_for_token(self, code: str, state: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        # Validate state
        if state not in self.states:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired state parameter")

        oauth_state = self.states[state]

        # Check expiration
        if datetime.utcnow() > oauth_state.expires_at:
            del self.states[state]
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth state has expired")

        provider = self.providers[oauth_state.provider]

        # Prepare token request
        token_data = {
            "client_id": provider.client_id,
            "client_secret": provider.client_secret,
            "code": code,
            "grant_type": provider.grant_type,
            "redirect_uri": oauth_state.redirect_uri,
            "code_verifier": oauth_state.code_verifier,
        }

        # Exchange code for token
        async with aiohttp.ClientSession() as session:
            async with session.post(
                str(provider.token_url), data=token_data, headers={"Content-Type": "application/x-www-form-urlencoded"}
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Token exchange failed: {error_text}")

                token_response = await response.json()

        # Clean up state
        del self.states[state]

        return token_response

    async def get_user_info(self, access_token: str, provider_name: str) -> OAuthUserInfo:
        """Get user information from OAuth provider"""
        if provider_name not in self.providers:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported OAuth provider: {provider_name}")

        provider = self.providers[provider_name]

        # Get user info from provider
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {access_token}"}
            async with session.get(str(provider.userinfo_url), headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to get user info: {error_text}"
                    )

                user_data = await response.json()

        # Normalize user info based on provider
        if provider_name == "google":
            return OAuthUserInfo(
                sub=user_data.get("sub"),
                email=user_data.get("email"),
                email_verified=user_data.get("email_verified", False),
                name=user_data.get("name"),
                given_name=user_data.get("given_name"),
                family_name=user_data.get("family_name"),
                picture=user_data.get("picture"),
                locale=user_data.get("locale"),
                provider=provider_name,
                raw_data=user_data,
            )
        elif provider_name == "microsoft":
            return OAuthUserInfo(
                sub=user_data.get("id"),
                email=user_data.get("mail") or user_data.get("userPrincipalName"),
                email_verified=True,  # Microsoft emails are typically verified
                name=user_data.get("displayName"),
                given_name=user_data.get("givenName"),
                family_name=user_data.get("surname"),
                locale=user_data.get("preferredLanguage"),
                provider=provider_name,
                raw_data=user_data,
            )
        else:
            # Generic OIDC provider
            return OAuthUserInfo(
                sub=user_data.get("sub"),
                email=user_data.get("email"),
                email_verified=user_data.get("email_verified", False),
                name=user_data.get("name"),
                given_name=user_data.get("given_name"),
                family_name=user_data.get("family_name"),
                picture=user_data.get("picture"),
                locale=user_data.get("locale"),
                provider=provider_name,
                raw_data=user_data,
            )

    async def verify_id_token(self, id_token: str, provider_name: str) -> Dict[str, Any]:
        """Verify JWT ID token from OIDC provider"""
        if provider_name not in self.providers:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported OAuth provider: {provider_name}")

        provider = self.providers[provider_name]

        if not provider.jwks_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"JWKS URL not configured for provider: {provider_name}"
            )

        # Get JWKS from provider
        async with aiohttp.ClientSession() as session:
            async with session.get(str(provider.jwks_url)) as response:
                if response.status != 200:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to fetch JWKS")

                jwks = await response.json()

        # Decode token header to get key ID
        try:
            header = jwt.get_unverified_header(id_token)
            kid = header.get("kid")
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid ID token: {str(e)}")

        # Find matching key
        key = None
        for jwk in jwks.get("keys", []):
            if jwk.get("kid") == kid:
                key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
                break

        if not key:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No matching key found in JWKS")

        # Verify token
        try:
            payload = jwt.decode(
                id_token,
                key,
                algorithms=["RS256"],
                audience=provider.client_id,
                options={"verify_exp": True, "verify_aud": True},
            )
            return payload
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"ID token verification failed: {str(e)}")

    async def authenticate_user(self, oauth_user: OAuthUserInfo, db: Session) -> Tuple[UserModel, bool]:
        """Authenticate or create user from OAuth info"""
        # Check if user exists by OAuth provider ID
        user = (
            db.query(UserModel)
            .filter(UserModel.oauth_provider == oauth_user.provider, UserModel.oauth_subject == oauth_user.sub)
            .first()
        )

        is_new_user = False

        if not user:
            # Check if user exists by email
            user = db.query(UserModel).filter(UserModel.email == oauth_user.email).first()

            if user:
                # Link existing user to OAuth provider
                user.oauth_provider = oauth_user.provider
                user.oauth_subject = oauth_user.sub
                user.email_verified = oauth_user.email_verified
            else:
                # Create new user
                user = UserModel(
                    email=oauth_user.email,
                    first_name=oauth_user.given_name or "",
                    last_name=oauth_user.family_name or "",
                    is_active=True,
                    email_verified=oauth_user.email_verified,
                    oauth_provider=oauth_user.provider,
                    oauth_subject=oauth_user.sub,
                    profile_picture=oauth_user.picture,
                    locale=oauth_user.locale,
                )
                db.add(user)
                is_new_user = True
        else:
            # Update existing OAuth user info
            if oauth_user.name:
                names = oauth_user.name.split(" ", 1)
                user.first_name = names[0]
                user.last_name = names[1] if len(names) > 1 else ""

            user.email_verified = oauth_user.email_verified
            user.profile_picture = oauth_user.picture
            user.locale = oauth_user.locale
            user.last_login = datetime.utcnow()

        db.commit()
        db.refresh(user)

        # Log authentication event
        await self.audit_service.log_event(
            event_type="authentication",
            action="oauth_login",
            user_id=user.id,
            details={"provider": oauth_user.provider, "is_new_user": is_new_user, "email_verified": oauth_user.email_verified},
        )

        return user, is_new_user

    def get_supported_providers(self) -> List[str]:
        """Get list of supported OAuth providers"""
        return list(self.providers.keys())

    async def cleanup_expired_states(self):
        """Clean up expired OAuth states"""
        current_time = datetime.utcnow()
        expired_states = [state for state, oauth_state in self.states.items() if current_time > oauth_state.expires_at]

        for state in expired_states:
            del self.states[state]
