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
    if [ -n "$API_PID" ] && kill -0 "$API_PID" 2>/dev/null; then
        kill "$API_PID" 2>/dev/null
        sleep 2
        if kill -0 "$API_PID" 2>/dev/null; then
            kill -9 "$API_PID" 2>/dev/null
        fi
        echo -e "${GREEN}✓ FastAPI stopped (PID: $API_PID)${NC}"
    else
        echo -e "${YELLOW}   FastAPI not running (stale PID file)${NC}"
    fi
    rm logs/api.pid 2>/dev/null
else
    echo -e "${YELLOW}   FastAPI not running${NC}"
fi

sleep 1
echo ""
echo -e "${GREEN}✓ Done${NC}"
echo ""
