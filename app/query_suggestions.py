"""
Query Suggestions Generator
Analyzes database schema and generates sample natural language queries
"""

from typing import List, Dict, Any
from app.schema_loader import load_schema
from app.redshift_config import REDSHIFT_TARGETS


def analyze_schema(target_name: str) -> Dict[str, Any]:
    """
    Analyze the database schema and extract useful information
    for generating query suggestions.
    """
    schema = load_schema(target_name)
    cfg = REDSHIFT_TARGETS[target_name]

    analysis = {
        "target": target_name,
        "schema": cfg["schema"],
        "tables": []
    }
    
    for table_name, table_info in schema.items():
        table_analysis = {
            "name": table_name,
            "columns": [],
            "numeric_columns": [],
            "date_columns": [],
            "text_columns": [],
            "categorical_columns": [],
            "partitions": table_info.get("partitions", [])
        }
        
        for col in table_info["columns"]:
            col_name = col["name"]
            col_type = col["type"].lower()
            
            table_analysis["columns"].append({
                "name": col_name,
                "type": col_type
            })
            
            # Categorize columns by type
            if any(t in col_type for t in ["int", "bigint", "decimal", "double", "float"]):
                table_analysis["numeric_columns"].append(col_name)
            
            if any(t in col_type for t in ["date", "timestamp"]) or "date" in col_name or "time" in col_name:
                table_analysis["date_columns"].append(col_name)
            
            if "string" in col_type or "varchar" in col_type:
                if any(keyword in col_name for keyword in ["name", "status", "category", "type", "severity", "department"]):
                    table_analysis["categorical_columns"].append(col_name)
                else:
                    table_analysis["text_columns"].append(col_name)
        
        analysis["tables"].append(table_analysis)
    
    return analysis


def generate_query_suggestions(target_name: str) -> List[Dict[str, str]]:
    """
    Generate suggested natural language queries based on the database schema.
    """
    analysis = analyze_schema(target_name)
    suggestions = []
    
    for table in analysis["tables"]:
        table_name = table["name"]
        
        # Basic queries
        suggestions.append({
            "category": "Basic",
            "query": f"Show all {table_name}",
            "description": f"Retrieve all records from {table_name} table"
        })
        
        suggestions.append({
            "category": "Basic",
            "query": f"Show me 10 {table_name}",
            "description": f"Get a sample of records from {table_name}"
        })
        
        # Date-based queries
        if table["date_columns"]:
            date_col = table["date_columns"][0]
            
            suggestions.append({
                "category": "Time-based",
                "query": f"Show recent {table_name}",
                "description": f"Get the most recent records based on {date_col}"
            })
            
            suggestions.append({
                "category": "Time-based",
                "query": f"Show {table_name} from last 7 days",
                "description": f"Filter records from the past week"
            })
            
            suggestions.append({
                "category": "Time-based",
                "query": f"Show {table_name} from today",
                "description": f"Get today's records"
            })
        
        # Categorical queries
        for cat_col in table["categorical_columns"]:
            col_display = cat_col.replace("_", " ")
            
            suggestions.append({
                "category": "Filtering",
                "query": f"Show {table_name} by {col_display}",
                "description": f"Group or filter by {col_display}"
            })
            
            if "status" in cat_col.lower():
                suggestions.append({
                    "category": "Filtering",
                    "query": f"Show pending {table_name}",
                    "description": f"Filter by pending status"
                })
                
                suggestions.append({
                    "category": "Filtering",
                    "query": f"Show completed {table_name}",
                    "description": f"Filter by completed status"
                })
            
            if "severity" in cat_col.lower():
                suggestions.append({
                    "category": "Filtering",
                    "query": f"Show high severity {table_name}",
                    "description": f"Filter by high severity"
                })
        
        # Numeric aggregations
        if table["numeric_columns"]:
            for num_col in table["numeric_columns"][:2]:  # Limit to first 2
                col_display = num_col.replace("_", " ")
                
                suggestions.append({
                    "category": "Analytics",
                    "query": f"What is the total {col_display}",
                    "description": f"Calculate sum of {col_display}"
                })
                
                suggestions.append({
                    "category": "Analytics",
                    "query": f"What is the average {col_display}",
                    "description": f"Calculate average {col_display}"
                })
        
        # Count queries
        suggestions.append({
            "category": "Analytics",
            "query": f"How many {table_name} are there",
            "description": f"Count total records in {table_name}"
        })
        
        if table["categorical_columns"]:
            cat_col = table["categorical_columns"][0]
            col_display = cat_col.replace("_", " ")
            
            suggestions.append({
                "category": "Analytics",
                "query": f"Count {table_name} by {col_display}",
                "description": f"Group count by {col_display}"
            })
        
        # Combined queries
        if table["date_columns"] and table["categorical_columns"]:
            cat_col = table["categorical_columns"][0]
            col_display = cat_col.replace("_", " ")
            
            suggestions.append({
                "category": "Combined",
                "query": f"Show recent {table_name} by {col_display}",
                "description": f"Recent records grouped by {col_display}"
            })
        
        # Top N queries
        if table["numeric_columns"] and table["categorical_columns"]:
            num_col = table["numeric_columns"][0]
            cat_col = table["categorical_columns"][0]
            num_display = num_col.replace("_", " ")
            cat_display = cat_col.replace("_", " ")
            
            suggestions.append({
                "category": "Top/Bottom",
                "query": f"Top 10 {table_name} by {num_display}",
                "description": f"Highest values of {num_display}"
            })
    
    return suggestions


def get_schema_summary(target_name: str) -> Dict[str, Any]:
    """
    Get a human-readable summary of the database schema.
    """
    analysis = analyze_schema(target_name)
    cfg = REDSHIFT_TARGETS[target_name]

    summary = {
        "target": target_name,
        "schema": cfg["schema"],
        "tables": []
    }
    
    for table in analysis["tables"]:
        table_summary = {
            "name": table["name"],
            "total_columns": len(table["columns"]),
            "column_types": {
                "numeric": len(table["numeric_columns"]),
                "date": len(table["date_columns"]),
                "categorical": len(table["categorical_columns"]),
                "text": len(table["text_columns"])
            },
            "key_columns": {
                "dates": table["date_columns"],
                "categories": table["categorical_columns"],
                "metrics": table["numeric_columns"][:5]  # First 5 numeric columns
            },
            "partitions": table["partitions"],
            "all_columns": [col["name"] for col in table["columns"]]
        }
        summary["tables"].append(table_summary)
    
    return summary
