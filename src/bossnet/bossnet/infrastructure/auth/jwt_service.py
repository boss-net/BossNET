import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from core.entities.user import User
from core.repositories.base import UserRepository
from core.services.auth_service import AccountLockedError, AuthenticationError, AuthService, InvalidCredentialsError, TokenPair
from jose import JWTError
from passlib.context import CryptContext

# Configuration (should be moved to settings)
SECRET_KEY = "your-secret-key-here"  # Use environment variable in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


class JWTService(AuthService):
    """JWT-based authentication service implementation."""

    def __init__(
        self,
        user_repository: UserRepository,
        secret_key: str = SECRET_KEY,
        algorithm: str = ALGORITHM,
        access_token_expire_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES,
        refresh_token_expire_days: int = REFRESH_TOKEN_EXPIRE_DAYS,
    ):
        self.user_repository = user_repository
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    async def authenticate_user(self, username: str, password: str) -> User:
        """Authenticate a user with username and password."""
        user = await self.user_repository.get_by_username(username)
        if not user:
            # Hash a dummy password to prevent timing attacks
            self.pwd_context.hash("dummy_password")
            raise InvalidCredentialsError("Incorrect username or password")

        if not self.pwd_context.verify(password, user.hashed_password):
            raise InvalidCredentialsError("Incorrect username or password")

        if not user.is_active:
            raise AccountLockedError("Account is inactive")

        # Update last login timestamp
        await self.user_repository.update_last_login(user.id)

        return user

    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create access token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire, "type": "access"})

        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh"})

        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            raise ValueError("Invalid token")

    def get_user_id_from_token(self, token: str) -> Optional[int]:
        """Extract user ID from token"""
        try:
            payload = self.decode_token(token)
            user_id = payload.get("sub")
            return int(user_id) if user_id else None
        except (ValueError, TypeError):
            return None

    async def create_tokens(self, user_id: int) -> TokenPair:
        """Create access and refresh tokens for a user."""
        access_token = self.create_access_token(data={"sub": user_id})

        refresh_token = self.create_refresh_token(data={"sub": user_id})

        # Store refresh token in database (implementation needed)
        # await self._store_refresh_token(user_id, refresh_token)

        return TokenPair((access_token, refresh_token))

    async def refresh_access_token(self, refresh_token: str) -> TokenPair:
        """Create a new access token using a refresh token."""
        try:
            payload = self.decode_token(refresh_token)
            user_id = self.get_user_id_from_token(refresh_token)

            if user_id is None:
                raise InvalidCredentialsError("Invalid refresh token")

            # Verify the refresh token is valid and not revoked
            # if not await self._is_valid_refresh_token(user_id, refresh_token):
            #     raise InvalidCredentialsError("Invalid refresh token")

            # Create new tokens
            return await self.create_tokens(user_id)

        except ValueError:
            raise InvalidCredentialsError("Invalid refresh token")

    async def revoke_refresh_token(self, token: str) -> None:
        """Revoke a refresh token."""
        # Implementation needed to mark token as revoked
        pass

    async def get_current_user(self, token: str) -> User:
        """Get the current user from an access token."""
        try:
            payload = self.decode_token(token)
            user_id = self.get_user_id_from_token(token)

            if user_id is None:
                raise InvalidCredentialsError("Could not validate credentials")

            user = await self.user_repository.get_by_id(user_id)
            if user is None:
                raise InvalidCredentialsError("User not found")

            return user

        except ValueError:
            raise InvalidCredentialsError("Could not validate credentials")

    async def register_user(self, user_data) -> User:
        """Register a new user."""
        # Check if user already exists
        existing_user = await self.user_repository.get_by_email(user_data.email)
        if existing_user:
            raise ValueError("Email already registered")

        existing_user = await self.user_repository.get_by_username(user_data.username)
        if existing_user:
            raise ValueError("Username already taken")

        # Hash the password
        hashed_password = self.pwd_context.hash(user_data.password)

        # Create user
        user = User(
            email=user_data.email,
            username=user_data.username,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            hashed_password=hashed_password,
            is_active=True,
            is_verified=False,
            roles=["student"],  # Default role
        )

        # Save user to database
        created_user = await self.user_repository.add(user)

        # Send verification email (implementation needed)
        # await self._send_verification_email(created_user)

        return created_user

    async def verify_email(self, token: str) -> bool:
        """Verify a user's email using a verification token."""
        # Implementation needed
        pass

    async def request_password_reset(self, email: str) -> None:
        """Request a password reset for a user."""
        # Implementation needed
        pass

    async def reset_password(self, token: str, new_password: str) -> bool:
        """Reset a user's password using a reset token."""
        # Implementation needed
        pass
