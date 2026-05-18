# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A production FastAPI service that converts natural language questions into Amazon Redshift SQL queries using a locally-loaded `defog/sqlcoder-7b-2` model. Results are returned with display type hints (table/bar/pie/line/metric) for frontend rendering.

## Running the Application

```bash
# Start FastAPI (port 8000)
./start.sh

# Stop all services
./stop.sh

# Manual start
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Deploy latest from git (production)
ssh shawn.yap@34.126.131.59 "cd ~/gcp-erchat && git pull && ./stop.sh && ./start.sh"
```

Logs are written to `logs/api.log`. Swagger UI available at `http://localhost:8000/docs`.

## Running Tests

```bash
python test/test_questions.py           # NLQ query test suite
python test/test_suggestions.py         # Query suggestion tests
python test/test_sqlcoder_date_fixes.py # SQL post-processing unit tests
python test/test_display_detection.py   # Display type detection tests
python test/test_display_types.py       # Display type integration tests
python test/test_column_formatting.py   # Column name formatting tests
python test/stress_test.py              # Load/stress testing
python test/debug_query.py              # Debug individual queries
python test/health_check.py             # Health check verification
python test/eval_corpus.py              # 38-question NL-to-SQL evaluation corpus
python test/test_target_questions.py    # Target-specific NLQ tests
python test/test_50_questions.py        # 50-question expanded NLQ test suite
python3 test/eval_maintenance.py        # 39-question maintenance eval (37/39 pass, 94%) — primary eval suite
python3 test/eval_maintenance.py --dry-run              # SQL-only, no Redshift execution (fast)
python3 test/eval_maintenance.py --category date_filter # Run single category
python3 test/eval_maintenance.py --id S02 --verbose     # Run single question with SQL output
```

To test against the remote server: `API_URL=http://34.126.131.59:8000 python3 test/eval_maintenance.py --dry-run`

For offline SQL generation (skips Redshift execution), add `"dry_run": true` to the execution payload, or pass `--dry-run` to test scripts that support it.

## Environment Setup

Copy `.env.example` to `.env` and configure:

```
# Redshift connection (password auth)
REDSHIFT_HOST=your-workgroup.region.redshift-serverless.amazonaws.com
REDSHIFT_PORT=5439
REDSHIFT_DBNAME=dev
REDSHIFT_USER=your_username
REDSHIFT_PASSWORD=your_password
REDSHIFT_SCHEMA=your_schema_name

# Model: true → 4-bit quantization (~4-5GB VRAM); false → float16 (~13GB VRAM, faster, default for L4 24GB)
USE_QUANTIZATION=false
```

Install dependencies: `pip install -r requirements.txt`

The production server uses a conda environment: `~/miniconda3/envs/venv1`. To run scripts on the remote server, use `~/miniconda3/envs/venv1/bin/python3` explicitly (no `venv/bin/activate`).

## Architecture

### Request Pipeline (`app/main.py`)

The `/nlq/execute` endpoint processes requests through a strict sequential pipeline:

1. **Input validation** (`app/input_validator.py`) — XSS/injection sanitization
2. **Rate limiting** (`app/rate_limiter.py`) — token bucket, 2 req/s, burst 10
3. **Redshift target resolution** — maps request to `REDSHIFT_TARGETS` config (`app/redshift_config.py`)
4. **Prompt construction** (`app/prompt.py`) — loads schema from Redshift `information_schema` via `app/schema_loader.py` (cached in-memory), normalizes query (`app/query_normalizer.py`), injects property UUID access restrictions and ENUM column distinct values
   - `get_time_expression_hint()` — detects calendar expressions ('this week', 'last month', etc.) and injects exact SQL filter snippets as entity hints, overriding the model's tendency to use rolling windows
5. **Model inference** (`app/sqlcoder.py`) — runs sqlcoder-7b-2 in ThreadPoolExecutor (non-blocking); has LRU cache (500 entries)
6. **SQL post-processing** — applied in order, split across two locations:
   - *Inside `extract_sql()` in `app/sqlcoder.py`:*
   - `fix_date_parse_to_to_date()` — safety net: converts Athena-style `date_parse()` to Redshift `TO_DATE()`
   - `fix_date_add_to_dateadd()` — safety net: converts Athena-style `date_add()` to Redshift `DATEADD()`
   - `fix_date_part()` — wraps `date_part()`/`EXTRACT()` on `snapshotdate` (VARCHAR) with `TO_DATE()`
   - `fix_date_comparisons()` — wraps bare `snapshotdate` references with `TO_DATE()` for date comparisons
   - `fix_bigint_date_comparisons()` — rewrites date predicates on BIGINT timestamp columns to use `snapshotdate`
   - *In `app/main.py` after inference:*
   - `fix_snapshotdate()` — replaces hallucinated `snapshotdate` column → `created_date`
   - `fix_table_names()` — corrects hallucinated table name variants; negative lookbehind prevents clobbering column refs like `department_name`
   - `fix_spurious_department_join()` — removes spurious `JOIN department` when question doesn't ask about department
   - `fix_main_table_fk_names()` — converts raw integer FK filters (`WHERE status = 1`) → proper JOIN; skips if JOIN already present
   - `fix_department_column()` — rewrites `d.department` → `d.department_name` (wrong column alias)
   - `fix_invalid_extract_from_table()` — fixes hallucinated `EXTRACT(YEAR/WEEK FROM table_name)` → `DATE_TRUNC('week', CURRENT_DATE)`
   - `fix_impossible_this_period_filter()` — removes self-contradicting `>= DATE_TRUNC('week') AND < DATE_TRUNC('week')` upper bounds
   - `fix_last_week_filter()` — when question says "last week", converts rolling `-7 day` window to calendar Mon–Sun boundary
   - `fix_property_column()` — rewrites `property_name IN (uuid)` → `property IN (uuid)` when model uses wrong column
   - `inject_property_filter()` — injects mandatory `WHERE property IN (...)` if model drops it entirely
7. **SQL validation** (`app/security.py`) — blocks forbidden operations (DROP/DELETE/etc.), validates table access
8. **Redshift execution** (`app/redshift_client.py`) — optional, skipped when `dry_run=true`; opens IAM-authenticated connection, sets `search_path`, executes query, closes connection
9. **Column formatting** (`app/column_formatter.py`) — remaps raw DB column names to human-readable display names (e.g. `category_name` → `Category`, `snapshotdate` → `Date`)
10. **Display type detection** (`app/display_hint.py`) — priority: user-specified → question pattern matching → SQL structure analysis
11. **Chart formatting** (`app/chart_formatter.py`) — reshapes data for bar/pie/line/metric displays

### Key Data Flow Constraints

- CTE queries (`WITH prev AS (...), curr AS (...) SELECT ...`) are fully supported: `extract_sql()` detects the `WITH` keyword and returns the full CTE; `validate_sql()` excludes CTE alias names from unknown-table checks.
- Calendar expressions ('this week', 'this month') use `DATE_TRUNC()` boundary; rolling windows ('last 7 days', 'last 30 days') use `DATEADD()`. These are NOT interchangeable — "last week" means Mon–Sun, not -7 days.
- `created_date`, `completed_date`, `cancelled_date`, `assigned_date` are TIMESTAMP columns — no casting needed. Use directly in WHERE clauses.
- **CRITICAL — `maintenance_order` has NO `department_uuid` column.** The `department` table is in the schema but there is no FK linking it to `maintenance_order`. Any query generating `JOIN department d ON m.department_uuid = d.department_uuid` will fail at runtime with `column m.department_uuid does not exist`. Department-breakdown queries are currently unanswerable with this schema.
- All queries are capped at `LIMIT 100`.
- The model is loaded once at startup (`lifespan` context manager) and shared across requests behind a `threading.Lock`.

### Redshift Targets (`app/redshift_config.py`)

One configured target:
- `default` — schema `nxg_107747471_q2sj`, tables: `maintenance_order`, `master_maintenance_status`, `master_job_priority`, `department`, `property_location`

Adding a new target: add entries to both `REDSHIFT_TARGETS` and `ENUM_COLUMNS` dicts; schema is auto-fetched from `information_schema.columns` on first request and cached in-memory. `ENUM_COLUMNS` defines which categorical columns should have their distinct values fetched and injected into the model prompt to improve SQL generation accuracy.

### Property-Based Access Control

Authentication is handled externally. The API receives pre-authorized `property_uuid` values in the request context. `app/prompt.py` injects a mandatory `WHERE property_col IN (...)` restriction into the LLM prompt. The property UUID column name is auto-detected via `find_property_uuid_column()` from the schema (tries `property_uuid`, then columns containing both "property" and "uuid", then `property`).

The `maintenance_order` schema uses `property_uuid` (VARCHAR) for access control. `fix_property_column()` and `inject_property_filter()` in `app/sqlcoder.py` ensure the filter is always present and uses the correct column.

### Display Type Logic (`app/display_hint.py`)

- `QUERY_DISPLAY_TYPE_MAP` — hardcoded mapping for 60 known demo questions (checked first)
- Pattern matching — regex rules on the NL question
- SQL analysis fallback — inspects GROUP BY, aggregation functions, row/column counts

### Self-Correction Loop

On Redshift execution failure (`RuntimeError`), the pipeline automatically retries up to **2 times**: generates a correction prompt containing the failed SQL + Redshift error message, re-runs model inference, re-validates, and retries. `correction_attempts` is reported in the response trace.

### Static Web UI

`static/index.html` is served at `/` by the FastAPI app.

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/nlq/execute` | POST | Main NLQ to SQL conversion + optional execution |
| `/nlq/suggestions` | GET | Suggested queries for a target |
| `/nlq/schema` | GET | Schema summary for a target |
| `/health` | GET | Health check + rate limiter stats |
| `/logs` | GET | Last N request/response logs |
| `/rate-limit/stats` | GET | Rate limiter statistics |

## Request Payload Structure

```json
{
  "text": "How many open high priority maintenance orders?",
  "context": {
    "property_uuid": "uuid1,uuid2",
    "language": "en"
  },
  "sql": { "dialect": "redshift", "tables": [] },
  "execution": { "dry_run": false, "max_rows": 100, "redshift_target": "default" },
  "model": { "max_tokens": 256 },
  "display": { "type": "metric" },
  "trace": { "request_id": "optional-id", "source": "manual" }
}
```

See `test/sample_payloads.json` and `test/clis/curl-request-template.txt` for curl examples.

## Remote Server

Production runs at `http://34.126.131.59:8000`. SSH access: `ssh shawn.yap@34.126.131.59`, code at `~/gcp-erchat`. Deploy by pulling latest git and restarting with `./stop.sh && ./start.sh`. Conda env: `~/miniconda3/envs/venv1`.
