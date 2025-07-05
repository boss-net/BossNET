#!/usr/bin/env python3
"""
Launch script for the Demographic Insights Dashboard
"""
import os
import subprocess
import sys
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_dependencies():
    """Check if all required dependencies are installed."""
    required_packages = ["streamlit", "plotly", "pandas", "numpy", "sqlalchemy", "python-dotenv"]

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


def launch_dashboard():
    """Launch the Demographic Insights Dashboard."""
    dashboard_path = project_root / "dashboards" / "demographic_insights" / "app.py"

    if not dashboard_path.exists():
        print(f"❌ Dashboard file not found: {dashboard_path}")
        return False

    print("🚀 Launching Demographic Insights Dashboard...")
    print("👥 Dashboard will be available at: http://localhost:8501")
    print("🔍 Interactive filters available in sidebar")
    print("⏹️ Press Ctrl+C to stop the dashboard")
    print("-" * 50)

    try:
        # Launch the dashboard with Streamlit
        subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(dashboard_path),
                "--server.port",
                "8501",
                "--server.address",
                "0.0.0.0",
                "--browser.gatherUsageStats",
                "false",
            ],
            check=True,
        )

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
    """Main function to launch the demographics dashboard."""
    print("👥 Demographic Insights Dashboard Launcher")
    print("=" * 50)

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    # Check database connection
    if not check_database_connection():
        sys.exit(1)

    # Launch dashboard
    if not launch_dashboard():
        sys.exit(1)


if __name__ == "__main__":
    main()
