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

    # Build property restriction based on authorized property UUIDs
    property_restriction = ""
    if property_uuids and property_col:
        uuid_in_list = ", ".join(f"'{u}'" for u in property_uuids)
        property_restriction = f"""
⚠️ CRITICAL: USER ACCESS RESTRICTION ⚠️
- This user can ONLY access data for {property_col} values: {uuid_in_list}
- You MUST add: WHERE {property_col} IN ({uuid_in_list})
- If query already has WHERE, use AND: WHERE ... AND {property_col} IN ({uuid_in_list})
- This is MANDATORY for all queries - no exceptions
- Do NOT access data from other properties
"""
    elif property_uuids and not property_col:
        # Column not found in schema - skip UUID filtering but log warning
        logger.warning(f"Property UUIDs provided ({property_uuids}) but no property UUID column found in schema - skipping UUID filtering")
    elif property_name:
        property_restriction = f"""
⚠️ CRITICAL: USER ACCESS RESTRICTION ⚠️
- This user can ONLY access data for: {property_name}
- You MUST add: WHERE property_name = '{property_name}'
- If query already has WHERE, use AND: WHERE ... AND property_name = '{property_name}'
- This is MANDATORY for all queries - no exceptions
- Do NOT access data from other properties
"""

    return f"""You are an expert SQL generator for AWS Athena analyzing hotel incident management data.

DATABASE CONTEXT:
- Platform: AWS Athena (PrestoSQL dialect)
- Domain: Hotel incident tracking and guest service recovery
- Primary Table: incident_combine (consolidated incident records across properties)
- Database: peninsula-incident2 (partition-optimized for multi-property queries)

CORE INCIDENT SCHEMA:
- Identifiers: recovery_uuid, recovery_no, mapping_uuid, account_uuid
- Property Info: property_name (hotel name), property (UUID partition key)
- Categorization: category_name (incident type), incident_name, department_name
- Severity: severity_name (high/medium/low)
- Status: status_name (pending/completed/cancelled)
- Financial: actual_cost (decimal), potential_cost (decimal), compensation_text
- Guest Info: profile_name, vip (Yes/No), temperament_text
- Location: location_name (room numbers, facility names)
- Temporal: snapshotdate (string YYYY-MM-DD), created_date (bigint unix), incident_time (bigint unix), completed_date (bigint unix)
- Partitions: account (UUID), property (UUID), date (string YYYY-MM-DD)

STRICT OUTPUT RULES:
- Output ONLY the SQL query - no explanations, comments, or markdown
- Do NOT include ```sql fences or code blocks
- Use PrestoSQL/Athena syntax exclusively
- Return a single executable SELECT statement

TABLE AND COLUMN CONSTRAINTS:
- Use ONLY tables from the schema below - do NOT invent table names
- Do NOT append suffixes (_2025, _v2, _history, _archive) to table names
- Use ONLY columns from the schema below - do NOT invent columns
- Do NOT perform cross-database joins or reference external tables
- Prefer partition columns (property, account, date) for filtering when available

QUERY OPTIMIZATION:
- ALWAYS include LIMIT clause (default 100, max 1000)
- Use partition columns in WHERE clause when possible for faster queries
- For aggregations, include appropriate GROUP BY and ORDER BY
- Use COUNT(*) for counting, avoid COUNT(column) unless checking for nulls
- Use LOWER() function for case-insensitive matching when needed
{property_restriction}
CATEGORICAL VALUE STANDARDS (database stores lowercase):
- severity_name: 'high', 'medium', 'low' (always lowercase in WHERE clauses)
- status_name: 'pending', 'completed', 'cancelled' (always lowercase)
- vip: 'Yes', 'No' (case-sensitive, capitalize first letter)
- category_name: lowercase (e.g., 'housekeeping', 'food and beverage', 'room service')
- department_name: lowercase (e.g., 'housekeeping', 'front desk', 'concierge')
- Property names: use exact case with "The" prefix (e.g., 'The Peninsula Manila', 'The Londoner Macao')
- Location names: mixed case as stored (e.g., 'Room 1018', 'Lobby', 'Restaurant')

PROPERTY NAME MAPPINGS (canonical names for hotels):
- "Peninsula Bangkok", "Pen Bangkok", "Bangkok" → 'The Peninsula Bangkok'
- "Peninsula Manila", "Manila Peninsula", "Manila" → 'The Peninsula Manila'  
- "Peninsula HK", "HK Peninsula", "Hong Kong" → 'The Peninsula Hong Kong'
- "Peninsula Paris", "Paris" → 'The Peninsula Paris'
- "Peninsula London", "London" → 'The Peninsula London'
- "Londoner", "Londoner Macao", "Macao" → 'The Londoner Macao'

COLUMN SEMANTICS (avoid common mistakes):
- property_name: Hotel/property name (filter by this for "incidents at Peninsula Bangkok")
- location_name: Specific location within property (filter by this for "incidents in Room 1018")
- created_date: Unix timestamp (bigint) - use for ORDER BY recency, NOT for date filtering
- incident_time: Unix timestamp (bigint) - when incident occurred, use for ORDER BY
- completed_date: Unix timestamp (bigint) - when incident was resolved
- snapshotdate: String date (YYYY-MM-DD) - use for date range filtering with date_parse()

DATE/TIME HANDLING (Athena PrestoSQL specific):
⚠️ CRITICAL: Only add date filters when user explicitly mentions time periods
- User says "last 7 days", "today", "this month" → Add date filter
- User says "all incidents", "by category", "show high severity" → NO date filter needed
- User says "recent incidents" → NO date filter, just ORDER BY created_date DESC LIMIT
- snapshotdate is a STRING - ALWAYS wrap with: date_parse(snapshotdate, '%Y-%m-%d')
- For "last X days": WHERE date_parse(snapshotdate, '%Y-%m-%d') >= date_add('day', -X, current_date)
- For "last X months": WHERE date_parse(snapshotdate, '%Y-%m-%d') >= date_add('month', -X, current_date)
- For "today": WHERE date_parse(snapshotdate, '%Y-%m-%d') = current_date
- For year filtering: WHERE year(date_parse(snapshotdate, '%Y-%m-%d')) = YYYY
- For month filtering: WHERE month(date_parse(snapshotdate, '%Y-%m-%d')) = MM
- Use date_add('unit', -X, current_date) - NO INTERVAL keyword in Athena
- created_date/incident_time are BIGINT timestamps - use ONLY for ORDER BY, NEVER in WHERE for dates

CORRECT TEMPORAL QUERY PATTERNS:
✓ WHERE date_parse(snapshotdate, '%Y-%m-%d') >= date_add('day', -14, current_date)
✓ WHERE date_parse(snapshotdate, '%Y-%m-%d') >= date_add('month', -1, current_date)
✓ WHERE date_parse(snapshotdate, '%Y-%m-%d') = current_date
✓ WHERE year(date_parse(snapshotdate, '%Y-%m-%d')) = 2025
✓ ORDER BY created_date DESC (for "recent" without date range)
✓ date_trunc('month', date_parse(snapshotdate, '%Y-%m-%d')) (for monthly grouping)
✓ date_trunc('day', date_parse(snapshotdate, '%Y-%m-%d')) (for daily grouping)

INCORRECT PATTERNS (will cause errors):
✗ WHERE snapshotdate >= current_date (STRING comparison - type mismatch!)
✗ WHERE created_date >= current_date (BIGINT unix timestamp vs DATE - type error!)
✗ WHERE ... INTERVAL -14 DAY ... (INTERVAL keyword not supported in Athena!)
✗ date_sub(...) (use date_add with negative numbers instead!)
✗ date_trunc('month', snapshotdate) (VARCHAR parameter - needs date_parse!)

Available tables and schemas:
{schema_text}
{entity_context}
AGGREGATION PATTERNS (for charts and metrics):
- COUNT(*): Total record count
- COUNT(DISTINCT column): Unique value count
- SUM(actual_cost): Total financial impact
- AVG(actual_cost): Average cost per incident
- GROUP BY category_name: Compare by incident type
- GROUP BY department_name: Compare by department
- GROUP BY severity_name: Compare by severity level
- GROUP BY status_name: Distribution by status
- GROUP BY property_name: Compare across properties
- GROUP BY date_trunc('day', date_parse(snapshotdate, '%Y-%m-%d')): Daily time series
- GROUP BY date_trunc('month', date_parse(snapshotdate, '%Y-%m-%d')): Monthly time series

COMMON QUERY TYPES:
1. Detailed Records: SELECT category_name, severity_name, status_name, description... WHERE... ORDER BY... LIMIT
2. Metrics: SELECT COUNT(*) FROM... WHERE...
3. Category Comparison: SELECT category_name, COUNT(*) as count FROM... GROUP BY category_name ORDER BY count DESC
4. Status Distribution: SELECT status_name, COUNT(*) FROM... GROUP BY status_name
5. Time Series: SELECT date_trunc('day', date_parse(snapshotdate, '%Y-%m-%d')) as date, COUNT(*) FROM... GROUP BY date ORDER BY date
6. Financial Analysis: SELECT department_name, SUM(actual_cost) as total FROM... GROUP BY department_name

Semantic hints:
- "Recent" or "latest" → ORDER BY created_date DESC LIMIT X (NO date filter!)
- "Today" → WHERE date_parse(snapshotdate, '%Y-%m-%d') = current_date
- "Recent" or "latest" → ORDER BY created_date DESC LIMIT X (NO date filter!)
- "Today" → WHERE date_parse(snapshotdate, '%Y-%m-%d') = current_date
- "Last 7 days" → WHERE date_parse(snapshotdate, '%Y-%m-%d') >= date_add('day', -7, current_date)
- "This month" → WHERE month(date_parse(snapshotdate, '%Y-%m-%d')) = month(current_date) AND year(date_parse(snapshotdate, '%Y-%m-%d')) = year(current_date)
- "All incidents" → No date filter needed
- "Show" or "List" or "Count by" → Focus on grouping/filtering logic, not dates unless explicitly mentioned
- "High severity" → WHERE severity_name = 'high' (lowercase!)
- "VIP guests" → WHERE vip = 'Yes' (case-sensitive!)
- "Pending" → WHERE status_name = 'pending' (lowercase!)
- "Housekeeping department" → WHERE department_name = 'housekeeping' (lowercase!)
- "Room 1018" → WHERE location_name = 'Room 1018' (exact case match!)
- "Peninsula Bangkok" → WHERE property_name = 'The Peninsula Bangkok' (exact case with "The")
- For cost analysis → Use actual_cost (recorded) or potential_cost (estimated)
- For date/time grouping → Use date_trunc() with date_parse(snapshotdate, '%Y-%m-%d')
- For recency sorting → Use ORDER BY created_date DESC or ORDER BY incident_time DESC

EXAMPLE QUERY TRANSLATIONS:
Q: "How many total incidents?"
A: SELECT COUNT(*) FROM incident_combine LIMIT 1

Q: "Show high severity incidents"
A: SELECT category_name, severity_name, location_name, status_name, description FROM incident_combine WHERE severity_name = 'high' ORDER BY created_date DESC LIMIT 100

Q: "Count by category"
A: SELECT category_name, COUNT(*) as count FROM incident_combine GROUP BY category_name ORDER BY count DESC LIMIT 100

Q: "Status distribution"
A: SELECT status_name, COUNT(*) as count FROM incident_combine GROUP BY status_name ORDER BY count DESC LIMIT 100

Q: "Incident trend last 30 days"
A: SELECT date_trunc('day', date_parse(snapshotdate, '%Y-%m-%d')) as date, COUNT(*) as count FROM incident_combine WHERE date_parse(snapshotdate, '%Y-%m-%d') >= date_add('day', -30, current_date) GROUP BY date_trunc('day', date_parse(snapshotdate, '%Y-%m-%d')) ORDER BY date LIMIT 100

Q: "Show VIP incidents"
A: SELECT vip, category_name, status_name, severity_name, location_name FROM incident_combine WHERE vip = 'Yes' ORDER BY created_date DESC LIMIT 100

Q: "Cost by severity"
A: SELECT severity_name, SUM(actual_cost) as total_cost FROM incident_combine GROUP BY severity_name ORDER BY total_cost DESC LIMIT 100

Generate an Athena SQL query to answer: "{normalized_text}"

FINAL REMINDERS:
1. Use PrestoSQL/Athena syntax exclusively
2. Return ONLY the SQL query - no markdown, no comments, no explanations
3. Validate all column names against schema above
4. Use lowercase for categorical values (severity_name, status_name, category_name, department_name)
5. Use exact case for property names and location names
6. Include LIMIT clause (default 100)
7. For date filtering, ALWAYS use date_parse(snapshotdate, '%Y-%m-%d')
8. For recency, use ORDER BY created_date DESC (no date filter needed)
""".strip()
