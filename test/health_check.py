"""
Quick health check script for the API
Run this to test if the backend is responding
"""
import requests
import time

API_URL = "http://localhost:8080"

print("🔍 Testing NLQ API Health...\n")

# Test 1: Basic health check
print("1. Testing root endpoint...")
try:
    response = requests.get(f"{API_URL}/", timeout=5)
    print(f"   ✅ Status: {response.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: Schema endpoint (faster)
print("\n2. Testing schema endpoint...")
try:
    start = time.time()
    response = requests.get(f"{API_URL}/nlq/schema?target=peninsula_incident", timeout=30)
    elapsed = time.time() - start
    print(f"   ✅ Status: {response.status_code} ({elapsed:.2f}s)")
    data = response.json()
    print(f"   📊 Tables: {len(data.get('tables', []))}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Simple query (slower - model loading)
print("\n3. Testing query endpoint (this may take 2-5 min on first run)...")
try:
    start = time.time()
    response = requests.post(
        f"{API_URL}/nlq/execute",
        json={
            "text": "Show me 5 incidents",
            "context": {
                "account_uuid": "00000000-0000-0000-0000-000000000000",
                "property_uuid": "00000000-0000-0000-0000-000000000000",
                "language": "en"
            },
            "sql": {"dialect": "redshift"},
            "execution": {"dry_run": True, "max_rows": 5},
            "model": {
                "name": "Qwen/Qwen2.5-Coder-7B-Instruct",
                "temperature": 0.0,
                "max_tokens": 256
            },
            "trace": {"source": "health-check"}
        },
        timeout=300
    )
    elapsed = time.time() - start
    print(f"   ✅ Status: {response.status_code} ({elapsed:.2f}s)")
    data = response.json()
    if data.get('success'):
        print(f"   🎯 SQL Generated: {data.get('sql', {}).get('query', 'N/A')[:100]}...")
    else:
        print(f"   ⚠️  Error: {data.get('error', 'Unknown')}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n✅ Health check complete!")
