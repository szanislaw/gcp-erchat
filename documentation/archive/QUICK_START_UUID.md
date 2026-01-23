# Quick Start Guide - User UUID Configuration

## 🚀 5-Minute Setup

### 1. Add Your User UUIDs

Edit `app/user_table_permissions.py`:

```python
USER_TABLE_PERMISSIONS: Dict[str, List[str]] = {
    # Replace with your actual user UUIDs
    "user-abc123...": ["incident_combine", "incident_analytics"],
    "user-def456...": ["incident_combine"],
    "user-ghi789...": ["*"],  # Admin with full access
}
```

### 2. Start the Server

```bash
./start_api.sh
```

### 3. Test It Works

```bash
curl http://localhost:8080/health
```

---

## 📝 Common User Patterns

### Pattern 1: Staff User (Limited Access)
```python
"user-staff-uuid": ["incident_combine"]
```

### Pattern 2: Manager (Full Property Access)
```python
"user-manager-uuid": [
    "incident_combine",
    "incident_history",
    "incident_analytics",
    "incident_reports"
]
```

### Pattern 3: Analyst (Analytics Only)
```python
"user-analyst-uuid": [
    "incident_analytics",
    "incident_reports"
]
```

### Pattern 4: Admin (Everything)
```python
"user-admin-uuid": ["*"]
```

---

## 🔍 Testing User Access

### Test Request Template

```bash
curl -X POST http://localhost:8080/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Show me recent incidents",
    "context": {
      "account_uuid": "YOUR-ACCOUNT-UUID",
      "property_uuid": "YOUR-PROPERTY-UUID",
      "user_uuid": "YOUR-USER-UUID",
      "language": "en"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": true, "max_rows": 10},
    "model": {},
    "trace": {}
  }'
```

### Expected Responses

**✅ Success (200):**
```json
{
  "success": true,
  "sql": {
    "query": "SELECT ...",
    "confidence": 0.95
  }
}
```

**❌ No User Permission (403):**
```json
{
  "detail": "User user-xxx does not have access to tables: ['table_name']"
}
```

**❌ User Not Found (403):**
```json
{
  "detail": "User UUID 'user-xxx' not found in table permissions"
}
```

---

## 📋 Management Commands

```bash
# Start server
./start_api.sh

# Stop server
./stop_api.sh

# Restart server (after config changes)
./restart_servers.sh

# Check if running
ps aux | grep uvicorn

# View logs
tail -f logs/api.log

# Test health
curl http://localhost:8080/health
```

---

## 🔧 Configuration Files

| File | Purpose |
|------|---------|
| `app/user_table_permissions.py` | User UUID → Table mappings |
| `app/permissions_config.py` | Account/Property permissions |
| `.env` | AWS credentials and config |
| `app/athena_config.py` | Database connection details |

---

## 📚 Full Documentation

- [USER_UUID_CONFIG.md](documentation/USER_UUID_CONFIG.md) - Complete guide
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment options
- [DISPLAY_CONFIG.md](documentation/DISPLAY_CONFIG.md) - UI display config

---

## 💡 Tips

1. **Use UUIDs with 'user-' prefix** for clarity
2. **Restart server** after changing permissions
3. **Test with dry_run: true** before production
4. **Monitor logs** for access issues
5. **Use wildcards (*) sparingly** - only for admins

---

## 🆘 Troubleshooting

| Problem | Solution |
|---------|----------|
| User not found | Add UUID to `user_table_permissions.py` |
| Access denied | Check both user AND account permissions |
| Server won't start | Check logs: `cat logs/api.log` |
| Can't connect | Verify server is running: `ps aux \| grep uvicorn` |

---

## 📞 Quick Support Checklist

Before asking for help, check:

- [ ] User UUID is in `user_table_permissions.py`
- [ ] Server is running (`ps aux | grep uvicorn`)
- [ ] Account/property UUIDs are correct
- [ ] Table names match exactly (case-insensitive)
- [ ] Server was restarted after config changes
- [ ] Logs don't show errors (`tail -f logs/api.log`)
