from app.schema_loader import load_schema, compress_schema
from app.query_normalizer import preprocess_query
from typing import Optional


def build_prompt(text, context, sql, athena_target: str, property_uuid: Optional[str] = None, user_uuid: Optional[str] = None) -> str:
    schema = load_schema(athena_target)
    schema_text = compress_schema(schema)
    
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

    # Build property restriction if property name is provided (from user UUID validation)
    property_restriction = ""
    if property_name:
        property_restriction = f"""
⚠️ CRITICAL: USER ACCESS RESTRICTION ⚠️
- This user can ONLY access data for: {property_name}
- You MUST add: WHERE property_name = '{property_name}'
- If query already has WHERE, use AND: WHERE ... AND property_name = '{property_name}'
- This is MANDATORY for all queries - no exceptions
- Do NOT access data from other properties
"""

    return f"""You are an expert SQL generator for AWS Athena (PrestoSQL).

STRICT RULES:
- Output ONLY the SQL query, nothing else
- Do NOT include explanations before or after the query
- Do NOT include comments
- Do NOT include markdown code fences like ```sql
- Use PrestoSQL syntax ONLY
- Use ONLY the columns listed below
- Do NOT invent columns
- DO NOT perform cross-database joins
- Prefer partition columns when filtering
- ALWAYS include a LIMIT clause (respect the requested number, max 100)
- Use LOWERCASE for categorical values (severity_name, status_name, etc.)
- Use EXACT CASE for property names and location names (e.g., 'The Peninsula Manila')
- Use LOWER() function for case-insensitive matching when needed
{property_restriction}
DATE FILTERING RULES (MANDATORY):
- snapshotdate is a STRING - ALWAYS write: date_parse(snapshotdate, '%Y-%m-%d')
- For any date comparisons: date_parse(snapshotdate, '%Y-%m-%d') >= date_add('day', -X, current_date)
- Exact syntax: date_add('day', -14, current_date) NOT date_add(INTERVAL -14 DAY, ...)
- Use date_add() with NEGATIVE numbers (NO date_sub or INTERVAL keywords)
- created_date/incident_time are BIGINT - ONLY use for ORDER BY, NEVER in WHERE for dates

Available tables and schemas:
{schema_text}
{entity_context}
Semantic hints:
- For "most recent", prefer bigint timestamp columns such as created_date or incident_time
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

Wrong examples (cause errors):
✗ WHERE snapshotdate >= current_date (STRING comparison fails!)
✗ WHERE created_date >= current_date (BIGINT comparison fails!)
✗ WHERE ... INTERVAL -14 DAY ... (INTERVAL keyword not supported!)

Generate a SQL query for this request:
{normalized_text}

Return only the SQL query:""".strip()
