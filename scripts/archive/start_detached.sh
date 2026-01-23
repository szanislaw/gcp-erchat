#!/bin/bash
# Start the API in a detached screen session

# Kill any existing screen session named "nlq-api"
screen -S nlq-api -X quit 2>/dev/null

# Kill any existing uvicorn processes
pkill -f uvicorn

# Wait a moment for processes to terminate
sleep 2

# Start new screen session with the API
screen -dmS nlq-api bash -c "cd /home/shawnyzy/sqlcoder-src && conda activate venv1 && uvicorn app.main:app --host 0.0.0.0 --port 8080"

echo "✓ API started in detached screen session 'nlq-api'"
echo ""
echo "Useful commands:"
echo "  screen -r nlq-api     # Reattach to view logs"
echo "  screen -ls            # List all screen sessions"
echo "  Ctrl+A, then D        # Detach from screen (while attached)"
echo "  screen -S nlq-api -X quit  # Stop the session"
