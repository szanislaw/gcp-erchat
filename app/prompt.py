from app.schema_loader import load_schema, schema_to_ddl, load_column_values
from app.query_normalizer import preprocess_query
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def _find_property_uuid_column(schema: dict) -> str:
    """
    Detect the property UUID column name from the Glue schema.
    The actual column may be 'property_uuid', 'property', etc.
    Also checks partition keys.

    Priority:
    1. Exact match: 'property_uuid' in columns or partitions
    2. Contains both 'property' and 'uuid' in columns
    3. Column named 'property' (often contains UUID values)
    4. Partition key named 'property' (contains UUID values)

    Returns the column name or None if not found.
    """
    # Pass 1: exact match 'property_uuid' in columns
    for table_name, meta in schema.items():
        for col in meta.get("columns", []):
            if col["name"].lower() == "property_uuid":
                return "property_uuid"
        
        # Check partitions too
        for part in meta.get("partitions", []):
            if part["name"].lower() == "property_uuid":
                return "property_uuid"

    # Pass 2: contains both 'property' and 'uuid' in columns
    for table_name, meta in schema.items():
        for col in meta.get("columns", []):
            name_lower = col["name"].lower()
            if "property" in name_lower and "uuid" in name_lower:
                return col["name"]

    # Pass 3: column named exactly 'property'
    for table_name, meta in schema.items():
        for col in meta.get("columns", []):
            if col["name"].lower() == "property":
                return col["name"]
        
        # Check partitions - 'property' partition key often holds UUIDs
        for part in meta.get("partitions", []):
            if part["name"].lower() == "property":
                logger.info("Found 'property' as partition key - will use for filtering")
                return "property"

    return None


def _format_enum_section(column_values: dict) -> str:
    if not column_values:
        return ""
    lines = ["EXACT ALLOWED VALUES (use these exact strings, case-sensitive):"]
    for col, vals in column_values.items():
        if vals:
            lines.append(f"- {col}: {', '.join(repr(v) for v in vals)}")
    return "\n".join(lines)


def _build_common_parts(
    text, context, sql, athena_target: str,
    property_uuid: Optional[str] = None,
    user_uuid: Optional[str] = None,
):
    """Shared logic for building the schema, instructions, and normalized text."""
    schema = load_schema(athena_target)
    ddl_schema = schema_to_ddl(schema)
    column_values = load_column_values(athena_target)
    enum_section = _format_enum_section(column_values)

    property_uuids = [u.strip() for u in property_uuid.split(',') if u.strip()] if property_uuid else []
    property_name = getattr(context, 'location_name', None)
    normalized_text, matched_entities, entity_hints = preprocess_query(text)

    property_col = _find_property_uuid_column(schema)
    if property_col:
        logger.info(f"Detected property UUID column: '{property_col}'")
    else:
        logger.warning("Could not detect property UUID column from schema")

    property_restriction = ""
    if property_uuids and property_col:
        uuid_in_list = ", ".join(f"'{u}'" for u in property_uuids)
        property_restriction = f"\nCRITICAL: You MUST include WHERE {property_col} IN ({uuid_in_list}) in every query. This is mandatory."
    elif property_uuids and not property_col:
        logger.warning(f"Property UUIDs provided ({property_uuids}) but no property UUID column found in schema - skipping UUID filtering")
    elif property_name:
        property_restriction = f"\nCRITICAL: You MUST include WHERE property_name = '{property_name}' in every query. This is mandatory."

    entity_context = f"\nDETECTED ENTITIES (use these exact values):\n{entity_hints}" if matched_entities else ""
    enum_hint = f"\n{enum_section}" if enum_section else ""

    additional_instructions = f"""
Use AWS Athena (PrestoSQL) syntax. Output ONLY the SQL query, no explanation.
- ALWAYS include LIMIT (max 100)
- Use ONLY the tables and columns in the schema below — do NOT invent names or append suffixes
- Categorical values are lowercase in the DB: severity='high'/'medium'/'low', status='pending'/'completed'/'cancelled'
- snapshotdate is VARCHAR: for ALL date filtering AND date-based GROUP BY use date_parse(snapshotdate, '%Y-%m-%d')
- Date arithmetic: use date_add('day', -N, current_date) NEVER use INTERVAL syntax in any form
- Date range filter: ALWAYS use >= date_add('day', -N, current_date). NEVER use date_part() or EXTRACT() to build ranges.
  Example "last 7 days": WHERE date_parse(snapshotdate, '%Y-%m-%d') >= date_add('day', -7, current_date)
  Example "last 4 weeks": WHERE date_parse(snapshotdate, '%Y-%m-%d') >= date_add('day', -28, current_date)
- Year filter: use year(date_parse(snapshotdate, '%Y-%m-%d')) = YYYY, NOT date_part()
- Monthly trend: GROUP BY date_trunc('month', date_parse(snapshotdate, '%Y-%m-%d'))
- Weekly trend: GROUP BY date_trunc('week', date_parse(snapshotdate, '%Y-%m-%d'))
- Daily trend: GROUP BY snapshotdate
- created_date, incident_time, completed_date, cancelled_date are BIGINT timestamps: use ONLY for ORDER BY, NEVER in WHERE, GROUP BY, or any date function
- For "recent" without a time period: ORDER BY created_date DESC LIMIT X — no date filter needed
- property_name = hotel display name (e.g. 'The Peninsula Manila') — a TEXT column, NOT for UUID filtering
- location_name = room/area within hotel
- The `property` partition key holds UUIDs for access control — NEVER use property_name for UUID filtering{property_restriction}{entity_context}{enum_hint}"""

    return normalized_text, ddl_schema, additional_instructions


def build_prompt(text, context, sql, athena_target: str, property_uuid: Optional[str] = None, user_uuid: Optional[str] = None) -> str:
    normalized_text, ddl_schema, additional_instructions = _build_common_parts(
        text, context, sql, athena_target, property_uuid, user_uuid
    )

    return f"""### Task
Generate a SQL query to answer [QUESTION]{normalized_text}[/QUESTION]
{additional_instructions}

### Database Schema
The query will run on a database with the following schema:
{ddl_schema}

### Answer
Given the database schema, here is the SQL query that [QUESTION]{normalized_text}[/QUESTION]
[SQL]"""


def build_correction_prompt(
    text, context, sql, athena_target: str,
    failed_sql: str, error_message: str,
    property_uuid: Optional[str] = None,
    user_uuid: Optional[str] = None,
) -> str:
    normalized_text, ddl_schema, additional_instructions = _build_common_parts(
        text, context, sql, athena_target, property_uuid, user_uuid
    )
    # Trim the error to the first line — Athena errors are specific and not too long
    error_summary = error_message.split('\n')[0][:300]

    return f"""### Task
The following SQL query failed. Fix it to answer [QUESTION]{normalized_text}[/QUESTION]

Failed SQL:
{failed_sql}

Athena error:
{error_summary}
{additional_instructions}

### Database Schema
The query will run on a database with the following schema:
{ddl_schema}

### Answer
Given the database schema, here is the corrected SQL query that [QUESTION]{normalized_text}[/QUESTION]
[SQL]"""
