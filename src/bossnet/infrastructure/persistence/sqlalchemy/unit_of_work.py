from contextlib import asynccontextmanager
from typing import Any, Callable, Generic, TypeVar

from core.domain.repositories.user_repository import UserRepository as UserRepositoryPort
from infrastructure.persistence.sqlalchemy.repositories.user_repository import UserRepository
from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session

T = TypeVar("T")


class UnitOfWork:
    """Unit of Work pattern implementation for SQLAlchemy."""

    def __init__(self, session_factory: Callable[..., AsyncSession]):
        """Initialize with a session factory."""
        self.session_factory = session_factory
        self.session: AsyncSession = None

        # Initialize repositories
        self._user_repository = None

    async def __aenter__(self) -> "UnitOfWork":
        """Enter the async context manager."""
        self.session = self.session_factory()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the async context manager."""
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()

        await self.session.close()

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Roll back the current transaction."""
        await self.session.rollback()

    async def refresh(self, instance: Any) -> None:
        """Refresh the state of an instance."""
        await self.session.refresh(instance)

    @property
    def users(self) -> UserRepositoryPort:
        """Get the user repository."""
        if self._user_repository is None:
            self._user_repository = UserRepository(self.session)
        return self._user_repository


class UnitOfWorkManager:
    """Manager for Unit of Work pattern."""

    def __init__(self, session_factory: Callable[..., AsyncSession]):
        """Initialize with a session factory."""
        self.session_factory = session_factory

    async def start(self) -> UnitOfWork:
        """Start a new unit of work."""
        return await UnitOfWork(self.session_factory).__aenter__()

    @asynccontextmanager
    async def transaction(self):
        """Context manager for a transaction."""
        uow = await self.start()
        try:
            yield uow
            await uow.commit()
        except Exception:
            await uow.rollback()
            raise
        finally:
            await uow.__aexit__(None, None, None)
