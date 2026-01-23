#!/usr/bin/env python3
"""
Generate sample NLQ payloads for testing the API
"""
import requests
import json
from typing import Dict, Any

API_URL = "http://localhost:8080/nlq/execute"

# Sample payloads with different scenarios
sample_payloads = [
    {
        "name": "Simple incident count query",
        "payload": {
            "text": "How many incidents were created last month?",
            "context": {
                "account_uuid": "acc-12345",
                "property_uuid": "prop-67890",
                "user_role": "admin",
                "location_name": "Building A",
                "language": "en"
            },
            "sql": {
                "dialect": "athena"
            },
            "execution": {
                "dry_run": True,
                "max_rows": 100,
                "timeout_ms": 5000
            },
            "model": {
                "name": "Ellbendls/Qwen-2.5-3b-Text_to_SQL",
                "temperature": 0.0,
                "max_tokens": 256
            },
            "trace": {
                "request_id": "req-001",
                "source": "payload-generator"
            }
        }
    },
    {
        "name": "Filter by status query",
        "payload": {
            "text": "Show me all open incidents with high priority",
            "context": {
                "account_uuid": "acc-12345",
                "property_uuid": "prop-67890",
                "user_role": "manager",
                "location_name": "Building B",
                "language": "en"
            },
            "sql": {
                "dialect": "athena"
            },
            "execution": {
                "dry_run": True,
                "max_rows": 50,
                "timeout_ms": 5000
            },
            "model": {
                "name": "Ellbendls/Qwen-2.5-3b-Text_to_SQL",
                "temperature": 0.0,
                "max_tokens": 256
            },
            "trace": {
                "request_id": "req-002",
                "source": "payload-generator"
            }
        }
    },
    {
        "name": "Aggregation with grouping",
        "payload": {
            "text": "What is the average resolution time by category?",
            "context": {
                "account_uuid": "acc-12345",
                "property_uuid": "prop-67890",
                "user_role": "analyst",
                "location_name": "All Locations",
                "language": "en"
            },
            "sql": {
                "dialect": "athena"
            },
            "execution": {
                "dry_run": True,
                "max_rows": 100,
                "timeout_ms": 5000
            },
            "model": {
                "name": "Ellbendls/Qwen-2.5-3b-Text_to_SQL",
                "temperature": 0.0,
                "max_tokens": 256
            },
            "trace": {
                "request_id": "req-003",
                "source": "payload-generator"
            }
        }
    },
    {
        "name": "Date range query with Chinese language",
        "payload": {
            "text": "上个月有多少个新的工单？",
            "context": {
                "account_uuid": "acc-12345",
                "property_uuid": "prop-67890",
                "user_role": "user",
                "location_name": "Singapore Office",
                "language": "zh"
            },
            "sql": {
                "dialect": "athena"
            },
            "execution": {
                "dry_run": True,
                "max_rows": 100,
                "timeout_ms": 5000
            },
            "model": {
                "name": "Ellbendls/Qwen-2.5-3b-Text_to_SQL",
                "temperature": 0.0,
                "max_tokens": 256
            },
            "trace": {
                "request_id": "req-004",
                "source": "payload-generator"
            }
        }
    },
    {
        "name": "Complex multi-condition query",
        "payload": {
            "text": "List all incidents created in the last 7 days that are assigned to John and have not been resolved",
            "context": {
                "account_uuid": "acc-12345",
                "property_uuid": "prop-67890",
                "user_role": "supervisor",
                "location_name": "Main Campus",
                "language": "en"
            },
            "sql": {
                "dialect": "athena"
            },
            "execution": {
                "dry_run": False,
                "max_rows": 200,
                "timeout_ms": 10000
            },
            "model": {
                "name": "Ellbendls/Qwen-2.5-3b-Text_to_SQL",
                "temperature": 0.0,
                "max_tokens": 256
            },
            "trace": {
                "request_id": "req-005",
                "source": "payload-generator"
            }
        }
    }
]


def print_payload(name: str, payload: Dict[Any, Any]) -> None:
    """Print a formatted payload"""
    print("\n" + "="*80)
    print(f"PAYLOAD: {name}")
    print("="*80)
    print(json.dumps(payload, indent=2))
    print("="*80 + "\n")


def test_payload(name: str, payload: Dict[Any, Any]) -> None:
    """Test a payload against the API"""
    print(f"\n🧪 Testing: {name}")
    print("-" * 80)
    
    try:
        response = requests.post(API_URL, json=payload, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Success!")
            result = response.json()
            print("\nResponse Preview:")
            print(json.dumps(result, indent=2)[:500] + "..." if len(json.dumps(result)) > 500 else json.dumps(result, indent=2))
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text[:300])
    
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    print("-" * 80)


def main():
    print("\n" + "🎯" * 40)
    print("NLQ API PAYLOAD GENERATOR")
    print("🎯" * 40)
    
    print("\n📋 Available actions:")
    print("1. Display all payloads (no API calls)")
    print("2. Test all payloads against API")
    print("3. Save payloads to file")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        print("\n" + "📄" * 40)
        print("DISPLAYING ALL PAYLOADS")
        print("📄" * 40)
        for item in sample_payloads:
            print_payload(item["name"], item["payload"])
    
    elif choice == "2":
        print("\n" + "🚀" * 40)
        print("TESTING ALL PAYLOADS AGAINST API")
        print("🚀" * 40)
        for item in sample_payloads:
            test_payload(item["name"], item["payload"])
    
    elif choice == "3":
        filename = "sample_payloads.json"
        with open(filename, "w") as f:
            json.dump(sample_payloads, f, indent=2)
        print(f"\n✅ Payloads saved to {filename}")
    
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()
