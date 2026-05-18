# Demo Questions — Maintenance Order Analytics

## System Workflow

```
┌────────────────────────────────────────────────────────────────────┐
│                   USER INPUT (Natural Language)                     │
│          "How many open high priority orders are there?"            │
└────────────────────────────┬───────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│              NLQ API  (localhost:8000/nlq/execute)                  │
│  1. Validate & sanitize input text                                  │
│  2. Rate limit check (2 req/s, burst 10)                            │
│  3. Resolve Redshift target → "default"                             │
│  4. Build prompt (schema DDL + FK rules + examples)                 │
│  5. SQLCoder-7b-2 inference (GPU, 4-bit quantized)                  │
│  6. Post-process SQL (12 fixers)                                    │
│  7. Validate SQL (allowlist, forbidden ops)                         │
│  8. Execute on Amazon Redshift Serverless                           │
│  9. Detect display type → table / metric / bar / pie / line         │
│ 10. Return results + chart_data                                     │
└────────────────────────────┬───────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│                    GENERATED SQL EXAMPLE                            │
│                                                                     │
│  SELECT COUNT(*) FROM maintenance_order m                           │
│  JOIN master_maintenance_status s ON m.status = s.status_id         │
│  JOIN master_job_priority p      ON m.priority = p.priority_id      │
│  WHERE s.status_name = 'Open'                                       │
│    AND p.priority_name = 'High'                                     │
│  LIMIT 100                                                          │
└────────────────────────────────────────────────────────────────────┘
```

## Key Schema

| Table | Role |
|-------|------|
| `maintenance_order` | Main fact table (status/priority as FK integers) |
| `master_maintenance_status` | Lookup: status_id → status_name |
| `master_job_priority` | Lookup: priority_id → priority_name |
| `department` | Lookup: department_uuid → department_name |
| `property_location` | Lookup: location_uuid → location_name |

**FK pattern every query must follow:**
- `m.status  (SMALLINT) → master_maintenance_status.status_id → s.status_name`
- `m.priority (SMALLINT) → master_job_priority.priority_id    → p.priority_name`

---

## Display Type Decision Flow

```
Natural Language Query
        │
        ▼
┌─────────────────────────┐
│  Hardcoded map          │──HIT──► return mapped type
│  (60 known questions)   │
└────────────┬────────────┘
             │ MISS
             ▼
┌─────────────────────────┐
│  Regex patterns         │──MATCH──► "how many" → metric
│  on question text       │          "by department" → bar
└────────────┬────────────┘          "trend" → line
             │ NO MATCH              "distribution" → pie
             ▼                       "show/list" → table
┌─────────────────────────┐
│  SQL analysis fallback  │──► single value → metric
│  (after generation)     │──► GROUP BY + count → bar/pie
│                         │──► GROUP BY date → line
└─────────────────────────┘──► SELECT * / listing → table
```

---

## Overview

**39 evaluation questions across 8 categories — 37/39 (94%) pass rate**

| Category | Count | Pass | Notes |
|----------|-------|------|-------|
| simple_count | 7 | 7/7 | 100% |
| date_filter | 7 | 7/7 | 100% |
| department | 5 | 5/5 | 100% |
| location | 2 | 2/2 | 100% |
| aggregation | 4 | 4/4 | 100% |
| trend | 4 | 4/4 | 100% |
| group_by | 5 | 4/5 | C03 `cume_dist()` hallucination |
| hallucination_guard | 5 | 4/5 | H02 three-way JOIN beyond 7B limit |

---

## METRIC — Simple Counts (S01–S07)

### S01. How many total maintenance orders are there?
**Display:** metric  
**SQL shape:** `SELECT COUNT(*) FROM maintenance_order`

### S02. How many maintenance orders are currently open?
**Display:** metric  
**SQL shape:** `... JOIN master_maintenance_status ... WHERE s.status_name = 'Open'`

### S03. How many maintenance orders have been completed?
**Display:** metric  
**SQL shape:** `... WHERE s.status_name = 'Completed'`

### S04. How many maintenance orders are cancelled?
**Display:** metric  
**SQL shape:** `... WHERE s.status_name = 'Cancelled'`

### S05. How many high priority maintenance orders are there?
**Display:** metric  
**SQL shape:** `... JOIN master_job_priority ... WHERE p.priority_name = 'High'`

### S06. How many low priority maintenance orders exist?
**Display:** metric  
**SQL shape:** `... WHERE p.priority_name = 'Low'`

### S07. How many urgent maintenance orders are there?
**Display:** metric  
**SQL shape:** `... WHERE p.priority_name = 'Urgent'`

---

## BAR — Department Breakdown (D01–D05)

### D01. Show maintenance order count grouped by department
**Display:** bar  
**SQL shape:** `SELECT d.department_name, COUNT(*) ... JOIN department d ... GROUP BY d.department_name`

### D02. Which department has the most maintenance orders?
**Display:** metric / bar  
**SQL shape:** `... GROUP BY d.department_name ORDER BY COUNT(*) DESC LIMIT 1`

### D03. How many open orders does each department have?
**Display:** bar  
**SQL shape:** `... WHERE s.status_name = 'Open' GROUP BY d.department_name`

### D04. Which departments have high priority maintenance orders?
**Display:** bar / table  
**SQL shape:** `... WHERE p.priority_name = 'High' GROUP BY d.department_name`

### D05. Show top 5 departments by number of maintenance orders
**Display:** bar  
**SQL shape:** `... GROUP BY d.department_name ORDER BY COUNT(*) DESC LIMIT 5`

---

## BAR/PIE — Group By (G01–G05)

### G01. Show maintenance order count by status
**Display:** bar  
**SQL shape:** `SELECT s.status_name, COUNT(*) ... GROUP BY s.status_name`

### G02. Show maintenance order count by priority
**Display:** bar  
**SQL shape:** `SELECT p.priority_name, COUNT(*) ... GROUP BY p.priority_name`

### G03. What is the distribution of maintenance orders by status and priority?
**Display:** table  
**SQL shape:** `SELECT s.status_name, p.priority_name, COUNT(*) ... GROUP BY s.status_name, p.priority_name`  
⚠️ Known failure: model hallucinates `cume_dist()` window function

### G04. Which status has the most maintenance orders?
**Display:** metric  
**SQL shape:** `... GROUP BY s.status_name ORDER BY COUNT(*) DESC LIMIT 1`

### G05. Show high priority open maintenance orders
**Display:** table  
**SQL shape:** `SELECT m.maintenance_no, m.created_date ... WHERE s.status_name = 'Open' AND p.priority_name = 'High'`

---

## METRIC — Date Filters (F01–F07)

### F01. How many maintenance orders were created this month?
**Display:** metric  
**SQL shape:** `... WHERE m.created_date >= DATE_TRUNC('month', CURRENT_DATE)`

### F02. How many maintenance orders were created this week?
**Display:** metric  
**SQL shape:** `... WHERE m.created_date >= DATE_TRUNC('week', CURRENT_DATE)`

### F03. Show maintenance orders created in the last 30 days
**Display:** table  
**SQL shape:** `... WHERE m.created_date >= DATEADD(day, -30, CURRENT_DATE)`

### F04. How many maintenance orders were created last week?
**Display:** metric  
**SQL shape:** `... WHERE m.created_date >= DATEADD(week, -1, DATE_TRUNC('week', CURRENT_DATE)) AND m.created_date < DATE_TRUNC('week', CURRENT_DATE)`

### F05. How many maintenance orders were completed this year?
**Display:** metric  
**SQL shape:** `... WHERE EXTRACT(YEAR FROM m.completed_date) = EXTRACT(YEAR FROM CURRENT_DATE)`

### F06. Show orders created in the last 7 days
**Display:** table  
**SQL shape:** `... WHERE m.created_date >= DATEADD(day, -7, CURRENT_DATE)`

### F07. How many maintenance orders were cancelled last month?
**Display:** metric  
**SQL shape:** `... WHERE m.cancelled_date >= DATEADD(month, -1, DATE_TRUNC('month', CURRENT_DATE)) AND m.cancelled_date < DATE_TRUNC('month', CURRENT_DATE)`

---

## LINE — Trends (T01–T04)

### T01. Show the monthly trend of maintenance orders created
**Display:** line  
**SQL shape:** `SELECT DATE_TRUNC('month', m.created_date) AS month, COUNT(*) ... GROUP BY 1 ORDER BY 1`

### T02. Show weekly maintenance order trend for this year
**Display:** line  
**SQL shape:** `SELECT DATE_TRUNC('week', m.created_date) AS week, COUNT(*) ... WHERE EXTRACT(YEAR FROM ...) = CURRENT_YEAR GROUP BY 1 ORDER BY 1`

### T03. How many maintenance orders were created each day this month?
**Display:** line  
**SQL shape:** `SELECT DATE_TRUNC('day', m.created_date) AS day, COUNT(*) ... WHERE created_date >= DATE_TRUNC('month', CURRENT_DATE) GROUP BY 1 ORDER BY 1`

### T04. Show trend of high priority orders by month
**Display:** line  
**SQL shape:** `SELECT DATE_TRUNC('month', ...) AS month, COUNT(*) ... WHERE p.priority_name = 'High' GROUP BY 1 ORDER BY 1`

---

## BAR — Location (L01–L02)

### L01. Show maintenance order count by location
**Display:** bar  
**SQL shape:** `SELECT pl.location_name, COUNT(*) ... JOIN property_location pl ON m.location_uuid = pl.location_uuid GROUP BY pl.location_name`

### L02. Which location has the most maintenance orders?
**Display:** metric  
**SQL shape:** `... GROUP BY pl.location_name ORDER BY COUNT(*) DESC LIMIT 1`

---

## Advanced Aggregation (A01–A04)

### A01. What percentage of maintenance orders are completed?
**Display:** metric  
**SQL shape:** `SELECT CAST(COUNT(CASE WHEN s.status_name = 'Completed' THEN 1 END) AS FLOAT) * 100.0 / NULLIF(COUNT(*), 0) ...`

### A02. What is the most common maintenance order type?
**Display:** metric  
**SQL shape:** `SELECT m.type, COUNT(*) ... GROUP BY m.type ORDER BY COUNT(*) DESC LIMIT 1`

### A03. Show the 10 most recent maintenance orders
**Display:** table  
**SQL shape:** `SELECT m.maintenance_no, m.created_date ... ORDER BY m.created_date DESC LIMIT 10`

### A04. How many maintenance orders were created vs completed this month?
**Display:** metric  
**SQL shape:** `SELECT COUNT(CASE WHEN m.created_date >= DATE_TRUNC('month', CURRENT_DATE) THEN 1 END) AS created_count, COUNT(CASE WHEN m.completed_date >= DATE_TRUNC('month', CURRENT_DATE) THEN 1 END) AS completed_count FROM maintenance_order`

---

## Hallucination Guards (H01–H05)

### H01. Show all maintenance orders for the housekeeping department
**Display:** table  
**SQL shape:** `... JOIN department d ... WHERE d.department_name = 'Housekeeping'`  
✅ Tests: no raw integer status filters; correct department JOIN

### H02. How many open high priority orders are in the engineering department?
**Display:** metric  
**SQL shape:** three-way JOIN: status + priority + department  
⚠️ Known failure: 7B model frequently drops JOINs, uses raw `m.status = 1`

### H03. Show maintenance orders created this month by department
**Display:** bar  
**SQL shape:** `... JOIN department d ... WHERE created_date >= DATE_TRUNC('month', CURRENT_DATE) GROUP BY d.department_name`

### H04. What are the most recent 5 completed maintenance orders?
**Display:** table  
**SQL shape:** `... WHERE s.status_name = 'Completed' ORDER BY m.created_date DESC LIMIT 5`

### H05. Show cancelled orders from last month grouped by priority
**Display:** bar  
**SQL shape:** `... WHERE cancelled_date in last month range ... GROUP BY p.priority_name`

---

## Testing Commands

```bash
# Run full eval suite (dry-run, fast)
python3 test/eval_maintenance.py --dry-run

# Run specific category
python3 test/eval_maintenance.py --category simple_count

# Run single question
python3 test/eval_maintenance.py --id S02 --verbose

# Run against remote server
API_URL=http://34.126.131.59:8000 python3 test/eval_maintenance.py --dry-run

# One-off curl test
curl -s -X POST http://localhost:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "How many open high priority orders are there?",
    "context": {"property_uuid": null, "language": "en"},
    "sql": {"dialect": "redshift"},
    "execution": {"dry_run": false, "max_rows": 100, "redshift_target": "default"},
    "model": {"max_tokens": 256},
    "trace": {"source": "manual"}
  }' | python3 -m json.tool
```

---

## Demo Flow Recommendations

**Quick Demo (5 questions):**
1. **METRIC** — S02: "How many maintenance orders are currently open?"
2. **METRIC** — S05: "How many high priority maintenance orders are there?"
3. **BAR** — G01: "Show maintenance order count by status"
4. **BAR** — D01: "Show maintenance order count grouped by department"
5. **LINE** — T01: "Show the monthly trend of maintenance orders created"

**Extended Demo (10 questions):**
1. S01 — Total count KPI
2. S02 — Open orders count
3. S05 — High priority count
4. G05 — List high priority open orders (table)
5. G01 — Count by status (bar)
6. G02 — Count by priority (bar)
7. D01 — Count by department (bar)
8. D03 — Open orders per department (bar)
9. T01 — Monthly trend (line)
10. A04 — Created vs completed this month (metric)

**Narrative arc:** KPI snapshot → priority/status breakdown → department distribution → time trends

---

# Incident Report Analytics (`redshift_target: incident`)

**50 questions — 50/50 (100%) pass rate**

## Schema

`mv_recovery_all` is a **flat, pre-joined view**. No JOINs required — query it directly.

| Column | Type | Notes |
|--------|------|-------|
| `recovery_no` | VARCHAR | Incident report ID |
| `status_name` | VARCHAR | `pending`, `draft`, `completed`, `cancelled` |
| `severity_name` | VARCHAR | `critical`, `high`, `medium`, `low` |
| `department_name` | VARCHAR | Pre-joined, use directly |
| `incident_name` | VARCHAR | Type of incident |
| `category_name` | VARCHAR | Incident category |
| `location_name` | VARCHAR | Property location, pre-joined |
| `temperament_text` | VARCHAR | Guest temperament (Angry, Calm, etc.) |
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
- "resolved/closed/done" → `status_name = 'completed'`
- Always lowercase — never `'Completed'` or `'PENDING'`

---

## METRIC — Simple Counts (I01–I08)

### I01. How many total incidents are there?
**Display:** metric  
**SQL shape:** `SELECT COUNT(*) FROM mv_recovery_all LIMIT 100`

### I02. How many open incidents are there?
**Display:** metric  
**SQL shape:** `SELECT COUNT(*) FROM mv_recovery_all WHERE status_name IN ('pending', 'draft') LIMIT 100`

### I03. How many completed incidents?
**Display:** metric  
**SQL shape:** `SELECT COUNT(*) FROM mv_recovery_all WHERE status_name = 'completed' LIMIT 100`

### I04. How many cancelled incidents?
**Display:** metric  
**SQL shape:** `SELECT COUNT(*) FROM mv_recovery_all WHERE status_name = 'cancelled' LIMIT 100`

### I05. How many draft incidents are there?
**Display:** metric  
**SQL shape:** `SELECT COUNT(*) FROM mv_recovery_all WHERE status_name = 'draft' LIMIT 100`

### I06. How many high severity incidents?
**Display:** metric  
**SQL shape:** `SELECT COUNT(*) FROM mv_recovery_all WHERE severity_name = 'high' LIMIT 100`

### I07. How many critical severity incidents are there?
**Display:** metric  
**SQL shape:** `SELECT COUNT(*) FROM mv_recovery_all WHERE severity_name = 'critical' LIMIT 100`

### I08. How many pending incidents?
**Display:** metric  
**SQL shape:** `SELECT COUNT(*) FROM mv_recovery_all WHERE status_name IN ('pending', 'draft') LIMIT 100`

---

## BAR — Group By Breakdowns (IB01–IB08)

### IB01. Show incident count by status
**Display:** bar  
**SQL shape:** `SELECT status_name, COUNT(*) FROM mv_recovery_all GROUP BY status_name ORDER BY COUNT(*) DESC LIMIT 100`

### IB02. Show incident count by severity
**Display:** bar  
**SQL shape:** `SELECT severity_name, COUNT(*) FROM mv_recovery_all GROUP BY severity_name ORDER BY COUNT(*) DESC LIMIT 100`

### IB03. Show incident count by category
**Display:** bar  
**SQL shape:** `SELECT category_name, COUNT(*) FROM mv_recovery_all GROUP BY category_name ORDER BY COUNT(*) DESC LIMIT 100`

### IB04. Show incident count by department
**Display:** bar  
**SQL shape:** `SELECT department_name, COUNT(*) FROM mv_recovery_all GROUP BY department_name ORDER BY COUNT(*) DESC LIMIT 100`

### IB05. Which category has the most incidents?
**Display:** metric  
**SQL shape:** `SELECT category_name, COUNT(*) FROM mv_recovery_all GROUP BY category_name ORDER BY COUNT(*) DESC LIMIT 1`

### IB06. Which department has the most incidents?
**Display:** metric  
**SQL shape:** `SELECT department_name, COUNT(*) FROM mv_recovery_all GROUP BY department_name ORDER BY COUNT(*) DESC LIMIT 1`

### IB07. Show incident count by location
**Display:** bar  
**SQL shape:** `SELECT location_name, COUNT(*) FROM mv_recovery_all GROUP BY location_name ORDER BY COUNT(*) DESC LIMIT 100`

### IB08. Show top 5 incident categories
**Display:** bar  
**SQL shape:** `SELECT category_name, COUNT(*) FROM mv_recovery_all GROUP BY category_name ORDER BY COUNT(*) DESC LIMIT 5`

---

## METRIC — Date Filters (IC01–IC08)

### IC01. How many incidents were created this month?
**Display:** metric  
**SQL shape:** `SELECT COUNT(*) FROM mv_recovery_all WHERE created_date >= DATE_TRUNC('month', CURRENT_DATE) LIMIT 100`

### IC02. How many incidents were created this year?
**Display:** metric  
**SQL shape:** `SELECT COUNT(*) FROM mv_recovery_all WHERE EXTRACT(YEAR FROM created_date) = EXTRACT(YEAR FROM CURRENT_DATE) LIMIT 100`

### IC03. How many incidents were created this week?
**Display:** metric  
**SQL shape:** `SELECT COUNT(*) FROM mv_recovery_all WHERE created_date >= DATE_TRUNC('week', CURRENT_DATE) LIMIT 100`

### IC04. How many incidents were created last month?
**Display:** metric  
**SQL shape:** `SELECT COUNT(*) FROM mv_recovery_all WHERE created_date >= DATEADD(month, -1, DATE_TRUNC('month', CURRENT_DATE)) AND created_date < DATE_TRUNC('month', CURRENT_DATE) LIMIT 100`

### IC05. How many incidents were created last week?
**Display:** metric  
**SQL shape:** `SELECT COUNT(*) FROM mv_recovery_all WHERE created_date >= DATEADD(week, -1, DATE_TRUNC('week', CURRENT_DATE)) AND created_date < DATE_TRUNC('week', CURRENT_DATE) LIMIT 100`

### IC06. How many incidents were created in the last 30 days?
**Display:** metric  
**SQL shape:** `SELECT COUNT(*) FROM mv_recovery_all WHERE created_date >= DATEADD(day, -30, CURRENT_DATE) LIMIT 100`

### IC07. How many incidents were completed this month?
**Display:** metric  
**SQL shape:** `SELECT COUNT(*) FROM mv_recovery_all WHERE status_name = 'completed' AND DATE_TRUNC('month', created_date) = DATE_TRUNC('month', CURRENT_DATE) LIMIT 100`

### IC08. How many incidents were created in the last 7 days?
**Display:** metric  
**SQL shape:** `SELECT COUNT(*) FROM mv_recovery_all WHERE created_date >= DATEADD(day, -7, CURRENT_DATE) LIMIT 100`

---

## LINE — Trend Analysis (ID01–ID06)

### ID01. Show the monthly incident trend
**Display:** line  
**SQL shape:** `SELECT DATE_TRUNC('month', created_date) AS month, COUNT(*) AS incidents FROM mv_recovery_all GROUP BY 1 ORDER BY 1 LIMIT 100`

### ID02. Show the weekly incident trend for this year
**Display:** line  
**SQL shape:** `SELECT DATE_TRUNC('week', created_date) AS week, COUNT(*) AS incidents FROM mv_recovery_all WHERE EXTRACT(YEAR FROM created_date) = EXTRACT(YEAR FROM CURRENT_DATE) GROUP BY 1 ORDER BY 1 LIMIT 100`

### ID03. Show the daily incident trend this month
**Display:** line  
**SQL shape:** `SELECT DATE_TRUNC('day', created_date) AS day, COUNT(*) AS incidents FROM mv_recovery_all WHERE created_date >= DATE_TRUNC('month', CURRENT_DATE) GROUP BY 1 ORDER BY 1 LIMIT 100`

### ID04. Show monthly trend of completed incidents
**Display:** line  
**SQL shape:** `SELECT DATE_TRUNC('month', created_date) AS month, COUNT(*) FROM mv_recovery_all WHERE status_name = 'completed' GROUP BY 1 ORDER BY 1 LIMIT 100`

### ID05. Show monthly incident count by severity
**Display:** line / bar  
**SQL shape:** `SELECT DATE_TRUNC('month', created_date) AS month, severity_name, COUNT(*) FROM mv_recovery_all GROUP BY 1, 2 ORDER BY 1 LIMIT 100`

### ID06. Show weekly trend of open incidents
**Display:** line  
**SQL shape:** `SELECT DATE_TRUNC('week', created_date) AS week, COUNT(*) FROM mv_recovery_all WHERE status_name IN ('pending', 'draft') GROUP BY 1 ORDER BY 1 LIMIT 100`

---

## BAR — Cost Analysis (IE01–IE05)

### IE01. What is the average actual cost per incident?
**Display:** metric  
**SQL shape:** `SELECT AVG(actual_cost) FROM mv_recovery_all WHERE actual_cost > 0 LIMIT 100`

### IE02. Show average cost by category
**Display:** bar  
**SQL shape:** `SELECT category_name, AVG(actual_cost) AS avg_cost FROM mv_recovery_all WHERE actual_cost > 0 GROUP BY category_name ORDER BY avg_cost DESC LIMIT 100`

### IE03. Show average cost by severity
**Display:** bar  
**SQL shape:** `SELECT severity_name, AVG(actual_cost) AS avg_cost FROM mv_recovery_all WHERE actual_cost > 0 GROUP BY severity_name ORDER BY avg_cost DESC LIMIT 100`

### IE04. What is the total actual cost of all incidents?
**Display:** metric  
**SQL shape:** `SELECT SUM(actual_cost) FROM mv_recovery_all WHERE actual_cost > 0 LIMIT 100`

### IE05. Show top 5 categories by average cost
**Display:** bar  
**SQL shape:** `SELECT category_name, AVG(actual_cost) AS avg_cost FROM mv_recovery_all WHERE actual_cost > 0 GROUP BY category_name ORDER BY avg_cost DESC LIMIT 5`

---

## METRIC — Combined Filters (IF01–IF06)

### IF01. How many high severity open incidents are there?
**Display:** metric  
**SQL shape:** `SELECT COUNT(*) FROM mv_recovery_all WHERE severity_name = 'high' AND status_name IN ('pending', 'draft') LIMIT 100`

### IF02. How many critical incidents are pending?
**Display:** metric  
**SQL shape:** `SELECT COUNT(*) FROM mv_recovery_all WHERE severity_name = 'critical' AND status_name = 'pending' LIMIT 100`

### IF03. How many completed high severity incidents are there?
**Display:** metric  
**SQL shape:** `SELECT COUNT(*) FROM mv_recovery_all WHERE severity_name = 'high' AND status_name = 'completed' LIMIT 100`

### IF04. How many VIP guest incidents are there?
**Display:** metric  
**SQL shape:** `SELECT COUNT(*) FROM mv_recovery_all WHERE vip IS NOT NULL AND vip != '' LIMIT 100`

### IF05. How many high severity incidents were created this month?
**Display:** metric  
**SQL shape:** `SELECT COUNT(*) FROM mv_recovery_all WHERE severity_name = 'high' AND created_date >= DATE_TRUNC('month', CURRENT_DATE) LIMIT 100`

### IF06. How many open critical incidents are there?
**Display:** metric  
**SQL shape:** `SELECT COUNT(*) FROM mv_recovery_all WHERE severity_name = 'critical' AND status_name IN ('pending', 'draft') LIMIT 100`

---

## METRIC — Percentages (IG01–IG04)

### IG01. What percentage of incidents are completed?
**Display:** metric  
**SQL shape:** `SELECT CAST(COUNT(CASE WHEN status_name = 'completed' THEN 1 END) AS FLOAT) * 100.0 / NULLIF(COUNT(*), 0) AS pct_completed FROM mv_recovery_all LIMIT 100`

### IG02. What percentage of incidents are open?
**Display:** metric  
**SQL shape:** `SELECT CAST(COUNT(CASE WHEN status_name IN ('pending', 'draft') THEN 1 END) AS FLOAT) * 100.0 / NULLIF(COUNT(*), 0) AS pct_open FROM mv_recovery_all LIMIT 100`

### IG03. What percentage of incidents are high or critical severity?
**Display:** metric  
**SQL shape:** `SELECT CAST(COUNT(CASE WHEN severity_name IN ('high', 'critical') THEN 1 END) AS FLOAT) * 100.0 / NULLIF(COUNT(*), 0) AS pct_high_critical FROM mv_recovery_all LIMIT 100`

### IG04. What percentage of incidents created this month are completed?
**Display:** metric  
**SQL shape:** `SELECT CAST(COUNT(CASE WHEN status_name = 'completed' THEN 1 END) AS FLOAT) * 100.0 / NULLIF(COUNT(*), 0) FROM mv_recovery_all WHERE created_date >= DATE_TRUNC('month', CURRENT_DATE) LIMIT 100`

---

## TABLE — Listings (IH01–IH05)

### IH01. Show the 10 most recent incidents
**Display:** table  
**SQL shape:** `SELECT recovery_no, incident_name, status_name, severity_name, created_date FROM mv_recovery_all ORDER BY created_date DESC LIMIT 10`

### IH02. Show the 5 most recent completed incidents
**Display:** table  
**SQL shape:** `SELECT recovery_no, incident_name, department_name, created_date FROM mv_recovery_all WHERE status_name = 'completed' ORDER BY created_date DESC LIMIT 5`

### IH03. Show recent high severity incidents
**Display:** table  
**SQL shape:** `SELECT recovery_no, incident_name, department_name, created_date FROM mv_recovery_all WHERE severity_name = 'high' ORDER BY created_date DESC LIMIT 100`

### IH04. Show recent incidents with their categories and status
**Display:** table  
**SQL shape:** `SELECT recovery_no, incident_name, category_name, status_name, created_date FROM mv_recovery_all ORDER BY created_date DESC LIMIT 100`

### IH05. Show the most recent VIP guest incidents
**Display:** table  
**SQL shape:** `SELECT recovery_no, incident_name, status_name, created_date FROM mv_recovery_all WHERE vip IS NOT NULL AND vip != '' ORDER BY created_date DESC LIMIT 100`

---

## Testing Commands

```bash
# Run full 50-question incident test (dry-run, fast)
python3 test/test_50_incident_questions.py

# Run with live Redshift execution
python3 test/test_50_incident_questions.py --live

# Print SQL for all questions (no assertions)
python3 test/test_50_incident_questions.py --sql-only

# Against remote server
API_URL=http://34.126.131.59:8000 python3 test/test_50_incident_questions.py

# One-off dry-run curl
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

## Demo Flow (Incident Reports)

**Quick Demo (5 questions):**
1. **METRIC** — I02: "How many open incidents are there?"
2. **METRIC** — I07: "How many critical severity incidents are there?"
3. **BAR** — IB01: "Show incident count by status"
4. **BAR** — IB03: "Show incident count by category"
5. **LINE** — ID01: "Show the monthly incident trend"

**Extended Demo (10 questions):**
1. I01 — Total incident count KPI
2. I02 — Open incidents count
3. I07 — Critical severity count
4. IF01 — High severity open incidents
5. IB01 — Count by status (bar)
6. IB02 — Count by severity (bar)
7. IB03 — Count by category (bar)
8. ID01 — Monthly trend (line)
9. IE02 — Average cost by category (bar)
10. IG01 — Percentage completed (metric)

**Narrative arc:** KPI snapshot → severity/status breakdown → category distribution → time trends → cost analysis
