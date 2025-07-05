from datetime import datetime
from enum import Enum
from typing import List, Optional, Set

from core.domain.events import UserEmailVerified, UserPasswordChanged, UserRegistered
from core.entities.base import DomainModel
from core.value_objects.email import Email
from pydantic import EmailStr, Field, SecretStr, validator


class Password:
    """Value object representing a hashed password."""

    def __init__(self, hashed_password: str):
        self.hashed_password = hashed_password

    @classmethod
    def create(cls, plain_password: str) -> "Password":
        """Create a new password from plain text."""
        # In a real implementation, this would hash the password
        return cls(plain_password)

    def verify(self, plain_password: str) -> bool:
        """Verify a plain password against the hashed password."""
        # In a real implementation, this would verify the password hash
        return self.hashed_password == plain_password

    def __str__(self) -> str:
        return "[HIDDEN]"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Password):
            return False
        return self.hashed_password == other.hashed_password


class UserRole(str, Enum):
    """User roles in the system."""

    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"
    PARENT = "parent"
    STAFF = "staff"


class UserStatus(str, Enum):
    """User account status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class User(DomainModel):
    """User domain model representing a user in the system."""

    email: Email
    username: str = Field(..., min_length=3, max_length=50)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    _password: Password
    is_active: bool = True
    is_verified: bool = False
    status: UserStatus = UserStatus.PENDING_VERIFICATION
    roles: List[UserRole] = Field(default_factory=lambda: [UserRole.STUDENT])
    _events: List[DomainEvent] = Field(default_factory=list, exclude=True)

    @property
    def full_name(self) -> str:
        """Get the user's full name."""
        return f"{self.first_name} {self.last_name}"

    @property
    def password(self) -> str:
        """Get the hashed password."""
        return str(self._password.hashed_password)

    @classmethod
    def register(cls, email: str, username: str, first_name: str, last_name: str, password: str) -> "User":
        """Factory method to register a new user."""
        user = cls(
            email=Email.create(email),
            username=username,
            first_name=first_name,
            last_name=last_name,
            _password=Password.create(password),
            is_active=True,
            is_verified=False,
            status=UserStatus.PENDING_VERIFICATION,
            roles=[UserRole.STUDENT],
        )

        # Record the domain event
        user.record_event(UserRegistered(user_id=str(user.id) if user.id else "new", email=email, username=username))

        return user

    def verify_email(self) -> None:
        """Mark the user's email as verified."""
        if not self.is_verified:
            self.is_verified = True
            self.status = UserStatus.ACTIVE
            self.record_event(UserEmailVerified(user_id=str(self.id), email=str(self.email)))

    def change_password(self, new_password: str) -> None:
        """Change the user's password."""
        self._password = Password.create(new_password)
        self.record_event(UserPasswordChanged(user_id=str(self.id)))

    def verify_password(self, plain_password: str) -> bool:
        """Verify a plain password against the user's hashed password."""
        return self._password.verify(plain_password)

    def record_event(self, event: DomainEvent) -> None:
        """Record a domain event."""
        if not hasattr(self, "_events"):
            self._events = []
        self._events.append(event)

    def clear_events(self) -> None:
        """Clear all domain events."""
        self._events = []

    @property
    def events(self) -> List[DomainEvent]:
        """Get all recorded domain events."""
        return getattr(self, "_events", [])

    is_verified: bool = False
    is_superuser: bool = False
    roles: List[UserRole] = [UserRole.STUDENT]
    status: UserStatus = UserStatus.PENDING_VERIFICATION
    last_login: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "username": "johndoe",
                "first_name": "John",
                "last_name": "Doe",
                "is_active": True,
                "is_verified": False,
                "roles": ["student"],
            }
        }

    @property
    def full_name(self) -> str:
        """Return the full name of the user."""
        return f"{self.first_name} {self.last_name}"

    def has_role(self, role: UserRole) -> bool:
        """Check if user has the specified role."""
        return role in self.roles

    def has_any_role(self, roles: List[UserRole]) -> bool:
        """Check if user has any of the specified roles."""
        return any(role in self.roles for role in roles)

    def has_all_roles(self, roles: List[UserRole]) -> bool:
        """Check if user has all of the specified roles."""
        return all(role in self.roles for role in roles)


class UserCreate(DomainModel):
    """DTO for creating a new user."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8, max_length=100)
    password_confirm: str

    @validator("password_confirm")
    def passwords_match(cls, v, values, **kwargs):
        if "password" in values and v != values["password"]:
            raise ValueError("passwords do not match")
        return v


class UserUpdate(DomainModel):
    """DTO for updating user information."""

    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    status: Optional[UserStatus] = None
    roles: Optional[List[UserRole]] = None
