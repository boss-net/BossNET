from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar

from core.entities.base import DomainModel

T = TypeVar("T", bound=DomainModel)
ID = TypeVar("ID")


class Repository(Generic[T, ID], ABC):
    """Base repository interface for domain entities."""

    @abstractmethod
    async def get_by_id(self, id: ID) -> Optional[T]:
        """Get entity by ID."""
        pass

    @abstractmethod
    async def list(self, skip: int = 0, limit: int = 100) -> List[T]:
        """List entities with pagination."""
        pass

    @abstractmethod
    async def add(self, entity: T) -> T:
        """Add a new entity."""
        pass

    @abstractmethod
    async def update(self, id: ID, entity: T) -> Optional[T]:
        """Update an existing entity."""
        pass

    @abstractmethod
    async def delete(self, id: ID) -> bool:
        """Delete an entity by ID."""
        pass


class UserRepository(Repository["User", int], ABC):
    """Repository interface for User entity with user-specific operations."""

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional["User"]:
        """Get user by email."""
        pass

    @abstractmethod
    async def get_by_username(self, username: str) -> Optional["User"]:
        """Get user by username."""
        pass

    @abstractmethod
    async def update_last_login(self, user_id: int) -> None:
        """Update the last login timestamp for a user."""
        pass
