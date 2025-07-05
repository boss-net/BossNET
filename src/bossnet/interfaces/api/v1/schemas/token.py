"""
Token-related Pydantic schemas
"""

from typing import Optional

from pydantic import BaseModel


class Token(BaseModel):
    """Token response schema"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Token data schema"""

    user_id: Optional[int] = None
    email: Optional[str] = None


class TokenRefresh(BaseModel):
    """Token refresh request schema"""

    refresh_token: str
