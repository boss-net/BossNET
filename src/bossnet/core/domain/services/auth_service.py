from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from ..entities.user import TokenPayload, User, UserStatus


class AuthError(Exception):
    """Base authentication error."""

    pass


class InvalidCredentialsError(AuthError):
    """Raised when invalid credentials are provided."""

    pass


class AccountLockedError(AuthError):
    """Raised when an account is locked or inactive."""

    pass


class EmailNotVerifiedError(AuthError):
    """Raised when email is not verified but required."""

    pass


class TokenError(AuthError):
    """Raised when there's an error with token operations."""

    pass


class AuthService:
    """Authentication service interface for domain operations."""

    async def authenticate(self, username: str, password: str, require_verified_email: bool = True) -> User:
        """Authenticate a user with username/email and password.

        Args:
            username: Username or email of the user.
            password: Plain text password.
            require_verified_email: Whether to require email verification.

        Returns:
            The authenticated user.

        Raises:
            InvalidCredentialsError: If credentials are invalid.
            AccountLockedError: If account is not active.
            EmailNotVerifiedError: If email is not verified and required.
        """
        raise NotImplementedError

    async def create_access_token(
        self, user: User, expires_delta: Optional[timedelta] = None, additional_claims: Optional[dict] = None
    ) -> str:
        """Create an access token for a user.

        Args:
            user: The user to create token for.
            expires_delta: Optional expiration time delta.
            additional_claims: Additional claims to include in the token.

        Returns:
            The encoded JWT token.
        """
        raise NotImplementedError

    async def create_refresh_token(self, user: User, expires_delta: Optional[timedelta] = None) -> str:
        """Create a refresh token for a user.

        Args:
            user: The user to create token for.
            expires_delta: Optional expiration time delta.

        Returns:
            The encoded refresh token.
        """
        raise NotImplementedError

    async def verify_token(self, token: str, token_type: str = "access") -> TokenPayload:
        """Verify a JWT token and return its payload.

        Args:
            token: The JWT token to verify.
            token_type: The expected token type ("access" or "refresh").

        Returns:
            The decoded token payload.

        Raises:
            TokenError: If the token is invalid or expired.
        """
        raise NotImplementedError

    async def refresh_tokens(self, refresh_token: str) -> Tuple[str, str]:
        """Refresh an access token using a refresh token.

        Args:
            refresh_token: The refresh token.

        Returns:
            A tuple of (new_access_token, new_refresh_token).

        Raises:
            TokenError: If the refresh token is invalid or expired.
        """
        raise NotImplementedError

    async def revoke_token(self, token: str, token_type: str = "access") -> None:
        """Revoke/blacklist a token.

        Args:
            token: The token to revoke.
            token_type: The type of token ("access" or "refresh").
        """
        raise NotImplementedError

    async def revoke_all_user_tokens(self, user_id: int) -> None:
        """Revoke all tokens for a user.

        Args:
            user_id: The ID of the user.
        """
        raise NotImplementedError

    async def is_token_revoked(self, token: str, token_type: str = "access") -> bool:
        """Check if a token has been revoked.

        Args:
            token: The token to check.
            token_type: The type of token ("access" or "refresh").

        Returns:
            True if the token is revoked, False otherwise.
        """
        raise NotImplementedError

    async def get_user_permissions(self, user_id: int) -> List[str]:
        """Get all permissions for a user.

        Args:
            user_id: The ID of the user.

        Returns:
            A list of permission strings.
        """
        raise NotImplementedError

    async def has_permission(self, user_id: int, permission: str) -> bool:
        """Check if a user has a specific permission.

        Args:
            user_id: The ID of the user.
            permission: The permission to check.

        Returns:
            True if the user has the permission, False otherwise.
        """
        raise NotImplementedError
