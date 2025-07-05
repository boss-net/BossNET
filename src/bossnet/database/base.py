import os
from typing import AsyncGenerator, Generator, Optional

from sqlalchemy import MetaData, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.orm.decl_api import DeclarativeMeta
from sqlalchemy.pool import NullPool

from ..config import settings

# Naming convention for database constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Create base class with naming convention
Base: DeclarativeMeta = declarative_base(metadata=MetaData(naming_convention=convention))  # type: ignore

# Database engines and session factories
sync_engine = None
async_engine: Optional[AsyncEngine] = None
SessionLocal = None
AsyncSessionLocal = None


def init_database():
    """Initialize database connections and session factories."""
    global sync_engine, async_engine, SessionLocal, AsyncSessionLocal

    if sync_engine is None:
        sync_engine = create_engine(
            settings.SYNC_DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            echo=settings.SQL_ECHO,
        )

    if async_engine is None:
        async_engine = create_async_engine(
            settings.ASYNC_DATABASE_URL,
            echo=settings.SQL_ECHO,
            future=True,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            poolclass=NullPool if settings.TESTING else None,
        )

    # Create session factories
    SessionLocal = sessionmaker(
        bind=sync_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        class_=Session,
    )

    AsyncSessionLocal = sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


# Initialize database on import
init_database()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function that yields a synchronous database session.

    Yields:
        Session: A database session
    """
    if SessionLocal is None:
        init_database()

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function that yields an asynchronous database session.

    Yields:
        AsyncSession: An async database session
    """
    if AsyncSessionLocal is None:
        init_database()

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()


# Alias for FastAPI dependency injection
get_db_session = get_async_db
