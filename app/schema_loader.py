import boto3
from typing import Dict, Any
from app.athena_config import ATHENA_TARGETS

# In-memory cache to avoid repeated Glue calls
_SCHEMA_CACHE: Dict[str, Any] = {}


def load_schema(target_name: str) -> Dict[str, Any]:
    """
    Load table schemas from AWS Glue for a given Athena target.
    Cached after first load.
    """
    if target_name in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[target_name]

    if target_name not in ATHENA_TARGETS:
        raise ValueError(f"Unknown Athena target: {target_name}")

    cfg = ATHENA_TARGETS[target_name]

    # boto3 will automatically use AWS credentials from:
    # 1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    # 2. AWS credentials file (~/.aws/credentials)
    # 3. IAM role (if running on AWS EC2/ECS/Lambda)
    glue = boto3.client(
        "glue",
        region_name=cfg["region"]
    )

    schema: Dict[str, Any] = {}

    for table_name in cfg["tables"]:
        resp = glue.get_table(
            DatabaseName=cfg["database"],
            Name=table_name
        )

        table = resp["Table"]

        columns = table["StorageDescriptor"]["Columns"]
        partitions = table.get("PartitionKeys", [])

        schema[table_name] = {
            "columns": [
                {
                    "name": c["Name"],
                    "type": c["Type"]
                }
                for c in columns
            ],
            "partitions": [
                {
                    "name": p["Name"],
                    "type": p["Type"]
                }
                for p in partitions
            ]
        }

    _SCHEMA_CACHE[target_name] = schema
    return schema


def compress_schema(schema: Dict[str, Any]) -> str:
    """
    Convert Glue schema into a compact, prompt-friendly format.
    """
    lines = []

    for table, meta in schema.items():
        col_str = ", ".join(
            f"{c['name']} ({c['type']})"
            for c in meta["columns"]
        )

        part_str = (
            ", ".join(p["name"] for p in meta["partitions"])
            if meta["partitions"] else "none"
        )

        lines.append(
            f"- {table}: columns [{col_str}]; partitions [{part_str}]"
        )

    return "\n".join(lines)
