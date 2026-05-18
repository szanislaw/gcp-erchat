import re
from typing import List, Set

# Forbidden SQL operations (case-insensitive)
FORBIDDEN = re.compile(r"\b(drop|delete|update|insert|alter|truncate|grant|revoke|create)\b", re.I)
REDSHIFT_UNSUPPORTED = ["distinct on", "returning", "for update", "for share"]

# Comprehensive table extraction patterns for ~90% accuracy
TABLE_PATTERNS = [
    r'\bfrom\s+([a-zA-Z_][\w]*)',                          # FROM table
    r'\bjoin\s+([a-zA-Z_][\w]*)',                          # JOIN table  
    r'\binner\s+join\s+([a-zA-Z_][\w]*)',                  # INNER JOIN table
    r'\bleft\s+(?:outer\s+)?join\s+([a-zA-Z_][\w]*)',      # LEFT [OUTER] JOIN table
    r'\bright\s+(?:outer\s+)?join\s+([a-zA-Z_][\w]*)',     # RIGHT [OUTER] JOIN table
    r'\bfull\s+(?:outer\s+)?join\s+([a-zA-Z_][\w]*)',      # FULL [OUTER] JOIN table
    r'\bcross\s+join\s+([a-zA-Z_][\w]*)',                  # CROSS JOIN table
    r'\bnatural\s+join\s+([a-zA-Z_][\w]*)',                # NATURAL JOIN table
]

# SQL keywords that should not be treated as table names
SQL_KEYWORDS = {
    'select', 'from', 'where', 'and', 'or', 'not', 'in', 'is', 'null',
    'true', 'false', 'as', 'on', 'using', 'group', 'by', 'order', 'having',
    'limit', 'offset', 'union', 'intersect', 'except', 'case', 'when', 'then',
    'else', 'end', 'cast', 'between', 'like', 'ilike', 'exists', 'any', 'all',
    'distinct', 'asc', 'desc', 'nulls', 'first', 'last', 'over', 'partition',
    'row', 'rows', 'range', 'preceding', 'following', 'current', 'unbounded',
    'lateral', 'cross', 'inner', 'outer', 'left', 'right', 'full', 'natural',
    'join', 'with', 'recursive', 'values', 'default', 'set', 'coalesce',
    'greatest', 'least', 'date', 'time', 'timestamp', 'interval',
    # Common words that appear in SQL but are not tables
    'the', 'a', 'an', 'other', 'another', 'this', 'that', 'these', 'those',
    'each', 'every', 'some', 'many', 'few', 'several', 'both', 'either', 'neither',
    # Date/time keywords
    'year', 'month', 'day', 'hour', 'minute', 'second', 'week', 'quarter'
}


def extract_tables(sql: str) -> Set[str]:
    """
    Extract all table names from SQL query using comprehensive pattern matching.
    Filters out SQL keywords and common English words that might be falsely detected.
    
    Args:
        sql: SQL query string
        
    Returns:
        Set of table names found in query (lowercase)
    """
    if not sql:
        return set()
    
    found_tables = set()
    # Strip function calls that contain FROM (EXTRACT, SUBSTRING) so their
    # arguments aren't mistaken for table names by the FROM pattern.
    sql_scrubbed = re.sub(r'\b(?:EXTRACT|SUBSTRING)\s*\([^)]+\)', '__FUNC__', sql, flags=re.IGNORECASE)
    sql_lower = sql_scrubbed.lower()

    for pattern in TABLE_PATTERNS:
        matches = re.findall(pattern, sql_lower, re.IGNORECASE)
        for match in matches:
            # Clean the match (remove leading/trailing whitespace)
            match = match.strip()
            
            # Skip if empty after stripping
            if not match:
                continue
            
            # Filter out SQL keywords and common words
            if match.lower() in SQL_KEYWORDS:
                continue
            
            # Additional validation: table names should be valid identifiers
            # Must start with letter or underscore, contain only alphanumeric and underscore
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', match):
                continue
            
            # Skip very short names (1-2 chars) that are likely not real tables
            if len(match) <= 2:
                continue

            # Skip built-in pseudo-columns and system functions
            if match.lower() in {'current_date', 'current_time', 'current_timestamp',
                                   'localtime', 'localtimestamp', 'now'}:
                continue
            
            found_tables.add(match.lower())
    
    return found_tables


def validate_sql(sql: str, allowed_tables: List[str], dialect: str) -> str:
    """
    Validate SQL query for security and authorization.
    
    Args:
        sql: SQL query string
        allowed_tables: List of tables the user is allowed to query
        dialect: SQL dialect (e.g., 'redshift')

    Returns:
        The validated SQL string

    Raises:
        ValueError: If SQL fails validation
    """
    if not sql:
        raise ValueError("Empty SQL")

    sql_stripped = sql.strip()

    # Check for forbidden operations
    if FORBIDDEN.search(sql_stripped):
        forbidden_match = FORBIDDEN.search(sql_stripped)
        raise ValueError(f"Forbidden SQL operation: {forbidden_match.group()}")

    # Check for dialect-specific unsupported features
    if dialect == "redshift":
        sql_lower = sql_stripped.lower()
        for kw in REDSHIFT_UNSUPPORTED:
            if kw in sql_lower:
                raise ValueError(f"Redshift does not support: {kw}")

    # Extract and validate tables - case-insensitive comparison
    found_tables = extract_tables(sql_stripped)
    allowed_tables_lower = set(t.lower() for t in allowed_tables)

    # CTE aliases (e.g. WITH prev AS (...)) are not real tables — exclude from check
    cte_aliases = {m.lower() for m in re.findall(r'\b(\w+)\s+AS\s*\(', sql_stripped, re.IGNORECASE)}
    found_tables -= cte_aliases

    unauthorized_tables = found_tables - allowed_tables_lower
    if unauthorized_tables:
        raise ValueError(
            f"Unauthorized table(s): {', '.join(sorted(unauthorized_tables))}. "
            f"Allowed tables: {', '.join(allowed_tables)}"
        )

    return sql_stripped
