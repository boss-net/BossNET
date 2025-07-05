"""
Authentication service - Application layer
"""

from datetime import datetime, timedelta
from typing import Any, Dict

from src.core.domain.entities.user import User
from src.core.domain.repositories.user_repository import UserRepositoryInterface
from src.core.value_objects.email import Email
from src.infrastructure.auth.jwt_service import JWTService
from src.utils.security_utils import hash_password, verify_password


class AuthService:
    """Authentication service handling user authentication logic"""

    def __init__(self, user_repository: UserRepositoryInterface, jwt_service: JWTService):
        self._user_repository = user_repository
        self._jwt_service = jwt_service

    async def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user and return tokens"""
        # Validate email format
        email_obj = Email(email)

        # Get user from repository
        user = await self._user_repository.get_by_email(email_obj.value)
        if not user:
            raise ValueError("Invalid email or password")

        # Verify password
        if not verify_password(password, user.hashed_password):
            raise ValueError("Invalid email or password")

        # Check if user is active
        if not user.is_active:
            raise ValueError("User account is disabled")

        # Generate tokens
        access_token = self._jwt_service.create_access_token(data={"sub": str(user.id), "email": user.email})
        refresh_token = self._jwt_service.create_refresh_token(data={"sub": str(user.id), "email": user.email})

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self._jwt_service.access_token_expire_minutes * 60,
        }

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        try:
            payload = self._jwt_service.decode_token(refresh_token)
            user_id = int(payload.get("sub"))
            email = payload.get("email")

            # Verify user still exists and is active
            user = await self._user_repository.get_by_id(user_id)
            if not user or not user.is_active:
                raise ValueError("Invalid refresh token")

            # Generate new access token
            access_token = self._jwt_service.create_access_token(data={"sub": str(user.id), "email": user.email})

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,  # Keep the same refresh token
                "token_type": "bearer",
                "expires_in": self._jwt_service.access_token_expire_minutes * 60,
            }

        except Exception:
            raise ValueError("Invalid refresh token")

    async def register_user(self, email: str, password: str, full_name: str) -> User:
        """Register a new user"""
        # Validate email format
        email_obj = Email(email)

        # Check if user already exists
        existing_user = await self._user_repository.get_by_email(email_obj.value)
        if existing_user:
            raise ValueError("User with this email already exists")

        # Hash password
        hashed_password = hash_password(password)

        # Create user entity
        user = User(
            email=email_obj.value,
            hashed_password=hashed_password,
            full_name=full_name,
            is_active=True,
            created_at=datetime.utcnow(),
        )

        # Save user
        return await self._user_repository.create(user)

    async def logout_user(self, refresh_token: str) -> None:
        """Logout user by invalidating refresh token"""
        # In a production system, you would typically:
        # 1. Add the token to a blacklist/revocation list
        # 2. Store blacklisted tokens in Redis with expiration
        # For now, we'll just validate the token
        try:
            self._jwt_service.decode_token(refresh_token)
        except Exception:
            raise ValueError("Invalid refresh token")
