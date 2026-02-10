#!/bin/bash
# Test backend hardcoded display types for all 10 unique GM demo questions

echo "Testing Backend Hardcoded Display Types"
echo "========================================"
echo ""

BASE_URL="http://localhost:8000/nlq/execute"
CONTEXT='{
  "text": "QUESTION_PLACEHOLDER",
  "context": {
    "language": "en",
    "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec",
    "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"
  },
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 10},
  "model": {"max_tokens": 512},
  "trace": {"source": "gm-demo-test"}
}'

test_question() {
    local num="$1"
    local question="$2"
    local expected="$3"
    
    echo -n "Q${num}: \"${question}\" ... "
    
    payload=$(echo "$CONTEXT" | sed "s/QUESTION_PLACEHOLDER/$question/")
    result=$(curl -s -X POST "$BASE_URL" -H "Content-Type: application/json" -d "$payload" 2>/dev/null)
    
    display_type=$(echo "$result" | python3 -c "import json, sys; d=json.load(sys.stdin); print(d.get('display', {}).get('type', 'N/A'))" 2>/dev/null)
    
    if [ "$display_type" == "$expected" ]; then
        echo "✅ $display_type (expected: $expected)"
    else
        echo "❌ $display_type (expected: $expected)"
    fi
    
    sleep 1
}

# Test all 10 unique questions
echo "=== Testing 10 Unique GM Demo Questions ==="
echo ""

test_question "1" "Show me all incidents" "table"
test_question "2" "Show me all pending incidents" "table"
test_question "3" "Show me all Service Quality incidents" "bar"
test_question "4" "Show incidents from last 7 days" "line"
test_question "5" "Show recent incidents with medium severity" "pie"
test_question "6" "Show me incidents for Food and Beverage category" "bar"
test_question "7" "Show high severity incidents that are still pending" "table"
test_question "8" "Show me incidents with actual cost greater than 100" "bar"
test_question "9" "Show me all incidents sorted by actual cost" "table"
test_question "10" "Show me completed incidents" "pie"
test_question "11" "Show me incidents ordered by severity" "bar"

echo ""
echo "========================================"
echo "Test Complete!"
