# app/display_hint.py
# Determines the recommended display type for query results

import re
from typing import Dict, Any, List


def get_display_type(sql: str, execution_data: Dict[str, Any]) -> str:
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
        
    Returns:
        Display type as string
    """
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
