# User UUID Configuration Guide

## Overview

This guide explains how to configure user-level table access control in the NLQ API system.

## Table Access Control Architecture

The system implements **two-level access control**:

```
┌─────────────────────────────────────────────────────────────┐
│                    Access Request                            │
│  (account_uuid, property_uuid, user_uuid, query)            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│           Level 1: Account/Property Permissions              │
│         (app/permissions_config.py)                          │
│                                                               │
│  • Controls which databases the account can access           │
│  • Controls which tables are available to the account        │
│  • Required for all requests                                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼ PASS
                         │
┌─────────────────────────────────────────────────────────────┐
│           Level 2: User Table Permissions                    │
│         (app/user_table_permissions.py)                      │
│                                                               │
│  • Controls which specific tables each user can query        │
│  • Optional - only checked if user_uuid is provided          │
│  • Provides fine-grained access within an account            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼ PASS
                         │
                  ┌──────┴──────┐
                  │  SQL Query  │
                  │  Execution  │
                  └─────────────┘
```

## Configuration Files

### 1. Account/Property Permissions (`app/permissions_config.py`)

Defines broad access control at the account and property level:

```python
PERMISSIONS_MAPPING: Dict[tuple, Dict[str, any]] = {
    ("account_uuid", "property_uuid"): {
        "athena_targets": ["database_name"],
        "tables": ["table1", "table2", "table3"]
    },
}
```

### 2. User Table Permissions (`app/user_table_permissions.py`)

Defines granular table access for individual users:

```python
USER_TABLE_PERMISSIONS: Dict[str, List[str]] = {
    "user_uuid": ["table1", "table2"],
}
```

---

## Adding New Users

### Step 1: Get User UUIDs

Collect the UUIDs of users who need access. UUIDs should follow the format:
- Standard: `user-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- Or: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

### Step 2: Determine Table Access

Identify which tables each user should have access to:

| User Role | Typical Tables | Access Level |
|-----------|---------------|--------------|
| **Admin** | `["*"]` | All tables (wildcard) |
| **Manager** | Analytics + Core | Read/Write |
| **Analyst** | Analytics only | Read-only |
| **Staff** | Core tables only | Limited read |

### Step 3: Edit `app/user_table_permissions.py`

Add user entries to the `USER_TABLE_PERMISSIONS` dictionary:

```python
USER_TABLE_PERMISSIONS: Dict[str, List[str]] = {
    # ===== ADMINS =====
    "user-00000000-0000-0000-0000-000000000000": [
        "*"  # Full access to all tables
    ],
    
    # ===== MANAGERS =====
    "user-YOUR-MANAGER-UUID-HERE": [
        "incident_combine",        # Core incident data
        "incident_history",        # Historical records
        "incident_analytics",      # Analytics views
        "incident_reports"         # Generated reports
    ],
    
    # ===== ANALYSTS =====
    "user-YOUR-ANALYST-UUID-HERE": [
        "incident_analytics",      # Analytics only
        "incident_reports"         # Reports only
    ],
    
    # ===== STAFF =====
    "user-YOUR-STAFF-UUID-HERE": [
        "incident_combine"         # Basic incident data only
    ],
}
```

### Step 4: Update Table Metadata (Optional)

Add metadata for new tables:

```python
TABLE_METADATA: Dict[str, Dict[str, str]] = {
    "your_new_table": {
        "database": "database_name",
        "description": "Table description",
        "category": "incidents|analytics|reports",
        "access_level": "standard|analyst|manager"
    },
}
```

### Step 5: Restart the Server

```bash
# Stop current server
./stop_api.sh

# Start with new configuration
./start_api.sh

# Or use restart script
./restart_servers.sh
```

---

## Example Configurations

### Example 1: Hotel Property Structure

```python
# Peninsula Hotel Users
USER_TABLE_PERMISSIONS = {
    # Peninsula Manager
    "user-123e4567-e89b-12d3-a456-426614174000": [
        "incident_combine",
        "incident_history",
        "incident_analytics",
        "incident_reports"
    ],
    
    # Peninsula Front Desk Staff
    "user-123e4567-e89b-12d3-a456-426614174001": [
        "incident_combine"  # View current incidents only
    ],
    
    # Peninsula Maintenance
    "user-123e4567-e89b-12d3-a456-426614174002": [
        "incident_combine",
        "maintenance_tasks"
    ],
}
```

### Example 2: Multi-Property Regional Manager

```python
# Regional manager with access to multiple properties
"user-regional-manager-uuid": [
    "incident_combine",        # Peninsula incidents
    "incident_analytics",      # Peninsula analytics
    "ldco_testing",           # Londoner incidents
    "ldco_analytics"          # Londoner analytics
],
```

### Example 3: Corporate Analytics Team

```python
# Analytics team - read-only analytics across all properties
"user-analytics-team-uuid": [
    "incident_analytics",      # Peninsula
    "incident_reports",        # Peninsula
    "ldco_analytics",         # Londoner
    "ldco_reports"            # Londoner
],
```

---

## Testing User Access

### Test 1: Verify User Has Access

```bash
curl -X POST http://localhost:8080/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Show me recent incidents",
    "context": {
      "account_uuid": "acc-12345",
      "property_uuid": "prop-67890",
      "user_uuid": "user-YOUR-UUID-HERE",
      "language": "en"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": true, "max_rows": 10},
    "model": {"name": "Ellbendls/Qwen-2.5-3b-Text_to_SQL"},
    "trace": {"source": "test"}
  }'
```

### Test 2: Verify User Access Denied

Try to query a table the user doesn't have access to:

```bash
# This should fail with 403 if user doesn't have access
curl -X POST http://localhost:8080/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Show analytics reports",
    "context": {
      "account_uuid": "acc-12345",
      "property_uuid": "prop-67890",
      "user_uuid": "user-STAFF-UUID",
      "language": "en"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": true},
    "model": {},
    "trace": {}
  }'
```

Expected error:
```json
{
  "detail": "User user-STAFF-UUID does not have access to tables: ['incident_analytics']"
}
```

---

## Bulk User Import

### Option 1: CSV Import Script

Create `scripts/import_users.py`:

```python
import csv
import json

def import_users_from_csv(csv_file):
    """Import users from CSV file"""
    users = {}
    
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            user_uuid = row['user_uuid']
            tables = row['tables'].split(',')
            users[user_uuid] = [t.strip() for t in tables]
    
    return users

# Usage:
# users = import_users_from_csv('users.csv')
# print(json.dumps(users, indent=2))
```

CSV format:
```csv
user_uuid,tables,role
user-001,incident_combine,staff
user-002,"incident_combine,incident_analytics",manager
user-003,*,admin
```

### Option 2: Database-Driven Configuration

For larger deployments, consider storing user permissions in a database:

```python
# app/user_table_permissions.py
import psycopg2

def load_user_permissions_from_db():
    """Load user permissions from database"""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT user_uuid, array_agg(table_name) as tables
        FROM user_table_permissions
        GROUP BY user_uuid
    """)
    
    permissions = {}
    for user_uuid, tables in cur.fetchall():
        permissions[user_uuid] = tables
    
    return permissions

# Load at startup
USER_TABLE_PERMISSIONS = load_user_permissions_from_db()
```

---

## Troubleshooting

### Issue: User not found error

**Error:**
```
User UUID 'user-xxx' not found in table permissions
```

**Solution:**
1. Check the user UUID format is correct
2. Verify the UUID is added to `USER_TABLE_PERMISSIONS`
3. Restart the server after making changes

### Issue: User denied access to table

**Error:**
```
User user-xxx does not have access to tables: ['table_name']
```

**Solution:**
1. Verify the table name in `USER_TABLE_PERMISSIONS`
2. Check table name spelling (case-insensitive but must match)
3. Ensure account/property level also grants access to the table

### Issue: Wildcard access not working

**Problem:** User has `["*"]` but still denied

**Solution:**
1. Verify wildcard is exactly `"*"` not `"*.*"` or other variants
2. Check account/property level permissions exist
3. Restart server to reload configuration

---

## Security Best Practices

### 1. Principle of Least Privilege
- Only grant access to tables users actually need
- Use specific table names instead of wildcards when possible
- Regularly audit and remove unnecessary permissions

### 2. Regular Access Reviews
```bash
# List all users and their access
python3 -c "
from app.user_table_permissions import USER_TABLE_PERMISSIONS
import json
print(json.dumps(USER_TABLE_PERMISSIONS, indent=2))
"
```

### 3. Audit Logging
- Monitor `logs/api_requests.json` for access patterns
- Alert on failed access attempts
- Review user access logs regularly

### 4. UUID Rotation
- Plan for UUID rotation/revocation
- Keep user UUIDs in secure configuration management
- Never expose UUIDs in client-side code

---

## Quick Reference

### Check User's Tables
```python
from app.user_table_permissions import get_user_tables
tables = get_user_tables("user-uuid")
```

### Check Specific Access
```python
from app.user_table_permissions import has_table_access
allowed = has_table_access("user-uuid", "table_name")
```

### List All Users
```python
from app.user_table_permissions import list_all_users
users = list_all_users()
```

### List All Tables
```python
from app.user_table_permissions import list_all_tables
tables = list_all_tables()
```

---

## Support

For questions or issues with user UUID configuration:
1. Check application logs: `tail -f logs/api.log`
2. Review this documentation
3. Test with example UUIDs provided in `user_table_permissions.py`
4. Contact system administrator
