#!/usr/bin/env python3
"""
Redis setup and configuration script
"""
import os
import platform
import subprocess
import sys
import time
from pathlib import Path


def check_redis_installed():
    """Check if Redis is installed on the system."""
    try:
        result = subprocess.run(["redis-server", "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ Redis is installed: {result.stdout.strip()}")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    print("❌ Redis is not installed")
    return False


def install_redis():
    """Install Redis based on the operating system."""
    system = platform.system().lower()

    print(f"🔧 Installing Redis for {system}...")

    if system == "linux":
        # Ubuntu/Debian
        try:
            subprocess.run(["sudo", "apt", "update"], check=True)
            subprocess.run(["sudo", "apt", "install", "-y", "redis-server"], check=True)
            print("✅ Redis installed successfully on Linux")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install Redis on Linux")
            print("Please install Redis manually:")
            print("  sudo apt update && sudo apt install redis-server")
            return False

    elif system == "darwin":  # macOS
        try:
            # Check if Homebrew is installed
            subprocess.run(["brew", "--version"], check=True, capture_output=True)
            subprocess.run(["brew", "install", "redis"], check=True)
            print("✅ Redis installed successfully on macOS")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Failed to install Redis on macOS")
            print("Please install Redis manually:")
            print("  brew install redis")
            print("Or install Homebrew first: https://brew.sh/")
            return False

    elif system == "windows":
        print("❌ Automatic Redis installation not supported on Windows")
        print("Please install Redis manually:")
        print("1. Download Redis from: https://github.com/microsoftarchive/redis/releases")
        print("2. Or use WSL2 with Ubuntu")
        print("3. Or use Docker: docker run -d -p 6379:6379 redis:alpine")
        return False

    else:
        print(f"❌ Unsupported operating system: {system}")
        return False


def start_redis_server():
    """Start Redis server."""
    try:
        # Check if Redis is already running
        result = subprocess.run(["redis-cli", "ping"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip() == "PONG":
            print("✅ Redis server is already running")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    print("🚀 Starting Redis server...")

    try:
        # Start Redis server in background
        if platform.system().lower() == "windows":
            subprocess.Popen(["redis-server"], creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            subprocess.Popen(["redis-server", "--daemonize", "yes"])

        # Wait a moment for server to start
        time.sleep(2)

        # Test connection
        result = subprocess.run(["redis-cli", "ping"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip() == "PONG":
            print("✅ Redis server started successfully")
            return True
        else:
            print("❌ Redis server failed to start properly")
            return False

    except Exception as e:
        print(f"❌ Failed to start Redis server: {e}")
        return False


def configure_redis():
    """Configure Redis for optimal performance."""
    try:
        import redis

        # Connect to Redis
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)

        # Test connection
        r.ping()

        # Set some basic configuration
        r.config_set("maxmemory-policy", "allkeys-lru")
        r.config_set("save", "900 1 300 10 60 10000")  # Save snapshots

        print("✅ Redis configured successfully")
        print("📊 Redis configuration:")
        print(f"   - Memory policy: {r.config_get('maxmemory-policy')}")
        print(f"   - Save policy: {r.config_get('save')}")

        return True

    except ImportError:
        print("❌ Redis Python package not installed")
        print("Install with: pip install redis")
        return False
    except Exception as e:
        print(f"❌ Failed to configure Redis: {e}")
        return False


def create_redis_config():
    """Create Redis configuration file."""
    config_content = """
# Redis Configuration for Bangladesh Education Data Warehouse
# Generated automatically

# Network
bind 127.0.0.1
port 6379
timeout 0
tcp-keepalive 300

# General
daemonize yes
supervised no
pidfile /var/run/redis/redis-server.pid
loglevel notice
logfile /var/log/redis/redis-server.log

# Snapshotting
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir /var/lib/redis

# Replication
replica-serve-stale-data yes
replica-read-only yes

# Security
# requirepass your_password_here

# Memory management
maxmemory-policy allkeys-lru
maxmemory-samples 5

# Append only file
appendonly no
appendfilename "appendonly.aof"
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

# Lua scripting
lua-time-limit 5000

# Slow log
slowlog-log-slower-than 10000
slowlog-max-len 128

# Event notification
notify-keyspace-events ""

# Advanced config
hash-max-ziplist-entries 512
hash-max-ziplist-value 64
list-max-ziplist-size -2
list-compress-depth 0
set-max-intset-entries 512
zset-max-ziplist-entries 128
zset-max-ziplist-value 64
hll-sparse-max-bytes 3000
stream-node-max-bytes 4096
stream-node-max-entries 100
activerehashing yes
client-output-buffer-limit normal 0 0 0
client-output-buffer-limit replica 256mb 64mb 60
client-output-buffer-limit pubsub 32mb 8mb 60
hz 10
dynamic-hz yes
aof-rewrite-incremental-fsync yes
rdb-save-incremental-fsync yes
"""

    config_path = Path("redis.conf")
    try:
        with open(config_path, "w") as f:
            f.write(config_content.strip())
        print(f"✅ Redis configuration file created: {config_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to create Redis config: {e}")
        return False


def test_redis_performance():
    """Test Redis performance and caching."""
    try:
        import json
        import time

        import redis

        r = redis.Redis(host="localhost", port=6379, decode_responses=True)

        print("🧪 Testing Redis performance...")

        # Test basic operations
        start_time = time.time()
        for i in range(1000):
            r.set(f"test_key_{i}", f"test_value_{i}")
        set_time = time.time() - start_time

        start_time = time.time()
        for i in range(1000):
            r.get(f"test_key_{i}")
        get_time = time.time() - start_time

        # Test JSON operations (for dashboard caching)
        test_data = {
            "students": [{"id": i, "name": f"Student {i}", "grade": 85 + (i % 15)} for i in range(100)],
            "timestamp": time.time(),
        }

        start_time = time.time()
        r.set("test_json", json.dumps(test_data))
        json_set_time = time.time() - start_time

        start_time = time.time()
        cached_data = json.loads(r.get("test_json"))
        json_get_time = time.time() - start_time

        # Clean up test data
        for i in range(1000):
            r.delete(f"test_key_{i}")
        r.delete("test_json")

        print("📊 Redis Performance Results:")
        print(f"   - 1000 SET operations: {set_time:.3f}s ({1000/set_time:.0f} ops/sec)")
        print(f"   - 1000 GET operations: {get_time:.3f}s ({1000/get_time:.0f} ops/sec)")
        print(f"   - JSON SET operation: {json_set_time:.3f}s")
        print(f"   - JSON GET operation: {json_get_time:.3f}s")
        print("✅ Redis performance test completed")

        return True

    except Exception as e:
        print(f"❌ Redis performance test failed: {e}")
        return False


def main():
    """Main function to set up Redis."""
    print("🔧 Redis Setup for Bangladesh Education Data Warehouse")
    print("=" * 60)

    # Check if Redis is installed
    if not check_redis_installed():
        print("\n📦 Installing Redis...")
        if not install_redis():
            print("\n❌ Redis installation failed. Please install manually.")
            sys.exit(1)

    # Start Redis server
    print("\n🚀 Starting Redis server...")
    if not start_redis_server():
        print("\n❌ Failed to start Redis server.")
        sys.exit(1)

    # Configure Redis
    print("\n⚙️ Configuring Redis...")
    if not configure_redis():
        print("\n⚠️ Redis configuration failed, but server is running.")

    # Create configuration file
    print("\n📝 Creating Redis configuration file...")
    create_redis_config()

    # Test performance
    print("\n🧪 Testing Redis performance...")
    test_redis_performance()

    print("\n✅ Redis setup completed successfully!")
    print("\n📋 Redis Information:")
    print("   - Server: localhost:6379")
    print("   - Status: Running")
    print("   - Configuration: redis.conf")
    print("   - Ready for dashboard caching")

    print("\n🎯 Next Steps:")
    print("   1. Launch Performance Dashboard: python scripts/launch_performance_dashboard.py")
    print("   2. Launch Demographics Dashboard: python scripts/launch_demographics_dashboard.py")
    print("   3. Both dashboards will use Redis for caching")


if __name__ == "__main__":
    main()
