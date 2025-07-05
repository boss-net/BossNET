"""
Base model class with common fields and functionality.
"""

from datetime import datetime
from typing import Any, Dict, Optional, Type, TypeVar
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Integer, String, event
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

ModelType = TypeVar("ModelType", bound="Base")


@as_declarative()
class Base:
    """Base class for all SQLAlchemy models."""

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # UUID for external references
    uuid = Column(String(36), unique=True, index=True, default=lambda: str(uuid4()))

    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer, nullable=True)  # User ID who created the record
    updated_by = Column(Integer, nullable=True)  # User ID who last updated the record

    # Soft delete
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(Integer, nullable=True)

    # Version for optimistic locking
    version = Column(Integer, default=1, nullable=False)

    @declared_attr
    def __tablename__(cls) -> str:
        """Generate __tablename__ automatically from class name."""
        # Convert CamelCase to snake_case
        import re

        name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", cls.__name__)
        name = re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()
        # Remove 'model' suffix if present
        if name.endswith("_model"):
            name = name[:-6]
        return name

    def to_dict(self, exclude_fields: Optional[set] = None) -> Dict[str, Any]:
        """Convert model to dictionary."""
        exclude_fields = exclude_fields or set()
        exclude_fields.update({"_sa_instance_state"})

        result = {}
        for column in self.__table__.columns:
            if column.name not in exclude_fields:
                value = getattr(self, column.name)
                if isinstance(value, datetime):
                    value = value.isoformat()
                result[column.name] = value
        return result

    def update(self, **kwargs: Any) -> None:
        """Update model attributes."""
        for key, value in kwargs.items():
            if hasattr(self, key) and not key.startswith("_"):
                setattr(self, key, value)
        self.version += 1

    def soft_delete(self, deleted_by: Optional[int] = None) -> None:
        """Soft delete the record."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.deleted_by = deleted_by
        self.version += 1

    def restore(self) -> None:
        """Restore a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.version += 1

    @classmethod
    def get_active(cls, session: Session):
        """Get query for active (non-deleted) records."""
        return session.query(cls).filter(cls.is_deleted == False)

    def __repr__(self) -> str:
        """String representation of the model."""
        attrs = []
        for key in ["id", "uuid", "name", "title", "email"]:
            if hasattr(self, key):
                value = getattr(self, key)
                if value is not None:
                    attrs.append(f"{key}={value!r}")
                    break

        attrs_str = ", ".join(attrs) if attrs else f"id={getattr(self, 'id', 'None')}"
        return f"{self.__class__.__name__}({attrs_str})"


# Event listeners for audit fields
@event.listens_for(Base, "before_insert", propagate=True)
def set_created_at(mapper, connection, target):
    """Set created_at timestamp on insert."""
    if hasattr(target, "created_at") and target.created_at is None:
        target.created_at = datetime.utcnow()


@event.listens_for(Base, "before_update", propagate=True)
def set_updated_at(mapper, connection, target):
    """Set updated_at timestamp on update."""
    if hasattr(target, "updated_at"):
        target.updated_at = datetime.utcnow()
