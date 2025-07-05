from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar
from uuid import UUID

from core.domain.entities.base import Entity

T = TypeVar("T", bound=Entity)


class Repository(Generic[T], ABC):
    """Base repository interface for domain entities."""

    @abstractmethod
    async def get_by_id(self, id: int) -> Optional[T]:
        """Get an entity by ID."""
        raise NotImplementedError

    @abstractmethod
    async def list(self, *, skip: int = 0, limit: int = 100, **filters: Any) -> List[T]:
        """List entities with optional filtering and pagination."""
        raise NotImplementedError

    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create a new entity."""
        raise NotImplementedError

    @abstractmethod
    async def update(self, id: int, entity: T) -> Optional[T]:
        """Update an existing entity."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, id: int) -> bool:
        """Delete an entity by ID."""
        raise NotImplementedError

    @abstractmethod
    async def exists(self, **filters: Any) -> bool:
        """Check if an entity exists with the given filters."""
        raise NotImplementedError

    @abstractmethod
    async def count(self, **filters: Any) -> int:
        """Count entities matching the given filters."""
        raise NotImplementedError
