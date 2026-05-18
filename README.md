# Natural Language Query to SQL API

Production-ready FastAPI service that converts natural language questions into Athena SQL queries with comprehensive property-based access control, intelligent SQL post-processing, rate limiting, and automated display type recommendations.

## ✨ Key Features

- 🤖 **AI-Powered SQL Generation**: Uses `defog/sqlcoder-7b-2` — state-of-the-art NL-to-SQL model (outperforms GPT-4 on SQL benchmarks)
- 🛡️ **Property-Based Access Control**: Pre-authorized property UUIDs drive data access
- 🔧 **Automatic SQL Fixing**: Post-processes generated SQL to fix date comparisons and type mismatches
- 📊 **Smart Display Hints**: Automatically recommends chart types (line, bar, pie, metric, table)
- 🚦 **Rate Limiting**: Token bucket algorithm with request queuing (2 req/s, burst 10)
- 🔒 **Input Validation**: XSS and SQL injection protection with automatic sanitization
- 💾 **Query Caching**: LRU cache for frequently used queries (500 entry capacity)
- 📝 **Request Logging**: Comprehensive JSON logging of all API requests
- 🌐 **Multi-language Support**: English, Chinese, Malay, Tamil
- ⚡ **Async Architecture**: Non-blocking with thread pool for ML inference

## 🚀 Quick Start

### Option 1: Automated Startup (Recommended)

```bash
# Start API
./start.sh

# Stop API
./stop.sh
```

### Option 2: Manual Startup

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Services:**
- API: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`

## 🌐 Remote Server Access

If the application is hosted on a remote server (e.g., public IP: `128.106.57.220`), clients can access the API endpoint as follows:

### API Endpoint URL
```
http://128.106.57.220:8000
```

### Sending Queries from a Client

**Using cURL:**
```bash
curl -X POST http://128.106.57.220:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "How many high severity incidents in the last 7 days?",
    "context": {
      "language": "en",
      "property_uuid": "c7254cc9-9145-4602-b44b-0c1cff335f83,2b618b46-6b80-481b-b1e3-5aec1647b926",
      "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6",
      "user_role": null
    },
    "sql": {"dialect": "redshift", "tables": []},
    "execution": {"dry_run": false, "max_rows": 100, "redshift_target": null},
    "model": {"max_tokens": 512},
    "trace": {"source": "socket"}
  }'
```

**Using Python:**
```python
import requests
import json

# API endpoint
url = "http://128.106.57.220:8000/nlq/execute"

# Request payload
payload = {
    "text": "How many high severity incidents in the last 7 days?",
    "context": {
        "language": "en",
        "property_uuid": "c7254cc9-9145-4602-b44b-0c1cff335f83,2b618b46-6b80-481b-b1e3-5aec1647b926",
        "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6",
        "user_role": None
    },
    "sql": {"dialect": "redshift", "tables": []},
    "execution": {"dry_run": False, "max_rows": 100, "redshift_target": None},
    "model": {"max_tokens": 512},
    "trace": {"source": "socket"}
}

# Send request
response = requests.post(url, json=payload)

# Process response
if response.status_code == 200:
    result = response.json()
    print("SQL Query:", result['sql']['query'])
    if result['execution']['executed']:
        print("Rows returned:", result['execution']['row_count'])
        print("Data:", json.dumps(result['execution']['data'], indent=2))
else:
    print(f"Error: {response.status_code}")
    print(response.text)
```

**Using JavaScript/Node.js:**
```javascript
const axios = require('axios');

const url = 'http://128.106.57.220:8000/nlq/execute';

const payload = {
  text: 'How many high severity incidents in the last 7 days?',
  context: {
    language: 'en',
    property_uuid: 'c7254cc9-9145-4602-b44b-0c1cff335f83,2b618b46-6b80-481b-b1e3-5aec1647b926',
    account_uuid: 'fccb8d60-de9c-4bf8-abd8-fae523c732c6',
    user_role: null
  },
  sql: { dialect: "redshift", tables: [] },
  execution: { dry_run: false, max_rows: 100, athena_target: null },
  model: { max_tokens: 512 },
  trace: { source: 'socket' }
};

axios.post(url, payload)
  .then(response => {
    console.log('SQL Query:', response.data.sql.query);
    if (response.data.execution.executed) {
      console.log('Rows returned:', response.data.execution.row_count);
      console.log('Data:', JSON.stringify(response.data.execution.data, null, 2));
    }
  })
  .catch(error => {
    console.error('Error:', error.response ? error.response.data : error.message);
  });
```

### Server Configuration Notes

**Important:** Ensure the server firewall allows inbound connections on port:
- **8000** - FastAPI backend

**For production deployments:**
- Use HTTPS with SSL/TLS certificates (consider using nginx as reverse proxy)
- Implement authentication/authorization middleware
- Configure CORS policies in [app/main.py](app/main.py) (currently allows all origins)
- Set up rate limiting at the network/proxy level
- Use environment variables for sensitive configuration

## 📡 API Reference

### Base URL
```
http://localhost:8000
```

### Endpoints

#### 1. Generate SQL Query (Dry Run)
**POST** `/nlq/execute` with `"dry_run": true`

Converts natural language to SQL **without executing** on Athena.

**Request Body:**
```json
{
  "text": "How many high severity incidents in the last 7 days?",
  "context": {
    "language": "en",
    "property_uuid": "c7254cc9-9145-4602-b44b-0c1cff335f83,2b618b46-6b80-481b-b1e3-5aec1647b926",
    "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6",
    "user_role": null
  },
  "sql": {
    "dialect": "redshift",
    "tables": []
  },
  "execution": {
    "dry_run": true,
    "max_rows": 100,
    "redshift_target": null
  },
  "model": {
    "max_tokens": 512
  },
  "display": {
    "type": "metric"
  },
  "trace": {
    "source": "socket",
    "request_id": "ea6a29ca-ce23-4235-a3dc-5b9850f6bf16"
  }
}
```

> **Note:** The `display` field is **optional**. If provided, it overrides the automatic display type detection. Valid values: `"metric"`, `"pie"`, `"bar"`, `"line"`, `"table"`. If omitted, the API will automatically recommend the best display type based on the query pattern and results.

**cURL Example:**
```bash
curl -X POST http://128.106.57.220:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "How many high severity incidents in the last 7 days?",
    "context": {
      "language": "en",
      "property_uuid": "c7254cc9-9145-4602-b44b-0c1cff335f83,2b618b46-6b80-481b-b1e3-5aec1647b926",
      "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6",
      "user_role": null
    },
    "sql": {"dialect": "redshift", "tables": []},
    "execution": {"dry_run": false, "max_rows": 100, "redshift_target": null},
    "model": {"max_tokens": 512},
    "trace": {"source": "socket"}
  }'
```

**Response (200 OK):**
```json
{
  "success": true,
  "sql": {
    "query": "SELECT COUNT(*) as count FROM incident_combine WHERE severity_name = 'high' AND date_parse(snapshotdate, '%Y-%m-%d') >= date_add('day', -7, current_date) AND property_uuid IN ('c7254cc9-9145-4602-b44b-0c1cff335f83', '2b618b46-6b80-481b-b1e3-5aec1647b926') LIMIT 100",
    "confidence": 0.9
  },
  "execution": {
    "executed": false,
    "row_count": null,
    "data": null
  },
  "display": {
    "type": "metric"
  },
  "explanation": {
    "summary": "SQL generated for Athena execution.",
    "assumptions": []
  },
  "trace": {
    "request_id": "ea6a29ca-ce23-4235-a3dc-5b9850f6bf16",
    "model_latency_ms": 2847,
    "total_latency_ms": 2963,
    "redshift_target": "peninsula_incident",
    "allowed_tables": [
      "incident_combine"
    ],
    "input_warnings": []
  }
}
```

#### 2. Execute Query
**POST** `/nlq/execute`

Generates SQL and executes it on Athena.

**Request Body:**
```json
{
  "text": "Show recent high priority incidents",
  "context": {
    "language": "en",
    "property_uuid": "c7254cc9-9145-4602-b44b-0c1cff335f83,2b618b46-6b80-481b-b1e3-5aec1647b926",
    "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6",
    "user_role": null
  },
  "sql": {
    "dialect": "redshift",
    "tables": []
  },
  "execution": {
    "dry_run": false,
    "max_rows": 100,
    "redshift_target": null
  },
  "model": {
    "max_tokens": 512
  },
  "trace": {
    "source": "socket",
    "request_id": "ea6a29ca-ce23-4235-a3dc-5b9850f6bf16"
  }
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Show recent high priority incidents",
    "context": {
      "language": "en",
      "property_uuid": "c7254cc9-9145-4602-b44b-0c1cff335f83,2b618b46-6b80-481b-b1e3-5aec1647b926",
      "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6",
      "user_role": null
    },
    "sql": {"dialect": "redshift", "tables": []},
    "execution": {"dry_run": false, "max_rows": 100, "redshift_target": null},
    "model": {"max_tokens": 512},
    "trace": {"source": "socket"}
  }'
```

**Response (200 OK):**
```json
{
  "success": true,
  "sql": {
    "query": "SELECT incident_uuid, property_name, category_name, severity_name, status_name, created_date FROM incident_combine WHERE severity_name = 'high' AND property_uuid IN ('c7254cc9-9145-4602-b44b-0c1cff335f83', '2b618b46-6b80-481b-b1e3-5aec1647b926') ORDER BY created_date DESC LIMIT 10",
    "confidence": 0.9
  },
  "execution": {
    "executed": true,
    "row_count": 10,
    "data": {
      "columns": [
        "incident_uuid",
        "property_name",
        "category_name",
        "severity_name",
        "status_name",
        "created_date"
      ],
      "rows": [
        {
          "incident_uuid": "de77d198-abc2-4cfe-84b1-04fe84a13898",
          "property_name": "The Peninsula Hong Kong",
          "category_name": "systems",
          "severity_name": "high",
          "status_name": "pending",
          "created_date": "1760248368572404000"
        },
        {
          "incident_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
          "property_name": "The Peninsula Hong Kong",
          "category_name": "maintenance",
          "severity_name": "high",
          "status_name": "completed",
          "created_date": "1760148368572404000"
        },
        {
          "incident_uuid": "f9e8d7c6-b5a4-3210-fedc-ba9876543210",
          "property_name": "The Peninsula Hong Kong",
          "category_name": "guest_complaint",
          "severity_name": "high",
          "status_name": "pending",
          "created_date": "1760048368572404000"
        }
      ],
      "row_count": 10
    }
  },
  "display": {
    "type": "table"
  },
  "explanation": {
    "summary": "SQL generated for Athena execution.",
    "assumptions": []
  },
  "trace": {
    "request_id": "ea6a29ca-ce23-4235-a3dc-5b9850f6bf16",
    "model_latency_ms": 3024,
    "total_latency_ms": 4856,
    "redshift_target": "peninsula_incident",
    "allowed_tables": [
      "incident_combine"
    ],
    "input_warnings": []
  }
}
```

#### 3. Health Check
**GET** `/health`

**Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "0.4-refactored",
  "rate_limiter": {
    "requests_per_second": 2.0,
    "burst_size": 10,
    "queue_size": 100,
    "current_tokens": 8.5,
    "queued_requests": 0,
    "total_requests": 1247,
    "total_queued": 23,
    "total_rejected": 5
  }
}
```

### Request Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | Yes | Natural language query |
| `context.language` | string | No | Query language: "en", "zh", "ms", "ta" (default: "en") |
| `context.property_uuid` | string | Yes | Comma-separated property UUIDs (pre-authorized by upstream service) |
| `context.account_uuid` | string | Yes | Account UUID |
| `context.user_role` | string | No | User role (nullable) |
| `sql.dialect` | string | Yes | Must be "athena" |
| `sql.tables` | array | No | Allowed tables override (default: resolved from config) |
| `execution.dry_run` | boolean | No | If true, returns SQL without executing (default: true) |
| `execution.max_rows` | integer | No | Max rows to return (default: 100) |
| `execution.athena_target` | string | No | Athena target override (default: resolved from config) |
| `model.max_tokens` | integer | No | Max tokens for model generation (default: 256) |
| `trace.source` | string | No | Request source identifier (default: "fcs1-ui") |
| `trace.request_id` | string | No | Client-provided request ID (auto-generated if omitted) |

### Error Responses

**400 Bad Request - Invalid Input**
```json
{
  "detail": "Invalid input: Query text is required"
}
```

**400 Bad Request - Unauthorized Table**
```json
{
  "detail": "Unauthorized table(s): unauthorized_table. Allowed tables: incident_combine"
}
```

**429 Too Many Requests - Rate Limited**
```json
{
  "detail": "Rate limit exceeded. Retry after 0.5 seconds"
}
```

## 🔐 Access Control System

Access control is **handled by the upstream service** before requests reach iWiz. The `property_uuid` field contains a **comma-separated list of pre-authorized property UUIDs** that the user is allowed to access.

### How It Works

1. **Upstream service authenticates** the user and determines which properties they can access
2. **Request arrives at iWiz** with `property_uuid` containing one or more authorized UUIDs
3. **iWiz parses** the comma-separated UUIDs into a list
4. **SQL generation** automatically includes a `WHERE property_uuid IN (...)` clause scoped to those UUIDs
5. **SQL validation** ensures generated queries only reference allowed tables

### Single Property Access
```json
{
  "context": {
    "language": "en",
    "property_uuid": "c7254cc9-9145-4602-b44b-0c1cff335f83",
    "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6",
    "user_role": null
  }
}
```
Generated SQL: `... WHERE property_uuid IN ('c7254cc9-9145-4602-b44b-0c1cff335f83') ...`

### Multi-Property Access
```json
{
  "context": {
    "language": "en",
    "property_uuid": "c7254cc9-9145-4602-b44b-0c1cff335f83,2b618b46-6b80-481b-b1e3-5aec1647b926",
    "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6",
    "user_role": null
  }
}
```
Generated SQL: `... WHERE property_uuid IN ('c7254cc9-9145-4602-b44b-0c1cff335f83', '2b618b46-6b80-481b-b1e3-5aec1647b926') ...`

### Key Points

- **iWiz does not perform authorization** — it trusts the upstream service
- **All property UUIDs** in the comma-separated list are treated as authorized
- **Data filtering** is enforced at the SQL level via `WHERE property_uuid IN (...)`
- **Table access** is controlled by `sql.tables` (from payload) or `REDSHIFT_TARGETS` config

## 🗄️ Database Schema

### Available Databases
- **peninsula_incident** - Peninsula Hotels incident management
- **londoner_granded** - The Londoner Macao incident data

### Common Tables

#### `incident_combine`
Main incident tracking table.

| Column | Type | Description |
|--------|------|-------------|
| `incident_uuid` | VARCHAR | Unique incident identifier |
| `property_name` | VARCHAR | Property name (e.g., "The Peninsula Hong Kong") |
| `location_name` | VARCHAR | Specific location (e.g., "Room 1018") |
| `category_name` | VARCHAR | Incident category (lowercase) |
| `severity_name` | VARCHAR | Severity: "high", "medium", "low" |
| `status_name` | VARCHAR | Status: "pending", "completed", "cancelled" |
| `snapshotdate` | VARCHAR | Date string (format: YYYY-MM-DD) |
| `created_date` | BIGINT | Unix timestamp |
| `incident_time` | BIGINT | Unix timestamp |

## 💡 Example Queries

### Basic Queries
```bash
# Count incidents
curl -X POST http://localhost:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "How many incidents are there?",
    "context": {
      "language": "en",
      "property_uuid": "c7254cc9-9145-4602-b44b-0c1cff335f83,2b618b46-6b80-481b-b1e3-5aec1647b926",
      "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6",
      "user_role": null
    },
    "sql": {"dialect": "redshift", "tables": []},
    "execution": {"dry_run": false, "max_rows": 100, "redshift_target": null},
    "model": {"max_tokens": 512},
    "trace": {"source": "socket"}
  }'
```

### Time-based Queries
```bash
# Recent incidents
curl -X POST http://localhost:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Show incidents from last 7 days",
    "context": {
      "language": "en",
      "property_uuid": "c7254cc9-9145-4602-b44b-0c1cff335f83,2b618b46-6b80-481b-b1e3-5aec1647b926",
      "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6",
      "user_role": null
    },
    "sql": {"dialect": "redshift", "tables": []},
    "execution": {"dry_run": false, "max_rows": 100, "redshift_target": null},
    "model": {"max_tokens": 512},
    "trace": {"source": "socket"}
  }'
```

### Filtering Queries
```bash
# High severity incidents
curl -X POST http://localhost:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Show high severity pending incidents",
    "context": {
      "language": "en",
      "property_uuid": "c7254cc9-9145-4602-b44b-0c1cff335f83,2b618b46-6b80-481b-b1e3-5aec1647b926",
      "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6",
      "user_role": null
    },
    "sql": {"dialect": "redshift", "tables": []},
    "execution": {"dry_run": false, "max_rows": 100, "redshift_target": null},
    "model": {"max_tokens": 512},
    "trace": {"source": "socket"}
  }'
```

## 🛠️ Configuration Files

| File | Purpose |
|------|---------|
| `app/redshift_config.py` | Athena database configurations |
| `app/models.py` | Pydantic request/response models |
| `app/prompt.py` | LLM prompt construction with property UUID filtering |
| `app/security.py` | SQL validation and table allowlisting |

## 📊 Monitoring & Logging

All API requests are logged to `logs/api_requests.json`:
```json
{
  "timestamp": "2026-01-23T10:30:00Z",
  "endpoint": "/nlq/execute",
  "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6",
  "property_uuid": "c7254cc9-9145-4602-b44b-0c1cff335f83,2b618b46-6b80-481b-b1e3-5aec1647b926",
  "query_text": "Show recent incidents",
  "generated_sql": "SELECT ...",
  "status": "success",
  "execution_time_ms": 1234
}
```

## 🏗️ Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Request                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  FastAPI Application (main.py)                   │
│  • Rate Limiter (2 req/s, burst 10)                             │
│  • Input Validator (XSS/Injection protection)                   │
│  • Request Logger (JSON logs)                                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Access Control (upstream-authorized)              │
│  Property UUIDs → WHERE property_uuid IN (...) filter          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│           Query Normalizer (query_normalizer.py)                 │
│  • Entity alias resolution (property names, severities)          │
│  • Abbreviation expansion (HK → The Peninsula Hong Kong)        │
│  • Fuzzy matching for status/category names                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Prompt Builder (prompt.py)                          │
│  • Schema injection (tables, columns, samples)                   │
│  • Athena SQL syntax rules                                      │
│  • Date handling instructions                                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│        SQL Generator (sqlcoder.py)                               │
│  • defog/sqlcoder-7b-2 model (7B params, 4-bit quantized)       │
│  • Thread-safe model access with lock                           │
│  • LRU cache (500 queries, MD5 keys)                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│          SQL Post-Processing (sqlcoder.py)                       │
│  • fix_date_comparisons(): Wraps snapshotdate with date_parse() │
│  • LIMIT enforcement (max 100 rows)                             │
│  • SQL extraction and cleaning                                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│           SQL Validator (security.py)                            │
│  • Table allowlist enforcement                                  │
│  • Forbidden keyword detection (DROP, DELETE, etc.)             │
│  • SQL injection pattern matching                               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│         Athena Executor (redshift_client.py)                       │
│  • redshift_connector (IAM)                                        │
│  • Query execution and result polling                           │
│  • Result set fetching                                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│         Display Hint Generator (display_hint.py)                 │
│  • line: Time series with GROUP BY + aggregation                │
│  • bar: Categorical aggregations (≤50 rows)                     │
│  • pie: Categorical aggregations (≤10 rows)                     │
│  • metric: Single value (COUNT, SUM, etc.)                      │
│  • table: Default for raw records                               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      JSON Response                               │
│  { sql, results, display, trace, explanation }                  │
└─────────────────────────────────────────────────────────────────┘
```

### Module Descriptions

| Module | Purpose | Key Features |
|--------|---------|-------------|
| `main.py` | FastAPI app entry point | Rate limiting, CORS, async lifespan management |
| `sqlcoder.py` | SQL generation & fixing | Model inference, LRU caching, date comparison fixes |
| `permissions.py` | Access control enforcement | Property UUID parsing, SQL filtering |
| `redshift_client.py` | Redshift integration | Query execution, result fetching, error handling |
| `display_hint.py` | Display type recommendation | SQL pattern analysis, row/column heuristics |
| `input_validator.py` | Input sanitization | XSS detection, SQL injection prevention |
| `rate_limiter.py` | Request rate control | Token bucket, queue management, backpressure |
| `query_normalizer.py` | Entity normalization | Alias resolution, fuzzy matching |
| `prompt.py` | LLM prompt construction | Schema injection, SQL syntax rules |
| `security.py` | SQL security validation | Table allowlist, forbidden keywords |
| `schema_loader.py` | Database schema loading | Table/column metadata from JSON |
| `query_suggestions.py` | Sample query generation | Schema-based suggestions |

### SQL Post-Processing Pipeline

The API automatically fixes common SQL issues after generation:

#### 1. Date Comparison Fixing

**Problem**: The `snapshotdate` column is stored as VARCHAR (`'2025-01-23'`), causing Athena type mismatch errors:
```
TYPE_MISMATCH: Cannot apply operator: varchar <= date
```

**Solution**: `fix_date_comparisons()` automatically wraps bare `snapshotdate` in `date_parse()`:

```python
# Before (generated by model - causes error)
SELECT * FROM incident_combine 
WHERE snapshotdate >= date_add('day', -7, current_date)

# After (automatically fixed)
SELECT * FROM incident_combine 
WHERE date_parse(snapshotdate, '%Y-%m-%d') >= date_add('day', -7, current_date)
```

This ensures all time-based queries work correctly regardless of LLM output quality.

#### 2. LIMIT Enforcement

- Adds `LIMIT 100` if missing
- Caps existing LIMIT to max 100 rows
- Prevents resource exhaustion from unbounded queries

#### 3. SQL Extraction & Cleaning

- Removes markdown code fences (` ```sql `)
- Extracts SELECT statement using regex
- Normalizes whitespace

## 🔧 Environment Setup

### 1. Create Environment File

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

### 2. Required Environment Variables

The `.env` file must contain:

```bash
# AWS Credentials - Required for Athena access
AWS_ACCESS_KEY_ID=your_aws_access_key_id_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key_here
AWS_REGION=ap-east-1

# API Configuration
API_PORT=8000
API_HOST=0.0.0.0
```

**Alternative:** Use AWS CLI configuration (recommended for development)
```bash
aws configure
# This will store credentials in ~/.aws/credentials
```

**⚠️ Security Note:** 
- Never commit `.env` to version control
- The `.env` file is already in `.gitignore`
- Only use `.env.example` as a template with placeholder values

## 🎯 Display Type Configuration

The API provides flexible display type configuration through the `display` field in the request payload. You can either let the API automatically detect the best visualization type or manually specify your preference.

### Auto-Detection (Recommended)

**Omit the `display` field** from your request, and the API will automatically analyze the SQL query pattern and result structure to recommend the optimal visualization type.

```json
{
  "text": "How many incidents per status?",
  "context": { ... },
  "sql": { "dialect": "redshift" },
  "execution": { "dry_run": false }
}
```

The API response will include a recommended display type:
```json
{
  "display": {
    "type": "bar"
  }
}
```

### Manual Override

**Include the `display` field** in your request to explicitly specify the visualization type, overriding automatic detection.

```json
{
  "text": "How many incidents per status?",
  "context": { ... },
  "sql": { "dialect": "redshift" },
  "execution": { "dry_run": false },
  "display": {
    "type": "pie"
  }
}
```

The API will respect your preference:
```json
{
  "display": {
    "type": "pie"
  }
}
```

### Display Types Overview

| Display Type | When Used | Row Count | Query Pattern |
|--------------|-----------|-----------|---------------|
| **metric** | Single numeric value (KPI) | 1 row, 1 column | `COUNT(*)`, `SUM(*)`, `AVG(*)` |
| **pie** | Categorical breakdown | ≤10 rows | `GROUP BY` with aggregation |
| **bar** | Categorical comparison | 11-50 rows | `GROUP BY` with aggregation |
| **line** | Time series trend | Any | `GROUP BY` date/time + aggregation |
| **table** | Raw data or detailed list | >50 rows or no aggregation | `SELECT *`, detail queries |

**Time Series Detection:** The API automatically detects time series queries by analyzing:
- SQL patterns: `DATE()`, `CAST(... AS DATE)`, `DATE_TRUNC()`, date-related GROUP BY clauses
- Column names: Columns containing 'date', 'day', 'week', 'month', 'year', 'time'
- Query structure: Presence of aggregation functions with date grouping

**Example time series queries that will show line charts:**
- "Show me incidents per day over the last 7 days"
- "Count incidents by week for the last month"
- "Daily incident trend"

### 1. Metric Display (`"type": "metric"`)

**Use Case:** Single KPI values for dashboards

**Example Request:**
```bash
curl -X POST http://localhost:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "How many total incidents?",
    "context": {
      "language": "en",
      "property_uuid": "c7254cc9-9145-4602-b44b-0c1cff335f83,2b618b46-6b80-481b-b1e3-5aec1647b926",
      "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6",
      "user_role": null
    },
    "sql": {"dialect": "redshift", "tables": []},
    "execution": {"dry_run": false, "max_rows": 100, "redshift_target": null},
    "model": {"max_tokens": 512},
    "trace": {"source": "socket"}
  }'
```

**Response (truncated):**
```json
{
  "success": true,
  "sql": {
    "query": "SELECT COUNT(*) as total FROM incident_combine WHERE property_uuid IN ('c7254cc9-9145-4602-b44b-0c1cff335f83', '2b618b46-6b80-481b-b1e3-5aec1647b926') LIMIT 100"
  },
  "execution": {
    "executed": true,
    "data": {
      "columns": ["total"],
      "rows": [{"total": 1247}],
      "row_count": 1
    }
  },
  "display": {
    "type": "metric"
  }
}
```

**Frontend Rendering:** Large number card or KPI widget

---

### 2. Pie Chart Display (`"type": "pie"`)

**Use Case:** Category distribution with few categories

**Example Request:**
```bash
curl -X POST http://localhost:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Show incident breakdown by severity",
    "context": {
      "language": "en",
      "property_uuid": "c7254cc9-9145-4602-b44b-0c1cff335f83,2b618b46-6b80-481b-b1e3-5aec1647b926",
      "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6",
      "user_role": null
    },
    "sql": {"dialect": "redshift", "tables": []},
    "execution": {"dry_run": false, "max_rows": 100, "redshift_target": null},
    "model": {"max_tokens": 512},
    "trace": {"source": "socket"}
  }'
```

**Example with Manual Override:**
```bash
curl -X POST http://localhost:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Show incident breakdown by severity",
    "context": {
      "language": "en",
      "property_uuid": "c7254cc9-9145-4602-b44b-0c1cff335f83,2b618b46-6b80-481b-b1e3-5aec1647b926",
      "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6",
      "user_role": null
    },
    "sql": {"dialect": "redshift", "tables": []},
    "execution": {"dry_run": false, "max_rows": 100, "redshift_target": null},
    "model": {"max_tokens": 512},
    "display": {"type": "bar"},
    "trace": {"source": "socket"}
  }'
```

**Response (truncated):**
```json
{
  "success": true,
  "sql": {
    "query": "SELECT severity_name, COUNT(*) as count FROM incident_combine WHERE property_uuid IN ('c7254cc9-9145-4602-b44b-0c1cff335f83', '2b618b46-6b80-481b-b1e3-5aec1647b926') GROUP BY severity_name LIMIT 100"
  },
  "execution": {
    "executed": true,
    "data": {
      "columns": ["severity_name", "count"],
      "rows": [
        {"severity_name": "high", "count": 342},
        {"severity_name": "medium", "count": 567},
        {"severity_name": "low", "count": 338}
      ],
      "row_count": 3
    }
  },
  "display": {
    "type": "pie"
  }
}
```

**Frontend Rendering:** Pie or donut chart with percentage labels

---

### 3. Bar Chart Display (`"type": "bar"`)

**Use Case:** Comparing categories (more than 10, up to 50)

**Example Request:**
```bash
curl -X POST http://localhost:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Show incidents by category",
    "context": {
      "language": "en",
      "property_uuid": "c7254cc9-9145-4602-b44b-0c1cff335f83,2b618b46-6b80-481b-b1e3-5aec1647b926",
      "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6",
      "user_role": null
    },
    "sql": {"dialect": "redshift", "tables": []},
    "execution": {"dry_run": false, "max_rows": 100, "redshift_target": null},
    "model": {"max_tokens": 512},
    "trace": {"source": "socket"}
  }'
```

**Response (truncated):**
```json
{
  "success": true,
  "sql": {
    "query": "SELECT category_name, COUNT(*) as count FROM incident_combine WHERE property_uuid IN ('c7254cc9-9145-4602-b44b-0c1cff335f83', '2b618b46-6b80-481b-b1e3-5aec1647b926') GROUP BY category_name ORDER BY count DESC LIMIT 100"
  },
  "execution": {
    "executed": true,
    "data": {
      "columns": ["category_name", "count"],
      "rows": [
        {"category_name": "maintenance", "count": 245},
        {"category_name": "guest_complaint", "count": 189},
        {"category_name": "systems", "count": 156},
        {"category_name": "housekeeping", "count": 134},
        {"category_name": "engineering", "count": 98}
      ],
      "row_count": 15
    }
  },
  "display": {
    "type": "bar"
  }
}
```

**Frontend Rendering:** Vertical or horizontal bar chart

---

### 4. Line Chart Display (`"type": "line"`)

**Use Case:** Time series trends (requires GROUP BY with date/time column + aggregation)

**Example Request:**
```bash
curl -X POST http://localhost:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Show daily incident count for last 30 days",
    "context": {
      "language": "en",
      "property_uuid": "c7254cc9-9145-4602-b44b-0c1cff335f83,2b618b46-6b80-481b-b1e3-5aec1647b926",
      "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6",
      "user_role": null
    },
    "sql": {"dialect": "redshift", "tables": []},
    "execution": {"dry_run": false, "max_rows": 100, "redshift_target": null},
    "model": {"max_tokens": 512},
    "trace": {"source": "socket"}
  }'
```

**Response (truncated):**
```json
{
  "success": true,
  "sql": {
    "query": "SELECT snapshotdate, COUNT(*) as daily_count FROM incident_combine WHERE property_uuid IN ('c7254cc9-9145-4602-b44b-0c1cff335f83', '2b618b46-6b80-481b-b1e3-5aec1647b926') AND date_parse(snapshotdate, '%Y-%m-%d') >= date_add('day', -30, current_date) GROUP BY snapshotdate ORDER BY snapshotdate LIMIT 100"
  },
  "execution": {
    "executed": true,
    "data": {
      "columns": ["snapshotdate", "daily_count"],
      "rows": [
        {"snapshotdate": "2025-12-24", "daily_count": 12},
        {"snapshotdate": "2025-12-25", "daily_count": 8},
        {"snapshotdate": "2025-12-26", "daily_count": 15},
        {"snapshotdate": "2025-12-27", "daily_count": 11},
        {"snapshotdate": "2025-12-28", "daily_count": 14}
      ],
      "row_count": 30
    }
  },
  "display": {
    "type": "line"
  }
}
```

**Frontend Rendering:** Line chart with X-axis (dates) and Y-axis (counts)

**Important:** Line charts require:
- `GROUP BY` clause with a date/time column
- Aggregation function (`COUNT()`, `SUM()`, `AVG()`, etc.)
- Raw `SELECT *` queries with date columns will NOT trigger line chart

---

### 5. Table Display (`"type": "table"`)

**Use Case:** Raw records, detailed data, or many rows (>50)

**Example Request:**
```bash
curl -X POST http://localhost:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Show recent pending high severity incidents",
    "context": {
      "language": "en",
      "property_uuid": "c7254cc9-9145-4602-b44b-0c1cff335f83,2b618b46-6b80-481b-b1e3-5aec1647b926",
      "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6",
      "user_role": null
    },
    "sql": {"dialect": "redshift", "tables": []},
    "execution": {"dry_run": false, "max_rows": 100, "redshift_target": null},
    "model": {"max_tokens": 512},
    "trace": {"source": "socket"}
  }'
```

**Response (truncated):**
```json
{
  "success": true,
  "sql": {
    "query": "SELECT incident_uuid, category_name, severity_name, status_name, location_name, created_date FROM incident_combine WHERE property_uuid IN ('c7254cc9-9145-4602-b44b-0c1cff335f83', '2b618b46-6b80-481b-b1e3-5aec1647b926') AND severity_name = 'high' AND status_name = 'pending' ORDER BY created_date DESC LIMIT 100"
  },
  "execution": {
    "executed": true,
    "data": {
      "columns": ["incident_uuid", "category_name", "severity_name", "status_name", "location_name", "created_date"],
      "rows": [
        {
          "incident_uuid": "de77d198-abc2-4cfe-84b1-04fe84a13898",
          "category_name": "systems",
          "severity_name": "high",
          "status_name": "pending",
          "location_name": "1801",
          "created_date": "1760248368572404000"
        },
        {
          "incident_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
          "category_name": "maintenance",
          "severity_name": "high",
          "status_name": "pending",
          "location_name": "2305",
          "created_date": "1760148368572404000"
        }
      ],
      "row_count": 47
    }
  },
  "display": {
    "type": "table"
  }
}
```

**Frontend Rendering:** Data table with sortable columns, pagination

---

### Display Type Selection Logic

The API uses these rules (in order) to determine display type:

1. **Single value** (1 row, 1 column) → `metric`
2. **Aggregation + GROUP BY time column** → `line`
3. **Aggregation + GROUP BY** with ≤10 rows → `pie`
4. **Aggregation + GROUP BY** with 11-50 rows → `bar`
5. **Everything else** (raw SELECT, >50 rows) → `table`

**Key Insights:**
- Display hints are **recommendations** - frontend can override based on user preference
- All responses include the full data regardless of display type
- Display logic is in `app/display_hint.py` and can be customized

## 🚦 Rate Limiting

Built-in token bucket rate limiter protects the model from overload:

- **Rate**: 2 requests/second
- **Burst**: 10 requests (token bucket capacity)
- **Queue**: Up to 100 requests (30s timeout)
- **Algorithm**: Token bucket with request queuing

**Rate Limit Headers**:
```http
X-RateLimit-Limit: 2.0
X-RateLimit-Remaining: 8.5
X-RateLimit-Reset: 1674480000.123
```

**429 Response**:
```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Try again in 0.5 seconds",
  "retry_after": 0.5
}
```

## 🔒 Security Features

### Input Validation

All user inputs are validated before processing:

- **XSS Protection**: Detects and blocks `<script>`, `javascript:`, event handlers
- **SQL Injection Prevention**: Blocks multiple statements, UNION attacks, comment injections
- **HTML Sanitization**: Automatically escapes HTML entities
- **Length Limits**: Max 5000 characters for query text

### SQL Security

Generated SQL is validated before execution:

- **Table Allowlist**: Only tables in permissions config allowed
- **Forbidden Keywords**: Blocks `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`
- **Statement Limiting**: Only SELECT statements allowed
- **LIMIT Enforcement**: Maximum 100 rows returned

### Access Control

Upstream-authorized property UUID system:

1. **Upstream Service**: Authenticates user and determines allowed properties
2. **Property UUID Filtering**: `WHERE property_uuid IN (...)` enforced in generated SQL
3. **Table Allowlist**: Only configured tables permitted

## 📦 Dependencies

```bash
pip install -r requirements.txt
```

Key packages:
- `fastapi==0.104.1` - Web framework
- `uvicorn==0.24.0` - ASGI server
- `boto3==1.29.7` - AWS SDK
- `pyathena==3.0.10` - Athena driver
- `pydantic==2.5.0` - Data validation
- `transformers` - NLQ model (defog/sqlcoder-7b-2)
- `bitsandbytes` - 4-bit quantization
- `torch==2.1.1` - PyTorch for model inference
- `python-dotenv==1.0.0` - Environment variable loading

## 🧪 Testing

```bash
# Run test suite
python -m pytest test/

# Stress test
python test/stress_test.py

# Health check
curl http://localhost:8000/health
```

## 📝 Adding New Properties

1. **Upstream service grants access** to the property UUID for the user/account

2. **Test access:**
```bash
curl -X POST http://localhost:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "test query",
    "context": {
      "language": "en",
      "property_uuid": "new-property-uuid-here",
      "account_uuid": "account-uuid",
      "user_role": null
    },
    "sql": {"dialect": "redshift", "tables": []},
    "execution": {"dry_run": false, "max_rows": 100, "redshift_target": null},
    "model": {"max_tokens": 512},
    "trace": {"source": "socket"}
  }'
```

## ⚙️ Configuration

### Performance Tuning

**Model Configuration** (`app/sqlcoder.py`):
```python
# Model loading options
model_name = "defog/sqlcoder-7b-2"
quantization_config = BitsAndBytesConfig(load_in_4bit=True)  # ~4GB VRAM
device_map = "auto"  # Automatic GPU/CPU mapping
```

**Cache Settings** (`app/sqlcoder.py`):
```python
_CACHE_MAX_SIZE = 500  # LRU cache for SQL queries
```

**Rate Limiter** (`app/rate_limiter.py`):
```python
requests_per_second = 2.0  # Adjust based on hardware
burst_size = 10  # Token bucket capacity
queue_size = 100  # Max queued requests
queue_timeout = 30.0  # Queue wait timeout
```

**Thread Pool** (`app/main.py`):
```python
_executor = ThreadPoolExecutor(max_workers=4)  # For model inference
```

### Database Configuration

Athena targets are defined in `app/redshift_config.py`:

```python
REDSHIFT_TARGETS = {
    "peninsula_incident": {
        "database": "peninsula_incident",
        "workgroup": "primary",
        "output_location": "s3://your-bucket/athena-results/"
    }
}
```

## 🔒 Security Best Practices

- **Access control is handled upstream** — iWiz trusts the property UUIDs in the payload
- Property UUIDs are enforced at the SQL generation level via `WHERE property_uuid IN (...)`
- All SQL queries are validated before execution
- Table access is controlled per Athena target configuration
- **Cross-property queries are scoped** to only the UUIDs provided in `property_uuid`
- Input validation prevents XSS and SQL injection attacks
- Rate limiting prevents abuse and resource exhaustion
- All API requests are logged with full context for audit trails

## 📚 Additional Documentation

See `/documentation` folder for:
- Performance optimization guides
- Deployment procedures
- Test questions and examples

## 🆘 Troubleshooting

### Common Issues

**Problem:** 400 Bad Request - Table not allowed

**Solution:** Check that the Athena target configuration in `app/redshift_config.py` includes the required tables

---

**Problem:** Query returns no results

**Solution:** Verify property name matches exactly (case-sensitive). Use canonical names like "The Peninsula Hong Kong"

---

**Problem:** TYPE_MISMATCH error with date queries

**Solution:** This should be automatically fixed by `fix_date_comparisons()`. If still occurring:
1. Check `logs/api_requests.json` for the generated SQL
2. Verify the fix was applied correctly
3. Restart the server: `./stop.sh && ./start.sh`

---

**Problem:** 429 Rate Limit Exceeded

**Solution:** 
- Wait for the `retry_after` seconds indicated in the response
- Reduce request frequency to ≤2 req/s
- Implement client-side backoff strategy
- Check rate limiter stats: `curl http://localhost:8000/health`

---

**Problem:** Model loading fails or OOM (Out of Memory)

**Solution:**
- Ensure at least 8GB RAM available
- Check GPU memory if using CUDA: `nvidia-smi`
- Reduce `max_workers` in thread pool (currently 4)
- Clear model cache: Restart the server

---

**Problem:** Slow query responses (>10 seconds)

**Solution:**
1. Check if query is cached: Look for `"from_cache": true` in response
2. Verify Athena region matches: Should be `ap-east-1`
3. Check Athena query execution time in AWS Console
4. Consider optimizing the prompt or query structure

### Debugging Tools

**View API logs:**
```bash
tail -f logs/api_requests.json | jq .
```

**Check rate limiter stats:**
```bash
curl http://localhost:8000/health | jq .rate_limiter
```

**View process status:**
```bash
ps aux | grep uvicorn
```

**Monitor resource usage:**
```bash
htop  # or top
```

## 📞 Support

For issues or questions, check logs at `logs/api_requests.json` for detailed error information.
