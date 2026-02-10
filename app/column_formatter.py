# app/column_formatter.py
# Utility to format raw Athena column names into human-readable display names

import re
from typing import List, Dict, Any


def format_column_name(column: str) -> str:
    """
    Transform raw database column names into human-readable display names.
    
    Examples:
        snapshotdate → Date
        category_name → Category
        actual_cost → Actual Cost
        vip → VIP
        department_name → Department
        created_date → Created Date
    
    Args:
        column: Raw column name from database
        
    Returns:
        Formatted display name
    """
    # Handle special cases first
    special_cases = {
        "vip": "VIP",
        "uuid": "UUID",
        "id": "ID",
        "url": "URL",
        "api": "API",
        "ip": "IP",
    }
    
    # Check if entire column matches a special case
    if column.lower() in special_cases:
        return special_cases[column.lower()]
    
    # Remove common suffixes that are redundant in display
    # e.g., "category_name" → "category" → "Category"
    suffixes_to_remove = ["_name", "_text", "_no", "_uuid", "_id"]
    cleaned = column
    for suffix in suffixes_to_remove:
        if cleaned.lower().endswith(suffix):
            cleaned = cleaned[:-len(suffix)]
            break
    
    # Split by underscore
    parts = cleaned.split("_")
    
    # Split camelCase or concatenated words
    expanded_parts = []
    for part in parts:
        # Insert space before capital letters in camelCase
        spaced = re.sub(r'([a-z])([A-Z])', r'\1 \2', part)
        
        # Handle common concatenated patterns (e.g., "snapshotdate" → "snapshot date")
        # Look for known word boundaries
        common_words = [
            'snapshot', 'date', 'time', 'created', 'updated', 'completed', 'cancelled',
            'incident', 'actual', 'potential', 'category', 'department', 'severity',
            'status', 'location', 'profile', 'property', 'account', 'recovery',
            'compensation', 'temperament', 'description', 'mapping'
        ]
        
        # Try to split on known word boundaries
        remaining = spaced.lower()
        word_parts = []
        while remaining:
            found = False
            for word in sorted(common_words, key=len, reverse=True):  # Try longest first
                if remaining.startswith(word):
                    word_parts.append(word)
                    remaining = remaining[len(word):]
                    found = True
                    break
            if not found:
                # No match, try generic split
                words = re.findall(r'[a-z]+|[A-Z][a-z]*', remaining)
                if words:
                    word_parts.extend(words)
                break
        
        if word_parts:
            expanded_parts.extend(word_parts)
        else:
            expanded_parts.append(part)
    
    # Capitalize each word and join
    formatted = " ".join(word.capitalize() for word in expanded_parts if word)
    
    # Handle special acronyms after capitalization
    for key, value in special_cases.items():
        # Replace whole words only
        formatted = re.sub(rf'\b{key.capitalize()}\b', value, formatted, flags=re.IGNORECASE)
    
    return formatted


def format_columns(columns: List[str]) -> List[str]:
    """
    Format a list of column names.
    
    Args:
        columns: List of raw column names
        
    Returns:
        List of formatted column names
    """
    return [format_column_name(col) for col in columns]


def format_execution_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format execution data with cleaned column names while preserving original keys in rows.
    
    Args:
        data: Execution data dict with 'columns' and 'rows' keys
        
    Returns:
        New dict with formatted column names and remapped row keys
    """
    if not data or "columns" not in data or "rows" not in data:
        return data
    
    original_columns = data["columns"]
    formatted_columns = format_columns(original_columns)
    
    # Create mapping from original to formatted names
    column_mapping = dict(zip(original_columns, formatted_columns))
    
    # Remap row keys to use formatted column names
    formatted_rows = []
    for row in data["rows"]:
        formatted_row = {
            column_mapping.get(key, key): value 
            for key, value in row.items()
        }
        formatted_rows.append(formatted_row)
    
    return {
        "columns": formatted_columns,
        "rows": formatted_rows,
        "row_count": data.get("row_count", len(formatted_rows))
    }
