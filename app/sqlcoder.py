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

        logger.info("[BOOT] Loading Qwen-2.5-3b-Text_to_SQL model (specialized for SQL generation)...")

        model_name = "Ellbendls/Qwen-2.5-3b-Text_to_SQL"

        _tokenizer = AutoTokenizer.from_pretrained(model_name)

        _model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto",
            low_cpu_mem_usage=True  # Memory optimization
        )

        _model.eval()
        logger.info(f"[BOOT] {model_name} loaded successfully!")
        logger.info(f"[INFO] Model size: ~3B parameters, optimized for text-to-SQL tasks")


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
    """
    if not sql:
        return sql
    
    # Check if snapshotdate is already wrapped with date_parse
    already_wrapped = re.compile(
        r'date_parse\s*\(\s*snapshotdate',
        re.IGNORECASE
    )
    
    # If already properly wrapped, return as-is
    if already_wrapped.search(sql):
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

    text = text.replace("```sql", "").replace("```", "")

    match = SELECT_REGEX.search(text)
    if not match:
        return ""

    sql = match.group(1).strip()
    sql = re.sub(r"\s+", " ", sql)
    
    # Fix date comparisons for snapshotdate (VARCHAR column)
    sql = fix_date_comparisons(sql)

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
        # Format prompt as chat message for Qwen
        messages = [{"role": "user", "content": prompt}]
        formatted_prompt = _tokenizer.apply_chat_template(
            messages, 
            tokenize=False, 
            add_generation_prompt=True
        )
        
        inputs = _tokenizer(formatted_prompt, return_tensors="pt").to(_model.device)

        # Generate with torch.inference_mode for efficiency
        with torch.inference_mode():
            outputs = _model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                do_sample=False,
                temperature=0.0,
                top_p=1.0,
                eos_token_id=_tokenizer.eos_token_id,
                pad_token_id=_tokenizer.pad_token_id if _tokenizer.pad_token_id else _tokenizer.eos_token_id
            )

        raw_output = _tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Remove the input prompt from output
    if formatted_prompt in raw_output:
        raw_output = raw_output.replace(formatted_prompt, "").strip()

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
