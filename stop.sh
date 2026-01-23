#!/bin/bash
# stop.sh - Stop the complete NLQ to SQL application
# This stops both the FastAPI backend and Streamlit UI

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}   Stopping NLQ to SQL Application${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

STOPPED=0

# Stop FastAPI
echo -e "${YELLOW}Stopping FastAPI backend...${NC}"
if [ -f "logs/api.pid" ]; then
    API_PID=$(cat logs/api.pid)
    if ps -p $API_PID > /dev/null 2>&1; then
        kill $API_PID 2>/dev/null
        sleep 2
        
        # Force kill if still running
        if ps -p $API_PID > /dev/null 2>&1; then
            echo "   Force stopping..."
            kill -9 $API_PID 2>/dev/null
        fi
        echo -e "${GREEN}✓ FastAPI stopped (PID: $API_PID)${NC}"
        STOPPED=1
    else
        echo -e "${YELLOW}   FastAPI not running (stale PID file)${NC}"
    fi
    rm logs/api.pid 2>/dev/null
else
    # Try to kill by process name
    if pkill -f "uvicorn app.main:app" 2>/dev/null; then
        echo -e "${GREEN}✓ FastAPI stopped${NC}"
        STOPPED=1
    else
        echo -e "${YELLOW}   FastAPI not running${NC}"
    fi
fi

# Stop Streamlit
echo -e "${YELLOW}Stopping Streamlit UI...${NC}"
if [ -f "logs/streamlit.pid" ]; then
    STREAMLIT_PID=$(cat logs/streamlit.pid)
    if ps -p $STREAMLIT_PID > /dev/null 2>&1; then
        kill $STREAMLIT_PID 2>/dev/null
        sleep 2
        
        # Force kill if still running
        if ps -p $STREAMLIT_PID > /dev/null 2>&1; then
            echo "   Force stopping..."
            kill -9 $STREAMLIT_PID 2>/dev/null
        fi
        echo -e "${GREEN}✓ Streamlit stopped (PID: $STREAMLIT_PID)${NC}"
        STOPPED=1
    else
        echo -e "${YELLOW}   Streamlit not running (stale PID file)${NC}"
    fi
    rm logs/streamlit.pid 2>/dev/null
else
    # Try to kill by process name
    if pkill -f "streamlit run" 2>/dev/null; then
        echo -e "${GREEN}✓ Streamlit stopped${NC}"
        STOPPED=1
    else
        echo -e "${YELLOW}   Streamlit not running${NC}"
    fi
fi

echo ""

# Final verification
sleep 1
if pgrep -f "uvicorn app.main:app" > /dev/null || pgrep -f "streamlit run" > /dev/null; then
    echo -e "${RED}⚠ Some processes still running, forcing termination...${NC}"
    pkill -9 -f "uvicorn app.main:app" 2>/dev/null
    pkill -9 -f "streamlit run" 2>/dev/null
    sleep 1
fi

if [ $STOPPED -eq 1 ]; then
    echo -e "${GREEN}✓ All services stopped successfully${NC}"
else
    echo -e "${YELLOW}No services were running${NC}"
fi
echo ""
