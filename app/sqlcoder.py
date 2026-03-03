"""
Enhanced SQL code generation module with:
- Thread-safe model access
- LRU caching for repeated queries
- Better error handling
- Memory optimization
"""

import time
import re
import torch
import threading
import hashlib
from functools import lru_cache
from transformers import AutoTokenizer, AutoModelForCausalLM
from typing import Dict, Optional, Tuple
import logging

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
    """Load the SQL generation model. Thread-safe."""
    global _model, _tokenizer

    with _model_lock:
        if _model is not None:
            return

        model_name = "defog/sqlcoder-7b-2"
        logger.info(f"[BOOT] Loading {model_name} (state-of-the-art NL-to-SQL, 4-bit quantized)...")

        from transformers import BitsAndBytesConfig
        quantization_config = BitsAndBytesConfig(load_in_4bit=True)

        _tokenizer = AutoTokenizer.from_pretrained(model_name)

        _model = AutoModelForCausalLM.from_pretrained(
            model_name,
            quantization_config=quantization_config,
            device_map="auto",
        )

        logger.info(f"[BOOT] {model_name} loaded successfully!")


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
    
    if fixed_sql != sql:
        logger.debug(f"Fixed date comparison: {sql[:100]}... → {fixed_sql[:100]}...")
    
    return fixed_sql


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
        # Match the table name with any suffix like _2025, _v2, _history, etc.
        pattern = re.compile(
            r'\b' + re.escape(table) + r'_[a-zA-Z0-9_]+\b',
            re.IGNORECASE
        )
        matches = pattern.findall(sql)
        for match in matches:
            # Only replace if the hallucinated name is NOT itself an allowed table
            if match.lower() not in [t.lower() for t in allowed_tables]:
                logger.info(f"Fixed hallucinated table name: {match} → {table}")
                sql = sql.replace(match, table)
    
    return sql


def extract_sql(text: str) -> str:
    """Extract and clean SQL from model output."""
    if not text:
        return ""

    # SQLCoder outputs SQL after the [SQL] marker; grab everything after it
    if "[SQL]" in text:
        text = text.split("[SQL]")[-1]

    text = text.replace("```sql", "").replace("```", "")

    match = SELECT_REGEX.search(text)
    if not match:
        return ""

    sql = match.group(1).strip()
    sql = re.sub(r"\s+", " ", sql)
    
    # Fix date comparisons for snapshotdate (VARCHAR column)
    sql = fix_date_comparisons(sql)
    # Fix invalid BIGINT timestamp vs DATE comparisons (Athena TYPE_MISMATCH)
    sql = fix_bigint_date_comparisons(sql)

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
