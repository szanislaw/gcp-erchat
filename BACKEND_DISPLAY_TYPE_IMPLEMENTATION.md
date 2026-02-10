# Backend Display Type Hardcoding - Implementation Guide

## ✅ **SOLUTION IMPLEMENTED**

Display types are now **hardcoded in the backend** based on the question text. No frontend changes required!

---

## How It Works

### 1. User Experience
- User types question in chat bar: `"Show me all Service Quality incidents"`
- Frontend sends just the query text (no display type parameter needed)
- Backend automatically detects and sets the correct display type
- Response includes `display.type` field with the hardcoded value

### 2. Backend Detection Logic

**Priority Order:**
1. **Exact match in `QUERY_DISPLAY_TYPE_MAP`** (for GM demo questions) ⭐ **NEW**
2. Pattern matching (regex-based detection for other questions)
3. SQL analysis (fallback auto-detection from query structure)

### 3. Implementation Location

**File:** `app/display_hint.py`

**Hardcoded Map:**
```python
QUERY_DISPLAY_TYPE_MAP = {
    # === OPERATIONAL OVERVIEW (5 questions) ===
    "show me all incidents": "table",
    "show me all pending incidents": "table",
    "show me all service quality incidents": "bar",
    "show incidents from last 7 days": "line",
    "show recent incidents with medium severity": "pie",
    
    # === GUEST EXPERIENCE (2 unique questions) ===
    "show me incidents for food and beverage category": "bar",
    "show high severity incidents that are still pending": "table",
    
    # === FINANCIAL IMPACT (3 questions) ===
    "show me incidents with actual cost greater than 100": "bar",
    "show me all incidents sorted by actual cost": "table",
    "show me completed incidents": "pie",
    
    # === PERFORMANCE ANALYTICS (1 unique question) ===
    "show me incidents ordered by severity": "bar",
}
```

**Detection Function:**
```python
def get_display_type_from_question(question: str) -> Optional[str]:
    """
    Determine display type based on the user's natural language question.
    
    Priority:
    1. Exact match in QUERY_DISPLAY_TYPE_MAP (for GM demo questions)
    2. Pattern matching (regex-based detection)
    
    Returns:
        Display type string or None if no pattern matches
    """
    q = question.lower().strip()
    
    # PRIORITY 1: Check hardcoded GM demo question mapping first
    if q in QUERY_DISPLAY_TYPE_MAP:
        return QUERY_DISPLAY_TYPE_MAP[q]
    
    # PRIORITY 2: Pattern-based detection for other questions
    # ... (existing regex patterns)
```

---

## Request/Response Examples

### Example 1: Bar Chart (Category Comparison)

**Request:**
```json
{
  "text": "Show me all Service Quality incidents",
  "context": {
    "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec",
    "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"
  },
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 10},
  "trace": {"source": "gm-demo"}
}
```

**Response:**
```json
{
  "display": {
    "type": "bar",  // ✅ Automatically set by backend
    "chart_data": {
      "labels": ["2026-02-04", "2026-02-04", ...],
      "datasets": [...]
    }
  },
  "execution": {
    "rows": [...],
    "columns": [...]
  }
}
```

### Example 2: Table View (Detailed Data)

**Request:**
```json
{
  "text": "Show me all pending incidents",
  ...
}
```

**Response:**
```json
{
  "display": {
    "type": "table"  // ✅ Automatically set by backend
  },
  "execution": {
    "rows": [...],
    "columns": [...]
  }
}
```

### Example 3: Pie Chart (Distribution)

**Request:**
```json
{
  "text": "Show me completed incidents",
  ...
}
```

**Response:**
```json
{
  "display": {
    "type": "pie",  // ✅ Automatically set by backend
    "chart_data": {
      "labels": ["Completed", "Pending", ...],
      "datasets": [...]
    }
  }
}
```

### Example 4: Line Chart (Time Series)

**Request:**
```json
{
  "text": "Show incidents from last 7 days",
  ...
}
```

**Response:**
```json
{
  "display": {
    "type": "line",  // ✅ Automatically set by backend
    "chart_data": {
      "labels": ["Day 1", "Day 2", ...],
      "datasets": [...]
    }
  }
}
```

---

## Testing

### Automated Test Script

**File:** `test_backend_display_types.sh`

```bash
./test_backend_display_types.sh
```

### Test Results

All 11 unique GM demo questions verified:

```
Q1: "Show me all incidents" ... ✅ table (expected: table)
Q2: "Show me all pending incidents" ... ✅ table (expected: table)
Q3: "Show me all Service Quality incidents" ... ✅ bar (expected: bar)
Q4: "Show incidents from last 7 days" ... ✅ line (expected: line)
Q5: "Show recent incidents with medium severity" ... ✅ pie (expected: pie)
Q6: "Show me incidents for Food and Beverage category" ... ✅ bar (expected: bar)
Q7: "Show high severity incidents that are still pending" ... ✅ table (expected: table)
Q8: "Show me incidents with actual cost greater than 100" ... ✅ bar (expected: bar)
Q9: "Show me all incidents sorted by actual cost" ... ✅ table (expected: table)
Q10: "Show me completed incidents" ... ✅ pie (expected: pie)
Q11: "Show me incidents ordered by severity" ... ✅ bar (expected: bar)
```

---

## Display Type Distribution

Across 20 GM demo questions:

| Display Type | Count | Percentage | Use Case |
|-------------|-------|-----------|----------|
| **table** | 9 | 45% | Detailed data views, lists |
| **bar** | 7 | 35% | Category comparisons, rankings |
| **pie** | 3 | 15% | Status/severity distributions |
| **line** | 2 | 10% | Time series, trends |

---

## Key Advantages

1. ✅ **No Frontend Changes Required** - Works with existing chat bar
2. ✅ **Centralized Logic** - All display type rules in one place (backend)
3. ✅ **Case Insensitive** - Queries are normalized to lowercase
4. ✅ **Flexible** - Easy to add/modify mappings in `QUERY_DISPLAY_TYPE_MAP`
5. ✅ **Fallback Support** - Pattern matching for non-demo questions
6. ✅ **Type Safety** - Backend validates and formats chart data

---

## Adding New Questions

To add a new hardcoded display type:

1. Edit `app/display_hint.py`
2. Add entry to `QUERY_DISPLAY_TYPE_MAP`:
   ```python
   "your new question here": "bar",  # or "table", "pie", "line"
   ```
3. Restart the API server
4. Test with curl or the test script

**Example:**
```python
QUERY_DISPLAY_TYPE_MAP = {
    # ... existing mappings ...
    "show me high priority incidents": "table",
    "count incidents by department": "bar",
    # ... more mappings ...
}
```

---

## Files Modified

1. **`app/display_hint.py`**
   - Updated `QUERY_DISPLAY_TYPE_MAP` with 11 unique questions
   - Modified `get_display_type_from_question()` to check map first

2. **`app/main.py`**
   - Added missing import: `from app.chart_formatter import format_for_chart`

3. **`test_backend_display_types.sh`** (new file)
   - Automated test script for all questions

4. **`BACKEND_DISPLAY_TYPE_IMPLEMENTATION.md`** (this file)
   - Implementation documentation

---

## Related Documentation

- **`GM_DEMO_QUESTIONS.md`** - Complete list of 20 demo questions with display types
- **`GM_DEMO_TEST_RESULTS.md`** - Initial test results showing which queries work
- **`FRONTEND_DISPLAY_TYPE_SOLUTION.md`** - Frontend solutions (now deprecated)

---

## Troubleshooting

### Question not getting correct display type?

1. Check exact text match (case-insensitive):
   ```bash
   curl -X POST http://localhost:8000/nlq/execute -d '{
     "text": "Your Question Here",
     ...
   }'
   ```

2. Verify in logs:
   ```bash
   tail -f logs/api.log | grep "display type"
   ```

3. Check `QUERY_DISPLAY_TYPE_MAP` for typos

### Need to debug detection logic?

Add logging in `app/display_hint.py`:
```python
def get_display_type_from_question(question: str) -> Optional[str]:
    q = question.lower().strip()
    logger.info(f"Checking display type for: '{q}'")
    
    if q in QUERY_DISPLAY_TYPE_MAP:
        logger.info(f"Found in map: {QUERY_DISPLAY_TYPE_MAP[q]}")
        return QUERY_DISPLAY_TYPE_MAP[q]
    ...
```

---

## Summary

✅ **Problem Solved:** Display types are now hardcoded in the backend based on exact question text matching.

✅ **No Frontend Work Required:** Chat bar works as-is, just sends query text.

✅ **All 11 Unique Questions Tested:** Each returns the correct display type automatically.

✅ **Mixed Display Types Achieved:** 9 table, 7 bar, 3 pie, 2 line across 20 questions.

The solution is production-ready and requires no changes to the frontend code!
