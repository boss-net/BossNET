from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from core.entities.base import DomainModel
from core.repositories.base import Repository

T = TypeVar("T", bound=DomainModel)
ID = TypeVar("ID")


class BaseService(Generic[T, ID], ABC):
    """Base service class for domain services."""

    def __init__(self, repository: Repository[T, ID]):
        self.repository = repository

    async def get_by_id(self, id: ID) -> Optional[T]:
        """Get an entity by ID."""
        return await self.repository.get_by_id(id)

    async def list(self, skip: int = 0, limit: int = 100) -> List[T]:
        """List entities with pagination."""
        return await self.repository.list(skip=skip, limit=limit)

    async def create(self, data: Dict[str, Any]) -> T:
        """Create a new entity."""
        entity = self._create_entity_from_data(data)
        return await self.repository.add(entity)

    async def update(self, id: ID, data: Dict[str, Any]) -> Optional[T]:
        """Update an existing entity."""
        entity = await self.get_by_id(id)
        if not entity:
            return None

        updated_entity = self._update_entity_from_data(entity, data)
        return await self.repository.update(id, updated_entity)

    async def delete(self, id: ID) -> bool:
        """Delete an entity by ID."""
        return await self.repository.delete(id)

    @abstractmethod
    def _create_entity_from_data(self, data: Dict[str, Any]) -> T:
        """Create a new entity from dictionary data."""
        pass

    def _update_entity_from_data(self, entity: T, data: Dict[str, Any]) -> T:
        """Update an existing entity from dictionary data."""
        for key, value in data.items():
            if hasattr(entity, key) and value is not None:
                setattr(entity, key, value)
        return entity
