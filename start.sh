#!/bin/bash
# start.sh - Start the complete NLQ to SQL application
# This starts both the FastAPI backend and Streamlit UI

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}   NLQ to SQL Application Startup${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 1. Check if .env file exists
echo -e "${YELLOW}[1/6] Checking environment configuration...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${RED}✗ .env file not found${NC}"
    echo "   Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${YELLOW}⚠ Created .env file - please configure it with your AWS credentials${NC}"
        echo -e "${YELLOW}⚠ Edit .env and then run this script again${NC}"
        exit 1
    else
        echo -e "${RED}✗ .env.example not found${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✓ Environment file found${NC}"
echo ""

# 2. Verify credentials
echo -e "${YELLOW}[2/6] Verifying AWS credentials...${NC}"
if [ -f "verify_credentials.py" ]; then
    python verify_credentials.py --quiet 2>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ AWS credentials verified${NC}"
    else
        echo -e "${YELLOW}⚠ Running full credential verification:${NC}"
        echo ""
        python verify_credentials.py
        echo ""
        read -p "Credentials may have issues. Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Aborted."
            exit 1
        fi
    fi
else
    echo -e "${YELLOW}⚠ Credential verification script not found (skipping)${NC}"
fi
echo ""

# 3. Check Python dependencies
echo -e "${YELLOW}[3/6] Checking Python dependencies...${NC}"
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

# 4. Stop any existing processes
echo -e "${YELLOW}[4/6] Stopping existing processes...${NC}"
pkill -f "uvicorn app.main:app" 2>/dev/null
pkill -f "streamlit run" 2>/dev/null
sleep 2

# Force kill if still running
if pgrep -f "uvicorn app.main:app" > /dev/null; then
    echo "   Force stopping FastAPI..."
    pkill -9 -f "uvicorn app.main:app" 2>/dev/null
fi
if pgrep -f "streamlit run" > /dev/null; then
    echo "   Force stopping Streamlit..."
    pkill -9 -f "streamlit run" 2>/dev/null
fi
sleep 1
echo -e "${GREEN}✓ Old processes stopped${NC}"
echo ""

# 5. Start FastAPI Backend
echo -e "${YELLOW}[5/6] Starting FastAPI backend...${NC}"

# Create logs directory if it doesn't exist
mkdir -p logs

# Start FastAPI in background
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > logs/api.log 2>&1 &
FASTAPI_PID=$!
echo $FASTAPI_PID > logs/api.pid

# Wait and verify it started
sleep 3
if ps -p $FASTAPI_PID > /dev/null; then
    echo -e "${GREEN}✓ FastAPI started (PID: $FASTAPI_PID)${NC}"
    echo "   URL: http://localhost:8000"
    echo "   Logs: tail -f logs/api.log"
else
    echo -e "${RED}✗ FastAPI failed to start${NC}"
    echo "   Check logs: cat logs/api.log"
    exit 1
fi
echo ""

# 6. Start Streamlit UI
echo -e "${YELLOW}[6/6] Starting Streamlit UI...${NC}"

# Start Streamlit in background
nohup streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0 > logs/streamlit.log 2>&1 &
STREAMLIT_PID=$!
echo $STREAMLIT_PID > logs/streamlit.pid

# Wait and verify it started
sleep 3
if ps -p $STREAMLIT_PID > /dev/null; then
    echo -e "${GREEN}✓ Streamlit started (PID: $STREAMLIT_PID)${NC}"
    echo "   URL: http://localhost:8501"
    echo "   Logs: tail -f logs/streamlit.log"
else
    echo -e "${RED}✗ Streamlit failed to start${NC}"
    echo "   Check logs: cat logs/streamlit.log"
    # Don't exit, API is still running
fi
echo ""

# Summary
echo -e "${BLUE}============================================${NC}"
echo -e "${GREEN}✓ Application started successfully!${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo "📡 Services:"
echo "   • FastAPI Backend: http://localhost:8000"
echo "   • Streamlit UI:    http://localhost:8501"
echo ""
echo "📋 Management:"
echo "   • Stop all:   ./stop.sh"
echo "   • View logs:  tail -f logs/*.log"
echo "   • API status: curl http://localhost:8000/nlq/health"
echo ""
echo "🔐 Process IDs:"
echo "   • FastAPI:   $FASTAPI_PID (logs/api.pid)"
echo "   • Streamlit: $STREAMLIT_PID (logs/streamlit.pid)"
echo ""
