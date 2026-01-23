# Configuration Reference

This document provides quick reference for configuring the NLQ API system.

## Property UUIDs

| Property Name | Property UUID |
|---------------|---------------|
| The Peninsula Hong Kong | `8afe7e5e-22e5-4318-b5c7-f967fc44e81f` |
| The Peninsula Manila | `c9c29dc9-6fbb-4564-91e0-d2e18436fdf5` |
| The Peninsula Tokyo | `1ef8175a-6d1d-418e-8a51-31848b147b53` |
| The Peninsula Bangkok | `c0abc579-6ef4-47a3-8290-16cf26964aec` |

## Account UUIDs

| Account | Account UUID |
|---------|--------------|
| Peninsula Hotels Group | `149cd8f0-00e1-43a4-840b-6a54b4f857f6` |
| Manila Properties | `f706c73a-d248-4d63-a5b9-c8308ae12b07` |
| Tokyo Properties | `54126ed8-ca56-4fbc-9550-55732c572024` |
| Bangkok Properties | `5f7bf2e1-b8d4-4aa4-8d1a-e5161e39efa2` |

## Configuration Files

### 1. Account/Property Permissions (`app/permissions_config.py`)

Maps `(account_uuid, property_uuid)` to allowed databases and tables.

```python
PERMISSIONS_MAPPING = {
    (account_uuid, property_uuid): {
        "athena_targets": ["database_name"],
        "tables": ["table1", "table2"]
    }
}
```

### 2. User Permissions (`app/user_table_permissions.py`)

Maps `user_uuid` to allowed `property_uuid` list.

```python
USER_TABLE_PERMISSIONS = {
    "user-uuid-here": ["property-uuid-they-can-access"]
}
```

### 3. Athena Configuration (`app/athena_config.py`)

Database connection details.

```python
ATHENA_TARGETS = {
    "peninsula_incident": {
        "database": "peninsula-incident2",
        "bucket": "s3://your-bucket/",
        "workgroup": "primary"
    }
}
```

## Adding New Users - Step by Step

### Step 1: Get User Details
You need:
- `user_uuid` - Unique identifier for the user
- `property_uuid` - Which property they should access
- `account_uuid` - Their account identifier

### Step 2: Add to User Permissions
Edit `app/user_table_permissions.py`:

```python
USER_TABLE_PERMISSIONS = {
    # ... existing entries ...
    
    # New user
    "new-user-uuid-here": ["property-uuid-here"]
}
```

### Step 3: Verify Account/Property Mapping Exists
Check `app/permissions_config.py` has the account/property pair:

```python
PERMISSIONS_MAPPING = {
    ("account-uuid", "property-uuid"): {
        "athena_targets": ["peninsula_incident"],
        "tables": ["incident_combine", "incident_history"]
    }
}
```

If not, add it.

### Step 4: Restart Service

```bash
sudo systemctl restart nlq-api
```

### Step 5: Test

```bash
curl -X POST http://localhost:8080/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "show me recent incidents",
    "context": {
      "account_uuid": "account-uuid-here",
      "property_uuid": "property-uuid-here",
      "user_uuid": "new-user-uuid-here"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": false}
  }'
```

## Permission Validation Flow

```
Request with (account_uuid, property_uuid, user_uuid)
    ↓
┌───────────────────────────────────────────────┐
│ Tier 1: Account/Property Level                │
│ Check: (account_uuid, property_uuid) exists   │
│ Result: allowed_databases, allowed_tables     │
└───────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────┐
│ Tier 2: Property Level                        │
│ Check: property_uuid maps to database         │
│ Result: database name, property name          │
└───────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────┐
│ Tier 3: User Level (if user_uuid provided)   │
│ Check: user has access to property_uuid       │
│ Result: RESTRICT queries to that property     │
└───────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────┐
│ SQL Generation with Property Filter           │
│ WHERE property_name = 'The Peninsula ...'     │
└───────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────┐
│ Execute on Athena                             │
└───────────────────────────────────────────────┘
```

## Common Patterns

### Pattern 1: Single Property User
User can only access one property.

```python
# Hong Kong staff member
"c4b943a0-57c5-4fe1-bfb9-6e09d5b60c40": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"]
```

### Pattern 2: Multi-Property User
User can access multiple properties.

```python
# Regional manager
"regional-manager-uuid": [
    "8afe7e5e-22e5-4318-b5c7-f967fc44e81f",  # Hong Kong
    "c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"   # Manila
]
```

### Pattern 3: Admin User
User has wildcard access to all properties.

```python
# Super admin
"admin-user-uuid": ["*"]
```

## Troubleshooting Checklist

### User Cannot Access Data

1. ✅ Check user exists in `USER_TABLE_PERMISSIONS`
2. ✅ Check user has correct property_uuid in their list
3. ✅ Check account/property pair exists in `PERMISSIONS_MAPPING`
4. ✅ Check property UUID matches exactly (case-sensitive)
5. ✅ Restart service after config changes
6. ✅ Check logs at `logs/api_requests.json`

### Wrong Data Returned

1. ✅ Verify `property_name` in database matches config
2. ✅ Check SQL query includes `WHERE property_name = ...`
3. ✅ Verify user_uuid is being sent in API request
4. ✅ Check prompt is receiving property restrictions

### Permission Denied Errors

```json
{
  "error_code": "USER_PROPERTY_NOT_ALLOWED",
  "suggestions": [...]
}
```

**Action:** User's property_uuid list doesn't include the requested property_uuid.

```json
{
  "error_code": "NO_PERMISSION_MAPPING"  
}
```

**Action:** Add (account_uuid, property_uuid) pair to PERMISSIONS_MAPPING.

## Security Best Practices

1. **Always include user_uuid** in production API requests
2. **Never share UUIDs** publicly or in client-side code
3. **Audit logs regularly** - check `logs/api_requests.json`
4. **Rotate credentials** periodically
5. **Use least privilege** - give users minimum necessary property access
6. **Test permissions** before granting production access

## Performance Tips

1. **Use specific properties** instead of wildcard when possible
2. **Include date filters** to limit data scanned
3. **Limit result sets** with appropriate max_rows
4. **Monitor query execution time** in logs
5. **Use partition columns** (snapshotdate) in WHERE clauses

## Support

For additional help:
- Check main [README.md](../README.md)
- Review logs at `logs/api_requests.json`
- See archived docs in `documentation/archive/`
