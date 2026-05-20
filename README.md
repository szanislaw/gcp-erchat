# gcp-erchat — NLQ → Redshift SQL API

Production FastAPI service that converts natural language questions into Amazon Redshift SQL queries using `defog/sqlcoder-7b-2`. Returns structured results with automatic display type hints (metric / bar / line / table) for frontend chart rendering.

**Production:** `http://34.126.131.59:8000`  
**Eval:** 96% pass rate (48/50) on 50-question test suite

---

## Features

- **Dual-domain NLQ**: maintenance orders and incident/recovery records
- **Hotel filtering**: natural language property names resolved to UUIDs via fuzzy matching
- **Chart-aware SQL prompts**: bar/line chart structure hints injected into LLM prompt to improve column shape and ordering
- **Display type routing**: exact-match map → regex patterns → SQL structure analysis
- **Self-correction loop**: failed SQL retried up to 2× with Redshift error feedback
- **Property-based access control**: `WHERE property IN (...)` enforced at prompt level
- **Rate limiting**: token bucket, 2 req/s, burst 10
- **LRU query cache**: 500 entries (MD5-keyed)

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with Redshift credentials and AWS keys

# Start server (port 8000)
./start.sh

# Stop
./stop.sh
```

Logs: `logs/api.log`  
Swagger UI: `http://localhost:8000/docs`  
GM Dashboard: `http://localhost:8000/dashboard`

### Docker

```bash
# Configure runtime secrets locally; this file is not copied into the image
cp .env.example .env

# Build and run
docker compose up --build

# Or run an already-built image
docker run --rm --env-file .env -p 8000:8000 gcp-erchat-api:latest
```

If the model needs GPU acceleration, run Docker with NVIDIA container runtime support and pass GPU access, for example `docker run --gpus all ...`.

---

## Environment Variables

```bash
# Redshift (password auth)
REDSHIFT_HOST=your-cluster.region.redshift-serverless.amazonaws.com
REDSHIFT_PORT=5439
REDSHIFT_DBNAME=dev
REDSHIFT_USER=admin
REDSHIFT_PASSWORD=yourpassword

# AWS (for IAM operations)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=ap-east-1

# Incident schema (default: public)
REDSHIFT_INCIDENT_SCHEMA=public

# Model quantization: true → 4-bit ~4GB VRAM, false → float16 ~13GB VRAM
USE_QUANTIZATION=false
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/nlq/execute` | NLQ → SQL + optional Redshift execution |
| GET | `/nlq/suggestions` | Suggested queries for a target |
| GET | `/nlq/schema` | Schema summary for a target |
| GET | `/health` | Health check + rate limiter stats |
| GET | `/logs` | Last N request/response logs |
| GET | `/dashboard` | GM analytics dashboard |

---

## Request Payload

```json
{
  "text": "How many open high priority maintenance orders?",
  "context": {
    "property_uuid": "uuid1,uuid2",
    "language": "en"
  },
  "sql": { "dialect": "redshift", "tables": [] },
  "execution": {
    "dry_run": false,
    "max_rows": 100,
    "redshift_target": "default"
  },
  "model": { "max_tokens": 256 },
  "display": { "type": "metric" },
  "trace": { "request_id": "optional-id", "source": "manual" }
}
```

**`redshift_target`**: `"default"` (maintenance) or `"incident"` (incident/recovery)  
**`display.type`**: optional override — `metric`, `bar`, `line`, `table`, `pie`  
**`dry_run: true`**: returns SQL without executing on Redshift

---

## Response

```json
{
  "success": true,
  "sql": { "query": "SELECT COUNT(*) FROM maintenance_order WHERE ..." },
  "execution": {
    "executed": true,
    "row_count": 1,
    "data": { "columns": ["count"], "rows": [{"count": 42}] }
  },
  "display": { "type": "metric" },
  "trace": {
    "request_id": "...",
    "model_latency_ms": 2100,
    "total_latency_ms": 2350,
    "correction_attempts": 0
  }
}
```

---

## Architecture

```
POST /nlq/execute
  │
  ├─ Input validation (XSS / injection sanitization)
  ├─ Rate limiting (token bucket)
  ├─ Target resolution → REDSHIFT_TARGETS config
  ├─ Prompt construction
  │   ├─ Schema DDL from information_schema (cached)
  │   ├─ ENUM column values (cached)
  │   ├─ Hotel name fuzzy matching → property UUID injection
  │   ├─ Calendar expression hints (this week / last month)
  │   └─ Chart structure hints (bar: 2-col + ORDER BY DESC, line: DATE_TRUNC + ORDER BY ASC)
  ├─ SQLCoder-7b-2 inference (ThreadPoolExecutor, LRU cached)
  ├─ SQL post-processing (date fixers, table name corrections, property filter injection)
  ├─ SQL validation (blocklist: DROP/DELETE/UPDATE/INSERT/ALTER)
  ├─ Redshift execution (skipped if dry_run=true)
  │   └─ Self-correction loop on failure (up to 2 retries)
  ├─ Column formatting (raw DB names → human-readable display names)
  └─ Display type detection → chart formatting
```

### SQL Post-Processing Pipeline

Applied in two stages:

**Inside `extract_sql()` (`app/sqlcoder.py`):**
- `fix_date_parse_to_to_date()` — Athena → Redshift date syntax
- `fix_date_add_to_dateadd()` — Athena → Redshift date arithmetic
- `fix_date_part()` — wraps VARCHAR date columns in `TO_DATE()`
- `fix_date_comparisons()` — ensures date predicates use correct casting
- `fix_bigint_date_comparisons()` — rewrites BIGINT timestamp predicates to use `snapshotdate`

**In `app/main.py` after inference:**
- `fix_snapshotdate()` — replaces hallucinated `snapshotdate` → `created_date` (incident schema)
- `fix_table_names()` — corrects hallucinated table name variants
- `fix_spurious_department_join()` — removes invalid department joins
- `fix_main_table_fk_names()` — integer FK → proper JOIN
- `fix_department_column()` — `d.department` → `d.department_name`
- `fix_invalid_extract_from_table()` — fixes hallucinated `EXTRACT(YEAR FROM table_name)`
- `fix_impossible_this_period_filter()` — removes self-contradicting date bounds
- `fix_last_week_filter()` — rolling -7 days → calendar Mon–Sun boundary
- `fix_property_column()` — `property_name IN (uuid)` → `property IN (uuid)`
- `inject_property_filter()` — adds mandatory property filter if model drops it

---

## Redshift Targets

Configured in `app/redshift_config.py`:

| Target | Schema | Primary Tables |
|--------|--------|----------------|
| `default` | `nxg_107747471_q2sj` | `maintenance_order`, `master_maintenance_status`, `master_job_priority`, `department`, `property_location` |
| `incident` | `public` | `mv_recovery_all` |

To add a new target, add entries to `REDSHIFT_TARGETS` and `ENUM_COLUMNS`. Schema is auto-fetched from `information_schema` on first request and cached in-memory.

---

## Display Type Logic

Priority order:
1. User-specified `display.type` in request
2. `QUERY_DISPLAY_TYPE_MAP` — exact-match dictionary (64 incident + 30 maintenance known questions)
3. Regex pattern matching on NL question
4. SQL structure analysis (GROUP BY, aggregation, row/column counts)

| Type | When |
|------|------|
| `metric` | Single value (COUNT/SUM/AVG, 1 row 1 col) |
| `bar` | GROUP BY categorical dimension + aggregation |
| `line` | GROUP BY DATE_TRUNC + aggregation (time series) |
| `table` | Raw records or >50 rows |
| `pie` | Categorical with ≤10 rows |

---

## Running Tests

```bash
python test/test_questions.py                         # NLQ query suite
python test/test_50_questions.py                      # 50-question expanded suite
python3 test/eval_maintenance.py                      # 39-question maintenance eval (94%, 37/39)
python3 test/eval_maintenance.py --dry-run            # SQL-only, no Redshift (fast)
python3 test/eval_maintenance.py --category date_filter
python3 test/eval_maintenance.py --id S02 --verbose
python test/test_display_detection.py                 # Display type detection
python test/test_sqlcoder_date_fixes.py               # SQL post-processing unit tests
python test/health_check.py                           # Health check

# Remote
API_URL=http://34.126.131.59:8000 python3 test/eval_maintenance.py --dry-run
```

---

## Deployment

```bash
# Deploy to production
ssh shawn.yap@34.126.131.59 "cd ~/gcp-erchat && git pull && ./stop.sh && ./start.sh"
```

Production conda env: `~/miniconda3/envs/venv1`

---

## Key Constraints

- **`maintenance_order` has NO `department_uuid` column** — any generated `JOIN department d ON m.department_uuid = d.department_uuid` will fail at runtime. Department-breakdown queries are unanswerable with this schema.
- `created_date`, `completed_date`, `cancelled_date`, `assigned_date` are TIMESTAMP columns — no casting needed.
- Calendar expressions (`this week`, `this month`) use `DATE_TRUNC()` boundaries; rolling windows (`last 7 days`) use `DATEADD()`. These are not interchangeable.
- All queries are capped at `LIMIT 100`.
- Model is loaded once at startup and shared behind a `threading.Lock`.
