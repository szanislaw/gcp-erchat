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
60 demonstration questions showcasing all 5 display types using the `incident_combine` table from Athena.

**Display Type Distribution:**
- 12 TABLE displays (detailed records)
- 12 METRIC displays (KPI values)
- 12 BAR charts (category comparisons)
- 12 PIE charts (distribution breakdowns)
- 12 LINE charts (time series trends)

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

### 5. Show pending incidents with location
**Purpose:** Track incomplete incidents by location  
**Expected Columns:** status_name, location_name, category_name, created_date, description

### 6. Show incidents by profile name
**Purpose:** Review incidents grouped by guest profile  
**Expected Columns:** profile_name, category_name, severity_name, status_name, incident_time

### 7. Show cancelled incidents
**Purpose:** Audit cancelled incidents with reasons  
**Expected Columns:** status_name, category_name, compensation_text, cancelled_date, description

### 8. Show expensive incidents
**Purpose:** Review high-cost incidents for budget analysis  
**Expected Columns:** actual_cost, category_name, severity_name, department_name, description

### 9. Show recent incidents
**Purpose:** Review incidents from the last 7 days  
**Expected Columns:** created_date, category_name, status_name, severity_name, description

### 10. Show incidents by severity and status
**Purpose:** Cross-reference severity with completion status  
**Expected Columns:** severity_name, status_name, category_name, department_name, actual_cost

### 11. Show maintenance incidents
**Purpose:** Review maintenance-related incidents  
**Expected Columns:** category_name, location_name, status_name, actual_cost, description

### 12. Show incidents with description
**Purpose:** Browse incidents with detailed notes  
**Expected Columns:** description, category_name, severity_name, status_name, created_date

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

### 9. How many pending incidents
**Purpose:** Count of incomplete incidents for workload tracking  
**Expected Result:** Single COUNT(*) WHERE status_name = 'Pending'

### 10. How many high severity incidents
**Purpose:** Critical incident count for priority attention  
**Expected Result:** Single COUNT(*) WHERE severity_name = 'High'

### 11. What is the average actual cost
**Purpose:** Actual average spending per incident  
**Expected Result:** Single AVG(actual_cost) value

### 12. How many completed incidents
**Purpose:** Completed incident count for productivity tracking  
**Expected Result:** Single COUNT(*) WHERE status_name = 'Completed'

### 13. How many cancelled incidents
**Purpose:** Cancelled incident count for tracking  
**Expected Result:** Single COUNT(*) WHERE status_name = 'Cancelled'

### 14. What is the maximum cost
**Purpose:** Highest incident cost for outlier analysis  
**Expected Result:** Single MAX(actual_cost) value

### 15. How many incidents today
**Purpose:** Today's incident count for daily tracking  
**Expected Result:** Single COUNT(*) WHERE created_date = today

### 16. What is the minimum cost
**Purpose:** Lowest incident cost for baseline analysis  
**Expected Result:** Single MIN(actual_cost) WHERE actual_cost > 0

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

### 13. Count by location
**Purpose:** Compare incidents across different locations  
**Expected Result:** location_name with COUNT(*) grouped

### 14. Count by status
**Purpose:** Compare pending vs completed vs cancelled  
**Expected Result:** status_name with COUNT(*) grouped

### 15. Average cost by category
**Purpose:** Compare average spending across categories  
**Expected Result:** category_name with AVG(actual_cost) grouped

### 16. Count by profile
**Purpose:** Compare incidents across guest profiles  
**Expected Result:** profile_name with COUNT(*) grouped

### 17. Cost by department
**Purpose:** Compare total spending across departments  
**Expected Result:** department_name with SUM(actual_cost) grouped

### 18. Count by severity
**Purpose:** Compare high vs medium vs low severity counts  
**Expected Result:** severity_name with COUNT(*) grouped

### 19. Count by temperament
**Purpose:** Compare guest temperament across incidents  
**Expected Result:** temperament_text with COUNT(*) grouped

### 20. Average cost by status
**Purpose:** Compare average spending by incident status  
**Expected Result:** status_name with AVG(actual_cost) grouped

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

### 17. Department breakdown
**Purpose:** Incident distribution by department  
**Expected Result:** department_name with COUNT(*) grouped (5-10 categories)

### 18. Category breakdown
**Purpose:** Incident distribution by category  
**Expected Result:** category_name with COUNT(*) grouped (5-10 categories)

### 19. Compensation distribution
**Purpose:** Incidents requiring vs not requiring compensation  
**Expected Result:** compensation_text grouped (2 categories: with/without)

### 20. High severity distribution
**Purpose:** Distribution of high severity by category  
**Expected Result:** category_name with COUNT(*) WHERE severity = 'High'

### 21. Location distribution
**Purpose:** Incident distribution by location  
**Expected Result:** location_name with COUNT(*) grouped (5-10 categories)

### 22. Profile distribution
**Purpose:** Incident distribution by guest profile  
**Expected Result:** profile_name with COUNT(*) grouped (5-10 categories)

### 23. Property distribution
**Purpose:** Incident distribution across properties  
**Expected Result:** property_name with COUNT(*) grouped (2-5 categories)

### 24. Cost range distribution
**Purpose:** Distribution by cost brackets (low/medium/high)  
**Expected Result:** Cost ranges with COUNT(*) grouped

---

## LINE Chart Display (12 questions)

### 25. Incident trend last 30 days
**Purpose:** Daily incident creation trend over past month  
**Expected Result:** date with COUNT(*) grouped by day

### 26. Daily incident count
**Purpose:** Daily snapshot of incident counts  
**Expected Result:** snapshotdate with COUNT(*) grouped by date

### 27. Completion trend
**Purpose:** Daily incident resolution trend  
**Expected Result:** completed_date with COUNT(*) grouped by day

### 28. Incidents per day
**Purpose:** When incidents actually occurred (time series)  
**Expected Result:** incident_time with COUNT(*) grouped by day

### 29. Weekly incident trend
**Purpose:** Weekly aggregation of incident counts  
**Expected Result:** week with COUNT(*) grouped by week

### 30. High severity trend
**Purpose:** Track high severity incidents over time  
**Expected Result:** date with COUNT(*) WHERE severity = 'High' grouped by day

### 31. Cost trend over time
**Purpose:** Track incident costs over time  
**Expected Result:** date with SUM(actual_cost) grouped by day

### 32. Vip incident trend
**Purpose:** Track VIP incidents over time  
**Expected Result:** date with COUNT(*) WHERE vip = 'Yes' grouped by day

### 33. Monthly incident trend
**Purpose:** Monthly aggregation of incident counts  
**Expected Result:** month with COUNT(*) grouped by month

### 34. Cancellation trend
**Purpose:** Track cancelled incidents over time  
**Expected Result:** cancelled_date with COUNT(*) grouped by day

### 35. Department trend over time
**Purpose:** Track incidents by department over time  
**Expected Result:** date with COUNT(*) grouped by department and day

### 36. Severity trend by month
**Purpose:** Track severity distribution over months  
**Expected Result:** month with COUNT(*) grouped by severity and month

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

**Quick Demo (5 questions):**
1. **METRIC** (#5) - "How many total incidents" - Opening KPI
2. **TABLE** (#1) - "Show high severity incidents" - Browse critical records
3. **BAR** (#9) - "Count by category" - Category comparison
4. **PIE** (#13) - "Status distribution" - Progress tracking
5. **LINE** (#21) - "Incident trend last 30 days" - Time series pattern

**Extended Demo (10 questions):**
1. **METRIC** (#5) - Total incidents KPI
2. **METRIC** (#10) - High severity count
3. **TABLE** (#1) - High severity details
4. **TABLE** (#5) - Pending incidents by location
5. **BAR** (#9) - Count by category
6. **BAR** (#14) - Count by status
7. **PIE** (#13) - Status distribution
8. **PIE** (#17) - Department breakdown
9. **LINE** (#21) - Incident trend last 30 days
10. **LINE** (#27) - Cost trend over time

**Full Demo (60 questions):**
Cycle through all questions alternating display types to showcase comprehensive capabilities.

This creates a narrative: KPI overview → detailed records → comparisons → distributions → trends
