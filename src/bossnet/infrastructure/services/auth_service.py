import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from core.config import settings
from core.domain.entities.user import TokenPayload, User, UserRole, UserStatus
from core.domain.repositories.user_repository import UserRepository as UserRepositoryPort
from core.domain.services.auth_service import AccountLockedError, AuthError
from core.domain.services.auth_service import AuthService as AuthServicePort
from core.domain.services.auth_service import EmailNotVerifiedError, InvalidCredentialsError, TokenError
from jose import JWTError, jwt
from passlib.context import CryptContext


class AuthService(AuthServicePort):
    """Implementation of the authentication service."""

    def __init__(
        self,
        user_repository: UserRepositoryPort,
        secret_key: str = settings.SECRET_KEY,
        algorithm: str = settings.JWT_ALGORITHM,
        access_token_expire_minutes: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        refresh_token_expire_days: int = settings.REFRESH_TOKEN_EXPIRE_DAYS,
    ):
        """Initialize the authentication service."""
        self.user_repository = user_repository
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    async def authenticate(self, username: str, password: str, require_verified_email: bool = True) -> User:
        """Authenticate a user with username/email and password."""
        # Try to get user by username or email
        if "@" in username:
            user = await self.user_repository.get_by_email(username)
        else:
            user = await self.user_repository.get_by_username(username)

        # Check if user exists and password is correct
        if not user or not self._verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Incorrect username or password")

        # Check if account is active
        if user.status != UserStatus.ACTIVE:
            raise AccountLockedError("Account is not active")

        # Check if email is verified if required
        if require_verified_email and not user.email_verified:
            raise EmailNotVerifiedError("Email not verified")

        # Update last login
        await self.user_repository.update_last_login(user.id)

        return user

    async def create_access_token(
        self, user: User, expires_delta: Optional[timedelta] = None, additional_claims: Optional[dict] = None
    ) -> str:
        """Create an access token for a user."""
        return self._create_token(
            subject=str(user.id),
            expires_delta=expires_delta or timedelta(minutes=self.access_token_expire_minutes),
            token_type="access",
            additional_claims={
                "email": user.email,
                "username": user.username,
                "roles": [role.value for role in user.roles],
                **(additional_claims or {}),
            },
        )

    async def create_refresh_token(self, user: User, expires_delta: Optional[timedelta] = None) -> str:
        """Create a refresh token for a user."""
        return self._create_token(
            subject=str(user.id),
            expires_delta=expires_delta or timedelta(days=self.refresh_token_expire_days),
            token_type="refresh",
            additional_claims={"jti": str(uuid.uuid4())},
        )

    def _create_token(
        self, subject: str, expires_delta: timedelta, token_type: str, additional_claims: Optional[dict] = None
    ) -> str:
        """Create a JWT token."""
        now = datetime.utcnow()
        expires_at = now + expires_delta

        to_encode = {"sub": subject, "iat": now, "exp": expires_at, "type": token_type, **(additional_claims or {})}

        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    async def verify_token(self, token: str, token_type: str = "access") -> TokenPayload:
        """Verify a JWT token and return its payload."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Check token type
            if payload.get("type") != token_type:
                raise TokenError("Invalid token type")

            # Convert to TokenPayload
            return TokenPayload(
                sub=payload["sub"],
                exp=datetime.fromtimestamp(payload["exp"]),
                iat=datetime.fromtimestamp(payload["iat"]),
                type=payload["type"],
                scopes=payload.get("scopes", []),
            )

        except JWTError as e:
            raise TokenError("Invalid token") from e

    async def refresh_tokens(self, refresh_token: str) -> Tuple[str, str]:
        """Refresh an access token using a refresh token."""
        try:
            # Verify refresh token
            payload = await self.verify_token(refresh_token, "refresh")

            # Get user
            user_id = int(payload.sub)
            user = await self.user_repository.get_by_id(user_id)

            if not user:
                raise TokenError("User not found")

            # Create new tokens
            new_access_token = await self.create_access_token(user)
            new_refresh_token = await self.create_refresh_token(user)

            return new_access_token, new_refresh_token

        except JWTError as e:
            raise TokenError("Invalid refresh token") from e

    async def revoke_token(self, token: str, token_type: str = "access") -> None:
        """Revoke/blacklist a token."""
        # In a real implementation, you would store the token ID (jti) in a blacklist
        # and check against it in verify_token
        pass

    async def revoke_all_user_tokens(self, user_id: int) -> None:
        """Revoke all tokens for a user."""
        # In a real implementation, you would remove all tokens for this user
        # from the blacklist
        pass

    async def is_token_revoked(self, token: str, token_type: str = "access") -> bool:
        """Check if a token has been revoked."""
        # In a real implementation, you would check if the token ID (jti)
        # is in the blacklist
        return False

    async def get_user_permissions(self, user_id: int) -> List[str]:
        """Get all permissions for a user."""
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            return []

        # In a real implementation, you would fetch permissions from the database
        # based on the user's roles
        permissions = []
        if UserRole.ADMIN in user.roles:
            permissions.extend(["*"])  # Admin has all permissions

        return permissions

    async def has_permission(self, user_id: int, permission: str) -> bool:
        """Check if a user has a specific permission."""
        if not permission:
            return True

        permissions = await self.get_user_permissions(user_id)

        # Check for wildcard permission
        if "*" in permissions:
            return True

        # Check for exact match or wildcard match
        for p in permissions:
            if p == permission or (p.endswith("*") and permission.startswith(p[:-1])):
                return True

        return False

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash."""
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Generate a password hash."""
        return self.pwd_context.hash(password)
