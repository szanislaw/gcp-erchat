# NLQ → Athena SQL API (Intermediate Version)

## Overview

This API converts **natural language queries** into **AWS Athena–compatible SQL** using a large language model (SQLCoder).  
It supports **dry-run SQL generation** as well as **optional query execution** against Athena.

This service is **read-only** and does **not modify any data**.

> ⚠️ Note: This API is currently hosted separately from other FCS APIs and is exposed via a direct VM IP address.

---

## Base URL

```
http://136.110.55.203:8080
```

---

## Endpoint

### `POST /nlq/execute`

**Content-Type:** `application/json`

---

## Purpose

- Convert natural language questions into Athena SQL
- Allow preview of generated SQL (`dry_run`)
- Optionally execute SQL and return results
- Enforce basic safety guarantees (SELECT-only, LIMIT enforced)

---

## Request Body Schema

```json
{
  "text": "string (required)",
  "context": {
    "language": "en | zh | ms | ta",
    "property_uuid": "string (optional)",
    "user_role": "string (optional)"
  },
  "sql": {
    "dialect": "athena",
    "tables": ["string"]
  },
  "execution": {
    "dry_run": true | false,
    "max_rows": number,
    "athena_target": "string"
  },
  "model": {
    "max_tokens": number
  },
  "trace": {
    "request_id": "string (optional)",
    "source": "string"
  }
}
```

---

## Required Fields

| Field | Description |
|-----|------------|
| `text` | Natural language query |
| `sql.dialect` | Must be `"athena"` |
| `sql.tables` | Tables allowed for SQL generation |
| `execution.athena_target` | Athena configuration target |

---

## Example 1: Dry Run (SQL Generation Only)

### Request

```json
{
  "text": "show the most recent records",
  "context": {
    "language": "en"
  },
  "sql": {
    "dialect": "athena",
    "tables": ["incident_combine"]
  },
  "execution": {
    "dry_run": true,
    "max_rows": 10,
    "athena_target": "peninsula_incident"
  },
  "model": {
    "max_tokens": 512
  },
  "trace": {
    "source": "frontend-ui"
  }
}
```

### Response

```json
{
  "success": true,
  "sql": {
    "query": "SELECT * FROM incident_combine ORDER BY snapshotdate DESC LIMIT 100",
    "confidence": 0.9
  },
  "execution": {
    "executed": false,
    "row_count": null,
    "data": null
  }
}
```

---

## Example 2: Execute Query (Athena)

### Request

```json
{
  "text": "show the most recent records",
  "context": {
    "language": "en"
  },
  "sql": {
    "dialect": "athena",
    "tables": ["incident_combine"]
  },
  "execution": {
    "dry_run": false,
    "max_rows": 10,
    "athena_target": "peninsula_incident"
  }
}
```

### Response

```json
{
  "success": true,
  "sql": {
    "query": "SELECT * FROM incident_combine ORDER BY snapshotdate DESC LIMIT 100"
  },
  "execution": {
    "executed": true,
    "row_count": 10,
    "data": {
      "columns": ["snapshotdate", "incident_name", "..."],
      "rows": [
        {
          "snapshotdate": "2024-12-12",
          "incident_name": "..."
        }
      ]
    }
  }
}
```

---

## Error Responses

### Invalid Input / No SQL Generated

```json
{
  "detail": "Empty SQL"
}
```

### Athena Execution Failure

```json
{
  "detail": "Athena query FAILED: <reason>"
}
```

---

## Operational Notes

### Latency
- First request after restart may take **30–90 seconds** (model warm-up)
- Subsequent requests typically respond within **1–3 seconds** (dry-run)

### Safety Guarantees
- Only `SELECT` queries are generated
- `LIMIT` is always enforced
- No data mutation is possible

### Cost Considerations
- `dry_run = true` does **not** incur Athena query cost
- `dry_run = false` executes Athena queries and incurs standard Athena costs

---

## Integration Guidance

- Use **dry-run** first to preview SQL
- Validate SQL before execution
- Do not assume semantic optimality of SQL (intermediate version)
- Treat results as **best-effort analytical queries**

---

## Status & Limitations

- This is an **intermediate / prototype version**
- API contract may evolve
- Additional guardrails (partition enforcement, cost estimation) will be added later
- Hosted outside the main FCS API gateway for now

---

## Contact / Ownership

For changes, questions, or integration feedback, please contact the AI Engineering team.
