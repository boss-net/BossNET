#!/usr/bin/env python3
"""
Database management script for migrations and initialization.
"""
import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from src.config import settings
from src.database.base import Base, async_engine, sync_engine
from src.models import *  # Import all models to ensure they're registered with SQLAlchemy

from alembic import command

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the directory containing this script
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
ALEMBIC_CFG = PROJECT_ROOT / "alembic.ini"


def run_migrations():
    """Run database migrations using Alembic."""
    logger.info("Running database migrations...")

    # Configure Alembic
    alembic_cfg = Config(str(ALEMBIC_CFG))

    try:
        # Run the upgrade command
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        raise


def create_tables():
    """Create database tables directly using SQLAlchemy."""
    logger.info("Creating database tables...")
    try:
        # Create all tables
        Base.metadata.create_all(bind=sync_engine)
        logger.info("Database tables created successfully")
    except SQLAlchemyError as e:
        logger.error(f"Error creating database tables: {e}")
        raise


async def drop_tables():
    """Drop all database tables."""
    confirm = input("Are you sure you want to drop all tables? This will delete all data. (y/n): ")
    if confirm.lower() != "y":
        logger.info("Operation cancelled")
        return

    logger.info("Dropping all database tables...")
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Dropped all database tables")
    except SQLAlchemyError as e:
        logger.error(f"Error dropping tables: {e}")
        raise


def reset_database():
    """Reset the database by dropping and recreating all tables."""
    logger.info("Resetting database...")

    # Drop all tables
    asyncio.run(drop_tables())

    # Create all tables
    create_tables()

    logger.info("Database reset complete")


def check_connection():
    """Check if the database connection is working."""
    logger.info("Checking database connection...")
    try:
        with sync_engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            logger.info(f"Database connection successful. PostgreSQL version: {version}")
            return True
    except SQLAlchemyError as e:
        logger.error(f"Database connection failed: {e}")
        return False


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Database management utility")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Migrate command
    migrate_parser = subparsers.add_parser("migrate", help="Run database migrations")

    # Create tables command
    create_parser = subparsers.add_parser("create-tables", help="Create database tables")

    # Drop tables command
    drop_parser = subparsers.add_parser("drop-tables", help="Drop all database tables")

    # Reset database command
    reset_parser = subparsers.add_parser("reset", help="Reset the database (drop and recreate all tables)")

    # Check connection command
    check_parser = subparsers.add_parser("check", help="Check database connection")

    return parser.parse_args()


def main():
    """Main entry point for the database management script."""
    args = parse_args()

    if not args.command:
        logger.error("No command specified")
        return

    try:
        if args.command == "migrate":
            run_migrations()
        elif args.command == "create-tables":
            create_tables()
        elif args.command == "drop-tables":
            asyncio.run(drop_tables())
        elif args.command == "reset":
            reset_database()
        elif args.command == "check":
            check_connection()
        else:
            logger.error(f"Unknown command: {args.command}")
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
