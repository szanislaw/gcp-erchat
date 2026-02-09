# Potential Issues Analysis - 20 GM Demo Questions

## Summary
After analyzing the database schema and comparing with the 20 demo questions, here are the potential issues identified:

---

## ✅ QUESTIONS THAT SHOULD WORK PERFECTLY (15/20)

### No Issues Expected:
1. ✓ "How many incidents were reported today?"
2. ✓ "Show me all pending incidents"
3. ✓ "Count incidents by department"
4. ✓ "Show incidents from last 7 days"
5. ✓ "How many high severity incidents in the last 30 days?"
8. ✓ "Show high severity incidents that are still pending"
9. ✓ "Show me all incidents at room 1018"
10. ✓ "What is the total actual cost of all incidents?"
11. ✓ "Show me the top 5 incidents by actual cost"
13. ✓ "Which department has the most incidents?"
14. ✓ "Show incident breakdown by severity"
15. ✓ "Count incidents by category"
18. ✓ "How many incidents does each property have?"
19. ✓ "Show me incidents ordered by severity"
20. ✓ "Count incidents by status"

---

## ⚠️ QUESTIONS WITH POTENTIAL ISSUES (5/20)

### 6. "Show me Room Service incidents from this week"
**Potential Issue:** Category name mismatch
- **Problem:** The question assumes "Room Service" is a category name
- **Reality:** We don't know the exact category values in the database
- **Possible values:** Could be "Food & Beverage - Room Service", "F&B", "Room Service", etc.
- **Risk Level:** MEDIUM
- **Recommendation:** 
  - Update question to: "Show me Food and Beverage incidents from this week"
  - OR verify actual category_name values and use exact match

### 7. "What are the most common Room Cleanliness incidents?"
**Potential Issue:** Category name mismatch
- **Problem:** Assumes "Room Cleanliness" is the exact category name
- **Reality:** Could be "Housekeeping - Room Cleanliness", "Cleanliness", "Room Cleaning", etc.
- **Risk Level:** MEDIUM
- **Recommendation:**
  - Update to: "What are the most common housekeeping category incidents?"
  - OR: "Count incidents by category where category contains cleanliness"

### 12. "What is the average actual cost for completed incidents by category?"
**Potential Issue:** Complex aggregation + filtering
- **Problem:** Requires AVG() + GROUP BY + WHERE status_name='completed'
- **Reality:** Should work but is complex - model might struggle
- **Risk Level:** LOW-MEDIUM
- **Recommendation:** Test this query specifically; might need rephrasing

### 16. "Show recent Housekeeping incidents with medium severity"
**Potential Issue:** Department name case sensitivity
- **Problem:** Question uses "Housekeeping" - need exact match including case
- **Reality:** Database has department_name, but we don't know the exact casing
- **Possible values:** "Housekeeping", "housekeeping", "HOUSEKEEPING", "Hskp", etc.
- **Risk Level:** LOW (prompt instructs model to use lowercase)
- **Note:** The prompt says categorical values are lowercase, so model should generate `department_name = 'housekeeping'`

### 17. "How many incidents were completed in the last month?"
**Potential Issue:** "Last month" date interpretation
- **Problem:** "Last month" is ambiguous - could mean:
  - Last 30 days
  - Previous calendar month (e.g., if today is Feb 9, then January)
  - Last 4 weeks
- **Risk Level:** LOW
- **Recommendation:** Rephrase to "in the last 30 days" for clarity

---

## 🔍 SPECIFIC CONCERNS TO TEST

### 1. Date Filtering (Multiple Questions)
**Questions Affected:** 1, 4, 5, 6, 17
**Issue:** snapshotdate is a STRING column
- **Must use:** `date_parse(snapshotdate, '%Y-%m-%d')`
- **Prompt handles this:** Yes, explicitly instructs date parsing
- **Action:** Test date queries to ensure proper formatting

### 2. Time Aggregation (Not in 20 questions, but mentioned in your issue)
**Question:** "Show me number of incidents per month"
**Issue:** Month grouping/extraction
- **SQL needed:** `month(date_parse(snapshotdate, '%Y-%m-%d'))` or similar
- **Status:** Should work now with improved time series detection
- **Display:** Should show as line chart

### 3. Property UUID Filtering
**All Questions Affected**
**Issue:** Property partition filtering
- **Fixed:** Now correctly uses `property` partition instead of non-existent `property_uuid`
- **Behavior:** All queries will include `WHERE property IN (...)` 
- **Note:** For demo with all-zeros UUID (super user), no filtering applied

### 4. Case Sensitivity
**Questions Affected:** 5, 8, 14, 16, 20
**Issue:** Severity and status values
- **Database values:** Lowercase ('high', 'medium', 'low', 'pending', 'completed', 'cancelled')
- **Prompt handles:** Yes, explicitly states to use lowercase
- **Action:** Should work correctly

---

## 📋 RECOMMENDED FIXES FOR GM_DEMO_QUESTIONS.md

### Priority 1: High Risk (Should Fix)
```markdown
# BEFORE:
6. "Show me Room Service incidents from this week"

# AFTER:
6. "Show me incidents from this week for the Food and Beverage department"
OR
6. "Show me incidents this week where category contains 'room service'"
```

```markdown
# BEFORE:
7. "What are the most common Room Cleanliness incidents?"

# AFTER:
7. "What are the most common housekeeping incidents?"
OR
7. "Count incidents by incident name for housekeeping department"
```

### Priority 2: Medium Risk (Consider Rephrasing)
```markdown
# BEFORE:
17. "How many incidents were completed in the last month?"

# AFTER:
17. "How many incidents were completed in the last 30 days?"
```

### Priority 3: Test These Specifically
- Question 12: Complex aggregation with filtering
- Question 16: Department name matching
- All date-based questions (1, 4, 5, 6, 17)

---

## 🧪 SUGGESTED PRE-DEMO VALIDATION

### 1. Query Actual Category Values
```sql
SELECT DISTINCT category_name 
FROM incident_combine 
WHERE property = 'YOUR_PROPERTY_UUID'
ORDER BY category_name
LIMIT 50
```

### 2. Query Actual Department Values
```sql
SELECT DISTINCT department_name 
FROM incident_combine 
WHERE property = 'YOUR_PROPERTY_UUID'
ORDER BY department_name
```

### 3. Test Date Queries
Run questions 1, 4, 5 to verify date filtering works correctly

### 4. Test Aggregations
Run questions 12, 13, 15 to verify GROUP BY queries work

---

## 🎯 OVERALL ASSESSMENT

**Risk Level:** LOW-MEDIUM
- **15 of 20 questions (75%)** should work perfectly without modification
- **2 questions (10%)** have category/department name assumptions that need verification
- **3 questions (15%)** are complex but should work with testing

**Recommendation:** 
1. ✅ Use the 15 "safe" questions for the main demo
2. ⚠️ Test questions 6, 7, 12, 16, 17 before including in demo
3. 🔧 Update questions 6 and 7 to avoid specific category names
4. 📊 Verify actual category_name and department_name values in the database

**Action Items:**
- [ ] Query database for actual category_name values
- [ ] Query database for actual department_name values
- [ ] Test all 20 questions against real data
- [ ] Update GM_DEMO_QUESTIONS.md with verified category/department names
- [ ] Create backup questions for questions 6 and 7
