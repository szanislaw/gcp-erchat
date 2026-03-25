# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A production FastAPI service that converts natural language questions into AWS Athena SQL queries using a locally-loaded `defog/sqlcoder-7b-2` model. Results are returned with display type hints (table/bar/pie/line/metric) for frontend rendering.

## Running the Application

```bash
# Start FastAPI (port 8000)
./start.sh

# Stop all services
./stop.sh

# Manual start
uvicorn app.main:app --host 0.0.0.0 --port 8000
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
python test/eval_corpus.py              # 38-question NL-to-SQL evaluation corpus (100% pass rate)
python test/test_target_questions.py    # Target-specific NLQ tests
python test/test_50_questions.py        # 50-question expanded NLQ test suite (48/50 pass, 96% — A–E perfect, F04/F05 CTE trend failures known)
```

## Environment Setup

Copy `.env.example` to `.env` and configure:

```
# Required: AWS credentials for Athena
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=ap-east-1

# Model: true → 4-bit quantization (~4-5GB VRAM); false → float16 (~13GB VRAM, faster, default for L4 24GB)
USE_QUANTIZATION=false

# Optional overrides (defaults: 0.0.0.0:8000)
API_HOST=0.0.0.0
API_PORT=8000
```

Alternatively, use AWS CLI configuration (`aws configure`). The app uses boto3's default credential chain.

Install dependencies: `pip install -r requirements.txt`

The production server uses a conda environment: `~/miniconda3/envs/venv1`. To run scripts on the remote server, use `~/miniconda3/envs/venv1/bin/python3` explicitly (no `venv/bin/activate`).

## Architecture

### Request Pipeline (`app/main.py`)

The `/nlq/execute` endpoint processes requests through a strict sequential pipeline:

1. **Input validation** (`app/input_validator.py`) — XSS/injection sanitization
2. **Rate limiting** (`app/rate_limiter.py`) — token bucket, 2 req/s, burst 10
3. **Athena target resolution** — maps request to `ATHENA_TARGETS` config (`app/athena_config.py`)
4. **Prompt construction** (`app/prompt.py`) — loads schema from AWS Glue via `app/schema_loader.py` (cached in-memory), normalizes query (`app/query_normalizer.py`), injects property UUID access restrictions and ENUM column distinct values
   - `get_time_expression_hint()` — detects calendar expressions ('this week', 'last month', etc.) and injects exact SQL filter snippets as entity hints, overriding the model's tendency to use rolling windows
5. **Model inference** (`app/sqlcoder.py`) — runs sqlcoder-7b-2 in ThreadPoolExecutor (non-blocking); has LRU cache (500 entries)
6. **SQL post-processing** — applied in order, split across two locations:
   - *Inside `extract_sql()` in `app/sqlcoder.py`:*
   - `fix_date_part()` — converts `date_part()`/`EXTRACT()` on `snapshotdate` to Athena-native functions
   - `fix_date_comparisons()` — wraps bare `snapshotdate` references in `date_parse()` (also handles reverse: `<expr> op snapshotdate`)
   - `fix_bigint_date_comparisons()` — rewrites date predicates on BIGINT timestamp columns to use `snapshotdate`
   - `fix_interval_syntax()` — converts PostgreSQL `INTERVAL` to `date_add()`
   - `fix_group_by_aliases()` — replaces SELECT aliases in `GROUP BY` with ordinal positions (Athena rejects aliases)
   - *In `app/main.py` after inference:*
   - `fix_table_names()` — corrects hallucinated table name variants; falls back to replacing any unknown `FROM/JOIN` table with the primary allowed table
   - `fix_float_cast()` — replaces `CAST(... AS FLOAT)` with `CAST(... AS DOUBLE)` (Athena does not support FLOAT type)
   - `fix_invalid_extract_from_table()` — fixes hallucinated `EXTRACT(YEAR/WEEK FROM table_name)` → `date_trunc('week', current_date)`
   - `fix_impossible_this_period_filter()` — removes self-contradicting `>= date_trunc('week') AND < date_trunc('week')` upper bounds
   - `fix_last_week_filter()` — when question says "last week", converts rolling `-7 day` window to calendar Mon–Sun boundary
   - `fix_property_column()` — rewrites `property_name IN (uuid)` → `property IN (uuid)` when model uses wrong column
   - `inject_property_filter()` — injects mandatory `WHERE property IN (...)` if model drops it entirely
7. **SQL validation** (`app/security.py`) — blocks forbidden operations (DROP/DELETE/etc.), validates table access
8. **Athena execution** (`app/athena_client.py`) — optional, skipped when `dry_run=true`
9. **Column formatting** (`app/column_formatter.py`) — remaps raw DB column names to human-readable display names (e.g. `category_name` → `Category`, `snapshotdate` → `Date`)
10. **Display type detection** (`app/display_hint.py`) — priority: user-specified → question pattern matching → SQL structure analysis
11. **Chart formatting** (`app/chart_formatter.py`) — reshapes data for bar/pie/line/metric displays

### Key Data Flow Constraints

- CTE queries (`WITH prev AS (...), curr AS (...) SELECT ...`) are fully supported: `extract_sql()` detects the `WITH` keyword and returns the full CTE; `validate_sql()` excludes CTE alias names from unknown-table checks.
- Calendar expressions ('this week', 'this month') use `date_trunc()` boundary; rolling windows ('last 7 days', 'last 30 days') use `date_add()`. These are NOT interchangeable — "last week" means Mon–Sun, not -7 days.
- `snapshotdate` is a `VARCHAR` column — SQL must use `date_parse(snapshotdate, '%Y-%m-%d')` for any date comparisons. The post-processor in `sqlcoder.py` automatically fixes this.
- `created_date`, `incident_time`, `completed_date`, `cancelled_date` are `BIGINT` timestamps — **never** use these in WHERE clauses for date filtering, only for `ORDER BY`.
- All queries are capped at `LIMIT 100`.
- The model is loaded once at startup (`lifespan` context manager) and shared across requests behind a `threading.Lock`.

### Athena Targets (`app/athena_config.py`)

Two configured targets:
- `peninsula_incident` — database `peninsula-incident2`, table `incident_combine`
- `londoner_granded` — database `londoner_granded`, table `ldco_testing`

Adding a new target: add entries to both `ATHENA_TARGETS` and `ENUM_COLUMNS` dicts; schema is auto-fetched from AWS Glue on first request and cached in-memory. `ENUM_COLUMNS` defines which categorical columns should have their distinct values fetched and injected into the model prompt to improve SQL generation accuracy.

### Property-Based Access Control

Authentication is handled externally. The API receives pre-authorized `property_uuid` values in the request context. `app/prompt.py` injects a mandatory `WHERE property_col IN (...)` restriction into the LLM prompt. The property UUID column name is auto-detected via `find_property_uuid_column()` from the Glue schema (tries `property_uuid`, then columns containing both "property" and "uuid", then `property`).

**Critical schema gotcha:** `peninsula_incident` has two similarly-named columns:
- `property` — **partition key**, holds UUID values used for access control filtering
- `property_name` — regular VARCHAR column, holds hotel display names (e.g. `'The Peninsula Manila'`)

The model frequently hallucinates `WHERE property_name IN ('uuid')` instead of `WHERE property IN ('uuid')`, returning 0 rows. `fix_property_column()` and `inject_property_filter()` in `app/sqlcoder.py` correct this in post-processing.

### Display Type Logic (`app/display_hint.py`)

- `QUERY_DISPLAY_TYPE_MAP` — hardcoded mapping for 60 known demo questions (checked first)
- Pattern matching — regex rules on the NL question
- SQL analysis fallback — inspects GROUP BY, aggregation functions, row/column counts

### Self-Correction Loop

On Athena execution failure (`RuntimeError`), the pipeline automatically retries up to **2 times**: generates a correction prompt containing the failed SQL + Athena error message, re-runs model inference, re-validates, and retries. `correction_attempts` is reported in the response trace.

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
  "text": "How many high severity incidents?",
  "context": {
    "property_uuid": "uuid1,uuid2",
    "user_uuid": "...",
    "language": "en"
  },
  "sql": { "dialect": "athena", "tables": [] },
  "execution": { "dry_run": false, "max_rows": 100, "athena_target": "peninsula_incident" },
  "model": { "max_tokens": 256 },
  "display": { "type": "metric" },
  "trace": { "request_id": "optional-id", "source": "manual" }
}
```

See `test/sample_payloads.json` and `test/clis/curl-request-template.txt` for curl examples.

## Remote Server

Production runs at `http://34.126.131.59:8000`. SSH access: `ssh shawn.yap@34.126.131.59`, code at `~/gcp-erchat`. Deploy by pulling latest git and restarting with `./stop.sh && ./start.sh`. Conda env: `~/miniconda3/envs/venv1`.
