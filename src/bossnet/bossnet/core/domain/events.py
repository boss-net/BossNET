from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Type, TypeVar
from uuid import UUID, uuid4

T = TypeVar("T", bound="DomainEvent")


@dataclass(frozen=True)
class DomainEvent:
    """Base class for domain events."""

    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_on: datetime = field(default_factory=datetime.utcnow)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}[id={self.event_id}]"


@dataclass(frozen=True)
class UserRegistered(DomainEvent):
    """Event raised when a new user registers."""

    user_id: str
    email: str
    username: str


@dataclass(frozen=True)
class UserEmailVerified(DomainEvent):
    """Event raised when a user verifies their email."""

    user_id: str
    email: str


@dataclass(frozen=True)
class UserPasswordChanged(DomainEvent):
    """Event raised when a user changes their password."""

    user_id: str


class DomainEventBus:
    """Simple in-memory event bus for domain events."""

    def __init__(self):
        self._handlers = {}

    def subscribe(self, event_type: Type[DomainEvent], handler):
        """Subscribe a handler to an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def publish(self, event: DomainEvent):
        """Publish an event to all subscribers."""
        event_type = type(event)
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                handler(event)


# Global event bus instance
event_bus = DomainEventBus()
