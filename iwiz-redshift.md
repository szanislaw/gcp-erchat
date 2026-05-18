# iWiz Redshift — NLQ-to-SQL Pipeline Technical Reference

**Service**: `gcp-erchat` FastAPI application  
**Model**: `defog/sqlcoder-7b-2` (float16, ~13 GB VRAM)  
**Database**: Amazon Redshift Serverless (password auth)  
**Schema**: `nxg_107747471_q2sj` (maintenance order domain)  
**Production**: `http://34.126.131.59:8000`

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Request Pipeline](#2-request-pipeline)
3. [Data Model & Schema Constraints](#3-data-model--schema-constraints)
4. [Input Processing](#4-input-processing)
5. [Prompt Construction](#5-prompt-construction)
6. [Model Inference](#6-model-inference)
7. [SQL Post-Processing Fixers](#7-sql-post-processing-fixers)
8. [SQL Security Validation](#8-sql-security-validation)
9. [Redshift Execution](#9-redshift-execution)
10. [Output Formatting](#10-output-formatting)
11. [Display Type Detection](#11-display-type-detection)
12. [Rate Limiting](#12-rate-limiting)
13. [Caching Architecture](#13-caching-architecture)
14. [API Reference](#14-api-reference)
15. [Configuration Reference](#15-configuration-reference)
16. [Known Limitations & Failure Modes](#16-known-limitations--failure-modes)

---

## 1. System Overview

The service converts natural language questions (NLQ) into Amazon Redshift SQL queries, executes them, and returns structured results with display type hints for frontend rendering.

```
HTTP POST /nlq/execute
         │
         ▼
   Input Validation  ──────────────────► 400 (XSS / injection / length)
         │
         ▼
   Rate Limiting  ───────────────────── ► 429 (token bucket exhausted)
         │
         ▼
   Query Normalizer  (entity alias resolution)
         │
         ▼
   Prompt Builder  (schema DDL + ENUM values + property restriction)
         │
         ▼
   Model Inference  (defog/sqlcoder-7b-2, ThreadPoolExecutor)
         │ LRU cache keyed by md5(prompt::max_tokens)
         ▼
   SQL Post-Processing  (17 regex fixers, two-stage pipeline)
         │
         ▼
   SQL Validation  (forbidden ops, table allowlist, CTE awareness)
         │
         ▼
   Redshift Execution  ──────────────── ► RuntimeError → Self-correction loop (×2)
         │
         ▼
   Column Formatter  (raw DB names → display names)
         │
         ▼
   Display Type Detection  (metric / bar / pie / line / table)
         │
         ▼
   Chart Formatter  (reshape for frontend rendering)
         │
         ▼
   JSON Response  + request log
```

### Key design constraints

- Model runs on a single GPU. All inference is serialised through `_model_lock` (threading.Lock).
- The async FastAPI event loop never blocks: model inference and Redshift execution both run in a `ThreadPoolExecutor` via `loop.run_in_executor`.
- Model is loaded once at startup (`lifespan` context) and never reloaded at runtime.
- All queries are hard-capped at `LIMIT 100`.

---

## 2. Request Pipeline

Entry point: `POST /nlq/execute` in `app/main.py`.

### Step 1 — Input Validation (`app/input_validator.py`)

Validates and sanitises the raw `text` field before it touches any downstream system.

| Check | Behaviour |
|-------|-----------|
| `None` / empty | 400 — `"Query text cannot be null"` |
| Length < 2 chars | 400 |
| Length > 2000 chars | 400 |
| XSS patterns (9 regexes) | 400 in strict mode |
| SQL injection patterns (12 regexes) | 400 in strict mode |
| Control characters (`\x00-\x1f`) | Stripped silently |
| HTML entities | `html.escape()` applied |

After validation, `sanitized_text` is used for all downstream processing. `req.text` (original) is used only for display-type pattern matching.

### Step 2 — Rate Limiting (`app/rate_limiter.py`)

Token bucket algorithm. Configuration (global singleton, set at startup):

| Parameter | Value |
|-----------|-------|
| `requests_per_second` | 2.0 |
| `burst_size` | 10 |
| `queue_size` | 50 |
| `queue_timeout` | 60 s |

Returns `HTTP 429` with `Retry-After` header on exhaustion.

### Step 3 — Target & Table Resolution

`redshift_target` from `req.execution.redshift_target` (defaults to `"default"`).

Allowed tables resolved in priority order:
1. `req.sql.tables` — caller-specified override
2. `REDSHIFT_TARGETS[target]["tables"]` — config-level default

Current default allowed tables:
```
maintenance_order, master_maintenance_status, master_job_priority, property_location
```

### Step 4 — Prompt Construction

See [Section 5](#5-prompt-construction).

### Step 5 — Model Inference

See [Section 6](#6-model-inference). Runs non-blocking via `ThreadPoolExecutor`.

### Step 5.5 — SQL Post-Processing

See [Section 7](#7-sql-post-processing-fixers). Applied after inference, before validation.

### Step 6 — SQL Validation

See [Section 8](#8-sql-security-validation).

### Step 7 — Redshift Execution + Self-Correction Loop

Runs only when `dry_run = false`. Up to **2 correction attempts** on `RuntimeError`:

```
attempt 0 → execute SQL
  └─ RuntimeError → build correction prompt → re-infer → re-fix → re-validate
attempt 1 → execute corrected SQL
  └─ RuntimeError → build correction prompt → re-infer → re-fix → re-validate  
attempt 2 → execute corrected SQL
  └─ RuntimeError → propagate as HTTP 400
```

The correction prompt includes the failed SQL and the Redshift error message (first 300 chars).

### Step 8–11 — Output

Column formatting → display type detection → chart data reshaping → JSON response + request log.

---

## 3. Data Model & Schema Constraints

### Tables

#### `maintenance_order` (primary table, ~97 columns)

Key columns used in SQL generation:

| Column | Type | Notes |
|--------|------|-------|
| `maintenance_no` | VARCHAR | Human-readable order ID |
| `status` | SMALLINT | FK → `master_maintenance_status.status_id` |
| `priority` | SMALLINT | FK → `master_job_priority.priority_id` |
| `location_uuid` | VARCHAR | FK → `property_location.location_uuid` |
| `property_uuid` | VARCHAR | Access control partition |
| `created_date` | TIMESTAMP | Main date filter column |
| `completed_date` | TIMESTAMP | |
| `cancelled_date` | TIMESTAMP | |
| `assigned_date` | TIMESTAMP | |
| `modified_date` | TIMESTAMP | |

**CRITICAL**: `maintenance_order` has **no `department_uuid` column**. There is no FK path to any department table. Department-breakdown queries cannot be answered with this schema.

#### `master_maintenance_status`

| Column | Type |
|--------|------|
| `status_id` | SMALLINT (PK) |
| `status_name` | VARCHAR |

Actual DB values (all lowercase): `'completed'`, `'delayed'`, `'pending'`, `'cancelled'`, `'acknowledged'`

There is **no status called `'open'`**. "Open orders" maps to: `status_name IN ('pending', 'delayed', 'acknowledged')`.

#### `master_job_priority`

| Column | Type |
|--------|------|
| `priority_id` | SMALLINT (PK) |
| `priority_name` | VARCHAR |

#### `property_location`

| Column | Type |
|--------|------|
| `location_uuid` | VARCHAR (PK) |
| `location_name` | VARCHAR |

### Foreign Key Pattern

The model is instructed to always JOIN through lookup tables — never filter on raw integer FK values:

```sql
-- CORRECT
SELECT COUNT(*) FROM maintenance_order m
JOIN master_maintenance_status s ON m.status = s.status_id
WHERE s.status_name = 'completed'

-- WRONG (raw FK integer)
SELECT COUNT(*) FROM maintenance_order m
WHERE m.status = 2
```

### Date Columns

All date columns (`created_date`, `completed_date`, `cancelled_date`, `assigned_date`, `modified_date`) are **TIMESTAMP** — no casting required. Use directly in WHERE clauses.

### Date Semantics

| Question | Correct SQL pattern |
|----------|-------------------|
| "this week" | `created_date >= DATE_TRUNC('week', CURRENT_DATE)` |
| "this month" | `created_date >= DATE_TRUNC('month', CURRENT_DATE)` |
| "last week" | `created_date >= DATEADD(week, -1, DATE_TRUNC('week', CURRENT_DATE)) AND created_date < DATE_TRUNC('week', CURRENT_DATE)` |
| "last month" | `created_date >= DATEADD(month, -1, DATE_TRUNC('month', CURRENT_DATE)) AND created_date < DATE_TRUNC('month', CURRENT_DATE)` |
| "last 30 days" | `created_date >= DATEADD(day, -30, CURRENT_DATE)` |
| "this year" | `EXTRACT(YEAR FROM created_date) = EXTRACT(YEAR FROM CURRENT_DATE)` |

**Calendar vs rolling**: "this week / last week" use `DATE_TRUNC` boundaries (Mon–Sun calendar). "Last 7 days / last 30 days" use rolling `DATEADD`. These are NOT interchangeable.

---

## 4. Input Processing

### Query Normalizer (`app/query_normalizer.py`)

Runs before prompt construction. Resolves natural language aliases to canonical DB values and injects them as SQL hints in the prompt.

**Entity alias tables:**

| Entity | Example aliases → canonical |
|--------|---------------------------|
| Property | `"bkk"` → `"The Peninsula Bangkok"` |
| Status | `"open"` → `"pending"`, `"done"` → `"completed"` |
| Department | `"f&b"` → `"Food & Beverage"`, `"eng"` → `"Engineering"` |
| Category | `"noise"` → `"Disturbance"`, `"billing"` → `"Billing"` |
| Incident type | `"ac"` → `"AC Issue"`, `"leak"` → `"Plumbing / Drainage Issue"` |

Normalisation order: property → incident → severity → status → department → category.  
Longest-match-first within each alias table.

Results from `normalize_query()` are cached via `@lru_cache(maxsize=512)`.

**Time expression hints** (`get_time_expression_hint`):

When the question contains `"this week"`, `"this month"`, `"last week"`, or `"last month"`, an explicit SQL date filter snippet is injected as an entity hint in the prompt — overriding the model's tendency to generate rolling windows or incorrect date_part comparisons.

Note: `_TIME_SQL_HINTS` uses `date_parse(snapshotdate, ...)` syntax (legacy Athena hints). These are corrected by the `fix_snapshotdate` + `fix_date_add_to_dateadd` post-processors before the SQL is used.

---

## 5. Prompt Construction

**File**: `app/prompt.py`

### Schema loading (`app/schema_loader.py`)

`load_schema(target)` queries `information_schema.columns` for all tables in the target config. Result cached in `_SCHEMA_CACHE` (in-memory, process lifetime). Converted to DDL `CREATE TABLE` statements via `schema_to_ddl()`.

`load_column_values(target)` fetches `DISTINCT` values from tables listed in `ENUM_COLUMNS`. Injects them as an exact-values section in the prompt. Cached in `_COLUMN_VALUES_CACHE`.

Current ENUM columns (default target):
- `master_maintenance_status.status_name` (limit 50)
- `master_job_priority.priority_name` (limit 50)

### Property UUID restriction

`find_property_uuid_column(schema)` auto-detects the property filter column (priority: exact `property_uuid` → contains both "property" and "uuid" → exact `property`).

If `property_uuid` is set in `req.context`, injects mandatory filter into the prompt:
```
CRITICAL: Every query MUST include WHERE property_uuid IN ('uuid1', 'uuid2').
This is a mandatory access control filter — never omit it.
```

Post-processing fixers (`fix_property_column`, `inject_property_filter`) enforce this even if the model ignores the instruction.

### Prompt template

```
### Task
Generate a SQL query to answer [QUESTION]{normalized_text}[/QUESTION]
{additional_instructions}

### Database Schema
{ddl_schema}

### Answer
Given the database schema, here is the SQL query that [QUESTION]{normalized_text}[/QUESTION]
[SQL]
```

The `[SQL]` suffix is the SQLCoder stop token — `extract_sql()` splits on it to isolate the generated SQL from model preamble.

### `additional_instructions` content

The instructions block embeds:
- Redshift SQL syntax requirement
- All FK JOIN relationships with explicit column mappings
- Status semantics (exact lowercase values, `'open'` expansion)
- Priority term mapping (`"urgent"` → `WHERE p.priority_name = 'urgent'`)
- 8 concrete SQL examples covering common patterns
- 10 rules (LIMIT, no invented columns, no raw FK integers, date syntax, trend grouping, percentage formula, etc.)
- Property UUID access control filter (if applicable)
- Detected entity hints (if any)
- ENUM allowed values section (if any)

---

## 6. Model Inference

**File**: `app/sqlcoder.py`

### Model loading

```python
model_name = "defog/sqlcoder-7b-2"
# float16 (~13 GB VRAM) — default for L4 24GB
# 4-bit NF4 quantisation (~4–5 GB) — set USE_QUANTIZATION=true
```

Loaded once in `lifespan()`. Protected by `_model_lock` (threading.Lock). `device_map="auto"` with `GPU_MEMORY_CAP` (default `"11GiB"`) + `"cpu": "32GiB"` overflow.

### Inference parameters

```python
outputs = model.generate(
    max_new_tokens=max_tokens,  # default 256 from request payload
    do_sample=False,
    num_beams=1,                # greedy decode — deterministic, minimal VRAM
    eos_token_id=tokenizer.eos_token_id,
)
```

Greedy decode (`num_beams=1`) is deliberate: beam search (`num_beams=4`) was tried but caused CUDA OOM on the L4 by keeping 4× activations in memory simultaneously.

### SQL extraction (`extract_sql`)

1. Splits on `[SQL]` marker if present
2. Strips markdown code fences
3. Prefers CTE (`WITH ...`) over bare `SELECT` when CTE starts first
4. Normalises whitespace
5. Runs all schema-context-free fixers (see Section 7 — Stage A)
6. Enforces `LIMIT 100` cap

### LRU cache

Key: `md5(prompt + "::" + max_tokens)`  
Size: 500 entries (LRU eviction on oldest key when full)  
Cache hit: `latency_ms = 0`, `from_cache = True`

**Important**: Fixers run inside `extract_sql()` are applied before the cache write. The cached result already contains their corrections. Fixers in `main.py` (Stage B) run on every request, including cache hits.

---

## 7. SQL Post-Processing Fixers

All fixers are pure regex/string transforms. None make Redshift calls. Ordering is load-bearing in several cases (noted below).

### Stage A — Inside `extract_sql()` (runs once, result cached)

These fixers have no request-level context (no `allowed_tables`, no `property_uuid`, no question text).

| Order | Function | Trigger | Fix |
|-------|----------|---------|-----|
| 1 | `fix_date_parse_to_to_date` | `date_parse(` | Athena → Redshift: strips cast for TIMESTAMP cols, converts others to `TO_DATE()` |
| 2 | `fix_date_add_to_dateadd` | `date_add(` | Athena `date_add('unit', N, date)` → Redshift `DATEADD(unit, N, date)` |
| 3 | `fix_interval_to_dateadd` | `INTERVAL` | ANSI `expr - INTERVAL 'N unit'` → `DATEADD(unit, -N, expr)` |
| 4 | `fix_snapshotdate` | `snapshotdate` | Replaces hallucinated `snapshotdate` → `created_date`, strips any `TO_DATE()` wrapper since `created_date` is already TIMESTAMP |
| 5 | `fix_unaliased_table_ref` | `maintenance_order AS m` | `maintenance_order.col` → `m.col` — **must run before** `fix_table_names` in main.py would add `maintenance_order` alias |
| 6 | `fix_dateadd_quoted_unit` | `DATEADD('` | `DATEADD('day', N, d)` → `DATEADD(day, N, d)` — Redshift requires unquoted unit identifier |
| 7 | `fix_date_part_this_period` | `date_part(` | Two-pattern match (period-first AND year-first ordering) for `date_part('week'/'month', col) = date_part(..., CURRENT_DATE) AND date_part('year', ...) = ...` → `col >= DATE_TRUNC('week'/'month', CURRENT_DATE)` |
| 8 | `fix_extract_week_trend` | `EXTRACT` + `WEEK` | Replaces `EXTRACT(YEAR FROM col) AS y, EXTRACT(WEEK FROM col) AS w` → `DATE_TRUNC('week', col) AS week_start`; also rewrites GROUP BY and ORDER BY aliases (`YEAR`, `WEEK`, `YEAR_NUM`, `WEEK_NUM`) |
| 9 | `fix_spurious_department_join` | `department` | Removes `JOIN department ON m.department_name = ...` (hallucinated column) or `JOIN department ON m.department_uuid = ...` (no FK path); also strips dangling WHERE conditions referencing removed alias |
| 10 | `fix_main_table_fk_names` | `m.status_name` / `m.priority_name` | When JOIN is absent: `m.status_name = 'X'` → `m.status IN (SELECT status_id FROM master_maintenance_status WHERE status_name = 'X')` |
| 11 | `fix_scalar_subquery_eq` | `= (SELECT` | `= (SELECT ...)` → `IN (SELECT ...)` — prevents "more than one row returned by a subquery" runtime error |
| 12 | `fix_status_case` | status/priority string literals | Normalises Title Case → lowercase: `'Completed'` → `'completed'`; maps `'Open'`/`'open'` → `IN ('pending', 'delayed', 'acknowledged')` |
| 13 | `fix_department_column` | `.department` (no suffix) | `alias.department` → `alias.department_name` (wrong column; actual column is `department_name`) |
| 14 | `fix_year_extract_comparison` | `EXTRACT(YEAR` | `EXTRACT(YEAR FROM col) = DATE_TRUNC(...)` → `= EXTRACT(YEAR FROM CURRENT_DATE)` — type mismatch: EXTRACT returns integer, DATE_TRUNC returns timestamp |

After all fixers: enforces `LIMIT 100` (adds if absent; clamps to 100 if > 100).

---

### Stage B — In `main.py` after inference (runs every request, including cache hits)

These fixers have access to request context (`allowed_tables`, `property_uuid`, `question_text`).

**Ordering is critical** — deviating from this order causes bugs:

```python
result["query"] = fix_snapshotdate(result["query"])
result["query"] = fix_table_names(result["query"], allowed_tables)
result["query"] = fix_unaliased_table_ref(result["query"])          # ← MUST be after fix_table_names
result["query"] = fix_dateadd_quoted_unit(result["query"])
result["query"] = fix_date_part_this_period(result["query"])
result["query"] = fix_extract_week_trend(result["query"])
result["query"] = fix_spurious_department_join(result["query"])
result["query"] = fix_main_table_fk_names(result["query"])
result["query"] = fix_scalar_subquery_eq(result["query"])
result["query"] = fix_status_case(result["query"])
result["query"] = fix_department_column(result["query"])
result["query"] = fix_invalid_extract_from_table(result["query"])
result["query"] = fix_year_extract_comparison(result["query"])
result["query"] = fix_impossible_this_period_filter(result["query"])
result["query"] = fix_last_week_filter(result["query"], sanitized_text)
# Then: fix_property_column, inject_property_filter (require property_uuid context)
```

Additional Stage B-only fixers:

| Function | Trigger | Fix |
|----------|---------|-----|
| `fix_table_names(sql, allowed_tables)` | Unknown table in FROM/JOIN | Two-pass: (1) remap `table_variant` → `table` for allowed-table prefixes; (2) replace unknown `FROM/JOIN target` → primary table. Negative lookbehind `(?<!\.)` prevents matching column refs like `m.department_uuid`. |
| `fix_invalid_extract_from_table` | `EXTRACT(unit FROM table_name)` | Model passes a table name instead of a column expression: `EXTRACT(YEAR FROM maintenance_order)` → `DATE_TRUNC('week', CURRENT_DATE)` |
| `fix_impossible_this_period_filter` | `>= DATE_TRUNC AND < DATE_TRUNC` (same period) | Removes self-contradicting upper bound: `created_date >= DATE_TRUNC('week', ...) AND created_date < DATE_TRUNC('week', ...)` removes the AND clause |
| `fix_last_week_filter(sql, question_text)` | `"last week"` in question | Converts rolling `-7 day` window → calendar Mon–Sun: `DATEADD(day, -7, CURRENT_DATE)` → `DATEADD(week, -1, DATE_TRUNC('week', CURRENT_DATE)) AND ... < DATE_TRUNC('week', CURRENT_DATE)` |
| `fix_property_column(sql, col, uuids)` | UUID values in wrong property column | Rewrites `property_name IN (uuid)` → `property_uuid IN (uuid)` when model uses wrong column name |
| `inject_property_filter(sql, col, uuids)` | UUID values absent from SQL | Injects `WHERE property_uuid IN (...)` if model dropped the mandatory access control filter entirely |

### Why `fix_unaliased_table_ref` must follow `fix_table_names`

`fix_table_names` uses regex `\b(FROM|JOIN)\s+(\w+)\b`. This pattern matches `EXTRACT(YEAR FROM m.col)` — treating `m` as an unknown table name — and would replace it with `maintenance_order`, producing `EXTRACT(YEAR FROM maintenance_order.col)`. Running `fix_unaliased_table_ref` after repairs this back to `m.col`. Both fixers run in both stages, so the ordering applies in both.

---

## 8. SQL Security Validation

**File**: `app/security.py`

### Forbidden operations

Blocks any SQL containing these keywords (case-insensitive, whole-word match):
`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, `GRANT`, `REVOKE`, `CREATE`

### Redshift-unsupported features

Blocks: `DISTINCT ON`, `RETURNING`, `FOR UPDATE`, `FOR SHARE`

### Table allowlist enforcement

`extract_tables(sql)` uses 8 regex patterns to find all FROM/JOIN targets. Filters out:
- SQL keywords and common English words
- Names ≤ 2 characters
- System pseudo-columns (`CURRENT_DATE`, `NOW`, etc.)

**CTE aliases** (e.g., `WITH prev AS (...)`) are excluded from the table check — they are valid SQL but not real tables.

Any table not in `allowed_tables` raises `ValueError: Unauthorized table(s): ...`. This error propagates as `HTTP 400`.

---

## 9. Redshift Execution

**File**: `app/redshift_client.py`

### Connection management

Opens a fresh connection per request (`get_connection()`). No connection pool — connections are opened and closed synchronously within the executor thread. Each connection:
1. Sets `search_path TO {schema}, public`
2. Executes the SQL
3. Fetches up to `max_rows` rows (`fetchmany`)
4. Closes immediately

### Query result cache

`_QUERY_CACHE`: `md5(sql + ":" + target + ":" + max_rows)` → normalized result dict  
Size: 100 entries (LRU eviction)

Only SELECT and CTE (WITH) queries are permitted — checked before execution.

### Error handling

Any exception from `redshift_connector` is caught and re-raised as `RuntimeError(f"Redshift query failed: {e}")`. This RuntimeError is caught in `main.py` to trigger the self-correction loop.

### Result normalisation

Returns:
```json
{
  "columns": ["col1", "col2"],
  "rows": [{"col1": "val", "col2": "val"}, ...],
  "row_count": N
}
```

All values are cast to `str` (or `None`).

---

## 10. Output Formatting

### Column formatter (`app/column_formatter.py`)

`format_execution_data(data)` maps raw DB column names to human-readable display names, remapping both `columns` list and row dict keys.

Transformation pipeline per column name:
1. Special-case exact matches: `vip` → `VIP`, `uuid` → `UUID`, `id` → `ID`
2. Strip common suffixes: `_name`, `_text`, `_no`, `_uuid`, `_id`
3. Split on `_`
4. Expand camelCase
5. Identify known word boundaries: `snapshotdate` → `snapshot date`
6. Capitalise each word

Examples: `status_name` → `Status`, `created_date` → `Created Date`, `snapshotdate` → `Snapshot Date`, `actual_cost` → `Actual Cost`

### Chart formatter (`app/chart_formatter.py`)

`format_for_chart(data, display_type)` reshapes results:

| Display type | Output |
|-------------|--------|
| `metric` | `{"value": rows[0][col0], "label": col0}` |
| `bar` / `pie` / `line` | `{"labels": [...], "values": [...], "label_column": col0, "value_column": col1}` |
| `table` | `null` (frontend uses raw `execution.data`) |

Assumes: col[0] = label axis, col[1] = numeric axis.

---

## 11. Display Type Detection

**File**: `app/display_hint.py`

Priority cascade (first match wins):

1. **User-specified** — `req.display.type` in request payload
2. **Hardcoded map** — 60 exact-match demo questions in `QUERY_DISPLAY_TYPE_MAP`
3. **Question pattern matching** — regex patterns on `req.text`
4. **SQL + result analysis** — inspects GROUP BY, aggregation functions, row/column counts

### SQL + result analysis rules

| Condition | Display type |
|-----------|-------------|
| 1 row × 1 col | `metric` |
| 1 row × ≤3 cols + aggregation | `metric` |
| time-series GROUP BY + aggregation | `line` |
| 2 cols + ≥2 rows + aggregation + GROUP BY + date-named first col | `line` |
| 2 cols + ≤10 rows + aggregation + GROUP BY | `pie` |
| GROUP BY + aggregation + ≤50 rows | `bar` |
| GROUP BY + aggregation + >50 rows | `table` |
| default | `table` |

---

## 12. Rate Limiting

**File**: `app/rate_limiter.py`

### Token bucket algorithm

Tokens refill continuously at `rate` tokens/second up to `capacity`. Each request consumes 1 token. If no token available, returns `retry_after` = (tokens_needed − current_tokens) / rate.

Thread-safe via `threading.Lock` in `_refill()` and `consume()`.

### Per-client limiting

Optional — activated when `client_id` passed to `check_rate_limit()`. Currently not wired to client identity in the `/nlq/execute` handler (global bucket only).

### Stats endpoint

`GET /rate-limit/stats` returns:
```json
{
  "queue_size": N,
  "queue_max": 50,
  "tokens_available": 7.4,
  "requests_per_second": 2.0,
  "burst_capacity": 10
}
```

---

## 13. Caching Architecture

Three independent caches, all in-process (lost on restart):

| Cache | Location | Key | Size | Eviction |
|-------|----------|-----|------|----------|
| SQL generation | `_sql_cache` in `sqlcoder.py` | `md5(prompt::max_tokens)` | 500 | LRU (oldest first) |
| Query results | `_QUERY_CACHE` in `redshift_client.py` | `md5(sql:target:max_rows)` | 100 | LRU |
| Schema | `_SCHEMA_CACHE` in `schema_loader.py` | target name | unbounded | Never evicted |
| Column values | `_COLUMN_VALUES_CACHE` in `schema_loader.py` | target name | unbounded | Never evicted |
| Query normalizer | `lru_cache(512)` on `normalize_query` | raw text | 512 | LRU |

**SQL cache invalidation note**: The SQL cache key includes the full prompt, which embeds the schema DDL. If the schema changes, cache keys change automatically — no manual invalidation needed. However, if prompt instructions change (e.g., editing `additional_instructions`), the server must restart to clear the cache, or call `clear_sql_cache()` directly.

---

## 14. API Reference

### `POST /nlq/execute`

**Request body:**
```json
{
  "text": "How many open high priority maintenance orders?",
  "context": {
    "property_uuid": "uuid1,uuid2",
    "language": "en"
  },
  "sql": {
    "dialect": "redshift",
    "tables": []
  },
  "execution": {
    "dry_run": false,
    "max_rows": 100,
    "redshift_target": "default"
  },
  "model": {
    "max_tokens": 256
  },
  "display": {
    "type": "metric"
  },
  "trace": {
    "request_id": "optional-uuid",
    "source": "fcs1-ui"
  }
}
```

**Response (200):**
```json
{
  "success": true,
  "sql": {
    "query": "SELECT COUNT(*) FROM ...",
    "confidence": 0.90
  },
  "execution": {
    "executed": true,
    "row_count": 1,
    "data": {
      "columns": ["Count"],
      "rows": [{"Count": "47"}],
      "row_count": 1
    }
  },
  "display": {
    "type": "metric",
    "chart_data": {"value": "47", "label": "Count"}
  },
  "explanation": {
    "summary": "SQL generated for Redshift execution.",
    "assumptions": []
  },
  "trace": {
    "request_id": "req-abc123",
    "latency_ms": {
      "prompt_ms": 12,
      "model_ms": 4200,
      "postprocess_ms": 3,
      "query_ms": 180,
      "total_ms": 4395
    },
    "redshift_target": "default",
    "allowed_tables": ["maintenance_order", "master_maintenance_status", "master_job_priority", "property_location"],
    "input_warnings": [],
    "correction_attempts": 0
  }
}
```

**Error responses:**

| Code | Cause |
|------|-------|
| 400 | Input validation failed, SQL validation failed, forbidden SQL operation, unauthorized table, Redshift execution failed (after all retries) |
| 429 | Rate limit exceeded |
| 500 | Unexpected internal error |

### `GET /health`

Returns service status and rate limiter stats.

### `GET /nlq/suggestions?target=default`

Returns generated query suggestions based on schema.

### `GET /nlq/schema?target=default`

Returns schema summary for target.

### `GET /logs?limit=100`

Returns last N request/response logs (in-memory, max 100).

### `GET /rate-limit/stats`

Returns current rate limiter state.

---

## 15. Configuration Reference

All configuration via environment variables (`.env` file or shell):

| Variable | Default | Description |
|----------|---------|-------------|
| `REDSHIFT_HOST` | `""` | Redshift Serverless endpoint |
| `REDSHIFT_PORT` | `5439` | Redshift port |
| `REDSHIFT_DBNAME` | `dev` | Database name |
| `REDSHIFT_USER` | `""` | Username |
| `REDSHIFT_PASSWORD` | `""` | Password |
| `REDSHIFT_SCHEMA` | `nxg_107747471_q2sj` | Schema name (sets search_path) |
| `USE_QUANTIZATION` | `false` | `true` = 4-bit NF4 (~4–5 GB); `false` = float16 (~13 GB) |
| `GPU_MEMORY_CAP` | `11GiB` | GPU allocation ceiling (leave headroom for OS/desktop) |

### Adding a new Redshift target

1. Add entry to `REDSHIFT_TARGETS` in `app/redshift_config.py`:
   ```python
   "my_target": {
       "schema": "my_schema_name",
       "tables": ["table1", "table2"],
   }
   ```
2. Add entry to `ENUM_COLUMNS` for any categorical columns:
   ```python
   "my_target": [
       {"table": "my_status_table", "columns": ["status_name"], "limit": 50},
   ]
   ```
3. Schema and ENUM values are auto-fetched on first request and cached.

---

## 16. Known Limitations & Failure Modes

### Model-level (7B parameter limit)

| Failure | Symptom | Post-processor fix | Status |
|---------|---------|-------------------|--------|
| `snapshotdate` hallucination | `WHERE snapshotdate = ...` | `fix_snapshotdate` | Fixed |
| Raw FK integers | `WHERE m.status = 1` | `fix_main_table_fk_names` | Partially fixed — requires JOIN absent |
| Department column hallucination | `JOIN department ON m.department_uuid = ...` | `fix_spurious_department_join` | Fixed |
| Title Case status values | `WHERE s.status_name = 'Completed'` | `fix_status_case` | Fixed |
| Athena date syntax | `date_add('day', -7, current_date)` | `fix_date_add_to_dateadd` | Fixed |
| Quoted DATEADD unit | `DATEADD('day', ...)` | `fix_dateadd_quoted_unit` | Fixed |
| date_part calendar filter | `date_part('week', col) = date_part('week', CURRENT_DATE) AND ...` | `fix_date_part_this_period` | Fixed |
| EXTRACT week trend | `EXTRACT(YEAR FROM col) AS YEAR, EXTRACT(WEEK FROM col) AS WEEK` | `fix_extract_week_trend` | Fixed |
| Scalar subquery | `m.status = (SELECT ...)` | `fix_scalar_subquery_eq` | Fixed |
| Unaliased table in EXTRACT | `EXTRACT(YEAR FROM maintenance_order)` | `fix_invalid_extract_from_table` | Fixed |
| Wrong EXTRACT comparison type | `EXTRACT(YEAR FROM col) = DATE_TRUNC(...)` | `fix_year_extract_comparison` | Fixed |
| Impossible period filter | `>= DATE_TRUNC('week') AND < DATE_TRUNC('week')` | `fix_impossible_this_period_filter` | Fixed |
| Rolling window for "last week" | `-7 day` instead of Mon–Sun | `fix_last_week_filter` | Fixed |
| Two simultaneous FK JOINs + raw int | `m.status = 1` when also JOINing priority | `fix_main_table_fk_names` skips if JOIN present | **Open (C05)** |

### Schema constraints (unanswerable queries)

- **Department breakdowns**: `maintenance_order` has no `department_uuid` FK column. Any query asking "how many orders per department" cannot be answered. The 8 department-related eval questions were removed from the test suite.
- **`cume_dist()` / window functions for "distribution"**: Model occasionally generates `cume_dist()` when asked for "distribution by X". Post-processor cannot reliably detect intent to replace with COUNT+GROUP BY.

### Operational constraints

- Model inference is not parallelisable — `_model_lock` serialises all requests to a single inference thread. Under concurrent load, requests queue behind each other. The `ThreadPoolExecutor` (max_workers=4) handles multiple threads, but only one holds `_model_lock` at a time.
- All three in-process caches are lost on restart. Cold start re-fetches schema from Redshift on first request.
- The query result cache (`_QUERY_CACHE`) caches by exact SQL text. Two semantically equivalent queries with different whitespace produce different cache keys.
- `max_tokens=256` (request default) is sufficient for most single-table queries. Complex multi-CTE queries may truncate; increase via `"model": {"max_tokens": 512}` in the request.

### Eval suite status (as of 2026-05-14)

**30/31 (96%)** pass rate on live Redshift execution (`test/eval_maintenance.py`).

| Category | Score |
|----------|-------|
| aggregation | 4/4 |
| date_filter | 7/7 |
| hallucination_guard | 2/2 |
| location | 2/2 |
| simple_count | 7/7 |
| trend | 4/4 |
| group_by | 4/5 |

Single remaining failure: **C05** — "Show high priority open maintenance orders" — model generates `m.status = 1` (raw integer) when asked for both a status and priority filter simultaneously.
