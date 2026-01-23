#!/usr/bin/env python3
"""
Test script to generate and display query suggestions
"""

from app.query_suggestions import generate_query_suggestions, get_schema_summary
import json

print("=" * 80)
print("DATABASE SCHEMA SUMMARY")
print("=" * 80)

schema = get_schema_summary("peninsula_incident")
print(json.dumps(schema, indent=2))

print("\n" + "=" * 80)
print("SUGGESTED QUERIES")
print("=" * 80)

suggestions = generate_query_suggestions("peninsula_incident")

# Group by category
by_category = {}
for s in suggestions:
    cat = s["category"]
    if cat not in by_category:
        by_category[cat] = []
    by_category[cat].append(s)

for category, items in by_category.items():
    print(f"\n{category}:")
    print("-" * 40)
    for item in items[:5]:  # Show first 5 per category
        print(f"  • {item['query']}")
        print(f"    → {item['description']}")
    if len(items) > 5:
        print(f"    ... and {len(items) - 5} more")

print("\n" + "=" * 80)
print(f"Total suggestions: {len(suggestions)}")
print("=" * 80)
