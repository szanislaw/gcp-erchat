"""
SQL code generation module with thread-safe model access, LRU caching,
and Redshift-dialect SQL fixers.
"""

import time
import re
import os
import torch
import threading
import hashlib
from transformers import AutoTokenizer, AutoModelForCausalLM
from typing import Dict
import logging

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

logger = logging.getLogger(__name__)

_model_lock = threading.Lock()
_model = None
_tokenizer = None

SELECT_REGEX = re.compile(r"(select\s+.*?)(;|\Z)", re.IGNORECASE | re.DOTALL)

_sql_cache: Dict[str, dict] = {}
_CACHE_MAX_SIZE = 500

# Tables in the current schema — used by fix_invalid_extract_from_table
_KNOWN_TABLES = frozenset({
    'maintenance_order', 'master_maintenance_status',
    'master_job_priority', 'property_location',
})


def _get_cache_key(prompt: str, max_tokens: int) -> str:
    return hashlib.md5(f"{prompt}::{max_tokens}".encode()).hexdigest()


def load_model():
    """Load the SQL generation model. Thread-safe.

    Set USE_QUANTIZATION=true for 4-bit quantization (~4-5GB VRAM).
    Default float16 (~13GB VRAM) recommended for L4 24GB.
    GPU_MEMORY_CAP limits allocation (default 11GiB to leave headroom for desktop).
    """
    global _model, _tokenizer

    with _model_lock:
        if _model is not None:
            return

        model_name = "defog/sqlcoder-7b-2"
        use_quantization = os.getenv("USE_QUANTIZATION", "false").lower() == "true"

        gpu_memory_cap = os.getenv("GPU_MEMORY_CAP", "11GiB")
        max_memory = {0: gpu_memory_cap, "cpu": "32GiB"}

        if use_quantization:
            from transformers import BitsAndBytesConfig
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
            )
            logger.info(f"[BOOT] Loading {model_name} (4-bit quantized, gpu_cap={gpu_memory_cap})...")
            kwargs = {"quantization_config": quantization_config, "device_map": "auto", "max_memory": max_memory}
        else:
            logger.info(f"[BOOT] Loading {model_name} (float16, gpu_cap={gpu_memory_cap})...")
            kwargs = {"torch_dtype": torch.float16, "device_map": "auto", "max_memory": max_memory}

        _tokenizer = AutoTokenizer.from_pretrained(model_name)
        _model = AutoModelForCausalLM.from_pretrained(model_name, **kwargs)

        device = next(_model.parameters()).device
        logger.info(f"[BOOT] {model_name} loaded on {device} (quantized={use_quantization})")


# ─── Redshift safety-net fixers ────────────────────────────────────────────

_TIMESTAMP_COLS = frozenset({
    'created_date', 'completed_date', 'cancelled_date',
    'assigned_date', 'modified_date',
})


def fix_date_parse_to_to_date(sql: str) -> str:
    """
    Safety net: convert Athena date_parse() to Redshift syntax.
    - Known TIMESTAMP columns: strip the cast entirely (column is already a timestamp)
    - Other columns: convert to TO_DATE(col, 'YYYY-MM-DD')
    """
    if not sql or "date_parse" not in sql.lower():
        return sql

    def _replace(match: re.Match) -> str:
        col = match.group(1)  # may be "col" or "alias.col"
        col_bare = col.split('.')[-1].lower()
        if col_bare in _TIMESTAMP_COLS:
            return col  # TIMESTAMP — no cast needed
        return f"TO_DATE({col}, 'YYYY-MM-DD')"

    fixed = re.sub(
        r"date_parse\s*\(\s*(\w+(?:\.\w+)?)(?:::text)?\s*,\s*'%Y-%m-%d'\s*\)",
        _replace, sql, flags=re.IGNORECASE
    )
    if fixed != sql:
        logger.info("Fixed date_parse() → stripped cast or TO_DATE()")
    return fixed


def fix_interval_to_dateadd(sql: str) -> str:
    """Fix ANSI INTERVAL syntax → Redshift DATEADD. E.g. CURRENT_DATE - INTERVAL '7 days' → DATEADD(day, -7, CURRENT_DATE)."""
    if not sql or "interval" not in sql.lower():
        return sql

    _UNIT_MAP = {
        "day": "day", "days": "day",
        "week": "week", "weeks": "week",
        "month": "month", "months": "month",
        "year": "year", "years": "year",
    }

    def _replace(match: re.Match) -> str:
        date_expr = match.group(1).strip()
        n_str = match.group(2)
        unit_raw = match.group(3).lower()
        unit = _UNIT_MAP.get(unit_raw, unit_raw)
        n = int(n_str)
        return f"DATEADD({unit}, -{n}, {date_expr})"

    fixed = re.sub(
        r'(\w+(?:\s*\(\s*\))?)\s*-\s*INTERVAL\s+\'(\d+)\s+(\w+)\'',
        _replace, sql, flags=re.IGNORECASE
    )
    if fixed != sql:
        logger.info("Fixed INTERVAL subtraction → DATEADD()")
    return fixed


def fix_date_add_to_dateadd(sql: str) -> str:
    """Safety net: convert Athena date_add('unit', N, date) → Redshift DATEADD(unit, N, date)."""
    if not sql or "date_add" not in sql.lower():
        return sql

    _UNIT_MAP = {
        "day": "day", "days": "day",
        "week": "week", "weeks": "week",
        "month": "month", "months": "month",
        "year": "year", "years": "year",
    }

    def _replace(match: re.Match) -> str:
        unit_raw = match.group(1).strip("'\"").lower()
        unit = _UNIT_MAP.get(unit_raw, unit_raw)
        n = match.group(2)
        date_expr = match.group(3).strip()
        return f"DATEADD({unit}, {n}, {date_expr})"

    fixed = re.sub(
        r"date_add\s*\(\s*['\"](\w+)['\"],\s*(-?\d+)\s*,\s*([^)]+)\)",
        _replace, sql, flags=re.IGNORECASE
    )
    if fixed != sql:
        logger.info("Converted date_add() → DATEADD()")
    return fixed


def fix_main_table_fk_names(sql: str) -> str:
    """
    Fix model placing lookup-table column names directly on maintenance_order alias.

    Patterns corrected (only when the lookup JOIN is absent):
      m.status_name = 'X'   → m.status = (SELECT status_id FROM master_maintenance_status WHERE status_name = 'X')
      m.priority_name = 'X' → m.priority = (SELECT priority_id FROM master_job_priority WHERE priority_name = 'X')

    If the model already JOINed master_maintenance_status/master_job_priority and filters
    on alias.status_name = 'X', that's correct SQL — leave it alone.
    """
    if not sql:
        return sql

    has_status_join = bool(re.search(r'\bJOIN\s+master_maintenance_status\b', sql, re.IGNORECASE))
    has_priority_join = bool(re.search(r'\bJOIN\s+master_job_priority\b', sql, re.IGNORECASE))

    def _status_replace(match):
        if has_status_join:
            return match.group(0)  # JOIN already present — filter is correct as-is
        alias, val = match.group(1), match.group(2)
        return (f"{alias}.status = "
                f"(SELECT status_id FROM master_maintenance_status WHERE status_name = '{val}')")

    def _priority_replace(match):
        if has_priority_join:
            return match.group(0)
        alias, val = match.group(1), match.group(2)
        return (f"{alias}.priority = "
                f"(SELECT priority_id FROM master_job_priority WHERE priority_name = '{val}')")

    original = sql
    sql = re.sub(
        r'\b(\w+)\.status_name\s*=\s*\'([^\']+)\'',
        _status_replace, sql, flags=re.IGNORECASE
    )
    sql = re.sub(
        r'\b(\w+)\.priority_name\s*=\s*\'([^\']+)\'',
        _priority_replace, sql, flags=re.IGNORECASE
    )
    if sql != original:
        logger.info("Fixed m.status_name/m.priority_name → FK subquery lookup")
    return sql


def fix_spurious_department_join(sql: str) -> str:
    """
    Remove spurious JOIN department that maintenance_order doesn't need.

    Spurious patterns (maintenance_order has no department_name/department column):
      - JOIN department d ON m.department_name = d.department_name  (hallucinated col)
      - JOIN department d ON m.department_uuid = d.department_uuid  (real FK, but spurious when not asked)
    Legitimate JOIN: kept when question explicitly asks about department breakdown.
    We detect spurious by checking if there's no SELECT of d.department_name in the query.
    """
    if not sql or "department" not in sql.lower():
        return sql

    logger.debug(f"fix_spurious_department_join input: {repr(sql[:300])}")

    original = sql

    # Pattern 1: JOIN on the hallucinated department_name column (always spurious)
    sql = re.sub(
        r'\b(?:LEFT\s+|INNER\s+|RIGHT\s+)?JOIN\s+department\s+(?:AS\s+)?\w+\s+ON\s+\w+\.department_name\s*=\s*\w+\.department_name\b',
        '', sql, flags=re.IGNORECASE
    )

    # Pattern 2: JOIN on department_uuid but no d.department_name in SELECT (spurious)
    if sql == original:
        dept_join_match = re.search(
            r'\b(?:LEFT\s+|INNER\s+|RIGHT\s+)?JOIN\s+department\s+(?:AS\s+)?(\w+)\s+ON\s+\w+\.department_uuid\s*=\s*\1\.department_uuid\b',
            sql, flags=re.IGNORECASE
        )
        if dept_join_match:
            alias = dept_join_match.group(1)
            # Only remove if the alias is never SELECTed (truly spurious)
            if not re.search(rf'\b{re.escape(alias)}\.department_name\b', sql, re.IGNORECASE):
                sql = sql[:dept_join_match.start()] + sql[dept_join_match.end():]
                logger.info(f"Removed spurious JOIN department (alias '{alias}' never selected)")

    if sql == original:
        return sql  # nothing matched — legitimate department JOIN, leave it

    # Clean up dangling WHERE / AND conditions referencing the removed alias
    # Pattern: WHERE alias.department_name = 'val' AND ...
    sql = re.sub(
        r'\bWHERE\s+\w+\.department_name\s*=\s*\'[^\']+\'\s+AND\s+',
        'WHERE ', sql, flags=re.IGNORECASE
    )
    # Pattern: AND alias.department_name = 'val'
    sql = re.sub(
        r'\s+AND\s+\w+\.department_name\s*=\s*\'[^\']+\'',
        '', sql, flags=re.IGNORECASE
    )
    # Pattern: WHERE alias.department_name = 'val' (nothing after)
    sql = re.sub(
        r'\bWHERE\s+\w+\.department_name\s*=\s*\'[^\']+\'\s*$',
        '', sql, flags=re.IGNORECASE
    )
    sql = re.sub(r'\s{2,}', ' ', sql).strip()
    logger.info("Removed spurious JOIN department ON m.department_name (column doesn't exist)")
    return sql


def fix_snapshotdate(sql: str) -> str:
    """Replace hallucinated 'snapshotdate' column with 'created_date'. snapshotdate does not exist in this schema."""
    if not sql or "snapshotdate" not in sql.lower():
        return sql
    fixed = re.sub(r'\bsnapshotdate\b', 'created_date', sql, flags=re.IGNORECASE)
    if fixed != sql:
        logger.info("Fixed hallucinated snapshotdate → created_date")
    # Also strip any TO_DATE() wrapping since created_date is already a TIMESTAMP
    fixed = re.sub(
        r"\bTO_DATE\s*\(\s*([\w.]+)\s*,\s*'[^']+'\s*\)",
        r'\1', fixed, flags=re.IGNORECASE
    )
    return fixed


def fix_department_column(sql: str) -> str:
    """
    Fix model hallucination: alias.department used as a column (column doesn't exist).
    The department table column is 'department_name', not 'department'.
    Replaces [alias].department → [alias].department_name unless already suffixed.
    """
    if "department" not in sql.lower():
        return sql
    fixed = re.sub(
        r'\b(\w+)\.department\b(?!_)',
        r'\1.department_name',
        sql, flags=re.IGNORECASE
    )
    if fixed != sql:
        logger.info("Fixed hallucinated .department → .department_name")
    return fixed


def fix_dateadd_quoted_unit(sql: str) -> str:
    """Fix DATEADD('day', n, date) → DATEADD(day, n, date) — Redshift requires unquoted unit."""
    if not sql or 'dateadd' not in sql.lower():
        return sql
    fixed = re.sub(r"\bDATEADD\s*\(\s*'(\w+)'\s*,", r"DATEADD(\1,", sql, flags=re.IGNORECASE)
    if fixed != sql:
        logger.info("Fixed DATEADD quoted unit → unquoted")
    return fixed


def fix_date_part_this_period(sql: str) -> str:
    """Convert date_part month/week equality pairs → DATE_TRUNC boundary filter.
    Handles both orderings: period-first and year-first.
    """
    if not sql or 'date_part' not in sql.lower():
        return sql

    for period in ('month', 'week'):
        # Period-first: date_part('period', col) = ... AND date_part('year', col) = ...
        p1 = re.compile(
            rf"date_part\s*\(\s*'{period}'\s*,\s*([\w.]+)\s*\)\s*=\s*"
            rf"date_part\s*\(\s*'{period}'\s*,\s*CURRENT_DATE\s*\)\s+"
            rf"AND\s+date_part\s*\(\s*'year'\s*,\s*[\w.]+\s*\)\s*=\s*"
            rf"date_part\s*\(\s*'year'\s*,\s*CURRENT_DATE\s*\)",
            re.IGNORECASE,
        )
        m = p1.search(sql)
        if m:
            col = m.group(1)
            sql = p1.sub(f"{col} >= DATE_TRUNC('{period}', CURRENT_DATE)", sql)
            logger.info(f"Fixed date_part '{period}' pair (period-first) → DATE_TRUNC")
            continue

        # Year-first: date_part('year', col) = ... AND date_part('period', col) = ...
        p2 = re.compile(
            rf"date_part\s*\(\s*'year'\s*,\s*([\w.]+)\s*\)\s*=\s*"
            rf"date_part\s*\(\s*'year'\s*,\s*CURRENT_DATE\s*\)\s+"
            rf"AND\s+date_part\s*\(\s*'{period}'\s*,\s*[\w.]+\s*\)\s*=\s*"
            rf"date_part\s*\(\s*'{period}'\s*,\s*CURRENT_DATE\s*\)",
            re.IGNORECASE,
        )
        m = p2.search(sql)
        if m:
            col = m.group(1)  # col from the year part (same table column)
            sql = p2.sub(f"{col} >= DATE_TRUNC('{period}', CURRENT_DATE)", sql)
            logger.info(f"Fixed date_part '{period}' pair (year-first) → DATE_TRUNC")

        # "Last period" arithmetic: date_part('month', col) = date_part('month', CURRENT_DATE) - 1
        # Broken at year boundaries (Jan: 0 ≠ 12). Convert to DATEADD range.
        p_last = re.compile(
            rf"date_part\s*\(\s*'{period}'\s*,\s*([\w.]+)\s*\)\s*=\s*"
            rf"date_part\s*\(\s*'{period}'\s*,\s*CURRENT_DATE\s*\)\s*-\s*1"
            rf"(?:\s+AND\s+date_part\s*\(\s*'year'\s*,\s*[\w.]+\s*\)\s*=\s*"
            rf"date_part\s*\(\s*'year'\s*,\s*CURRENT_DATE\s*\))?",
            re.IGNORECASE,
        )
        m = p_last.search(sql)
        if m:
            col = m.group(1)
            sql = p_last.sub(
                f"{col} >= DATEADD({period}, -1, DATE_TRUNC('{period}', CURRENT_DATE))"
                f" AND {col} < DATE_TRUNC('{period}', CURRENT_DATE)",
                sql,
            )
            logger.info(f"Fixed date_part last-{period} arithmetic → DATEADD range")

    return sql


def fix_extract_week_trend(sql: str) -> str:
    """Replace EXTRACT(YEAR/WEEK FROM col) trend pattern → DATE_TRUNC('week', col)."""
    if not sql or 'extract' not in sql.lower() or 'week' not in sql.lower():
        return sql

    col_match = re.search(r'EXTRACT\s*\(\s*WEEK\s+FROM\s+([\w.]+)\s*\)', sql, re.IGNORECASE)
    if not col_match:
        return sql
    col = col_match.group(1)

    # Replace SELECT EXTRACT(YEAR FROM col) AS y, EXTRACT(WEEK FROM col) AS w
    fixed = re.sub(
        r"EXTRACT\s*\(\s*YEAR\s+FROM\s+[\w.]+\s*\)\s*AS\s+\w+\s*,\s*"
        r"EXTRACT\s*\(\s*WEEK\s+FROM\s+[\w.]+\s*\)\s*AS\s+\w+",
        f"DATE_TRUNC('week', {col}) AS week_start",
        sql, flags=re.IGNORECASE,
    )
    _WEEK_ALIASES = frozenset({'YEAR', 'WEEK', 'YEAR_NUM', 'WEEK_NUM'})

    # Fix GROUP BY clause referencing old YEAR/WEEK aliases
    fixed = re.sub(
        r'(GROUP\s+BY\s+)(\w+)\s*,\s*(\w+)',
        lambda m: (
            f"{m.group(1)}DATE_TRUNC('week', {col})"
            if m.group(2).upper() in _WEEK_ALIASES or m.group(3).upper() in _WEEK_ALIASES
            else m.group(0)
        ),
        fixed, flags=re.IGNORECASE,
    )

    # Fix ORDER BY clause referencing old YEAR/WEEK aliases
    fixed = re.sub(
        r'ORDER\s+BY\s+(?:\w+\s*,\s*)*(?:YEAR|WEEK|YEAR_NUM|WEEK_NUM)\b[^)]*?(?=\s*LIMIT|\s*$)',
        f"ORDER BY DATE_TRUNC('week', {col})",
        fixed, flags=re.IGNORECASE,
    )

    if fixed != sql:
        logger.info("Fixed EXTRACT(YEAR/WEEK) trend → DATE_TRUNC('week', col)")
    return fixed


def fix_scalar_subquery_eq(sql: str) -> str:
    """Convert = (SELECT ...) → IN (SELECT ...) to handle multi-row and zero-row subqueries safely."""
    if not sql or '(select' not in sql.lower():
        return sql
    fixed = re.sub(r'\s*=\s*\(\s*(SELECT\s+)', r' IN (\1', sql, flags=re.IGNORECASE)
    if fixed != sql:
        logger.info("Fixed scalar subquery: = (SELECT ...) → IN (SELECT ...)")
    return fixed


def fix_status_case(sql: str) -> str:
    """Normalize status_name/priority_name values to actual DB lowercase.
    'open' → IN ('pending','delayed','acknowledged') since no 'open' status exists.
    """
    if not sql:
        return sql

    # 'open' status doesn't exist — map to the active/non-terminal statuses
    fixed = re.sub(
        r"(status_name\s*(?:=|IN\s*\())\s*'(?:Open|open)'",
        r"\1'pending'",
        sql, flags=re.IGNORECASE,
    )
    fixed = re.sub(
        r"(status_name\s*=\s*)'[Oo]pen'",
        r"\1IN ('pending', 'delayed', 'acknowledged')",
        fixed, flags=re.IGNORECASE,
    )

    # Normalize Title Case → lowercase for status values
    for val in ('Completed', 'Cancelled', 'Pending', 'Delayed', 'Acknowledged', 'In Progress'):
        fixed = re.sub(
            rf"(status_name\s*=\s*)'{re.escape(val)}'",
            rf"\g<1>'{val.lower()}'",
            fixed, flags=re.IGNORECASE,
        )

    # Normalize Title Case → lowercase for priority values
    for val in ('High', 'Low', 'Medium', 'Normal', 'Urgent', 'Critical'):
        fixed = re.sub(
            rf"(priority_name\s*=\s*)'{re.escape(val)}'",
            rf"\g<1>'{val.lower()}'",
            fixed, flags=re.IGNORECASE,
        )

    if fixed != sql:
        logger.info("Normalized status/priority values to lowercase")
    return fixed


def fix_unaliased_table_ref(sql: str) -> str:
    """Replace maintenance_order.col with m.col when alias m is in use."""
    if not sql or 'maintenance_order' not in sql.lower():
        return sql
    if not re.search(r'\bmaintenance_order\s+(?:AS\s+)?m\b', sql, re.IGNORECASE):
        return sql
    fixed = re.sub(r'\bmaintenance_order\.(\w+)\b', r'm.\1', sql, flags=re.IGNORECASE)
    if fixed != sql:
        logger.info("Fixed unaliased maintenance_order.col → m.col")
    return fixed


def fix_year_extract_comparison(sql: str) -> str:
    """Fix EXTRACT(YEAR FROM col) = DATE_TRUNC(...) — wrong type comparison → EXTRACT(YEAR FROM CURRENT_DATE)."""
    if not sql or 'extract' not in sql.lower():
        return sql
    fixed = re.sub(
        r'(EXTRACT\s*\(\s*YEAR\s+FROM\s+[\w.]+\s*\))\s*=\s*DATE_TRUNC\s*\([^)]+\)',
        r'\1 = EXTRACT(YEAR FROM CURRENT_DATE)',
        sql, flags=re.IGNORECASE,
    )
    if fixed != sql:
        logger.info("Fixed EXTRACT(YEAR) = DATE_TRUNC() → = EXTRACT(YEAR FROM CURRENT_DATE)")
    return fixed


def inject_property_filter(sql: str, property_col: str, property_uuids: list) -> str:
    """Ensure the mandatory property UUID filter is present. Injects if absent."""
    if not sql or not property_col or not property_uuids:
        return sql

    if any(u in sql for u in property_uuids):
        return sql

    uuid_list = ", ".join(f"'{u}'" for u in property_uuids)
    filter_clause = f"{property_col} IN ({uuid_list})"

    where_match = re.search(r'\bWHERE\b', sql, re.IGNORECASE)
    if where_match:
        insert_pos = where_match.end()
        sql = sql[:insert_pos] + f" {filter_clause} AND" + sql[insert_pos:]
    else:
        insert_match = re.search(r'\b(GROUP\s+BY|ORDER\s+BY|LIMIT)\b', sql, re.IGNORECASE)
        if insert_match:
            sql = sql[:insert_match.start()] + f"WHERE {filter_clause} " + sql[insert_match.start():]
        else:
            sql = sql.rstrip(";") + f" WHERE {filter_clause}"

    logger.info(f"Injected missing property filter: {filter_clause}")
    return sql


def fix_property_column(sql: str, correct_col: str, property_uuids: list) -> str:
    """Fix model hallucinating a wrong property column in WHERE IN clauses containing UUIDs."""
    if not sql or not correct_col or not property_uuids:
        return sql

    pattern = re.compile(r'(\b\w+\.)?(property\w*)\s+(IN\s*\([^)]+\))', re.IGNORECASE)

    def _replace(match):
        alias = match.group(1) or ""
        col = match.group(2)
        in_clause = match.group(3)
        if col.lower() != correct_col.lower() and any(u in in_clause for u in property_uuids):
            logger.info(f"Fixed hallucinated property column: {col} → {correct_col}")
            return f"{alias}{correct_col} {in_clause}"
        return match.group(0)

    return pattern.sub(_replace, sql)


def fix_invalid_extract_from_table(sql: str) -> str:
    """Fix EXTRACT(unit FROM table_name) where model passes a table name instead of a column."""
    def _replace(match):
        unit = match.group(1).lower()
        target = match.group(2).lower()
        if target in _KNOWN_TABLES:
            logger.warning(f"Fixed hallucinated EXTRACT({unit} FROM {target}) → DATE_TRUNC('week', CURRENT_DATE)")
            return "DATE_TRUNC('week', CURRENT_DATE)"
        return match.group(0)

    return re.sub(
        r'\bEXTRACT\s*\(\s*(\w+)\s+FROM\s+(\w+)\s*\)',
        _replace, sql, flags=re.IGNORECASE
    )


def fix_impossible_this_period_filter(sql: str) -> str:
    """Fix impossible date range: created_date >= DATE_TRUNC('p') AND created_date < DATE_TRUNC('p')."""
    for period in ('week', 'month'):
        has_lower = re.search(
            rf"created_date\s*>=\s*DATE_TRUNC\s*\(\s*'{period}'\s*,\s*CURRENT_DATE\s*\)",
            sql, re.IGNORECASE
        )
        if not has_lower:
            continue
        sql = re.sub(
            rf"\s+AND\s+created_date\s*<\s*DATE_TRUNC\s*\(\s*'{period}'\s*,\s*CURRENT_DATE\s*\)",
            "", sql, flags=re.IGNORECASE
        )
    return sql


def fix_last_week_filter(sql: str, question_text: str) -> str:
    """When question says 'last week', normalise to Mon–Sun calendar boundary."""
    if not question_text or "last week" not in question_text.lower():
        return sql

    original = sql

    # Pattern 1: rolling -7 day window → calendar last week
    if re.search(r"DATEADD\s*\(\s*day\s*,\s*-7", sql, re.IGNORECASE):
        pattern = re.compile(
            r"created_date\s*>=\s*DATEADD\s*\(\s*day\s*,\s*-7\s*,\s*CURRENT_DATE\s*\)"
            r"(?:\s+AND\s+created_date\s*<\s*DATE_TRUNC\s*\(\s*'day'\s*,\s*CURRENT_DATE\s*\))?",
            re.IGNORECASE,
        )
        sql = pattern.sub(
            "created_date >= DATEADD(week, -1, DATE_TRUNC('week', CURRENT_DATE))"
            " AND created_date < DATE_TRUNC('week', CURRENT_DATE)",
            sql,
        )

    # Pattern 2: date_part('week'/'year', ...) → calendar last week
    if re.search(r"date_part\s*\(\s*'week'", sql, re.IGNORECASE):
        # Strip the whole date_part expression and replace with DATE_TRUNC bounds
        sql = re.sub(
            r"date_part\s*\(\s*'year'\s*,\s*[\w.]+\s*\)\s*=\s*date_part\s*\(\s*'year'\s*,\s*CURRENT_DATE\s*\)"
            r"\s+AND\s+date_part\s*\(\s*'week'\s*,\s*[\w.]+\s*\)\s*=\s*[^A-Z\s][^\s]*",
            "created_date >= DATEADD(week, -1, DATE_TRUNC('week', CURRENT_DATE))"
            " AND created_date < DATE_TRUNC('week', CURRENT_DATE)",
            sql, flags=re.IGNORECASE,
        )
        if sql == original:
            # Simpler fallback: just replace any date_part week reference
            sql = re.sub(
                r"\bdate_part\s*\(\s*'week'\s*,\s*([\w.]+)\s*\)\s*=\s*\S+",
                r"\1 >= DATEADD(week, -1, DATE_TRUNC('week', CURRENT_DATE))"
                r" AND \1 < DATE_TRUNC('week', CURRENT_DATE)",
                sql, flags=re.IGNORECASE,
            )

    if sql != original:
        logger.info("Fixed 'last week' filter → Mon–Sun calendar boundary")
    return sql


def fix_table_names(sql: str, allowed_tables: list = None) -> str:
    """Fix hallucinated table name variants; fall back unknown FROM/JOIN targets to primary table."""
    if not sql or not allowed_tables:
        return sql

    for table in allowed_tables:
        # Negative lookbehind for '.' prevents matching column refs like m.department_uuid
        pattern = re.compile(r'(?<!\.)' + r'\b' + re.escape(table) + r'_[a-zA-Z0-9_]+\b', re.IGNORECASE)
        for match in pattern.findall(sql):
            if match.lower() not in [t.lower() for t in allowed_tables]:
                logger.info(f"Fixed hallucinated table name: {match} → {table}")
                # Replace only standalone refs (not column refs like alias.department_uuid)
                sql = re.sub(r'(?<!\.)\b' + re.escape(match) + r'\b', table, sql, flags=re.IGNORECASE)

    primary_table = allowed_tables[0]
    allowed_lower = {t.lower() for t in allowed_tables}
    cte_aliases = {m.lower() for m in re.findall(r'\b(\w+)\s+AS\s*\(', sql, re.IGNORECASE)}

    def _replace_unknown_from(match):
        keyword = match.group(1)
        table_name = match.group(2)
        if table_name.lower() in allowed_lower or table_name.lower() in cte_aliases:
            return match.group(0)
        # Skip FROM inside function calls like EXTRACT(YEAR FROM col) or DATEADD(day, N, date)
        if keyword.upper() == 'FROM':
            pre = sql[:match.start()]
            if pre.count('(') > pre.count(')'):
                return match.group(0)
        logger.warning(f"Replacing unknown table '{table_name}' with '{primary_table}'")
        return f"{keyword} {primary_table}"

    sql = re.sub(
        r'\b(FROM|JOIN)\s+(\w+)\b',
        _replace_unknown_from,
        sql, flags=re.IGNORECASE,
    )

    return sql


# ─── SQL extraction + post-processing pipeline ─────────────────────────────

def extract_sql(text: str) -> str:
    """Extract SQL from model output. Handles plain SELECT and CTE (WITH ... SELECT) queries."""
    if not text:
        return ""

    if "[SQL]" in text:
        text = text.split("[SQL]")[-1]

    text = text.replace("```sql", "").replace("```", "")

    cte_match = re.search(r'\b(with\s+\w.+)', text, re.IGNORECASE | re.DOTALL)
    select_match = SELECT_REGEX.search(text)

    if cte_match and (not select_match or cte_match.start() <= select_match.start()):
        sql = cte_match.group(1).split(';')[0].strip()
    elif select_match:
        sql = select_match.group(1).strip()
    else:
        return ""

    sql = re.sub(r"\s+", " ", sql)

    # Redshift safety nets
    sql = fix_date_parse_to_to_date(sql)
    sql = fix_date_add_to_dateadd(sql)
    sql = fix_interval_to_dateadd(sql)
    # Schema-specific hallucination fixes (order matters)
    sql = fix_snapshotdate(sql)               # replace hallucinated snapshotdate → created_date
    sql = fix_unaliased_table_ref(sql)        # maintenance_order.col → m.col
    sql = fix_dateadd_quoted_unit(sql)        # DATEADD('day',...) → DATEADD(day,...)
    sql = fix_date_part_this_period(sql)      # date_part pairs → DATE_TRUNC boundary
    sql = fix_extract_week_trend(sql)         # EXTRACT(YEAR/WEEK) trend → DATE_TRUNC('week')
    # fix_spurious_department_join and fix_main_table_fk_names are maintenance-specific.
    # They run in Stage B (main.py) where the redshift_target is known.
    sql = fix_scalar_subquery_eq(sql)         # = (SELECT ...) → IN (SELECT ...)
    sql = fix_status_case(sql)                # normalize status/priority case + 'open' mapping
    sql = fix_department_column(sql)          # finally alias.department → alias.department_name
    sql = fix_year_extract_comparison(sql)    # EXTRACT(YEAR) = DATE_TRUNC() → EXTRACT(YEAR FROM CURRENT_DATE)

    if " limit " not in sql.lower():
        sql = sql.rstrip(";") + " LIMIT 100"
    else:
        limit_match = re.search(r'limit\s+(\d+)', sql, re.IGNORECASE)
        if limit_match and int(limit_match.group(1)) > 100:
            sql = re.sub(r'limit\s+\d+', 'LIMIT 100', sql, flags=re.IGNORECASE)

    return sql


# ─── Model inference ────────────────────────────────────────────────────────

def run_sqlcoder(prompt: str, max_tokens: int) -> dict:
    """Run SQL generation with thread safety and LRU caching."""
    cache_key = _get_cache_key(prompt, max_tokens)
    if cache_key in _sql_cache:
        cached = _sql_cache[cache_key].copy()
        cached["from_cache"] = True
        cached["latency_ms"] = 0
        logger.debug(f"SQL cache hit for key {cache_key[:8]}...")
        return cached

    load_model()

    start = time.time()

    with _model_lock:
        torch.cuda.empty_cache()
        inputs = _tokenizer(prompt, return_tensors="pt").to(_model.device)
        input_length = inputs["input_ids"].shape[1]

        with torch.inference_mode():
            outputs = _model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                do_sample=False,
                num_beams=1,
                eos_token_id=_tokenizer.eos_token_id,
                pad_token_id=_tokenizer.pad_token_id if _tokenizer.pad_token_id else _tokenizer.eos_token_id,
            )

        raw_output = _tokenizer.decode(outputs[0][input_length:], skip_special_tokens=True)

    logger.debug(f"Raw model output: {raw_output[:200]}...")

    sql = extract_sql(raw_output)
    latency_ms = int((time.time() - start) * 1000)

    result = {
        "query": sql,
        "confidence": 0.90,
        "latency_ms": latency_ms,
        "explanation": {
            "summary": "SQL generated for Redshift execution.",
            "assumptions": []
        },
        "from_cache": False
    }

    if sql:
        if len(_sql_cache) >= _CACHE_MAX_SIZE:
            del _sql_cache[next(iter(_sql_cache))]
        _sql_cache[cache_key] = result.copy()

    return result


def clear_sql_cache():
    """Clear the SQL generation cache."""
    global _sql_cache
    _sql_cache = {}
    logger.info("SQL cache cleared")


def get_cache_stats() -> dict:
    """Get SQL cache statistics."""
    return {"size": len(_sql_cache), "max_size": _CACHE_MAX_SIZE}
