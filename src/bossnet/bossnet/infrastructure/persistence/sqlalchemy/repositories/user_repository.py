"""
SQLAlchemy User repository implementation
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.domain.entities.user import User
from src.core.domain.repositories.user_repository import UserRepositoryInterface
from src.infrastructure.persistence.sqlalchemy.models.user import UserModel


class SQLAlchemyUserRepository(UserRepositoryInterface):
    """SQLAlchemy implementation of User repository"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, user: User) -> User:
        """Create a new user"""
        try:
            db_user = UserModel(
                email=user.email, hashed_password=user.hashed_password, full_name=user.full_name, is_active=user.is_active
            )

            self._session.add(db_user)
            await self._session.flush()
            await self._session.refresh(db_user)

            # Convert back to domain entity
            return User(
                id=db_user.id,
                email=db_user.email,
                hashed_password=db_user.hashed_password,
                full_name=db_user.full_name,
                is_active=db_user.is_active,
                created_at=db_user.created_at,
                updated_at=db_user.updated_at,
            )
        except IntegrityError:
            await self._session.rollback()
            raise ValueError("User with this email already exists")

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self._session.execute(stmt)
        db_user = result.scalar_one_or_none()

        if not db_user:
            return None

        return User(
            id=db_user.id,
            email=db_user.email,
            hashed_password=db_user.hashed_password,
            full_name=db_user.full_name,
            is_active=db_user.is_active,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at,
        )

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self._session.execute(stmt)
        db_user = result.scalar_one_or_none()

        if not db_user:
            return None

        return User(
            id=db_user.id,
            email=db_user.email,
            hashed_password=db_user.hashed_password,
            full_name=db_user.full_name,
            is_active=db_user.is_active,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at,
        )

    async def update(self, user: User) -> User:
        """Update user"""
        stmt = select(UserModel).where(UserModel.id == user.id)
        result = await self._session.execute(stmt)
        db_user = result.scalar_one_or_none()

        if not db_user:
            raise ValueError("User not found")

        db_user.full_name = user.full_name
        db_user.is_active = user.is_active

        await self._session.flush()
        await self._session.refresh(db_user)

        return User(
            id=db_user.id,
            email=db_user.email,
            hashed_password=db_user.hashed_password,
            full_name=db_user.full_name,
            is_active=db_user.is_active,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at,
        )

    async def delete(self, user_id: int) -> bool:
        """Delete user"""
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self._session.execute(stmt)
        db_user = result.scalar_one_or_none()

        if not db_user:
            return False

        await self._session.delete(db_user)
        return True

    async def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """List users with pagination"""
        stmt = select(UserModel).offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        db_users = result.scalars().all()

        return [
            User(
                id=db_user.id,
                email=db_user.email,
                hashed_password=db_user.hashed_password,
                full_name=db_user.full_name,
                is_active=db_user.is_active,
                created_at=db_user.created_at,
                updated_at=db_user.updated_at,
            )
            for db_user in db_users
        ]
