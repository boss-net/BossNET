from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from core.entities.base import DomainModel
from core.repositories.base import Repository
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType")
EntityType = TypeVar("EntityType", bound=DomainModel)


class SQLAlchemyRepository(Repository[EntityType, int], Generic[EntityType, ModelType]):
    """Base repository implementation using SQLAlchemy."""

    def __init__(
        self,
        session: AsyncSession,
        model: Type[ModelType],
        entity_type: Type[EntityType],
    ):
        self.session = session
        self.model = model
        self.entity_type = entity_type

    async def get_by_id(self, id: int) -> Optional[EntityType]:
        """Get entity by ID."""
        result = await self.session.get(self.model, id)
        if result is None:
            return None
        return self.entity_type.model_validate(result.__dict__)

    async def list(self, skip: int = 0, limit: int = 100) -> List[EntityType]:
        """List entities with pagination."""
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return [self.entity_type.model_validate(item.__dict__) for item in result.scalars().all()]

    async def add(self, entity: EntityType) -> EntityType:
        """Add a new entity."""
        data = entity.model_dump(exclude_unset=True, exclude={"id", "created_at", "updated_at"})
        db_item = self.model(**data)
        self.session.add(db_item)
        await self.session.flush()
        await self.session.refresh(db_item)
        return self.entity_type.model_validate(db_item.__dict__)

    async def update(self, id: int, entity: EntityType) -> Optional[EntityType]:
        """Update an existing entity."""
        data = entity.model_dump(exclude_unset=True, exclude={"id", "created_at", "updated_at"})
        data["updated_at"] = datetime.utcnow()

        stmt = update(self.model).where(self.model.id == id).values(**data).returning(self.model)

        result = await self.session.execute(stmt)
        updated = result.scalar_one_or_none()

        if updated is None:
            return None

        await self.session.refresh(updated)
        return self.entity_type.model_validate(updated.__dict__)

    async def delete(self, id: int) -> bool:
        """Delete an entity by ID."""
        stmt = delete(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
