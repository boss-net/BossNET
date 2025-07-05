from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class DomainModel(BaseModel):
    """Base domain model that all domain entities will inherit from."""

    model_config = {
        "arbitrary_types_allowed": True,
        "from_attributes": True,
        "json_encoders": {datetime: lambda v: v.isoformat()},
    }

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return self.model_dump(exclude_unset=True)

    def to_json(self) -> str:
        """Convert model to JSON string."""
        return self.model_dump_json()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DomainModel":
        """Create model from dictionary."""
        return cls.model_validate(data)


class Entity(DomainModel):
    """Base class for domain entities with an ID."""

    id: Optional[int] = Field(default=None, description="Unique identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Entity):
            return False
        if self.id is None or other.id is None:
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        if self.id is None:
            return hash(id(self))
        return hash(self.id)
