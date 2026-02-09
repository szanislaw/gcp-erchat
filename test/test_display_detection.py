#!/usr/bin/env python3
"""
Test display type detection for time series queries.
Verifies that "incidents per day over last 7 days" type queries return "line" chart.
"""

import sys
sys.path.insert(0, '/home/shawnyzy/Documents/GitHub/gcp-erchat')

from app.display_hint import get_display_type

# Test cases for time series detection
test_cases = [
    {
        "name": "Incidents per day (DATE function)",
        "sql": "SELECT DATE(created_date) as day, COUNT(*) as count FROM incident_combine WHERE created_date >= date_add('day', -7, current_date) GROUP BY DATE(created_date) ORDER BY day",
        "execution_data": {
            "columns": ["day", "count"],
            "rows": [
                {"day": "2026-02-02", "count": 5},
                {"day": "2026-02-03", "count": 8},
                {"day": "2026-02-04", "count": 3},
                {"day": "2026-02-05", "count": 7},
                {"day": "2026-02-06", "count": 6},
                {"day": "2026-02-07", "count": 4},
                {"day": "2026-02-08", "count": 9}
            ],
            "row_count": 7
        },
        "expected": "line"
    },
    {
        "name": "Incidents per day (CAST AS DATE)",
        "sql": "SELECT CAST(created_date AS DATE) as day, COUNT(*) as incidents FROM incident_combine WHERE created_date >= CURRENT_DATE - INTERVAL '7' DAY GROUP BY CAST(created_date AS DATE)",
        "execution_data": {
            "columns": ["day", "incidents"],
            "rows": [
                {"day": "2026-02-02", "incidents": 5},
                {"day": "2026-02-03", "incidents": 8},
                {"day": "2026-02-04", "incidents": 3},
                {"day": "2026-02-05", "incidents": 7},
                {"day": "2026-02-06", "incidents": 6},
                {"day": "2026-02-07", "incidents": 4},
                {"day": "2026-02-08", "incidents": 9}
            ],
            "row_count": 7
        },
        "expected": "line"
    },
    {
        "name": "Incidents with date column name",
        "sql": "SELECT snapshotdate, COUNT(*) as count FROM incident_combine GROUP BY snapshotdate ORDER BY snapshotdate DESC LIMIT 7",
        "execution_data": {
            "columns": ["snapshotdate", "count"],
            "rows": [
                {"snapshotdate": "2026-02-08", "count": 9},
                {"snapshotdate": "2026-02-07", "count": 4},
                {"snapshotdate": "2026-02-06", "count": 6},
                {"snapshotdate": "2026-02-05", "count": 7},
                {"snapshotdate": "2026-02-04", "count": 3},
                {"snapshotdate": "2026-02-03", "count": 8},
                {"snapshotdate": "2026-02-02", "count": 5}
            ],
            "row_count": 7
        },
        "expected": "line"
    },
    {
        "name": "Simple count (not time series)",
        "sql": "SELECT COUNT(*) as total FROM incident_combine",
        "execution_data": {
            "columns": ["total"],
            "rows": [{"total": 1247}],
            "row_count": 1
        },
        "expected": "metric"
    },
    {
        "name": "Incidents by severity (pie chart)",
        "sql": "SELECT severity_name, COUNT(*) as count FROM incident_combine GROUP BY severity_name",
        "execution_data": {
            "columns": ["severity_name", "count"],
            "rows": [
                {"severity_name": "high", "count": 342},
                {"severity_name": "medium", "count": 567},
                {"severity_name": "low", "count": 338}
            ],
            "row_count": 3
        },
        "expected": "pie"
    },
    {
        "name": "Incidents by department (4 categories - pie/bar)",
        "sql": "SELECT department_name, COUNT(*) as count FROM incident_combine GROUP BY department_name",
        "execution_data": {
            "columns": ["department_name", "count"],
            "rows": [
                {"department_name": "Housekeeping", "count": 450},
                {"department_name": "Front Desk", "count": 320},
                {"department_name": "F&B", "count": 280},
                {"department_name": "Maintenance", "count": 197}
            ],
            "row_count": 4
        },
        "expected": "pie"  # With 4 items (<=10), system prefers pie chart
    }
]

def run_tests():
    print("="*70)
    print("Display Type Detection Test Suite")
    print("="*70)
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        result = get_display_type(test["sql"], test["execution_data"])
        
        if result == test["expected"]:
            print(f"✓ PASS: {test['name']}")
            print(f"  Expected: {test['expected']}, Got: {result}")
            passed += 1
        else:
            print(f"✗ FAIL: {test['name']}")
            print(f"  Expected: {test['expected']}, Got: {result}")
            print(f"  SQL: {test['sql'][:100]}...")
            failed += 1
        print()
    
    print("="*70)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("="*70)
    
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
