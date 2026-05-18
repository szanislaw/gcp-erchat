# app/chart_formatter.py
# Transform Redshift query results into chart-ready format

from typing import Dict, Any, List, Optional


def format_for_chart(execution_data: Dict[str, Any], display_type: str) -> Optional[Dict[str, Any]]:
    """
    Transform raw Redshift results into chart-friendly format.
    
    Returns:
        Chart data structure with labels and values, or None if not applicable
    """
    if not execution_data or not execution_data.get("rows"):
        return None
    
    rows = execution_data["rows"]
    columns = execution_data.get("columns", [])
    
    # Metric display - single value
    if display_type == "metric":
        if len(rows) == 1 and len(columns) >= 1:
            first_col = columns[0]
            value = rows[0].get(first_col)
            return {
                "value": value,
                "label": first_col
            }
        return None
    
    # Bar/Pie/Line charts - need labels and values
    if display_type in ["bar", "pie", "line"]:
        if len(columns) < 2 or len(rows) == 0:
            return None
        
        # Assume first column is labels, second column is values
        label_col = columns[0]
        value_col = columns[1]
        
        labels = []
        values = []
        
        for row in rows:
            label = row.get(label_col)
            value = row.get(value_col)
            
            # Skip null labels
            if label is None:
                continue
                
            labels.append(str(label))
            
            # Handle null values
            try:
                values.append(float(value) if value is not None else 0)
            except (ValueError, TypeError):
                values.append(0)
        
        return {
            "labels": labels,
            "values": values,
            "label_column": label_col,
            "value_column": value_col
        }
    
    # Table display - return raw data
    return None
