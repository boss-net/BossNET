"""
User-related models for authentication and authorization.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Table, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base


class UserStatus(str, Enum):
    """User account status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"
    LOCKED = "locked"


class UserRole(str, Enum):
    """User roles in the system."""

    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"
    PARENT = "parent"
    ANALYST = "analyst"
    VIEWER = "viewer"


# Association table for many-to-many relationship between users and roles
user_roles_table = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("assigned_at", DateTime(timezone=True), server_default=func.now()),
    Column("assigned_by", Integer, ForeignKey("users.id"), nullable=True),
    UniqueConstraint("user_id", "role_id", name="uq_user_roles"),
)


class RoleModel(Base):
    """Role model for role-based access control."""

    __tablename__ = "roles"

    # Core fields
    name = Column(String(50), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Permissions (stored as JSON array)
    permissions = Column(JSON, default=list, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_system_role = Column(Boolean, default=False, nullable=False)  # Cannot be deleted

    # Relationships
    users = relationship("UserModel", secondary=user_roles_table, back_populates="roles", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Role(name='{self.name}', display_name='{self.display_name}')>"


class UserModel(Base):
    """User model for authentication and user management."""

    __tablename__ = "users"

    # Authentication fields
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    # Profile fields
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    full_name = Column(String(200), nullable=True)  # Computed field
    phone = Column(String(20), nullable=True)

    # Status and verification
    status = Column(String(30), default=UserStatus.PENDING_VERIFICATION.value, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)

    # Login tracking
    last_login = Column(DateTime(timezone=True), nullable=True)
    login_count = Column(Integer, default=0, nullable=False)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    # Verification
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_token = Column(String(255), nullable=True, index=True)
    verification_token_expires = Column(DateTime(timezone=True), nullable=True)

    # Password reset
    password_reset_token = Column(String(255), nullable=True, index=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    password_changed_at = Column(DateTime(timezone=True), nullable=True)

    # Profile and preferences
    avatar_url = Column(String(500), nullable=True)
    timezone = Column(String(50), default="Asia/Dhaka", nullable=False)
    language = Column(String(10), default="en", nullable=False)
    preferences = Column(JSON, default=dict, nullable=True)

    # Metadata
    metadata_ = Column("metadata", JSON, default=dict, nullable=True)

    # Relationships
    roles = relationship("RoleModel", secondary=user_roles_table, back_populates="users", lazy="selectin")

    refresh_tokens = relationship("RefreshTokenModel", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")

    # Indexes
    __table_args__ = (
        Index("ix_users_email_status", "email", "status"),
        Index("ix_users_verification_token", "verification_token"),
        Index("ix_users_reset_token", "password_reset_token"),
    )

    @property
    def display_name(self) -> str:
        """Get user's display name."""
        if self.full_name:
            return self.full_name
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_locked(self) -> bool:
        """Check if user account is locked."""
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until

    @property
    def role_names(self) -> List[str]:
        """Get list of role names."""
        return [role.name for role in self.roles]

    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role."""
        return role_name in self.role_names

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        if self.is_superuser:
            return True

        for role in self.roles:
            if permission in role.permissions:
                return True
        return False

    def lock_account(self, duration_minutes: int = 30) -> None:
        """Lock user account for specified duration."""
        self.locked_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
        self.status = UserStatus.LOCKED.value

    def unlock_account(self) -> None:
        """Unlock user account."""
        self.locked_until = None
        self.failed_login_attempts = 0
        if self.status == UserStatus.LOCKED.value:
            self.status = UserStatus.ACTIVE.value

    def record_login(self) -> None:
        """Record successful login."""
        self.last_login = datetime.utcnow()
        self.login_count += 1
        self.failed_login_attempts = 0

    def record_failed_login(self) -> None:
        """Record failed login attempt."""
        self.failed_login_attempts += 1

        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.lock_account(30)  # Lock for 30 minutes

    def __repr__(self) -> str:
        return f"<User(email='{self.email}', name='{self.display_name}')>"


class RefreshTokenModel(Base):
    """Refresh token model for JWT token management."""

    __tablename__ = "refresh_tokens"

    # Token fields
    token = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Expiration and status
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    # Client information
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    device_info = Column(JSON, nullable=True)

    # Relationships
    user = relationship("UserModel", back_populates="refresh_tokens")

    # Indexes
    __table_args__ = (
        Index("ix_refresh_tokens_user_active", "user_id", "is_revoked"),
        Index("ix_refresh_tokens_expires", "expires_at"),
    )

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.utcnow() >= self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if token is valid (not expired and not revoked)."""
        return not self.is_revoked and not self.is_expired

    def revoke(self) -> None:
        """Revoke the token."""
        self.is_revoked = True
        self.revoked_at = datetime.utcnow()

    def __repr__(self) -> str:
        return f"<RefreshToken(user_id={self.user_id}, expires_at={self.expires_at})>"


class UserSessionModel(Base):
    """User session model for tracking active sessions."""

    __tablename__ = "user_sessions"

    # Session fields
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Session data
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    device_info = Column(JSON, nullable=True)
    location_info = Column(JSON, nullable=True)

    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("UserModel", backref="sessions")

    # Indexes
    __table_args__ = (
        Index("ix_user_sessions_user_active", "user_id", "is_active"),
        Index("ix_user_sessions_expires", "expires_at"),
    )

    @property
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.utcnow() >= self.expires_at

    def end_session(self) -> None:
        """End the session."""
        self.is_active = False
        self.ended_at = datetime.utcnow()

    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()

    def __repr__(self) -> str:
        return f"<UserSession(user_id={self.user_id}, session_id='{self.session_id[:8]}...')>"
