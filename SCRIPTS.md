# Application Management Scripts

Quick reference for managing the NLQ to SQL application.

## 🚀 Primary Commands

### Start Everything
```bash
./start.sh
```
Starts both FastAPI backend and Streamlit UI with:
- ✅ Environment validation
- ✅ Credential verification
- ✅ Dependency checks
- ✅ Process management
- ✅ Automatic logging

### Stop Everything
```bash
./stop.sh
```
Gracefully stops all services and cleans up PID files.

## 📊 Monitoring

### Check Status
```bash
# Check if services are running
ps aux | grep -E "uvicorn|streamlit"

# Test API health
curl http://localhost:8000/nlq/health
```

### View Logs
```bash
# Real-time logs
tail -f logs/api.log         # FastAPI logs
tail -f logs/streamlit.log   # Streamlit logs

# View all logs
tail -f logs/*.log
```

### Check Process IDs
```bash
cat logs/api.pid        # FastAPI PID
cat logs/streamlit.pid  # Streamlit PID
```

## 🔧 Manual Management

### Start Individual Services

**FastAPI Only:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Streamlit Only:**
```bash
streamlit run streamlit_app.py --server.port 8501
```

### Stop Individual Services

**Stop FastAPI:**
```bash
pkill -f "uvicorn app.main:app"
```

**Stop Streamlit:**
```bash
pkill -f "streamlit run"
```

## 🆘 Troubleshooting

### Port Already in Use
```bash
# Find what's using port 8000
lsof -i :8000

# Kill process on port
kill $(lsof -t -i:8000)
```

### Service Won't Start
```bash
# Check logs
cat logs/api.log
cat logs/streamlit.log

# Verify credentials
python verify_credentials.py

# Check dependencies
pip install -r requirements.txt
```

### Zombie Processes
```bash
# Force kill everything
pkill -9 -f "uvicorn app.main:app"
pkill -9 -f "streamlit run"

# Clean up PID files
rm logs/*.pid

# Restart
./start.sh
```

## 📁 File Locations

| File | Purpose |
|------|---------|
| `start.sh` | Start complete application |
| `stop.sh` | Stop all services |
| `logs/api.log` | FastAPI logs |
| `logs/streamlit.log` | Streamlit logs |
| `logs/api.pid` | FastAPI process ID |
| `logs/streamlit.pid` | Streamlit process ID |
| `logs/api_requests.json` | API request audit log |
| `scripts/archive/` | Old/deprecated scripts |

## 🔐 Security Notes

- Logs are automatically created in `logs/` directory
- PID files track running processes
- All sensitive credentials are in `.env` (git-ignored)
- API requests are logged to `logs/api_requests.json`

## 📋 Archived Scripts

Old scripts moved to `scripts/archive/`:
- `start_api.sh` - Individual API starter
- `run_streamlit.sh` - Individual UI starter
- `stop_api.sh` - API stopper
- `restart_servers.sh` - Legacy restart script
- `start_background.sh` - Background starter
- `start_detached.sh` - Detached starter
- `kill_restart.sh` - Force restart
- `install_service.sh` - Systemd service installer

Use the new `start.sh` and `stop.sh` instead for simplified management.
