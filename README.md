# Natural Language Query to SQL API

Production-ready FastAPI service that converts natural language questions into Athena SQL queries with comprehensive property-based access control.

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
  "query": "SELECT COUNT(*) as count FROM incident_combine WHERE severity_name = 'high' AND date_parse(snapshotdate, '%Y-%m-%d') >= date_add('day', -7, current_date) LIMIT 100",
  "explanation": "Query counts high severity incidents from the last 7 days",
  "tables_used": ["incident_combine"],
  "athena_target": "peninsula_incident"
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
  "query": "SELECT incident_uuid, property_name, category_name, severity_name, status_name FROM incident_combine WHERE severity_name = 'high' ORDER BY created_date DESC LIMIT 10",
  "results": [
    {
      "incident_uuid": "inc-123",
      "property_name": "The Peninsula Hong Kong",
      "category_name": "maintenance",
      "severity_name": "high",
      "status_name": "pending"
    }
  ],
  "row_count": 10,
  "execution_time_ms": 1234
}
```

#### 3. Health Check
**GET** `/health`

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-23T10:30:00Z"
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

## 📦 Dependencies

```bash
pip install -r requirements.txt
```

Key packages:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `boto3` - AWS SDK
- `pyathena` - Athena driver
- `pydantic` - Data validation
- `transformers` - NLQ model

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

## 🔒 Security Notes

- **Always include `user_uuid` for production requests** to enable property-level access control
- User-level permissions are enforced at the SQL generation level
- All SQL queries are validated before execution
- Table access is strictly controlled per property
- **Cross-property queries are automatically blocked when user_uuid is provided**
- Users can ONLY access data for properties they are explicitly assigned to

## 📚 Additional Documentation

See `/documentation` folder for:
- Performance optimization guides
- Streamlit UI documentation
- Deployment procedures
- Test questions and examples

## 🆘 Troubleshooting

**Problem:** 403 Forbidden - USER_PROPERTY_NOT_ALLOWED

**Solution:** Verify the user_uuid has access to the specified property_uuid in `app/user_table_permissions.py`

---

**Problem:** 400 Bad Request - Table not allowed

**Solution:** Check that the property mapping in `app/permissions_config.py` includes the required tables

---

**Problem:** Query returns no results

**Solution:** Verify property name matches exactly (case-sensitive). Use canonical names like "The Peninsula Hong Kong"

## 📞 Support

For issues or questions, check logs at `logs/api_requests.json` for detailed error information.
