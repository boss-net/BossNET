"""
User-related Pydantic schemas
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, validator


class UserBase(BaseModel):
    """Base user schema"""

    email: EmailStr
    full_name: str
    is_active: bool = True


class UserCreate(UserBase):
    """Schema for user creation"""

    password: str

    @validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserUpdate(BaseModel):
    """Schema for user updates"""

    full_name: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """Schema for user responses"""

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class UserInDB(UserBase):
    """Schema for user in database"""

    id: int
    hashed_password: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
