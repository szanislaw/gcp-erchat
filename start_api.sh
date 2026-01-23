#!/bin/bash
# start_api.sh - Start the NLQ API server with proper configuration

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Starting NLQ → Athena API Server${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  Warning: .env file not found${NC}"
    echo "Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}✓ Created .env file - please configure it${NC}"
        echo -e "${RED}Please edit .env with your AWS credentials before starting${NC}"
        exit 1
    else
        echo -e "${RED}❌ .env.example not found${NC}"
        exit 1
    fi
fi

# Check if Python dependencies are installed
echo "Checking dependencies..."
python3 -c "import fastapi" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Dependencies not installed${NC}"
    echo "Installing from requirements.txt..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to install dependencies${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Dependencies installed${NC}"
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Check if server is already running
if pgrep -f "uvicorn app.main:app" > /dev/null; then
    echo -e "${YELLOW}⚠️  Server is already running${NC}"
    echo "PID: $(pgrep -f 'uvicorn app.main:app')"
    echo ""
    echo "Options:"
    echo "  1. Stop and restart: ./restart_servers.sh"
    echo "  2. View logs: tail -f logs/api.log"
    echo "  3. Check status: ps aux | grep uvicorn"
    exit 0
fi

# Start the server
echo -e "${GREEN}Starting API server on port 8080...${NC}"

# Option 1: Run in background with nohup
nohup uvicorn app.main:app --host 0.0.0.0 --port 8080 \
    > logs/api.log 2>&1 &

API_PID=$!

# Wait a moment for server to start
sleep 3

# Check if server started successfully
if ps -p $API_PID > /dev/null; then
    echo -e "${GREEN}✓ API server started successfully${NC}"
    echo "  PID: $API_PID"
    echo "  Port: 8080"
    echo "  Logs: logs/api.log"
    echo ""
    echo "Test the server:"
    echo "  curl http://localhost:8080/health"
    echo ""
    echo "View logs:"
    echo "  tail -f logs/api.log"
    echo ""
    echo "Stop the server:"
    echo "  kill $API_PID"
    echo "  or: pkill -f 'uvicorn app.main:app'"
    
    # Save PID for later management
    echo $API_PID > logs/api.pid
    
    # Test health endpoint
    sleep 2
    echo ""
    echo "Testing health endpoint..."
    curl -s http://localhost:8080/health | python3 -m json.tool 2>/dev/null || echo "Server starting..."
    
else
    echo -e "${RED}❌ Failed to start server${NC}"
    echo "Check logs/api.log for errors"
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Server is running!${NC}"
echo -e "${GREEN}========================================${NC}"
