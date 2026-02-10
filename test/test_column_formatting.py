#!/usr/bin/env python3
"""Test column name formatting"""

import sys
sys.path.insert(0, '/home/shawnyzy/Documents/GitHub/gcp-erchat')

from app.column_formatter import format_column_name, format_columns, format_execution_data

# Test individual column names
test_columns = [
    "snapshotdate",
    "group_name",
    "account_uuid",
    "property_name",
    "recovery_uuid",
    "recovery_no",
    "category_name",
    "incident_name",
    "profile_name",
    "department_name",
    "severity_name",
    "mapping_uuid",
    "compensation_text",
    "potential_cost",
    "actual_cost",
    "status_name",
    "location_name",
    "vip",
    "temperament_text",
    "description",
    "created_date",
    "incident_time",
    "completed_date",
    "cancelled_date"
]

print("=" * 60)
print("COLUMN NAME FORMATTING TEST")
print("=" * 60)
print()

for col in test_columns:
    formatted = format_column_name(col)
    print(f"{col:25s} → {formatted}")

print()
print("=" * 60)
print("EXECUTION DATA FORMATTING TEST")
print("=" * 60)
print()

# Test full execution data formatting
sample_data = {
    "columns": ["category_name", "severity_name", "actual_cost", "status_name"],
    "rows": [
        {
            "category_name": "Housekeeping",
            "severity_name": "High",
            "actual_cost": "150.50",
            "status_name": "Completed"
        },
        {
            "category_name": "Food & Beverage",
            "severity_name": "Medium",
            "actual_cost": "75.25",
            "status_name": "Pending"
        }
    ],
    "row_count": 2
}

formatted_data = format_execution_data(sample_data)

print("Original columns:", sample_data["columns"])
print("Formatted columns:", formatted_data["columns"])
print()
print("Original row keys:", list(sample_data["rows"][0].keys()))
print("Formatted row keys:", list(formatted_data["rows"][0].keys()))
print()
print("Sample formatted row:")
print(formatted_data["rows"][0])
