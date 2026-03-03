#!/bin/bash
# stop.sh - Stop the NLQ to SQL API

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}   Stopping NLQ to SQL API${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${YELLOW}Stopping FastAPI backend...${NC}"
if [ -f "logs/api.pid" ]; then
    API_PID=$(cat logs/api.pid)
    if ps -p $API_PID > /dev/null 2>&1; then
        kill $API_PID 2>/dev/null
        sleep 2
        if ps -p $API_PID > /dev/null 2>&1; then
            kill -9 $API_PID 2>/dev/null
        fi
        echo -e "${GREEN}✓ FastAPI stopped (PID: $API_PID)${NC}"
    else
        echo -e "${YELLOW}   FastAPI not running (stale PID file)${NC}"
    fi
    rm logs/api.pid 2>/dev/null
else
    if pkill -f "uvicorn app.main:app" 2>/dev/null; then
        echo -e "${GREEN}✓ FastAPI stopped${NC}"
    else
        echo -e "${YELLOW}   FastAPI not running${NC}"
    fi
fi

# Final sweep
sleep 1
if pgrep -f "uvicorn app.main:app" > /dev/null; then
    echo -e "${RED}⚠ Force stopping remaining processes...${NC}"
    pkill -9 -f "uvicorn app.main:app" 2>/dev/null
fi

echo ""
echo -e "${GREEN}✓ Done${NC}"
echo ""
