#!/usr/bin/env python3
"""Get table schema from AWS Glue"""

import sys
sys.path.insert(0, '/home/shawnyzy/Documents/GitHub/gcp-erchat')

from app.schema_loader import load_schema
import json

# Load schema for peninsula_incident target
schema = load_schema("peninsula_incident")

# Print columns for incident_combine table
if "incident_combine" in schema:
    table_schema = schema["incident_combine"]
    print("incident_combine columns:")
    print("=" * 60)
    for col in table_schema["columns"]:
        print(f"  - {col['name']} ({col['type']})")
    
    print(f"\nTotal columns: {len(table_schema['columns'])}")
    
    print("\nPartitions:")
    for part in table_schema.get("partitions", []):
        print(f"  - {part['name']} ({part['type']})")
