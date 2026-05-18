# NLQ → Athena SQL Pipeline

Full architecture reference for the `/nlq/execute` endpoint. Covers every stage from HTTP request to JSON response, including all post-processing fixers, caching layers, and fallback strategies.

---

## High-Level Overview

```
HTTP POST /nlq/execute
        │
        ▼
┌───────────────────┐
│  1. Input         │  input_validator.py  — XSS / injection / length
│     Validation    │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  2. Rate          │  rate_limiter.py     — token bucket, 2 req/s, burst 10
│     Limiting      │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  3. Target        │  athena_config.py    — resolve DB/table from athena_target
│     Resolution    │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  4. Prompt        │  prompt.py           — schema DDL + entity hints + rules
│     Construction  │  query_normalizer.py — alias normalisation + SQL hints
│                   │  schema_loader.py    — Glue schema (cached) + ENUM values
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  5. Model         │  sqlcoder.py         — LLM inference in ThreadPoolExecutor
│     Inference     │                        LRU cache (500 entries)
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  5a. SQL Extract  │  sqlcoder.py         — extract_sql(): CTE vs SELECT,
│  + Fixers Pass 1  │                        5 post-processing fixers
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  5b. Fixers       │  main.py (imports    — 7 context-aware fixers
│      Pass 2       │  from sqlcoder.py)     (table names, property filter, etc.)
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  6. SQL           │  security.py         — block forbidden ops, table ACL
│     Validation    │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐    ┌─────────────────────────────────────┐
│  7. Athena        │───▶│  Self-Correction Loop (max 2 retries)│
│     Execution     │    │  build_correction_prompt → re-infer  │
│  (or dry_run)     │    │  → fix → validate → retry Athena     │
└────────┬──────────┘    └─────────────────────────────────────┘
         │
         ▼
┌───────────────────┐
│  8. Column        │  column_formatter.py — raw DB names → human-readable
│     Formatting    │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  9. Display Type  │  display_hint.py     — 4-priority detection system
│     Detection     │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 10. Chart         │  chart_formatter.py  — reshape data for bar/pie/line/metric
│     Formatting    │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 11. Response +    │  request_logger.py   — persist to logs/api_requests.json
│     Logging       │
└───────────────────┘
```

---

## Stage-by-Stage Detail

### Startup (once, not per-request)

**File:** `app/main.py` → `lifespan()`, `app/sqlcoder.py` → `load_model()`

On first boot, the model is loaded into GPU memory and held for the life of the process. A `ThreadPoolExecutor(max_workers=4)` is created for non-blocking inference. The global rate limiter is initialised.

```
Model load path (sqlcoder.py):
  USE_QUANTIZATION=false (default) → float16, ~13GB VRAM (recommended for L4 24GB)
  USE_QUANTIZATION=true            → 4-bit NF4, ~4-5GB VRAM (slower, lower quality)
```

Model is accessed under `_model_lock` (threading.Lock) — only one inference runs at a time.

---

### Stage 1 — Input Validation

**File:** `app/input_validator.py`  
**Function:** `validate_nlq_input(text, strict_mode=True)`

| Check | Detail |
|-------|--------|
| Null / empty | Immediate reject |
| Min length | < 2 chars → reject |
| Max length | > 2000 chars → reject (truncated copy in error) |
| XSS detection | 9 regex patterns: `<script>`, `javascript:`, `on*=`, `<iframe>`, `<object>`, `<embed>`, `<img src=javascript:>`, CSS `expression()`, `url(javascript:)` |
| Injection detection | 12 regex patterns: `; DROP`, `; DELETE`, `; INSERT`, `UNION SELECT`, `'; --`, etc. |
| Control characters | Strips `\x00–\x08`, `\x0b`, `\x0c`, `\x0e–\x1f` |
| HTML escaping | `html.escape()` neutralises any residual XSS |
| Whitespace | Collapses all runs of whitespace |

Returns `ValidationResult(is_valid, sanitized_text, warnings, error)`. The sanitised text (not the raw input) is used for all downstream stages.

---

### Stage 2 — Rate Limiting

**File:** `app/rate_limiter.py`  
**Function:** `rate_limiter.check_rate_limit()`

Implements a **token bucket** algorithm:

```
Config (get_rate_limiter()):
  requests_per_second: 2.0
  burst_size:          10
  queue_size:          50
  queue_timeout:       60s
```

- Each request consumes 1 token. Tokens refill at 2/s up to burst capacity of 10.
- If insufficient tokens: returns HTTP 429 with `Retry-After` header (exact seconds until refill).
- Per-client buckets are also available (same config) but currently not wired by client ID.
- `GET /rate-limit/stats` exposes current token count and queue depth.

---

### Stage 3 — Target Resolution

**File:** `app/athena_config.py`

Maps the `athena_target` field to a concrete AWS configuration:

| Target key | Database | Table | S3 output |
|---|---|---|---|
| `peninsula_incident` (default) | `peninsula-incident2` | `incident_combine` | `s3://athena-query-results-ap-east-1/nlq/` |
| `londoner_granded` | `londoner_granded` | `ldco_testing` | `s3://athena-query-results-ap-east-1/nlq/` |

`allowed_tables` is taken from the request payload `sql.tables` if provided, otherwise from `ATHENA_TARGETS[target]["tables"]`.

**Adding a new target:** add entries to both `ATHENA_TARGETS` and `ENUM_COLUMNS` dicts. Schema auto-fetches from Glue on first request.

---

### Stage 4 — Prompt Construction

**Files:** `app/prompt.py`, `app/query_normalizer.py`, `app/schema_loader.py`

This stage has three sub-phases that run in sequence:

#### 4a. Query Normalisation (`query_normalizer.py`)

`preprocess_query(text)` runs the text through a pipeline of alias resolvers:

1. **Room reference expansion** — `"room 1018"` → `"Room 1018"`
2. **Property name normalisation** — `"bkk"` → `"The Peninsula Bangkok"` (longest-match alias dict)
3. **Incident type normalisation** — `"ac issue"` → `"AC Issue"`, `"leak"` → `"Plumbing / Drainage Issue"`
4. **Severity normalisation** — `"serious"` → `"high"`, `"urgent"` → `"critical"`
5. **Status normalisation** — `"open"` → `"pending"`, `"done"` → `"completed"`
6. **Department normalisation** — `"f&b"` → `"Food & Beverage"`, `"eng"` → `"Engineering"`
7. **Category normalisation** — `"noise"` → `"Disturbance"`, `"billing"` → `"Billing"`

All resolvers use longest-match-first to avoid partial conflicts. Results cached via `@lru_cache(maxsize=512)`.

`get_entity_hints()` converts matched entities into SQL hints injected into the prompt:
```
- Use severity_name = 'high' in WHERE clause
- Use department_name = 'Housekeeping' in WHERE clause
```

#### 4b. Calendar Time Hint (`query_normalizer.py`)

`get_time_expression_hint(text)` detects calendar keywords and injects **exact SQL snippets** rather than letting the model infer the date logic:

| Expression | Injected hint |
|---|---|
| `"this week"` | `date_parse(snapshotdate, '%Y-%m-%d') >= date_trunc('week', current_date)` |
| `"this month"` | `date_parse(snapshotdate, '%Y-%m-%d') >= date_trunc('month', current_date)` |
| `"last week"` | `>= date_add('week', -1, date_trunc('week', current_date)) AND < date_trunc('week', current_date)` |
| `"last month"` | `>= date_add('month', -1, date_trunc('month', current_date)) AND < date_trunc('month', current_date)` |

This overrides the model's tendency to use rolling windows (`date_add('day', -7)`) for calendar-boundary queries.

#### 4c. Schema + ENUM Loading (`schema_loader.py`)

- `load_schema(target)` — fetches table columns + partition keys from AWS Glue. **Cached in-memory** for the process lifetime. Converted to DDL format via `schema_to_ddl()` (required by SQLCoder's prompt format).
- `load_column_values(target)` — fetches up to 50 DISTINCT values per ENUM column from Athena (cached similarly). Only cached when all columns succeed; partial failures are retried on next request.

ENUM columns per target:

| Target | ENUM columns |
|---|---|
| `peninsula_incident` | department_name, category_name, severity_name, status_name, property_name, profile_name, temperament_text, vip |
| `londoner_granded` | department_name, category_name, severity_name, status_name, property_name |

#### 4d. Property UUID Injection

`find_property_uuid_column(schema)` auto-detects the property column by priority:
1. Exact column/partition named `property_uuid`
2. Column containing both `"property"` and `"uuid"`
3. Column named exactly `property`
4. Partition key named `property`

Once found, the prompt includes:
```
CRITICAL: You MUST include WHERE property IN ('uuid1', 'uuid2') in every query.
```

#### 4e. Prompt Assembly

`build_prompt()` assembles the final prompt in SQLCoder's required format:

```
### Task
Generate a SQL query to answer [QUESTION]{normalized_text}[/QUESTION]

{additional_instructions}   ← 30+ line rule block covering all Athena gotchas

### Database Schema
{DDL CREATE TABLE statements from Glue}

### Answer
Given the database schema, here is the SQL query that [QUESTION]{normalized_text}[/QUESTION]
[SQL]
```

The `additional_instructions` block encodes all known model failure modes as explicit rules:
- snapshotdate type handling, date arithmetic syntax, BIGINT column restrictions
- Rolling vs calendar window semantics, CTE structure for trend queries
- VIP/percentage/AVG-vs-SUM patterns, single-table constraint, property column gotcha

---

### Stage 5 — Model Inference

**File:** `app/sqlcoder.py`  
**Function:** `run_sqlcoder(prompt, max_tokens)`

```python
# Non-blocking: runs in ThreadPoolExecutor
result = await loop.run_in_executor(_executor, _run_model_inference, prompt, max_tokens)
```

**Caching:** MD5 hash of `prompt + max_tokens` → dict lookup before any GPU work. Cache size capped at 500 (FIFO eviction). Cache hits return `latency_ms=0`.

**Generation parameters:**
```python
model.generate(
    do_sample=False,     # Greedy (deterministic)
    num_beams=4,         # Beam search for quality
    max_new_tokens=256,  # Default (configurable in request)
)
```

Only newly generated tokens are decoded (prompt tokens are sliced off by `input_length`).

---

### Stage 5a — SQL Extraction + Fixers Pass 1

**File:** `app/sqlcoder.py`  
**Function:** `extract_sql(raw_output)`

Extracts SQL from the model's raw text output:
1. Splits on `[SQL]` marker (SQLCoder prompt format)
2. Strips markdown code fences (` ```sql `, ` ``` `)
3. **CTE detection:** if `WITH \w...` appears before (or instead of) a bare `SELECT`, the full CTE is used — prevents capturing only an inner SELECT inside a CTE body
4. Collapses whitespace

Then applies **5 fixers in order:**

| Fixer | What it fixes |
|---|---|
| `fix_date_part()` | `date_part('year', snapshotdate)` → `year(date_parse(snapshotdate, '%Y-%m-%d'))` and same for `EXTRACT(YEAR FROM snapshotdate)` |
| `fix_date_comparisons()` | Bare `snapshotdate >= date_add(...)` → `date_parse(snapshotdate, '%Y-%m-%d') >= date_add(...)`. Handles forward and reverse comparisons. Also fixes `date_trunc('month', snapshotdate)` and `year(snapshotdate)`. |
| `fix_bigint_date_comparisons()` | `created_date >= current_date` → `date_parse(snapshotdate, '%Y-%m-%d') >= current_date`. Covers CAST/DATE wrappers, standard comparisons, and BETWEEN. |
| `fix_interval_syntax()` | `current_date - INTERVAL '7 days'` → `date_add('day', -7, current_date)` |
| `fix_group_by_aliases()` | `GROUP BY month_label` (where `month_label` is a SELECT alias) → `GROUP BY 1` (ordinal). Athena rejects aliases in GROUP BY. |

Finally enforces `LIMIT 100` — adds if absent, caps if > 100.

---

### Stage 5b — Fixers Pass 2 (Context-Aware)

**File:** `app/main.py` (imports from `app/sqlcoder.py` and `app/prompt.py`)

Applied after inference, using request context (allowed tables, property UUIDs, question text):

| Fixer | What it fixes |
|---|---|
| `fix_table_names()` | Hallucinated table variants (`incident_combine_2025` → `incident_combine`). Fallback: any `FROM/JOIN unknown_table` is replaced with the primary allowed table. CTE aliases are excluded from replacement. |
| `fix_float_cast()` | `CAST(... AS FLOAT)` / `CAST(... AS FLOAT64)` → `CAST(... AS DOUBLE)`. Athena has no FLOAT type. |
| `fix_invalid_extract_from_table()` | `EXTRACT(YEAR FROM incident_combine)` hallucination → `date_parse(snapshotdate, '%Y-%m-%d') >= date_trunc('week', current_date)` |
| `fix_impossible_this_period_filter()` | Removes spurious upper bound: `>= date_trunc('week', current_date) AND < date_trunc('week', current_date)` (always false — same value on both sides) |
| `fix_last_week_filter()` | When question contains "last week" AND SQL uses rolling `-7 day` window → replaces with calendar Mon–Sun boundary |
| `fix_property_column()` | `WHERE property_name IN ('uuid')` → `WHERE property IN ('uuid')`. Triggered only when the IN clause contains a known property UUID. |
| `inject_property_filter()` | If none of the known UUIDs appear anywhere in the SQL, injects `WHERE property IN (...)` before GROUP BY / ORDER BY / LIMIT, or appends to end. |

**Why two passes?** Pass 1 (`extract_sql`) operates on raw model output without request context. Pass 2 requires `allowed_tables`, `property_uuids`, and `question_text` — information only available in the request handler.

---

### Stage 6 — SQL Validation

**File:** `app/security.py`  
**Function:** `validate_sql(sql, allowed_tables, dialect)`

| Check | Detail |
|---|---|
| Empty SQL | Raises ValueError immediately |
| Forbidden operations | Regex for: DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE, GRANT, REVOKE, CREATE |
| Athena-unsupported syntax | Blocks: `DISTINCT ON`, `RETURNING`, `FOR UPDATE`, `FOR SHARE` |
| Table extraction | 8 regex patterns covering FROM, JOIN, INNER JOIN, LEFT/RIGHT/FULL/CROSS/NATURAL JOIN |
| Keyword filtering | ~50 SQL keywords excluded from extracted table names |
| CTE alias exclusion | `WITH alias AS (...)` patterns extracted and excluded from table name check |
| Table ACL | Any extracted table not in `allowed_tables` → ValueError with name of unauthorized table |

Raises `ValueError` (→ HTTP 400) on any violation.

---

### Stage 7 — Athena Execution + Self-Correction Loop

**File:** `app/athena_client.py`  
**Function:** `execute_query(sql, target_name, max_rows)`

Skipped entirely when `execution.dry_run = true`.

**Caching:** MD5 of `sql + target_name + max_rows` → cached results dict (max 100, FIFO eviction).

**AWS execution:**
```python
client.start_query_execution(
    ResultReuseConfiguration={
        'ResultReuseByAgeConfiguration': {
            'Enabled': True,
            'MaxAgeInMinutes': 60   # Reuse Athena results up to 1 hour
        }
    }
)
```

**Polling:** Exponential backoff starting at 200ms, capped at 2s. Returns on `SUCCEEDED`, raises `RuntimeError` on `FAILED` or `CANCELLED` with the Athena reason string.

Results normalized to: `{columns: [...], rows: [{col: val, ...}], row_count: N}`

#### Self-Correction Loop

On `RuntimeError` from Athena, `main.py` retries up to **2 times**:

```
for attempt in range(3):        # 0, 1, 2
    try:
        execute_query(sql)
        break
    except RuntimeError as err:
        if attempt >= 2: raise
        correction_prompt = build_correction_prompt(
            failed_sql=current_sql,
            error_message=str(err).split('\n')[0][:300]  # first line only
        )
        correction_result = await run_in_executor(inference, correction_prompt)
        corrected_sql = fix_table_names(...) + fix_property_column(...) + inject_property_filter(...)
        corrected_sql = validate_sql(corrected_sql, ...)
        current_sql = corrected_sql
```

The correction prompt uses `build_correction_prompt()` which includes the failed SQL and trimmed error message alongside the same DDL schema and rules as the original prompt. `correction_attempts` is reported in the response trace.

---

### Stage 8 — Column Formatting

**File:** `app/column_formatter.py`  
**Function:** `format_execution_data(data)`

Remaps raw Athena column names to human-readable display names. Applied to both column headers and row dict keys.

**Transformation logic:**
1. Special cases: `vip` → `VIP`, `uuid` → `UUID`, `id` → `ID`
2. Strip suffixes: `_name`, `_text`, `_no`, `_uuid`, `_id`
3. Split concatenated words using a known-words list (`snapshotdate` → `snapshot` + `date`)
4. Title-case each word, rejoin with spaces
5. Re-apply special-case acronyms (e.g. `Vip` → `VIP`)

**Examples:**

| DB column | Display name |
|---|---|
| `snapshotdate` | `Date` |
| `category_name` | `Category` |
| `department_name` | `Department` |
| `actual_cost` | `Actual Cost` |
| `vip` | `VIP` |
| `severity_name` | `Severity` |
| `location_name` | `Location` |
| `recovery_no` | `Recovery` |

---

### Stage 9 — Display Type Detection

**File:** `app/display_hint.py`  
**Functions:** `get_display_type_from_question()`, `get_display_type()`

Four-level priority cascade:

```
Priority 1: User-specified display.type in request
      ↓ (if not set)
Priority 2: Exact match in QUERY_DISPLAY_TYPE_MAP
            60 hardcoded demo questions → {"table"|"metric"|"bar"|"pie"|"line"}
      ↓ (if no match)
Priority 3: Regex pattern matching on NL question
            metric  ← "how many", "what is the total", "in the last N days?"
            pie     ← "breakdown by severity/status/category", "distribution by"
            bar     ← "count by department/category", "which department"
            line    ← "per day/week/month", "over time", "trend"
            table   ← "show me all", "top N", "pending incidents"
      ↓ (if executed and data available)
Priority 4: SQL + result structure analysis
            metric  ← 1 row, 1 col  OR  1 row, ≤3 cols with aggregation
            line    ← time-grouped column in GROUP BY + aggregation
            pie     ← 2 cols, ≤10 rows, aggregation + GROUP BY
            bar     ← GROUP BY + aggregation, ≤50 rows
            table   ← default fallback
```

Supported types: `table`, `metric`, `bar`, `pie`, `line`, `card`, `list`

---

### Stage 10 — Chart Formatting

**File:** `app/chart_formatter.py`  
**Function:** `format_for_chart(execution_data, display_type)`

Only called for `bar`, `pie`, `line`, `metric` types when execution ran.

| Display type | Output structure |
|---|---|
| `metric` | `{value: <first_col_value>, label: <col_name>}` |
| `bar` / `pie` / `line` | `{labels: [...], values: [...], label_column: ..., value_column: ...}` — first column = labels, second column = numeric values |
| `table` | Returns `None` (raw `execution.data` used directly) |

---

### Stage 11 — Response + Logging

**File:** `app/main.py`, `app/request_logger.py`

**Response envelope:**

```json
{
  "success": true,
  "sql": {
    "query": "SELECT ...",
    "confidence": 0.90
  },
  "execution": {
    "executed": true,
    "row_count": 12,
    "data": {
      "columns": ["Category", "Count"],
      "rows": [...],
      "row_count": 12
    }
  },
  "display": {
    "type": "bar",
    "chart_data": {
      "labels": [...],
      "values": [...]
    }
  },
  "explanation": {
    "summary": "SQL generated for Athena execution.",
    "assumptions": []
  },
  "trace": {
    "request_id": "req-...",
    "latency_ms": {
      "prompt_ms": 45,
      "model_ms": 2300,
      "postprocess_ms": 3,
      "athena_ms": 1800,
      "total_ms": 4150
    },
    "athena_target": "peninsula_incident",
    "allowed_tables": ["incident_combine"],
    "input_warnings": [],
    "correction_attempts": 0
  }
}
```

**Logging:** `log_request()` appends to `logs/api_requests.json` (thread-safe file lock). Max 100 entries — oldest entry evicted on overflow. Accessible via `GET /logs?limit=N`.

**Error mapping:**

| Exception type | HTTP status | Logged |
|---|---|---|
| `HTTPException` | As-is (400 / 429) | No (re-raised) |
| `ValueError` (SQL validation) | 400 | Yes |
| `RuntimeError` (Athena exhausted) | 400 | Yes |
| Any other `Exception` | 500 | Yes (full traceback in server log) |

---

## Caching Summary

| Cache | Location | Key | Size | Eviction |
|---|---|---|---|---|
| Schema (Glue) | `schema_loader._SCHEMA_CACHE` | `target_name` | Unbounded | Process restart only |
| ENUM values | `schema_loader._COLUMN_VALUES_CACHE` | `target_name` | Unbounded | Process restart only |
| SQL generation | `sqlcoder._sql_cache` | MD5(prompt+max_tokens) | 500 | FIFO on overflow |
| Athena results | `athena_client._QUERY_CACHE` | MD5(sql+target+max_rows) | 100 | FIFO on overflow |
| Query normalisation | `query_normalizer.normalize_query` (lru_cache) | `text` string | 512 | LRU |
| Athena clients | `athena_client._ATHENA_CLIENTS` | `target_name` | Unbounded | Process restart only |

Additionally, Athena itself caches query results for 60 minutes via `ResultReuseByAgeConfiguration`.

---

## Data Constraints Reference

| Column | Type | Usage rule |
|---|---|---|
| `snapshotdate` | VARCHAR | **Never** compare directly. Always wrap: `date_parse(snapshotdate, '%Y-%m-%d')` |
| `created_date` | BIGINT | Use for `ORDER BY` only — **never** in `WHERE`, `GROUP BY`, or date functions |
| `incident_time` | BIGINT | Use for `ORDER BY` only |
| `completed_date` | BIGINT | Use for `ORDER BY` only |
| `cancelled_date` | BIGINT | Use for `ORDER BY` only |
| `property` | VARCHAR (partition key) | UUID values for access control. **Not** `property_name`. |
| `property_name` | VARCHAR | Hotel display name (e.g. `'The Peninsula Manila'`). Never use for UUID filtering. |
| `vip` | VARCHAR | Value `'Y'` for VIP. Filter: `WHERE vip = 'Y'` |
| `severity_name` | VARCHAR | Values lowercase: `'high'`, `'medium'`, `'low'`, `'critical'` |
| `status_name` | VARCHAR | Values lowercase: `'pending'`, `'completed'`, `'cancelled'` |

All queries capped at `LIMIT 100`.

---

## Key Architectural Decisions

**Single table, no joins.** All data lives in one denormalised table per target (`incident_combine`). The model is explicitly instructed never to join to dimension tables that don't exist.

**Two post-processing passes.** Pass 1 (`extract_sql`) runs without request context and fixes universal model output errors. Pass 2 (in `main.py`) requires `allowed_tables`, `property_uuids`, and `question_text` — context that only exists in the request handler.

**Model lock vs executor.** A single `threading.Lock` on the model means only one inference runs at a time, even though the executor has `max_workers=4`. This prevents GPU memory contention at the cost of serialising inference. The async loop is not blocked because inference runs in the executor.

**Property filter: two safety nets.** `fix_property_column()` corrects the wrong column name; `inject_property_filter()` catches the case where the filter is dropped entirely. Both run on every request — neither is redundant.

**Self-correction is bounded.** Maximum 2 retries prevents runaway latency. The correction prompt trims Athena's error to the first line (≤300 chars) to avoid token budget blowout.

**Calendar vs rolling windows.** `"last week"` = Mon–Sun (calendar). `"last 7 days"` = rolling. The normaliser, prompt rules, and `fix_last_week_filter` fixer all reinforce this distinction because the model consistently conflates them.
