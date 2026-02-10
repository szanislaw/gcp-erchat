from app.schema_loader import load_schema, compress_schema
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


def build_prompt(text, context, sql, athena_target: str, property_uuid: Optional[str] = None, user_uuid: Optional[str] = None) -> str:
    schema = load_schema(athena_target)
    schema_text = compress_schema(schema)
    
    # Parse comma-separated property UUIDs (pre-authorized by upstream service)
    property_uuids = []
    if property_uuid:
        property_uuids = [u.strip() for u in property_uuid.split(',') if u.strip()]
    
    # Property name from context (authentication handled externally)
    property_name = getattr(context, 'location_name', None)
    
    # Preprocess the query to normalize entity names
    normalized_text, matched_entities, entity_hints = preprocess_query(text)
    
    # Build entity context section if entities were matched
    entity_context = ""
    if matched_entities:
        entity_context = f"""
DETECTED ENTITIES (use these exact values):
{entity_hints}
"""

    # Detect the actual property UUID column name from Glue schema
    property_col = _find_property_uuid_column(schema)
    if property_col:
        logger.info(f"Detected property UUID column: '{property_col}'")
    else:
        logger.warning("Could not detect property UUID column from schema")

    # Optional property filtering (not mandatory)
    property_restriction = ""
    if property_uuids and property_col:
        uuid_in_list = ", ".join(f"'{u}'" for u in property_uuids)
        property_restriction = f"""
PROPERTY FILTERING (Optional):
- Property UUIDs provided: {uuid_in_list}
- To filter by property, add: WHERE {property_col} IN ({uuid_in_list})
- Only use this filter if it makes sense for the query context
"""
    elif property_name:
        property_restriction = f"""
PROPERTY FILTERING (Optional):
- Property name provided: {property_name}
- To filter by property, add: WHERE property_name = '{property_name}'
- Only use this filter if it makes sense for the query context
"""

    return f"""You are an expert SQL generator for AWS Athena (PrestoSQL).

STRICT RULES:
- Output ONLY the SQL query, nothing else
- Do NOT include explanations before or after the query
- Do NOT include comments
- Do NOT include markdown code fences like ```sql
- Use PrestoSQL syntax ONLY
- Use ONLY the tables listed below - do NOT invent or guess table names
- Do NOT append suffixes like _2025, _v2, _history to table names
- Use ONLY the columns listed below
- Do NOT invent columns
- DO NOT perform cross-database joins
- Prefer partition columns when filtering
- ALWAYS include a LIMIT clause (respect the requested number, max 100)
- Use LOWERCASE for categorical values (severity_name, status_name, etc.)
- Use EXACT CASE for property names and location names (e.g., 'The Peninsula Manila')
- Use LOWER() function for case-insensitive matching when needed

COLUMN SELECTION RULES:
⚠️ IMPORTANT: Select ONLY the columns mentioned in the user's question
- For "show me X with Y and Z" → SELECT Y, Z, X FROM ... (only relevant columns)
- For "list incidents with department and status" → SELECT department_name, status_name, ... 
- For "display vip incidents with category" → SELECT vip, category_name, ...
- For "show high severity with location" → SELECT severity_name, location_name, ...
- Add WHERE clause columns to SELECT if they provide context
- AVOID SELECT * unless user explicitly asks for "all columns" or "everything about"
- For aggregations, SELECT only the grouped column and aggregated value
- For detailed views, include: primary identifiers (recovery_no), key columns (category_name, status_name), and specifically mentioned columns

EXAMPLES:
✓ "show high severity incidents with location" → SELECT severity_name, location_name, category_name, status_name, recovery_no FROM incident_combine WHERE severity_name = 'high'
✓ "list incidents with department and cost" → SELECT department_name, actual_cost, category_name, status_name, recovery_no FROM incident_combine
✓ "display vip incidents with category and status" → SELECT vip, category_name, status_name, severity_name, recovery_no FROM incident_combine WHERE vip = 'Yes'
✗ "show high severity incidents" → SELECT * FROM incident_combine WHERE severity_name = 'high' (too broad!)
{property_restriction}
DATE FILTERING RULES (ONLY WHEN USER ASKS ABOUT DATES/TIME):
⚠️ IMPORTANT: Only add date filters if the user question mentions dates, time periods, or temporal context
- Examples needing date filters: "today", "yesterday", "last 7 days", "this month", "in 2025"
- Examples NOT needing date filters: "count by department", "all incidents", "by severity"
- snapshotdate is a STRING - ALWAYS write: date_parse(snapshotdate, '%Y-%m-%d')
- For any date comparisons: date_parse(snapshotdate, '%Y-%m-%d') >= date_add('day', -X, current_date)
- Exact syntax: date_add('day', -14, current_date) NOT date_add(INTERVAL -14 DAY, ...)
- Use date_add() with NEGATIVE numbers (NO date_sub or INTERVAL keywords)
- created_date/incident_time are BIGINT - ONLY use for ORDER BY, NEVER in WHERE for dates
- For year-based filtering: WHERE year(date_parse(snapshotdate, '%Y-%m-%d')) = YYYY

Available tables and schemas:
{schema_text}
{entity_context}
Semantic hints:
- For "recent" queries (without specific time period): Use ORDER BY created_date DESC LIMIT X - NO date filtering needed
- ⚠️ "Recent" means "most recent records", not "last N days" - just sort by timestamp
- For "most recent", prefer bigint timestamp columns such as created_date or incident_time for ORDER BY
- Do not use string date columns for recency ordering if bigint timestamps exist
- Categorical values (severity_name, status_name, category_name, etc.) are lowercase in the database
- Use lowercase values: 'high', 'medium', 'low' for severity
- Use lowercase values: 'pending', 'completed', 'cancelled' for status
- property_name = hotel/property name (e.g., 'The Peninsula Manila', 'The Peninsula London')
- location_name = room number or specific location within property (e.g., 'Room 1018', 'Lobby')
- When filtering by hotel/property, use property_name column, NOT location_name

PROPERTY NAME ALIASES (use canonical names):
- "Peninsula Bangkok", "Pen Bangkok" → 'The Peninsula Bangkok'
- "Peninsula Manila", "Manila Peninsula" → 'The Peninsula Manila'  
- "Peninsula HK", "HK Peninsula" → 'The Peninsula Hong Kong'
- "Londoner", "Londoner Macao" → 'The Londoner Macao'

Date/Time handling:
Step-by-step for ANY date query:
1. snapshotdate is STRING → wrap with date_parse(snapshotdate, '%Y-%m-%d')
2. Use date_add('day', -X, current_date) for "last X days" - NO INTERVAL keyword
3. Use date_add('month', -X, current_date) for "last X months" - NO INTERVAL keyword

Real examples (exact syntax):
✓ WHERE date_parse(snapshotdate, '%Y-%m-%d') >= date_add('day', -14, current_date)
✓ WHERE date_parse(snapshotdate, '%Y-%m-%d') >= date_add('month', -1, current_date)
✓ WHERE date_parse(snapshotdate, '%Y-%m-%d') = current_date
✓ WHERE year(date_parse(snapshotdate, '%Y-%m-%d')) = 2025
✓ WHERE year(date_parse(snapshotdate, '%Y-%m-%d')) = 2025 AND month(date_parse(snapshotdate, '%Y-%m-%d')) = 6
✓ date_trunc('month', date_parse(snapshotdate, '%Y-%m-%d'))
✓ date_trunc('year', date_parse(snapshotdate, '%Y-%m-%d'))

Wrong examples (cause errors):
✗ WHERE snapshotdate >= current_date (STRING comparison fails!)
✗ WHERE created_date >= current_date (BIGINT comparison fails!)
✗ WHERE ... INTERVAL -14 DAY ... (INTERVAL keyword not supported!)
✗ date_trunc('month', snapshotdate) (VARCHAR parameter fails!)

Generate an Athena SQL query to answer the following question: "{normalized_text}"

Important: 
1. Use PrestoSQL / Athena syntax.
2. Return ONLY the SQL query.
""".strip()
