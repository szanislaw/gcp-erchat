#!/usr/bin/env python3
"""Test hardcoded query functionality"""

import sys
sys.path.insert(0, '/home/shawnyzy/Documents/GitHub/gcp-erchat')

from app.hardcoded_queries import get_hardcoded_query, inject_property_filter

print("=" * 70)
print("HARDCODED QUERY TEST")
print("=" * 70)
print()

# Test questions
test_questions = [
    "How many total incidents",
    "Show high severity incidents",
    "Count by category",
    "Status distribution",
    "incident trend last 30 days",
    "This question is not hardcoded"
]

for question in test_questions:
    result = get_hardcoded_query(question)
    if result:
        print(f"✅ MATCHED: '{question}'")
        print(f"   SQL: {result['sql'][:80]}...")
        print(f"   Confidence: {result['confidence']}")
        print()
    else:
        print(f"❌ NO MATCH: '{question}'")
        print(f"   Will use ML model")
        print()

print("=" * 70)
print("PROPERTY FILTER INJECTION TEST")
print("=" * 70)
print()

# Test property filter injection
base_sql = "SELECT COUNT(*) as total_count FROM incident_combine LIMIT 100"
property_uuids = ["c7254cc9-9145-4602-b44b-0c1cff335f83", "2b618b46-6b80-481b-b1e3-5aec1647b926"]

print("Base SQL:")
print(f"  {base_sql}")
print()
print("Property UUIDs:")
for uuid in property_uuids:
    print(f"  - {uuid}")
print()

filtered_sql = inject_property_filter(base_sql, property_uuids)
print("Filtered SQL:")
print(f"  {filtered_sql}")
print()

# Test with GROUP BY
base_sql_group = "SELECT category_name, COUNT(*) as count FROM incident_combine GROUP BY category_name ORDER BY count DESC LIMIT 100"
filtered_sql_group = inject_property_filter(base_sql_group, property_uuids)
print("With GROUP BY:")
print(f"  Original: {base_sql_group}")
print(f"  Filtered: {filtered_sql_group}")
print()

# Test with WHERE
base_sql_where = "SELECT * FROM incident_combine WHERE severity_name = 'High' ORDER BY incident_time DESC LIMIT 100"
filtered_sql_where = inject_property_filter(base_sql_where, property_uuids)
print("With WHERE:")
print(f"  Original: {base_sql_where}")
print(f"  Filtered: {filtered_sql_where}")
