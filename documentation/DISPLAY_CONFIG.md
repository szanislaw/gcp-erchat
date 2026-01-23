# Display Configuration Design

## Overview

The `display` field provides UI rendering hints to frontend applications, enabling intelligent visualization of query results based on query intent and data characteristics.

## Display Types

### 1. **metric**
For single-value results (counts, sums, averages)
```json
{
  "type": "metric",
  "title": "Total Incidents",
  "subtitle": "Last 30 days",
  "chart_config": {
    "size": "large|medium|small",
    "color": "#4F46E5",
    "icon": "📊",
    "locale": "en|zh-CN|ms|ta"
  }
}
```

**Use cases:**
- "How many incidents?"
- "What is the total revenue?"
- "Count of active users"

---

### 2. **table**
For tabular data with multiple rows and columns
```json
{
  "type": "table",
  "title": "Incident List",
  "subtitle": "Filtered results",
  "chart_config": {
    "columns": ["id", "title", "status", "priority"],
    "sortable": true,
    "filterable": true,
    "paginated": true,
    "highlight_rows": {
      "field": "value"
    }
  }
}
```

**Use cases:**
- "Show all incidents"
- "List users by department"
- "Display product inventory"

---

### 3. **bar**
For categorical comparisons
```json
{
  "type": "bar",
  "title": "Resolution Time by Category",
  "subtitle": "Average hours",
  "chart_config": {
    "x_axis": "category",
    "y_axis": "avg_time",
    "orientation": "vertical|horizontal",
    "color_scheme": "blue|green|red|multi",
    "show_values": true,
    "unit": "hours|count|currency"
  }
}
```

**Use cases:**
- "Compare sales by region"
- "Average resolution time by category"
- "Incidents per status"

---

### 4. **line**
For time-series and trend analysis
```json
{
  "type": "line",
  "title": "Incident Trends",
  "subtitle": "Last 90 days",
  "chart_config": {
    "x_axis": "date",
    "y_axis": "count",
    "show_markers": true,
    "smooth_line": true,
    "show_area": false,
    "color": "#10B981"
  }
}
```

**Use cases:**
- "Incident trends over time"
- "Revenue growth monthly"
- "User registrations by week"

---

### 5. **pie**
For part-to-whole relationships
```json
{
  "type": "pie",
  "title": "Incidents by Status",
  "subtitle": "Distribution breakdown",
  "chart_config": {
    "value_field": "count",
    "label_field": "status",
    "show_percentage": true,
    "show_legend": true,
    "color_palette": ["#4F46E5", "#10B981", "#F59E0B", "#EF4444"]
  }
}
```

**Use cases:**
- "Distribution of incidents by status"
- "Market share by product"
- "Budget allocation by department"

---

### 6. **card**
For dashboard-style multi-metric displays
```json
{
  "type": "card",
  "title": "Incident Overview",
  "subtitle": "Real-time metrics",
  "chart_config": {
    "layout": "grid|stack",
    "cards": [
      {
        "label": "Open",
        "value_field": "open_count",
        "color": "#4F46E5"
      },
      {
        "label": "In Progress",
        "value_field": "in_progress_count",
        "color": "#F59E0B"
      }
    ]
  }
}
```

**Use cases:**
- "Dashboard summary"
- "KPI overview"
- "Multi-metric displays"

---

### 7. **list**
For card-based item displays with rich metadata
```json
{
  "type": "list",
  "title": "Recent Incidents",
  "subtitle": "Requires attention",
  "chart_config": {
    "group_by": "priority|status|category",
    "show_badges": true,
    "enable_actions": true,
    "actions": ["view", "edit", "delete"],
    "card_layout": {
      "show_avatar": true,
      "show_timestamp": true,
      "show_status_badge": true
    }
  }
}
```

**Use cases:**
- "Recent activity feed"
- "Task lists"
- "Notification items"

---

## Intelligent Display Selection Logic

### Query Pattern → Display Type Mapping

| Query Pattern | Keywords | Display Type |
|--------------|----------|--------------|
| **Count/Sum queries** | "how many", "total", "count", "sum" | `metric` |
| **List/Filter queries** | "show", "list", "display", "get all" | `table` or `list` |
| **Comparison queries** | "compare", "by category", "per", "each" | `bar` |
| **Trend queries** | "over time", "monthly", "daily", "trend" | `line` |
| **Distribution queries** | "distribution", "breakdown", "percentage" | `pie` |
| **Multi-metric queries** | "overview", "dashboard", "summary" | `card` |

### Context-Based Selection

```python
# Example logic for automatic display type selection
def recommend_display_type(query_text, expected_result_structure):
    query_lower = query_text.lower()
    
    # Aggregation with single value
    if any(word in query_lower for word in ['how many', 'total', 'count', 'sum']):
        return 'metric'
    
    # Time-based queries
    if any(word in query_lower for word in ['trend', 'over time', 'monthly', 'daily']):
        return 'line'
    
    # Grouped aggregations
    if 'by' in query_lower and any(word in query_lower for word in ['average', 'total', 'count']):
        return 'bar'
    
    # Distribution queries
    if any(word in query_lower for word in ['distribution', 'breakdown', 'percentage']):
        return 'pie'
    
    # List queries with actions needed
    if any(word in query_lower for word in ['assigned to', 'my', 'recent']):
        return 'list'
    
    # Default to table for multi-column results
    return 'table'
```

---

## Best Practices

### 1. **Match Display to Data Shape**
- Single value → `metric`
- Multiple rows, few columns → `table`
- Multiple rows, needs grouping → `bar`, `pie`, or `line`
- Rich metadata items → `list`

### 2. **Consider User Intent**
- Analysis → Charts (`bar`, `line`, `pie`)
- Action required → `list` or `table` with actions
- Quick glance → `metric` or `card`

### 3. **Localization**
Always include locale in chart_config for i18n support:
```json
{
  "chart_config": {
    "locale": "zh-CN",  // Matches context.language
    "date_format": "YYYY-MM-DD",
    "number_format": "0,0.00"
  }
}
```

### 4. **Accessibility**
```json
{
  "chart_config": {
    "alt_text": "Bar chart showing average resolution time by category",
    "color_blind_safe": true,
    "high_contrast": false
  }
}
```

### 5. **Interactive Elements**
```json
{
  "chart_config": {
    "enable_drill_down": true,
    "enable_export": true,
    "enable_filter": true,
    "click_action": "show_detail"
  }
}
```

---

## Response Enhancement

The backend can enhance display recommendations based on actual query results:

```python
# Pseudo-code for response enhancement
def enhance_display_config(display_config, query_results):
    """
    Adjust display config based on actual result characteristics
    """
    result_count = len(query_results)
    columns = list(query_results[0].keys()) if result_count > 0 else []
    
    # Override display type if data doesn't match
    if display_config['type'] == 'table' and result_count == 1 and len(columns) == 1:
        display_config['type'] = 'metric'
    
    # Add detected columns to table config
    if display_config['type'] == 'table':
        if 'columns' not in display_config.get('chart_config', {}):
            display_config['chart_config']['columns'] = columns
    
    # Auto-detect x/y axes for charts
    if display_config['type'] in ['bar', 'line'] and len(columns) == 2:
        display_config['chart_config']['x_axis'] = columns[0]
        display_config['chart_config']['y_axis'] = columns[1]
    
    return display_config
```

---

## Implementation Checklist

- [x] Add `DisplayConfig` model to backend
- [x] Make `display` field optional in `NLQRequest`
- [ ] Implement automatic display type inference
- [ ] Add display config to API response
- [ ] Create frontend renderer components
- [ ] Add display config validation
- [ ] Document display types in API docs
- [ ] Add unit tests for display recommendations
- [ ] Implement A/B testing for display effectiveness

---

## Future Enhancements

1. **Machine Learning-Based Recommendations**
   - Train model to predict optimal display type from query embeddings
   - Learn user preferences over time

2. **Dynamic Display Switching**
   - Allow users to toggle between display types
   - Remember user preferences per query pattern

3. **Custom Display Templates**
   - Enable users to create custom display configurations
   - Share templates across organization

4. **Responsive Design**
   - Adapt display type based on screen size
   - Mobile-optimized alternatives

5. **Animation & Transitions**
   - Smooth transitions between display types
   - Loading states and skeleton screens
