import uuid
from datetime import datetime, timedelta

from auth.models import PasswordMixin, UserRole
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text

from config import settings
from database.base import Base


class UserDB(Base, PasswordMixin):
    """Database model for users with authentication support"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    role = Column(PgEnum(UserRole, name="user_role_enum"), nullable=False, default=UserRole.STUDENT)
    is_active = Column(Boolean, default=False)  # Requires email verification
    is_verified = Column(Boolean, default=False)
    email_verification_token = Column(String(100), unique=True, nullable=True)
    reset_password_token = Column(String(100), unique=True, nullable=True)
    reset_password_expires = Column(DateTime(timezone=True), nullable=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    login_attempts = Column(Integer, default=0)
    account_locked_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"

    def to_dict(self):
        """Convert model instance to dictionary"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role.value if self.role else None,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def set_password(self, password: str):
        """Set hashed password"""
        self.hashed_password = self.get_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify password"""
        return self.verify_password(password, self.hashed_password)

    def generate_email_verification_token(self):
        """Generate email verification token"""
        self.email_verification_token = str(uuid.uuid4())
        return self.email_verification_token

    def generate_password_reset_token(self):
        """Generate password reset token"""
        self.reset_password_token = str(uuid.uuid4())
        self.reset_password_expires = datetime.utcnow() + timedelta(hours=24)
        return self.reset_password_token

    def verify_reset_token(self, token: str) -> bool:
        """Verify password reset token"""
        if not self.reset_password_token or not self.reset_password_expires:
            return False
        return self.reset_password_token == token and datetime.utcnow() < self.reset_password_expires

    def record_login_attempt(self, success: bool):
        """Record login attempt and handle account locking"""
        if success:
            self.login_attempts = 0
            self.account_locked_until = None
            self.last_login = datetime.utcnow()
        else:
            self.login_attempts += 1
            if self.login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                lockout_minutes = settings.ACCOUNT_LOCKOUT_MINUTES
                self.account_locked_until = datetime.utcnow() + timedelta(minutes=lockout_minutes)

    def is_account_locked(self) -> bool:
        """Check if account is currently locked"""
        if not self.account_locked_until:
            return False
        if datetime.utcnow() >= self.account_locked_until:
            self.account_locked_until = None
            self.login_attempts = 0
            return False
        return True


class RefreshToken(Base):
    """Refresh token model for JWT refresh tokens"""

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(512), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("UserDB", back_populates="refresh_tokens")

    def is_expired(self) -> bool:
        """Check if token is expired"""
        return datetime.utcnow() >= self.expires_at

    def revoke(self):
        """Revoke the token"""
        self.revoked_at = datetime.utcnow()

    def is_revoked(self) -> bool:
        """Check if token is revoked"""
        return self.revoked_at is not None

    def is_valid(self) -> bool:
        """Check if token is valid"""
        return not (self.is_expired() or self.is_revoked())
