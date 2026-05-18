"""
Run all DEMO_QUESTIONS.md questions against the API and save raw JSON responses.

Usage:
    python test/run_demo_questions.py
    python test/run_demo_questions.py --dry-run
    python test/run_demo_questions.py --output results/demo_run.json
    API_URL=http://34.126.131.59:8000 python test/run_demo_questions.py
"""

import os
import sys
import json
import time
import argparse
import requests

API_URL = os.environ.get("API_URL", "http://localhost:8000")
PROPERTY_UUID = os.environ.get("PROPERTY_UUID", "")
REDSHIFT_TARGET = os.environ.get("REDSHIFT_TARGET", "default")

DEMO_QUESTIONS = [
    # Simple Counts
    {"id": "S01", "category": "simple_count", "question": "How many total maintenance orders are there?"},
    {"id": "S02", "category": "simple_count", "question": "How many maintenance orders are currently open?"},
    {"id": "S03", "category": "simple_count", "question": "How many maintenance orders have been completed?"},
    {"id": "S04", "category": "simple_count", "question": "How many maintenance orders are cancelled?"},
    {"id": "S05", "category": "simple_count", "question": "How many high priority maintenance orders are there?"},
    {"id": "S06", "category": "simple_count", "question": "How many low priority maintenance orders exist?"},
    {"id": "S07", "category": "simple_count", "question": "How many urgent maintenance orders are there?"},
    # Department Breakdown
    {"id": "D01", "category": "department", "question": "Show maintenance order count grouped by department"},
    {"id": "D02", "category": "department", "question": "Which department has the most maintenance orders?"},
    {"id": "D03", "category": "department", "question": "How many open orders does each department have?"},
    {"id": "D04", "category": "department", "question": "Which departments have high priority maintenance orders?"},
    {"id": "D05", "category": "department", "question": "Show top 5 departments by number of maintenance orders"},
    # Group By
    {"id": "G01", "category": "group_by", "question": "Show maintenance order count by status"},
    {"id": "G02", "category": "group_by", "question": "Show maintenance order count by priority"},
    {"id": "G03", "category": "group_by", "question": "What is the distribution of maintenance orders by status and priority?"},
    {"id": "G04", "category": "group_by", "question": "Which status has the most maintenance orders?"},
    {"id": "G05", "category": "group_by", "question": "Show high priority open maintenance orders"},
    # Date Filters
    {"id": "F01", "category": "date_filter", "question": "How many maintenance orders were created this month?"},
    {"id": "F02", "category": "date_filter", "question": "How many maintenance orders were created this week?"},
    {"id": "F03", "category": "date_filter", "question": "Show maintenance orders created in the last 30 days"},
    {"id": "F04", "category": "date_filter", "question": "How many maintenance orders were created last week?"},
    {"id": "F05", "category": "date_filter", "question": "How many maintenance orders were completed this year?"},
    {"id": "F06", "category": "date_filter", "question": "Show orders created in the last 7 days"},
    {"id": "F07", "category": "date_filter", "question": "How many maintenance orders were cancelled last month?"},
    # Trends
    {"id": "T01", "category": "trend", "question": "Show the monthly trend of maintenance orders created"},
    {"id": "T02", "category": "trend", "question": "Show weekly maintenance order trend for this year"},
    {"id": "T03", "category": "trend", "question": "How many maintenance orders were created each day this month?"},
    {"id": "T04", "category": "trend", "question": "Show trend of high priority orders by month"},
    # Location
    {"id": "L01", "category": "location", "question": "Show maintenance order count by location"},
    {"id": "L02", "category": "location", "question": "Which location has the most maintenance orders?"},
    # Aggregation
    {"id": "A01", "category": "aggregation", "question": "What percentage of maintenance orders are completed?"},
    {"id": "A02", "category": "aggregation", "question": "What is the most common maintenance order type?"},
    {"id": "A03", "category": "aggregation", "question": "Show the 10 most recent maintenance orders"},
    {"id": "A04", "category": "aggregation", "question": "How many maintenance orders were created vs completed this month?"},
    # Hallucination Guards
    {"id": "H01", "category": "hallucination_guard", "question": "Show all maintenance orders for the housekeeping department"},
    {"id": "H02", "category": "hallucination_guard", "question": "How many open high priority orders are in the engineering department?"},
    {"id": "H03", "category": "hallucination_guard", "question": "Show maintenance orders created this month by department"},
    {"id": "H04", "category": "hallucination_guard", "question": "What are the most recent 5 completed maintenance orders?"},
    {"id": "H05", "category": "hallucination_guard", "question": "Show cancelled orders from last month grouped by priority"},
]


def call_api(question: str, dry_run: bool) -> tuple[dict, int, float]:
    payload = {
        "text": question,
        "context": {"property_uuid": PROPERTY_UUID, "language": "en"},
        "sql": {"dialect": "redshift", "tables": []},
        "execution": {"dry_run": dry_run, "max_rows": 100, "redshift_target": REDSHIFT_TARGET},
        "model": {"max_tokens": 256},
        "trace": {"source": "run_demo_questions"},
    }
    t0 = time.time()
    resp = requests.post(f"{API_URL}/nlq/execute", json=payload, timeout=120)
    elapsed_ms = int((time.time() - t0) * 1000)
    return resp.json(), resp.status_code, elapsed_ms


def main():
    parser = argparse.ArgumentParser(description="Run DEMO_QUESTIONS against API, save raw JSON")
    parser.add_argument("--dry-run", action="store_true", help="Skip Redshift execution")
    parser.add_argument("--output", default="test/demo_questions_responses.json",
                        help="Output JSON file path (default: test/demo_questions_responses.json)")
    args = parser.parse_args()

    # Health check
    try:
        r = requests.get(f"{API_URL}/health", timeout=10)
        if r.status_code != 200:
            print(f"WARNING: /health returned {r.status_code}")
    except Exception as e:
        print(f"ERROR: Cannot reach API at {API_URL}: {e}")
        sys.exit(1)

    mode = "dry-run" if args.dry_run else "live"
    print(f"\nRunning {len(DEMO_QUESTIONS)} DEMO_QUESTIONS — {mode} — API: {API_URL}\n")

    results = []
    for q in DEMO_QUESTIONS:
        print(f"  [{q['id']}] {q['question'][:70]}", end="", flush=True)
        try:
            raw, status_code, elapsed_ms = call_api(q["question"], args.dry_run)
            sql = raw.get("sql", {}).get("query", "") if raw.get("success") else ""
            results.append({
                "id": q["id"],
                "category": q["category"],
                "question": q["question"],
                "http_status": status_code,
                "elapsed_ms": elapsed_ms,
                "response": raw,
            })
            print(f"  {elapsed_ms}ms  {'✓' if raw.get('success') else '✗'}")
        except Exception as e:
            results.append({
                "id": q["id"],
                "category": q["category"],
                "question": q["question"],
                "http_status": None,
                "elapsed_ms": None,
                "error": str(e),
                "response": None,
            })
            print(f"  ERROR: {e}")

    output = {
        "meta": {
            "api_url": API_URL,
            "redshift_target": REDSHIFT_TARGET,
            "dry_run": args.dry_run,
            "total_questions": len(DEMO_QUESTIONS),
            "run_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "results": results,
    }

    os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2, default=str)

    success = sum(1 for r in results if r.get("response", {}) and r["response"].get("success"))
    print(f"\nDone. {success}/{len(DEMO_QUESTIONS)} succeeded. Saved → {args.output}\n")


if __name__ == "__main__":
    main()
