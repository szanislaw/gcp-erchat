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

### `GET /logs?limit=100`

Retrieve recent API request/response logs.

**Example:**
```bash
curl http://localhost:8080/logs?limit=10
```

---

## ⚙️ Configuration

### 1. Athena Targets (`app/athena_config.py`)

Configure AWS Athena database connections:

```python
ATHENA_TARGETS = {
    "peninsula_incident": {
        "region": "ap-east-1",
        "database": "peninsula-incident2",
        "tables": ["incident_combine"],
        "s3_output": "s3://athena-query-results-ap-east-1/nlq/",
        "aws_access_key_id": "YOUR_ACCESS_KEY",
        "aws_secret_access_key": "YOUR_SECRET_KEY"
    }
}
```

⚠️ **Security Warning:** Store credentials in environment variables or AWS Secrets Manager for production.

### 2. Permissions (`app/permissions.py`)

Map account/property UUIDs to allowed Athena targets:

```python
PERMISSIONS = {
    ("account-uuid-123", "property-uuid-456"): {
        "athena_targets": ["peninsula_incident"],
        "tables": ["incident_combine"]
    }
}
```

### 3. Supported Languages (`app/models.py`)

Currently accepts: `en`, `zh`, `ms`, `ta` (English, Chinese, Malay, Tamil)

---

## 🛠️ Development

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
│   └── utils.py             # Helper functions
├── scripts/
│   ├── install_service.sh   # Install systemd service
│   ├── kill_restart.sh      # Kill & restart manually
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

### Key Components

**1. Model Loading (`sqlcoder.py`)**
- Loads Mistral-7B-Instruct-v0.3 on first request
- Uses FP16 precision for GPU efficiency
- Extracts SQL via regex pattern matching
- Auto-adds `LIMIT 100` if missing

**2. Security Validation (`security.py`)**
- Blocks: DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE
- Validates table access against permissions
- Checks Athena-specific syntax compatibility

**3. Schema Awareness (`schema_loader.py`)**
- Fetches table schemas from AWS Glue
- Caches schemas in memory
- Provides column names and types to model

**4. Request Logging (`request_logger.py`)**
- Stores last 100 API requests to `logs/api_requests.json`
- Includes full request/response payloads
- Thread-safe file operations

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

## 🚦 Deployment Checklist

- [ ] Move AWS credentials to environment variables
- [ ] Configure real account/property UUIDs in permissions
- [ ] Add API authentication (API keys/JWT)
- [ ] Set up HTTPS/TLS (nginx reverse proxy)
- [ ] Configure firewall rules (only allow necessary ports)
- [ ] Implement log rotation and retention policies
- [ ] Set up monitoring and alerting
- [ ] Configure backup strategy for logs
- [ ] Test with production-like data volumes
- [ ] Document API rate limits

---

## 🤝 Contributing

1. Modify code in `app/` directory
2. Test changes locally: `uvicorn app.main:app --reload`
3. Restart service: `sudo systemctl restart nlq-api`
4. Check logs: `sudo journalctl -u nlq-api -f`

---

## 📄 License

[Specify your license here]

---

## 📞 Support

For issues or questions:
- Check logs: `sudo journalctl -u nlq-api -n 100`
- View API logs: `http://your-server:8080/logs`
- Review recent requests in `logs/api_requests.json`

---

## 🔄 Version History

**v0.3-prototype** (Current)
- FastAPI-based architecture
- Mistral-7B model integration
- AWS Athena execution
- Systemd service support
- Pretty-formatted JSON responses
- Request logging (last 100 entries)
