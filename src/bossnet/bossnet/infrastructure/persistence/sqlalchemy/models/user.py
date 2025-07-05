from datetime import datetime
from typing import Any, Dict, List, Optional

from core.entities.user import UserRole, UserStatus
from sqlalchemy import ARRAY, JSON, Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Table, event
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from .base import Base


class UserRoleModel(Base):
    """SQLAlchemy model for User Role association."""

    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(20), nullable=False)

    # Add a unique constraint on the combination of user_id and role
    __table_args__ = ({"sqlite_autoincrement": True},)

    def __repr__(self) -> str:
        return f"<UserRoleModel(user_id={self.user_id}, role='{self.role}')>"


class UserModel(Base):
    """SQLAlchemy User model"""

    __tablename__ = "users"

    # Core fields
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Status fields
    is_verified = Column(Boolean, default=False, nullable=False)
    status = Column(String(20), default=UserStatus.PENDING_VERIFICATION.value, nullable=False)

    # Timestamps
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Additional metadata
    metadata_ = Column("metadata", JSON, default=dict, nullable=True)

    # Relationships
    roles_rel = relationship("UserRoleModel", backref="user", cascade="all, delete-orphan", lazy="selectin")

    @property
    def roles(self) -> List[str]:
        """Get roles as a list of strings."""
        return [role.role for role in self.roles_rel]

    @roles.setter
    def roles(self, role_names: List[str]):
        """Set roles from a list of role names."""
        # Remove existing roles
        self.roles_rel = []

        # Add new roles
        for role_name in role_names:
            self.roles_rel.append(UserRoleModel(role=role_name))

    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return self.is_active

    @property
    def is_anonymous(self) -> bool:
        """Check if user is anonymous."""
        return False

    def __repr__(self) -> str:
        return f"<UserModel(id={self.id}, email='{self.email}', full_name='{self.full_name}')>"


class RefreshTokenModel(Base):
    """SQLAlchemy model for RefreshToken entity."""

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    user_agent = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)

    @property
    def is_expired(self) -> bool:
        """Check if the token is expired."""
        return datetime.utcnow() >= self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if the token is valid (not expired and not revoked)."""
        return not self.revoked and not self.is_expired

    def revoke(self) -> None:
        """Revoke the token."""
        self.revoked = True

    def __repr__(self) -> str:
        return f"<RefreshToken(user_id={self.user_id}, expires_at={self.expires_at})>"


# Set up the relationship between User and RefreshToken
UserModel.refresh_tokens = relationship("RefreshTokenModel", back_populates="user", lazy="dynamic")
RefreshTokenModel.user = relationship("UserModel", back_populates="refresh_tokens")


@event.listens_for(Session, "before_flush")
def validate_user_roles(session: Session, context: Any, instances: Any) -> None:
    """Validate user roles before flush."""
    for instance in session.new | session.dirty:
        if isinstance(instance, UserModel):
            # Ensure at least one role is assigned
            if not instance.roles:
                instance.roles = [UserRole.STUDENT.value]

            # Validate role values
            for role in instance.roles:
                if role not in [r.value for r in UserRole]:
                    raise ValueError(f"Invalid role: {role}")


class RoleModel(Base):
    """SQLAlchemy model for Role entity."""

    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    permissions = Column(ARRAY(String), default=[], nullable=False)

    # Relationships
    users = relationship("UserModel", secondary="user_roles", back_populates="roles_rel")

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name='{self.name}')>"
