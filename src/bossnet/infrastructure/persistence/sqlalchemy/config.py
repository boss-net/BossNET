from typing import AsyncGenerator, Optional

from core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL_ASYNC,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    connect_args={
        "server_settings": {
            "application_name": settings.APP_NAME,
            "timezone": "UTC",
        },
        "command_timeout": settings.DB_COMMAND_TIMEOUT,
    },
)

# Create async session factory
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Create scoped session factory
AsyncScopedSession = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_scoped_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides a scoped async database session."""
    session = AsyncScopedSession()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


def create_tables():
    """Create all database tables."""
    # Import all models here to ensure they are registered with SQLAlchemy
    from infrastructure.persistence.sqlalchemy.models import user  # noqa
    from sqlalchemy import inspect
    from sqlalchemy.schema import CreateSchema

    async def _create_tables():
        # Create schema if it doesn't exist
        async with engine.begin() as conn:
            # Create public schema if it doesn't exist
            await conn.execute("CREATE SCHEMA IF NOT EXISTS public")

            # Create tables
            from infrastructure.persistence.sqlalchemy.models.base import Base

            await conn.run_sync(Base.metadata.create_all)

    import asyncio

    asyncio.run(_create_tables())


def drop_tables():
    """Drop all database tables."""
    from sqlalchemy.schema import CreateSchema, DropSchema

    async def _drop_tables():
        async with engine.begin() as conn:
            # Drop all tables
            from infrastructure.persistence.sqlalchemy.models.base import Base

            await conn.run_sync(Base.metadata.drop_all)

            # Recreate the public schema
            await conn.execute(DropSchema("public", cascade=True, if_exists=True))
            await conn.execute(CreateSchema("public"))

    import asyncio

    asyncio.run(_drop_tables())
