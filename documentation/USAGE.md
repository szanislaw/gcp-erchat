# NLQ to SQL Service - Usage Guide

This guide explains how to start and use the Natural Language Query (NLQ) to SQL translation service.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Starting the Service](#starting-the-service)
- [Using the Web GUI](#using-the-web-gui)
- [Using the API with curl](#using-the-api-with-curl)
- [API Endpoints](#api-endpoints)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

## Prerequisites

1. **Python Environment**: Python 3.8+ with required packages installed
   ```bash
   pip install -r requirements.txt
   ```

2. **AWS Credentials**: Configure AWS credentials for Athena access
   ```bash
   # Option 1: Environment variables
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_DEFAULT_REGION=us-east-1

   # Option 2: AWS CLI configuration
   aws configure

   # Option 3: Credentials file (~/.aws/credentials)
   [default]
   aws_access_key_id = your_access_key
   aws_secret_access_key = your_secret_key
   ```

3. **Model Download**: The Qwen2.5-Coder-7B-Instruct model will be downloaded automatically on first run (~4-5GB)

## Starting the Service

### Method 1: Foreground (for testing/debugging)
```bash
cd /home/shawnyzy/Documents/GitHub/gcp-erchat
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

### Method 2: Background (detached process)
```bash
cd /home/shawnyzy/Documents/GitHub/gcp-erchat
nohup uvicorn app.main:app --host 0.0.0.0 --port 8080 > logs/service.log 2>&1 &
```

### Method 3: Using systemctl (as a service)
```bash
# Install the service
sudo ./scripts/install_service.sh

# Start the service
sudo systemctl start nlq-api

# Enable auto-start on boot
sudo systemctl enable nlq-api

# Check status
sudo systemctl status nlq-api
```

### Stopping the Service
```bash
# Kill by process name
pkill -f "uvicorn app.main:app"

# Kill by port
lsof -i :8080 | grep -v COMMAND | awk '{print $2}' | xargs -r kill -9
```

## Using the Web GUI

1. **Open your browser** and navigate to:
   ```
   http://localhost:8080
   ```
   Or if accessing remotely:
   ```
   http://your-server-ip:8080
   ```

2. **Fill in the form fields:**
   - **Query Text**: Enter your question in plain English
     - Example: "Show me high severity incidents that are pending"
   - **Account UUID**: Your account identifier (default: all zeros for testing)
   - **Property UUID**: Your property identifier (default: all zeros for testing)
   - **Max Rows**: Maximum number of results to return (default: 100)
   - **Max Tokens**: Maximum tokens for SQL generation (default: 256)

3. **Query Suggestions** (optional):
   - Click "Toggle Query Suggestions" to see pre-generated example queries
   - Click any suggestion to automatically fill the query text field
   - Suggestions are organized by category (aggregation, filtering, time-based, etc.)

4. **Execute Query:**
   - Click "Execute Query" button
   - View the generated SQL and results in the response area
   - Results are displayed in a formatted table

## Using the API with curl

### Execute NLQ Query

**Basic Query:**
```bash
curl -X POST http://localhost:8080/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Show me recent incidents",
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
      "max_tokens": 256
    },
    "trace": {
      "source": "curl"
    }
  }'
```

**Severity Filtering:**
```bash
curl -X POST http://localhost:8080/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Show me high severity incidents that are still pending",
    "context": {
      "account_uuid": "00000000-0000-0000-0000-000000000000",
      "property_uuid": "00000000-0000-0000-0000-000000000000",
      "language": "en"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false, "max_rows": 50},
    "model": {"max_tokens": 256}
  }'
```

**Count Aggregation:**
```bash
curl -X POST http://localhost:8080/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "How many incidents are there by severity?",
    "context": {
      "account_uuid": "00000000-0000-0000-0000-000000000000",
      "property_uuid": "00000000-0000-0000-0000-000000000000"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false, "max_rows": 100}
  }'
```

**Date Range Query:**
```bash
curl -X POST http://localhost:8080/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Show me incidents from last week",
    "context": {
      "account_uuid": "00000000-0000-0000-0000-000000000000",
      "property_uuid": "00000000-0000-0000-0000-000000000000"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false, "max_rows": 100}
  }'
```

**Dry Run (SQL generation only, no execution):**
```bash
curl -X POST http://localhost:8080/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Show me all incidents",
    "context": {
      "account_uuid": "00000000-0000-0000-0000-000000000000",
      "property_uuid": "00000000-0000-0000-0000-000000000000"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": true}
  }'
```

### Response Format

Successful response:
```json
{
  "sql": "SELECT * FROM incident_combine WHERE severity_name = 'high' ORDER BY created_date DESC LIMIT 100",
  "data": [
    {
      "incident_id": "INC-12345",
      "severity_name": "high",
      "status_name": "pending",
      "created_date": 1704844800000
    }
  ],
  "metadata": {
    "row_count": 1,
    "execution_time_ms": 2345
  }
}
```

Error response:
```json
{
  "detail": "Error message here"
}
```

## API Endpoints

### GET /
- **Description**: Serves the web GUI
- **Response**: HTML page

### POST /nlq/execute
- **Description**: Execute natural language query
- **Request Body**: NLQ request (see curl examples above)
- **Response**: SQL, data results, and metadata

### GET /nlq/suggestions
- **Description**: Get pre-generated query suggestions based on schema
- **Response**: Array of categorized example queries
```bash
curl http://localhost:8080/nlq/suggestions
```

### GET /nlq/schema
- **Description**: Get database schema summary
- **Response**: Schema information including tables, columns, and types
```bash
curl http://localhost:8080/nlq/schema
```

### GET /logs
- **Description**: View API request logs
- **Response**: Recent API requests and their details
```bash
curl http://localhost:8080/logs
```

## Configuration

### Model Parameters
- **max_tokens**: Controls SQL generation length (default: 256, range: 64-512)
  - Lower values = faster generation
  - Higher values = more complex SQL support

### Query Execution
- **max_rows**: Limits result set size (default: 100)
- **dry_run**: Set to `true` to generate SQL without executing

### Caching
- Query results are cached in memory (100 entries max)
- Cache key is MD5 hash of query + context
- Athena result reuse enabled (60-minute window)

### Performance Optimizations Applied
- Query result caching (instant repeated queries)
- Athena ResultReuseConfiguration (reuses previous execution results)
- Exponential backoff polling (200ms → 2s)
- Reduced default token limit (512 → 256)
- Model upgraded to Qwen2.5-Coder-7B-Instruct

## Troubleshooting

### Port 8080 Already in Use
```bash
lsof -i :8080 | grep -v COMMAND | awk '{print $2}' | xargs -r kill -9
```

### AWS Credentials Error
```
ERROR: UnrecognizedClientException: The security token included in the request is invalid
```
**Solution**: Check AWS credentials configuration (see Prerequisites section)

### Model Loading Issues
```
ERROR: Model failed to load
```
**Solution**: 
- Ensure ~4-5GB of disk space available
- Check internet connection for model download
- Verify PyTorch and transformers are installed

### Empty Results
If queries return "No results returned":
- Check that string values in WHERE clauses use lowercase (e.g., 'high', not 'High')
- Verify account_uuid and property_uuid match your data
- Check date ranges are appropriate for your dataset

### Service Not Starting
```bash
# Check for errors in logs
tail -f logs/service.log

# Verify Python environment
which python
python --version

# Test imports
python -c "import fastapi, torch, transformers; print('OK')"
```

## Example Queries

### Basic Queries
- "Show me recent incidents"
- "List all high severity incidents"
- "What incidents are still pending?"

### Aggregation Queries
- "How many incidents by severity?"
- "Count incidents by status"
- "Average incidents per day"

### Time-Based Queries
- "Show me incidents from last week"
- "What happened today?"
- "Incidents created in December 2025"

### Complex Queries
- "Show me high severity incidents that are still pending"
- "List cancelled incidents with medium severity"
- "What are the most common incident categories?"

## Additional Resources

- **Query Suggestions**: See [app/query_suggestions.py](app/query_suggestions.py) for all generated examples
- **Test Questions**: See `TEST_QUESTIONS.md` for 20 evaluation queries
- **Optimization Details**: See `OPTIMIZATIONS_APPLIED.md` for performance improvements
- **API Logs**: Check `logs/api_requests.json` for request history
