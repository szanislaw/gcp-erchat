# Demo Questions — Incident Management Analytics

**50 questions — 50/50 (100%) pass rate**  
**Target:** `redshift_target: incident`  
**Table:** `mv_recovery_all` (flat pre-joined view — NO JOINs needed)

---

## Schema

| Column | Type | Notes |
|--------|------|-------|
| `recovery_no` | VARCHAR | Incident report ID |
| `status_name` | VARCHAR | `pending`, `draft`, `completed`, `cancelled` |
| `severity_name` | VARCHAR | `critical`, `high`, `medium`, `low` |
| `department_name` | VARCHAR | Pre-joined, use directly |
| `incident_name` | VARCHAR | Type of incident |
| `category_name` | VARCHAR | Incident category |
| `location_name` | VARCHAR | Property location, pre-joined |
| `temperament_text` | VARCHAR | Guest temperament (Angry, Calm, Concerned…) |
| `profile_name` | VARCHAR | Recovery profile/type |
| `compensation_text` | VARCHAR | Compensation offered |
| `vip` | VARCHAR | VIP guest flag (non-null/non-empty = VIP) |
| `created_date` | TIMESTAMP | When incident was logged |
| `incident_time` | TIMESTAMP | When incident occurred |
| `completed_date` | TIMESTAMP | When resolved |
| `cancelled_date` | TIMESTAMP | When cancelled |
| `actual_cost` | NUMERIC | Actual compensation cost |
| `potential_cost` | NUMERIC | Estimated cost |

**Status semantics:**
- "open" → `status_name IN ('pending', 'draft')`
- "resolved / closed / done" → `status_name = 'completed'`
- Always lowercase — never `'Completed'` or `'PENDING'`

---

## Question Index

| ID | Question | Display |
|----|----------|---------|
| I01 | How many total incidents are there? | metric |
| I02 | How many open incidents are there? | metric |
| I03 | How many completed incidents? | metric |
| I04 | How many cancelled incidents? | metric |
| I05 | How many draft incidents are there? | metric |
| I06 | How many high severity incidents? | metric |
| I07 | How many critical severity incidents are there? | metric |
| I08 | How many pending incidents? | metric |
| IB01 | Show incident count by status | bar |
| IB02 | Show incident count by severity | bar |
| IB03 | Show incident count by category | bar |
| IB04 | Show incident count by department | bar |
| IB05 | Which category has the most incidents? | metric |
| IB06 | Which department has the most incidents? | metric |
| IB07 | Show incident count by location | bar |
| IB08 | Show top 5 incident categories | bar |
| IC01 | How many incidents were created this month? | metric |
| IC02 | How many incidents were created this year? | metric |
| IC03 | How many incidents were created this week? | metric |
| IC04 | How many incidents were created last month? | metric |
| IC05 | How many incidents were created last week? | metric |
| IC06 | How many incidents were created in the last 30 days? | metric |
| IC07 | How many incidents were completed this month? | metric |
| IC08 | How many incidents were created in the last 7 days? | metric |
| ID01 | Show the monthly incident trend | line |
| ID02 | Show the weekly incident trend for this year | line |
| ID03 | Show the daily incident trend this month | line |
| ID04 | Show monthly trend of completed incidents | line |
| ID05 | Show monthly incident count by severity | line |
| ID06 | Show weekly trend of open incidents | line |
| IE01 | What is the average actual cost per incident? | metric |
| IE02 | Show average cost by category | bar |
| IE03 | Show average cost by severity | bar |
| IE04 | What is the total actual cost of all incidents? | metric |
| IE05 | Show top 5 categories by average cost | bar |
| IF01 | How many high severity open incidents are there? | metric |
| IF02 | How many critical incidents are pending? | metric |
| IF03 | How many completed high severity incidents are there? | metric |
| IF04 | How many VIP guest incidents are there? | metric |
| IF05 | How many high severity incidents were created this month? | metric |
| IF06 | How many open critical incidents are there? | metric |
| IG01 | What percentage of incidents are completed? | metric |
| IG02 | What percentage of incidents are open? | metric |
| IG03 | What percentage of incidents are high or critical severity? | metric |
| IG04 | What percentage of incidents created this month are completed? | metric |
| IH01 | Show the 10 most recent incidents | table |
| IH02 | Show the 5 most recent completed incidents | table |
| IH03 | Show recent high severity incidents | table |
| IH04 | Show recent incidents with their categories and status | table |
| IH05 | Show the most recent VIP guest incidents | table |

---

## METRIC — Simple Counts (I01–I08)

### I01. How many total incidents are there?
**SQL:**
```sql
SELECT COUNT(*) FROM mv_recovery_all LIMIT 100
```

### I02. How many open incidents are there?
**SQL:**
```sql
SELECT COUNT(*) FROM mv_recovery_all
WHERE status_name IN ('pending', 'draft') LIMIT 100
```

### I03. How many completed incidents?
**SQL:**
```sql
SELECT COUNT(*) FROM mv_recovery_all
WHERE status_name = 'completed' LIMIT 100
```

### I04. How many cancelled incidents?
**SQL:**
```sql
SELECT COUNT(*) FROM mv_recovery_all
WHERE status_name = 'cancelled' LIMIT 100
```

### I05. How many draft incidents are there?
**SQL:**
```sql
SELECT COUNT(*) FROM mv_recovery_all
WHERE status_name = 'draft' LIMIT 100
```

### I06. How many high severity incidents?
**SQL:**
```sql
SELECT COUNT(*) FROM mv_recovery_all
WHERE severity_name = 'high' LIMIT 100
```

### I07. How many critical severity incidents are there?
**SQL:**
```sql
SELECT COUNT(*) FROM mv_recovery_all
WHERE severity_name = 'critical' LIMIT 100
```

### I08. How many pending incidents?
**SQL:**
```sql
SELECT COUNT(*) FROM mv_recovery_all
WHERE status_name IN ('pending', 'draft') LIMIT 100
```

---

## BAR — Group By Breakdowns (IB01–IB08)

### IB01. Show incident count by status
**SQL:**
```sql
SELECT status_name, COUNT(*) FROM mv_recovery_all
GROUP BY status_name ORDER BY COUNT(*) DESC LIMIT 100
```

### IB02. Show incident count by severity
**SQL:**
```sql
SELECT severity_name, COUNT(*) FROM mv_recovery_all
GROUP BY severity_name ORDER BY COUNT(*) DESC LIMIT 100
```

### IB03. Show incident count by category
**SQL:**
```sql
SELECT category_name, COUNT(*) FROM mv_recovery_all
GROUP BY category_name ORDER BY COUNT(*) DESC LIMIT 100
```

### IB04. Show incident count by department
**SQL:**
```sql
SELECT department_name, COUNT(*) FROM mv_recovery_all
GROUP BY department_name ORDER BY COUNT(*) DESC LIMIT 100
```

### IB05. Which category has the most incidents?
**SQL:**
```sql
SELECT category_name, COUNT(*) FROM mv_recovery_all
GROUP BY category_name ORDER BY COUNT(*) DESC LIMIT 1
```

### IB06. Which department has the most incidents?
**SQL:**
```sql
SELECT department_name, COUNT(*) FROM mv_recovery_all
GROUP BY department_name ORDER BY COUNT(*) DESC LIMIT 1
```

### IB07. Show incident count by location
**SQL:**
```sql
SELECT location_name, COUNT(*) FROM mv_recovery_all
GROUP BY location_name ORDER BY COUNT(*) DESC LIMIT 100
```

### IB08. Show top 5 incident categories
**SQL:**
```sql
SELECT category_name, COUNT(*) FROM mv_recovery_all
GROUP BY category_name ORDER BY COUNT(*) DESC LIMIT 5
```

---

## METRIC — Date Filters (IC01–IC08)

### IC01. How many incidents were created this month?
**SQL:**
```sql
SELECT COUNT(*) FROM mv_recovery_all
WHERE created_date >= DATE_TRUNC('month', CURRENT_DATE) LIMIT 100
```

### IC02. How many incidents were created this year?
**SQL:**
```sql
SELECT COUNT(*) FROM mv_recovery_all
WHERE EXTRACT(YEAR FROM created_date) = EXTRACT(YEAR FROM CURRENT_DATE) LIMIT 100
```

### IC03. How many incidents were created this week?
**SQL:**
```sql
SELECT COUNT(*) FROM mv_recovery_all
WHERE created_date >= DATE_TRUNC('week', CURRENT_DATE) LIMIT 100
```

### IC04. How many incidents were created last month?
**SQL:**
```sql
SELECT COUNT(*) FROM mv_recovery_all
WHERE created_date >= DATEADD(month, -1, DATE_TRUNC('month', CURRENT_DATE))
  AND created_date < DATE_TRUNC('month', CURRENT_DATE) LIMIT 100
```

### IC05. How many incidents were created last week?
**SQL:**
```sql
SELECT COUNT(*) FROM mv_recovery_all
WHERE created_date >= DATEADD(week, -1, DATE_TRUNC('week', CURRENT_DATE))
  AND created_date < DATE_TRUNC('week', CURRENT_DATE) LIMIT 100
```

### IC06. How many incidents were created in the last 30 days?
**SQL:**
```sql
SELECT COUNT(*) FROM mv_recovery_all
WHERE created_date >= DATEADD(day, -30, CURRENT_DATE) LIMIT 100
```

### IC07. How many incidents were completed this month?
**SQL:**
```sql
SELECT COUNT(*) FROM mv_recovery_all
WHERE status_name = 'completed'
  AND DATE_TRUNC('month', created_date) = DATE_TRUNC('month', CURRENT_DATE) LIMIT 100
```

### IC08. How many incidents were created in the last 7 days?
**SQL:**
```sql
SELECT COUNT(*) FROM mv_recovery_all
WHERE created_date >= DATEADD(day, -7, CURRENT_DATE) LIMIT 100
```

---

## LINE — Trend Analysis (ID01–ID06)

### ID01. Show the monthly incident trend
**SQL:**
```sql
SELECT DATE_TRUNC('month', created_date) AS month, COUNT(*) AS incidents
FROM mv_recovery_all GROUP BY 1 ORDER BY 1 LIMIT 100
```

### ID02. Show the weekly incident trend for this year
**SQL:**
```sql
SELECT DATE_TRUNC('week', created_date) AS week, COUNT(*) AS incidents
FROM mv_recovery_all
WHERE EXTRACT(YEAR FROM created_date) = EXTRACT(YEAR FROM CURRENT_DATE)
GROUP BY 1 ORDER BY 1 LIMIT 100
```

### ID03. Show the daily incident trend this month
**SQL:**
```sql
SELECT DATE_TRUNC('day', created_date) AS day, COUNT(*) AS incidents
FROM mv_recovery_all
WHERE created_date >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY 1 ORDER BY 1 LIMIT 100
```

### ID04. Show monthly trend of completed incidents
**SQL:**
```sql
SELECT DATE_TRUNC('month', created_date) AS month, COUNT(*) AS incidents
FROM mv_recovery_all WHERE status_name = 'completed'
GROUP BY 1 ORDER BY 1 LIMIT 100
```

### ID05. Show monthly incident count by severity
**SQL:**
```sql
SELECT DATE_TRUNC('month', created_date) AS month, severity_name, COUNT(*) AS incidents
FROM mv_recovery_all GROUP BY 1, 2 ORDER BY 1 LIMIT 100
```

### ID06. Show weekly trend of open incidents
**SQL:**
```sql
SELECT DATE_TRUNC('week', created_date) AS week, COUNT(*) AS incidents
FROM mv_recovery_all WHERE status_name IN ('pending', 'draft')
GROUP BY 1 ORDER BY 1 LIMIT 100
```

---

## BAR — Cost Analysis (IE01–IE05)

### IE01. What is the average actual cost per incident?
**SQL:**
```sql
SELECT AVG(actual_cost) AS avg_cost FROM mv_recovery_all
WHERE actual_cost > 0 LIMIT 100
```

### IE02. Show average cost by category
**SQL:**
```sql
SELECT category_name, AVG(actual_cost) AS avg_cost FROM mv_recovery_all
WHERE actual_cost > 0 GROUP BY category_name ORDER BY avg_cost DESC LIMIT 100
```

### IE03. Show average cost by severity
**SQL:**
```sql
SELECT severity_name, AVG(actual_cost) AS avg_cost FROM mv_recovery_all
WHERE actual_cost > 0 GROUP BY severity_name ORDER BY avg_cost DESC LIMIT 100
```

### IE04. What is the total actual cost of all incidents?
**SQL:**
```sql
SELECT SUM(actual_cost) AS total_cost FROM mv_recovery_all
WHERE actual_cost > 0 LIMIT 100
```

### IE05. Show top 5 categories by average cost
**SQL:**
```sql
SELECT category_name, AVG(actual_cost) AS avg_cost FROM mv_recovery_all
WHERE actual_cost > 0 GROUP BY category_name ORDER BY avg_cost DESC LIMIT 5
```

---

## METRIC — Combined Filters (IF01–IF06)

### IF01. How many high severity open incidents are there?
**SQL:**
```sql
SELECT COUNT(*) FROM mv_recovery_all
WHERE severity_name = 'high' AND status_name IN ('pending', 'draft') LIMIT 100
```

### IF02. How many critical incidents are pending?
**SQL:**
```sql
SELECT COUNT(*) FROM mv_recovery_all
WHERE severity_name = 'critical' AND status_name = 'pending' LIMIT 100
```

### IF03. How many completed high severity incidents are there?
**SQL:**
```sql
SELECT COUNT(*) FROM mv_recovery_all
WHERE severity_name = 'high' AND status_name = 'completed' LIMIT 100
```

### IF04. How many VIP guest incidents are there?
**SQL:**
```sql
SELECT COUNT(*) FROM mv_recovery_all
WHERE vip IS NOT NULL AND vip != '' LIMIT 100
```

### IF05. How many high severity incidents were created this month?
**SQL:**
```sql
SELECT COUNT(*) FROM mv_recovery_all
WHERE severity_name = 'high'
  AND created_date >= DATE_TRUNC('month', CURRENT_DATE) LIMIT 100
```

### IF06. How many open critical incidents are there?
**SQL:**
```sql
SELECT COUNT(*) FROM mv_recovery_all
WHERE severity_name = 'critical' AND status_name IN ('pending', 'draft') LIMIT 100
```

---

## METRIC — Percentages (IG01–IG04)

### IG01. What percentage of incidents are completed?
**SQL:**
```sql
SELECT CAST(COUNT(CASE WHEN status_name = 'completed' THEN 1 END) AS FLOAT)
       * 100.0 / NULLIF(COUNT(*), 0) AS pct_completed
FROM mv_recovery_all LIMIT 100
```

### IG02. What percentage of incidents are open?
**SQL:**
```sql
SELECT CAST(COUNT(CASE WHEN status_name IN ('pending', 'draft') THEN 1 END) AS FLOAT)
       * 100.0 / NULLIF(COUNT(*), 0) AS pct_open
FROM mv_recovery_all LIMIT 100
```

### IG03. What percentage of incidents are high or critical severity?
**SQL:**
```sql
SELECT CAST(COUNT(CASE WHEN severity_name IN ('high', 'critical') THEN 1 END) AS FLOAT)
       * 100.0 / NULLIF(COUNT(*), 0) AS pct_high_critical
FROM mv_recovery_all LIMIT 100
```

### IG04. What percentage of incidents created this month are completed?
**SQL:**
```sql
SELECT CAST(COUNT(CASE WHEN status_name = 'completed' THEN 1 END) AS FLOAT)
       * 100.0 / NULLIF(COUNT(*), 0) AS pct_completed
FROM mv_recovery_all
WHERE created_date >= DATE_TRUNC('month', CURRENT_DATE) LIMIT 100
```

---

## TABLE — Listings (IH01–IH05)

### IH01. Show the 10 most recent incidents
**SQL:**
```sql
SELECT recovery_no, incident_name, status_name, severity_name, created_date
FROM mv_recovery_all ORDER BY created_date DESC LIMIT 10
```

### IH02. Show the 5 most recent completed incidents
**SQL:**
```sql
SELECT recovery_no, incident_name, department_name, created_date
FROM mv_recovery_all WHERE status_name = 'completed'
ORDER BY created_date DESC LIMIT 5
```

### IH03. Show recent high severity incidents
**SQL:**
```sql
SELECT recovery_no, incident_name, department_name, created_date
FROM mv_recovery_all WHERE severity_name = 'high'
ORDER BY created_date DESC LIMIT 100
```

### IH04. Show recent incidents with their categories and status
**SQL:**
```sql
SELECT recovery_no, incident_name, category_name, status_name, created_date
FROM mv_recovery_all ORDER BY created_date DESC LIMIT 100
```

### IH05. Show the most recent VIP guest incidents
**SQL:**
```sql
SELECT recovery_no, incident_name, status_name, created_date
FROM mv_recovery_all WHERE vip IS NOT NULL AND vip != ''
ORDER BY created_date DESC LIMIT 100
```

---

## Testing

```bash
# Run full 50-question suite (dry-run, no Redshift needed)
python3 test/test_50_incident_questions.py

# Live Redshift execution
python3 test/test_50_incident_questions.py --live

# Print SQL without assertions
python3 test/test_50_incident_questions.py --sql-only

# Against remote server
API_URL=http://34.126.131.59:8000 python3 test/test_50_incident_questions.py

# One-off curl
curl -s -X POST http://localhost:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "How many open incidents are there?",
    "context": {},
    "sql": {"dialect": "redshift", "tables": []},
    "execution": {"dry_run": true, "max_rows": 100, "redshift_target": "incident"},
    "model": {"max_tokens": 300},
    "trace": {"source": "manual"}
  }' | python3 -m json.tool
```

---

## Demo Flow

**Quick (5 questions):**
1. I02 — "How many open incidents are there?" → metric
2. I07 — "How many critical severity incidents are there?" → metric
3. IB01 — "Show incident count by status" → bar
4. IB03 — "Show incident count by category" → bar
5. ID01 — "Show the monthly incident trend" → line

**Extended (10 questions):**
1. I01 — Total count KPI
2. I02 — Open incidents
3. I07 — Critical count
4. IF01 — High severity + open combined filter
5. IB01 — By status (bar)
6. IB02 — By severity (bar)
7. IB03 — By category (bar)
8. ID01 — Monthly trend (line)
9. IE02 — Average cost by category (bar)
10. IG01 — % completed (metric)

**Narrative arc:** KPI snapshot → severity/status breakdown → category distribution → time trends → cost analysis

---

> Maintenance order questions: see `DEMO_QUESTIONS_MAINTENANCE.md`
