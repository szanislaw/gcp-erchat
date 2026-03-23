import boto3
import time
import hashlib
from typing import Dict, Any
from app.athena_config import ATHENA_TARGETS


# Cache Athena clients per target to avoid re-creation
_ATHENA_CLIENTS: Dict[str, Any] = {}

# Cache query results to avoid re-execution of identical queries
_QUERY_CACHE: Dict[str, Any] = {}
_CACHE_MAX_SIZE = 100  # Limit cache size


def get_client(target_name: str):
    """
    Return a cached boto3 Athena client for the given target.
    """
    if target_name not in ATHENA_TARGETS:
        raise ValueError(f"Unknown Athena target: {target_name}")

    if target_name in _ATHENA_CLIENTS:
        return _ATHENA_CLIENTS[target_name]

    cfg = ATHENA_TARGETS[target_name]

    # boto3 will automatically use AWS credentials from:
    # 1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    # 2. AWS credentials file (~/.aws/credentials)
    # 3. IAM role (if running on AWS EC2/ECS/Lambda)
    client = boto3.client(
        "athena",
        region_name=cfg["region"],
    )

    _ATHENA_CLIENTS[target_name] = client
    return client


def execute_query(sql: str, target_name: str, max_rows: int):
    """
    Execute a SQL query against Athena and return normalized results.
    Uses caching to avoid re-execution of identical queries.
    """
    sql_lower = sql.strip().lower()
    if not (sql_lower.startswith("select") or sql_lower.startswith("with")):
        raise ValueError("Only SELECT queries are allowed for Athena execution")

    # Check cache first
    cache_key = hashlib.md5(f"{sql}:{target_name}:{max_rows}".encode()).hexdigest()
    if cache_key in _QUERY_CACHE:
        return _QUERY_CACHE[cache_key]

    cfg = ATHENA_TARGETS[target_name]
    client = get_client(target_name)

    response = client.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={
            "Database": cfg["database"]
        },
        ResultConfiguration={
            "OutputLocation": cfg["s3_output"]
        },
        ResultReuseConfiguration={
            'ResultReuseByAgeConfiguration': {
                'Enabled': True,
                'MaxAgeInMinutes': 60  # Reuse results for 1 hour
            }
        }
    )

    query_execution_id = response["QueryExecutionId"]

    _wait_for_query(client, query_execution_id)

    results = client.get_query_results(
        QueryExecutionId=query_execution_id,
        MaxResults=max_rows
    )

    normalized = _normalize_results(results)
    
    # Cache the result (with size limit)
    if len(_QUERY_CACHE) >= _CACHE_MAX_SIZE:
        # Remove oldest entry (simple FIFO)
        _QUERY_CACHE.pop(next(iter(_QUERY_CACHE)))
    _QUERY_CACHE[cache_key] = normalized
    
    return normalized


def _wait_for_query(client, query_execution_id: str):
    """
    Poll Athena until query finishes.
    Uses exponential backoff for efficient polling.
    """
    poll_interval = 0.2  # Start with 200ms
    max_interval = 2.0
    
    while True:
        res = client.get_query_execution(
            QueryExecutionId=query_execution_id
        )
        status = res["QueryExecution"]["Status"]["State"]

        if status == "SUCCEEDED":
            return
        if status in ("FAILED", "CANCELLED"):
            reason = res["QueryExecution"]["Status"].get(
                "StateChangeReason", "Unknown reason"
            )
            raise RuntimeError(f"Athena query {status}: {reason}")

        time.sleep(poll_interval)
        poll_interval = min(poll_interval * 1.5, max_interval)  # Exponential backoff


def _normalize_results(results):
    """
    Convert Athena result set into JSON-friendly structure.
    """
    rows = results["ResultSet"]["Rows"]

    if not rows or len(rows) == 1:
        return {
            "columns": [],
            "rows": [],
            "row_count": 0
        }

    headers = [
        col.get("VarCharValue") for col in rows[0]["Data"]
    ]

    data = []
    for row in rows[1:]:
        record = {}
        for idx, col in enumerate(row["Data"]):
            record[headers[idx]] = col.get("VarCharValue")
        data.append(record)

    return {
        "columns": headers,
        "rows": data,
        "row_count": len(data)
    }
