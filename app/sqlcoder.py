"""
Enhanced SQL code generation module with:
- Thread-safe model access
- LRU caching for repeated queries
- Better error handling
- Memory optimization
"""

import time
import re
import os
import torch
import threading
import hashlib
from functools import lru_cache
from transformers import AutoTokenizer, AutoModelForCausalLM
from typing import Dict, Optional, Tuple
import logging

# Reduce CUDA memory fragmentation when processing many sequential requests
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

logger = logging.getLogger(__name__)

# Thread lock for model access
_model_lock = threading.Lock()

_model = None
_tokenizer = None

SELECT_REGEX = re.compile(
    r"(select\s+.*?)(;|\Z)",
    re.IGNORECASE | re.DOTALL
)

# LRU cache for SQL generation results
_sql_cache: Dict[str, dict] = {}
_CACHE_MAX_SIZE = 500

BIGINT_TIMESTAMP_COLUMNS = (
    "created_date",
    "incident_time",
    "completed_date",
    "cancelled_date",
)

_BIGINT_COLUMN_PATTERN = "|".join(BIGINT_TIMESTAMP_COLUMNS)
_QUALIFIED_BIGINT_COLUMN_PATTERN = rf"(?:\b\w+\.)?(?:{_BIGINT_COLUMN_PATTERN})\b"
_CLAUSE_BOUNDARY = r"(?=\s+(?:and|or|group\s+by|order\s+by|limit|having)\b|$)"
_DATE_LITERAL_RE = re.compile(r"^'?\d{4}-\d{2}-\d{2}'?$", re.IGNORECASE)
_DATE_EXPR_RE = re.compile(
    r"\b(current_date|current_timestamp|date_add\s*\(|date_parse\s*\(|date_trunc\s*\(|from_iso8601_date\s*\(|cast\s*\(.*?\bas\s+date\b|date\s*')",
    re.IGNORECASE,
)


def _get_cache_key(prompt: str, max_tokens: int) -> str:
    """Generate cache key from prompt and parameters"""
    content = f"{prompt}::{max_tokens}"
    return hashlib.md5(content.encode()).hexdigest()


def load_model():
    """Load the SQL generation model. Thread-safe.

    Set USE_QUANTIZATION=true in .env to enable 4-bit quantization (~4-5GB VRAM, slower).
    Default is float16 (~13GB VRAM, faster, better quality) — recommended for L4 (23GB).
    """
    global _model, _tokenizer

    with _model_lock:
        if _model is not None:
            return

        model_name = "defog/sqlcoder-7b-2"
        use_quantization = os.getenv("USE_QUANTIZATION", "false").lower() == "true"

        if use_quantization:
            from transformers import BitsAndBytesConfig
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
            )
            logger.info(f"[BOOT] Loading {model_name} (4-bit quantized)...")
            kwargs = {"quantization_config": quantization_config, "device_map": "auto"}
        else:
            logger.info(f"[BOOT] Loading {model_name} (float16, no quantization)...")
            kwargs = {"torch_dtype": torch.float16, "device_map": "auto"}

        _tokenizer = AutoTokenizer.from_pretrained(model_name)
        _model = AutoModelForCausalLM.from_pretrained(model_name, **kwargs)

        device = next(_model.parameters()).device
        logger.info(f"[BOOT] {model_name} loaded successfully on {device} (quantized={use_quantization})")


def fix_date_comparisons(sql: str) -> str:
    """
    Fix common date comparison issues for Athena.
    
    snapshotdate is stored as VARCHAR (string) like '2025-01-23',
    so direct comparisons with date functions fail.
    
    This fixes patterns like:
    - snapshotdate >= date_add(...) → date_parse(snapshotdate, '%Y-%m-%d') >= date_add(...)
    - snapshotdate <= current_date → date_parse(snapshotdate, '%Y-%m-%d') <= current_date
    - snapshotdate BETWEEN ... → date_parse(snapshotdate, '%Y-%m-%d') BETWEEN ...
    - year(snapshotdate) → year(date_parse(snapshotdate, '%Y-%m-%d'))
    - month(snapshotdate) → month(date_parse(snapshotdate, '%Y-%m-%d'))
    - date_trunc('month', snapshotdate) → date_trunc('month', date_parse(snapshotdate, '%Y-%m-%d'))

    Each fix targets specific patterns and won't double-wrap already-fixed instances.
    """
    if not sql:
        return sql
    
    # Fix 1: Date extraction functions - year(snapshotdate), month(snapshotdate), day(snapshotdate), etc.
    date_func_pattern = re.compile(
        r'\b(year|month|day|hour|minute|second|date|week)\s*\(\s*snapshotdate\s*\)',
        re.IGNORECASE
    )
    
    def replace_date_func(match):
        func_name = match.group(1)
        return f"{func_name}(date_parse(snapshotdate, '%Y-%m-%d'))"
    
    sql = date_func_pattern.sub(replace_date_func, sql)
    
    # Fix 1b: date_trunc('interval', snapshotdate) → date_trunc('interval', date_parse(...))
    date_trunc_pattern = re.compile(
        r"date_trunc\s*\(\s*(['\"][^'\"]+['\"])\s*,\s*snapshotdate\s*\)",
        re.IGNORECASE
    )
    
    def replace_date_trunc(match):
        interval = match.group(1)
        return f"date_trunc({interval}, date_parse(snapshotdate, '%Y-%m-%d'))"
    
    sql = date_trunc_pattern.sub(replace_date_trunc, sql)
    
    # Fix 2: Direct comparisons - snapshotdate >= date_add(...), snapshotdate BETWEEN ..., etc.
    date_comparison_pattern = re.compile(
        r'\bsnapshotdate\s*([><=!]+|BETWEEN)\s*',
        re.IGNORECASE
    )
    
    def replace_snapshotdate(match):
        operator = match.group(1)
        return f"date_parse(snapshotdate, '%Y-%m-%d') {operator} "
    
    fixed_sql = date_comparison_pattern.sub(replace_snapshotdate, sql)

    # Fix 3: Reverse comparison — <date_expr> [op] snapshotdate (snapshotdate on right side)
    # e.g., date_trunc('week', current_date) <= snapshotdate
    # Negative lookahead (?!\s*,) prevents matching snapshotdate inside date_parse(snapshotdate, ...)
    reverse_comparison_pattern = re.compile(
        r'([><=!]+)\s*\bsnapshotdate\b(?!\s*,)',
        re.IGNORECASE
    )

    def replace_reverse_snapshotdate(match):
        op = match.group(1)
        return f"{op} date_parse(snapshotdate, '%Y-%m-%d')"

    fixed_sql = reverse_comparison_pattern.sub(replace_reverse_snapshotdate, fixed_sql)

    if fixed_sql != sql:
        logger.debug(f"Fixed date comparison: {sql[:100]}... → {fixed_sql[:100]}...")

    return fixed_sql


def fix_interval_syntax(sql: str) -> str:
    """
    Convert PostgreSQL-style INTERVAL arithmetic to Athena date_add() calls.

    Athena (Presto) does not support:
      current_date - INTERVAL 'N days'
      current_date + INTERVAL 'N days'

    Converts to:
      date_add('day', -N, current_date)
      date_add('day', N, current_date)

    Handles: 'N day', 'N days', 'N week', 'N weeks', 'N month', 'N months'
    """
    if not sql or "interval" not in sql.lower():
        return sql

    _UNIT_MAP = {
        "day": "day", "days": "day",
        "week": "week", "weeks": "week",
        "month": "month", "months": "month",
    }

    def _replace(match: re.Match) -> str:
        sign = match.group(1)  # '+' or '-'
        amount = int(match.group(2))
        unit_raw = match.group(3).lower()
        unit = _UNIT_MAP.get(unit_raw, unit_raw)
        delta = amount if sign == "+" else -amount
        return f"date_add('{unit}', {delta}, current_date)"

    pattern = re.compile(
        r"current_date\s*([+-])\s*INTERVAL\s*['\"](\d+)\s+(\w+)['\"]",
        re.IGNORECASE,
    )
    fixed = pattern.sub(_replace, sql)
    if fixed != sql:
        logger.info("Converted INTERVAL arithmetic to date_add() for Athena compatibility")
    return fixed


def _looks_like_date_expression(expr: str) -> bool:
    """Check if SQL expression is date-like (DATE/TIMESTAMP function or yyyy-mm-dd literal)."""
    candidate = expr.strip()
    if _DATE_LITERAL_RE.match(candidate):
        return True
    return bool(_DATE_EXPR_RE.search(candidate))


def fix_bigint_date_comparisons(sql: str) -> str:
    """
    Fix Athena type mismatches where BIGINT timestamp columns are compared to DATE.

    Rewrites date-based predicates on bigint timestamp columns to use snapshotdate,
    which is the canonical date partition used for date filtering.
    """
    if not sql:
        return sql

    original_sql = sql

    # Normalize CAST/DATE wrappers around BIGINT timestamp columns.
    sql = re.sub(
        rf"\bcast\s*\(\s*{_QUALIFIED_BIGINT_COLUMN_PATTERN}\s+as\s+date\s*\)",
        "date_parse(snapshotdate, '%Y-%m-%d')",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(
        rf"\bdate\s*\(\s*{_QUALIFIED_BIGINT_COLUMN_PATTERN}\s*\)",
        "date_parse(snapshotdate, '%Y-%m-%d')",
        sql,
        flags=re.IGNORECASE,
    )

    # BIGINT timestamp comparison with DATE expression.
    comparison_pattern = re.compile(
        rf"{_QUALIFIED_BIGINT_COLUMN_PATTERN}\s*(<=|>=|<|>|=)\s*(.+?){_CLAUSE_BOUNDARY}",
        re.IGNORECASE,
    )

    def _replace_comparison(match: re.Match) -> str:
        operator = match.group(1)
        rhs = match.group(2).strip()
        if _looks_like_date_expression(rhs):
            return f"date_parse(snapshotdate, '%Y-%m-%d') {operator} {rhs}"
        return match.group(0)

    sql = comparison_pattern.sub(_replace_comparison, sql)

    # DATE expression compared to BIGINT timestamp column (reversed operands).
    reverse_comparison_pattern = re.compile(
        rf"(.+?)\s*(<=|>=|<|>|=)\s*({_QUALIFIED_BIGINT_COLUMN_PATTERN}){_CLAUSE_BOUNDARY}",
        re.IGNORECASE,
    )

    def _replace_reverse_comparison(match: re.Match) -> str:
        lhs = match.group(1).strip()
        operator = match.group(2)
        if _looks_like_date_expression(lhs):
            return f"{lhs} {operator} date_parse(snapshotdate, '%Y-%m-%d')"
        return match.group(0)

    sql = reverse_comparison_pattern.sub(_replace_reverse_comparison, sql)

    # BETWEEN predicates on BIGINT timestamp columns.
    between_pattern = re.compile(
        rf"{_QUALIFIED_BIGINT_COLUMN_PATTERN}\s+between\s+(.+?)\s+and\s+(.+?){_CLAUSE_BOUNDARY}",
        re.IGNORECASE,
    )

    def _replace_between(match: re.Match) -> str:
        start_expr = match.group(1).strip()
        end_expr = match.group(2).strip()
        if _looks_like_date_expression(start_expr) or _looks_like_date_expression(end_expr):
            return (
                f"date_parse(snapshotdate, '%Y-%m-%d') BETWEEN {start_expr} AND {end_expr}"
            )
        return match.group(0)

    sql = between_pattern.sub(_replace_between, sql)

    if sql != original_sql:
        logger.info("Rewrote bigint/date predicates to snapshotdate for Athena compatibility")

    return sql


def fix_date_part(sql: str) -> str:
    """
    Convert date_part() / EXTRACT() calls on snapshotdate to Athena-compatible equivalents.

    Athena supports these functions on DATE/TIMESTAMP types, but snapshotdate is VARCHAR,
    so it must be wrapped with date_parse() first. Only targets snapshotdate — leaves
    date_part()/EXTRACT() on other columns untouched.

    Converts:
      date_part('year', [alias.]snapshotdate)          → year(date_parse(snapshotdate, '%Y-%m-%d'))
      EXTRACT(YEAR FROM [alias.]snapshotdate)           → year(date_parse(snapshotdate, '%Y-%m-%d'))
    """
    if not sql:
        return sql

    _PART_FUNC = {
        "year": "year", "month": "month", "day": "day",
        "week": "week", "hour": "hour", "minute": "minute", "second": "second",
        "dow": "day_of_week", "doy": "day_of_year",
    }
    _WRAPPED = "date_parse(snapshotdate, '%Y-%m-%d')"

    original = sql

    def _replace_date_part(m):
        part = m.group(1).lower().strip("'\"")
        func = _PART_FUNC.get(part, part)
        return f"{func}({_WRAPPED})"

    def _replace_extract(m):
        part = m.group(1).lower()
        func = _PART_FUNC.get(part, part)
        return f"{func}({_WRAPPED})"

    # date_part('year', [alias.]snapshotdate)
    sql = re.sub(
        r"date_part\s*\(\s*['\"]?(\w+)['\"]?\s*,\s*(?:\w+\.)?snapshotdate\s*\)",
        _replace_date_part, sql, flags=re.IGNORECASE
    )
    # date_part('year', date_parse(snapshotdate, ...))  — already wrapped by fix_date_comparisons
    sql = re.sub(
        r"date_part\s*\(\s*['\"]?(\w+)['\"]?\s*,\s*date_parse\s*\(\s*(?:\w+\.)?snapshotdate\s*,[^)]+\)\s*\)",
        _replace_date_part, sql, flags=re.IGNORECASE
    )

    # EXTRACT(YEAR FROM [alias.]snapshotdate)
    sql = re.sub(
        r"EXTRACT\s*\(\s*(\w+)\s+FROM\s+(?:\w+\.)?snapshotdate\s*\)",
        _replace_extract, sql, flags=re.IGNORECASE
    )
    # EXTRACT(YEAR FROM date_parse(snapshotdate, ...))  — already wrapped
    sql = re.sub(
        r"EXTRACT\s*\(\s*(\w+)\s+FROM\s+date_parse\s*\(\s*(?:\w+\.)?snapshotdate\s*,[^)]+\)\s*\)",
        _replace_extract, sql, flags=re.IGNORECASE
    )

    if sql != original:
        logger.info("Converted date_part()/EXTRACT() on snapshotdate to Athena-compatible functions")
    return sql


def fix_group_by_aliases(sql: str) -> str:
    """
    Replace SELECT aliases used in GROUP BY with ordinal positions.

    Athena (Presto) does not support referencing SELECT aliases in GROUP BY.
    Detects aliases defined as 'AS alias' in SELECT and replaces matching
    GROUP BY terms with their 1-based ordinal position.

    Only replaces exact alias matches — real column names in GROUP BY are left alone.
    """
    if not sql or "group by" not in sql.lower():
        return sql

    select_match = re.search(r'\bSELECT\b\s+(.+?)\s+\bFROM\b', sql, re.IGNORECASE | re.DOTALL)
    if not select_match:
        return sql

    # Split SELECT items by top-level commas (skip commas inside parentheses)
    select_str = select_match.group(1)
    items, depth, current = [], 0, []
    for ch in select_str:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        if ch == ',' and depth == 0:
            items.append(''.join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        items.append(''.join(current).strip())

    # Build alias → ordinal map (only explicit AS aliases)
    alias_map = {}
    for pos, item in enumerate(items, start=1):
        m = re.search(r'\bAS\s+(\w+)\s*$', item, re.IGNORECASE)
        if m:
            alias_map[m.group(1).lower()] = pos

    if not alias_map:
        return sql

    def _replace_group_by(match):
        cols = re.split(r',\s*', match.group(1).strip())
        fixed = []
        for col in cols:
            col_clean = col.strip()
            if col_clean.lower() in alias_map:
                fixed.append(str(alias_map[col_clean.lower()]))
            else:
                fixed.append(col_clean)
        return "GROUP BY " + ", ".join(fixed) + " "

    original = sql
    sql = re.sub(
        r'\bGROUP\s+BY\s+((?:(?!\bORDER\b|\bHAVING\b|\bLIMIT\b).)+)',
        _replace_group_by, sql, flags=re.IGNORECASE | re.DOTALL
    )
    if sql != original:
        logger.info("Replaced GROUP BY aliases with ordinal positions for Athena compatibility")
    return sql


def inject_property_filter(sql: str, property_col: str, property_uuids: list) -> str:
    """
    Ensure the mandatory property UUID filter is present in the SQL WHERE clause.

    The model sometimes drops the CRITICAL property filter entirely when the query
    has a complex WHERE clause. This detects absence and injects it before LIMIT/GROUP BY.

    Only injects if: property_col and property_uuids are provided AND the filter is absent.
    """
    if not sql or not property_col or not property_uuids:
        return sql

    # Check if any of the UUIDs are already in the SQL (filter already present)
    if any(u in sql for u in property_uuids):
        return sql

    uuid_list = ", ".join(f"'{u}'" for u in property_uuids)
    filter_clause = f"{property_col} IN ({uuid_list})"

    where_match = re.search(r'\bWHERE\b', sql, re.IGNORECASE)
    if where_match:
        # Inject as the first condition in WHERE (avoids AND precedence issues)
        insert_pos = where_match.end()
        sql = sql[:insert_pos] + f" {filter_clause} AND" + sql[insert_pos:]
    else:
        # No WHERE clause — insert before GROUP BY / ORDER BY / LIMIT, or at end
        insert_match = re.search(r'\b(GROUP\s+BY|ORDER\s+BY|LIMIT)\b', sql, re.IGNORECASE)
        if insert_match:
            sql = sql[:insert_match.start()] + f"WHERE {filter_clause} " + sql[insert_match.start():]
        else:
            sql = sql.rstrip(";") + f" WHERE {filter_clause}"

    logger.info(f"Injected missing property filter: {filter_clause}")
    return sql


def fix_property_column(sql: str, correct_col: str, property_uuids: list) -> str:
    """
    Fix model hallucinating a wrong property column in WHERE IN clauses.

    The 7B model often generates WHERE property_name IN ('uuid') instead of
    WHERE property IN ('uuid') because 'property_name' exists as a regular column
    in the schema. This detects any property* column in an IN clause that contains
    our known UUIDs and rewrites it to the correct partition column.
    """
    if not sql or not correct_col or not property_uuids:
        return sql

    # Match: optional_alias.property_something IN ('...uuid...')
    pattern = re.compile(
        r'(\b\w+\.)?(property\w*)\s+(IN\s*\([^)]+\))',
        re.IGNORECASE
    )

    def _replace(match):
        alias = match.group(1) or ""
        col = match.group(2)
        in_clause = match.group(3)
        # Only fix if the IN clause contains one of our known UUIDs
        if col.lower() != correct_col.lower() and any(u in in_clause for u in property_uuids):
            logger.info(f"Fixed hallucinated property column: {col} → {correct_col}")
            return f"{alias}{correct_col} {in_clause}"
        return match.group(0)

    return pattern.sub(_replace, sql)


def fix_invalid_extract_from_table(sql: str) -> str:
    """
    Fix model hallucination: EXTRACT(YEAR/WEEK FROM table_name) or EXTRACT(unit FROM CURRENT_TABLE).
    Converts year(snapshotdate) = EXTRACT(YEAR FROM <non-date>) AND week(snapshotdate) = EXTRACT(WEEK FROM <non-date>)
    into the proper date_trunc('week', current_date) filter.
    """
    # Pattern: year(date_parse(snapshotdate,...)) = EXTRACT(YEAR FROM <something>) AND
    #          week(date_parse(snapshotdate,...)) = EXTRACT(WEEK FROM <something>)
    week_pattern = re.compile(
        r"year\s*\(\s*date_parse\s*\(\s*(?:\w+\.)?snapshotdate\s*,[^)]+\)\s*\)\s*=\s*EXTRACT\s*\(\s*YEAR\s+FROM\s+[^)]+\)"
        r"\s+AND\s+"
        r"week\s*\(\s*date_parse\s*\(\s*(?:\w+\.)?snapshotdate\s*,[^)]+\)\s*\)\s*=\s*EXTRACT\s*\(\s*WEEK\s+FROM\s+[^)]+\)",
        re.IGNORECASE,
    )
    if week_pattern.search(sql):
        replacement = "date_parse(snapshotdate, '%Y-%m-%d') >= date_trunc('week', current_date)"
        sql = week_pattern.sub(replacement, sql)
        logger.info("Fixed invalid EXTRACT(unit FROM table) → date_trunc('week', current_date)")
    return sql


def fix_impossible_this_period_filter(sql: str) -> str:
    """
    Fix impossible date range: model sometimes generates
    >= date_trunc('week', current_date) AND < date_trunc('week', current_date)
    which is always false (same lower and upper bound). Remove the spurious upper bound.
    """
    for period in ('week', 'month'):
        # Only fix when we also have the >= side with the same period (no date_add shift)
        has_lower = re.search(
            rf">=\s*date_trunc\s*\(\s*'{period}'\s*,\s*current_date\s*\)",
            sql, re.IGNORECASE
        )
        if not has_lower:
            continue
        # Remove the AND ... < date_trunc('period', current_date) that makes it impossible
        sql = re.sub(
            rf"\s+AND\s+date_parse\s*\([^)]+\)\s*<\s*date_trunc\s*\(\s*'{period}'\s*,\s*current_date\s*\)",
            "",
            sql,
            flags=re.IGNORECASE,
        )
    return sql


def fix_last_week_filter(sql: str, question_text: str) -> str:
    """
    When question mentions 'last week', ensure SQL uses calendar-boundary filter
    (Mon–Sun) rather than a rolling 7-day window (date_add('day', -7)).
    """
    if not question_text or "last week" not in question_text.lower():
        return sql
    if not re.search(r"date_add\s*\(\s*'day'\s*,\s*-7", sql, re.IGNORECASE):
        return sql

    # Replace rolling 7-day window with proper last-week calendar boundary
    pattern = re.compile(
        r"date_parse\s*\(\s*(?:\w+\.)?snapshotdate\s*,\s*'%Y-%m-%d'\s*\)\s*"
        r">=\s*date_add\s*\(\s*'day'\s*,\s*-7\s*,\s*current_date\s*\)"
        r"(?:\s+AND\s+date_parse\s*\(\s*(?:\w+\.)?snapshotdate\s*,\s*'%Y-%m-%d'\s*\)\s*"
        r"<\s*date_trunc\s*\(\s*'day'\s*,\s*current_date\s*\))?",
        re.IGNORECASE,
    )
    replacement = (
        "date_parse(snapshotdate, '%Y-%m-%d') >= date_add('week', -1, date_trunc('week', current_date))"
        " AND date_parse(snapshotdate, '%Y-%m-%d') < date_trunc('week', current_date)"
    )
    fixed = pattern.sub(replacement, sql)
    if fixed != sql:
        logger.info("Fixed 'last week' rolling window → calendar boundary")
    return fixed


def fix_float_cast(sql: str) -> str:
    """
    Athena (PrestoSQL) does not recognise FLOAT as a type — use DOUBLE instead.
    Replaces CAST(... AS FLOAT) and CAST(... AS FLOAT64) with CAST(... AS DOUBLE).
    """
    fixed = re.sub(r'\bAS\s+FLOAT(?:64)?\b', 'AS DOUBLE', sql, flags=re.IGNORECASE)
    if fixed != sql:
        logger.debug("Fixed CAST AS FLOAT → CAST AS DOUBLE")
    return fixed


def fix_table_names(sql: str, allowed_tables: list = None) -> str:
    """
    Fix hallucinated table names by replacing variants with the correct table name.
    
    The model sometimes invents table names like:
    - incident_combine_2025 → incident_combine
    - incident_combine_v2 → incident_combine
    - incident_combine_history → incident_combine
    
    This uses the allowed_tables list to find the closest base table match.
    """
    if not sql or not allowed_tables:
        return sql
    
    # For each allowed table, find and replace hallucinated variants
    # Pattern: allowed_table_name followed by extra suffixes (_YYYY, _vN, _something)
    for table in allowed_tables:
        pattern = re.compile(
            r'\b' + re.escape(table) + r'_[a-zA-Z0-9_]+\b',
            re.IGNORECASE
        )
        matches = pattern.findall(sql)
        for match in matches:
            if match.lower() not in [t.lower() for t in allowed_tables]:
                logger.info(f"Fixed hallucinated table name: {match} → {table}")
                sql = sql.replace(match, table)

    # Fallback: replace any unknown table name in FROM/JOIN with the primary allowed table.
    # Exclude CTE aliases (defined as "name AS (") so we don't clobber valid CTEs.
    if allowed_tables:
        primary_table = allowed_tables[0]
        allowed_lower = {t.lower() for t in allowed_tables}
        cte_aliases = {m.lower() for m in re.findall(r'\b(\w+)\s+AS\s*\(', sql, re.IGNORECASE)}

        def _replace_unknown_from(match):
            keyword = match.group(1)   # FROM or JOIN
            table_name = match.group(2)
            if table_name.lower() in allowed_lower or table_name.lower() in cte_aliases:
                return match.group(0)
            logger.warning(f"Replacing unknown table '{table_name}' with '{primary_table}'")
            return f"{keyword} {primary_table}"

        sql = re.sub(
            r'\b(FROM|JOIN)\s+(\w+)\b',
            _replace_unknown_from,
            sql,
            flags=re.IGNORECASE,
        )

    return sql


def extract_sql(text: str) -> str:
    """Extract and clean SQL from model output. Handles both plain SELECT and CTE (WITH...SELECT) queries."""
    if not text:
        return ""

    # SQLCoder outputs SQL after the [SQL] marker; grab everything after it
    if "[SQL]" in text:
        text = text.split("[SQL]")[-1]

    text = text.replace("```sql", "").replace("```", "")

    # Check for CTE (WITH ... SELECT ...) — must be extracted before SELECT_REGEX to avoid
    # capturing only an inner SELECT inside a CTE definition.
    cte_match = re.search(r'\b(with\s+\w.+)', text, re.IGNORECASE | re.DOTALL)
    select_match = SELECT_REGEX.search(text)

    if cte_match and (not select_match or cte_match.start() <= select_match.start()):
        # CTE found before (or instead of) a bare SELECT — use the full WITH clause
        sql = cte_match.group(1).split(';')[0].strip()
    elif select_match:
        sql = select_match.group(1).strip()
    else:
        return ""

    sql = re.sub(r"\s+", " ", sql)
    
    # Fix date_part()/EXTRACT() on snapshotdate (VARCHAR column)
    sql = fix_date_part(sql)
    # Fix date comparisons for snapshotdate (VARCHAR column)
    sql = fix_date_comparisons(sql)
    # Fix invalid BIGINT timestamp vs DATE comparisons (Athena TYPE_MISMATCH)
    sql = fix_bigint_date_comparisons(sql)
    # Convert PostgreSQL INTERVAL syntax to Athena date_add()
    sql = fix_interval_syntax(sql)
    # Fix GROUP BY aliases → ordinal positions (Athena doesn't support aliases in GROUP BY)
    sql = fix_group_by_aliases(sql)

    # Only add LIMIT if missing, and cap at 100 for safety
    if " limit " not in sql.lower():
        sql = sql.rstrip(";") + " LIMIT 100"
    else:
        # Extract and cap the limit value at 100
        limit_match = re.search(r'limit\s+(\d+)', sql, re.IGNORECASE)
        if limit_match:
            limit_val = int(limit_match.group(1))
            if limit_val > 100:
                sql = re.sub(r'limit\s+\d+', 'LIMIT 100', sql, flags=re.IGNORECASE)

    return sql


def run_sqlcoder(prompt: str, max_tokens: int) -> dict:
    """
    Run SQL generation with thread safety and caching.
    
    Args:
        prompt: The prompt to generate SQL from
        max_tokens: Maximum tokens to generate
        
    Returns:
        Dict with query, confidence, latency_ms, and explanation
    """
    # Check cache first
    cache_key = _get_cache_key(prompt, max_tokens)
    if cache_key in _sql_cache:
        cached = _sql_cache[cache_key].copy()
        cached["from_cache"] = True
        cached["latency_ms"] = 0
        logger.debug(f"SQL cache hit for key {cache_key[:8]}...")
        return cached
    
    # Ensure model is loaded
    load_model()
    
    start = time.time()

    # Use lock for thread-safe model access
    with _model_lock:
        inputs = _tokenizer(prompt, return_tensors="pt").to(_model.device)
        input_length = inputs["input_ids"].shape[1]

        with torch.inference_mode():
            outputs = _model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                do_sample=False,
                num_beams=4,
                eos_token_id=_tokenizer.eos_token_id,
                pad_token_id=_tokenizer.pad_token_id if _tokenizer.pad_token_id else _tokenizer.eos_token_id,
            )

        # Decode only the newly generated tokens (exclude the prompt)
        raw_output = _tokenizer.decode(outputs[0][input_length:], skip_special_tokens=True)

    # Log for debugging (reduce verbosity in production)
    logger.debug(f"Raw model output: {raw_output[:200]}...")

    sql = extract_sql(raw_output)
    latency_ms = int((time.time() - start) * 1000)

    result = {
        "query": sql,
        "confidence": 0.90,
        "latency_ms": latency_ms,
        "explanation": {
            "summary": "SQL generated for Athena execution.",
            "assumptions": []
        },
        "from_cache": False
    }
    
    # Cache the result (with size limit)
    if sql:  # Only cache successful generations
        if len(_sql_cache) >= _CACHE_MAX_SIZE:
            # Remove oldest entry
            oldest_key = next(iter(_sql_cache))
            del _sql_cache[oldest_key]
        _sql_cache[cache_key] = result.copy()
    
    return result


def clear_sql_cache():
    """Clear the SQL generation cache."""
    global _sql_cache
    _sql_cache = {}
    logger.info("SQL cache cleared")


def get_cache_stats() -> dict:
    """Get SQL cache statistics."""
    return {
        "size": len(_sql_cache),
        "max_size": _CACHE_MAX_SIZE
    }
