#!/usr/bin/env python3
"""
Test all 20 demo questions with the hardcoded query system
"""

import requests
import json
import time
from typing import Dict, Any

API_URL = "http://localhost:8000/nlq/execute"

# All 20 demo questions
DEMO_QUESTIONS = {
    "TABLE": [
        "Show high severity incidents",
        "Show VIP incidents",
        "Show all completed incidents",
        "Show incidents with actual cost over 1000"
    ],
    "METRIC": [
        "How many total incidents",
        "What is the total actual cost",
        "How many high severity incidents",
        "How many VIP incidents"
    ],
    "BAR": [
        "Count by category",
        "Count by department",
        "Count by severity",
        "Count by location"
    ],
    "PIE": [
        "Status distribution",
        "Severity distribution",
        "VIP vs non-VIP",
        "Category distribution"
    ],
    "LINE": [
        "Incident trend last 30 days",
        "Cost trend last 30 days",
        "High severity trend last 7 days",
        "Completion trend last 30 days"
    ]
}

def test_question(question: str, expected_type: str) -> Dict[str, Any]:
    """Test a single question"""
    payload = {
        "text": question,
        "context": {
            "property_uuid": "c7254cc9-9145-4602-b44b-0c1cff335f83,2b618b46-6b80-481b-b1e3-5aec1647b926",
            "account_uuid": "fccb8d60-de9c-4bf8-abd8-fae523c732c6"
        },
        "sql": {"dialect": "athena"},
        "execution": {"dry_run": True},
        "model": {},
        "trace": {}
    }
    
    try:
        response = requests.post(API_URL, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        confidence = result['sql']['confidence']
        display_type = result['display']['type']
        model_latency = result['trace']['model_latency_ms']
        
        is_hardcoded = confidence == 1.0
        type_matches = display_type == expected_type.lower()
        
        return {
            "success": True,
            "is_hardcoded": is_hardcoded,
            "type_matches": type_matches,
            "confidence": confidence,
            "display_type": display_type,
            "model_latency": model_latency,
            "sql": result['sql']['query']
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def main():
    print("=" * 80)
    print("DEMO QUESTIONS TEST - Hardcoded Query System")
    print("=" * 80)
    print()
    
    total_tests = 0
    passed_tests = 0
    hardcoded_tests = 0
    type_matches = 0
    
    for expected_type, questions in DEMO_QUESTIONS.items():
        print(f"\n📊 {expected_type} Questions:")
        print("-" * 80)
        
        for question in questions:
            total_tests += 1
            result = test_question(question, expected_type)
            
            if result['success']:
                status = "✅" if result['is_hardcoded'] and result['type_matches'] else "⚠️"
                
                print(f"{status} {question}")
                print(f"   Confidence: {result['confidence']} | "
                      f"Display: {result['display_type']} | "
                      f"Latency: {result['model_latency']}ms")
                
                if result['is_hardcoded']:
                    print(f"   🎯 HARDCODED")
                    hardcoded_tests += 1
                else:
                    print(f"   ⚠️  Using ML model (should be hardcoded)")
                
                if result['type_matches']:
                    type_matches += 1
                else:
                    print(f"   ⚠️  Type mismatch: expected {expected_type.lower()}, got {result['display_type']}")
                
                passed_tests += 1
            else:
                print(f"❌ {question}")
                print(f"   Error: {result['error']}")
            
            print()
            time.sleep(0.5)  # Rate limiting
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total tests:       {total_tests}")
    print(f"Passed:            {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
    print(f"Hardcoded:         {hardcoded_tests} ({hardcoded_tests/total_tests*100:.1f}%)")
    print(f"Type matches:      {type_matches} ({type_matches/total_tests*100:.1f}%)")
    print()
    
    if hardcoded_tests == total_tests and type_matches == total_tests:
        print("🎉 All tests PASSED! All questions use hardcoded queries with correct display types.")
    elif hardcoded_tests == total_tests:
        print("⚠️  All queries are hardcoded, but some display types don't match.")
    else:
        print(f"⚠️  {total_tests - hardcoded_tests} questions are not using hardcoded queries.")

if __name__ == "__main__":
    main()
