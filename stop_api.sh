#!/bin/bash
# stop_api.sh - Stop the NLQ API server

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Stopping NLQ API Server...${NC}"

# Check if PID file exists
if [ -f "logs/api.pid" ]; then
    API_PID=$(cat logs/api.pid)
    if ps -p $API_PID > /dev/null 2>&1; then
        echo "Stopping server (PID: $API_PID)..."
        kill $API_PID
        sleep 2
        
        # Force kill if still running
        if ps -p $API_PID > /dev/null 2>&1; then
            echo "Force stopping..."
            kill -9 $API_PID
        fi
        
        rm logs/api.pid
        echo -e "${GREEN}✓ Server stopped${NC}"
    else
        echo -e "${YELLOW}Server not running (PID file exists but process not found)${NC}"
        rm logs/api.pid
    fi
else
    # Try to find and kill by process name
    if pgrep -f "uvicorn app.main:app" > /dev/null; then
        echo "Found server process, stopping..."
        pkill -f "uvicorn app.main:app"
        sleep 2
        
        # Force kill if still running
        if pgrep -f "uvicorn app.main:app" > /dev/null; then
            pkill -9 -f "uvicorn app.main:app"
        fi
        echo -e "${GREEN}✓ Server stopped${NC}"
    else
        echo -e "${YELLOW}Server is not running${NC}"
    fi
fi

# Also stop Streamlit if running
if pgrep -f "streamlit run" > /dev/null; then
    echo "Stopping Streamlit UI..."
    pkill -f "streamlit run"
    echo -e "${GREEN}✓ Streamlit stopped${NC}"
fi

echo -e "${GREEN}All services stopped${NC}"
