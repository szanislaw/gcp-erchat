#!/bin/bash
# Start the API in background with nohup

# Kill any existing uvicorn processes
pkill -f uvicorn

# Wait for processes to terminate
sleep 2

cd /home/shawnyzy/sqlcoder-src

# Start with nohup (assumes conda env is already activated)
nohup uvicorn app.main:app --host 0.0.0.0 --port 8080 > logs/uvicorn.log 2>&1 &

echo "✓ API started in background (PID: $!)"
echo "✓ Logs: tail -f logs/uvicorn.log"
echo ""
echo "To stop: pkill -f uvicorn"
