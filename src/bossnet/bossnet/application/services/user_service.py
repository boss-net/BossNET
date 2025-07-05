"""
User service - Application layer
"""

from typing import List, Optional

from src.core.domain.entities.user import User
from src.core.domain.repositories.user_repository import UserRepositoryInterface


class UserService:
    """User service for user management operations"""

    def __init__(self, user_repository: UserRepositoryInterface):
        self._user_repository = user_repository

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return await self._user_repository.get_by_id(user_id)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return await self._user_repository.get_by_email(email)

    async def update_user(self, user_id: int, full_name: Optional[str] = None, is_active: Optional[bool] = None) -> User:
        """Update user profile"""
        user = await self._user_repository.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        # Update fields if provided
        if full_name is not None:
            user.update_profile(full_name=full_name)

        if is_active is not None:
            if is_active:
                user.activate()
            else:
                user.deactivate()

        return await self._user_repository.update(user)

    async def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """List users with pagination"""
        return await self._user_repository.list_users(skip=skip, limit=limit)

    async def delete_user(self, user_id: int) -> bool:
        """Delete user"""
        return await self._user_repository.delete(user_id)
