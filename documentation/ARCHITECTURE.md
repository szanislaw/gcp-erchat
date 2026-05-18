# NLQ → Athena SQL Pipeline — Architecture

## Overview

This system is a **Natural Language Query (NLQ) to SQL API** built on FastAPI. It accepts free-text questions in English (or other supported languages), translates them into PrestoSQL/Athena-compatible queries using a local 7B LLM, executes them against AWS Athena, and returns results with visualization recommendations.

**Supported targets:** Peninsula Hotels incident data (`peninsula_incident`), Londoner Granded (`londoner_granded`).

---

## System Context

```
┌─────────────────────────────────────────────────────────────────┐
│                         Caller / UI                             │
│          (Web GUI at / or external service via API)             │
└───────────────────────────┬─────────────────────────────────────┘
                            │ POST /nlq/execute  (NLQRequest JSON)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Application                         │
│                        (app/main.py)                            │
│                                                                 │
│  ┌────────────┐   ┌────────────┐   ┌──────────────────────┐    │
│  │ CORS Layer │   │ Rate Limit │   │  PrettyJSONResponse  │    │
│  │ Middleware │   │ Dependency │   │  (indent=2 output)   │    │
│  └────────────┘   └────────────┘   └──────────────────────┘    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
             ┌──────────────▼──────────────┐
             │   NLQ Processing Pipeline   │
             │   (9 sequential stages)     │
             └─────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
  │  AWS Glue    │  │  SQLCoder    │  │   AWS Athena     │
  │ (schema def) │  │  7B LLM     │  │ (query engine)   │
  └──────────────┘  │ (on GPU/CPU)│  └──────────────────┘
                    └──────────────┘
```

---

## Request/Response Data Model

```
NLQRequest
├── text: str                    # Natural language question
├── context
│   ├── property_uuid: str       # UUID(s) used as access-control filter
│   ├── user_uuid: str
│   ├── location_name: str
│   └── language: en|zh|ms|ta
├── sql
│   ├── dialect: "athena"
│   └── tables: List[str]        # Optional allowlist override
├── execution
│   ├── dry_run: bool            # Skip Athena execution if true
│   ├── max_rows: int (100)
│   └── athena_target: str
├── model
│   ├── name: str
│   ├── temperature: float (0.0)
│   └── max_tokens: int (256)
├── display
│   └── type: table|metric|bar|line|pie|card|list
└── trace
    └── request_id: str
```

---

## Full Pipeline: Step-by-Step

```
POST /nlq/execute
        │
        ▼
┌───────────────────────────────────────┐
│  Step 1 — Input Validation            │
│  app/input_validator.py               │
│  • Length check (2–2000 chars)        │
│  • XSS pattern detection (9 patterns) │
│  • SQL injection detection (10 patt.) │
│  • HTML escape + control-char strip   │
│  → sanitized_text                     │
└──────────────────┬────────────────────┘
                   │
                   ▼
┌───────────────────────────────────────┐
│  Step 2 — Rate Limiting               │
│  app/rate_limiter.py                  │
│  • Token bucket (2 req/s, burst 10)   │
│  • Optional per-client buckets        │
│  → HTTP 429 if exhausted              │
└──────────────────┬────────────────────┘
                   │
                   ▼
┌───────────────────────────────────────┐
│  Step 3 — Target & Table Resolution   │
│  app/athena_config.py                 │
│  • Resolve athena_target              │
│  • Determine allowed_tables           │
│    (from payload or ATHENA_TARGETS)   │
└──────────────────┬────────────────────┘
                   │
                   ▼
┌───────────────────────────────────────┐
│  Step 4 — Prompt Construction         │
│  app/prompt.py  +  app/query_         │
│  normalizer.py  +  app/schema_        │
│  loader.py                            │
│                                       │
│  4a. Query Normalization              │
│     • Room ref expansion              │
│     • Entity alias resolution         │
│       (property, severity, status,    │
│        department, category,          │
│        incident type)                 │
│     • LRU-cached (512 entries)        │
│     → normalized_text, entity_hints   │
│                                       │
│  4b. Schema Load (AWS Glue)           │
│     • boto3 get_table per table       │
│     • In-memory cache (permanent)     │
│     → DDL CREATE TABLE statements     │
│                                       │
│  4c. Enum Values Load (Athena)        │
│     • DISTINCT per categorical col    │
│     • In-memory cache (permanent)     │
│     → exact allowed values section   │
│                                       │
│  4d. Assemble SQLCoder Prompt         │
│     • PrestoSQL syntax rules (~25)    │
│     • Property UUID restriction       │
│     • Time expression SQL hints       │
│     • Entity hints from step 4a       │
│     • Enum values                     │
│     • DDL schema                      │
└──────────────────┬────────────────────┘
                   │
                   ▼
┌───────────────────────────────────────┐
│  Step 5 — LLM Inference               │
│  app/sqlcoder.py                      │
│  • Model: defog/sqlcoder-7b-2         │
│  • float16 or 4-bit quantized         │
│  • num_beams=4, do_sample=False       │
│  • Thread-safe (_model_lock)          │
│  • Runs in ThreadPoolExecutor         │
│    (non-blocking async)               │
│  • MD5-keyed LRU cache (500 entries)  │
│  → raw SQL string                     │
└──────────────────┬────────────────────┘
                   │
                   ▼
┌───────────────────────────────────────┐
│  Step 5.5 — SQL Post-Processing       │
│  app/sqlcoder.py  (8 fixers)          │
│                                       │
│  Fixer 1: extract_sql()               │
│    CTE/SELECT extraction,             │
│    LIMIT cap at 100                   │
│  Fixer 2: fix_date_part()             │
│    EXTRACT/date_part on VARCHAR col   │
│  Fixer 3: fix_date_comparisons()      │
│    snapshotdate VARCHAR wrapping      │
│  Fixer 4: fix_bigint_date_comparisons │
│    BIGINT timestamp vs DATE mismatch  │
│  Fixer 5: fix_interval_syntax()       │
│    INTERVAL → date_add()             │
│  Fixer 6: fix_group_by_aliases()      │
│    Aliases → ordinal positions        │
│  Fixer 7: fix_float_cast()            │
│    FLOAT/FLOAT64 → DOUBLE            │
│  Fixer 8: fix_invalid_extract_        │
│    from_table()                       │
│    Malformed EXTRACT hallucination    │
│  Fixer 9: fix_impossible_this_        │
│    period_filter()                    │
│    Impossible date range removal      │
│  Fixer 10: fix_last_week_filter()     │
│    Rolling 7-day → calendar boundary │
│  Fixer 11: fix_table_names()          │
│    Hallucinated table name variants   │
│  Fixer 12: fix_property_column()      │
│    Wrong property column in WHERE IN  │
│  Fixer 13: inject_property_filter()   │
│    Safety net: inject mandatory       │
│    property UUID filter if absent     │
└──────────────────┬────────────────────┘
                   │
                   ▼
┌───────────────────────────────────────┐
│  Step 6 — SQL Security Validation     │
│  app/security.py                      │
│  • Forbid DML/DDL keywords            │
│  • Athena-unsupported syntax check    │
│  • Table extraction (8 regex patt.)   │
│  • CTE alias exclusion                │
│  • Unauthorized table check           │
│  → raises ValueError on violation     │
└──────────────────┬────────────────────┘
                   │
                   ▼
┌───────────────────────────────────────┐
│  Step 7 — Athena Execution            │
│  app/athena_client.py                 │
│  (skipped if dry_run=true)            │
│                                       │
│  • start_query_execution              │
│  • Exponential backoff poll           │
│    (200ms → 2000ms)                   │
│  • Athena result reuse (1 hour)       │
│  • MD5-keyed result cache (100 ent.)  │
│  • normalize → columns/rows/count     │
│                                       │
│  Self-Correction Loop (max 2 rounds): │
│  On RuntimeError from Athena:         │
│  → build_correction_prompt()          │
│  → re-run LLM inference               │
│  → re-apply fixers + validation       │
│  → retry Athena execution             │
└──────────────────┬────────────────────┘
                   │
                   ▼
┌───────────────────────────────────────┐
│  Step 8 — Column Name Formatting      │
│  app/column_formatter.py              │
│  • Strip _name/_text/_uuid suffixes   │
│  • snake_case → Title Case            │
│  • Special acronyms (VIP, ID, UUID)   │
│  • Remap row keys to display names    │
└──────────────────┬────────────────────┘
                   │
                   ▼
┌───────────────────────────────────────┐
│  Step 9 — Display Type Detection      │
│  app/display_hint.py                  │
│                                       │
│  Priority (first match wins):         │
│  P1: User-specified display.type      │
│  P2: Exact match in 60-entry demo map │
│  P3: Regex pattern matching on text   │
│      (metric/pie/bar/line/table)      │
│  P4: SQL structural analysis          │
│      (aggregation, GROUP BY,          │
│       time series detection)          │
└──────────────────┬────────────────────┘
                   │
                   ▼
┌───────────────────────────────────────┐
│  Step 10 — Chart Data Formatting      │
│  app/chart_formatter.py               │
│  (only for bar/pie/line/metric)       │
│  • metric → {value, label}            │
│  • bar/pie/line → {labels[], values[]}│
│    (col[0]=labels, col[1]=values)     │
└──────────────────┬────────────────────┘
                   │
                   ▼
┌───────────────────────────────────────┐
│  Response Assembly + Audit Log        │
│  app/request_logger.py                │
│  Returns:                             │
│  • sql.query + sql.confidence         │
│  • execution.data (formatted)         │
│  • display.type + chart_data          │
│  • trace (request_id, latency         │
│    breakdown, correction_attempts)    │
└───────────────────────────────────────┘
```

---

## Module Map

| Module | Responsibility |
|--------|---------------|
| `main.py` | FastAPI app, routing, middleware, pipeline orchestration |
| `models.py` | Pydantic request/response schemas |
| `input_validator.py` | XSS/injection detection, text sanitization |
| `rate_limiter.py` | Token bucket algorithm, per-request queue |
| `query_normalizer.py` | Entity alias resolution, NLQ preprocessing |
| `schema_loader.py` | AWS Glue schema fetch → DDL, enum value fetch |
| `prompt.py` | Prompt assembly for SQLCoder (initial + correction) |
| `sqlcoder.py` | LLM inference, SQL extraction, 8+ SQL fixers |
| `security.py` | DML/DDL blocking, table authorization |
| `athena_client.py` | Athena query execution, result normalization |
| `column_formatter.py` | DB column names → human-readable display names |
| `display_hint.py` | Visualization type selection (4-level priority) |
| `chart_formatter.py` | Transform Athena rows → chart-ready `{labels, values}` |
| `request_logger.py` | In-memory audit log (ring buffer) |
| `athena_config.py` | Target database config, enum column config |
| `utils.py` | `gen_request_id()` |

---

## Caching Architecture

Three independent cache layers are stacked to reduce latency at each bottleneck:

```
Request
   │
   ├─ [Cache L1] Query Normalization
   │  • lru_cache(maxsize=512) on normalize_query()
   │  • Key: raw text string
   │  • Saves: alias resolution CPU work
   │
   ├─ [Cache L2] SQL Generation
   │  • Dict, max 500 entries (FIFO eviction)
   │  • Key: MD5(prompt + max_tokens)
   │  • Saves: ~3–15s GPU inference time
   │
   ├─ [Cache L3] Athena Query Results
   │  • Dict, max 100 entries (FIFO eviction)
   │  • Key: MD5(sql + target + max_rows)
   │  • Saves: Athena execution RTT
   │  • Also uses Athena's built-in result reuse (1hr)
   │
   ├─ [Cache L4] Glue Schema
   │  • In-memory dict, never evicted
   │  • Key: target_name
   │  • Saves: Glue API call per request
   │
   └─ [Cache L5] Enum Column Values
      • In-memory dict, never evicted (only cached on full success)
      • Key: target_name
      • Saves: N × Athena DISTINCT queries per request
```

---

## Self-Correction Loop

When Athena returns a `RuntimeError` (query execution failure), the pipeline enters an automatic correction loop before surfacing the error to the caller:

```
Athena fails (RuntimeError)
        │
        ▼
   attempt < MAX_CORRECTIONS (2)?
        │ yes
        ▼
build_correction_prompt()
  Includes: original question + failed SQL + Athena error (first line, max 300 chars)
        │
        ▼
LLM inference (same model, same max_tokens)
        │
        ▼
Post-processing fixers (fix_table_names, fix_property_column, inject_property_filter)
        │
        ▼
SQL security validation
        │
        ▼
Retry Athena execution
        │
   success? ─── yes ──→ commit corrected SQL to response
        │ no
        ▼
   attempt++ → loop back (up to 2 corrections)
        │
   still failing after 2 corrections?
        ▼
Raise RuntimeError → HTTP 400 to caller
```

---

## Property Filter Safety Net

The `property_uuid` from the request context is a mandatory access-control boundary. Two independent fixers defend it:

```
LLM generates SQL
        │
        ▼
fix_property_column()         ← fixes wrong column name
  Model may use `property_name` instead of `property` (partition key).
  Detects any property* column in a WHERE IN clause that contains a known UUID
  and rewrites it to the correct partition column.
        │
        ▼
inject_property_filter()      ← ensures filter is present at all
  Checks if any of the known UUIDs appear anywhere in the SQL.
  If absent, injects `WHERE <property_col> IN ('uuid1', ...)` before
  GROUP BY / ORDER BY / LIMIT, or appends to end.
        │
        ▼
validate_sql()                ← downstream table authorization check
```

These two fixers run on both the initial generation path and inside the correction loop, so the property filter is enforced even on retried SQL.

---

## Async & Threading Model

```
FastAPI async event loop
        │
        ├── Synchronous work runs directly in the event loop
        │   (input validation, rate limiting, prompt building, display detection)
        │
        └── Blocking work offloaded to ThreadPoolExecutor (max_workers=4)
            │
            ├── LLM inference (run_sqlcoder)
            │   • Acquires _model_lock (threading.Lock)
            │   • torch.inference_mode() on GPU
            │
            └── Athena execution (execute_query)
                • boto3 polling loop with exponential backoff
```

`asyncio.get_event_loop().run_in_executor(_executor, fn)` is used for both blocking calls, preserving FastAPI's async request handling for all other concurrent requests.

---

## Query Normalization Detail

Before prompt construction, the raw question passes through a preprocessing pipeline that translates colloquial terms into exact database values:

```
"show me incidents at hk with fb issues"
        │
        ▼ expand_room_reference()    (no change here)
        │
        ▼ normalize_property_name()
          "hk" → "The Peninsula Hong Kong"
        │
        ▼ normalize_incident_type()
        │
        ▼ normalize_severity()
        │
        ▼ normalize_status()
        │
        ▼ normalize_department()
          "fb" → "Food & Beverage"
        │
        ▼ normalize_category()
        │
        ▼ get_entity_hints()
          "- Use property_name = 'The Peninsula Hong Kong' in WHERE clause"
          "- Use department_name = 'Food & Beverage' in WHERE clause"
        │
        ▼ get_time_expression_hint()  (if time expression present)
          Injects exact SQL date filter snippet
```

Alias dictionaries cover: 5 hotel properties, 4 severity levels, 3 status values, ~30 departments, ~40 categories, ~30 incident types.

---

## Display Type Selection

The visualization recommendation follows a 4-level priority cascade:

```
P1 (highest): User-provided display.type in request payload
      │
      ▼ (if absent)
P2: Exact match in 60-question demo map (QUERY_DISPLAY_TYPE_MAP)
      │
      ▼ (if no match)
P3: Regex pattern matching on question text
      metric: "how many", "what is the total/average"
      pie:    "breakdown by severity/status", "distribution by"
      bar:    "count by department/category", "which department"
      line:   "per day/week/month", "trend", "over time"
      table:  "show me all", "top N", "pending incidents"
      │
      ▼ (if no match, and query was executed)
P4: SQL structural analysis
      metric: 1 row × 1 col (or 1 row with aggregation)
      line:   GROUP BY + date function + aggregation
      pie:    2 cols + ≤10 rows + GROUP BY + aggregation
      bar:    GROUP BY + aggregation + ≤50 rows
      table:  default fallback
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serve web GUI (static/index.html) |
| `GET` | `/health` | Health check + rate limiter stats |
| `POST` | `/nlq/execute` | Main NLQ → SQL → execute pipeline |
| `GET` | `/nlq/suggestions?target=` | Schema-based query suggestions |
| `GET` | `/nlq/schema?target=` | Schema summary for a target |
| `GET` | `/logs?limit=` | Last N request/response audit logs |
| `GET` | `/rate-limit/stats` | Token bucket statistics |
| `GET` | `/static/*` | Static assets for web GUI |

---

## Latency Breakdown

The response includes a `trace.latency_ms` object showing per-stage timing:

```json
{
  "prompt_ms":      40,    // Step 4: schema load + prompt build
  "model_ms":      4200,   // Step 5: LLM inference (or 0 if cache hit)
  "postprocess_ms": 8,     // Steps 5.5 + 6: fixers + validation
  "athena_ms":     1800,   // Step 7: Athena execution (or 0 if dry_run)
  "total_ms":      6100
}
```

---

## Configuration & Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_REGION` | `ap-east-1` | AWS region for Athena + Glue |
| `AWS_ACCESS_KEY_ID` | — | AWS credentials (or IAM role) |
| `AWS_SECRET_ACCESS_KEY` | — | AWS credentials (or IAM role) |
| `USE_QUANTIZATION` | `false` | Enable 4-bit NF4 quantization (~4-5GB VRAM vs ~13GB) |

AWS credentials are resolved via boto3's standard chain: env vars → `~/.aws/credentials` → IAM role.

---

## Key Architectural Trade-offs

| Decision | Trade-off |
|----------|-----------|
| Single `incident_combine` table | Simplifies SQL (no JOINs needed); all dimensions are denormalized columns |
| `num_beams=4` beam search | Higher quality SQL at cost of ~2–4× inference time vs greedy decoding |
| In-process LLM (no external API) | Eliminates external latency/dependency; requires GPU-enabled host |
| FIFO eviction on SQL cache | Simple; can evict hot entries under churn — an LRU variant would be more optimal |
| `inject_property_filter` as safety net | Dual defense for access control; adds a second pass over generated SQL on every request |
| `dry_run=true` default in models | Safe default prevents accidental Athena charges during integration testing |
