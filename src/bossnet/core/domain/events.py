from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Type, TypeVar
from uuid import uuid4


@dataclass(frozen=True)
class UserRegistered:
    """Event raised when a new user registers."""

    user_id: str
    email: str
    username: str
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_on: datetime = field(default_factory=datetime.utcnow)

    def __str__(self) -> str:
        return f"UserRegistered[id={self.event_id}]"


@dataclass(frozen=True)
class UserEmailVerified:
    """Event raised when a user verifies their email."""

    user_id: str
    email: str
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_on: datetime = field(default_factory=datetime.utcnow)

    def __str__(self) -> str:
        return f"UserEmailVerified[id={self.event_id}]"


@dataclass(frozen=True)
class UserPasswordChanged:
    """Event raised when a user changes their password."""

    user_id: str
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_on: datetime = field(default_factory=datetime.utcnow)

    def __str__(self) -> str:
        return f"UserPasswordChanged[id={self.event_id}]"


class DomainEventBus:
    """Simple in-memory event bus for domain events."""

    def __init__(self):
        self._handlers = {}

    def subscribe(self, event_type: Type, handler):
        """Subscribe a handler to an event type.

        Args:
            event_type: The type of event to subscribe to
            handler: A callable that will be called when the event is published
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def publish(self, event):
        """Publish an event to all subscribers.

        Args:
            event: The event instance to publish
        """
        event_type = type(event)
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                handler(event)


# Global event bus instance
event_bus = DomainEventBus()
