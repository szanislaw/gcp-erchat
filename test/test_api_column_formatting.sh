#!/bin/bash
# Test column formatting with actual API calls

echo "Starting API server in background..."
cd /home/shawnyzy/Documents/GitHub/gcp-erchat
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/api_test.log 2>&1 &
API_PID=$!
echo "API PID: $API_PID"

sleep 5

echo ""
echo "===== TEST 1: TABLE Display (Show high severity incidents) ====="
curl -s -X POST http://localhost:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Show high severity incidents",
    "context": {
        "language": "en",
        "property_uuid": "",
        "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false}
  }' | python3 -c "import json, sys; d=json.load(sys.stdin); ex=d.get('execution',{}).get('data',{}); print('Columns:', ex.get('columns',[])); print('Row count:', ex.get('row_count',0))"

sleep 2

echo ""
echo "===== TEST 2: BAR Chart (Count by category) ====="
curl -s -X POST http://localhost:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Count by category",
    "context": {
        "language": "en",
        "property_uuid": "",
        "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false}
  }' | python3 -c "import json, sys; d=json.load(sys.stdin); ex=d.get('execution',{}).get('data',{}); print('Columns:', ex.get('columns',[])); print('Row count:', ex.get('row_count',0))"

echo ""
echo "Stopping API server..."
kill $API_PID 2>/dev/null

echo "Test complete!"
