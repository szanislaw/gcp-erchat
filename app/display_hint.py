# app/display_hint.py
# Determines the recommended display type for query results

import re
from typing import Dict, Any, List


def get_display_type(sql: str, execution_data: Dict[str, Any]) -> str:
    """
    Determine the recommended display type for query results.
    Uses hardcoded heuristics based on SQL query patterns and result structure.
    
    Display types:
    - "line": Time series data (best for line graphs)
    - "bar": Categorical aggregations (best for bar charts)
    - "pie": Single metric with categories (best for pie charts)
    - "table": Default tabular view (default)
    
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
    
    # Check for time series patterns
    if _is_time_series(sql_lower, columns):
        return "line"
    
    # Check for pie chart candidates (single metric with categories, limited rows)
    if col_count == 2 and row_count <= 10 and _has_aggregation(sql_lower):
        return "pie"
    
    # Check for bar chart candidates (aggregations with GROUP BY)
    if _has_group_by(sql_lower) and _has_aggregation(sql_lower):
        if row_count <= 50:  # Reasonable for bar chart
            return "bar"
        else:
            return "table"  # Too many rows for bar chart
    
    # Default to table view
    return "table"


def _is_time_series(sql: str, columns: List[str]) -> bool:
    """
    Detect if query is likely a time series.
    Looks for date/time columns and time-based grouping.
    """
    # Common time-related column patterns
    time_patterns = [
        r'\bdate\b', r'\btime\b', r'\btimestamp\b', 
        r'\byear\b', r'\bmonth\b', r'\bday\b',
        r'\bcreated\b', r'\bupdated\b', r'\boccurred\b'
    ]
    
    # Check SQL for time-related terms
    for pattern in time_patterns:
        if re.search(pattern, sql):
            # Also check for ORDER BY (common in time series)
            if 'order by' in sql:
                return True
    
    # Check column names
    for col in columns:
        col_lower = col.lower()
        if any(term in col_lower for term in ['date', 'time', 'year', 'month', 'day', 'created', 'updated']):
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
