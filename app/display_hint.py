# app/display_hint.py
# Determines the recommended display type for query results

import re
from typing import Dict, Any, List, Optional


def get_display_type_from_question(question: str) -> Optional[str]:
    """
    Determine display type based on the user's natural language question.
    This is used BEFORE SQL generation to hardcode the display type for known patterns.
    
    Returns:
        Display type string or None if no pattern matches (fallback to auto-detection)
    """
    q = question.lower().strip()
    
    # METRIC patterns (single numeric value)
    metric_patterns = [
        r'^how many\b.*\?$',  # "How many incidents..."
        r'^what is the total\b',  # "What is the total cost..."
        r'^what is the average\b.*\?$',  # "What is the average..." (without "by")
        r'\bwere (reported|completed|created)\b.*today',  # "...reported today"
        r'\bin the last \d+ days\?$',  # Ends with "in the last X days?"
        r'\bin the last (week|month|year)\?$',  # Ends with time period
    ]
    
    for pattern in metric_patterns:
        if re.search(pattern, q):
            # But NOT if it has aggregation by category
            if not re.search(r'\bby (category|department|severity|status|property)', q):
                return "metric"
    
    # PIE patterns (category breakdown, limited categories)
    pie_patterns = [
        r'breakdown by (severity|status|category)',
        r'count.*by status',
        r'distribution by',
        r'most common .* incidents',  # "most common Room Cleanliness incidents"
    ]
    
    for pattern in pie_patterns:
        if re.search(pattern, q):
            return "pie"
    
    # BAR patterns (category comparison, rankings)
    bar_patterns = [
        r'count.*by (department|category|property)',
        r'which department',
        r'average.*by category',
        r'each property have',
        r'by department',
    ]
    
    for pattern in bar_patterns:
        if re.search(pattern, q):
            return "bar"
    
    # LINE patterns (time series)
    line_patterns = [
        r'per (day|week|month|year)',
        r'over (time|the)',
        r'trend',
        r'incidents from last \d+ days.*per day',
    ]
    
    for pattern in line_patterns:
        if re.search(pattern, q):
            return "line"
    
    # TABLE patterns (lists, details, filtering)
    table_patterns = [
        r'^show me (all|the)',  # "Show me all pending..."
        r'^show (recent|high|medium|low)',  # "Show recent incidents..."
        r'incidents (from|at|in)',  # "incidents from last week", "incidents at room"
        r'top \d+',  # "top 5 incidents"
        r'ordered by',
        r'pending incidents',
        r'at room \d+',
    ]
    
    for pattern in table_patterns:
        if re.search(pattern, q):
            return "table"
    
    # No pattern matched - return None to use auto-detection
    return None

# Hardcoded query-to-display-type mapping for GM Demo Questions
# Maps natural language queries to their desired display types
QUERY_DISPLAY_TYPE_MAP = {
    # OPERATIONAL OVERVIEW
    "how many incidents do we have?": "metric",
    "show me all pending incidents": "table",
    "count incidents by category": "bar",
    "show incidents from last 7 days": "table",
    "how many high severity incidents are there?": "metric",
    
    # GUEST EXPERIENCE
    "show me incidents for food and beverage category": "table",
    "what are the most common incident categories?": "bar",
    "show high severity incidents that are still pending": "table",
    "show me all incidents at location room 1018": "table",
    
    # FINANCIAL IMPACT
    "what is the total actual cost of all incidents?": "metric",
    "show me the incidents with highest actual cost": "table",
    "what is the average actual cost by category?": "bar",
    
    # PERFORMANCE ANALYTICS
    "which category has the most incidents?": "bar",
    "show incident breakdown by severity": "pie",
    "show recent incidents with medium severity": "table",
    
    # STRATEGIC INSIGHTS
    "how many incidents were completed?": "metric",
    "how many incidents does each property have?": "bar",
    "show me incidents ordered by severity": "table",
    "count incidents by status": "pie",
}


def get_display_type(sql: str, execution_data: Dict[str, Any], query_text: str = None) -> str:
    """
    Determine the recommended display type for query results.
    Uses hardcoded heuristics based on SQL query patterns and result structure.
    
    Display types:
    - "line": Time series data with aggregations (best for line graphs)
    - "bar": Categorical aggregations (best for bar charts)
    - "pie": Single metric with categories (best for pie charts)
    - "metric": Single numeric value (best for KPI cards)
    - "table": Default tabular view (default for raw records)
    
    Args:
        sql: The SQL query that was executed
        execution_data: The result data structure from Athena
        query_text: The original natural language query (optional, for hardcoded mappings)
        
    Returns:
        Display type as string
    """
    # Check hardcoded query mapping first (for GM demo questions)
    if query_text:
        normalized_query = query_text.lower().strip()
        if normalized_query in QUERY_DISPLAY_TYPE_MAP:
            return QUERY_DISPLAY_TYPE_MAP[normalized_query]
    
    if not execution_data or not execution_data.get("rows"):
        return "table"
    
    sql_lower = sql.lower()
    columns = execution_data.get("columns", [])
    rows = execution_data.get("rows", [])
    row_count = len(rows)
    col_count = len(columns)
    
    # Single value result (e.g., COUNT(*)) - use metric/card display
    if row_count == 1 and col_count == 1:
        return "metric"
    
    # Single row with few columns - also metric-like
    if row_count == 1 and col_count <= 3 and _has_aggregation(sql_lower):
        return "metric"
    
    # Check for time series patterns - MUST have aggregation + time grouping
    # Raw records with date columns should NOT be line charts
    if _is_time_series(sql_lower, columns) and _has_aggregation(sql_lower) and _has_group_by(sql_lower):
        return "line"
    
    # Additional time series detection: if we have 2 columns, multiple rows, 
    # aggregation, GROUP BY, and first column looks like a date, it's likely time series
    if (col_count == 2 and row_count >= 2 and row_count <= 100 and 
        _has_aggregation(sql_lower) and _has_group_by(sql_lower)):
        first_col = columns[0].lower()
        if any(term in first_col for term in ['date', 'day', 'week', 'month', 'year', 'time']):
            return "line"
    
    # Check for pie chart candidates (single metric with categories, limited rows)
    if col_count == 2 and row_count <= 10 and _has_aggregation(sql_lower) and _has_group_by(sql_lower):
        return "pie"
    
    # Check for bar chart candidates (aggregations with GROUP BY)
    if _has_group_by(sql_lower) and _has_aggregation(sql_lower):
        if row_count <= 50:  # Reasonable for bar chart
            return "bar"
        else:
            return "table"  # Too many rows for bar chart
    
    # Default to table view (raw records, SELECT *, etc.)
    return "table"


def _is_time_series(sql: str, columns: List[str]) -> bool:
    """
    Detect if query is likely a time series aggregation.
    Requires:
    - Time-related column in GROUP BY (not just in SELECT)
    - Aggregation function (COUNT, SUM, etc.)
    - Time-related grouping pattern
    """
    # Check for time-related GROUP BY patterns (actual time series)
    time_group_patterns = [
        r'group\s+by\s+[^,]*\b(date|year|month|week|day)\b',
        r'group\s+by\s+[^,]*date_trunc',
        r'group\s+by\s+[^,]*extract\s*\(',
        r'group\s+by\s+[^,]*snapshotdate',
        r'group\s+by\s+[^,]*created_date',
        r'group\s+by\s+[^,]*date\s*\(',  # DATE() function
        r'group\s+by\s+[^,]*cast\s*\([^)]*as\s+date',  # CAST(... AS DATE)
        r'group\s+by\s+[^,]*to_char\s*\(',  # TO_CHAR date formatting
        r'group\s+by\s+[^,]*date_format',  # DATE_FORMAT
        r'group\s+by\s+[^,]*from_unixtime',  # FROM_UNIXTIME
    ]
    
    for pattern in time_group_patterns:
        if re.search(pattern, sql, re.IGNORECASE):
            return True
    
    # Also check column names for time-related terms
    time_column_names = ['date', 'day', 'week', 'month', 'year', 'time', 'timestamp']
    for col in columns:
        col_lower = col.lower()
        if any(time_term in col_lower for time_term in time_column_names):
            # If we have a time-named column AND it's likely grouped, treat as time series
            if re.search(r'group\s+by', sql, re.IGNORECASE):
                return True
    
    return False


def _has_group_by(sql: str) -> bool:
    """Check if SQL contains GROUP BY clause."""
    return bool(re.search(r'\bgroup\s+by\b', sql))


def _has_aggregation(sql: str) -> bool:
    """Check if SQL contains aggregation functions."""
    agg_functions = [
        r'\bcount\s*\(', r'\bsum\s*\(', r'\bavg\s*\(',
        r'\bmin\s*\(', r'\bmax\s*\(', r'\bstddev\s*\(',
        r'\bvariance\s*\('
    ]
    return any(re.search(pattern, sql) for pattern in agg_functions)
