# NLQ → Athena SQL API

A FastAPI-based service that converts **Natural Language Queries (NLQ)** into SQL queries and executes them against AWS Athena databases using a Mistral-7B language model.

## 🎯 Overview

This API service allows users to ask questions in plain English (or other supported languages) and automatically:
1. Generates SQL queries using AI (Mistral-7B-Instruct-v0.3)
2. Validates queries for security and permissions
3. Executes queries against AWS Athena
4. Returns structured results

**Use Cases:**
- Business intelligence dashboards
- Natural language database interfaces
- Multi-tenant data analytics platforms
- Incident tracking and reporting systems

---

## 🏗️ Architecture

```
┌─────────────────┐
│   User Request  │
│  (Natural Lang) │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│      FastAPI Endpoint           │
│    (/nlq/execute)               │
└────────┬────────────────────────┘
         │
         ├─► Permissions Check (UUID-based)
         │
         ├─► Schema Loader (AWS Glue)
         │
         ├─► Prompt Builder
         │
         ▼
┌─────────────────────────────────┐
│   Mistral-7B-Instruct-v0.3      │
│   (SQL Generation)              │
└────────┬────────────────────────┘
         │
         ├─► SQL Validation & Security
         │
         ▼
┌─────────────────────────────────┐
│     AWS Athena Execution        │
│     (boto3 client)              │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│   Formatted JSON Response       │
└─────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- CUDA-compatible GPU (for model inference)
- AWS credentials with Athena and Glue access
- Conda or virtualenv

### Installation

```bash
# Clone repository
git clone https://github.com/szanislaw/gcp-erchat.git
cd gcp-erchat

# Create conda environment
conda create -n venv1 python=3.11
conda activate venv1

# Install dependencies
pip install -r requirements.txt

# Set up as systemd service (for persistent running)
chmod +x scripts/install_service.sh
./scripts/install_service.sh
```

### Manual Run (Development)
```bash
conda activate venv1
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

---

## 📡 API Endpoints

### `POST /nlq/execute`

Convert natural language to SQL and execute against Athena.

**Request:**
```json
{
  "text": "how many incidents are there?",
  "context": {
    "account_uuid": "00000000-0000-0000-0000-000000000000",
    "property_uuid": "00000000-0000-0000-0000-000000000000",
    "language": "en"
  },
  "sql": {
    "dialect": "athena"
  },
  "execution": {
    "dry_run": false,
    "max_rows": 100
  },
  "model": {
    "max_tokens": 512
  },
  "trace": {
    "source": "manual-test"
  }
}
```

**Response:**
```json
{
  "success": true,
  "sql": {
    "query": "SELECT COUNT(*) FROM incident_combine LIMIT 100",
    "confidence": 0.90
  },
  "execution": {
    "executed": true,
    "row_count": 1,
    "data": {
      "columns": ["_col0"],
      "rows": [{"_col0": "1523"}],
      "row_count": 1
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
    "request_id": "req-a1b2c3d4...",
    "latency_ms": 2345,
    "athena_target": "peninsula_incident",
    "allowed_tables": ["incident_combine"]
  }
}
```

**Display Types:**

The API automatically determines the recommended visualization type based on the query structure and results:

| Type | Description | When Used |
|------|-------------|-----------|
| `table` | Tabular display (default) | Default for all queries, complex results |
| `line` | Line chart | Time series data with ORDER BY and date/time columns |
| `bar` | Bar chart | GROUP BY with aggregations, ≤50 rows |
| `pie` | Pie chart | 2 columns, aggregation, ≤10 rows |

**Examples:**

*Time Series (Line Chart):*
```json
"display": { "type": "line" }
// Query: SELECT date, COUNT(*) FROM incidents GROUP BY date ORDER BY date
```

*Categorical (Bar Chart):*
```json
"display": { "type": "bar" }
// Query: SELECT status, COUNT(*) FROM incidents GROUP BY status
```

*Small Categories (Pie Chart):*
```json
"display": { "type": "pie" }
// Query: SELECT type, COUNT(*) FROM incidents GROUP BY type LIMIT 5
```

### `GET /logs?limit=100`

Retrieve recent API request/response logs.

**Example:**
```bash
curl http://localhost:8080/logs?limit=10
```

---

## ⚙️ Configuration

### 1. Athena Targets (`app/athena_config.py`)

Configure AWS Athena database connections. Each target represents a separate Athena database with its own AWS credentials, region, and S3 output location.

**Configuration Structure:**
```python
ATHENA_TARGETS = {
    "target_name": {
        "region": "aws-region",              # AWS region where Athena is hosted
        "database": "database-name",          # Athena database name
        "tables": ["table1", "table2"],       # List of available tables
        "s3_output": "s3://bucket/path/",     # S3 location for query results
        "aws_access_key_id": "ACCESS_KEY",
        "aws_secret_access_key": "SECRET_KEY"
    }
}
```

**Example Configuration:**
```python
ATHENA_TARGETS = {
    "peninsula_incident": {
        "region": "ap-east-1",
        "database": "peninsula-incident2",
        "tables": ["incident_combine"],
        "s3_output": "s3://athena-query-results-ap-east-1/nlq/",
        "aws_access_key_id": "YOUR_ACCESS_KEY",
        "aws_secret_access_key": "YOUR_SECRET_KEY"
    },
    "londoner_granded": {
        "region": "ap-east-1",
        "database": "londoner_granded",
        "tables": ["ldco_testing"],
        "s3_output": "s3://athena-query-results-ap-east-1/nlq/",
        "aws_access_key_id": "YOUR_ACCESS_KEY",
        "aws_secret_access_key": "YOUR_SECRET_KEY"
    }
}
```

⚠️ **Security Warning:** Store credentials in environment variables or AWS Secrets Manager for production.

**Adding a New Athena Target:**
1. Add new entry to `ATHENA_TARGETS` dictionary
2. Ensure AWS credentials have access to Athena and Glue APIs
3. Verify S3 bucket has proper write permissions for query results
4. Restart the service: `sudo systemctl restart nlq-api`

---

### 2. UUID-Based Permission System (`app/permissions.py`)

The permission system provides **multi-tenant access control** by mapping `(account_uuid, property_uuid)` pairs to allowed Athena targets and tables. This ensures users can only query databases and tables they have been explicitly granted access to.

#### **Permission Data Structure**

```python
PERMISSIONS: Dict[tuple, Dict[str, any]] = {
    (account_uuid, property_uuid): {
        "athena_targets": [list of allowed target names],
        "tables": [list of allowed table names]
    }
}
```

#### **How It Works: Request Flow**

1. **Client sends request** with account and property UUIDs:
```json
{
  "text": "how many incidents are there?",
  "context": {
    "account_uuid": "acc-123e4567-e89b-12d3-a456-426614174000",
    "property_uuid": "prop-987f6543-e21a-45d6-b789-123456789abc"
  }
}
```

2. **API looks up permissions** (`app/main.py`):
```python
access = get_allowed_access(req.context.account_uuid, req.context.property_uuid)
if access is None:
    raise HTTPException(status_code=403, detail="Access denied")
```

3. **System extracts allowed resources**:
```python
athena_target = access["athena_targets"][0]  # Currently uses first target
allowed_tables = access["tables"]            # List of allowed tables
```

4. **Schema loader fetches only allowed tables** from AWS Glue for the specified target

5. **AI model generates SQL** using only the available schema

6. **SQL validator checks** that generated query only references allowed tables:
```python
sql = validate_sql(
    result["query"],
    allowed_tables,    # Only these tables are permitted
    req.sql.dialect
)
```

7. **If validation passes**, query executes on Athena; otherwise returns 400 error

#### **Configuration Examples**

**Example 1: Single Database Access**
```python
PERMISSIONS = {
    # User can only access Peninsula incident database
    ("acc-123e4567-e89b-12d3-a456-426614174000", "prop-987f6543-e21a-45d6-b789-123456789abc"): {
        "athena_targets": ["peninsula_incident"],
        "tables": ["incident_combine"]
    }
}
```

**Example 2: Multi-Database Access**
```python
PERMISSIONS = {
    # User has access to both databases
    ("acc-345e6789-e89b-12d3-a456-426614174002", "prop-765f4321-e21a-45d6-b789-123456789ghi"): {
        "athena_targets": ["peninsula_incident", "londoner_granded"],
        "tables": ["incident_combine", "ldco_testing"]
    }
}
```

**Example 3: Multiple Tables in Same Database**
```python
PERMISSIONS = {
    # User can query multiple tables in peninsula_incident database
    ("acc-456e7890-e89b-12d3-a456-426614174003", "prop-654f3210-e21a-45d6-b789-123456789jkl"): {
        "athena_targets": ["peninsula_incident"],
        "tables": ["incident_combine", "user_logs", "audit_trail"]
    }
}
```

**Example 4: Super User (Current Default)**
```python
PERMISSIONS = {
    # All-zeros UUID has full access to everything
    ("00000000-0000-0000-0000-000000000000", "00000000-0000-0000-0000-000000000000"): {
        "athena_targets": ["peninsula_incident", "londoner_granded"],
        "tables": ["incident_combine", "ldco_testing"]
    }
}
```

#### **Adding New Permissions**

**Step 1:** Edit `app/permissions.py`
```python
PERMISSIONS = {
    # Existing entries...
    
    # Add new account/property pair
    ("your-account-uuid", "your-property-uuid"): {
        "athena_targets": ["peninsula_incident"],
        "tables": ["incident_combine"]
    }
}
```

**Step 2:** Restart the service
```bash
sudo systemctl restart nlq-api
```

**Step 3:** Test with curl
```bash
curl -X POST http://localhost:8080/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "show me recent incidents",
    "context": {
      "account_uuid": "your-account-uuid",
      "property_uuid": "your-property-uuid",
      "language": "en"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false, "max_rows": 10},
    "model": {"max_tokens": 512},
    "trace": {"source": "test"}
  }'
```

#### **Permission Validation Logic**

The system performs two levels of validation:

**Level 1: UUID Lookup** (`app/permissions.py::get_allowed_access()`)
- Checks if `(account_uuid, property_uuid)` exists in `PERMISSIONS`
- Returns `None` if not found → Results in **403 Forbidden**

**Level 2: Table Validation** (`app/security.py::validate_sql()`)
- Extracts table names from generated SQL using regex
- Compares against `allowed_tables` list
- Raises `ValueError` if unauthorized table detected → Results in **400 Bad Request**

**Validation Flow:**
```python
# Extract tables from SQL
tables = re.findall(r"from\s+([a-zA-Z_][\w]*)", sql, re.I)

# Check each table
for table in tables:
    if table not in allowed_tables:
        raise ValueError(f"Table not allowed: {table}")
```

#### **Current Limitations**

1. **Static Configuration**: Requires code changes and service restart to update permissions
2. **First Target Only**: When multiple `athena_targets` are allowed, system uses first one
3. **No Role Hierarchy**: No concept of admin/user roles - access is binary (allowed/denied)
4. **No Time-Based Access**: No expiration or time-based restrictions
5. **No Audit Trail**: Permission checks are logged but not persisted long-term

#### **Future Enhancements (Recommendations)**

1. **Database-backed permissions**: Store in PostgreSQL/DynamoDB for dynamic updates
2. **API for permission management**: CRUD endpoints for managing access
3. **Multi-target query support**: Allow queries across multiple databases
4. **Role-based access control (RBAC)**: Implement user roles with inherited permissions
5. **Column-level permissions**: Restrict access to specific columns within tables
6. **Row-level security**: Filter results based on user context (e.g., only show user's own data)

---

### 3. Supported Languages (`app/models.py`)

The API accepts language context in requests to potentially customize prompts or responses.

**Currently Supported:**
- `en` - English
- `zh` - Chinese (Mandarin)
- `ms` - Malay
- `ta` - Tamil

**Usage in Request:**
```json
{
  "context": {
    "language": "en"
  }
}
```

⚠️ **Note:** While the API accepts these language codes, **prompts are currently only generated in English**. The AI model (Mistral-7B) primarily understands English, though it has some multilingual capabilities.

**To implement multilingual support:**
1. Modify `app/prompt.py::build_prompt()` to include language-specific templates
2. Translate schema descriptions and semantic hints
3. Consider using a multilingual model for better non-English support

---

## 🛠️ Technical Architecture & Development

### Project Structure
```
sqlcoder-src/
├── app/
│   ├── main.py              # FastAPI app & endpoints
│   ├── sqlcoder.py          # Mistral model inference
│   ├── prompt.py            # Prompt engineering
│   ├── schema_loader.py     # AWS Glue schema fetching
│   ├── security.py          # SQL validation
│   ├── permissions.py       # Access control
│   ├── athena_client.py     # AWS Athena execution
│   ├── athena_config.py     # Athena connection configs
│   ├── models.py            # Pydantic request models
│   ├── request_logger.py    # API logging (last 100 requests)
│   ├── display_hint.py      # Display type detection
│   └── utils.py             # Helper functions
├── scripts/
│   ├── install_service.sh   # Install systemd service
│   ├── kill_restart.sh      # Kill & restart manually
│   ├── start_detached.sh    # Run in screen session
│   ├── start_background.sh  # Run with nohup
│   └── nlq-api.service      # Systemd service config
├── logs/
│   ├── api_requests.json    # API request/response logs
│   ├── uvicorn.log          # Service stdout logs
│   └── uvicorn_error.log    # Service stderr logs
├── clis/
│   └── curl-request-template.txt
├── requirements.txt
└── README.md
```

---

### Detailed Component Documentation

#### **1. Main API (`app/main.py`)**

**Purpose:** FastAPI application with endpoints and request orchestration

**Key Functions:**
- `execute(req: NLQRequest)` - Main endpoint handling NLQ-to-SQL conversion
- `view_logs(limit: int)` - Retrieves recent API logs

**Request Processing Flow:**
```python
1. Parse and validate request (Pydantic models)
2. Generate or extract request_id
3. Check permissions (UUID-based lookup)
4. Build prompt with schema context
5. Generate SQL using Mistral model
6. Validate SQL for security and permissions
7. Execute on Athena (if not dry_run)
8. Determine display type (if executed)
9. Format response
10. Log request/response
11. Return formatted JSON
```

**Error Handling:**
- `HTTPException(403)` - Permission denied
- `HTTPException(400)` - Invalid SQL, validation errors, execution failures
- All errors are logged with full context

**Response Format:**
```python
PrettyJSONResponse  # Custom class with 2-space indentation
```

---

#### **2. AI Model Layer (`app/sqlcoder.py`)**

**Purpose:** Manages Mistral-7B model loading and inference

**Key Functions:**

**`load_model()`**
- Loads model on first API request (lazy loading)
- Uses `torch.float16` for memory efficiency
- Applies `device_map="auto"` for automatic GPU allocation
- Sets model to evaluation mode

**Model Configuration:**
```python
model_name = "mistralai/Mistral-7B-Instruct-v0.3"
torch_dtype = torch.float16
device_map = "auto"  # Automatically uses available GPU
```

**`run_sqlcoder(prompt: str, max_tokens: int)`**
- Formats prompt using Mistral's chat template
- Generates SQL with `do_sample=False` (deterministic output)
- Returns: `{query, confidence, latency_ms, explanation}`

**`extract_sql(text: str)`**
- Removes markdown code fences (```sql, ```)
- Extracts SELECT statements using regex
- Auto-adds `LIMIT 100` if not present
- Handles multiple SQL statements (takes first SELECT)

**Regex Pattern:**
```python
SELECT_REGEX = re.compile(
    r"(select\s+.*?)(;|\Z)",
    re.IGNORECASE | re.DOTALL
)
```

**Performance:**
- **Cold start**: 30-60 seconds (model loading)
- **Warm inference**: 2-5 seconds per query
- **Memory**: ~14GB VRAM (FP16)
- **Hardware**: Tested on NVIDIA T4 GPU

**Known Issues:**
- Confidence score is hardcoded to 0.90 (not calculated)
- Model name mismatch (uses Mistral, not actual SQLCoder)
- No temperature control (always deterministic)

---

#### **3. Prompt Engineering (`app/prompt.py`)**

**Purpose:** Constructs prompts with schema context for SQL generation

**`build_prompt(text, context, sql, athena_target)`**

**Prompt Structure:**
```
1. System role definition
2. Strict rules (output format, syntax requirements)
3. Table schemas (from AWS Glue)
4. Semantic hints (domain-specific guidance)
5. User's natural language query
6. Output instruction
```

**Schema Integration:**
```python
schema = load_schema(athena_target)  # Fetch from Glue
schema_text = compress_schema(schema)  # Format for prompt
```

**Semantic Hints:**
- Guides model on column usage (e.g., timestamp vs. string dates)
- Provides context for ambiguous queries
- Explains partition columns for query optimization

**Example Prompt Output:**
```
You are an expert SQL generator for AWS Athena (PrestoSQL).

STRICT RULES:
- Output ONLY the SQL query, nothing else
- Use PrestoSQL syntax ONLY
- Use ONLY the columns listed below
- ALWAYS include LIMIT 100

Available tables and schemas:
- incident_combine: columns [id (bigint), title (string), ...]; partitions [year]

Semantic hints:
- For "most recent", prefer bigint timestamp columns

Generate a SQL query for this request:
how many incidents are there?

Return only the SQL query:
```

**Customization Points:**
- Add domain-specific hints in prompt template
- Adjust output format requirements
- Include example queries (few-shot learning)

---

#### **4. Schema Management (`app/schema_loader.py`)**

**Purpose:** Fetches and caches table schemas from AWS Glue

**Key Functions:**

**`load_schema(target_name: str)`**
- Retrieves table definitions from AWS Glue Data Catalog
- Caches results in `_SCHEMA_CACHE` (in-memory, persistent across requests)
- Returns structured schema dictionary

**Schema Structure:**
```python
{
    "table_name": {
        "columns": [
            {"name": "column_name", "type": "data_type"}
        ],
        "partitions": [
            {"name": "partition_key", "type": "data_type"}
        ]
    }
}
```

**`compress_schema(schema: Dict)`**
- Converts schema to compact, prompt-friendly string
- Format: `table: columns [col1 (type), col2 (type)]; partitions [p1, p2]`

**AWS Glue Integration:**
```python
glue = boto3.client("glue", region_name, aws_access_key_id, aws_secret_access_key)
resp = glue.get_table(DatabaseName=database, Name=table_name)
```

**Caching Behavior:**
- **Cache hit**: Instant (no API call)
- **Cache miss**: 100-500ms (Glue API call)
- **Cache lifetime**: Until service restart
- **No automatic refresh**: Schema changes require restart

**Performance Optimization:**
```python
# Cache prevents repeated Glue API calls
if target_name in _SCHEMA_CACHE:
    return _SCHEMA_CACHE[target_name]  # O(1) lookup
```

**Limitations:**
- No cache invalidation mechanism
- All tables loaded at once (no lazy loading per table)
- No schema versioning or change detection

---

#### **5. Security Layer (`app/security.py`)**

**Purpose:** Validates SQL queries to prevent malicious operations

**`validate_sql(sql: str, allowed_tables: List[str], dialect: str)`**

**Security Checks:**

**1. SQL Injection Prevention**
```python
FORBIDDEN = re.compile(r"\b(drop|delete|update|insert|alter|truncate)\b", re.I)
if FORBIDDEN.search(sql):
    raise ValueError("Forbidden SQL operation")
```

**2. Athena Compatibility**
```python
ATHENA_UNSUPPORTED = ["distinct on", "returning"]
for kw in ATHENA_UNSUPPORTED:
    if kw in sql.lower():
        raise ValueError(f"Athena does not support: {kw}")
```

**3. Table Access Control**
```python
tables = re.findall(r"from\s+([a-zA-Z_][\w]*)", sql, re.I)
for t in tables:
    if t not in allowed_tables:
        raise ValueError(f"Table not allowed: {t}")
```

**Validation Flow:**
```
Input SQL → Empty check → Forbidden operations → Dialect checks → Table validation → Return validated SQL
```

**Blocked Operations:**
- `DROP` - Prevent table/database deletion
- `DELETE` - No data deletion
- `UPDATE` - No data modification
- `INSERT` - No data insertion
- `ALTER` - No schema changes
- `TRUNCATE` - No table truncation

**Allowed Operations:**
- `SELECT` - Read-only queries
- `WITH` - Common Table Expressions (CTEs)
- Aggregate functions (`COUNT`, `SUM`, `AVG`, etc.)
- Joins (`INNER`, `LEFT`, `RIGHT`, `FULL`)
- Subqueries

**Known Limitations:**
- Simple regex-based detection (can be bypassed with obfuscation)
- No detection of expensive queries (CROSS JOIN, Cartesian products)
- No query complexity analysis
- No resource limits enforcement (handled by Athena)

**Security Recommendations:**
1. Implement query cost estimation before execution
2. Add rate limiting per UUID
3. Set up AWS Athena workgroup query limits
4. Monitor for anomalous query patterns

---

#### **6. Athena Client (`app/athena_client.py`)**

**Purpose:** Executes SQL queries on AWS Athena and retrieves results

**Key Functions:**

**`get_client(target_name: str)`**
- Creates and caches boto3 Athena clients
- One client per target (connection pooling)

**`execute_query(sql, target_name, max_rows)`**

**Execution Flow:**
```python
1. Validate SQL starts with SELECT
2. Start async query execution
3. Poll for completion (0.5s intervals)
4. Retrieve results
5. Normalize to JSON format
6. Return structured data
```

**Query Execution:**
```python
response = client.start_query_execution(
    QueryString=sql,
    QueryExecutionContext={"Database": database},
    ResultConfiguration={"OutputLocation": s3_output}
)
query_execution_id = response["QueryExecutionId"]
```

**Status Polling:**
```python
while True:
    status = client.get_query_execution(QueryExecutionId=id)["Status"]["State"]
    if status == "SUCCEEDED": return
    if status in ("FAILED", "CANCELLED"): raise RuntimeError
    time.sleep(0.5)  # Poll every 500ms
```

**Result Normalization:**
```python
{
    "columns": ["col1", "col2", "col3"],
    "rows": [
        {"col1": "value1", "col2": "value2", "col3": "value3"},
        ...
    ],
    "row_count": N
}
```

**Performance Characteristics:**
- **Query startup**: 1-3 seconds (Athena cold start)
- **Polling overhead**: 500ms per check
- **Result retrieval**: 100ms-1s (depends on data size)
- **Total latency**: 3-10 seconds typical

**Error Handling:**
- Query timeout: Handled by Athena (configurable in workgroup)
- Failed queries: Raises `RuntimeError` with Athena error message
- Network issues: boto3 retries with exponential backoff

**Client Caching:**
```python
_ATHENA_CLIENTS: Dict[str, Any] = {}  # Global cache
```

**Limitations:**
- No connection pooling (single client per target)
- Synchronous polling (blocks during execution)
- No query cancellation mechanism exposed
- No streaming results (all results loaded to memory)

---

#### **7. Request Logging (`app/request_logger.py`)**

**Purpose:** Persistent logging of API requests and responses

**Key Features:**
- Stores last 100 requests in `logs/api_requests.json`
- Thread-safe file operations
- Includes full request/response payloads
- Timestamps in ISO 8601 format (UTC)

**`log_request(...)`**
```python
log_entry = {
    "timestamp": "2025-12-21T15:30:45.123456Z",
    "request_id": "req-uuid",
    "status_code": 200,
    "request": {full_request_payload},
    "response": {full_response_payload},
    "error": None  # or error message
}
```

**File Management:**
- Automatic rotation (keeps only last 100 entries)
- Thread-safe writes using `threading.Lock()`
- Auto-creates log directory if missing

**`get_logs(limit: int)`**
- Returns most recent entries (newest first)
- Exposed via `/logs` endpoint
- Default limit: 100, max: 100

**Log File Structure:**
```json
[
  {
    "timestamp": "2025-12-21T15:30:45Z",
    "request_id": "req-a1b2c3d4",
    "status_code": 200,
    "request": {...},
    "response": {...},
    "error": null
  },
  ...
]
```

**Thread Safety:**
```python
_file_lock = threading.Lock()

with _file_lock:
    logs = _read_logs_from_file()
    logs.append(log_entry)
    _write_logs_to_file(logs)
```

**Privacy Considerations:**
- Logs contain full payloads (may include sensitive data)
- No automatic PII redaction
- No encryption at rest
- Consider implementing log sanitization for production

---

#### **8. Display Type Detection (`app/display_hint.py`)**

**Purpose:** Automatically determines recommended visualization type for query results

**Key Function:**

**`get_display_type(sql: str, execution_data: Dict)`**
- Analyzes SQL query patterns and result structure
- Returns visualization type hint for frontend

**Display Types:**
- `"table"` - Default tabular display (all queries)
- `"line"` - Time series data (date/time columns + ORDER BY)
- `"bar"` - Categorical aggregations (GROUP BY + aggregation, ≤50 rows)
- `"pie"` - Small category sets (2 columns, aggregation, ≤10 rows)

**Detection Heuristics:**

**Line Chart Detection:**
```python
# Looks for:
- Date/time related column names (date, time, year, month, created, updated)
- ORDER BY clause in SQL
- Time-related keywords in query
```

**Bar Chart Detection:**
```python
# Looks for:
- GROUP BY clause
- Aggregation functions (COUNT, SUM, AVG, etc.)
- Row count ≤ 50 (reasonable for bar display)
```

**Pie Chart Detection:**
```python
# Looks for:
- Exactly 2 columns
- Aggregation functions
- Row count ≤ 10 (small category sets)
```

**Implementation Details:**

**Helper Functions:**
- `_is_time_series(sql, columns)` - Detects time-based queries
- `_has_group_by(sql)` - Checks for GROUP BY clause
- `_has_aggregation(sql)` - Checks for aggregation functions

**Regex Patterns:**
```python
# Time patterns
r'\bdate\b', r'\btime\b', r'\btimestamp\b', 
r'\byear\b', r'\bmonth\b', r'\bday\b'

# Aggregation patterns
r'\bcount\s*\(', r'\bsum\s*\(', r'\bavg\s*\(',
r'\bmin\s*\(', r'\bmax\s*\('

# GROUP BY pattern
r'\bgroup\s+by\b'
```

**Usage in API Flow:**
```python
# After query execution
if executed and execution_data:
    display_type = get_display_type(sql, execution_data)
    response["display"] = {"type": display_type}
```

**Examples:**

*Query:* `SELECT COUNT(*) FROM incidents`
*Result:* `{"type": "table"}` (default)

*Query:* `SELECT date, COUNT(*) FROM incidents GROUP BY date ORDER BY date`
*Result:* `{"type": "line"}` (time series detected)

*Query:* `SELECT status, COUNT(*) FROM incidents GROUP BY status`
*Result:* `{"type": "bar"}` (categorical aggregation)

*Query:* `SELECT category, COUNT(*) FROM incidents GROUP BY category LIMIT 5`
*Result:* `{"type": "pie"}` (small categories)

**Current Limitations:**
- Hardcoded heuristics (not ML-based)
- No user preference override
- Simple pattern matching (can be fooled)
- No multi-series detection
- No consideration of data types (all detected via query structure)

**Future Enhancements:**
- Allow client to override display type
- Support combined visualizations (e.g., bar + line)
- ML-based classification of result patterns
- Column data type analysis for better detection
- Support for more chart types (scatter, area, heatmap)

---

### Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                        CLIENT REQUEST                         │
│  {text, context: {account_uuid, property_uuid}, ...}         │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │   FastAPI Endpoint Validation │
         │   (Pydantic models)           │
         └───────────┬───────────────────┘
                     │
                     ▼
         ┌───────────────────────────────┐
         │   Permission Lookup           │
         │   permissions.py              │
         │   (account_uuid, property_uuid)│
         └───────────┬───────────────────┘
                     │
         ┌───────────┴───────────┐
         │ Found?                │
         └───────────┬───────────┘
                     │
        NO ┌─────────┴─────────┐ YES
           │                   │
           ▼                   ▼
    ┌──────────┐    ┌──────────────────────┐
    │ 403      │    │ Extract allowed      │
    │ Forbidden│    │ - athena_targets[0]  │
    └──────────┘    │ - tables[]           │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Load Schema          │
                    │ schema_loader.py     │
                    │ (AWS Glue API)       │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Build Prompt         │
                    │ prompt.py            │
                    │ + schema context     │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ AI Model Inference   │
                    │ sqlcoder.py          │
                    │ Mistral-7B           │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Extract SQL          │
                    │ (regex + cleanup)    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Validate SQL         │
                    │ security.py          │
                    │ - Check forbidden ops│
                    │ - Validate tables    │
                    └──────────┬───────────┘
                               │
                  ┌────────────┴────────────┐
                  │ Valid?                  │
                  └────────────┬────────────┘
                               │
              NO ┌─────────────┴─────────┐ YES
                 │                       │
                 ▼                       ▼
          ┌──────────┐        ┌─────────────────┐
          │ 400 Bad  │        │ dry_run?        │
          │ Request  │        └────────┬────────┘
          └──────────┘                 │
                              NO ┌─────┴─────┐ YES
                                 │           │
                                 ▼           ▼
                      ┌──────────────┐  ┌─────────────┐
                      │ Execute SQL  │  │ Skip exec   │
                      │ athena_client│  └──────┬──────┘
                      │ (boto3)      │         │
                      └──────┬───────┘         │
                             │                 │
                             ▼                 │
                      ┌──────────────┐         │
                      │ Poll Results │         │
                      └──────┬───────┘         │
                             │                 │
                             └────────┬────────┘
                                      │
                                      ▼
                           ┌──────────────────┐
                           │ Format Response  │
                           │ (PrettyJSON)     │
                           └────────┬─────────┘
                                    │
                                    ▼
                           ┌──────────────────┐
                           │ Log Request      │
                           │ request_logger.py│
                           └────────┬─────────┘
                                    │
                                    ▼
                           ┌──────────────────┐
                           │ Return to Client │
                           └──────────────────┘
```

---

## 🔧 Systemd Service Management

The API runs as a persistent systemd service that survives SSH disconnections and reboots.

### Service Commands

```bash
# Restart service
sudo systemctl restart nlq-api

# Check status
sudo systemctl status nlq-api

# Stop service
sudo systemctl stop nlq-api

# Start service
sudo systemctl start nlq-api

# View live logs
sudo journalctl -u nlq-api -f

# View recent logs (last 100 lines)
sudo journalctl -u nlq-api -n 100

# Disable auto-start on boot
sudo systemctl disable nlq-api

# Re-enable auto-start
sudo systemctl enable nlq-api
```

### Service Features
- ✅ Auto-restart on failure
- ✅ Starts on system boot
- ✅ Runs in background (detached from terminal)
- ✅ Logs to `logs/uvicorn.log` and `logs/uvicorn_error.log`

---

## 🧪 Testing

### Example cURL Request
```bash
curl -X POST http://localhost:8080/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "how many incidents are there?",
    "context": {
      "account_uuid": "00000000-0000-0000-0000-000000000000",
      "property_uuid": "00000000-0000-0000-0000-000000000000",
      "language": "en"
    },
    "sql": {
      "dialect": "athena"
    },
    "execution": {
      "dry_run": false,
      "max_rows": 100
    },
    "model": {
      "max_tokens": 512
    },
    "trace": {
      "source": "manual-test"
    }
  }'
```

### Dry Run Mode
Set `"dry_run": true` to generate SQL without executing:
```json
{
  "execution": {
    "dry_run": true
  }
}
```

---

## 🔒 Security Considerations

### ⚠️ Current Issues (Must Fix for Production)

1. **Hardcoded AWS Credentials**
   - Credentials are in `app/athena_config.py`
   - **Action Required:** Move to environment variables or AWS Secrets Manager

2. **Super-User Access**
   - All-zeros UUID (`00000000-0000-0000-0000-000000000000`) has full access
   - **Action Required:** Configure real account/property UUIDs

3. **No Authentication**
   - API has no authentication layer
   - **Action Required:** Add API keys, OAuth, or JWT tokens

4. **Request Logging Privacy**
   - Logs contain full payloads (may include sensitive data)
   - **Action Required:** Implement PII filtering or encryption

### Built-in Security Features
- ✅ SQL injection prevention (blocks DML/DDL operations)
- ✅ Table access control per UUID
- ✅ Query validation before execution
- ✅ Read-only operations (SELECT only)

---

## 📊 Model Information

**Current Model:** `mistralai/Mistral-7B-Instruct-v0.3`
- **Type:** General-purpose instruction-following LLM
- **Parameters:** 7 billion
- **Precision:** FP16
- **Hardware:** Requires GPU (tested on T4)

**Note:** Originally designed for `defog/sqlcoder-7b-2`, but currently uses Mistral. SQLCoder may provide better SQL-specific performance.

---

## 🌐 Supported SQL Dialects

Currently supports:
- **Athena (PrestoSQL)** - AWS Athena dialect

Blocked features:
- `DISTINCT ON`
- `RETURNING` clause

---

## 📝 Logging

### API Request Logs
Location: `logs/api_requests.json`
- Stores last 100 requests/responses
- Includes timestamps, request IDs, and full payloads

### Service Logs
Locations:
- `logs/uvicorn.log` - Standard output
- `logs/uvicorn_error.log` - Error output

View with:
```bash
tail -f logs/uvicorn.log
sudo journalctl -u nlq-api -f
```

---

## 🔄 Version History

**v0.4-prototype** (Current - December 21, 2025)
- Added automatic display type detection (table, line, bar, pie)
- Simplified response format with `display.type` field
- Enhanced technical documentation in README

**v0.3-prototype** (December 19, 2025)
- FastAPI-based architecture
- Mistral-7B model integration
- AWS Athena execution
- Systemd service support
- Pretty-formatted JSON responses
- Request logging (last 100 entries)
- Comprehensive UUID-based permission system
