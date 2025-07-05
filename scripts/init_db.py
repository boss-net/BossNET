#!/usr/bin/env python3
"""
Initialize the database with required tables and initial data.
"""
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from src.config import settings
from src.database.base import Base
from src.models.student_model import StudentDB
from src.models.user_model import UserDB

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_db():
    """Initialize the database with required tables."""
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")

        # Create admin user if not exists
        create_initial_admin()

    except SQLAlchemyError as e:
        logger.error(f"Error initializing database: {e}")
        raise


def create_initial_admin():
    """Create an initial admin user if none exists."""
    from sqlalchemy.orm import sessionmaker
    from src.auth.models import get_password_hash

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Check if admin user already exists
        admin = session.query(UserDB).filter_by(username="admin").first()
        if not admin:
            # Create admin user (password: admin123)
            admin_user = UserDB(
                username="admin",
                email="admin@example.com",
                hashed_password=get_password_hash("admin123"),
                full_name="Admin User",
                role="admin",
                is_active=True,
            )
            session.add(admin_user)
            session.commit()
            logger.info("Created initial admin user")
        else:
            logger.info("Admin user already exists")

    except Exception as e:
        session.rollback()
        logger.error(f"Error creating admin user: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    # Create database engine
    engine = create_engine(settings.DATABASE_URL)

    print("Initializing database...")
    init_db()
    print("Database initialization complete.")
