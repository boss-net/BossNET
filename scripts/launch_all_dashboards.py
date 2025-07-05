#!/usr/bin/env python3
"""
Launch script for all dashboards simultaneously
"""
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class DashboardLauncher:
    def __init__(self):
        self.processes = []
        self.running = True

    def check_dependencies(self):
        """Check if all required dependencies are installed."""
        required_packages = [
            "dash",
            "dash-bootstrap-components",
            "plotly",
            "pandas",
            "sqlalchemy",
            "redis",
            "python-dotenv",
            "streamlit",
            "numpy",
        ]

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

    def check_database_connection(self):
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
            return False

    def check_redis_connection(self):
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
            print("Dashboards will work without caching")
            return False

    def launch_performance_dashboard(self):
        """Launch the Student Performance Dashboard in a separate thread."""
        dashboard_path = project_root / "dashboards" / "student_performance" / "app.py"

        if not dashboard_path.exists():
            print(f"❌ Performance dashboard not found: {dashboard_path}")
            return

        try:
            print("🚀 Starting Student Performance Dashboard...")
            os.chdir(dashboard_path.parent)

            process = subprocess.Popen([sys.executable, "app.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            self.processes.append(("Performance Dashboard", process))

            # Wait a moment to check if it started successfully
            time.sleep(3)
            if process.poll() is None:
                print("✅ Student Performance Dashboard started on http://localhost:8050")
            else:
                stdout, stderr = process.communicate()
                print(f"❌ Performance Dashboard failed to start: {stderr.decode()}")

        except Exception as e:
            print(f"❌ Failed to launch Performance Dashboard: {e}")

    def launch_demographics_dashboard(self):
        """Launch the Demographic Insights Dashboard in a separate thread."""
        dashboard_path = project_root / "dashboards" / "demographic_insights" / "app.py"

        if not dashboard_path.exists():
            print(f"❌ Demographics dashboard not found: {dashboard_path}")
            return

        try:
            print("🚀 Starting Demographic Insights Dashboard...")

            process = subprocess.Popen(
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
                    "--server.headless",
                    "true",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.processes.append(("Demographics Dashboard", process))

            # Wait a moment to check if it started successfully
            time.sleep(5)
            if process.poll() is None:
                print("✅ Demographic Insights Dashboard started on http://localhost:8501")
            else:
                stdout, stderr = process.communicate()
                print(f"❌ Demographics Dashboard failed to start: {stderr.decode()}")

        except Exception as e:
            print(f"❌ Failed to launch Demographics Dashboard: {e}")

    def monitor_processes(self):
        """Monitor running processes and restart if needed."""
        while self.running:
            time.sleep(10)

            for name, process in self.processes:
                if process.poll() is not None:
                    print(f"⚠️ {name} has stopped unexpectedly")
                    # Could implement restart logic here

    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print("\n🛑 Shutting down all dashboards...")
        self.running = False

        for name, process in self.processes:
            print(f"   Stopping {name}...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

        print("✅ All dashboards stopped")
        sys.exit(0)

    def launch_all(self):
        """Launch all dashboards."""
        print("🎓 Bangladesh Education Data Warehouse - Dashboard Launcher")
        print("=" * 60)

        # Check dependencies
        if not self.check_dependencies():
            sys.exit(1)

        # Check database connection
        if not self.check_database_connection():
            sys.exit(1)

        # Check Redis (optional)
        self.check_redis_connection()

        # Set up signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        print("\n🚀 Launching dashboards...")

        # Launch dashboards in separate threads
        performance_thread = threading.Thread(target=self.launch_performance_dashboard)
        demographics_thread = threading.Thread(target=self.launch_demographics_dashboard)

        performance_thread.start()
        time.sleep(2)  # Stagger the launches
        demographics_thread.start()

        # Wait for threads to complete initial setup
        performance_thread.join(timeout=10)
        demographics_thread.join(timeout=10)

        print("\n📊 Dashboard Status:")
        print("   🎯 Student Performance Dashboard: http://localhost:8050")
        print("   👥 Demographic Insights Dashboard: http://localhost:8501")
        print("\n⏹️ Press Ctrl+C to stop all dashboards")
        print("-" * 60)

        # Monitor processes
        try:
            self.monitor_processes()
        except KeyboardInterrupt:
            self.signal_handler(signal.SIGINT, None)


def main():
    """Main function."""
    launcher = DashboardLauncher()
    launcher.launch_all()


if __name__ == "__main__":
    main()
