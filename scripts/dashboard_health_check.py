#!/usr/bin/env python3
"""
Dashboard Health Check Script
Monitors the health and performance of running dashboards.
"""

import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

import psutil
import redis
import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()


class DashboardHealthChecker:
    """Health checker for dashboard services."""

    def __init__(self):
        self.services = {
            "performance_dashboard": {"url": "http://localhost:8050", "name": "Student Performance Dashboard", "port": 8050},
            "demographics_dashboard": {"url": "http://localhost:8501", "name": "Demographic Insights Dashboard", "port": 8501},
        }

        self.database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/student_data_db")
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    def check_service_health(self, service_name: str) -> Dict:
        """Check health of a specific service."""
        service = self.services.get(service_name)
        if not service:
            return {"status": "unknown", "error": "Service not found"}

        try:
            # Check if port is listening
            port_open = self._check_port(service["port"])
            if not port_open:
                return {"status": "down", "error": f"Port {service['port']} not listening", "response_time": None}

            # Check HTTP response
            start_time = time.time()
            response = requests.get(service["url"], timeout=10)
            response_time = (time.time() - start_time) * 1000  # Convert to ms

            if response.status_code == 200:
                return {"status": "healthy", "response_time": round(response_time, 2), "status_code": response.status_code}
            else:
                return {
                    "status": "unhealthy",
                    "response_time": round(response_time, 2),
                    "status_code": response.status_code,
                    "error": f"HTTP {response.status_code}",
                }

        except requests.exceptions.ConnectionError:
            return {"status": "down", "error": "Connection refused", "response_time": None}
        except requests.exceptions.Timeout:
            return {"status": "timeout", "error": "Request timeout", "response_time": None}
        except Exception as e:
            return {"status": "error", "error": str(e), "response_time": None}

    def check_database_health(self) -> Dict:
        """Check database connectivity and performance."""
        try:
            engine = create_engine(self.database_url)

            start_time = time.time()
            with engine.connect() as conn:
                # Test basic connectivity
                result = conn.execute(text("SELECT 1"))
                result.fetchone()

                # Test a more complex query
                result = conn.execute(
                    text(
                        """
                    SELECT COUNT(*) as student_count
                    FROM students
                    WHERE is_deleted = false
                """
                    )
                )
                student_count = result.fetchone()[0]

            response_time = (time.time() - start_time) * 1000

            return {"status": "healthy", "response_time": round(response_time, 2), "student_count": student_count}

        except Exception as e:
            return {"status": "unhealthy", "error": str(e), "response_time": None}

    def check_redis_health(self) -> Dict:
        """Check Redis connectivity and performance."""
        try:
            r = redis.from_url(self.redis_url, decode_responses=True)

            start_time = time.time()

            # Test basic connectivity
            r.ping()

            # Test set/get operations
            test_key = f"health_check_{int(time.time())}"
            r.set(test_key, "test_value", ex=60)
            value = r.get(test_key)
            r.delete(test_key)

            response_time = (time.time() - start_time) * 1000

            # Get Redis info
            info = r.info()

            return {
                "status": "healthy",
                "response_time": round(response_time, 2),
                "memory_used": info.get("used_memory_human", "Unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
            }

        except Exception as e:
            return {"status": "unhealthy", "error": str(e), "response_time": None}

    def check_system_resources(self) -> Dict:
        """Check system resource usage."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()

            # Disk usage
            disk = psutil.disk_usage("/")

            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_percent": disk.percent,
                "disk_free_gb": round(disk.free / (1024**3), 2),
            }

        except Exception as e:
            return {"error": str(e)}

    def _check_port(self, port: int) -> bool:
        """Check if a port is listening."""
        for conn in psutil.net_connections():
            if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                return True
        return False

    def run_health_check(self) -> Dict:
        """Run complete health check."""
        timestamp = datetime.now().isoformat()

        health_report = {
            "timestamp": timestamp,
            "overall_status": "healthy",
            "services": {},
            "infrastructure": {},
            "system": {},
        }

        # Check services
        for service_name in self.services:
            service_health = self.check_service_health(service_name)
            health_report["services"][service_name] = service_health

            if service_health["status"] not in ["healthy"]:
                health_report["overall_status"] = "degraded"

        # Check infrastructure
        health_report["infrastructure"]["database"] = self.check_database_health()
        health_report["infrastructure"]["redis"] = self.check_redis_health()

        # Check system resources
        health_report["system"] = self.check_system_resources()

        # Determine overall status
        if health_report["infrastructure"]["database"]["status"] != "healthy":
            health_report["overall_status"] = "unhealthy"

        return health_report

    def print_health_report(self, report: Dict):
        """Print formatted health report."""
        print("🏥 Dashboard Health Check Report")
        print("=" * 50)
        print(f"Timestamp: {report['timestamp']}")
        print(f"Overall Status: {self._get_status_emoji(report['overall_status'])} {report['overall_status'].upper()}")
        print()

        # Services
        print("📊 Dashboard Services:")
        for service_name, health in report["services"].items():
            service_display_name = self.services[service_name]["name"]
            status_emoji = self._get_status_emoji(health["status"])
            print(f"  {status_emoji} {service_display_name}")
            print(f"     Status: {health['status']}")
            if health.get("response_time"):
                print(f"     Response Time: {health['response_time']}ms")
            if health.get("error"):
                print(f"     Error: {health['error']}")
            print()

        # Infrastructure
        print("🔧 Infrastructure:")

        # Database
        db_health = report["infrastructure"]["database"]
        db_emoji = self._get_status_emoji(db_health["status"])
        print(f"  {db_emoji} Database")
        print(f"     Status: {db_health['status']}")
        if db_health.get("response_time"):
            print(f"     Response Time: {db_health['response_time']}ms")
        if db_health.get("student_count"):
            print(f"     Student Records: {db_health['student_count']:,}")
        if db_health.get("error"):
            print(f"     Error: {db_health['error']}")
        print()

        # Redis
        redis_health = report["infrastructure"]["redis"]
        redis_emoji = self._get_status_emoji(redis_health["status"])
        print(f"  {redis_emoji} Redis Cache")
        print(f"     Status: {redis_health['status']}")
        if redis_health.get("response_time"):
            print(f"     Response Time: {redis_health['response_time']}ms")
        if redis_health.get("memory_used"):
            print(f"     Memory Used: {redis_health['memory_used']}")
        if redis_health.get("connected_clients"):
            print(f"     Connected Clients: {redis_health['connected_clients']}")
        if redis_health.get("error"):
            print(f"     Error: {redis_health['error']}")
        print()

        # System Resources
        print("💻 System Resources:")
        system = report["system"]
        if "error" not in system:
            print(f"  🖥️  CPU Usage: {system['cpu_percent']}%")
            print(f"  🧠 Memory Usage: {system['memory_percent']}% ({system['memory_available_gb']}GB available)")
            print(f"  💾 Disk Usage: {system['disk_percent']}% ({system['disk_free_gb']}GB free)")
        else:
            print(f"  ❌ Error: {system['error']}")

    def _get_status_emoji(self, status: str) -> str:
        """Get emoji for status."""
        emoji_map = {
            "healthy": "✅",
            "unhealthy": "❌",
            "degraded": "⚠️",
            "down": "🔴",
            "timeout": "⏰",
            "error": "💥",
            "unknown": "❓",
        }
        return emoji_map.get(status, "❓")


def main():
    """Main function."""
    checker = DashboardHealthChecker()

    if len(sys.argv) > 1 and sys.argv[1] == "--monitor":
        # Continuous monitoring mode
        print("🔄 Starting continuous health monitoring...")
        print("Press Ctrl+C to stop")
        print()

        try:
            while True:
                report = checker.run_health_check()

                # Clear screen
                os.system("clear" if os.name == "posix" else "cls")

                checker.print_health_report(report)

                # Wait before next check
                time.sleep(30)

        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped")

    elif len(sys.argv) > 1 and sys.argv[1] == "--json":
        # JSON output mode
        report = checker.run_health_check()
        print(json.dumps(report, indent=2))

    else:
        # Single check mode
        report = checker.run_health_check()
        checker.print_health_report(report)

        # Exit with appropriate code
        if report["overall_status"] == "healthy":
            sys.exit(0)
        elif report["overall_status"] == "degraded":
            sys.exit(1)
        else:
            sys.exit(2)


if __name__ == "__main__":
    main()
