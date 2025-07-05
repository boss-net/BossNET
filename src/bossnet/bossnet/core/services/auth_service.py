from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from core.entities.user import User, UserCreate, UserRole, UserUpdate
from core.repositories.base import UserRepository


class AuthenticationError(Exception):
    """Base authentication error."""

    pass


class InvalidCredentialsError(AuthenticationError):
    """Raised when invalid credentials are provided."""

    pass


class AccountLockedError(AuthenticationError):
    """Raised when an account is locked."""

    pass


class TokenPair(Tuple[str, str]):
    """A pair of access and refresh tokens."""

    access_token: str
    refresh_token: str


class AuthService(ABC):
    """Authentication service interface."""

    @abstractmethod
    async def authenticate_user(self, username: str, password: str) -> User:
        """Authenticate a user with username and password."""
        pass

    @abstractmethod
    async def create_tokens(self, user_id: int) -> TokenPair:
        """Create access and refresh tokens for a user."""
        pass

    @abstractmethod
    async def refresh_access_token(self, refresh_token: str) -> TokenPair:
        """Create a new access token using a refresh token."""
        pass

    @abstractmethod
    async def revoke_refresh_token(self, token: str) -> None:
        """Revoke a refresh token."""
        pass

    @abstractmethod
    async def get_current_user(self, token: str) -> User:
        """Get the current user from an access token."""
        pass

    @abstractmethod
    async def register_user(self, user_data: UserCreate) -> User:
        """Register a new user."""
        pass

    @abstractmethod
    async def verify_email(self, token: str) -> bool:
        """Verify a user's email using a verification token."""
        pass

    @abstractmethod
    async def request_password_reset(self, email: str) -> None:
        """Request a password reset for a user."""
        pass

    @abstractmethod
    async def reset_password(self, token: str, new_password: str) -> bool:
        """Reset a user's password using a reset token."""
        pass
