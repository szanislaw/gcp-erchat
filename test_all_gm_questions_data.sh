#!/bin/bash
# Test all 11 unique GM demo questions for data + logical display types

BASE_URL="http://localhost:8000/nlq/execute"
CONTEXT_TEMPLATE='{
  "text": "QUESTION_PLACEHOLDER",
  "context": {
    "language": "en",
    "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec",
    "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"
  },
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "trace": {"source": "gm-data-test"}
}'

test_question() {
    local num="$1"
    local question="$2"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Q${num}: ${question}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    payload=$(echo "$CONTEXT_TEMPLATE" | sed "s/QUESTION_PLACEHOLDER/$question/")
    result=$(curl -s -X POST "$BASE_URL" -H "Content-Type: application/json" -d "$payload" 2>/dev/null)
    
    # Extract key info
    row_count=$(echo "$result" | python3 -c "import json, sys; d=json.load(sys.stdin); print(len(d.get('execution', {}).get('rows', [])))" 2>/dev/null)
    col_count=$(echo "$result" | python3 -c "import json, sys; d=json.load(sys.stdin); print(len(d.get('execution', {}).get('columns', [])))" 2>/dev/null)
    display_type=$(echo "$result" | python3 -c "import json, sys; d=json.load(sys.stdin); print(d.get('display', {}).get('type', 'N/A'))" 2>/dev/null)
    sql=$(echo "$result" | python3 -c "import json, sys; d=json.load(sys.stdin); print(d.get('sql', 'N/A'))" 2>/dev/null)
    
    echo "📊 Data: ${row_count} rows × ${col_count} cols"
    echo "🎨 Display Type: ${display_type}"
    echo "🔍 SQL: ${sql}"
    
    if [ "$row_count" == "0" ] || [ "$row_count" == "" ]; then
        echo "⚠️  WARNING: NO DATA RETURNED!"
    fi
    
    echo ""
    sleep 2
}

echo "=========================================="
echo "Testing All GM Demo Questions for Data"
echo "=========================================="
echo ""

test_question "1" "Show me all incidents"
test_question "2" "Show me all pending incidents"
test_question "3" "Show me all Service Quality incidents"
test_question "4" "Show incidents from last 7 days"
test_question "5" "Show recent incidents with medium severity"
test_question "6" "Show me incidents for Food and Beverage category"
test_question "7" "Show high severity incidents that are still pending"
test_question "8" "Show me incidents with actual cost greater than 100"
test_question "9" "Show me all incidents sorted by actual cost"
test_question "10" "Show me completed incidents"
test_question "11" "Show me incidents ordered by severity"

echo "=========================================="
echo "Test Complete!"
echo "=========================================="
