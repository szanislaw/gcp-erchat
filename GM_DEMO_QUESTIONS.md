# 20 Hotel GM Demo Questions - Natural Language Query Interface

## Database: Peninsula Incident Management System
**Table:** `incident_combine`
**Context:** Hotel incident tracking and management data

---

## 📊 OPERATIONAL OVERVIEW (5 Questions)

### 1. Daily Operations Dashboard
**Question:** "How many incidents were reported today?"
- **Display Type:** metric
- **Use Case:** Quick daily snapshot of operational issues
- **Expected Result:** Single count value

### 2. Current Open Issues
**Question:** "Show me all pending incidents"
- **Display Type:** table
- **Use Case:** Active issues requiring attention
- **Expected Result:** List of unresolved incidents

### 3. Property-Wide Summary
**Question:** "Count incidents by department"
- **Display Type:** bar
- **Use Case:** Identify which departments have most issues
- **Expected Result:** Bar chart showing Housekeeping, Front Desk, F&B, Maintenance, etc.

### 4. Weekly Trend
**Question:** "Show incidents from last 7 days"
- **Display Type:** table
- **Use Case:** Recent activity analysis
- **Expected Result:** List of incidents from past week

### 5. Severity Distribution
**Question:** "How many high severity incidents in the last 30 days?"
- **Display Type:** metric
- **Use Case:** Critical issues requiring immediate GM attention
- **Expected Result:** Count of high-priority incidents

---

## 🏨 GUEST EXPERIENCE (4 Questions)

### 6. Room Service Issues
**Question:** "Show me Room Service incidents from this week"
- **Display Type:** table
- **Use Case:** Food & Beverage quality monitoring
- **Expected Result:** List of Room Service complaints/issues

### 7. Housekeeping Performance
**Question:** "What are the most common Room Cleanliness incidents?"
- **Display Type:** bar/pie
- **Use Case:** Identify recurring housekeeping problems
- **Expected Result:** Breakdown of cleanliness issues

### 8. Guest Complaint Tracking
**Question:** "Show high severity incidents that are still pending"
- **Display Type:** table
- **Use Case:** Critical guest issues awaiting resolution
- **Expected Result:** List of urgent unresolved guest complaints

### 9. Room-Specific Issues
**Question:** "Show me all incidents at room 1018"
- **Display Type:** table
- **Use Case:** Track problematic rooms requiring maintenance or attention
- **Expected Result:** History of incidents for specific room

---

## 💰 FINANCIAL IMPACT (3 Questions)

### 10. Total Compensation Costs
**Question:** "What is the total actual cost of all incidents?"
- **Display Type:** metric
- **Use Case:** Financial impact of incidents on bottom line
- **Expected Result:** Sum of all compensation/resolution costs

### 11. High-Cost Incidents
**Question:** "Show me the top 5 incidents by actual cost"
- **Display Type:** table
- **Use Case:** Identify most expensive guest issues
- **Expected Result:** List of 5 highest-cost incidents

### 12. Compensation Analysis
**Question:** "What is the average actual cost for completed incidents by category?"
- **Display Type:** bar
- **Use Case:** Understand compensation patterns by incident type
- **Expected Result:** Average costs per incident category

---

## 📈 PERFORMANCE ANALYTICS (4 Questions)

### 13. Department Accountability
**Question:** "Which department has the most incidents?"
- **Display Type:** bar
- **Use Case:** Identify departments needing improvement
- **Expected Result:** Ranked list of departments by incident count

### 14. Severity Analysis
**Question:** "Show incident breakdown by severity"
- **Display Type:** pie
- **Use Case:** Understand distribution of issue criticality
- **Expected Result:** Pie chart showing high/medium/low severity split

### 15. Category Distribution
**Question:** "Count incidents by category"
- **Display Type:** bar
- **Use Case:** Identify most common types of guest issues
- **Expected Result:** Bar chart of categories (Room Cleanliness, Noise, Amenities, etc.)

### 16. Recent Critical Issues
**Question:** "Show recent Housekeeping incidents with medium severity"
- **Display Type:** table
- **Use Case:** Monitor specific department's performance
- **Expected Result:** Filtered list of housekeeping issues

---

## 🎯 STRATEGIC INSIGHTS (4 Questions)

### 17. Resolution Tracking
**Question:** "How many incidents were completed in the last month?"
- **Display Type:** metric
- **Use Case:** Measure incident closure rate
- **Expected Result:** Count of resolved incidents

### 18. Property Comparison
**Question:** "How many incidents does each property have?"
- **Display Type:** bar
- **Use Case:** Compare performance across multiple hotel locations
- **Expected Result:** Bar chart showing incident counts per property

### 19. Incident Trend Analysis
**Question:** "Show me incidents ordered by severity"
- **Display Type:** table
- **Use Case:** Prioritized view of all incidents
- **Expected Result:** Sorted list from high to low severity

### 20. Status Overview
**Question:** "Count incidents by status"
- **Display Type:** pie
- **Use Case:** Pipeline view of incident lifecycle
- **Expected Result:** Pie chart showing pending/completed/cancelled distribution

---

## 💡 DEMO TIPS FOR PRESENTATION

### Opening Statement:
*"As a Hotel General Manager, you need real-time insights into your property's operations. This AI-powered query interface lets you ask questions in plain English and instantly get visualized answers from your incident management system."*

### Demo Flow:
1. **Start with metrics** (Q1, Q5) - Show quick KPIs
2. **Show critical issues** (Q8, Q11) - Demonstrate urgency handling
3. **Department analysis** (Q3, Q13) - Identify problem areas
4. **Financial impact** (Q10, Q12) - Connect to bottom line
5. **Trend analysis** (Q14, Q18) - Strategic insights

### Key Selling Points:
- ✅ **No SQL knowledge required** - Natural language queries
- ✅ **Real-time data** - Direct connection to operational database
- ✅ **Smart visualizations** - Automatic chart type selection
- ✅ **Mobile-friendly** - Access insights anywhere
- ✅ **Secure** - Property-based access control via UUID

---

## 📋 Sample API Requests with Hardcoded Display Types

### Example 1: Metric Display (Q5 - Severity Count)
```bash
curl -X POST http://localhost:8080/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "How many high severity incidents in the last 30 days?",
    "context": {
      "language": "en",
      "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec",
      "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false, "max_rows": 100},
    "model": {"max_tokens": 512},
    "display": {"type": "metric"},
    "trace": {"source": "gm-demo"}
  }'
```

### Example 2: Pie Chart Display (Q14 - Severity Breakdown)
```bash
curl -X POST http://localhost:8080/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Show incident breakdown by severity",
    "context": {
      "language": "en",
      "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec",
      "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false, "max_rows": 100},
    "model": {"max_tokens": 512},
    "display": {"type": "pie"},
    "trace": {"source": "gm-demo"}
  }'
```

### Example 3: Bar Chart Display (Q3 - Department Count)
```bash
curl -X POST http://localhost:8080/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Count incidents by department",
    "context": {
      "language": "en",
      "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec",
      "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false, "max_rows": 100},
    "model": {"max_tokens": 512},
    "display": {"type": "bar"},
    "trace": {"source": "gm-demo"}
  }'
```

### Example 4: Table Display (Q2 - Pending Incidents)
```bash
curl -X POST http://localhost:8080/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Show me all pending incidents",
    "context": {
      "language": "en",
      "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec",
      "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false, "max_rows": 100},
    "model": {"max_tokens": 512},
    "display": {"type": "table"},
    "trace": {"source": "gm-demo"}
  }'
```

---

## 📝 Complete Request Payloads for All 20 Questions

### OPERATIONAL OVERVIEW

**Q1: Daily Operations Dashboard (metric)**
```json
{
  "text": "How many incidents were reported today?",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "metric"},
  "trace": {"source": "gm-demo"}
}
```

**Q2: Current Open Issues (table)**
```json
{
  "text": "Show me all pending incidents",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "table"},
  "trace": {"source": "gm-demo"}
}
```

**Q3: Property-Wide Summary (bar)**
```json
{
  "text": "Count incidents by department",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "bar"},
  "trace": {"source": "gm-demo"}
}
```

**Q4: Weekly Trend (table)**
```json
{
  "text": "Show incidents from last 7 days",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "table"},
  "trace": {"source": "gm-demo"}
}
```

**Q5: Severity Distribution (metric)**
```json
{
  "text": "How many high severity incidents in the last 30 days?",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "metric"},
  "trace": {"source": "gm-demo"}
}
```

### GUEST EXPERIENCE

**Q6: Room Service Issues (table)**
```json
{
  "text": "Show me Room Service incidents from this week",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "table"},
  "trace": {"source": "gm-demo"}
}
```

**Q7: Housekeeping Performance (pie)**
```json
{
  "text": "What are the most common Room Cleanliness incidents?",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "pie"},
  "trace": {"source": "gm-demo"}
}
```

**Q8: Guest Complaint Tracking (table)**
```json
{
  "text": "Show high severity incidents that are still pending",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "table"},
  "trace": {"source": "gm-demo"}
}
```

**Q9: Room-Specific Issues (table)**
```json
{
  "text": "Show me all incidents at room 1018",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "table"},
  "trace": {"source": "gm-demo"}
}
```

### FINANCIAL IMPACT

**Q10: Total Compensation Costs (metric)**
```json
{
  "text": "What is the total actual cost of all incidents?",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "metric"},
  "trace": {"source": "gm-demo"}
}
```

**Q11: High-Cost Incidents (table)**
```json
{
  "text": "Show me the top 5 incidents by actual cost",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "table"},
  "trace": {"source": "gm-demo"}
}
```

**Q12: Compensation Analysis (bar)**
```json
{
  "text": "What is the average actual cost for completed incidents by category?",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "bar"},
  "trace": {"source": "gm-demo"}
}
```

### PERFORMANCE ANALYTICS

**Q13: Department Accountability (bar)**
```json
{
  "text": "Which department has the most incidents?",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "bar"},
  "trace": {"source": "gm-demo"}
}
```

**Q14: Severity Analysis (pie)**
```json
{
  "text": "Show incident breakdown by severity",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "pie"},
  "trace": {"source": "gm-demo"}
}
```

**Q15: Category Distribution (bar)**
```json
{
  "text": "Count incidents by category",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "bar"},
  "trace": {"source": "gm-demo"}
}
```

**Q16: Recent Critical Issues (table)**
```json
{
  "text": "Show recent Housekeeping incidents with medium severity",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "table"},
  "trace": {"source": "gm-demo"}
}
```

### STRATEGIC INSIGHTS

**Q17: Resolution Tracking (metric)**
```json
{
  "text": "How many incidents were completed in the last month?",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "metric"},
  "trace": {"source": "gm-demo"}
}
```

**Q18: Property Comparison (bar)**
```json
{
  "text": "How many incidents does each property have?",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "bar"},
  "trace": {"source": "gm-demo"}
}
```

**Q19: Incident Trend Analysis (table)**
```json
{
  "text": "Show me incidents ordered by severity",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "table"},
  "trace": {"source": "gm-demo"}
}
```

**Q20: Status Overview (pie)**
```json
{
  "text": "Count incidents by status",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "pie"},
  "trace": {"source": "gm-demo"}
}
```

---

## 🎨 Recommended Display Types by Question Type

| Question Type | Display Type | Reason |
|---------------|--------------|--------|
| "How many..." | metric | Single KPI value |
| "Show breakdown by..." | pie/bar | Category distribution |
| "Show me..." (list) | table | Detailed records |
| "Top X..." | bar/table | Ranked comparison |
| "Trend over time" | line | Time series visualization |
| "Which department..." | bar | Categorical comparison |

---

**Target Audience:** Hotel General Managers, Operations Directors, Property Managers
**Demo Duration:** 10-15 minutes
**Success Metric:** GM can independently query data within 5 minutes of training
