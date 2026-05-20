#!/bin/bash
# start.sh - Start the NLQ to SQL API

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}   NLQ to SQL API Startup${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 1. Check .env
echo -e "${YELLOW}[1/4] Checking environment configuration...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${RED}✗ .env file not found${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${YELLOW}⚠ Created .env from .env.example — configure AWS credentials then re-run${NC}"
    else
        echo -e "${RED}✗ .env.example not found${NC}"
    fi
    exit 1
fi
echo -e "${GREEN}✓ Environment file found${NC}"
echo ""

# 2. Authentication note
echo -e "${YELLOW}[2/4] Authentication check...${NC}"
echo -e "${GREEN}✓ Authentication handled by external token service${NC}"
echo ""

# 3. Check Python dependencies
echo -e "${YELLOW}[3/4] Checking Python dependencies...${NC}"
if ! python -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}⚠ Dependencies not installed. Installing...${NC}"
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo -e "${RED}✗ Failed to install dependencies${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# 4. Start FastAPI
echo -e "${YELLOW}[4/4] Starting FastAPI backend...${NC}"

# Stop any existing process recorded by the previous startup.
if [ -f "logs/api.pid" ]; then
    OLD_PID=$(cat logs/api.pid)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo -e "${YELLOW}⚠ Stopping existing FastAPI process (PID: $OLD_PID)...${NC}"
        kill "$OLD_PID" 2>/dev/null
        sleep 2
        if kill -0 "$OLD_PID" 2>/dev/null; then
            kill -9 "$OLD_PID" 2>/dev/null
            sleep 1
        fi
    fi
    rm -f logs/api.pid
fi

mkdir -p logs
export PYTORCH_ALLOC_CONF=expandable_segments:True
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > logs/api.log 2>&1 &
FASTAPI_PID=$!
echo $FASTAPI_PID > logs/api.pid

sleep 3
if kill -0 "$FASTAPI_PID" 2>/dev/null; then
    echo -e "${GREEN}✓ FastAPI started (PID: $FASTAPI_PID)${NC}"
else
    echo -e "${RED}✗ FastAPI failed to start — check logs/api.log${NC}"
    exit 1
fi
echo ""

echo -e "${BLUE}============================================${NC}"
echo -e "${GREEN}✓ API started successfully!${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo "Services:"
echo "   • FastAPI: http://localhost:8000"
echo "   • Docs:    http://localhost:8000/docs"
echo ""
echo "Management:"
echo "   • Stop:    ./stop.sh"
echo "   • Logs:    tail -f logs/api.log"
echo "   • Health:  curl http://localhost:8000/health"
echo ""
