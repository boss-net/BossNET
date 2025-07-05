"""
User domain entity - Clean Architecture
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """User domain entity"""

    email: str
    hashed_password: str
    full_name: str
    is_active: bool = True
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()

    def deactivate(self) -> None:
        """Deactivate user account"""
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def activate(self) -> None:
        """Activate user account"""
        self.is_active = True
        self.updated_at = datetime.utcnow()

    def update_profile(self, full_name: Optional[str] = None) -> None:
        """Update user profile"""
        if full_name is not None:
            self.full_name = full_name
        self.updated_at = datetime.utcnow()
