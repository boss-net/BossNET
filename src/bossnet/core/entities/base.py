from datetime import datetime
from typing import Any, Dict, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class DomainModel(BaseModel):
    """Base domain model that all domain entities should inherit from."""

    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {
        "arbitrary_types_allowed": True,
        "from_attributes": True,
        "populate_by_name": True,
        "use_enum_values": True,
    }

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return self.model_dump(exclude_unset=True)

    def update(self, **kwargs):
        """Update model attributes."""
        for field, value in kwargs.items():
            if hasattr(self, field):
                setattr(self, field, value)
        return self
