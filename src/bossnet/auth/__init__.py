"""
Authentication and authorization module for the application.

This module provides user authentication, authorization, and user management functionality.
It includes JWT token handling, password hashing, role-based access control, and email notifications.
"""

# Import key components for easier access
from .models import (
    Token,
    TokenData,
    UserCreate,
    UserInDB,
    UserResponse,
    UserRole,
    UserUpdate,
    PasswordReset,
    PasswordChange,
    EmailVerification,
    Message,
    NewPassword,
    TokenPayload,
)

from .service import AuthService
from .dependencies import (
    get_current_user,
    get_current_active_user,
    get_current_active_superuser,
    get_password_hash,
    verify_password,
)

from .email_service import EmailService, EmailTemplate

__all__ = [
    "AuthService",
    "EmailService",
    "EmailTemplate",
    "Token",
    "TokenData",
    "UserCreate",
    "UserInDB",
    "UserResponse",
    "UserRole",
    "UserUpdate",
    "PasswordReset",
    "PasswordChange",
    "EmailVerification",
    "Message",
    "NewPassword",
    "TokenPayload",
    "get_current_user",
    "get_current_active_user",
    "get_current_active_superuser",
    "get_password_hash",
    "verify_password",
]
