#!/bin/bash
# Test script to verify all display types using actual column-based questions

API_URL="http://localhost:8000/nlq/execute"
ACCOUNT_UUID="fccb8d60-de9c-4bf8-abd8-fae523c732c6"

echo "===== TESTING COLUMN-BASED DISPLAY TYPES ====="
echo ""

# Test METRIC display (Single value KPIs)
echo "1. METRIC: What is the total incident count"
curl -s -X POST $API_URL -H "Content-Type: application/json" -d '{
  "text": "What is the total incident count",
  "context": {"language": "en", "property_uuid": "", "account_uuid": "'$ACCOUNT_UUID'"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false}
}' | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"Display Type: {d.get('display',{}).get('type')}\"); print(f\"Rows: {len(d.get('execution',{}).get('rows',[]))}\"); print()"

sleep 2

echo "2. METRIC: What is the total potential cost of all incidents"
curl -s -X POST $API_URL -H "Content-Type: application/json" -d '{
  "text": "What is the total potential cost of all incidents",
  "context": {"language": "en", "property_uuid": "", "account_uuid": "'$ACCOUNT_UUID'"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false}
}' | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"Display Type: {d.get('display',{}).get('type')}\"); print(f\"Rows: {len(d.get('execution',{}).get('rows',[]))}\"); print()"

sleep 2

# Test BAR chart (Category comparisons)
echo "3. BAR: Show incident count by category name"
curl -s -X POST $API_URL -H "Content-Type: application/json" -d '{
  "text": "Show incident count by category name",
  "context": {"language": "en", "property_uuid": "", "account_uuid": "'$ACCOUNT_UUID'"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false}
}' | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"Display Type: {d.get('display',{}).get('type')}\"); print(f\"Rows: {len(d.get('execution',{}).get('rows',[]))}\"); print()"

sleep 2

echo "4. BAR: Count incidents by department name"
curl -s -X POST $API_URL -H "Content-Type: application/json" -d '{
  "text": "Count incidents by department name",
  "context": {"language": "en", "property_uuid": "", "account_uuid": "'$ACCOUNT_UUID'"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false}
}' | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"Display Type: {d.get('display',{}).get('type')}\"); print(f\"Rows: {len(d.get('execution',{}).get('rows',[]))}\"); print()"

sleep 2

# Test PIE chart (Distribution)
echo "5. PIE: Show status name distribution"
curl -s -X POST $API_URL -H "Content-Type: application/json" -d '{
  "text": "Show status name distribution",
  "context": {"language": "en", "property_uuid": "", "account_uuid": "'$ACCOUNT_UUID'"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false}
}' | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"Display Type: {d.get('display',{}).get('type')}\"); print(f\"Rows: {len(d.get('execution',{}).get('rows',[]))}\"); print()"

sleep 2

echo "6. PIE: Display severity name breakdown"
curl -s -X POST $API_URL -H "Content-Type: application/json" -d '{
  "text": "Display severity name breakdown",
  "context": {"language": "en", "property_uuid": "", "account_uuid": "'$ACCOUNT_UUID'"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false}
}' | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"Display Type: {d.get('display',{}).get('type')}\"); print(f\"Rows: {len(d.get('execution',{}).get('rows',[]))}\"); print()"

sleep 2

# Test LINE chart (Time series)
echo "7. LINE: Show incident trend by created date"
curl -s -X POST $API_URL -H "Content-Type: application/json" -d '{
  "text": "Show incident trend by created date",
  "context": {"language": "en", "property_uuid": "", "account_uuid": "'$ACCOUNT_UUID'"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false}
}' | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"Display Type: {d.get('display',{}).get('type')}\"); print(f\"Rows: {len(d.get('execution',{}).get('rows',[]))}\"); print()"

sleep 2

echo "8. LINE: Display daily incident count from snapshotdate"
curl -s -X POST $API_URL -H "Content-Type: application/json" -d '{
  "text": "Display daily incident count from snapshotdate",
  "context": {"language": "en", "property_uuid": "", "account_uuid": "'$ACCOUNT_UUID'"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false}
}' | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"Display Type: {d.get('display',{}).get('type')}\"); print(f\"Rows: {len(d.get('execution',{}).get('rows',[]))}\"); print()"

sleep 2

# Test TABLE display (Detailed rows)
echo "9. TABLE: Show me all incidents with their category and severity"
curl -s -X POST $API_URL -H "Content-Type: application/json" -d '{
  "text": "Show me all incidents with their category and severity",
  "context": {"language": "en", "property_uuid": "", "account_uuid": "'$ACCOUNT_UUID'"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false}
}' | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"Display Type: {d.get('display',{}).get('type')}\"); print(f\"Rows: {len(d.get('execution',{}).get('rows',[]))}\"); print()"

sleep 2

echo "10. TABLE: List all incidents with department and status"
curl -s -X POST $API_URL -H "Content-Type: application/json" -d '{
  "text": "List all incidents with department and status",
  "context": {"language": "en", "property_uuid": "", "account_uuid": "'$ACCOUNT_UUID'"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false}
}' | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"Display Type: {d.get('display',{}).get('type')}\"); print(f\"Rows: {len(d.get('execution',{}).get('rows',[]))}\"); print()"

echo ""
echo "===== TEST COMPLETE ====="
echo "Expected results: metric (2), bar (2), pie (2), line (2), table (2)"
