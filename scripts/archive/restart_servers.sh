#!/bin/bash
# Restart both FastAPI backend and Streamlit UI servers

echo "🔄 Restarting NLQ servers..."
echo ""

# Stop existing processes
echo "1. Stopping existing processes..."
pkill -f "uvicorn app.main:app" 2>/dev/null
pkill -f "streamlit run" 2>/dev/null
sleep 2

# Verify processes are stopped
if pgrep -f "uvicorn app.main:app" > /dev/null || pgrep -f "streamlit run" > /dev/null; then
    echo "   ⚠️  Some processes still running, forcing kill..."
    pkill -9 -f "uvicorn app.main:app" 2>/dev/null
    pkill -9 -f "streamlit run" 2>/dev/null
    sleep 1
fi

echo "   ✅ Old processes stopped"
echo ""

# Start FastAPI backend
echo "2. Starting FastAPI backend..."
cd /home/shawnyzy/Documents/GitHub/gcp-erchat
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload > /dev/null 2>&1 &
FASTAPI_PID=$!
sleep 3

# Check if FastAPI is running
if curl -s http://localhost:8080/ > /dev/null 2>&1; then
    echo "   ✅ FastAPI running on http://localhost:8080 (PID: $FASTAPI_PID)"
else
    echo "   ❌ Failed to start FastAPI"
    exit 1
fi
echo ""

# Start Streamlit UI
echo "3. Starting Streamlit UI..."
streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0 > /dev/null 2>&1 &
STREAMLIT_PID=$!
sleep 3

# Check if Streamlit is running
if curl -s http://localhost:8501/ > /dev/null 2>&1; then
    echo "   ✅ Streamlit running on http://localhost:8501 (PID: $STREAMLIT_PID)"
else
    echo "   ⚠️  Streamlit may still be starting..."
fi
echo ""

echo "🎉 Server restart complete!"
echo ""
echo "📡 Services:"
echo "   FastAPI Backend: http://localhost:8080"
echo "   Streamlit UI:    http://localhost:8501"
echo ""
echo "💡 To stop servers: pkill -f 'uvicorn app.main:app' && pkill -f 'streamlit run'"
