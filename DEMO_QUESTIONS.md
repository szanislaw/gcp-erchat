# Demo Questions - Hotel Incident Management

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

### 1. Show me all high severity incidents with their location
**Purpose:** Browse critical incidents with location details  
**Expected Columns:** severity_name, location_name, category_name, status_name, description

### 2. List all incidents with department and compensation details
**Purpose:** Review incidents requiring compensation by department  
**Expected Columns:** department_name, compensation_text, actual_cost, status_name, category_name

### 3. Display vip incidents with their category and status
**Purpose:** Track VIP guest incidents for priority handling  
**Expected Columns:** vip, category_name, status_name, severity_name, location_name

### 4. Show incidents from housekeeping with actual cost
**Purpose:** Review housekeeping department incidents and costs  
**Expected Columns:** department_name, category_name, actual_cost, status_name, description

---

## METRIC Display (4 questions)

### 5. What is the total incident count
**Purpose:** Overall incident volume KPI  
**Expected Result:** Single COUNT(*) value

### 6. What is the total actual cost of all incidents
**Purpose:** Total financial impact of all incidents  
**Expected Result:** Single SUM(actual_cost) value

### 7. How many vip incidents are there
**Purpose:** VIP incident count for priority tracking  
**Expected Result:** Single COUNT(*) WHERE vip = 'Yes'

### 8. What is the average potential cost per incident
**Purpose:** Average estimated cost for budgeting  
**Expected Result:** Single AVG(potential_cost) value

---

## BAR Chart Display (4 questions)

### 9. Show incident count by category name
**Purpose:** Compare incident volume across categories  
**Expected Result:** category_name with COUNT(*) grouped

### 10. Count incidents by department name
**Purpose:** Compare which departments have most incidents  
**Expected Result:** department_name with COUNT(*) grouped

### 11. Display actual cost by severity name
**Purpose:** Compare total costs across severity levels  
**Expected Result:** severity_name with SUM(actual_cost) grouped

### 12. Show incident count by property name
**Purpose:** Compare incident volume across properties  
**Expected Result:** property_name with COUNT(*) grouped

---

## PIE Chart Display (4 questions)

### 13. Show status name distribution
**Purpose:** See breakdown of pending/completed/cancelled incidents  
**Expected Result:** status_name with COUNT(*) grouped (2-5 categories)

### 14. Display severity name breakdown
**Purpose:** Distribution of high/medium/low severity incidents  
**Expected Result:** severity_name with COUNT(*) grouped (2-5 categories)

### 15. Show vip incident percentage
**Purpose:** VIP vs non-VIP incident distribution  
**Expected Result:** vip with COUNT(*) grouped (2 categories)

### 16. Display incident distribution by temperament text
**Purpose:** Guest temperament distribution (angry/calm/neutral)  
**Expected Result:** temperament_text with COUNT(*) grouped

---

## LINE Chart Display (4 questions)

### 17. Show incident trend by created date for last 30 days
**Purpose:** Daily incident creation trend over past month  
**Expected Result:** date with COUNT(*) grouped by day

### 18. Display daily incident count from snapshotdate
**Purpose:** Daily snapshot of incident counts  
**Expected Result:** snapshotdate with COUNT(*) grouped by date

### 19. Show completion trend by completed date
**Purpose:** Daily incident resolution trend  
**Expected Result:** completed_date with COUNT(*) grouped by day

### 20. Count incidents per day by incident time
**Purpose:** When incidents actually occurred (time series)  
**Expected Result:** incident_time with COUNT(*) grouped by day

---

## Testing Command

```bash
curl -X POST http://localhost:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "What is the total incident count",
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

1. Start with **METRIC** (#5) - Show total incident count as opening KPI
2. Show **TABLE** (#1) - Browse specific high severity incidents
3. Show **BAR** (#9) - Category comparison for trends
4. Show **PIE** (#13) - Status distribution for progress tracking
5. Show **LINE** (#17) - Time series trend for patterns
6. Continue through remaining questions alternating display types

This creates a narrative: KPI overview → detailed records → comparisons → distributions → trends
