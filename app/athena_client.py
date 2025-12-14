import boto3
import time
from typing import Dict, Any
from app.athena_config import ATHENA_TARGETS


# Cache Athena clients per target to avoid re-creation
_ATHENA_CLIENTS: Dict[str, Any] = {}


def get_client(target_name: str):
    """
    Return a cached boto3 Athena client for the given target.
    """
    if target_name not in ATHENA_TARGETS:
        raise ValueError(f"Unknown Athena target: {target_name}")

    if target_name in _ATHENA_CLIENTS:
        return _ATHENA_CLIENTS[target_name]

    cfg = ATHENA_TARGETS[target_name]

    client = boto3.client(
        "athena",
        region_name=cfg["region"],
        aws_access_key_id=cfg["aws_access_key_id"],
        aws_secret_access_key=cfg["aws_secret_access_key"],
    )

    _ATHENA_CLIENTS[target_name] = client
    return client


def execute_query(sql: str, target_name: str, max_rows: int):
    """
    Execute a SQL query against Athena and return normalized results.
    """
    if not sql.lower().startswith("select"):
        raise ValueError("Only SELECT queries are allowed for Athena execution")

    cfg = ATHENA_TARGETS[target_name]
    client = get_client(target_name)

    response = client.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={
            "Database": cfg["database"]
        },
        ResultConfiguration={
            "OutputLocation": cfg["s3_output"]
        }
    )

    query_execution_id = response["QueryExecutionId"]

    _wait_for_query(client, query_execution_id)

    results = client.get_query_results(
        QueryExecutionId=query_execution_id,
        MaxResults=max_rows
    )

    return _normalize_results(results)


def _wait_for_query(client, query_execution_id: str):
    """
    Poll Athena until query finishes.
    """
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

        time.sleep(0.5)


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
