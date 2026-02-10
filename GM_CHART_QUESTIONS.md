# GM Demo Questions - Chart Visualizations

## ⚠️ Property UUID Configuration

**These questions use property UUIDs that have actual data:**
```
Property UUIDs: c7254cc9-9145-4602-b44b-0c1cff335f83,2b618b46-6b80-481b-b1e3-5aec1647b926
Account UUID: fccb8d60-de9c-4bf8-abd8-fae523c732c6
```

---

## 📊 Chart-Based Questions

These questions use **aggregation queries** (COUNT, SUM, AVG with GROUP BY) which properly display as charts.

---

### 📈 METRIC DISPLAYS (KPI Cards)

Single numeric values - great for dashboards

#### Q1: Total Incident Count
**Question:** "How many incidents are there"
- **Display Type:** metric
- **Expected SQL:** `SELECT COUNT(*) FROM incident_combine WHERE property IN (...)`
- **Use Case:** Overall incident volume KPI

**Test:**
```bash
curl -X POST http://localhost:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "How many incidents are there",
    "context": {
      "language": "en",
      "property_uuid": "c7254cc9-9145-4602-b44b-0c1cff335f83,2b618b46-6b80-481b-b1e3-5aec1647b926",
      "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false, "max_rows": 100},
    "model": {"max_tokens": 512},
    "trace": {"source": "gm-demo"}
  }'
```

#### Q2: High Severity Count
**Question:** "How many high severity incidents"
- **Display Type:** metric
- **Expected SQL:** `SELECT COUNT(*) FROM incident_combine WHERE severity_name = 'high' AND property IN (...)`
- **Use Case:** Critical incidents KPI

#### Q3: Pending Count
**Question:** "How many pending incidents"
- **Display Type:** metric
- **Expected SQL:** `SELECT COUNT(*) FROM incident_combine WHERE status_name = 'pending' AND property IN (...)`
- **Use Case:** Open items KPI

---

### 📊 BAR CHART DISPLAYS (Category Comparisons)

Comparing categories side-by-side

#### Q4: Incidents by Category
**Question:** "Count incidents by category"
- **Display Type:** bar
- **Expected SQL:** `SELECT category_name, COUNT(*) as count FROM incident_combine WHERE property IN (...) GROUP BY category_name ORDER BY count DESC`
- **Use Case:** See which categories have the most incidents

**Test:**
```bash
curl -X POST http://localhost:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Count incidents by category",
    "context": {
      "language": "en",
      "property_uuid": "c7254cc9-9145-4602-b44b-0c1cff335f83,2b618b46-6b80-481b-b1e3-5aec1647b926",
      "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false, "max_rows": 100},
    "model": {"max_tokens": 512},
    "trace": {"source": "gm-demo"}
  }'
```

#### Q5: Category Breakdown
**Question:** "Show incident breakdown by category"
- **Display Type:** bar
- **Expected SQL:** `SELECT category_name, COUNT(*) as count FROM incident_combine WHERE property IN (...) GROUP BY category_name`
- **Use Case:** Category comparison view

#### Q6: Top Categories
**Question:** "Which categories have the most incidents"
- **Display Type:** bar
- **Expected SQL:** `SELECT category_name, COUNT(*) as count FROM incident_combine WHERE property IN (...) GROUP BY category_name ORDER BY count DESC LIMIT 10`
- **Use Case:** Identify problem areas

#### Q7: Severity Comparison
**Question:** "Count incidents by severity"
- **Display Type:** bar
- **Expected SQL:** `SELECT severity_name, COUNT(*) as count FROM incident_combine WHERE property IN (...) GROUP BY severity_name`
- **Use Case:** Compare high/medium/low volumes

---

### 🥧 PIE CHART DISPLAYS (Distribution Breakdown)

Showing proportions of the whole

#### Q8: Status Distribution
**Question:** "Incident breakdown by status"
- **Display Type:** pie
- **Expected SQL:** `SELECT status_name, COUNT(*) as count FROM incident_combine WHERE property IN (...) GROUP BY status_name`
- **Use Case:** See % pending vs completed vs cancelled

**Test:**
```bash
curl -X POST http://localhost:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Incident breakdown by status",
    "context": {
      "language": "en",
      "property_uuid": "c7254cc9-9145-4602-b44b-0c1cff335f83,2b618b46-6b80-481b-b1e3-5aec1647b926",
      "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false, "max_rows": 100},
    "model": {"max_tokens": 512},
    "trace": {"source": "gm-demo"}
  }'
```

#### Q9: Status Distribution Alt
**Question:** "Show status distribution"
- **Display Type:** pie
- **Expected SQL:** `SELECT status_name, COUNT(*) FROM incident_combine WHERE property IN (...) GROUP BY status_name`
- **Use Case:** Visual status breakdown

#### Q10: Severity Distribution
**Question:** "Incident distribution by severity"
- **Display Type:** pie
- **Expected SQL:** `SELECT severity_name, COUNT(*) FROM incident_combine WHERE property IN (...) GROUP BY severity_name`
- **Use Case:** See % high vs medium vs low

#### Q11: Severity Breakdown
**Question:** "Show severity breakdown"
- **Display Type:** pie
- **Expected SQL:** `SELECT severity_name, COUNT(*) as count FROM incident_combine WHERE property IN (...) GROUP BY severity_name`
- **Use Case:** Severity proportions

---

### 📉 LINE CHART DISPLAYS (Time Series Trends)

Showing trends over time

#### Q12: Daily Trend (7 Days)
**Question:** "Incidents per day last 7 days"
- **Display Type:** line
- **Expected SQL:** 
```sql
SELECT DATE(snapshotdate) as date, COUNT(*) as count 
FROM incident_combine 
WHERE property IN (...) 
AND date_parse(snapshotdate, '%Y-%m-%d') >= date_add('day', -7, current_date)
GROUP BY DATE(snapshotdate)
ORDER BY date
```
- **Use Case:** See if incidents are increasing/decreasing

**Test:**
```bash
curl -X POST http://localhost:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Incidents per day last 7 days",
    "context": {
      "language": "en",
      "property_uuid": "c7254cc9-9145-4602-b44b-0c1cff335f83,2b618b46-6b80-481b-b1e3-5aec1647b926",
      "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false, "max_rows": 100},
    "model": {"max_tokens": 512},
    "trace": {"source": "gm-demo"}
  }'
```

#### Q13: Daily Count (Last Week)
**Question:** "Daily incident count last week"
- **Display Type:** line
- **Expected SQL:** Similar to Q12
- **Use Case:** Weekly incident pattern

#### Q14: 30-Day Trend
**Question:** "Incident trend over last 30 days"
- **Display Type:** line
- **Expected SQL:** 
```sql
SELECT DATE(snapshotdate) as date, COUNT(*) as count 
FROM incident_combine 
WHERE property IN (...) 
AND date_parse(snapshotdate, '%Y-%m-%d') >= date_add('day', -30, current_date)
GROUP BY DATE(snapshotdate)
ORDER BY date
```
- **Use Case:** Monthly trend analysis

#### Q15: Daily Trend Generic
**Question:** "Show daily incident trend"
- **Display Type:** line
- **Expected SQL:** Daily aggregation with GROUP BY date
- **Use Case:** Trend visualization

---

## 📋 Complete Question List (By Display Type)

### Metrics (5 questions)
1. How many incidents are there
2. How many incidents do we have
3. How many high severity incidents
4. How many pending incidents
5. What is the total incident count

### Bar Charts (7 questions)
6. Count incidents by category
7. Show incidents by category
8. Incidents by department
9. How many incidents per category
10. Count incidents by severity
11. Show incident breakdown by category
12. Which categories have the most incidents

### Pie Charts (6 questions)
13. Incident breakdown by status
14. Show status distribution
15. Count incidents by status
16. Incident distribution by severity
17. Show severity breakdown
18. Percentage of incidents by status

### Line Charts (6 questions)
19. Incidents per day last 7 days
20. Daily incident count last week
21. Incident trend over last 30 days
22. Show daily incident trend
23. Incidents per day this month
24. Daily incident count

---

## 🧪 Testing All Chart Types

Run this test script to verify all chart types work:

```bash
#!/bin/bash

BASE_URL="http://localhost:8000/nlq/execute"
PROPERTY_UUID="c7254cc9-9145-4602-b44b-0c1cff335f83,2b618b46-6b80-481b-b1e3-5aec1647b926"
ACCOUNT_UUID="fccb8d60-de9c-4bf8-abd8-fae523c732c6"

test_query() {
    local question="$1"
    local expected_type="$2"
    
    echo "Testing: $question"
    echo "Expected: $expected_type"
    
    result=$(curl -s -X POST "$BASE_URL" -H "Content-Type: application/json" -d "{
      \"text\": \"$question\",
      \"context\": {
        \"language\": \"en\",
        \"property_uuid\": \"$PROPERTY_UUID\",
        \"account_uuid\": \"$ACCOUNT_UUID\"
      },
      \"sql\": {\"dialect\": \"athena\"},
      \"execution\": {\"dry_run\": false, \"max_rows\": 100},
      \"model\": {\"max_tokens\": 512},
      \"trace\": {\"source\": \"chart-test\"}
    }")
    
    display_type=$(echo "$result" | python3 -c "import json, sys; d=json.load(sys.stdin); print(d.get('display', {}).get('type', 'N/A'))" 2>/dev/null)
    row_count=$(echo "$result" | python3 -c "import json, sys; d=json.load(sys.stdin); print(len(d.get('execution', {}).get('rows', [])))" 2>/dev/null)
    
    if [ "$display_type" == "$expected_type" ]; then
        echo "✅ Display: $display_type, Rows: $row_count"
    else
        echo "❌ Display: $display_type (expected: $expected_type), Rows: $row_count"
    fi
    echo ""
    sleep 2
}

echo "=========================================="
echo "Testing Chart Display Types"
echo "=========================================="
echo ""

# Test metric
test_query "How many incidents are there" "metric"

# Test bar chart
test_query "Count incidents by category" "bar"

# Test pie chart
test_query "Incident breakdown by status" "pie"

# Test line chart
test_query "Incidents per day last 7 days" "line"

echo "=========================================="
echo "Test Complete!"
echo "=========================================="
```

---

## 💡 Key Differences from Table Questions

| Aspect | Table Questions | Chart Questions |
|--------|----------------|-----------------|
| **SQL Pattern** | `SELECT * FROM ... WHERE` | `SELECT category, COUNT(*) FROM ... GROUP BY` |
| **Data Structure** | Detailed rows | Aggregated summaries |
| **Row Count** | Many (10-100) | Few (2-50) |
| **Columns** | Many (5-15) | Few (2-3) |
| **Use Case** | Drill-down details | High-level overview |
| **Sorting** | By date, cost, severity | By count DESC |

---

## 🎯 Demo Flow Recommendation

1. **Start with metrics** - Show quick KPIs
   - "How many incidents are there"
   - "How many high severity incidents"

2. **Show distributions** - Use pie charts
   - "Incident breakdown by status"
   - "Show severity breakdown"

3. **Compare categories** - Use bar charts
   - "Count incidents by category"
   - "Which categories have the most incidents"

4. **Show trends** - Use line charts
   - "Incidents per day last 7 days"
   - "Incident trend over last 30 days"

5. **Drill down** - Switch to table view
   - "Show me all high severity incidents"

---

## 🔑 Success Criteria

For each chart type:

**Metric:**
- ✅ Returns 1 row, 1 column (single number)
- ✅ Response has `"type": "metric"`

**Bar Chart:**
- ✅ Returns 5-50 rows
- ✅ 2 columns: category + count
- ✅ Response has `"type": "bar"`
- ✅ Has chart_data with labels and datasets

**Pie Chart:**
- ✅ Returns 2-10 rows
- ✅ 2 columns: category + count
- ✅ Response has `"type": "pie"`
- ✅ Has chart_data with labels and datasets

**Line Chart:**
- ✅ Returns 7-30 rows (dates)
- ✅ 2 columns: date + count
- ✅ Response has `"type": "line"`
- ✅ Has chart_data with labels and datasets
- ✅ Data is ordered by date

---

## 📝 Notes

- All chart questions require **aggregation queries** (COUNT, SUM, AVG)
- All chart questions require **GROUP BY** clause
- Chart types are **automatically detected** by backend if not in the hardcoded map
- Frontend can override display type if needed via `display.type` in request payload
