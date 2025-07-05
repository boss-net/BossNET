import secrets
import string
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from models.user_model import RefreshToken, UserDB

# Import password hashing utilities
from passlib.context import CryptContext
from pydantic import EmailStr, ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from config import settings
from database.base import get_db

# Import email service
from .email_service import EmailService, EmailTemplate
from .models import PasswordMixin, Token, TokenData, TokenPayload, UserCreate, UserInDB, UserResponse, UserRole

# Initialize password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# OAuth2 scheme with token URL
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token", auto_error=False)


class AuthService(PasswordMixin):
    """Service for handling authentication and user management"""

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS
        self.email_service = EmailService()

    async def authenticate_user(self, username: str, password: str) -> Optional[UserDB]:
        """Authenticate a user with username and password"""
        try:
            user = self.db.query(UserDB).filter((UserDB.username == username) | (UserDB.email == username)).first()

            if not user:
                return None

            # Check if account is locked
            if user.is_account_locked():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account is temporarily locked due to too many failed login attempts",
                )

            # Verify password
            if not user.check_password(password):
                # Record failed login attempt
                user.record_login_attempt(success=False)
                self.db.commit()
                return None

            # Record successful login
            user.record_login_attempt(success=True)
            self.db.commit()

            return user

        except SQLAlchemyError as e:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error authenticating user")

    def create_access_token(self, user_id: int, scopes: List[str] = None) -> str:
        """Create a JWT access token"""
        if scopes is None:
            scopes = []

        expires_delta = timedelta(minutes=self.access_token_expire_minutes)
        expire = datetime.utcnow() + expires_delta

        to_encode = {
            "sub": str(user_id),
            "scopes": scopes,
            "type": "access",
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": secrets.token_urlsafe(16),
        }

        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: int) -> str:
        """Create a refresh token and store it in the database"""
        # Generate a unique token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)

        # Store the refresh token in the database
        db_token = RefreshToken(token=token, user_id=user_id, expires_at=expires_at)

        self.db.add(db_token)
        self.db.commit()
        self.db.refresh(db_token)

        return token

    def create_tokens(self, user_id: int, scopes: List[str] = None) -> Token:
        """Create both access and refresh tokens"""
        if scopes is None:
            scopes = []

        access_token = self.create_access_token(user_id, scopes)
        refresh_token = self.create_refresh_token(user_id)

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_at=datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes),
        )

    def refresh_access_token(self, refresh_token: str) -> Token:
        """Create a new access token using a refresh token"""
        # Verify the refresh token exists and is valid
        db_token = (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.token == refresh_token,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > datetime.utcnow(),
            )
            .first()
        )

        if not db_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

        # Get user scopes
        user = self.db.query(UserDB).get(db_token.user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

        # Create new access token
        scopes = self.get_user_scopes(user)
        access_token = self.create_access_token(user.id, scopes)

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,  # Keep the same refresh token
            token_type="bearer",
            expires_at=datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes),
        )

    def revoke_refresh_token(self, token: str) -> None:
        """Revoke a refresh token"""
        db_token = self.db.query(RefreshToken).filter(RefreshToken.token == token, RefreshToken.revoked_at.is_(None)).first()

        if db_token:
            db_token.revoke()
            self.db.commit()

    def revoke_all_user_refresh_tokens(self, user_id: int) -> None:
        """Revoke all refresh tokens for a user"""
        self.db.query(RefreshToken).filter(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)).update(
            {"revoked_at": datetime.utcnow()}
        )
        self.db.commit()

    async def get_current_user(
        self,
        token: str = Depends(oauth2_scheme),
    ) -> UserInDB:
        """Get the current user from the JWT token"""
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )

        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        try:
            # Decode the token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={"verify_aud": False})

            # Validate token type
            if payload.get("type") != "access":
                raise credentials_exception

            user_id = payload.get("sub")
            if not user_id:
                raise credentials_exception

            # Get user from database
            user = self.db.query(UserDB).get(int(user_id))
            if not user:
                raise credentials_exception

            # Check if user is active
            if not user.is_active:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

            # Convert to Pydantic model
            return UserInDB.from_orm(user)

        except (JWTError, ValidationError) as e:
            raise credentials_exception from e

    async def get_current_active_user(
        self,
        current_user: UserInDB = Depends(get_current_user),
    ) -> UserInDB:
        """Get the current active user"""
        if not current_user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
        return current_user

    async def get_current_active_superuser(
        self,
        current_user: UserInDB = Depends(get_current_user),
    ) -> UserInDB:
        """Get the current active superuser"""
        if not current_user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
        if not self.has_role(current_user, UserRole.ADMIN):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        return current_user

    # User management
    def create_user(self, user_create: UserCreate) -> UserDB:
        """Create a new user"""
        try:
            # Check if username or email already exists
            existing_user = (
                self.db.query(UserDB)
                .filter((UserDB.username == user_create.username) | (UserDB.email == user_create.email))
                .first()
            )

            if existing_user:
                if existing_user.username == user_create.username:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
                if existing_user.email == user_create.email:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

            # Create new user
            hashed_password = self.get_password_hash(user_create.password)
            db_user = UserDB(
                username=user_create.username,
                email=user_create.email,
                hashed_password=hashed_password,
                full_name=user_create.full_name,
                role=user_create.role,
                is_active=False,  # User needs to verify email first
                is_verified=False,
            )

            # Generate email verification token
            db_user.generate_email_verification_token()

            self.db.add(db_user)
            self.db.commit()
            self.db.refresh(db_user)

            # Send verification email
            self.send_verification_email(db_user)

            return db_user

        except SQLAlchemyError as e:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error creating user") from e

    def verify_email(self, token: str) -> bool:
        """Verify user's email using verification token"""
        user = self.db.query(UserDB).filter(UserDB.email_verification_token == token).first()

        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token")

        if user.is_verified:
            return True

        user.is_verified = True
        user.is_active = True  # Activate the user
        user.email_verification_token = None

        self.db.commit()
        return True

    def request_password_reset(self, email: str) -> bool:
        """Request password reset and send reset email"""
        user = self.db.query(UserDB).filter(UserDB.email == email).first()
        if not user:
            # Don't reveal that the email doesn't exist
            return True

        # Generate reset token
        reset_token = user.generate_password_reset_token()
        self.db.commit()

        # Send password reset email
        self.send_password_reset_email(user, reset_token)
        return True

    def reset_password(self, token: str, new_password: str) -> bool:
        """Reset user's password using reset token"""
        user = (
            self.db.query(UserDB)
            .filter(UserDB.reset_password_token == token, UserDB.reset_password_expires > datetime.utcnow())
            .first()
        )

        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

        # Update password
        user.hashed_password = self.get_password_hash(new_password)
        user.reset_password_token = None
        user.reset_password_expires = None

        # Revoke all refresh tokens
        self.revoke_all_user_refresh_tokens(user.id)

        self.db.commit()
        return True

    def change_password(self, user: UserDB, current_password: str, new_password: str) -> bool:
        """Change user's password"""
        if not self.verify_password(current_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

        user.hashed_password = self.get_password_hash(new_password)
        self.db.commit()
        return True

    # Email sending methods
    def send_verification_email(self, user: UserDB) -> None:
        """Send email verification email"""
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={user.email_verification_token}"

        self.email_service.send_email(
            to_email=user.email,
            subject="Verify your email address",
            template=EmailTemplate.VERIFICATION,
            template_vars={"name": user.full_name or user.username, "verification_url": verification_url},
        )

    def send_password_reset_email(self, user: UserDB, reset_token: str) -> None:
        """Send password reset email"""
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

        self.email_service.send_email(
            to_email=user.email,
            subject="Reset your password",
            template=EmailTemplate.PASSWORD_RESET,
            template_vars={
                "name": user.full_name or user.username,
                "reset_url": reset_url,
                "expiration_hours": 24,  # Matches token expiration
            },
        )

    # Role and permission helpers
    def has_role(self, user: UserInDB, role: UserRole) -> bool:
        """Check if user has a specific role"""
        return user.role == role

    def has_any_role(self, user: UserInDB, roles: List[UserRole]) -> bool:
        """Check if user has any of the specified roles"""
        return user.role in roles

    def has_all_roles(self, user: UserInDB, roles: List[UserRole]) -> bool:
        """Check if user has all of the specified roles"""
        return all(role == user.role for role in roles)

    def get_user_scopes(self, user: UserInDB) -> List[str]:
        """Get user's scopes based on their role"""
        role_scopes = {
            UserRole.ADMIN: ["admin", "teacher", "staff", "student"],
            UserRole.TEACHER: ["teacher", "student"],
            UserRole.STAFF: ["staff"],
            UserRole.STUDENT: ["student"],
        }
        return role_scopes.get(user.role, [])
