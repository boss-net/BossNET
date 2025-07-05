#!/usr/bin/env python3
"""
Database initialization script for the Student Performance Dashboard.
This script creates the database and loads sample data.
"""
import logging
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_environment():
    """Load environment variables from .env file."""
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        logger.error(".env file not found. Please create one from .env.example")
        sys.exit(1)

    load_dotenv(dotenv_path=env_path)

    # Verify required environment variables
    required_vars = ["POSTGRES_SERVER", "POSTGRES_PORT", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"]

    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)


def get_db_connection_string():
    """Construct the database connection string from environment variables."""
    return f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_SERVER')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"


def run_psql_script(script_path):
    """Run a PostgreSQL script using psql command line."""
    try:
        # Set PGPASSWORD as an environment variable for psql
        env = os.environ.copy()
        env["PGPASSWORD"] = os.getenv("POSTGRES_PASSWORD")

        cmd = [
            "psql",
            "-h",
            os.getenv("POSTGRES_SERVER"),
            "-p",
            os.getenv("POSTGRES_PORT"),
            "-U",
            os.getenv("POSTGRES_USER"),
            "-d",
            os.getenv("POSTGRES_DB"),
            "-f",
            str(script_path),
        ]

        logger.info(f"Running script: {script_path}")
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"Error running script {script_path}:")
            logger.error(result.stderr)
            return False

        logger.info(f"Successfully executed {script_path}")
        return True

    except Exception as e:
        logger.error(f"Error executing script {script_path}: {str(e)}")
        return False


def main():
    """Main function to initialize the database."""
    logger.info("Starting database initialization...")

    # Load environment variables
    load_environment()

    # Get the directory containing this script
    script_dir = Path(__file__).parent

    # Path to the SQL initialization script
    init_script = script_dir / "init.sql"

    # Run the initialization script
    if not run_psql_script(init_script):
        logger.error("Database initialization failed")
        sys.exit(1)

    logger.info("Database initialization completed successfully!")


if __name__ == "__main__":
    main()
