from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field, HttpUrl, root_validator, validator
from pydantic.class_validators import root_validator

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenBase(BaseModel):
    token: str
    token_type: str

    class Config:
        orm_mode = True


class Token(TokenBase):
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    scopes: List[str] = []
    exp: Optional[datetime] = None
    iat: Optional[datetime] = None
    jti: Optional[str] = None
    type: Optional[str] = "access"  # 'access' or 'refresh'


class TokenData(BaseModel):
    username: Optional[str] = None
    scopes: list[str] = []


class UserRole(str, Enum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"
    STAFF = "staff"


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = False  # Requires email verification by default
    is_verified: bool = False
    role: UserRole = UserRole.STUDENT

    @validator("username")
    def username_alphanumeric(cls, v):
        if not v.isalnum():
            raise ValueError("Username must be alphanumeric")
        return v

    @validator("email")
    def email_must_contain_at(cls, v):
        if "@" not in v:
            raise ValueError("Email must contain @")
        return v.lower()


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserInDBBase(UserBase):
    id: int
    hashed_password: str
    email_verification_token: Optional[str] = None
    reset_password_token: Optional[str] = None
    reset_password_expires: Optional[datetime] = None
    last_login: Optional[datetime] = None
    login_attempts: int = 0
    account_locked_until: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class UserInDB(UserInDBBase):
    pass


class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class PasswordMixin:
    @classmethod
    def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @classmethod
    def get_password_hash(cls, password: str) -> str:
        return pwd_context.hash(password)

    @classmethod
    def generate_reset_token(cls, user_id: int) -> str:
        """Generate a password reset token"""
        expires_delta = timedelta(hours=24)
        to_encode = {"sub": str(user_id), "type": "reset", "exp": datetime.utcnow() + expires_delta}
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    @classmethod
    def verify_reset_token(cls, token: str) -> Optional[int]:
        """Verify password reset token and return user_id if valid"""
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM], options={"require": ["exp", "sub", "type"]}
            )
            if payload.get("type") != "reset":
                return None
            return int(payload["sub"])
        except (jwt.JWTError, KeyError, ValueError):
            return None


# Initialize password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)  # Increased for better security


def create_access_token(
    data: dict, secret_key: str, expires_delta: Optional[timedelta] = None, algorithm: str = "HS256"
) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret_key, algorithm=algorithm)
