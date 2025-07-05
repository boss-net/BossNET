#!/usr/bin/env python3
"""
Launch script for the Student Performance Dashboard
"""
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_dependencies():
    """Check if all required dependencies are installed."""
    required_packages = ["dash", "dash-bootstrap-components", "plotly", "pandas", "sqlalchemy", "redis", "python-dotenv"]

    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(f"❌ Missing required packages: {', '.join(missing_packages)}")
        print("Install them with: pip install " + " ".join(missing_packages))
        return False

    print("✅ All required packages are installed")
    return True


def check_database_connection():
    """Check if database is accessible."""
    try:
        from dotenv import load_dotenv
        from sqlalchemy import create_engine, text

        load_dotenv()
        db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/student_data_db")

        engine = create_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()

        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("Please ensure PostgreSQL is running and the database exists")
        return False


def check_redis_connection():
    """Check if Redis is accessible."""
    try:
        import redis
        from dotenv import load_dotenv

        load_dotenv()
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

        r = redis.from_url(redis_url)
        r.ping()

        print("✅ Redis connection successful")
        return True
    except Exception as e:
        print(f"⚠️ Redis connection failed: {e}")
        print("Dashboard will work without caching")
        return False


def launch_dashboard():
    """Launch the Student Performance Dashboard."""
    dashboard_path = project_root / "dashboards" / "student_performance" / "app.py"

    if not dashboard_path.exists():
        print(f"❌ Dashboard file not found: {dashboard_path}")
        return False

    print("🚀 Launching Student Performance Dashboard...")
    print("📊 Dashboard will be available at: http://localhost:8050")
    print("🔄 Auto-refresh is enabled (30 seconds)")
    print("⏹️ Press Ctrl+C to stop the dashboard")
    print("-" * 50)

    try:
        # Change to dashboard directory
        os.chdir(dashboard_path.parent)

        # Launch the dashboard
        subprocess.run([sys.executable, "app.py"], check=True)

    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped by user")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to launch dashboard: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def main():
    """Main function to launch the performance dashboard."""
    print("🎓 Student Performance Dashboard Launcher")
    print("=" * 50)

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    # Check database connection
    if not check_database_connection():
        sys.exit(1)

    # Check Redis (optional)
    check_redis_connection()

    # Launch dashboard
    if not launch_dashboard():
        sys.exit(1)


if __name__ == "__main__":
    main()
