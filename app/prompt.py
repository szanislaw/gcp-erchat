from app.schema_loader import load_schema, schema_to_ddl, load_column_values
from app.query_normalizer import preprocess_query, get_time_expression_hint
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def find_property_uuid_column(schema: dict) -> str:
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

    property_col = find_property_uuid_column(schema)
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

    time_hint = get_time_expression_hint(text)
    if time_hint:
        entity_hints = (entity_hints + "\n" + time_hint).strip() if entity_hints else time_hint
    entity_context = f"\nDETECTED ENTITIES (use these exact values):\n{entity_hints}" if (matched_entities or time_hint) else ""
    enum_hint = f"\n{enum_section}" if enum_section else ""

    additional_instructions = f"""
Use AWS Athena (PrestoSQL) syntax. Output ONLY the SQL query, no explanation.
- ALWAYS include LIMIT (max 100)
- Use ONLY the tables and columns in the schema below — do NOT invent names or append suffixes
- Categorical values are lowercase in the DB: severity='high'/'medium'/'low', status='pending'/'completed'/'cancelled'
- snapshotdate is VARCHAR: for ALL date filtering AND date-based GROUP BY use date_parse(snapshotdate, '%Y-%m-%d')
- Date arithmetic: use date_add() NEVER use INTERVAL syntax in any form
- Date range — rolling windows (last N days/weeks): use date_add()
  Example "last 7 days":  WHERE date_parse(snapshotdate, '%Y-%m-%d') >= date_add('day', -7, current_date)
  Example "last 30 days": WHERE date_parse(snapshotdate, '%Y-%m-%d') >= date_add('day', -30, current_date)
- Date range — calendar boundaries (this week / this month / last week / last month): use date_trunc()
  Example "this week":  WHERE date_parse(snapshotdate, '%Y-%m-%d') >= date_trunc('week', current_date)
  Example "this month": WHERE date_parse(snapshotdate, '%Y-%m-%d') >= date_trunc('month', current_date)
  Example "last week":  WHERE date_parse(snapshotdate, '%Y-%m-%d') >= date_add('week', -1, date_trunc('week', current_date)) AND date_parse(snapshotdate, '%Y-%m-%d') < date_trunc('week', current_date)
  Example "last month": WHERE date_parse(snapshotdate, '%Y-%m-%d') >= date_add('month', -1, date_trunc('month', current_date)) AND date_parse(snapshotdate, '%Y-%m-%d') < date_trunc('month', current_date)
- NEVER use date_part() or EXTRACT() to build date range filters
- Year filter: use year(date_parse(snapshotdate, '%Y-%m-%d')) = YYYY
- Monthly trend: GROUP BY date_trunc('month', date_parse(snapshotdate, '%Y-%m-%d'))
- Weekly trend: GROUP BY date_trunc('week', date_parse(snapshotdate, '%Y-%m-%d'))
- Daily trend: GROUP BY snapshotdate
- created_date, incident_time, completed_date, cancelled_date are BIGINT timestamps: use ONLY for ORDER BY, NEVER in WHERE, GROUP BY, or any date function. Even for "created this week/month", filter using snapshotdate not created_date.
- For "recent" without a time period: ORDER BY created_date DESC LIMIT X — no date filter needed
- property_name = hotel display name (e.g. 'The Peninsula Manila') — a TEXT column, NOT for UUID filtering
- location_name = room/area within hotel — use for "by location", "show location", "incidents by location"
- department_name = hotel department — "resolves" incidents means status_name = 'completed'; "reports" means COUNT by that department
- vip column: value 'Y' means VIP guest. VIP filter: WHERE vip = 'Y'. VIP count: COUNT(CASE WHEN vip = 'Y' THEN 1 END)
- Percentage of total: CAST(COUNT(CASE WHEN <condition> THEN 1 END) AS DOUBLE) * 100.0 / NULLIF(COUNT(*), 0) AS percentage
- Trend / rising / decreasing / growth / increasing / falling queries: ALWAYS use WITH CTE syntax — two named CTEs (prev, curr) with date_trunc('month') boundaries:
  WITH prev AS (SELECT dim, COUNT(*) AS cnt FROM incident_combine WHERE property IN (...) AND date_parse(snapshotdate,'%Y-%m-%d') >= date_add('month',-1,date_trunc('month',current_date)) AND date_parse(snapshotdate,'%Y-%m-%d') < date_trunc('month',current_date) GROUP BY dim),
  curr AS (SELECT dim, COUNT(*) AS cnt FROM incident_combine WHERE property IN (...) AND date_parse(snapshotdate,'%Y-%m-%d') >= date_trunc('month',current_date) GROUP BY dim)
  SELECT dim FROM prev JOIN curr USING(dim) WHERE curr.cnt > prev.cnt ORDER BY (curr.cnt-prev.cnt) DESC LIMIT 100
  Use WITH ... AS (...) NOT inline subqueries. "Rising/increasing" = WHERE curr.cnt > prev.cnt; "Decreasing/falling" = WHERE curr.cnt < prev.cnt (NOT status='completed'). For "costs" use SUM(actual_cost). For "fastest growth" ORDER BY DESC LIMIT 1. Each CTE must have mandatory property filter.
- ALL data is in ONE table only — never reference any separate dimension table (department, location, category, etc.). Do not add JOIN to any table other than the allowed table or CTEs derived from it.
- "recurring incidents" = most frequently occurring; use GROUP BY category_name (or location_name) ORDER BY COUNT(*) DESC
- "least incidents" = ORDER BY COUNT(*) ASC LIMIT 1; "most incidents" = ORDER BY COUNT(*) DESC LIMIT 1
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
