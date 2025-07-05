"""
Launch script for the Enrollment Trends Dashboard
"""

import logging
import os
import subprocess
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def launch_enrollment_dashboard():
    """Launch the enrollment trends dashboard."""
    try:
        # Get the project root directory
        project_root = Path(__file__).parent.parent
        dashboard_path = project_root / "dashboards" / "enrollment_trends" / "app.py"

        if not dashboard_path.exists():
            logger.error(f"Dashboard file not found: {dashboard_path}")
            return False

        # Set environment variables
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root)

        # Launch the Streamlit app
        cmd = [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(dashboard_path),
            "--server.port=8503",
            "--server.address=0.0.0.0",
            "--server.headless=true",
            "--browser.gatherUsageStats=false",
        ]

        logger.info("🚀 Launching Enrollment Trends Dashboard...")
        logger.info(f"📊 Dashboard will be available at: http://localhost:8503")
        logger.info(f"📁 Dashboard path: {dashboard_path}")

        # Start the process
        process = subprocess.Popen(
            cmd,
            env=env,
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
        )

        # Print output in real-time
        for line in process.stdout:
            print(line.strip())

        return True

    except Exception as e:
        logger.error(f"❌ Error launching enrollment dashboard: {e}")
        return False


if __name__ == "__main__":
    launch_enrollment_dashboard()
