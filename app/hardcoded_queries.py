# app/hardcoded_queries.py
# Hardcoded question-to-SQL mappings for consistent responses
# Questions that match these patterns will bypass ML model generation

from typing import Optional, Dict, Any


# Hardcoded SQL queries for demo questions
# Format: "normalized question text": {"sql": "...", "confidence": float}
HARDCODED_QUERIES = {
    # === TABLE DISPLAY (4 questions) ===
    "show high severity incidents": {
        "sql": "SELECT severity_name, location_name, category_name, status_name, description, incident_time FROM incident_combine WHERE severity_name = 'High' ORDER BY incident_time DESC LIMIT 100",
        "confidence": 1.0,
        "explanation": "Retrieves high severity incidents with location and category details"
    },
    "show incidents with compensation": {
        "sql": "SELECT department_name, compensation_text, actual_cost, status_name, category_name, incident_time FROM incident_combine WHERE compensation_text IS NOT NULL AND compensation_text != '' ORDER BY actual_cost DESC LIMIT 100",
        "confidence": 1.0,
        "explanation": "Lists incidents requiring compensation with department and cost information"
    },
    "show vip incidents": {
        "sql": "SELECT vip, category_name, status_name, severity_name, location_name, description FROM incident_combine WHERE vip = 'Yes' ORDER BY incident_time DESC LIMIT 100",
        "confidence": 1.0,
        "explanation": "Shows VIP guest incidents with category and status"
    },
    "show housekeeping incidents": {
        "sql": "SELECT department_name, category_name, actual_cost, status_name, description, incident_time FROM incident_combine WHERE department_name = 'Housekeeping' ORDER BY actual_cost DESC LIMIT 100",
        "confidence": 1.0,
        "explanation": "Displays housekeeping department incidents with costs"
    },
    # Additional table queries from DEMO_QUESTIONS.md
    "show all completed incidents": {
        "sql": "SELECT category_name, severity_name, status_name, actual_cost, completed_date FROM incident_combine WHERE status_name = 'Completed' ORDER BY completed_date DESC LIMIT 100",
        "confidence": 1.0,
        "explanation": "Shows all completed incidents with completion dates"
    },
    "show incidents with actual cost over 1000": {
        "sql": "SELECT category_name, department_name, actual_cost, severity_name, status_name, description FROM incident_combine WHERE actual_cost > 1000 ORDER BY actual_cost DESC LIMIT 100",
        "confidence": 1.0,
        "explanation": "Shows high-cost incidents over 1000"
    },
    
    # === METRIC DISPLAY (4 questions) ===
    "how many total incidents": {
        "sql": "SELECT COUNT(*) as total_count FROM incident_combine LIMIT 100",
        "confidence": 1.0,
        "explanation": "Counts total number of incidents"
    },
    "what is the total cost": {
        "sql": "SELECT SUM(actual_cost) as total_cost FROM incident_combine LIMIT 100",
        "confidence": 1.0,
        "explanation": "Sums the total actual cost of all incidents"
    },
    "how many vip incidents": {
        "sql": "SELECT COUNT(*) as vip_count FROM incident_combine WHERE vip = 'Yes' LIMIT 100",
        "confidence": 1.0,
        "explanation": "Counts VIP incidents"
    },
    "what is the average cost": {
        "sql": "SELECT AVG(potential_cost) as avg_cost FROM incident_combine LIMIT 100",
        "confidence": 1.0,
        "explanation": "Calculates average potential cost per incident"
    },
    # Additional metric queries from DEMO_QUESTIONS.md
    "what is the total actual cost": {
        "sql": "SELECT SUM(actual_cost) as total_actual_cost FROM incident_combine LIMIT 100",
        "confidence": 1.0,
        "explanation": "Sums the total actual cost of all incidents"
    },
    "how many high severity incidents": {
        "sql": "SELECT COUNT(*) as high_severity_count FROM incident_combine WHERE severity_name = 'High' LIMIT 100",
        "confidence": 1.0,
        "explanation": "Counts high severity incidents"
    },
    
    # === BAR CHART DISPLAY (4 questions) ===
    "count by category": {
        "sql": "SELECT category_name, COUNT(*) as count FROM incident_combine GROUP BY category_name ORDER BY count DESC LIMIT 100",
        "confidence": 1.0,
        "explanation": "Aggregates incident counts by category"
    },
    "count by department": {
        "sql": "SELECT department_name, COUNT(*) as count FROM incident_combine GROUP BY department_name ORDER BY count DESC LIMIT 100",
        "confidence": 1.0,
        "explanation": "Aggregates incident counts by department"
    },
    "cost by severity": {
        "sql": "SELECT severity_name, SUM(actual_cost) as total_cost FROM incident_combine GROUP BY severity_name ORDER BY total_cost DESC LIMIT 100",
        "confidence": 1.0,
        "explanation": "Aggregates total costs by severity level"
    },
    "count by property": {
        "sql": "SELECT property_name, COUNT(*) as count FROM incident_combine GROUP BY property_name ORDER BY count DESC LIMIT 100",
        "confidence": 1.0,
        "explanation": "Aggregates incident counts by property"
    },
    # Additional bar chart queries from DEMO_QUESTIONS.md
    "count by severity": {
        "sql": "SELECT severity_name, COUNT(*) as count FROM incident_combine GROUP BY severity_name ORDER BY count DESC LIMIT 100",
        "confidence": 1.0,
        "explanation": "Aggregates incident counts by severity"
    },
    "count by location": {
        "sql": "SELECT location_name, COUNT(*) as count FROM incident_combine GROUP BY location_name ORDER BY count DESC LIMIT 100",
        "confidence": 1.0,
        "explanation": "Aggregates incident counts by location"
    },
    
    # === PIE CHART DISPLAY (4 questions) ===
    "status distribution": {
        "sql": "SELECT status_name, COUNT(*) as count FROM incident_combine GROUP BY status_name LIMIT 100",
        "confidence": 1.0,
        "explanation": "Shows distribution of incidents by status"
    },
    "severity breakdown": {
        "sql": "SELECT severity_name, COUNT(*) as count FROM incident_combine GROUP BY severity_name LIMIT 100",
        "confidence": 1.0,
        "explanation": "Shows distribution of incidents by severity"
    },
    "vip percentage": {
        "sql": "SELECT vip, COUNT(*) as count FROM incident_combine GROUP BY vip LIMIT 100",
        "confidence": 1.0,
        "explanation": "Shows VIP vs non-VIP incident distribution"
    },
    "temperament distribution": {
        "sql": "SELECT temperament_text, COUNT(*) as count FROM incident_combine GROUP BY temperament_text LIMIT 100",
        "confidence": 1.0,
        "explanation": "Shows distribution by guest temperament"
    },
    # Additional pie chart queries from DEMO_QUESTIONS.md
    "severity distribution": {
        "sql": "SELECT severity_name, COUNT(*) as count FROM incident_combine GROUP BY severity_name LIMIT 100",
        "confidence": 1.0,
        "explanation": "Shows distribution of incidents by severity level"
    },
    "vip vs non-vip": {
        "sql": "SELECT vip, COUNT(*) as count FROM incident_combine GROUP BY vip LIMIT 100",
        "confidence": 1.0,
        "explanation": "Shows VIP vs non-VIP incident distribution"
    },
    "category distribution": {
        "sql": "SELECT category_name, COUNT(*) as count FROM incident_combine GROUP BY category_name LIMIT 100",
        "confidence": 1.0,
        "explanation": "Shows distribution of incidents by category"
    },
    
    # === LINE CHART DISPLAY (4 questions) ===
    "incident trend last 30 days": {
        "sql": "SELECT DATE(FROM_UNIXTIME(created_date / 1000000000)) as date, COUNT(*) as count FROM incident_combine WHERE FROM_UNIXTIME(created_date / 1000000000) >= DATE_ADD(CURRENT_DATE, INTERVAL -30 DAY) GROUP BY DATE(FROM_UNIXTIME(created_date / 1000000000)) ORDER BY date LIMIT 100",
        "confidence": 1.0,
        "explanation": "Shows daily incident count for last 30 days"
    },
    "daily incident count": {
        "sql": "SELECT snapshotdate as date, COUNT(*) as count FROM incident_combine GROUP BY snapshotdate ORDER BY snapshotdate DESC LIMIT 100",
        "confidence": 1.0,
        "explanation": "Shows daily incident counts from snapshot date"
    },
    "completion trend": {
        "sql": "SELECT DATE(FROM_UNIXTIME(completed_date / 1000000000)) as date, COUNT(*) as count FROM incident_combine WHERE completed_date IS NOT NULL AND completed_date > 0 GROUP BY DATE(FROM_UNIXTIME(completed_date / 1000000000)) ORDER BY date LIMIT 100",
        "confidence": 1.0,
        "explanation": "Shows daily completion trend"
    },
    "incidents per day": {
        "sql": "SELECT DATE(FROM_UNIXTIME(incident_time / 1000000000)) as date, COUNT(*) as count FROM incident_combine GROUP BY DATE(FROM_UNIXTIME(incident_time / 1000000000)) ORDER BY date LIMIT 100",
        "confidence": 1.0,
        "explanation": "Shows when incidents occurred per day"
    },
    # Additional line chart queries from DEMO_QUESTIONS.md
    "cost trend last 30 days": {
        "sql": "SELECT snapshotdate as date, SUM(actual_cost) as total_cost FROM incident_combine WHERE snapshotdate >= DATE_ADD(CURRENT_DATE, INTERVAL -30 DAY) GROUP BY snapshotdate ORDER BY snapshotdate LIMIT 100",
        "confidence": 1.0,
        "explanation": "Shows cost trend for last 30 days"
    },
    "high severity trend last 7 days": {
        "sql": "SELECT snapshotdate as date, COUNT(*) as count FROM incident_combine WHERE severity_name = 'High' AND snapshotdate >= DATE_ADD(CURRENT_DATE, INTERVAL -7 DAY) GROUP BY snapshotdate ORDER BY snapshotdate LIMIT 100",
        "confidence": 1.0,
        "explanation": "Shows high severity incident trend for last 7 days"
    },
    "completion trend last 30 days": {
        "sql": "SELECT DATE(FROM_UNIXTIME(completed_date / 1000000000)) as date, COUNT(*) as count FROM incident_combine WHERE completed_date IS NOT NULL AND completed_date > 0 AND FROM_UNIXTIME(completed_date / 1000000000) >= DATE_ADD(CURRENT_DATE, INTERVAL -30 DAY) GROUP BY DATE(FROM_UNIXTIME(completed_date / 1000000000)) ORDER BY date LIMIT 100",
        "confidence": 1.0,
        "explanation": "Shows completion trend for last 30 days"
    },
}


def get_hardcoded_query(question: str) -> Optional[Dict[str, Any]]:
    """
    Check if the question matches a hardcoded query pattern.
    
    Args:
        question: The user's natural language question
        
    Returns:
        Dict with 'sql', 'confidence', and 'explanation' if matched, None otherwise
    """
    # Normalize the question (lowercase, strip whitespace)
    normalized = question.lower().strip()
    
    # Remove common variations
    normalized = normalized.rstrip('?!.')
    
    # Check exact match
    if normalized in HARDCODED_QUERIES:
        return HARDCODED_QUERIES[normalized].copy()
    
    return None


def inject_property_filter(sql: str, property_uuids: list) -> str:
    """
    Inject property UUID filter into hardcoded SQL.
    Adds WHERE clause or extends existing WHERE with AND.
    
    Args:
        sql: Base SQL query
        property_uuids: List of property UUIDs to filter by
        
    Returns:
        SQL with property filter injected
    """
    if not property_uuids:
        return sql
    
    # Create the property filter clause
    uuid_list = "', '".join(property_uuids)
    property_filter = f"property IN ('{uuid_list}')"
    
    # Check if SQL already has WHERE clause
    sql_upper = sql.upper()
    where_idx = sql_upper.find(' WHERE ')
    group_idx = sql_upper.find(' GROUP BY ')
    order_idx = sql_upper.find(' ORDER BY ')
    limit_idx = sql_upper.find(' LIMIT ')
    
    if where_idx != -1:
        # Has WHERE - insert AND condition after WHERE
        # Find the position to insert (before GROUP BY, ORDER BY, or LIMIT)
        insert_positions = [
            (group_idx, ' GROUP BY '),
            (order_idx, ' ORDER BY '),
            (limit_idx, ' LIMIT ')
        ]
        insert_positions = [(pos, clause) for pos, clause in insert_positions if pos != -1]
        
        if insert_positions:
            # Insert before the first clause found
            insert_pos = min(insert_positions, key=lambda x: x[0])
            position, clause = insert_pos
            return f"{sql[:position]} AND {property_filter} {sql[position:]}"
        else:
            # No GROUP BY, ORDER BY, or LIMIT - append at end
            return f"{sql} AND {property_filter}"
    else:
        # No WHERE - need to add it
        # Insert before GROUP BY, ORDER BY, or LIMIT
        insert_positions = [
            (group_idx, ' GROUP BY '),
            (order_idx, ' ORDER BY '),
            (limit_idx, ' LIMIT ')
        ]
        insert_positions = [(pos, clause) for pos, clause in insert_positions if pos != -1]
        
        if insert_positions:
            # Insert WHERE before the first clause found
            insert_pos = min(insert_positions, key=lambda x: x[0])
            position, clause = insert_pos
            return f"{sql[:position]} WHERE {property_filter} {sql[position:]}"
        else:
            # No GROUP BY, ORDER BY, or LIMIT - append at end
            return f"{sql} WHERE {property_filter}"
