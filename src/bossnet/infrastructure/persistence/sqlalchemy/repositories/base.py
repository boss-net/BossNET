from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, Sequence, Type, TypeVar, Union, cast
from uuid import UUID

from core.domain.entities.base import Entity
from core.domain.repositories.base import Filter, OrderBy, Pagination, Repository
from pydantic import BaseModel
from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.sql.expression import Select

ModelType = TypeVar("ModelType", bound=Any)
EntityType = TypeVar("EntityType", bound=Entity)
SchemaType = TypeVar("SchemaType", bound=BaseModel)


class SQLAlchemyRepository(Generic[ModelType, EntityType], Repository[EntityType]):
    """Base repository implementation using SQLAlchemy."""

    def __init__(self, session: AsyncSession, model: Type[ModelType], entity_type: Type[EntityType]) -> None:
        """Initialize repository with database session and model class.

        Args:
            session: SQLAlchemy async session.
            model: SQLAlchemy model class.
            entity_type: Domain entity class.
        """
        self.session = session
        self.model = model
        self.entity_type = entity_type

    def _to_entity(self, model_instance: Optional[ModelType]) -> Optional[EntityType]:
        """Convert SQLAlchemy model instance to domain entity."""
        if model_instance is None:
            return None
        # Handle SQLAlchemy model to dict conversion safely
        data = {
            key: getattr(model_instance, key)
            for key in dir(model_instance)
            if not key.startswith("_") and not callable(getattr(model_instance, key))
        }
        return self.entity_type.model_validate(data)

    def _to_entity_list(self, model_instances: Sequence[ModelType]) -> List[EntityType]:
        """Convert a list of SQLAlchemy model instances to domain entities."""
        return [self._to_entity(instance) for instance in model_instances if instance is not None]

    def _apply_filters(self, query: Select, filters: Optional[List[Filter]] = None) -> Select:
        """Apply filters to the query."""
        if not filters:
            return query

        filter_conditions = []
        for f in filters:
            if f.operator == "eq":
                filter_conditions.append(getattr(self.model, f.field) == f.value)
            elif f.operator == "ne":
                filter_conditions.append(getattr(self.model, f.field) != f.value)
            elif f.operator == "gt":
                filter_conditions.append(getattr(self.model, f.field) > f.value)
            elif f.operator == "lt":
                filter_conditions.append(getattr(self.model, f.field) < f.value)
            elif f.operator == "ge":
                filter_conditions.append(getattr(self.model, f.field) >= f.value)
            elif f.operator == "le":
                filter_conditions.append(getattr(self.model, f.field) <= f.value)
            elif f.operator == "in":
                filter_conditions.append(getattr(self.model, f.field).in_(f.value))
            elif f.operator == "like":
                filter_conditions.append(getattr(self.model, f.field).like(f"%{f.value}%"))
            elif f.operator == "ilike":
                filter_conditions.append(getattr(self.model, f.field).ilike(f"%{f.value}%"))
            elif f.operator == "is_null":
                if f.value:
                    filter_conditions.append(getattr(self.model, f.field).is_(None))
                else:
                    filter_conditions.append(getattr(self.model, f.field).isnot(None))

        if filter_conditions:
            query = query.where(and_(*filter_conditions))

        return query

    def _apply_ordering(self, query: Select, order_by: Optional[List[OrderBy]] = None) -> Select:
        """Apply ordering to the query."""
        if not order_by:
            return query

        order_clauses = []
        for order in order_by:
            field = getattr(self.model, order.field)
            if order.descending:
                field = field.desc()
            order_clauses.append(field)

        return query.order_by(*order_clauses)

    def _apply_pagination(self, query: Select, pagination: Optional[Pagination] = None) -> Select:
        """Apply pagination to the query."""
        if not pagination:
            return query

        if pagination.offset is not None:
            query = query.offset(pagination.offset)
        if pagination.limit is not None:
            query = query.limit(pagination.limit)

        return query

    async def get_by_id(self, id: Union[int, str, UUID], options: Optional[List[Any]] = None) -> Optional[EntityType]:
        """Get entity by ID."""
        stmt = select(self.model).where(self.model.id == id)

        if options:
            stmt = stmt.options(*options)

        result = await self.session.execute(stmt)
        instance = result.scalar_one_or_none()
        return self._to_entity(instance)

    async def get_by_field(self, field: str, value: Any, options: Optional[List[Any]] = None) -> Optional[EntityType]:
        """Get entity by field value."""
        stmt = select(self.model).where(getattr(self.model, field) == value)

        if options:
            stmt = stmt.options(*options)

        result = await self.session.execute(stmt)
        instance = result.scalar_one_or_none()
        return self._to_entity(instance)

    async def list(
        self,
        filters: Optional[List[Filter]] = None,
        order_by: Optional[List[OrderBy]] = None,
        pagination: Optional[Pagination] = None,
        options: Optional[List[Any]] = None,
    ) -> List[EntityType]:
        """List entities with optional filtering, ordering and pagination."""
        stmt = select(self.model)

        if options:
            stmt = stmt.options(*options)

        stmt = self._apply_filters(stmt, filters)
        stmt = self._apply_ordering(stmt, order_by)
        stmt = self._apply_pagination(stmt, pagination)

        result = await self.session.execute(stmt)
        instances = result.scalars().all()
        return self._to_entity_list(instances)

    async def create(self, entity: EntityType) -> EntityType:
        """Create a new entity."""
        model_instance = self.model(**entity.model_dump(exclude_unset=True))
        self.session.add(model_instance)
        await self.session.flush()
        await self.session.refresh(model_instance)
        return self._to_entity(model_instance)

    async def update(self, id: Union[int, str, UUID], entity: EntityType) -> Optional[EntityType]:
        """Update an existing entity."""
        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(**entity.model_dump(exclude_unset=True, exclude={"id"}))
            .returning(self.model)
        )

        result = await self.session.execute(stmt)
        updated_instance = result.scalar_one_or_none()
        return self._to_entity(updated_instance)

    async def delete(self, id: Union[int, str, UUID]) -> bool:
        """Delete an entity by ID."""
        stmt = delete(self.model).where(self.model.id == id).returning(self.model.id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def exists(self, id: Union[int, str, UUID]) -> bool:
        """Check if an entity with the given ID exists."""
        stmt = select(self.model.id).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def count(self, filters: Optional[List[Filter]] = None) -> int:
        """Count entities matching the given filters."""
        stmt = select(self.model.id)
        stmt = self._apply_filters(stmt, filters)
        result = await self.session.execute(select(func.count()).select_from(stmt.subquery()))
        return result.scalar_one()

    async def list(self, *, skip: int = 0, limit: int = 100, **filters: Any) -> List[EntityType]:
        """List entities with optional filtering and pagination."""
        stmt = select(self.model).offset(skip).limit(limit)

        # Apply filters
        if filters:
            conditions = [getattr(self.model, key) == value for key, value in filters.items()]
            stmt = stmt.where(and_(*conditions))

        result = await self.session.execute(stmt)
        instances = result.scalars().all()
        return self._to_entity_list(instances)

    async def create(self, entity: EntityType) -> EntityType:
        """Create a new entity."""
        db_entity = self.model(**entity.model_dump(exclude_unset=True))
        self.session.add(db_entity)
        await self.session.flush()
        await self.session.refresh(db_entity)
        return self._to_entity(db_entity)

    async def update(self, id: int, entity: Union[EntityType, Dict[str, Any]]) -> Optional[EntityType]:
        """Update an existing entity."""
        update_data = entity.model_dump(exclude_unset=True) if isinstance(entity, DomainModel) else entity

        stmt = update(self.model).where(self.model.id == id).values(**update_data).returning(self.model)

        result = await self.session.execute(stmt)
        updated = result.scalar_one_or_none()

        if updated is None:
            return None

        await self.session.commit()
        return self._to_entity(updated)

    async def delete(self, id: int) -> bool:
        """Delete an entity by ID."""
        stmt = delete(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def exists(self, **filters: Any) -> bool:
        """Check if an entity exists with the given filters."""
        stmt = select(select(self.model).filter_by(**filters).exists())
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count(self, **filters: Any) -> int:
        """Count entities matching the given filters."""
        stmt = select(self.model)

        if filters:
            conditions = [getattr(self.model, key) == value for key, value in filters.items()]
            stmt = stmt.where(and_(*conditions))

        result = await self.session.execute(select(select(self.model).subquery().count()))
        return result.scalar_one()
