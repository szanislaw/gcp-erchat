"""
Debug script to check what data exists in the database
Helps troubleshoot why queries return no results
"""
import requests
import json

API_URL = "http://localhost:8080"

print("🔍 Debugging Query Results\n")
print("=" * 60)

# Test query to get all distinct property names
test_queries = [
    {
        "name": "Get all distinct property names",
        "text": "Show me all distinct property names",
        "dry_run": False
    },
    {
        "name": "Get sample incidents with property",
        "text": "Show me 10 incidents with their property names",
        "dry_run": False
    },
    {
        "name": "Test Peninsula Manila query (dry run)",
        "text": "What incidents happened at The Peninsula Manila?",
        "dry_run": True  # Just check SQL generation
    }
]

for test in test_queries:
    print(f"\n{'=' * 60}")
    print(f"Test: {test['name']}")
    print(f"Query: {test['text']}")
    print("-" * 60)
    
    try:
        response = requests.post(
            f"{API_URL}/nlq/execute",
            json={
                "text": test['text'],
                "context": {
                    "account_uuid": "00000000-0000-0000-0000-000000000000",
                    "property_uuid": "00000000-0000-0000-0000-000000000000",
                    "language": "en"
                },
                "sql": {"dialect": "athena"},
                "execution": {
                    "dry_run": test['dry_run'],
                    "max_rows": 100
                },
                "model": {
                    "name": "Qwen/Qwen2.5-Coder-7B-Instruct",
                    "temperature": 0.0,
                    "max_tokens": 256
                },
                "trace": {"source": "debug-script"}
            },
            timeout=300
        )
        
        result = response.json()
        
        if result.get('success'):
            sql = result.get('sql', {}).get('query', '')
            print(f"\n✅ Generated SQL:")
            print(f"   {sql}\n")
            
            execution = result.get('execution', {})
            if execution.get('executed'):
                row_count = execution.get('data', {}).get('row_count', 0)
                print(f"📊 Results: {row_count} rows")
                
                if row_count > 0:
                    rows = execution.get('data', {}).get('rows', [])
                    print("\n🔍 Sample data:")
                    for i, row in enumerate(rows[:5]):
                        print(f"   Row {i+1}: {json.dumps(row, indent=6)[:200]}...")
                else:
                    print("   ⚠️  No rows returned")
            else:
                print("   (Dry run - not executed)")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown')}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

print(f"\n{'=' * 60}")
print("\n✅ Debug complete!")
print("\n💡 Next steps:")
print("   1. Check if property names match exactly (case-sensitive)")
print("   2. Try variations: 'Peninsula Manila' vs 'The Peninsula Manila'")
print("   3. Check if data exists for that property in the date range")
