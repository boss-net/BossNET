#!/usr/bin/env python3
"""
Test database connection and data loading.
"""
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_environment():
    """Load environment variables."""
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        logger.error(".env file not found. Please create one from .env.example")
        return False

    load_dotenv(dotenv_path=env_path)
    return True


def test_connection():
    """Test database connection and basic queries."""
    try:
        # Create database URL
        db_url = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_SERVER')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"

        logger.info(f"Connecting to database: {db_url}")
        engine = create_engine(db_url)

        with engine.connect() as conn:
            # Test connection
            result = conn.execute(text("SELECT version();"))
            logger.info(f"PostgreSQL version: {result.scalar()}")

            # Check if tables exist
            result = conn.execute(
                text(
                    """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public';
            """
                )
            )
            tables = [row[0] for row in result.fetchall()]
            logger.info(f"Found tables: {', '.join(tables) if tables else 'No tables found'}")

            # Count records in each table
            for table in tables:
                try:
                    count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    logger.info(f"Table '{table}': {count} records")
                except Exception as e:
                    logger.warning(f"Could not count records in {table}: {str(e)}")

            # Test a sample query
            result = conn.execute(
                text(
                    """
                SELECT
                    c.class_name,
                    COUNT(DISTINCT s.student_id) as student_count,
                    ROUND(AVG(g.grade), 2) as avg_grade
                FROM classes c
                LEFT JOIN students s ON c.class_id = s.class_id
                LEFT JOIN grades g ON s.student_id = g.student_id
                GROUP BY c.class_name
                ORDER BY c.class_name;
            """
                )
            )

            logger.info("\nClass Performance Summary:")
            logger.info("-" * 50)
            logger.info(f"{'Class':<10} | {'Students':<10} | {'Avg Grade':<10}")
            logger.info("-" * 50)
            for row in result:
                logger.info(f"{row[0]:<10} | {row[1]:<10} | {row[2]:<10.2f}")

            return True

    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return False


def main():
    """Main function to run tests."""
    logger.info("Starting database connection test...")

    if not load_environment():
        sys.exit(1)

    if test_connection():
        logger.info("\n✅ Database connection test completed successfully!")
        return 0
    else:
        logger.error("\n❌ Database connection test failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
