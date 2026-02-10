# Frontend Display Type Hardcoding Solution

## Problem
The frontend WebSocket handler doesn't include display type in the payload, so the backend auto-detects it. For demo purposes, we want to hardcode specific display types for specific questions.

---

## Solution 1: Add Display Type Parameter to handleAsk

### Modified Frontend Code

```javascript
// Modified handleAsk function that accepts optional display type
const handleAsk = (query, displayType = null) => {
  try {
    const id = uuidV4();
    idRequest.current = id;
    
    // Build base payload
    const payload = {
      type: enumsWS.EVENT.IWIZ_ASK,
      payload: {
        request_id: id,
        query,
        account_uuid: listTokenRef.current?.account_uuid || '00000000-0000-0000-0000-000000000000',
        property_uuid: listTokenRef.current?.property_uuid || '00000000-0000-0000-0000-000000000000',
      },
    };
    
    // Add display type if provided
    if (displayType) {
      payload.payload.display = { type: displayType };
    }
    
    iWizWsc.ws.send(payload);
    iWizWsc.ws.stopAlive();
  } catch (e) {
    console.warn('Failed to send ws message', e);
  }
};

// Usage examples:
handleAsk("Show me all pending incidents", "table");
handleAsk("Count incidents by category", "bar");
handleAsk("Show incident breakdown by severity", "pie");
handleAsk("How many incidents do we have?", "metric");
handleAsk("Show me all incidents"); // No display type - backend auto-detects
```

---

## Solution 2: Automatic Display Type Detection from Query

### Create a mapping that automatically detects display type from the query text:

```javascript
// Demo question configuration - maps exact questions to display types
const GM_DEMO_DISPLAY_TYPES = {
  // OPERATIONAL OVERVIEW
  "Show me all incidents": "table",
  "Show me all pending incidents": "table",
  "Show me all Service Quality incidents": "bar",
  "Show incidents from last 7 days": "line",
  "Show recent incidents with medium severity": "pie",
  
  // GUEST EXPERIENCE
  "Show me incidents for Food and Beverage category": "bar",
  "Show high severity incidents that are still pending": "table",
  
  // FINANCIAL IMPACT
  "Show me incidents with actual cost greater than 100": "bar",
  "Show me all incidents sorted by actual cost": "table",
  "Show me completed incidents": "pie",
  
  // PERFORMANCE ANALYTICS
  "Show me incidents ordered by severity": "bar",
  
  // STRATEGIC INSIGHTS
  // Add all 20 questions here...
};

// Automatic handleAsk - detects display type from query
const handleAsk = query => {
  try {
    const id = uuidV4();
    idRequest.current = id;
    
    // Automatically lookup display type for this query
    const displayType = GM_DEMO_DISPLAY_TYPES[query];
    
    const payload = {
      type: enumsWS.EVENT.IWIZ_ASK,
      payload: {
        request_id: id,
        query,
        account_uuid: listTokenRef.current?.account_uuid || '00000000-0000-0000-0000-000000000000',
        property_uuid: listTokenRef.current?.property_uuid || '00000000-0000-0000-0000-000000000000',
      },
    };
    
    // Add display type if found in mapping
    if (displayType) {
      payload.payload.display = { type: displayType };
    }
    // Otherwise, backend will auto-detect (or default to table)
    
    iWizWsc.ws.send(payload);
    iWizWsc.ws.stopAlive();
  } catch (e) {
    console.warn('Failed to send ws message', e);
  }
};

// Usage - user just types in chat bar:
// "Show me all pending incidents" → automatically gets displayType: "table"
// "Show me all Service Quality incidents" → automatically gets displayType: "bar"
// "any other question" → backend auto-detects or uses default
```

### Complete Mapping for All 20 GM Demo Questions:

```javascript
const GM_DEMO_DISPLAY_TYPES = {
  // OPERATIONAL OVERVIEW (5)
  "Show me all incidents": "table",
  "Show me all pending incidents": "table",
  "Show me all Service Quality incidents": "bar",
  "Show incidents from last 7 days": "line",
  "Show recent incidents with medium severity": "pie",
  
  // GUEST EXPERIENCE (4)
  "Show me incidents for Food and Beverage category": "bar",
  "Show high severity incidents that are still pending": "table",
  
  // FINANCIAL IMPACT (3)
  "Show me incidents with actual cost greater than 100": "bar",
  "Show me all incidents sorted by actual cost": "table",
  "Show me completed incidents": "pie",
  
  // PERFORMANCE ANALYTICS (4)
  "Show me incidents ordered by severity": "bar",
  
  // STRATEGIC INSIGHTS (4)
  // Mapping for remaining questions
};
```

### Pattern-Based Detection (Alternative):

If exact string matching is too strict, use pattern detection:

```javascript
const getDisplayTypeForQuery = (query) => {
  const lowerQuery = query.toLowerCase();
  
  // Line chart for time-based queries
  if (lowerQuery.includes('last 7 days') || 
      lowerQuery.includes('last week') ||
      lowerQuery.includes('trend')) {
    return 'line';
  }
  
  // Pie chart for distribution/severity queries
  if (lowerQuery.includes('severity') && lowerQuery.includes('show')) {
    return 'pie';
  }
  
  // Bar chart for category/comparison queries
  if (lowerQuery.includes('service quality') ||
      lowerQuery.includes('food and beverage') ||
      lowerQuery.includes('ordered by') ||
      lowerQuery.includes('cost greater than')) {
    return 'bar';
  }
  
  // Default to table for everything else
  return 'table';
};

const handleAsk = query => {
  try {
    const id = uuidV4();
    idRequest.current = id;
    
    // Auto-detect display type based on query content
    const displayType = getDisplayTypeForQuery(query);
    
    const payload = {
      type: enumsWS.EVENT.IWIZ_ASK,
      payload: {
        request_id: id,
        query,
        account_uuid: listTokenRef.current?.account_uuid || '00000000-0000-0000-0000-000000000000',
        property_uuid: listTokenRef.current?.property_uuid || '00000000-0000-0000-0000-000000000000',
        display: { type: displayType },  // Always include display type
      },
    };
    
    iWizWsc.ws.send(payload);
    iWizWsc.ws.stopAlive();
  } catch (e) {
    console.warn('Failed to send ws message', e);
  }
};
```

---

## Solution 3: Suggested Questions Component (Optional Enhancement)

If you want to help users discover the demo questions, add clickable suggestions:

```javascript
const GMDemoSuggestions = () => {
  const suggestions = [
    { category: "📊 Operations", questions: [
      "Show me all pending incidents",
      "Show me all Service Quality incidents",
    ]},
    { category: "💰 Financial", questions: [
      "Show me incidents with actual cost greater than 100",
      "Show me all incidents sorted by actual cost",
    ]},
    { category: "📈 Analytics", questions: [
      "Show incidents from last 7 days",
      "Show recent incidents with medium severity",
    ]},
  ];

  return (
    <div className="demo-suggestions">
      {suggestions.map(cat => (
        <div key={cat.category}>
          <h4>{cat.category}</h4>
          {cat.questions.map(q => (
            <button
              key={q}
              onClick={() => handleAsk(q)}  // Just pass the query
              className="suggestion-btn"
            >
              {q}
            </button>
          ))}
        </div>
      ))}
    </div>
  );
};

// The display types are automatically handled by the mapping in handleAsk
```

---

## WebSocket Payload Format

### Expected backend payload structure:

```javascript
{
  type: "IWIZ_ASK",  // Your event enum
  payload: {
    request_id: "uuid-v4-string",
    query: "Show me all pending incidents",
    account_uuid: "fccb8d60-de9c-4bf8-abd8-fae523c732c6",
    property_uuid: "c0abc579-6ef4-47a3-8290-16cf26964aec",
    
    // ADD THIS FIELD TO FORCE DISPLAY TYPE
    display: {
      type: "table"  // Options: "table", "bar", "pie", "metric", "line"
    },
    
    // Optional: Other fields from HTTP API
    sql: {
      dialect: "athena"
    },
    execution: {
      dry_run: false,
      max_rows: 100
    },
    model: {
      max_tokens: 512
    },
    trace: {
      source: "gm-demo"
    }
  }
}
```

---

## Quick Implementation (Minimal Changes)

**For a simple chat bar where users only type queries:**

```javascript
// Define display type mapping at the top of your file
const DISPLAY_TYPE_MAP = {
  "Show me all incidents": "table",
  "Show me all pending incidents": "table",
  "Show me all Service Quality incidents": "bar",
  "Show incidents from last 7 days": "line",
  "Show recent incidents with medium severity": "pie",
  "Show me incidents for Food and Beverage category": "bar",
  "Show high severity incidents that are still pending": "table",
  "Show me incidents with actual cost greater than 100": "bar",
  "Show me all incidents sorted by actual cost": "table",
  "Show me completed incidents": "pie",
  "Show me incidents ordered by severity": "bar",
  // Add remaining questions...
};

// Modify your existing handleAsk to lookup display type
const handleAsk = query => {
  try {
    const id = uuidV4();
    idRequest.current = id;
    
    const payload = {
      type: enumsWS.EVENT.IWIZ_ASK,
      payload: {
        request_id: id,
        query,
        account_uuid: listTokenRef.current?.account_uuid || '00000000-0000-0000-0000-000000000000',
        property_uuid: listTokenRef.current?.property_uuid || '00000000-0000-0000-0000-000000000000',
      },
    };
    
    // Auto-add display type if query is in mapping
    const displayType = DISPLAY_TYPE_MAP[query];
    if (displayType) {
      payload.payload.display = { type: displayType };
    }
    
    iWizWsc.ws.send(payload);
    iWizWsc.ws.stopAlive();
  } catch (e) {
    console.warn('Failed to send ws message', e);
  }
};

// Usage - user just types in the chat bar:
// "Show me all pending incidents" ✅ automatically becomes table
// "Show me all Service Quality incidents" ✅ automatically becomes bar
// "any other question" ✅ backend auto-detects or uses default
```

---

## Display Type Options

Based on the backend API and the updated GM demo configuration:

| Display Type | Use Case | Example Questions | Count in Demo |
|--------------|----------|-------------------|---------------|
| `table` | Detailed row data, multi-column views | "Show me all pending incidents" | 9 questions |
| `bar` | Category comparisons, rankings | "Show me all Service Quality incidents" | 7 questions |
| `pie` | Distribution breakdown, percentages | "Show recent incidents with medium severity" | 3 questions |
| `line` | Time series trends, temporal data | "Show incidents from last 7 days" | 2 questions |

### Display Type Distribution in GM Demo:
- **45% Table** - For detailed analysis
- **35% Bar** - For category comparisons
- **15% Pie** - For distribution views
- **10% Line** - For time trends

**Note:** This mix provides visual variety while maintaining data clarity. The frontend should properly render each display type for an engaging demo experience.

---

## Recommended Approach for GM Demo

1. **Modify `handleAsk`** to accept optional `displayType` parameter
2. **Default to "table"** for all demo questions (most reliable)
3. **Create demo question buttons** with pre-configured queries
4. **Keep manual input flexible** - either default to table or let backend auto-detect

This gives you the best of both worlds:
- Controlled, predictable demo experience
- Flexibility for ad-hoc queries
