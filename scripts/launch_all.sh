#!/bin/bash

# Launch all dashboards script for Bangladesh Education Data Warehouse

echo "🎓 Bangladesh Education Data Warehouse - Dashboard Launcher"
echo "============================================================"

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to check dependencies
check_dependencies() {
    echo "🔍 Checking dependencies..."

    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python 3 is not installed"
        return 1
    fi

    # Check required Python packages
    local packages=("dash" "streamlit" "plotly" "pandas" "sqlalchemy" "redis")
    local missing_packages=()

    for package in "${packages[@]}"; do
        if ! python3 -c "import ${package//-/_}" &> /dev/null; then
            missing_packages+=("$package")
        fi
    done

    if [ ${#missing_packages[@]} -ne 0 ]; then
        echo "❌ Missing Python packages: ${missing_packages[*]}"
        echo "Install with: pip install ${missing_packages[*]}"
        return 1
    fi

    echo "✅ All dependencies are installed"
    return 0
}

# Function to check database connection
check_database() {
    echo "🗄️ Checking database connection..."

    if python3 -c "
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/student_data_db')

try:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1'))
        result.fetchone()
    print('✅ Database connection successful')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    exit(1)
"; then
        return 0
    else
        return 1
    fi
}

# Function to start Redis
start_redis() {
    echo "🔧 Starting Redis..."

    # Check if Redis is already running
    if redis-cli ping > /dev/null 2>&1; then
        echo "✅ Redis is already running"
        return 0
    fi

    # Start Redis
    if command -v redis-server &> /dev/null; then
        redis-server --daemonize yes
        sleep 2

        if redis-cli ping > /dev/null 2>&1; then
            echo "✅ Redis started successfully"
            return 0
        else
            echo "❌ Failed to start Redis"
            return 1
        fi
    else
        echo "⚠️ Redis not installed, dashboards will work without caching"
        return 0
    fi
}

# Function to launch Performance Dashboard
launch_performance_dashboard() {
    echo "🚀 Launching Student Performance Dashboard..."

    if check_port 8050; then
        echo "⚠️ Port 8050 is already in use"
        return 1
    fi

    cd "$(dirname "$0")/../dashboards/student_performance"
    python3 app.py &
    local pid=$!

    # Wait a moment and check if it's running
    sleep 3
    if kill -0 $pid 2>/dev/null; then
        echo "✅ Performance Dashboard started on http://localhost:8050 (PID: $pid)"
        echo $pid > /tmp/performance_dashboard.pid
        return 0
    else
        echo "❌ Failed to start Performance Dashboard"
        return 1
    fi
}

# Function to launch Demographics Dashboard
launch_demographics_dashboard() {
    echo "🚀 Launching Demographic Insights Dashboard..."

    if check_port 8501; then
        echo "⚠️ Port 8501 is already in use"
        return 1
    fi

    cd "$(dirname "$0")/../dashboards/demographic_insights"
    streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --browser.gatherUsageStats false --server.headless true &
    local pid=$!

    # Wait a moment and check if it's running
    sleep 5
    if kill -0 $pid 2>/dev/null; then
        echo "✅ Demographics Dashboard started on http://localhost:8501 (PID: $pid)"
        echo $pid > /tmp/demographics_dashboard.pid
        return 0
    else
        echo "❌ Failed to start Demographics Dashboard"
        return 1
    fi
}

# Function to monitor dashboards
monitor_dashboards() {
    echo ""
    echo "📊 Dashboard Status Monitor"
    echo "=========================="
    echo "🎯 Student Performance Dashboard: http://localhost:8050"
    echo "👥 Demographic Insights Dashboard: http://localhost:8501"
    echo ""
    echo "⏹️ Press Ctrl+C to stop all dashboards"
    echo "📊 Monitoring dashboard health..."

    while true; do
        sleep 30

        # Check Performance Dashboard
        if [ -f /tmp/performance_dashboard.pid ]; then
            local perf_pid=$(cat /tmp/performance_dashboard.pid)
            if ! kill -0 $perf_pid 2>/dev/null; then
                echo "⚠️ Performance Dashboard stopped unexpectedly"
                rm -f /tmp/performance_dashboard.pid
            fi
        fi

        # Check Demographics Dashboard
        if [ -f /tmp/demographics_dashboard.pid ]; then
            local demo_pid=$(cat /tmp/demographics_dashboard.pid)
            if ! kill -0 $demo_pid 2>/dev/null; then
                echo "⚠️ Demographics Dashboard stopped unexpectedly"
                rm -f /tmp/demographics_dashboard.pid
            fi
        fi
    done
}

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down all dashboards..."

    # Stop Performance Dashboard
    if [ -f /tmp/performance_dashboard.pid ]; then
        local perf_pid=$(cat /tmp/performance_dashboard.pid)
        if kill -0 $perf_pid 2>/dev/null; then
            echo "   Stopping Performance Dashboard (PID: $perf_pid)..."
            kill $perf_pid
            wait $perf_pid 2>/dev/null
        fi
        rm -f /tmp/performance_dashboard.pid
    fi

    # Stop Demographics Dashboard
    if [ -f /tmp/demographics_dashboard.pid ]; then
        local demo_pid=$(cat /tmp/demographics_dashboard.pid)
        if kill -0 $demo_pid 2>/dev/null; then
            echo "   Stopping Demographics Dashboard (PID: $demo_pid)..."
            kill $demo_pid
            wait $demo_pid 2>/dev/null
        fi
        rm -f /tmp/demographics_dashboard.pid
    fi

    # Kill any remaining processes on the ports
    if check_port 8050; then
        echo "   Cleaning up port 8050..."
        lsof -ti:8050 | xargs kill -9 2>/dev/null || true
    fi

    if check_port 8501; then
        echo "   Cleaning up port 8501..."
        lsof -ti:8501 | xargs kill -9 2>/dev/null || true
    fi

    echo "✅ All dashboards stopped"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Main execution
main() {
    # Check dependencies
    if ! check_dependencies; then
        exit 1
    fi

    # Check database
    if ! check_database; then
        exit 1
    fi

    # Start Redis
    start_redis

    echo ""
    echo "🚀 Launching dashboards..."

    # Launch dashboards
    local success=true

    if ! launch_performance_dashboard; then
        success=false
    fi

    sleep 2

    if ! launch_demographics_dashboard; then
        success=false
    fi

    if [ "$success" = true ]; then
        echo ""
        echo "🎉 All dashboards launched successfully!"
        monitor_dashboards
    else
        echo ""
        echo "❌ Some dashboards failed to start"
        cleanup
        exit 1
    fi
}

# Run main function
main
