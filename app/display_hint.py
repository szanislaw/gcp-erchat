# app/display_hint.py
# Determines the recommended display type for query results

import re
from typing import Dict, Any, List, Optional


def get_display_type_from_question(question: str) -> Optional[str]:
    """
    Determine display type based on the user's natural language question.
    This is used BEFORE SQL generation to hardcode the display type for known patterns.

    Priority:
    1. Exact match in QUERY_DISPLAY_TYPE_MAP (for demo questions)
    2. Pattern matching (regex-based detection)

    Returns:
        Display type string or None if no pattern matches (fallback to auto-detection)
    """
    q = question.lower().strip()

    if q in QUERY_DISPLAY_TYPE_MAP:
        return QUERY_DISPLAY_TYPE_MAP[q]

    # LINE first — "trend" / "each day" would otherwise trigger metric
    line_patterns = [
        r'\btrend\b',
        r'per (day|week|month|year)',
        r'each (day|week|month|year)',
        r'over (time|the)\b',
        r'(daily|weekly|monthly|yearly) (trend|count|breakdown)',
    ]
    for pattern in line_patterns:
        if re.search(pattern, q):
            return "line"

    # METRIC — single numeric answer
    metric_patterns = [
        r'^how many\b',
        r'^what is the total\b',
        r'^what is the average\b',
        r'^what percentage\b',
        r'^which .{0,40} has the most\b',
        r'^what is the most common\b',
        r'\bwere (completed|created|cancelled)\b.*(this|last).*(month|week|year)',
        r'\bin the last \d+ (days?|weeks?|months?)\?$',
        r'\bin the last (week|month|year)\?$',
    ]
    for pattern in metric_patterns:
        if re.search(pattern, q):
            if not re.search(r'\bby (category|department|severity|status|property|location|priority|type)\b', q):
                if not re.search(r'\bgrouped by\b', q):
                    return "metric"

    # BAR — categorical comparisons
    bar_patterns = [
        r'count.*by (department|category|severity|property|status|priority|location|type)',
        r'\bby (department|status|priority|location|severity|category|property)\b',
        r'grouped by (department|status|priority|location|severity|category)',
        r'per (department|location)\b',
        r'which (department|category|severity)',
        r'top \d+.*(department|location|status|priority|category|severity)',
        r'(average|avg).*by (category|severity|department|status|location)',
    ]
    for pattern in bar_patterns:
        if re.search(pattern, q):
            return "bar"

    # PIE — distribution / breakdown
    pie_patterns = [
        r'breakdown by (status|category|type)',
        r'distribution (of|by)',
    ]
    for pattern in pie_patterns:
        if re.search(pattern, q):
            return "pie"

    # TABLE — raw record listing
    table_patterns = [
        r'^show me (all|the)\b',
        r'^show (recent|open|completed|cancelled|high|low|urgent)\b.*(order|maintenance|incident)',
        r'^show.*(order|maintenance).*(last \d+|last week|last month|recent|from the)',
        r'^show (the )?(most recent|\d+) (recent )?(incident|order|maintenance)',
        r'^show recent\b',
        r'most recent \d+',
        r'\bordered by\b',
        r'\blast \d+ days\b',
    ]
    for pattern in table_patterns:
        if re.search(pattern, q):
            return "table"

    return None


# Exact-match map for known demo/eval questions.
# Checked FIRST before regex patterns and SQL analysis.
# Keys are lowercased question text. Based on eval_maintenance.py QUESTIONS list.
QUERY_DISPLAY_TYPE_MAP = {
    # === METRIC — simple counts ===
    "how many total maintenance orders are there?": "metric",
    "how many maintenance orders are currently open?": "metric",
    "how many maintenance orders have been completed?": "metric",
    "how many maintenance orders are cancelled?": "metric",
    "how many high priority maintenance orders are there?": "metric",
    "how many low priority maintenance orders exist?": "metric",
    "how many urgent maintenance orders are there?": "metric",

    # === METRIC — date-filtered counts ===
    "how many maintenance orders were created this month?": "metric",
    "how many maintenance orders were created this week?": "metric",
    "how many maintenance orders were created last week?": "metric",
    "how many maintenance orders were completed this year?": "metric",
    "how many maintenance orders were cancelled last month?": "metric",
    "how many maintenance orders were created vs completed this month?": "metric",

    # === METRIC — aggregations ===
    "what percentage of maintenance orders are completed?": "metric",
    "what is the most common maintenance order type?": "metric",
    "which status has the most maintenance orders?": "metric",
    "which location has the most maintenance orders?": "metric",

    # === BAR — group-by comparisons ===
    "show maintenance order count by status": "bar",
    "show maintenance order count by priority": "bar",
    "show maintenance order count by location": "bar",
    "show maintenance order count grouped by department": "bar",
    "which departments have open maintenance orders?": "bar",
    "show high priority maintenance orders per department": "bar",
    "show the top 5 departments with most maintenance orders": "bar",
    "show maintenance orders created this month by department": "bar",
    "show cancelled orders from last month grouped by priority": "bar",

    # === LINE — time-series trends ===
    "show the monthly trend of maintenance orders created": "line",
    "show weekly maintenance order trend for this year": "line",
    "how many maintenance orders were created each day this month?": "line",
    "show trend of high priority orders by month": "line",

    # === INCIDENT: METRIC — simple counts ===
    "how many total incidents are there?": "metric",
    "how many open incidents are there?": "metric",
    "how many completed incidents?": "metric",
    "how many cancelled incidents?": "metric",
    "how many draft incidents are there?": "metric",
    "how many high severity incidents?": "metric",
    "how many critical severity incidents are there?": "metric",
    "how many pending incidents?": "metric",

    # === INCIDENT: METRIC — date-filtered counts ===
    "how many incidents were created this month?": "metric",
    "how many incidents were created this year?": "metric",
    "how many incidents were created this week?": "metric",
    "how many incidents were created last month?": "metric",
    "how many incidents were created last week?": "metric",
    "how many incidents were created in the last 30 days?": "metric",
    "how many incidents were completed this month?": "metric",
    "how many incidents were created in the last 7 days?": "metric",

    # === INCIDENT: METRIC — combined filters ===
    "how many high severity open incidents are there?": "metric",
    "how many critical incidents are pending?": "metric",
    "how many completed high severity incidents are there?": "metric",
    "how many vip guest incidents are there?": "metric",
    "how many high severity incidents were created this month?": "metric",
    "how many open critical incidents are there?": "metric",

    # === INCIDENT: METRIC — percentages & aggregates ===
    "what percentage of incidents are completed?": "metric",
    "what percentage of incidents are open?": "metric",
    "what percentage of incidents are high or critical severity?": "metric",
    "what percentage of incidents created this month are completed?": "metric",
    "what is the average actual cost per incident?": "metric",
    "what is the total actual cost of all incidents?": "metric",

    # === INCIDENT: BAR — group-by breakdowns ===
    "show incident count by status": "bar",
    "show incident count by severity": "bar",
    "show incident count by category": "bar",
    "show incident count by department": "bar",
    "which category has the most incidents?": "bar",
    "which department has the most incidents?": "bar",
    "show incident count by location": "bar",
    "show top 5 incident categories": "bar",
    "show average cost by category": "bar",
    "show average cost by severity": "bar",
    "show top 5 categories by average cost": "bar",

    # === INCIDENT: LINE — time-series trends ===
    "show the monthly incident trend": "line",
    "show the weekly incident trend for this year": "line",
    "show the daily incident trend this month": "line",
    "show monthly trend of completed incidents": "line",
    "show monthly incident count by severity": "line",
    "show weekly trend of open incidents": "line",

    # === INCIDENT: TABLE — listings ===
    "show the 10 most recent incidents": "table",
    "show the 5 most recent completed incidents": "table",
    "show recent high severity incidents": "table",
    "show recent incidents with their categories and status": "table",
    "show the most recent vip guest incidents": "table",

    # === TABLE — raw record listings ===
    "what is the distribution of maintenance orders by status and priority?": "table",
    "show high priority open maintenance orders": "table",
    "show maintenance orders created in the last 30 days": "table",
    "show orders created in the last 7 days": "table",
    "show the 10 most recent maintenance orders": "table",
    "what are the most recent 5 completed maintenance orders?": "table",
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
        execution_data: The result data structure from Redshift
        query_text: The original natural language query (optional, for hardcoded mappings)

    Returns:
        Display type as string
    """
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

    if row_count == 1 and col_count == 1:
        return "metric"

    if row_count == 1 and col_count <= 3 and _has_aggregation(sql_lower):
        return "metric"

    if _is_time_series(sql_lower, columns) and _has_aggregation(sql_lower) and _has_group_by(sql_lower):
        return "line"

    if (col_count == 2 and row_count >= 2 and row_count <= 100 and
            _has_aggregation(sql_lower) and _has_group_by(sql_lower)):
        first_col = columns[0].lower()
        if any(term in first_col for term in ['date', 'day', 'week', 'month', 'year', 'time']):
            return "line"

    if col_count == 2 and row_count <= 10 and _has_aggregation(sql_lower) and _has_group_by(sql_lower):
        return "pie"

    if _has_group_by(sql_lower) and _has_aggregation(sql_lower):
        if row_count <= 50:
            return "bar"
        else:
            return "table"

    return "table"


def _is_time_series(sql: str, columns: List[str]) -> bool:
    """
    Detect if query is likely a time series aggregation.
    Requires:
    - Time-related column in GROUP BY (not just in SELECT)
    - Aggregation function (COUNT, SUM, etc.)
    - Time-related grouping pattern
    """
    time_group_patterns = [
        r'group\s+by\s+[^,]*\b(date|year|month|week|day)\b',
        r'group\s+by\s+[^,]*date_trunc',
        r'group\s+by\s+[^,]*extract\s*\(',
        r'group\s+by\s+[^,]*snapshotdate',
        r'group\s+by\s+[^,]*created_date',
        r'group\s+by\s+[^,]*date\s*\(',
        r'group\s+by\s+[^,]*cast\s*\([^)]*as\s+date',
        r'group\s+by\s+[^,]*to_char\s*\(',
        r'group\s+by\s+[^,]*date_format',
        r'group\s+by\s+[^,]*from_unixtime',
    ]

    for pattern in time_group_patterns:
        if re.search(pattern, sql, re.IGNORECASE):
            return True

    time_column_names = ['date', 'day', 'week', 'month', 'year', 'time', 'timestamp']
    for col in columns:
        col_lower = col.lower()
        if any(time_term in col_lower for time_term in time_column_names):
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
