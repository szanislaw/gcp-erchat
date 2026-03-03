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

Logs are written to `logs/api.log`.

## Running Tests

```bash
python test/test_questions.py       # NLQ query test suite
python test/test_suggestions.py     # Query suggestion tests
python test/test_sqlcoder_date_fixes.py  # SQL post-processing unit tests
python test/stress_test.py          # Load/stress testing
python test/debug_query.py          # Debug individual queries
python test/health_check.py         # Health check verification
python test/eval_corpus.py          # 38-question NL-to-SQL evaluation corpus (100% pass rate)
```

## Environment Setup

Copy `.env.example` to `.env` and configure AWS credentials:

```
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=ap-east-1
```

Alternatively, use AWS CLI configuration (`aws configure`). The app uses boto3's default credential chain.

Install dependencies: `pip install -r requirements.txt`

## Architecture

### Request Pipeline (`app/main.py`)

The `/nlq/execute` endpoint processes requests through a strict sequential pipeline:

1. **Input validation** (`app/input_validator.py`) — XSS/injection sanitization
2. **Rate limiting** (`app/rate_limiter.py`) — token bucket, 2 req/s, burst 10
3. **Athena target resolution** — maps request to `ATHENA_TARGETS` config (`app/athena_config.py`)
4. **Prompt construction** (`app/prompt.py`) — loads schema from AWS Glue, normalizes query (`app/query_normalizer.py`), injects property UUID access restrictions
5. **Model inference** (`app/sqlcoder.py`) — runs sqlcoder-7b-2 in ThreadPoolExecutor (non-blocking); has LRU cache (500 entries)
6. **SQL post-processing** — `fix_table_names()` corrects hallucinated table variants, then `fix_date_comparisons()`, `fix_bigint_date_comparisons()`, and `fix_interval_syntax()` fix Athena type mismatches and convert PostgreSQL `INTERVAL` syntax to `date_add()`
7. **SQL validation** (`app/security.py`) — blocks forbidden operations (DROP/DELETE/etc.), validates table access
8. **Athena execution** (`app/athena_client.py`) — optional, skipped when `dry_run=true`
9. **Display type detection** (`app/display_hint.py`) — priority: user-specified → question pattern matching → SQL structure analysis
10. **Chart formatting** (`app/chart_formatter.py`) — reshapes data for bar/pie/line/metric displays

### Key Data Flow Constraints

- `snapshotdate` is a `VARCHAR` column — SQL must use `date_parse(snapshotdate, '%Y-%m-%d')` for any date comparisons. The post-processor in `sqlcoder.py` automatically fixes this.
- `created_date`, `incident_time`, `completed_date`, `cancelled_date` are `BIGINT` timestamps — **never** use these in WHERE clauses for date filtering, only for `ORDER BY`.
- All queries are capped at `LIMIT 100`.
- The model is loaded once at startup (`lifespan` context manager) and shared across requests behind a `threading.Lock`.

### Athena Targets (`app/athena_config.py`)

Two configured targets:
- `peninsula_incident` — database `peninsula-incident2`, table `incident_combine`
- `londoner_granded` — database `londoner_granded`, table `ldco_testing`

Adding a new target: add an entry to `ATHENA_TARGETS` dict; schema is auto-fetched from AWS Glue on first request and cached in-memory.

### Property-Based Access Control

Authentication is handled externally. The API receives pre-authorized `property_uuid` values in the request context. `app/prompt.py` injects a mandatory `WHERE property_col IN (...)` restriction into the LLM prompt. The property UUID column name is auto-detected from the Glue schema (tries `property_uuid`, then columns containing both "property" and "uuid", then `property`).

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
  "execution": { "dry_run": false, "max_rows": 100 },
  "model": { "max_tokens": 256 },
  "display": { "type": "metric" },
  "trace": { "request_id": "optional-id", "source": "manual" }
}
```

See `test/sample_payloads.json` and `test/clis/curl-request-template.txt` for curl examples.
