"""
Security utility functions for the Bangladesh Student Data API.

This module provides various security-related utilities including:
- Password hashing and verification
- JWT token handling
- Input sanitization
- Security headers
- Rate limiting utilities
"""

import re
import secrets
import string
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from config.security import security_settings
from fastapi import HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: The data to encode in the token
        expires_delta: Optional expiration time delta

    Returns:
        str: The encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify a JWT token.

    Args:
        token: The JWT token to decode

    Returns:
        Dict[str, Any]: The decoded token payload

    Raises:
        HTTPException: If the token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM], options={"verify_aud": False})
        return payload
    except JWTError:
        raise credentials_exception


def sanitize_input(input_str: str) -> str:
    """
    Sanitize user input to prevent XSS and injection attacks.

    Args:
        input_str: The input string to sanitize

    Returns:
        str: The sanitized string
    """
    if not input_str:
        return ""

    # Remove any HTML/script tags
    sanitized = re.sub(r"<[^>]*>", "", str(input_str))

    # Remove control characters
    sanitized = re.sub(r"[\x00-\x1F\x7F-\x9F]", "", sanitized)

    return sanitized.strip()


def generate_secure_random_string(length: int = 32) -> str:
    """
    Generate a secure random string.

    Args:
        length: Length of the random string to generate

    Returns:
        str: A secure random string
    """
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def get_client_ip(request: Request) -> str:
    """
    Get the client's IP address from the request.

    Args:
        request: The FastAPI request object

    Returns:
        str: The client's IP address
    """
    if request.client is None:
        return "unknown"

    # Try to get the real IP behind proxies
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()

    return request.client.host


def get_security_headers() -> Dict[str, str]:
    """
    Get the security headers to be added to responses.

    Returns:
        Dict[str, str]: Dictionary of security headers
    """
    return {
        **security_settings.SECURITY_HEADERS,
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    }
