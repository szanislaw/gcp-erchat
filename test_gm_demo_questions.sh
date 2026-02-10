#!/bin/bash
# Quick Test Script for GM Demo Questions
# Run all 20 questions against localhost:8000

API_URL="http://localhost:8000/nlq/execute"
PROPERTY_UUID="c0abc579-6ef4-47a3-8290-16cf26964aec"
ACCOUNT_UUID="fccb8d60-de9c-4bf8-abd8-fae523c732c6"

echo "================================="
echo "GM Demo Questions - Quick Test"
echo "================================="
echo ""

test_query() {
    local num=$1
    local question=$2
    echo -n "Q$num: Testing '$question'... "
    
    result=$(curl -s -X POST "$API_URL" \
        -H "Content-Type: application/json" \
        -d "{
            \"text\": \"$question\",
            \"context\": {
                \"language\": \"en\",
                \"property_uuid\": \"$PROPERTY_UUID\",
                \"account_uuid\": \"$ACCOUNT_UUID\"
            },
            \"sql\": {\"dialect\": \"athena\"},
            \"execution\": {\"dry_run\": false, \"max_rows\": 100},
            \"model\": {\"max_tokens\": 512},
            \"display\": {\"type\": \"table\"},
            \"trace\": {\"source\": \"gm-demo\"}
        }")
    
    if echo "$result" | grep -q '"success": true'; then
        row_count=$(echo "$result" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('execution', {}).get('row_count', 0))" 2>/dev/null)
        echo "✅ SUCCESS ($row_count rows)"
    else
        echo "❌ FAILED"
    fi
}

# OPERATIONAL OVERVIEW
echo "📊 OPERATIONAL OVERVIEW"
test_query 1 "Show me all incidents"
test_query 2 "Show me all pending incidents"
test_query 3 "Show me all Service Quality incidents"
test_query 4 "Show incidents from last 7 days"
test_query 5 "Show recent incidents with medium severity"
echo ""

# GUEST EXPERIENCE
echo "🏨 GUEST EXPERIENCE"
test_query 6 "Show me incidents for Food and Beverage category"
test_query 7 "Show me incidents for Food and Beverage category"
test_query 8 "Show high severity incidents that are still pending"
test_query 9 "Show high severity incidents that are still pending"
echo ""

# FINANCIAL IMPACT
echo "💰 FINANCIAL IMPACT"
test_query 10 "Show me incidents with actual cost greater than 100"
test_query 11 "Show me all incidents sorted by actual cost"
test_query 12 "Show me completed incidents"
echo ""

# PERFORMANCE ANALYTICS
echo "📈 PERFORMANCE ANALYTICS"
test_query 13 "Show me incidents ordered by severity"
test_query 14 "Show incidents from last 7 days"
test_query 15 "Show me incidents for Food and Beverage category"
test_query 16 "Show recent incidents with medium severity"
echo ""

# STRATEGIC INSIGHTS
echo "🎯 STRATEGIC INSIGHTS"
test_query 17 "Show me completed incidents"
test_query 18 "Show me all pending incidents"
test_query 19 "Show me incidents ordered by severity"
test_query 20 "Show me all incidents sorted by actual cost"
echo ""

echo "================================="
echo "Test Complete!"
echo "================================="
