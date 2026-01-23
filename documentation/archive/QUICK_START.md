# Quick Start Guide

## Running the Application

### 1. Start the FastAPI Backend
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```
Backend will run on: **http://localhost:8080**

### 2. Start the Streamlit UI
```bash
./run_streamlit.sh
# OR
streamlit run streamlit_app.py --server.port 8501
```
UI will open at: **http://localhost:8501**

## Features

### 🔍 Query Interface
- Type natural language questions
- Choose between Peninsula and Londoner Grande databases
- Dry run mode to see SQL without executing
- Export results to CSV
- View data as tables or charts

### 💡 Suggestions
- Pre-built example queries for each database
- Click to use in your queries

### 📊 Schema Browser
- View table structures
- Column types and descriptions
- Sample values

### 📜 Query History
- Track all queries in the session
- Review previous results

## UUID Configuration

Quick presets in sidebar:
- **All 0s**: Super user (both databases)
- **All 1s**: Peninsula only

More UUIDs in [permissions_config.py](app/permissions_config.py)

## Database Targets

1. **peninsula_incident**
   - Database: `peninsula-incident2`
   - Table: `incident_combine`

2. **londoner_granded**
   - Database: `londoner_granded`
   - Table: `ldco_testing`

## Example Usage

1. Click "All 0s (Super)" button for authentication
2. Select "peninsula_incident" as target
3. Type: "Show me incidents from last month"
4. Click "Generate & Execute Query"
5. View results and download as CSV

## Troubleshooting

- **Connection refused**: Make sure FastAPI backend is running
- **No results**: Check UUID permissions match the target database
- **Timeout**: Try filtering to reduce query size

For more details, see [STREAMLIT_UI.md](STREAMLIT_UI.md)
