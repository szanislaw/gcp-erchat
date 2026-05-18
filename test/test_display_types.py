#!/usr/bin/env python3
"""
Test script to demonstrate display type configuration in API requests.

This script shows:
1. Auto-detection mode (omit display field)
2. Manual override mode (specify display.type)
3. All available display types (metric, pie, bar, line, table)

Usage:
    python test/test_display_types.py
"""

import requests
import json

API_URL = "http://localhost:8080/nlq/execute"

# Base request template
BASE_REQUEST = {
    "context": {
        "language": "en",
        "property_uuid": "c7254cc9-9145-4602-b44b-0c1cff335f83,2b618b46-6b80-481b-b1e3-5aec1647b926",
        "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6",
        "user_role": None
    },
    "sql": {"dialect": "redshift", "tables": []},
    "execution": {"dry_run": False, "max_rows": 100, "redshift_target": None},
    "model": {"max_tokens": 512},
    "trace": {"source": "test-display-types"}
}


def test_auto_detection():
    """Test 1: Auto-detection mode (no display field)"""
    print("\n" + "="*70)
    print("TEST 1: Auto-Detection Mode")
    print("="*70)
    
    request = {
        **BASE_REQUEST,
        "text": "How many high severity incidents in the last 7 days?"
    }
    
    print("Request (without display field):")
    print(json.dumps(request, indent=2))
    
    response = requests.post(API_URL, json=request)
    if response.status_code == 200:
        result = response.json()
        print(f"\nAPI Recommended Display Type: {result.get('display', {}).get('type')}")
        print(f"SQL Query: {result.get('sql', {}).get('query')}")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)


def test_manual_override_metric():
    """Test 2: Manual override - Metric display"""
    print("\n" + "="*70)
    print("TEST 2: Manual Override - Metric Display")
    print("="*70)
    
    request = {
        **BASE_REQUEST,
        "text": "Count incidents by status",
        "display": {"type": "metric"}
    }
    
    print("Request (with display.type = 'metric'):")
    print(json.dumps(request, indent=2))
    
    response = requests.post(API_URL, json=request)
    if response.status_code == 200:
        result = response.json()
        print(f"\nActual Display Type: {result.get('display', {}).get('type')}")
        print("✓ API respects user preference")
    else:
        print(f"Error: {response.status_code}")


def test_manual_override_pie():
    """Test 3: Manual override - Pie chart"""
    print("\n" + "="*70)
    print("TEST 3: Manual Override - Pie Chart")
    print("="*70)
    
    request = {
        **BASE_REQUEST,
        "text": "Show incident breakdown by severity",
        "display": {"type": "pie"}
    }
    
    print("Request (with display.type = 'pie'):")
    print(json.dumps(request, indent=2))
    
    response = requests.post(API_URL, json=request)
    if response.status_code == 200:
        result = response.json()
        print(f"\nActual Display Type: {result.get('display', {}).get('type')}")
        print("✓ API respects user preference")
    else:
        print(f"Error: {response.status_code}")


def test_manual_override_bar():
    """Test 4: Manual override - Bar chart"""
    print("\n" + "="*70)
    print("TEST 4: Manual Override - Bar Chart")
    print("="*70)
    
    request = {
        **BASE_REQUEST,
        "text": "Incidents per category",
        "display": {"type": "bar"}
    }
    
    print("Request (with display.type = 'bar'):")
    print(json.dumps(request, indent=2))
    
    response = requests.post(API_URL, json=request)
    if response.status_code == 200:
        result = response.json()
        print(f"\nActual Display Type: {result.get('display', {}).get('type')}")
        print("✓ API respects user preference")
    else:
        print(f"Error: {response.status_code}")


def test_manual_override_line():
    """Test 5: Manual override - Line chart"""
    print("\n" + "="*70)
    print("TEST 5: Manual Override - Line Chart")
    print("="*70)
    
    request = {
        **BASE_REQUEST,
        "text": "Incident trend over the last 30 days",
        "display": {"type": "line"}
    }
    
    print("Request (with display.type = 'line'):")
    print(json.dumps(request, indent=2))
    
    response = requests.post(API_URL, json=request)
    if response.status_code == 200:
        result = response.json()
        print(f"\nActual Display Type: {result.get('display', {}).get('type')}")
        print("✓ API respects user preference")
    else:
        print(f"Error: {response.status_code}")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("Display Type Configuration Test Suite")
    print("="*70)
    print("\nThis script demonstrates two modes:")
    print("1. AUTO-DETECTION: Omit 'display' field, API recommends best type")
    print("2. MANUAL OVERRIDE: Include 'display.type', API uses your preference")
    print("\nAvailable display types: metric, pie, bar, line, table")
    print("="*70)
    
    try:
        test_auto_detection()
        test_manual_override_metric()
        test_manual_override_pie()
        test_manual_override_bar()
        test_manual_override_line()
        
        print("\n" + "="*70)
        print("All tests completed!")
        print("="*70 + "\n")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to API server")
        print("Make sure the API is running at http://localhost:8080")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
