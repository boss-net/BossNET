from datetime import datetime
from typing import List, Optional

from core.entities.user import User, UserRole
from core.repositories.base import UserRepository as UserRepositoryBase
from infrastructure.persistence.sqlalchemy_repository import SQLAlchemyRepository

# Import your SQLAlchemy User model here
from models.user_model import RefreshToken, UserDB
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession


class UserRepository(UserRepositoryBase, SQLAlchemyRepository[User, UserDB]):
    """SQLAlchemy implementation of User repository."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, UserDB, User)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        stmt = select(self.model).where(self.model.email == email)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            return None
        return self.entity_type.model_validate(user.__dict__)

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        stmt = select(self.model).where(self.model.username == username)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            return None
        return self.entity_type.model_validate(user.__dict__)

    async def update_last_login(self, user_id: int) -> None:
        """Update the last login timestamp for a user."""
        stmt = update(self.model).where(self.model.id == user_id).values(last_login=datetime.utcnow())
        await self.session.execute(stmt)

    async def add_user_role(self, user_id: int, role: UserRole) -> bool:
        """Add a role to a user."""
        stmt = select(self.model).where(self.model.id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            return False

        if role not in user.roles:
            user.roles.append(role)
            await self.session.commit()
            return True
        return False

    async def remove_user_role(self, user_id: int, role: UserRole) -> bool:
        """Remove a role from a user."""
        stmt = select(self.model).where(self.model.id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            return False

        if role in user.roles:
            user.roles.remove(role)
            await self.session.commit()
            return True
        return False
