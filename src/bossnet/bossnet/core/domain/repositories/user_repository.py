from abc import ABC, abstractmethod
from typing import List, Optional

from src.core.domain.entities.user import User


class UserRepository(ABC):
    """Abstract base class for user repository."""

    @abstractmethod
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get a user by ID.

        Args:
            user_id: The ID of the user to retrieve.

        Returns:
            The user if found, None otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email.

        Args:
            email: The email of the user to retrieve.

        Returns:
            The user if found, None otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get a user by username.

        Args:
            username: The username of the user to retrieve.

        Returns:
            The user if found, None otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_status(self, status: str) -> List[User]:
        """Get all users with the given status.

        Args:
            status: The status to filter users by.

        Returns:
            A list of users with the given status.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_role(self, role: str) -> List[User]:
        """Get all users with the given role.

        Args:
            role: The role to filter users by.

        Returns:
            A list of users with the given role.
        """
        raise NotImplementedError

    @abstractmethod
    async def search(self, query: str, limit: int = 10, offset: int = 0) -> List[User]:
        """Search for users by name, email, or username.

        Args:
            query: The search query string.
            limit: Maximum number of results to return.
            offset: Number of results to skip.

        Returns:
            A list of matching users.
        """
        raise NotImplementedError

    @abstractmethod
    async def create(self, user: User) -> User:
        """Create a new user.

        Args:
            user: The user to create.

        Returns:
            The created user with ID populated.
        """
        raise NotImplementedError

    @abstractmethod
    async def update(self, user: User) -> User:
        """Update an existing user.

        Args:
            user: The user with updated fields.

        Returns:
            The updated user.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, user_id: int) -> bool:
        """Delete a user.

        Args:
            user_id: The ID of the user to delete.

        Returns:
            True if the user was deleted, False otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    async def add_role(self, user_id: int, role: str) -> bool:
        """Add a role to a user.

        Args:
            user_id: The ID of the user.
            role: The role to add.

        Returns:
            True if the role was added, False if the user already has the role.
        """
        raise NotImplementedError

    @abstractmethod
    async def remove_role(self, user_id: int, role: str) -> bool:
        """Remove a role from a user.

        Args:
            user_id: The ID of the user.
            role: The role to remove.

        Returns:
            True if the role was removed, False if the user didn't have the role.
        """
        raise NotImplementedError

    @abstractmethod
    async def update_status(self, user_id: int, status: str) -> bool:
        """Update a user's status.

        Args:
            user_id: The ID of the user.
            status: The new status.

        Returns:
            True if the status was updated, False otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    async def update_last_login(self, user_id: int) -> None:
        """Update the last login timestamp for a user.

        Args:
            user_id: The ID of the user.
        """
        raise NotImplementedError

    @abstractmethod
    async def exists(self, **filters) -> bool:
        """Check if a user exists with the given filters.

        Args:
            **filters: Field filters to check.

        Returns:
            True if a matching user exists, False otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    async def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """List users with pagination"""
        raise NotImplementedError
