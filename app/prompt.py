from app.schema_loader import load_schema, schema_to_ddl, load_column_values
from app.query_normalizer import preprocess_query, get_time_expression_hint
from app.display_hint import get_display_type_from_question
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def find_property_uuid_column(schema: dict) -> str:
    """
    Detect the property UUID column name from the schema.

    Priority:
    1. Exact match: 'property_uuid'
    2. Contains both 'property' and 'uuid'
    3. Column named exactly 'property'
    4. Partition key named 'property'
    """
    for table_name, meta in schema.items():
        for col in meta.get("columns", []):
            if col["name"].lower() == "property_uuid":
                return "property_uuid"
        for part in meta.get("partitions", []):
            if part["name"].lower() == "property_uuid":
                return "property_uuid"

    for table_name, meta in schema.items():
        for col in meta.get("columns", []):
            name_lower = col["name"].lower()
            if "property" in name_lower and "uuid" in name_lower:
                return col["name"]

    for table_name, meta in schema.items():
        for col in meta.get("columns", []):
            if col["name"].lower() == "property":
                return col["name"]
        for part in meta.get("partitions", []):
            if part["name"].lower() == "property":
                logger.info("Found 'property' as partition key — using for filtering")
                return "property"

    return None


def _match_hotel_name(text: str, property_names: list) -> Optional[str]:
    """Detect a hotel/property name in the NL query against known property_name values.

    Tries full-name substring match first, then partial match on significant words
    (strips 'the'/'a'/'an') so 'Peninsula Manila' hits 'The Peninsula Manila'.
    """
    if not property_names:
        return None
    text_lower = text.lower()
    for name in property_names:
        if name.lower() in text_lower:
            return name
    for name in property_names:
        significant = [w for w in name.lower().split() if w not in ('the', 'a', 'an')]
        if len(significant) >= 2 and all(w in text_lower for w in significant):
            return name
    return None


def _build_chart_hint(display_type: Optional[str]) -> str:
    if display_type == "bar":
        return (
            "\nCHART STRUCTURE (bar chart): Return exactly 2 columns — "
            "a category label column and a numeric value column (COUNT/SUM/AVG). "
            "ORDER BY the value column DESC so bars are sorted largest to smallest.\n"
            "Example: SELECT category_name, COUNT(*) AS count FROM ... GROUP BY 1 ORDER BY 2 DESC LIMIT 100"
        )
    if display_type == "line":
        return (
            "\nCHART STRUCTURE (line chart): Return exactly 2 columns — "
            "a time bucket column using DATE_TRUNC (x-axis) and a numeric value column (y-axis). "
            "ORDER BY the time column ASC so the trend flows left to right.\n"
            "Example: SELECT DATE_TRUNC('month', created_date) AS month, COUNT(*) AS count "
            "FROM ... GROUP BY 1 ORDER BY 1 LIMIT 100"
        )
    return ""


def _format_enum_section(column_values: dict) -> str:
    if not column_values:
        return ""
    lines = ["EXACT ALLOWED VALUES (use these exact strings, case-sensitive):"]
    for col, vals in column_values.items():
        if vals:
            lines.append(f"- {col}: {', '.join(repr(v) for v in vals)}")
    return "\n".join(lines)


def _build_maintenance_instructions(property_restriction: str, entity_context: str, enum_hint: str, chart_hint: str = "") -> str:
    return f"""
Use Amazon Redshift SQL syntax. Output ONLY the SQL query, no explanation.

FOREIGN KEY RELATIONSHIPS — always JOIN these, never use raw integer values:
  maintenance_order.status   (SMALLINT) → master_maintenance_status.status_id   → s.status_name
  maintenance_order.priority (SMALLINT) → master_job_priority.priority_id       → p.priority_name
  maintenance_order.location_uuid       → property_location.location_uuid        → pl.location_name

STATUS SEMANTICS — all values are lowercase in the database:
  Actual status values: 'completed', 'delayed', 'pending', 'cancelled', 'acknowledged'
  There is NO status called 'open' — "open orders" means: WHERE s.status_name IN ('pending', 'delayed', 'acknowledged')
  NEVER use Title Case ('Completed', 'Open', 'High') — always lowercase

PRIORITY TERMS → always JOIN master_job_priority:
  urgent/high/medium/low/normal/critical = priority level, NOT status
  "urgent orders" → WHERE p.priority_name = 'urgent'
  "high priority" → WHERE p.priority_name = 'high'

CORRECT EXAMPLES:
  "open orders" (pending/delayed/acknowledged, not a single status):
    SELECT COUNT(*) FROM maintenance_order m
    JOIN master_maintenance_status s ON m.status = s.status_id
    WHERE s.status_name IN ('pending', 'delayed', 'acknowledged') LIMIT 100

  "completed orders":
    SELECT COUNT(*) FROM maintenance_order m
    JOIN master_maintenance_status s ON m.status = s.status_id
    WHERE s.status_name = 'completed' LIMIT 100

  "high priority orders":
    SELECT COUNT(*) FROM maintenance_order m
    JOIN master_job_priority p ON m.priority = p.priority_id
    WHERE p.priority_name = 'high' LIMIT 100

  "count by priority":
    SELECT p.priority_name, COUNT(*) FROM maintenance_order m
    JOIN master_job_priority p ON m.priority = p.priority_id
    GROUP BY p.priority_name ORDER BY COUNT(*) DESC LIMIT 100

  "count by status":
    SELECT s.status_name, COUNT(*) FROM maintenance_order m
    JOIN master_maintenance_status s ON m.status = s.status_id
    GROUP BY s.status_name ORDER BY COUNT(*) DESC LIMIT 100

  "open high priority orders":
    SELECT COUNT(*) FROM maintenance_order m
    JOIN master_maintenance_status s ON m.status = s.status_id
    JOIN master_job_priority p ON m.priority = p.priority_id
    WHERE s.status_name IN ('pending', 'delayed', 'acknowledged') AND p.priority_name = 'high' LIMIT 100

  "most recent 5 completed orders":
    SELECT m.maintenance_no, m.created_date FROM maintenance_order m
    JOIN master_maintenance_status s ON m.status = s.status_id
    WHERE s.status_name = 'completed'
    ORDER BY m.created_date DESC LIMIT 5

  "show/list high priority open orders":
    SELECT m.maintenance_no, m.created_date FROM maintenance_order m
    JOIN master_maintenance_status s ON m.status = s.status_id
    JOIN master_job_priority p ON m.priority = p.priority_id
    WHERE s.status_name IN ('pending', 'delayed', 'acknowledged') AND p.priority_name = 'high'
    ORDER BY m.created_date DESC LIMIT 100

  "distribution by status and priority" (use COUNT + GROUP BY, NEVER window functions):
    SELECT s.status_name, p.priority_name, COUNT(*) FROM maintenance_order m
    JOIN master_maintenance_status s ON m.status = s.status_id
    JOIN master_job_priority p ON m.priority = p.priority_id
    GROUP BY s.status_name, p.priority_name ORDER BY COUNT(*) DESC LIMIT 100

  "created vs completed this month" (CASE WHEN on each date column):
    SELECT COUNT(CASE WHEN m.created_date >= DATE_TRUNC('month', CURRENT_DATE) THEN 1 END) AS created_count,
           COUNT(CASE WHEN m.completed_date >= DATE_TRUNC('month', CURRENT_DATE) THEN 1 END) AS completed_count
    FROM maintenance_order m LIMIT 100

RULES:
1. LIMIT required (max 100)
2. Use ONLY tables and columns in the schema — never invent names
3. NEVER filter status/priority with raw integers (WHERE status = 1 is WRONG)
4. Date columns (created_date, completed_date, cancelled_date, assigned_date, modified_date) are TIMESTAMP — no casting
5. Redshift date syntax only — NEVER date_add(), date_parse(), or INTERVAL '...':
   - Rolling: WHERE created_date >= DATEADD(day, -30, CURRENT_DATE)
   - This week: WHERE created_date >= DATE_TRUNC('week', CURRENT_DATE)
   - This month: WHERE created_date >= DATE_TRUNC('month', CURRENT_DATE)
   - Last week: WHERE created_date >= DATEADD(week, -1, DATE_TRUNC('week', CURRENT_DATE))
              AND created_date < DATE_TRUNC('week', CURRENT_DATE)
              NEVER use date_part('week', ...) comparisons for "last week"
   - Last month: WHERE created_date >= DATEADD(month, -1, DATE_TRUNC('month', CURRENT_DATE)) AND created_date < DATE_TRUNC('month', CURRENT_DATE)
   - Year: WHERE EXTRACT(YEAR FROM created_date) = EXTRACT(YEAR FROM CURRENT_DATE)
6. Trend: GROUP BY DATE_TRUNC('month'/'week'/'day', created_date) ORDER BY 1
7. Two-count comparison ("created vs completed this month"):
   SELECT COUNT(CASE WHEN created_date >= DATE_TRUNC('month', CURRENT_DATE) THEN 1 END) AS created_count,
          COUNT(CASE WHEN completed_date >= DATE_TRUNC('month', CURRENT_DATE) THEN 1 END) AS completed_count
   FROM maintenance_order LIMIT 100
   Growth/comparison across periods: WITH prev AS (...), curr AS (...) SELECT ...
8. Percentage: CAST(COUNT(CASE WHEN <cond> THEN 1 END) AS FLOAT) * 100.0 / NULLIF(COUNT(*), 0)
9. "Recent" no time period: ORDER BY created_date DESC LIMIT N — no date filter
10. NEVER use 'snapshotdate' — this column does not exist in this schema{chart_hint}{property_restriction}{entity_context}{enum_hint}"""


def _build_incident_instructions(property_restriction: str, entity_context: str, enum_hint: str, chart_hint: str = "") -> str:
    return f"""
Use Amazon Redshift SQL syntax. Output ONLY the SQL query, no explanation.

TABLE: mv_recovery_all — a flat, pre-joined view. NO JOINs required. Query it directly.

KEY COLUMNS:
  recovery_no      — incident report ID
  status_name      — incident status (lowercase: pending, draft, completed, cancelled)
  severity_name    — severity level (critical, high, medium, low)
  department_name  — department name (string, use directly — no JOIN needed)
  incident_name    — type of incident
  category_name    — incident category
  location_name    — property location (string, use directly — no JOIN needed)
  property_name    — hotel/property name (e.g. 'The Peninsula Manila') — filter with WHERE property_name = '...'
  temperament_text — guest temperament (Angry, Calm, Concerned, Disappointed...)
  profile_name     — recovery profile/type
  compensation_text — compensation offered
  created_date     — when incident was logged (TIMESTAMP)
  incident_time    — when incident occurred (TIMESTAMP)
  completed_date   — when resolved (TIMESTAMP)
  cancelled_date   — when cancelled (TIMESTAMP)
  actual_cost      — actual compensation cost (NUMERIC)
  potential_cost   — estimated cost (NUMERIC)
  vip              — VIP guest flag

STATUS SEMANTICS — all values are lowercase:
  "open" incidents → WHERE status_name IN ('pending', 'draft')
  "resolved" / "closed" / "done" → WHERE status_name = 'completed'
  NEVER use Title Case ('Pending', 'Completed') — always lowercase

CORRECT EXAMPLES:
  "how many total incidents":
    SELECT COUNT(*) FROM mv_recovery_all LIMIT 100

  "how many open incidents":
    SELECT COUNT(*) FROM mv_recovery_all
    WHERE status_name IN ('pending', 'draft') LIMIT 100

  "count by status":
    SELECT status_name, COUNT(*) FROM mv_recovery_all
    GROUP BY status_name ORDER BY COUNT(*) DESC LIMIT 100

  "count by severity":
    SELECT severity_name, COUNT(*) FROM mv_recovery_all
    GROUP BY severity_name ORDER BY COUNT(*) DESC LIMIT 100

  "high severity open incidents":
    SELECT COUNT(*) FROM mv_recovery_all
    WHERE severity_name = 'high' AND status_name IN ('pending', 'draft') LIMIT 100

  "count by category":
    SELECT category_name, COUNT(*) FROM mv_recovery_all
    GROUP BY category_name ORDER BY COUNT(*) DESC LIMIT 100

  "count by department":
    SELECT department_name, COUNT(*) FROM mv_recovery_all
    GROUP BY department_name ORDER BY COUNT(*) DESC LIMIT 100

  "monthly trend":
    SELECT DATE_TRUNC('month', created_date) AS month, COUNT(*) AS incidents
    FROM mv_recovery_all GROUP BY 1 ORDER BY 1 LIMIT 100

  "show recent 10 incidents":
    SELECT recovery_no, incident_name, status_name, severity_name, created_date
    FROM mv_recovery_all ORDER BY created_date DESC LIMIT 10

  "average actual cost by category":
    SELECT category_name, AVG(actual_cost) AS avg_cost FROM mv_recovery_all
    WHERE actual_cost > 0 GROUP BY category_name ORDER BY avg_cost DESC LIMIT 100

  "VIP incidents count":
    SELECT COUNT(*) FROM mv_recovery_all
    WHERE vip IS NOT NULL AND vip != '' LIMIT 100

  "percentage completed":
    SELECT CAST(COUNT(CASE WHEN status_name = 'completed' THEN 1 END) AS FLOAT) * 100.0
           / NULLIF(COUNT(*), 0) AS pct_completed
    FROM mv_recovery_all LIMIT 100

RULES:
1. LIMIT required (max 100)
2. Use ONLY columns from mv_recovery_all — never invent column or table names
3. NO JOINs — mv_recovery_all is already fully denormalized
4. All string filters use lowercase values (status_name, severity_name, incident_name, category_name)
5. Date columns (created_date, completed_date, cancelled_date, incident_time) are TIMESTAMP — no casting
6. Redshift date syntax only — NEVER date_add(), date_parse(), or INTERVAL '...':
   - Rolling: WHERE created_date >= DATEADD(day, -30, CURRENT_DATE)
   - This week: WHERE created_date >= DATE_TRUNC('week', CURRENT_DATE)
   - This month: WHERE created_date >= DATE_TRUNC('month', CURRENT_DATE)
   - Last week: WHERE created_date >= DATEADD(week, -1, DATE_TRUNC('week', CURRENT_DATE))
              AND created_date < DATE_TRUNC('week', CURRENT_DATE)
   - Last month: WHERE created_date >= DATEADD(month, -1, DATE_TRUNC('month', CURRENT_DATE))
               AND created_date < DATE_TRUNC('month', CURRENT_DATE)
   - Year: WHERE EXTRACT(YEAR FROM created_date) = EXTRACT(YEAR FROM CURRENT_DATE)
7. Trend: GROUP BY DATE_TRUNC('month'/'week'/'day', created_date) ORDER BY 1
8. Percentage: CAST(COUNT(CASE WHEN <cond> THEN 1 END) AS FLOAT) * 100.0 / NULLIF(COUNT(*), 0)
9. "Recent" no time period: ORDER BY created_date DESC LIMIT N — no date filter
10. NEVER use 'snapshotdate' — use created_date instead{chart_hint}{property_restriction}{entity_context}{enum_hint}"""


def _build_common_parts(
    text, context, sql, redshift_target: str,
    property_uuid: Optional[str] = None,
    user_uuid: Optional[str] = None,
):
    """Shared logic for building schema, instructions, and normalized text."""
    schema = load_schema(redshift_target)
    ddl_schema = schema_to_ddl(schema)
    column_values = load_column_values(redshift_target)
    enum_section = _format_enum_section(column_values)

    property_uuids = [u.strip() for u in property_uuid.split(',') if u.strip()] if property_uuid else []
    normalized_text, matched_entities, entity_hints = preprocess_query(text)

    property_col = find_property_uuid_column(schema)
    if property_col:
        logger.info(f"Detected property UUID column: '{property_col}'")
    else:
        logger.warning("Could not detect property UUID column from schema")

    property_restriction = ""
    if property_uuids and property_col:
        uuid_in_list = ", ".join(f"'{u}'" for u in property_uuids)
        property_restriction = (
            f"\nCRITICAL: Every query MUST include WHERE {property_col} IN ({uuid_in_list}). "
            "This is a mandatory access control filter — never omit it."
        )
    elif property_uuids and not property_col:
        logger.warning(
            f"Property UUIDs provided ({property_uuids}) but no property UUID column found — skipping filter"
        )

    time_hint = get_time_expression_hint(text)
    if time_hint:
        entity_hints = (entity_hints + "\n" + time_hint).strip() if entity_hints else time_hint

    # Hotel/property name detection for incident target
    hotel_hint = ""
    if redshift_target == "incident" and column_values:
        property_names = column_values.get("property_name", [])
        matched_hotel = _match_hotel_name(text, property_names)
        if matched_hotel:
            hotel_hint = f"property_name = '{matched_hotel}'"
            entity_hints = (entity_hints + "\n" + hotel_hint).strip() if entity_hints else hotel_hint
            matched_entities = True
            logger.info(f"Detected hotel in query: '{matched_hotel}'")

    entity_context = (
        f"\nDETECTED ENTITIES (use these exact values):\n{entity_hints}"
        if (matched_entities or time_hint) else ""
    )
    enum_hint = f"\n{enum_section}" if enum_section else ""

    detected_display = get_display_type_from_question(text)
    chart_hint = _build_chart_hint(detected_display)
    if chart_hint:
        logger.info(f"Injecting chart hint for display type: {detected_display}")

    if redshift_target == "incident":
        additional_instructions = _build_incident_instructions(property_restriction, entity_context, enum_hint, chart_hint)
    else:
        additional_instructions = _build_maintenance_instructions(property_restriction, entity_context, enum_hint, chart_hint)

    return normalized_text, ddl_schema, additional_instructions


def build_prompt(
    text, context, sql, redshift_target: str,
    property_uuid: Optional[str] = None,
    user_uuid: Optional[str] = None,
) -> str:
    normalized_text, ddl_schema, additional_instructions = _build_common_parts(
        text, context, sql, redshift_target, property_uuid, user_uuid
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
    text, context, sql, redshift_target: str,
    failed_sql: str, error_message: str,
    property_uuid: Optional[str] = None,
    user_uuid: Optional[str] = None,
) -> str:
    normalized_text, ddl_schema, additional_instructions = _build_common_parts(
        text, context, sql, redshift_target, property_uuid, user_uuid
    )
    error_summary = error_message.split('\n')[0][:300]

    return f"""### Task
The following SQL query failed. Fix it to answer [QUESTION]{normalized_text}[/QUESTION]

Failed SQL:
{failed_sql}

Redshift error:
{error_summary}
{additional_instructions}

### Database Schema
The query will run on a database with the following schema:
{ddl_schema}

### Answer
Given the database schema, here is the corrected SQL query that [QUESTION]{normalized_text}[/QUESTION]
[SQL]"""
