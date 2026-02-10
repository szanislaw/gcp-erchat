# Column-Based Display Type Questions

## Overview
This document contains hardcoded display type questions based on **actual column names** from the `incident_combine` table in AWS Athena.

## Table Schema

### incident_combine
**Columns:**
- `snapshotdate` (string) - Snapshot date of the incident
- `group_name` (string) - Group name
- `account_uuid` (string) - Account identifier
- `property_name` (string) - Property name
- `recovery_uuid` (string) - Recovery identifier
- `recovery_no` (string) - Recovery number
- `category_name` (string) - Incident category (e.g., Housekeeping, F&B)
- `incident_name` (string) - Incident name/title
- `profile_name` (string) - Profile name
- `department_name` (string) - Department responsible
- `severity_name` (string) - Severity level (High, Medium, Low)
- `mapping_uuid` (string) - Mapping identifier
- `compensation_text` (string) - Compensation details
- `potential_cost` (decimal) - Estimated potential cost
- `actual_cost` (decimal) - Actual incurred cost
- `status_name` (string) - Status (Pending, Completed, Cancelled)
- `location_name` (string) - Location of incident
- `vip` (string) - VIP flag
- `temperament_text` (string) - Guest temperament description
- `description` (string) - Incident description
- `created_date` (bigint) - Unix timestamp when created
- `incident_time` (bigint) - Unix timestamp of incident occurrence
- `completed_date` (bigint) - Unix timestamp when completed
- `cancelled_date` (int) - Unix timestamp when cancelled

**Partitions:** account, property, date

---

## Display Type Categories

### 1. TABLE Display (10 questions)
**Use Case:** Detailed rows with multiple columns - best for browsing specific records

1. Show me all incidents with their category and severity
2. List all incidents with department and status
3. Show me incidents with compensation text and actual cost
4. Display all vip incidents with location and description
5. Show incidents from housekeeping department
6. List all pending incidents with recovery number
7. Show me all incidents from the peninsula property
8. Display incidents with potential cost over 100
9. Show me all high severity incidents with their location
10. List incidents by profile name and temperament

**Expected SQL Pattern:**
```sql
SELECT category_name, severity_name, department_name, status_name, ...
FROM incident_combine
WHERE [filter conditions]
```

---

### 2. METRIC Display (8 questions)
**Use Case:** Single KPI values - COUNT, SUM, AVG without GROUP BY

1. What is the total incident count
2. How many incidents are there in the system
3. What is the total potential cost of all incidents
4. What is the average actual cost per incident
5. How many vip incidents do we have
6. What is the total compensation amount
7. Count all incidents with severity high
8. How many completed incidents are there

**Expected SQL Pattern:**
```sql
SELECT COUNT(*) FROM incident_combine
SELECT SUM(actual_cost) FROM incident_combine
SELECT AVG(potential_cost) FROM incident_combine WHERE severity_name = 'High'
```

---

### 3. BAR Chart Display (10 questions)
**Use Case:** Category comparisons using actual column names (5-50 categories)

1. Show incident count by category name
2. Count incidents by department name
3. Show incidents grouped by severity name
4. Display incident breakdown by location name
5. Show incident count by property name
6. Count incidents by profile name
7. Show actual cost by department name
8. Display potential cost by category name
9. Show average cost by severity name
10. Count incidents by status name

**Expected SQL Pattern:**
```sql
SELECT category_name, COUNT(*) as count
FROM incident_combine
GROUP BY category_name
ORDER BY count DESC
```

---

### 4. PIE Chart Display (6 questions)
**Use Case:** Distribution breakdown with 2-10 categories

1. Show status name distribution
2. Display severity name breakdown
3. Show vip vs non-vip incident distribution
4. Incident percentage by status name
5. Show completed vs pending vs cancelled breakdown
6. Display incident distribution by temperament text

**Expected SQL Pattern:**
```sql
SELECT status_name, COUNT(*) as count
FROM incident_combine
GROUP BY status_name
```

---

### 5. LINE Chart Display (7 questions)
**Use Case:** Time series trends using date columns

1. Show incident trend by created date
2. Display daily incident count from snapshotdate
3. Show incident completion trend by completed date
4. Count incidents per day for last 30 days
5. Display incident time series by date partition
6. Show weekly incident count trend
7. Display monthly incident count by created date

**Expected SQL Pattern:**
```sql
SELECT DATE(FROM_UNIXTIME(created_date)) as date, COUNT(*) as count
FROM incident_combine
GROUP BY DATE(FROM_UNIXTIME(created_date))
ORDER BY date
```

---

## Implementation

All these questions are hardcoded in `app/display_hint.py` in the `QUERY_DISPLAY_TYPE_MAP` dictionary.

**Mapping Priority:**
1. Exact match in `QUERY_DISPLAY_TYPE_MAP` (highest priority)
2. Pattern matching via regex
3. SQL structure analysis (fallback)

---

## Testing

Run the automated test script:
```bash
./test/test_column_based_display.sh
```

Or test individual questions:
```bash
curl -X POST http://localhost:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Show incident count by category name",
    "context": {
        "language": "en",
        "property_uuid": "",
        "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false}
  }'
```

---

## Display Type Distribution

- **TABLE:** 10 questions (detailed record browsing)
- **METRIC:** 8 questions (single KPI values)
- **BAR:** 10 questions (category comparisons)
- **PIE:** 6 questions (distribution breakdown)
- **LINE:** 7 questions (time series trends)

**Total:** 41 hardcoded display type mappings using actual column names
