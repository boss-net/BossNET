import logging

from models.student_model import Base, Gender, StudentDB
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

from database.base import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_db():
    """Initialize the database with required tables"""
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")

    except SQLAlchemyError as e:
        logger.error(f"Error creating database tables: {e}")
        raise


def drop_db():
    """Drop all database tables (use with caution in production)"""
    try:
        Base.metadata.drop_all(bind=engine)
        logger.warning("Dropped all database tables")
    except SQLAlchemyError as e:
        logger.error(f"Error dropping database tables: {e}")
        raise


if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Database initialization complete.")
