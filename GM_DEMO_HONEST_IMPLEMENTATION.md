# GM Demo Questions - Data & Display Type Implementation

## ⚠️ CRITICAL: Data Validation Required

**Before using these demo questions, you MUST verify that your property UUID has incident data.**

### Quick Data Check

```bash
# Test if your property has data
curl -X POST http://localhost:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Show me all incidents",
    "context": {
      "property_uuid": "YOUR_PROPERTY_UUID_HERE",
      "account_uuid": "YOUR_ACCOUNT_UUID_HERE"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false, "max_rows": 10},
    "model": {"max_tokens": 512},
    "trace": {"source": "data-check"}
  }'
```

**Expected:** Should return `"rows": [...]` with incident data
**If no data:** You need to use a different property UUID that has incidents

---

## 🎯 Display Type Philosophy

**All GM demo questions use "table" display type** because:

1. **Queries return detailed records** - `SELECT * FROM incident_combine WHERE...`
2. **No aggregation** - No `COUNT`, `SUM`, `AVG`, or `GROUP BY`
3. **Table is most honest** - Shows actual data structure without forcing inappropriate visualizations

### When to Use Each Display Type

| Display Type | Requires | Example Query |
|-------------|----------|---------------|
| **table** | Any SELECT query | `SELECT * FROM incidents WHERE status='pending'` |
| **bar** | GROUP BY + aggregation | `SELECT category, COUNT(*) FROM incidents GROUP BY category` |
| **pie** | GROUP BY + aggregation (2-10 categories) | `SELECT status, COUNT(*) FROM incidents GROUP BY status` |
| **line** | Date grouping + aggregation | `SELECT DATE(created), COUNT(*) FROM incidents GROUP BY DATE(created)` |

### ❌ Don't Force Charts

**Bad:** Showing `SELECT * FROM incidents` as a pie chart
- No aggregation = meaningless visualization
- Frontend would need to fabricate groupings
- Misleading to users

**Good:** Showing `SELECT * FROM incidents` as a table
- Displays actual data structure
- Users see real incident records
- Can sort/filter/search

---

## 📋 GM Demo Questions (All Table Display)

All 11 unique questions are configured with `display_type: "table"` in the backend.

### Why Table for All?

1. **"Show me all incidents"** - Returns list of incidents → Table makes sense ✅
2. **"Show me all pending incidents"** - Filtered list → Table makes sense ✅
3. **"Show me all Service Quality incidents"** - Category filter → Table makes sense ✅
4. **"Show incidents from last 7 days"** - Date filter → Table makes sense ✅
   - ❌ Line chart would need: `GROUP BY DATE(created)` 
5. **"Show recent incidents with medium severity"** - Severity filter → Table makes sense ✅
   - ❌ Pie chart would need: `GROUP BY severity`
6. **"Show me incidents for Food and Beverage category"** → Table makes sense ✅
   - ❌ Bar chart would need: `GROUP BY subcategory` or similar
7. **"Show high severity incidents that are still pending"** → Table makes sense ✅
8. **"Show me incidents with actual cost greater than 100"** → Table makes sense ✅
   - ❌ Bar chart would need: `GROUP BY category` 
9. **"Show me all incidents sorted by actual cost"** → Table makes sense ✅
10. **"Show me completed incidents"** → Table makes sense ✅
    - ❌ Pie chart would need: `GROUP BY status`
11. **"Show me incidents ordered by severity"** → Table makes sense ✅

---

## 🛠️ Implementation

### Backend (Already Implemented)

**File:** `app/display_hint.py`

```python
QUERY_DISPLAY_TYPE_MAP = {
    "show me all incidents": "table",
    "show me all pending incidents": "table",
    "show me all service quality incidents": "table",
    "show incidents from last 7 days": "table",
    "show recent incidents with medium severity": "table",
    "show me incidents for food and beverage category": "table",
    "show high severity incidents that are still pending": "table",
    "show me incidents with actual cost greater than 100": "table",
    "show me all incidents sorted by actual cost": "table",
    "show me completed incidents": "table",
    "show me incidents ordered by severity": "table",
}
```

### How Backend Works

1. User sends: `{"text": "Show me all pending incidents"}`
2. Backend checks `QUERY_DISPLAY_TYPE_MAP`
3. Finds exact match → Returns `{"display": {"type": "table"}}`
4. Frontend receives display type automatically

### Frontend Integration

**No changes needed!** Just render based on `response.display.type`:

```javascript
const response = await fetch('/nlq/execute', {
  method: 'POST',
  body: JSON.stringify({
    text: userQuery,  // Just the query text
    context: {...},
  })
});

const data = await response.json();
const displayType = data.display.type;  // "table" for all GM demo questions

if (displayType === "table") {
  renderTable(data.execution.rows, data.execution.columns);
} else if (displayType === "bar") {
  renderBarChart(data.display.chart_data);
} else if (displayType === "pie") {
  renderPieChart(data.display.chart_data);
} else if (displayType === "line") {
  renderLineChart(data.display.chart_data);
}
```

---

## 🚨 Common Issues

### Issue 1: No Data Returned

**Symptom:** All queries return 0 rows

**Cause:** Property UUID has no incident data in database

**Fix:**
1. Find a property UUID with data (see Data Check section above)
2. Update `property_uuid` in all requests
3. Retest queries

### Issue 2: Display Type Not Set

**Symptom:** `response.display.type` is undefined

**Cause:** Query text doesn't match `QUERY_DISPLAY_TYPE_MAP` exactly

**Fix:**
- Queries are case-insensitive
- Check for typos: "Show me all incidents" vs "show me all incidents"
- Backend normalizes to lowercase before matching

### Issue 3: Want Different Display Types

**Problem:** You want bar/pie/line charts for some questions

**Reality Check:**
- Current queries return `SELECT * FROM...` (detailed rows)
- Charts need aggregated data (`GROUP BY`)
- Forcing charts on non-aggregated data is misleading

**Solution:** Modify queries to use aggregation:
```sql
-- For bar chart:
SELECT category_name, COUNT(*) as count 
FROM incident_combine 
GROUP BY category_name

-- For pie chart:
SELECT severity_name, COUNT(*) as count 
FROM incident_combine 
GROUP BY severity_name

-- For line chart:
SELECT DATE(snapshotdate) as date, COUNT(*) as count 
FROM incident_combine 
WHERE snapshotdate >= CURRENT_DATE - INTERVAL '7' DAY
GROUP BY DATE(snapshotdate)
```

---

## 📊 Testing

### Test Script

```bash
./test_backend_display_types.sh
```

**Expected Output:**
```
Q1: "Show me all incidents" ... ✅ table (expected: table)
Q2: "Show me all pending incidents" ... ✅ table (expected: table)
... (all 11 questions should show ✅ table)
```

### Manual Test

```bash
curl -X POST http://localhost:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Show me all pending incidents",
    "context": {
      "property_uuid": "YOUR_UUID",
      "account_uuid": "YOUR_UUID"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false, "max_rows": 10},
    "model": {"max_tokens": 512},
    "trace": {"source": "manual-test"}
  }' | python3 -m json.tool | grep -A 2 '"display"'
```

**Expected:**
```json
"display": {
  "type": "table"
},
```

---

## 📝 Summary

✅ **All 11 GM demo questions use "table" display**
✅ **Backend automatically sets display type**
✅ **No frontend changes needed**
✅ **Honest representation of data structure**
✅ **No forced/fake visualizations**

⚠️ **Remember:** Verify your property UUID has data before demo!

---

## 🔗 Related Files

- `app/display_hint.py` - Backend display type mapping
- `GM_DEMO_QUESTIONS.md` - Complete question list (needs update)
- `test_backend_display_types.sh` - Automated testing
- `BACKEND_DISPLAY_TYPE_IMPLEMENTATION.md` - Original implementation docs
