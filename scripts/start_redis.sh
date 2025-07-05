#!/bin/bash

# Start Redis server script for Bangladesh Education Data Warehouse

echo "🔧 Starting Redis server for Bangladesh Education Data Warehouse"
echo "================================================================"

# Function to check if Redis is running
check_redis() {
    if redis-cli ping > /dev/null 2>&1; then
        echo "✅ Redis is already running"
        return 0
    else
        return 1
    fi
}

# Function to start Redis server
start_redis() {
    echo "🚀 Starting Redis server..."

    # Check if Redis is installed
    if ! command -v redis-server &> /dev/null; then
        echo "❌ Redis is not installed"
        echo "Please install Redis first:"
        echo "  Ubuntu/Debian: sudo apt install redis-server"
        echo "  macOS: brew install redis"
        echo "  Or use Docker: docker run -d -p 6379:6379 redis:alpine"
        exit 1
    fi

    # Start Redis server
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        redis-server --daemonize yes
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        redis-server --daemonize yes
    else
        # Other systems
        redis-server &
    fi

    # Wait for Redis to start
    sleep 2

    # Check if Redis started successfully
    if check_redis; then
        echo "✅ Redis server started successfully"
        echo "📊 Redis is running on localhost:6379"
        return 0
    else
        echo "❌ Failed to start Redis server"
        return 1
    fi
}

# Function to configure Redis
configure_redis() {
    echo "⚙️ Configuring Redis for optimal performance..."

    # Set memory policy
    redis-cli config set maxmemory-policy allkeys-lru

    # Set save policy
    redis-cli config set save "900 1 300 10 60 10000"

    # Set timeout
    redis-cli config set timeout 0

    echo "✅ Redis configured successfully"
}

# Function to test Redis
test_redis() {
    echo "🧪 Testing Redis functionality..."

    # Test basic operations
    redis-cli set test_key "test_value" > /dev/null
    result=$(redis-cli get test_key)

    if [ "$result" = "test_value" ]; then
        echo "✅ Redis basic operations working"
        redis-cli del test_key > /dev/null
    else
        echo "❌ Redis basic operations failed"
        return 1
    fi

    # Test JSON operations (for dashboard caching)
    redis-cli set test_json '{"name":"test","value":123}' > /dev/null
    json_result=$(redis-cli get test_json)

    if [[ "$json_result" == *"test"* ]]; then
        echo "✅ Redis JSON operations working"
        redis-cli del test_json > /dev/null
    else
        echo "❌ Redis JSON operations failed"
        return 1
    fi

    echo "✅ All Redis tests passed"
}

# Main execution
main() {
    # Check if Redis is already running
    if check_redis; then
        echo "Redis is already running. Checking configuration..."
        configure_redis
        test_redis
        echo ""
        echo "📋 Redis Status:"
        echo "   - Server: localhost:6379"
        echo "   - Status: Running"
        echo "   - Ready for dashboard caching"
        exit 0
    fi

    # Start Redis
    if start_redis; then
        configure_redis
        test_redis

        echo ""
        echo "🎯 Redis Setup Complete!"
        echo "📋 Redis Information:"
        echo "   - Server: localhost:6379"
        echo "   - Status: Running"
        echo "   - Memory Policy: allkeys-lru"
        echo "   - Save Policy: 900 1 300 10 60 10000"
        echo "   - Ready for dashboard caching"
        echo ""
        echo "🚀 You can now launch the dashboards:"
        echo "   python scripts/launch_performance_dashboard.py"
        echo "   python scripts/launch_demographics_dashboard.py"
    else
        echo "❌ Failed to start Redis. Please check the installation."
        exit 1
    fi
}

# Run main function
main
