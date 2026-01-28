# Natural Language Query to SQL API

Production-ready FastAPI service that converts natural language questions into Athena SQL queries with comprehensive property-based access control, intelligent SQL post-processing, rate limiting, and automated display type recommendations.

## ✨ Key Features

- 🤖 **AI-Powered SQL Generation**: Uses Qwen-2.5-3b-Text_to_SQL model for accurate NLQ to SQL conversion
- 🛡️ **Three-Tier Access Control**: Account → Property → User level permissions
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
# Start complete application (API + UI)
./start.sh

# Stop all services
./stop.sh
```

### Option 2: Manual Startup

```bash
# Start API server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Start Streamlit UI (in another terminal)
streamlit run streamlit_app.py --server.port 8501
```

**Services:**
- API: `http://localhost:8000`
- Streamlit UI: `http://localhost:8501`

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
      "account_uuid": "149cd8f0-00e1-43a4-840b-6a54b4f857f6",
      "property_uuid": "8afe7e5e-22e5-4318-b5c7-f967fc44e81f",
      "user_uuid": "c4b943a0-57c5-4fe1-bfb9-6e09d5b60c40",
      "language": "en"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false, "max_rows": 100},
    "model": {},
    "trace": {"source": "api"}
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
        "account_uuid": "149cd8f0-00e1-43a4-840b-6a54b4f857f6",
        "property_uuid": "8afe7e5e-22e5-4318-b5c7-f967fc44e81f",
        "user_uuid": "c4b943a0-57c5-4fe1-bfb9-6e09d5b60c40",
        "language": "en"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": False, "max_rows": 100},
    "model": {},
    "trace": {"source": "api"}
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
    account_uuid: '149cd8f0-00e1-43a4-840b-6a54b4f857f6',
    property_uuid: '8afe7e5e-22e5-4318-b5c7-f967fc44e81f',
    user_uuid: 'c4b943a0-57c5-4fe1-bfb9-6e09d5b60c40',
    language: 'en'
  },
  sql: { dialect: 'athena' },
  execution: { dry_run: false, max_rows: 100 },
  model: {},
  trace: { source: 'api' }
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

### Accessing the Streamlit UI
```
http://128.106.57.220:8501
```

### Server Configuration Notes

**Important:** Ensure the server firewall allows inbound connections on ports:
- **8000** - FastAPI backend
- **8501** - Streamlit UI

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

#### 1. Generate SQL Query
**POST** `/nlq/generate`

Converts natural language to SQL without executing.

**Request Body:**
```json
{
  "text": "How many high severity incidents in the last 7 days?",
  "context": {
    "account_uuid": "149cd8f0-00e1-43a4-840b-6a54b4f857f6",
    "property_uuid": "8afe7e5e-22e5-4318-b5c7-f967fc44e81f",
    "user_uuid": "c4b943a0-57c5-4fe1-bfb9-6e09d5b60c40",
    "language": "en"
  },
  "sql": {
    "dialect": "athena"
  },
  "execution": {
    "dry_run": true
  },
  "model": {},
  "trace": {
    "source": "api"
  }
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8000/nlq/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "How many high severity incidents in the last 7 days?",
    "context": {
      "account_uuid": "149cd8f0-00e1-43a4-840b-6a54b4f857f6",
      "property_uuid": "8afe7e5e-22e5-4318-b5c7-f967fc44e81f",
      "user_uuid": "c4b943a0-57c5-4fe1-bfb9-6e09d5b60c40",
      "language": "en"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": true},
    "model": {},
    "trace": {"source": "api"}
  }'
```

**Response (200 OK):**
```json
{
  "success": true,
  "sql": {
    "query": "SELECT COUNT(*) as count FROM incident_combine WHERE severity_name = 'high' AND date_parse(snapshotdate, '%Y-%m-%d') >= date_add('day', -7, current_date) LIMIT 100",
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
    "request_id": "req-abc123def456",
    "model_latency_ms": 2847,
    "total_latency_ms": 2963,
    "athena_target": "peninsula_incident",
    "allowed_tables": [
      "incident_combine",
      "incident_history",
      "incident_analytics"
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
    "account_uuid": "149cd8f0-00e1-43a4-840b-6a54b4f857f6",
    "property_uuid": "8afe7e5e-22e5-4318-b5c7-f967fc44e81f",
    "user_uuid": "c4b943a0-57c5-4fe1-bfb9-6e09d5b60c40",
    "language": "en"
  },
  "model": {},
  "trace": {
    "source": "api"
  },
  "sql": {
    "dialect": "athena"
  },
  "execution": {
    "dry_run": false,
    "max_rows": 100
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
      "account_uuid": "149cd8f0-00e1-43a4-840b-6a54b4f857f6",
      "property_uuid": "8afe7e5e-22e5-4318-b5c7-f967fc44e81f",
      "user_uuid": "c4b943a0-57c5-4fe1-bfb9-6e09d5b60c40",
      "language": "en"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false, "max_rows": 100},
    "model": {},
    "trace": {"source": "api"}
  }'
```

**Response (200 OK):**
```json
{
  "success": true,
  "sql": {
    "query": "SELECT incident_uuid, property_name, category_name, severity_name, status_name, created_date FROM incident_combine WHERE severity_name = 'high' AND property_name = 'The Peninsula Hong Kong' ORDER BY created_date DESC LIMIT 10",
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
    "request_id": "req-xyz789abc012",
    "model_latency_ms": 3024,
    "total_latency_ms": 4856,
    "athena_target": "peninsula_incident",
    "allowed_tables": [
      "incident_combine",
      "incident_history",
      "incident_analytics"
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
| `context.account_uuid` | string | Yes | Account UUID for access control |
| `context.property_uuid` | string | Yes | Property UUID for access control |
| `context.user_uuid` | string | **Recommended** | User UUID for granular property-level permissions |
| `context.language` | string | No | Query language: "en", "zh", "ms", "ta" (default: "en") |
| `sql.dialect` | string | Yes | Must be "athena" |
| `execution.dry_run` | boolean | No | If true, returns SQL without executing (default: true) |
| `execution.max_rows` | integer | No | Max rows to return (default: 100, max: 1000) |

### Error Responses

**403 Forbidden - Access Denied**
```json
{
  "detail": {
    "error": "User c4b943a0-57c5-4fe1-bfb9-6e09d5b60c40 does not have access to property c9c29dc9-6fbb-4564-91e0-d2e18436fdf5",
    "error_code": "USER_PROPERTY_NOT_ALLOWED",
    "suggestions": [
      "Your allowed properties: ['The Peninsula Hong Kong']",
      "Contact administrator to request access to this property"
    ]
  }
}
```

**400 Bad Request - Invalid Query**
```json
{
  "detail": "Invalid SQL: Table 'unauthorized_table' not allowed"
}
```

## 🔐 Access Control System

The API implements **three-tier access control**:

### Tier 1: Account/Property Level
Maps `(account_uuid, property_uuid)` pairs to allowed databases and tables.

**Configuration:** `app/permissions_config.py`
```python
PERMISSIONS_MAPPING = {
    ("149cd8f0-00e1-43a4-840b-6a54b4f857f6", "8afe7e5e-22e5-4318-b5c7-f967fc44e81f"): {
        "athena_targets": ["peninsula_incident"],
        "tables": ["incident_combine", "incident_history", "incident_analytics"]
    }
}
```

### Tier 2: Property Level
Maps properties to specific databases and tables.

**Properties:**
- **The Peninsula Hong Kong** (`8afe7e5e-22e5-4318-b5c7-f967fc44e81f`)
- **The Peninsula Manila** (`c9c29dc9-6fbb-4564-91e0-d2e18436fdf5`)
- **The Peninsula Tokyo** (`1ef8175a-6d1d-418e-8a51-31848b147b53`)
- **The Peninsula Bangkok** (`c0abc579-6ef4-47a3-8290-16cf26964aec`)

### Tier 3: User Level (Property-Based Access)
Maps individual users to specific properties they can access. **When user_uuid is provided, queries are restricted to that property's data only.**

**Configuration:** `app/user_table_permissions.py`
```python
USER_TABLE_PERMISSIONS = {
    # Hong Kong user - can ONLY access HK property data
    "c4b943a0-57c5-4fe1-bfb9-6e09d5b60c40": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    
    # Manila user - can ONLY access Manila property data
    "f7dabb0e-6692-4881-9df1-f8adedd4d74c": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"]
}
```

### How Access Control Works

1. **Request arrives** with `account_uuid`, `property_uuid`, and optionally `user_uuid`
2. **Tier 1 validation**: Check if account/property pair has access to requested database
3. **Tier 2 validation**: Verify property exists and maps to correct database
4. **Tier 3 validation** (if `user_uuid` provided): 
   - Verify user has access to the specified property
   - Only allow queries for that property's data
   - **Property isolation is enforced - user cannot access other properties' data**
5. **SQL validation**: Extract table names from generated SQL and verify against allowed tables

### Example Access Scenarios

**✅ Allowed:**
```json
{
  "account_uuid": "149cd8f0-00e1-43a4-840b-6a54b4f857f6",
  "property_uuid": "8afe7e5e-22e5-4318-b5c7-f967fc44e81f",
  "user_uuid": "c4b943a0-57c5-4fe1-bfb9-6e09d5b60c40"
}
// Hong Kong user accessing Hong Kong property ✓
```

**❌ Denied:**
```json
{
  "account_uuid": "149cd8f0-00e1-43a4-840b-6a54b4f857f6",
  "property_uuid": "c9c29dc9-6fbb-4564-91e0-d2e18436fdf5",
  "user_uuid": "c4b943a0-57c5-4fe1-bfb9-6e09d5b60c40"
}
// Hong Kong user trying to access Manila property ✗
// Error: USER_PROPERTY_NOT_ALLOWED
```

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
      "account_uuid": "149cd8f0-00e1-43a4-840b-6a54b4f857f6",
      "property_uuid": "8afe7e5e-22e5-4318-b5c7-f967fc44e81f",
      "user_uuid": "c4b943a0-57c5-4fe1-bfb9-6e09d5b60c40"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false},
    "model": {},
    "trace": {"source": "api"}
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
      "account_uuid": "149cd8f0-00e1-43a4-840b-6a54b4f857f6",
      "property_uuid": "8afe7e5e-22e5-4318-b5c7-f967fc44e81f",
      "user_uuid": "c4b943a0-57c5-4fe1-bfb9-6e09d5b60c40"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false},
    "model": {},
    "trace": {"source": "api"}
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
      "account_uuid": "149cd8f0-00e1-43a4-840b-6a54b4f857f6",
      "property_uuid": "8afe7e5e-22e5-4318-b5c7-f967fc44e81f",
      "user_uuid": "c4b943a0-57c5-4fe1-bfb9-6e09d5b60c40"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false},
    "model": {},
    "trace": {"source": "api"}
  }'
```

## 🛠️ Configuration Files

| File | Purpose |
|------|---------|
| `app/permissions_config.py` | Account/property access mappings |
| `app/user_table_permissions.py` | User-to-property access mappings |
| `app/athena_config.py` | Athena database configurations |
| `app/models.py` | Pydantic request/response models |

## 📊 Monitoring & Logging

All API requests are logged to `logs/api_requests.json`:
```json
{
  "timestamp": "2026-01-23T10:30:00Z",
  "endpoint": "/nlq/execute",
  "account_uuid": "149cd8f0-00e1-43a4-840b-6a54b4f857f6",
  "property_uuid": "8afe7e5e-22e5-4318-b5c7-f967fc44e81f",
  "user_uuid": "c4b943a0-57c5-4fe1-bfb9-6e09d5b60c40",
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
│              Access Control (permissions.py)                     │
│  Tier 1: Account/Property → Database mapping                    │
│  Tier 2: Property → Tables mapping                              │
│  Tier 3: User → Property access (optional)                      │
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
│  • Qwen-2.5-3b-Text_to_SQL model (3B params)                    │
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
│         Athena Executor (athena_client.py)                       │
│  • boto3 pyathena driver                                        │
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
| `permissions.py` | Access control enforcement | Three-tier validation, user-property mapping |
| `athena_client.py` | AWS Athena integration | Query execution, result fetching, error handling |
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

# Streamlit Configuration
STREAMLIT_PORT=8501
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

## 🎯 Display Type Recommendations

The API automatically analyzes SQL queries and results to recommend optimal visualization types in the `display.type` field of the response.

### Display Types Overview

| Display Type | When Used | Row Count | Query Pattern |
|--------------|-----------|-----------|---------------|
| **metric** | Single numeric value (KPI) | 1 row, 1 column | `COUNT(*)`, `SUM(*)`, `AVG(*)` |
| **pie** | Categorical breakdown | ≤10 rows | `GROUP BY` with aggregation |
| **bar** | Categorical comparison | 11-50 rows | `GROUP BY` with aggregation |
| **line** | Time series trend | Any | `GROUP BY` date/time + aggregation |
| **table** | Raw data or detailed list | >50 rows or no aggregation | `SELECT *`, detail queries |

### 1. Metric Display (`"type": "metric"`)

**Use Case:** Single KPI values for dashboards

**Example Request:**
```bash
curl -X POST http://localhost:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "How many total incidents?",
    "context": {
      "account_uuid": "149cd8f0-00e1-43a4-840b-6a54b4f857f6",
      "property_uuid": "8afe7e5e-22e5-4318-b5c7-f967fc44e81f",
      "user_uuid": "c4b943a0-57c5-4fe1-bfb9-6e09d5b60c40"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false},
    "model": {},
    "trace": {"source": "api"}
  }'
```

**Response (truncated):**
```json
{
  "success": true,
  "sql": {
    "query": "SELECT COUNT(*) as total FROM incident_combine WHERE property_name = 'The Peninsula Hong Kong' LIMIT 100"
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
      "account_uuid": "149cd8f0-00e1-43a4-840b-6a54b4f857f6",
      "property_uuid": "8afe7e5e-22e5-4318-b5c7-f967fc44e81f",
      "user_uuid": "c4b943a0-57c5-4fe1-bfb9-6e09d5b60c40"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false},
    "model": {},
    "trace": {"source": "api"}
  }'
```

**Response (truncated):**
```json
{
  "success": true,
  "sql": {
    "query": "SELECT severity_name, COUNT(*) as count FROM incident_combine WHERE property_name = 'The Peninsula Hong Kong' GROUP BY severity_name LIMIT 100"
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
      "account_uuid": "149cd8f0-00e1-43a4-840b-6a54b4f857f6",
      "property_uuid": "8afe7e5e-22e5-4318-b5c7-f967fc44e81f",
      "user_uuid": "c4b943a0-57c5-4fe1-bfb9-6e09d5b60c40"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false},
    "model": {},
    "trace": {"source": "api"}
  }'
```

**Response (truncated):**
```json
{
  "success": true,
  "sql": {
    "query": "SELECT category_name, COUNT(*) as count FROM incident_combine WHERE property_name = 'The Peninsula Hong Kong' GROUP BY category_name ORDER BY count DESC LIMIT 100"
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
      "account_uuid": "149cd8f0-00e1-43a4-840b-6a54b4f857f6",
      "property_uuid": "8afe7e5e-22e5-4318-b5c7-f967fc44e81f",
      "user_uuid": "c4b943a0-57c5-4fe1-bfb9-6e09d5b60c40"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false},
    "model": {},
    "trace": {"source": "api"}
  }'
```

**Response (truncated):**
```json
{
  "success": true,
  "sql": {
    "query": "SELECT snapshotdate, COUNT(*) as daily_count FROM incident_combine WHERE property_name = 'The Peninsula Hong Kong' AND date_parse(snapshotdate, '%Y-%m-%d') >= date_add('day', -30, current_date) GROUP BY snapshotdate ORDER BY snapshotdate LIMIT 100"
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
      "account_uuid": "149cd8f0-00e1-43a4-840b-6a54b4f857f6",
      "property_uuid": "8afe7e5e-22e5-4318-b5c7-f967fc44e81f",
      "user_uuid": "c4b943a0-57c5-4fe1-bfb9-6e09d5b60c40"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false},
    "model": {},
    "trace": {"source": "api"}
  }'
```

**Response (truncated):**
```json
{
  "success": true,
  "sql": {
    "query": "SELECT incident_uuid, category_name, severity_name, status_name, location_name, created_date FROM incident_combine WHERE property_name = 'The Peninsula Hong Kong' AND severity_name = 'high' AND status_name = 'pending' ORDER BY created_date DESC LIMIT 100"
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

Three-tier permission system:

1. **Account/Property Level**: Maps to specific databases
2. **Property Level**: Maps to specific tables
3. **User Level** (optional): Maps users to properties they can access

**All unauthorized access attempts are logged.**

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
- `transformers==4.35.2` - NLQ model (Qwen-2.5-3b)
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

## 📝 Adding New Users

1. **Add user to property mapping:**
```python
# app/user_table_permissions.py
USER_TABLE_PERMISSIONS = {
    "new-user-uuid": ["property-uuid-they-can-access"]
}
```

2. **Restart service:**
```bash
sudo systemctl restart nlq-api
```

3. **Test access:**
```bash
curl -X POST http://localhost:8000/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "test query",
    "context": {
      "account_uuid": "account-uuid",
      "property_uuid": "property-uuid",
      "user_uuid": "new-user-uuid"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false},
    "model": {},
    "trace": {"source": "api"}
  }'
```

## ⚙️ Configuration

### Performance Tuning

**Model Configuration** (`app/sqlcoder.py`):
```python
# Model loading options
model_name = "Ellbendls/Qwen-2.5-3b-Text_to_SQL"
torch_dtype = torch.float16  # FP16 for memory efficiency
device_map = "auto"  # Automatic GPU/CPU mapping
low_cpu_mem_usage = True  # Memory optimization
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

Athena targets are defined in `app/athena_config.py`:

```python
ATHENA_TARGETS = {
    "peninsula_incident": {
        "database": "peninsula_incident",
        "workgroup": "primary",
        "output_location": "s3://your-bucket/athena-results/"
    }
}
```

## 🔒 Security Best Practices

- **Always include `user_uuid` for production requests** to enable property-level access control
- User-level permissions are enforced at the SQL generation level
- All SQL queries are validated before execution
- Table access is strictly controlled per property
- **Cross-property queries are automatically blocked when user_uuid is provided**
- Users can ONLY access data for properties they are explicitly assigned to
- Input validation prevents XSS and SQL injection attacks
- Rate limiting prevents abuse and resource exhaustion
- All API requests are logged with full context for audit trails

## 📚 Additional Documentation

See `/documentation` folder for:
- Performance optimization guides
- Streamlit UI documentation
- Deployment procedures
- Test questions and examples

## 🆘 Troubleshooting

### Common Issues

**Problem:** 403 Forbidden - USER_PROPERTY_NOT_ALLOWED

**Solution:** Verify the user_uuid has access to the specified property_uuid in `app/user_table_permissions.py`

---

**Problem:** 400 Bad Request - Table not allowed

**Solution:** Check that the property mapping in `app/permissions_config.py` includes the required tables

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
ps aux | grep -E 'uvicorn|streamlit'
```

**Monitor resource usage:**
```bash
htop  # or top
```

## 📞 Support

For issues or questions, check logs at `logs/api_requests.json` for detailed error information.
