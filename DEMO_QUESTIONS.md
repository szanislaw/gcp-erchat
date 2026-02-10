# Demo Questions - Hotel Incident Management

## System Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          USER INPUT (Natural Language)                   │
│                    "What is the total incident count?"                   │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    NLQ API (localhost:8000/nlq/execute)                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  1. Receive Request                                             │   │
│  │     - text: natural language query                              │   │
│  │     - context: property_uuid, account_uuid                      │   │
│  │     - sql: dialect (athena)                                     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              DISPLAY TYPE DETECTION (app/display_hint.py)                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Priority 1: Hardcoded Mapping (QUERY_DISPLAY_TYPE_MAP)        │   │
│  │  └─ Check if question matches exact string in map              │   │
│  │  └─ Return: table | metric | bar | pie | line                  │   │
│  │                                                                  │   │
│  │  Priority 2: Pattern Matching (Regex)                          │   │
│  │  └─ Match patterns: "how many", "by category", "trend"         │   │
│  │  └─ Return appropriate display type                            │   │
│  │                                                                  │   │
│  │  Priority 3: SQL Analysis (Fallback)                           │   │
│  │  └─ Analyze GROUP BY, aggregation, time series                 │   │
│  │  └─ Default to "table" if uncertain                            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    SQL GENERATION (app/sqlcoder.py)                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  2. Load Schema from AWS Glue                                   │   │
│  │     - Table: incident_combine                                   │   │
│  │     - Columns: category_name, severity_name, actual_cost, etc.  │   │
│  │                                                                  │   │
│  │  3. Generate SQL Query                                          │   │
│  │     - Apply property_uuid filter (partition)                    │   │
│  │     - Build appropriate aggregations                            │   │
│  │     - Output: SELECT COUNT(*) FROM incident_combine WHERE...    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  QUERY EXECUTION (app/athena_client.py)                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  4. Execute on AWS Athena                                       │   │
│  │     - Database: peninsula-incident2                             │   │
│  │     - Region: us-west-2                                         │   │
│  │     - S3 Results: s3://athena-query-results-peninsula/          │   │
│  │                                                                  │   │
│  │  5. Validate Results                                            │   │
│  │     - Security check (SQL injection prevention)                 │   │
│  │     - Table allowlist validation                                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   RESPONSE FORMATTING (app/main.py)                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  6. Build Response Payload                                      │   │
│  │     {                                                            │   │
│  │       "display": {                                              │   │
│  │         "type": "metric",                                       │   │
│  │         "chart_data": {...}  // For bar/pie/line only          │   │
│  │       },                                                         │   │
│  │       "execution": {                                            │   │
│  │         "columns": ["count"],                                   │   │
│  │         "rows": [{"count": 12548}]                              │   │
│  │       },                                                         │   │
│  │       "query": "SELECT COUNT(*) FROM incident_combine..."       │   │
│  │     }                                                            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND RENDERING                                │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐         │
│  │   TABLE      │   METRIC     │   BAR CHART  │   PIE CHART  │         │
│  │  ┌────────┐  │  ┌────────┐  │  ┌────────┐  │  ┌────────┐  │         │
│  │  │ Row 1  │  │  │ 12,548 │  │  │   ███   │  │  │   ◕    │  │         │
│  │  │ Row 2  │  │  │ Total  │  │  │   ███   │  │  │  ◕◕◕   │  │         │
│  │  │ Row 3  │  │  │Incident│  │  │   ██    │  │  │ ◕◕     │  │         │
│  │  │  ...   │  │  │        │  │  │   █     │  │  │        │  │         │
│  │  └────────┘  │  └────────┘  │  └────────┘  │  └────────┘  │         │
│  └──────────────┴──────────────┴──────────────┴──────────────┘         │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────┐          │
│  │                    LINE CHART                             │          │
│  │  ┌──────────────────────────────────────────────────────┐ │          │
│  │  │        /\      /\                                     │ │          │
│  │  │       /  \    /  \    /\                             │ │          │
│  │  │      /    \  /    \  /  \                            │ │          │
│  │  │─────────────────────────────────────────────────────│ │          │
│  │  └──────────────────────────────────────────────────────┘ │          │
│  └──────────────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Display Type Decision Flow

```
Natural Language Query
        │
        ▼
┌─────────────────────────┐
│ Normalize & lowercase   │
│ "what is the total..."  │
└───────────┬─────────────┘
            │
            ▼
   ┌────────────────────┐
   │ Check Hardcoded    │──YES──► Return "metric"
   │ QUERY_DISPLAY_MAP? │
   └────────┬───────────┘
            │ NO
            ▼
   ┌────────────────────┐
   │ Regex Pattern      │──MATCH──► "how many" → metric
   │ Matching?          │          "by category" → bar
   └────────┬───────────┘          "trend" → line
            │ NO MATCH              "distribution" → pie
            ▼                       "show me all" → table
   ┌────────────────────┐
   │ Wait for SQL       │
   │ Generation         │
   └────────┬───────────┘
            │
            ▼
   ┌────────────────────┐
   │ Analyze SQL:       │──► Single value → metric
   │ - Aggregations?    │──► GROUP BY + COUNT → bar/pie
   │ - GROUP BY?        │──► GROUP BY date → line
   │ - Time series?     │──► SELECT * → table
   └────────────────────┘
```

## Overview
20 demonstration questions showcasing all 5 display types using the `incident_combine` table from Athena.

**Display Type Distribution:**
- 4 TABLE displays (detailed records)
- 4 METRIC displays (KPI values)
- 4 BAR charts (category comparisons)
- 4 PIE charts (distribution breakdowns)
- 4 LINE charts (time series trends)

---

## TABLE Display (4 questions)

### 1. Show high severity incidents
**Purpose:** Browse critical incidents with location details  
**Expected Columns:** severity_name, location_name, category_name, status_name, description

### 2. Show incidents with compensation
**Purpose:** Review incidents requiring compensation by department  
**Expected Columns:** department_name, compensation_text, actual_cost, status_name, category_name

### 3. Show vip incidents
**Purpose:** Track VIP guest incidents for priority handling  
**Expected Columns:** vip, category_name, status_name, severity_name, location_name

### 4. Show housekeeping incidents
**Purpose:** Review housekeeping department incidents and costs  
**Expected Columns:** department_name, category_name, actual_cost, status_name, description

---

## METRIC Display (4 questions)

### 5. How many total incidents
**Purpose:** Overall incident volume KPI  
**Expected Result:** Single COUNT(*) value

### 6. What is the total cost
**Purpose:** Total financial impact of all incidents  
**Expected Result:** Single SUM(actual_cost) value

### 7. How many vip incidents
**Purpose:** VIP incident count for priority tracking  
**Expected Result:** Single COUNT(*) WHERE vip = 'Yes'

### 8. What is the average cost
**Purpose:** Average estimated cost for budgeting  
**Expected Result:** Single AVG(potential_cost) value

---

## BAR Chart Display (4 questions)

### 9. Count by category
**Purpose:** Compare incident volume across categories  
**Expected Result:** category_name with COUNT(*) grouped

### 10. Count by department
**Purpose:** Compare which departments have most incidents  
**Expected Result:** department_name with COUNT(*) grouped

### 11. Cost by severity
**Purpose:** Compare total costs across severity levels  
**Expected Result:** severity_name with SUM(actual_cost) grouped

### 12. Count by property
**Purpose:** Compare incident volume across properties  
**Expected Result:** property_name with COUNT(*) grouped

---

## PIE Chart Display (4 questions)

### 13. Status distribution
**Purpose:** See breakdown of pending/completed/cancelled incidents  
**Expected Result:** status_name with COUNT(*) grouped (2-5 categories)

### 14. Severity breakdown
**Purpose:** Distribution of high/medium/low severity incidents  
**Expected Result:** severity_name with COUNT(*) grouped (2-5 categories)

### 15. Vip percentage
**Purpose:** VIP vs non-VIP incident distribution  
**Expected Result:** vip with COUNT(*) grouped (2 categories)

### 16. Temperament distribution
**Purpose:** Guest temperament distribution (angry/calm/neutral)  
**Expected Result:** temperament_text with COUNT(*) grouped

---

## LINE Chart Display (4 questions)

### 17. Incident trend last 30 days
**Purpose:** Daily incident creation trend over past month  
**Expected Result:** date with COUNT(*) grouped by day

### 18. Daily incident count
**Purpose:** Daily snapshot of incident counts  
**Expected Result:** snapshotdate with COUNT(*) grouped by date

### 19. Completion trend
**Purpose:** Daily incident resolution trend  
**Expected Result:** completed_date with COUNT(*) grouped by day

### 20. Incidents per day
**Purpose:** When incidents actually occurred (time series)  
**Expected Result:** incident_time with COUNT(*) grouped by day

---

## Testing Command

```bash
curl -X POST http://localhost:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "How many total incidents",
    "context": {
        "language": "en",
        "property_uuid": "",
        "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false}
  }'
```

## Demo Flow Recommendation

1. Start with **METRIC** (#5) - "How many total incidents" - Opening KPI
2. Show **TABLE** (#1) - "Show high severity incidents" - Browse critical records
3. Show **BAR** (#9) - "Count by category" - Category comparison
4. Show **PIE** (#13) - "Status distribution" - Progress tracking
5. Show **LINE** (#17) - "Incident trend last 30 days" - Time series pattern
6. Continue through remaining questions alternating display types

This creates a narrative: KPI overview → detailed records → comparisons → distributions → trends
