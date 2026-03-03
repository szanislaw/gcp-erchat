import boto3
import logging
from typing import Dict, Any
from app.athena_config import ATHENA_TARGETS

logger = logging.getLogger(__name__)

# In-memory cache to avoid repeated Glue calls
_SCHEMA_CACHE: Dict[str, Any] = {}
_COLUMN_VALUES_CACHE: Dict[str, Dict[str, list]] = {}


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


def schema_to_ddl(schema: Dict[str, Any]) -> str:
    """Convert schema dict to DDL CREATE TABLE statements (required by SQLCoder)."""
    statements = []
    for table_name, meta in schema.items():
        db = meta.get("database", "")
        full_name = f"{db}.{table_name}" if db else table_name

        col_defs = []
        for col in meta.get("columns", []):
            col_defs.append(f"    {col['name']} {col['type'].upper()}")
        for part in meta.get("partitions", []):
            col_defs.append(f"    {part['name']} {part['type'].upper()} -- partition key")

        statements.append(f"CREATE TABLE {full_name} (\n" + ",\n".join(col_defs) + "\n);")

    return "\n\n".join(statements)


def load_column_values(target_name: str) -> Dict[str, list]:
    """
    Fetch DISTINCT values for categorical columns from Athena.
    Cached after first load. Returns {column_name: [val1, val2, ...]}
    """
    if target_name in _COLUMN_VALUES_CACHE:
        return _COLUMN_VALUES_CACHE[target_name]

    from app.athena_config import ENUM_COLUMNS
    from app.athena_client import execute_query

    cfg = ENUM_COLUMNS.get(target_name)
    if not cfg:
        return {}

    result: Dict[str, list] = {}
    table = cfg["table"]
    limit = cfg["limit"]

    for col in cfg["columns"]:
        try:
            sql = f"SELECT DISTINCT {col} FROM {table} WHERE {col} IS NOT NULL ORDER BY {col} LIMIT {limit}"
            data = execute_query(sql=sql, target_name=target_name, max_rows=limit)
            values = [row[col] for row in data.get("rows", []) if row.get(col)]
            result[col] = values
        except Exception as e:
            logger.warning(f"Could not load distinct values for {col}: {e}")
            result[col] = []

    _COLUMN_VALUES_CACHE[target_name] = result
    return result
