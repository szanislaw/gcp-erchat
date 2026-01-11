# Streamlit UI Guide

## Overview
The Streamlit UI provides an interactive interface for querying AWS Athena using natural language questions.

## Features

### 1. Query Interface
- **Natural language input**: Type questions in plain English
- **Database selection**: Choose between `peninsula_incident` and `londoner_granded`
- **Authentication**: Configure account and property UUIDs
- **Query options**: Dry run mode, max rows, SQL dialect selection
- **Results display**: View data as tables or charts
- **Export**: Download results as CSV

### 2. Query Suggestions
- View pre-built example queries for each database
- Click to use suggestions directly in your queries
- Organized by category (Basic Queries, Time-Based, Aggregations, etc.)

### 3. Database Schema
- Browse table structures
- View column names, types, and descriptions
- See sample values for each column

### 4. Query History
- Track all queries made during the session
- Review previous results
- Reuse successful queries

## Getting Started

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running the Application

1. **Start the FastAPI backend** (in one terminal):
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

2. **Start the Streamlit UI** (in another terminal):
```bash
./run_streamlit.sh
# OR
streamlit run streamlit_app.py --server.port 8501
```

3. **Open your browser**:
```
http://localhost:8501
```

## Usage Examples

### Basic Query
1. Select database target (e.g., `peninsula_incident`)
2. Enter UUIDs (use All 0s for super user access)
3. Type your question: "Show me all incidents from last week"
4. Click "Generate & Execute Query"

### Dry Run
1. Enable "Dry Run" checkbox
2. Enter your question
3. View the generated SQL without executing

### Using Different Databases
1. Switch between `peninsula_incident` and `londoner_granded` in the sidebar
2. Use appropriate UUIDs:
   - All 0s: Super user (both databases)
   - All 1s: Peninsula only

## Authentication UUIDs

| UUID Pattern | Access |
|-------------|--------|
| 00000000-0000-0000-0000-000000000000 | Super user (all databases) |
| 11111111-1111-1111-1111-111111111111 | Peninsula only |

See [permissions_config.py](app/permissions_config.py) for complete UUID mappings.

## Architecture

```
┌─────────────────┐
│  Streamlit UI   │
│  (Port 8501)    │
└────────┬────────┘
         │ HTTP Requests
         ▼
┌─────────────────┐
│  FastAPI Backend│
│  (Port 8080)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  AWS Athena     │
└─────────────────┘
```

## Tips

- **Performance**: Results are cached on the backend for faster repeated queries
- **Security**: SQL queries are validated and sanitized before execution
- **Large Results**: Use the max rows slider to limit result size
- **Export Data**: Click "Download as CSV" to export query results

## Troubleshooting

### "Connection Error"
- Ensure FastAPI backend is running on port 8080
- Check API_BASE_URL in streamlit_app.py

### "Authentication Failed"
- Verify UUIDs in permissions_config.py
- Use correct UUID for the target database

### "Query Timeout"
- Complex queries may take longer
- Try adding filters to reduce data size
- Check AWS Athena service status

## Customization

### Change API URL
Edit `streamlit_app.py`:
```python
API_BASE_URL = "http://your-api-url:8080"
```

### Add More UUID Presets
Add buttons in the sidebar section of `streamlit_app.py`.

### Modify Theme
Streamlit themes can be configured in `.streamlit/config.toml`.
