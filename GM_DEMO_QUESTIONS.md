# 20 Hotel GM Demo Questions - Natural Language Query Interface

## Database: Peninsula Incident Management System
**Table:** `incident_combine`
**Context:** Hotel incident tracking and management data

---

## 📊 OPERATIONAL OVERVIEW (5 Questions)

### 1. Daily Operations Dashboard
**Question:** "Show me all incidents"
- **Display Type:** table
- **Use Case:** Quick snapshot of all operational issues
- **Expected Result:** List of all incidents

### 2. Current Open Issues
**Question:** "Show me all pending incidents"
- **Display Type:** table
- **Use Case:** Active issues requiring attention
- **Expected Result:** List of unresolved incidents

### 3. Category-Wide Summary
**Question:** "Show me all Service Quality incidents"
- **Display Type:** bar
- **Use Case:** Review Service Quality category issues (bar chart visualization)
- **Expected Result:** Service Quality incidents visualized as bar chart

### 4. Weekly Trend
**Question:** "Show incidents from last 7 days"
- **Display Type:** line
- **Use Case:** Recent activity trend analysis
- **Expected Result:** Time series visualization of recent incidents

### 5. Severity Distribution
**Question:** "Show recent incidents with medium severity"
- **Display Type:** pie
- **Use Case:** Severity distribution visualization
- **Expected Result:** Pie chart showing severity breakdown

---

## 🏨 GUEST EXPERIENCE (4 Questions)

### 6. Category Analysis
**Question:** "Show me incidents for Food and Beverage category"
- **Display Type:** bar
- **Use Case:** Food & Beverage quality monitoring (bar visualization)
- **Expected Result:** F&B incidents as bar chart

### 7. Common Issue Patterns
**Question:** "Show me incidents for Food and Beverage category"
- **Display Type:** table
- **Use Case:** Review Food & Beverage incidents
- **Expected Result:** List of F&B incidents

### 8. Critical Guest Issues
**Question:** "Show high severity incidents that are still pending"
- **Display Type:** table
- **Use Case:** Critical guest issues awaiting resolution
- **Expected Result:** Detailed list of urgent unresolved guest complaints

### 9. High Priority Issues
**Question:** "Show high severity incidents that are still pending"
- **Display Type:** table
- **Use Case:** Track urgent unresolved incidents
- **Expected Result:** List of high severity pending incidents

---

## 💰 FINANCIAL IMPACT (3 Questions)

### 10. High-Cost Incidents
**Question:** "Show me incidents with actual cost greater than 100"
- **Display Type:** bar
- **Use Case:** Financial impact visualization of costly incidents
- **Expected Result:** Bar chart of high-cost incidents

### 11. Cost-Sorted Incidents
**Question:** "Show me all incidents sorted by actual cost"
- **Display Type:** table
- **Use Case:** Detailed view of incidents ranked by financial impact
- **Expected Result:** Comprehensive list sorted by actual cost

### 12. Completed Incidents Review
**Question:** "Show me completed incidents"
- **Display Type:** pie
- **Use Case:** Resolution status visualization
- **Expected Result:** Pie chart showing completed vs other statuses

---

## 📈 PERFORMANCE ANALYTICS (4 Questions)

### 13. Severity-Ordered View
**Question:** "Show me incidents ordered by severity"
- **Display Type:** bar
- **Use Case:** Priority distribution visualization
- **Expected Result:** Bar chart showing incidents by severity level

### 14. Recent Activity
**Question:** "Show incidents from last 7 days"
- **Display Type:** line
- **Use Case:** Recent incident activity trend
- **Expected Result:** Line chart showing daily incident trends

### 15. Food & Beverage Focus
**Question:** "Show me incidents for Food and Beverage category"
- **Display Type:** table
- **Use Case:** Detailed F&B service quality review
- **Expected Result:** Comprehensive list of Food & Beverage incidents

### 16. Recent Medium Priority Issues
**Question:** "Show recent incidents with medium severity"
- **Display Type:** pie
- **Use Case:** Medium priority distribution visualization
- **Expected Result:** Pie chart of medium severity incidents

---

## 🎯 STRATEGIC INSIGHTS (4 Questions)

### 17. Resolution Tracking
**Question:** "Show me completed incidents"
- **Display Type:** bar
- **Use Case:** Resolution tracking visualization
- **Expected Result:** Bar chart of completed incidents

### 18. Pending Issues Overview
**Question:** "Show me all pending incidents"
- **Display Type:** table
- **Use Case:** Detailed view of all open issues requiring attention
- **Expected Result:** Comprehensive list of pending incidents

### 19. Incident Priority Analysis
**Question:** "Show me incidents ordered by severity"
- **Display Type:** bar
- **Use Case:** Priority distribution comparison
- **Expected Result:** Bar chart comparing incidents by severity

### 20. Cost Analysis
**Question:** "Show me all incidents sorted by actual cost"
- **Display Type:** table
- **Use Case:** Detailed financial impact analysis
- **Expected Result:** Incidents ordered by cost impact with full details

---

## 💡 DEMO TIPS FOR PRESENTATION

### Opening Statement:
*"As a Hotel General Manager, you need real-time insights into your property's operations. This AI-powered query interface lets you ask questions in plain English and instantly get visualized answers from your incident management system."*

### Demo Flow:
1. **Start with metrics** (Q1, Q5) - Show quick KPIs
2. **Show critical issues** (Q8, Q11) - Demonstrate urgency handling
3. **Category analysis** (Q3, Q13) - Identify problem areas
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

### Example 4: Line Chart Display - Weekly Trend (Q4)
```bash
curl -X POST http://localhost:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Show incidents from last 7 days",
    "context": {
      "language": "en",
      "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec",
      "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false, "max_rows": 100},
    "model": {"max_tokens": 512},
    "display": {"type": "line"},
    "trace": {"source": "gm-demo"}
  }'
```

### Example 2: Bar Chart Display - Service Quality (Q3)
```bash
curl -X POST http://localhost:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Show me all Service Quality incidents",
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

### Example 3: Pie Chart Display - Severity Distribution (Q5)
```bash
curl -X POST http://localhost:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Show recent incidents with medium severity",
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

### Example 4: Line Chart Display - Weekly Trend (Q4)
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

**Q1: Daily Operations Dashboard (table)**
```json
{
  "text": "Show me all incidents",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "table"},
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

**Q3: Category-Wide Summary (bar)**
```json
{
  "text": "Show me all Service Quality incidents",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "bar"},
  "trace": {"source": "gm-demo"}
}
```

**Q4: Weekly Trend (line)**
```json
{
  "text": "Show incidents from last 7 days",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "line"},
  "trace": {"source": "gm-demo"}
}
```

**Q5: Severity Distribution (pie)**
```json
{
  "text": "Show recent incidents with medium severity",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "pie"},
  "trace": {"source": "gm-demo"}
}
```

### GUEST EXPERIENCE

**Q6: Category Analysis (bar)**
```json
{
  "text": "Show me incidents for Food and Beverage category",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "bar"},
  "trace": {"source": "gm-demo"}
}
```

**Q7: Common Issue Patterns (table)**
```json
{
  "text": "Show me incidents for Food and Beverage category",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "table"},
  "trace": {"source": "gm-demo"}
}
```

**Q8: High Priority Issues (table)**
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

**Q9: High Priority Issues (table)**
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

### FINANCIAL IMPACT

**Q10: High-Cost Incidents (bar)**
```json
{
  "text": "Show me incidents with actual cost greater than 100",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "bar"},
  "trace": {"source": "gm-demo"}
}
```

**Q11: Cost-Sorted Incidents (table)**
```json
{
  "text": "Show me all incidents sorted by actual cost",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "table"},
  "trace": {"source": "gm-demo"}
}
```

**Q12: Completed Incidents Review (pie)**
```json
{
  "text": "Show me completed incidents",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "pie"},
  "trace": {"source": "gm-demo"}
}
```

### PERFORMANCE ANALYTICS

**Q13: Severity-Ordered View (bar)**
```json
{
  "text": "Show me incidents ordered by severity",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "bar"},
  "trace": {"source": "gm-demo"}
}
```

**Q14: Recent Activity (line)**
```json
{
  "text": "Show incidents from last 7 days",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "line"},
  "trace": {"source": "gm-demo"}
}
```

**Q15: Food & Beverage Focus (table)**
```json
{
  "text": "Show me incidents for Food and Beverage category",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "table"},
  "trace": {"source": "gm-demo"}
}
```

**Q16: Recent Medium Priority Issues (pie)**
```json
{
  "text": "Show recent incidents with medium severity",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "pie"},
  "trace": {"source": "gm-demo"}
}
```

### STRATEGIC INSIGHTS

**Q17: Resolution Tracking (bar)**
```json
{
  "text": "Show me completed incidents",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "bar"},
  "trace": {"source": "gm-demo"}
}
```

**Q18: Pending Issues Overview (table)**
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

**Q19: Incident Priority Analysis (bar)**
```json
{
  "text": "Show me incidents ordered by severity",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "bar"},
  "trace": {"source": "gm-demo"}
}
```

**Q20: Cost Analysis (table)**
```json
{
  "text": "Show me all incidents sorted by actual cost",
  "context": {"language": "en", "property_uuid": "c0abc579-6ef4-47a3-8290-16cf26964aec", "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"},
  "sql": {"dialect": "athena"},
  "execution": {"dry_run": false, "max_rows": 100},
  "model": {"max_tokens": 512},
  "display": {"type": "table"},
  "trace": {"source": "gm-demo"}
}
```

---

## 🎨 Display Type Distribution

### Overview of 20 Demo Questions:
- **Table (9 questions):** Detailed data views - Q1, Q2, Q7, Q8, Q11, Q15, Q18, Q20
- **Bar (7 questions):** Category comparisons - Q3, Q6, Q10, Q13, Q17, Q19
- **Pie (3 questions):** Distribution breakdowns - Q5, Q12, Q16
- **Line (2 questions):** Time series trends - Q4, Q14

### Display Type Use Cases:

| Display Type | Best For | Demo Questions |
|--------------|----------|----------------|
| **table** | Detailed records, multi-column data | Q1, Q2, Q7, Q8, Q11, Q15, Q18, Q20 |
| **bar** | Category comparisons, rankings | Q3, Q6, Q10, Q13, Q17, Q19 |
| **pie** | Distribution percentages, status breakdown | Q5, Q12, Q16 |
| **line** | Time series, trends over time | Q4, Q14 |

---

**Note:** Display types are hardcoded in the payload's `display.type` field. The frontend should pass this through the WebSocket message to ensure consistent visualization.

**Target Audience:** Hotel General Managers, Operations Directors, Property Managers
**Demo Duration:** 10-15 minutes
**Success Metric:** GM can independently query data within 5 minutes of training
