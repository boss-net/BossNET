"""
Database configuration and session management
"""

from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from src.config.settings import settings

# Create declarative base
Base = declarative_base()

# Global engine instance
engine: Optional[AsyncEngine] = None
async_session_factory: Optional[async_sessionmaker] = None


def get_database_url() -> str:
    """Get the database URL based on environment"""
    if settings.TESTING:
        return settings.TEST_DATABASE_URL
    return settings.ASYNC_DATABASE_URL


def create_engine() -> AsyncEngine:
    """Create database engine"""
    database_url = get_database_url()

    return create_async_engine(
        database_url,
        echo=settings.SQL_ECHO,
        future=True,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        poolclass=NullPool if settings.TESTING else None,
    )


def get_engine() -> AsyncEngine:
    """Get or create database engine"""
    global engine
    if engine is None:
        engine = create_engine()
    return engine


def get_session_factory() -> async_sessionmaker:
    """Get or create session factory"""
    global async_session_factory
    if async_session_factory is None:
        async_session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return async_session_factory


async def get_database() -> AsyncGenerator[AsyncSession, None]:
    """Database dependency for FastAPI"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    """Create all database tables"""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables():
    """Drop all database tables"""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
