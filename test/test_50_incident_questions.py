"""
50-question incident test suite covering all major query patterns for mv_recovery_all.

Usage:
  python test/test_50_incident_questions.py              # dry-run (no Redshift)
  python test/test_50_incident_questions.py --live       # live Redshift execution
  python test/test_50_incident_questions.py --sql-only   # print SQL, no assertions
  API_URL=http://34.126.131.59:8000 python test/test_50_incident_questions.py
"""

import requests
import json
import re
import sys
import time
import argparse
import os

API_URL = os.environ.get("API_URL", "http://localhost:8000")

def has(pattern, flags=re.IGNORECASE):
    return lambda sql: bool(re.search(pattern, sql, flags))

def has_all(*patterns):
    return lambda sql: all(re.search(p, sql, re.IGNORECASE) for p in patterns)

def has_any(*patterns):
    return lambda sql: any(re.search(p, sql, re.IGNORECASE) for p in patterns)

def has_none(*patterns):
    return lambda sql: not any(re.search(p, sql, re.IGNORECASE) for p in patterns)

def val_eq(col, val):
    return lambda sql: bool(re.search(
        rf"""{col}\s*=\s*['"]{{0,1}}{re.escape(val)}['"]{{0,1}}""", sql, re.IGNORECASE
    ))

def val_in(col, *vals):
    return lambda sql: any(re.search(
        rf"""{col}\s*=\s*['"]{{0,1}}{re.escape(v)}['"]{{0,1}}""", sql, re.IGNORECASE
    ) or re.search(rf"""['"]{re.escape(v)}['"]""", sql, re.IGNORECASE) for v in vals)

QUESTIONS = [
    # ═══════════════════════════════════════════════════════════════
    # CATEGORY A: Simple counts (8 questions)
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "I01", "category": "simple_count",
        "question": "How many total incidents are there?",
        "checks": [has(r"\bCOUNT\s*\("), has(r"\bmv_recovery_all\b"), has_none(r"\bGROUP\s+BY\b")],
    },
    {
        "id": "I02", "category": "simple_count",
        "question": "How many open incidents are there?",
        "checks": [has(r"\bCOUNT\s*\("), has(r"status_name"), has(r"pending|draft")],
    },
    {
        "id": "I03", "category": "simple_count",
        "question": "How many completed incidents?",
        "checks": [has(r"\bCOUNT\s*\("), has(r"status_name"), has(r"completed")],
    },
    {
        "id": "I04", "category": "simple_count",
        "question": "How many cancelled incidents?",
        "checks": [has(r"\bCOUNT\s*\("), has(r"status_name"), has(r"cancelled")],
    },
    {
        "id": "I05", "category": "simple_count",
        "question": "How many draft incidents are there?",
        "checks": [has(r"\bCOUNT\s*\("), has(r"status_name"), has(r"draft")],
    },
    {
        "id": "I06", "category": "simple_count",
        "question": "How many high severity incidents?",
        "checks": [has(r"\bCOUNT\s*\("), has(r"severity_name"), has(r"high")],
    },
    {
        "id": "I07", "category": "simple_count",
        "question": "How many critical severity incidents are there?",
        "checks": [has(r"\bCOUNT\s*\("), has(r"severity_name"), has(r"critical")],
    },
    {
        "id": "I08", "category": "simple_count",
        "question": "How many pending incidents?",
        "checks": [has(r"\bCOUNT\s*\("), has(r"status_name"), has(r"pending")],
    },

    # ═══════════════════════════════════════════════════════════════
    # CATEGORY B: Group-by breakdowns (8 questions)
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "IB01", "category": "group_by",
        "question": "Show incident count by status",
        "checks": [has(r"\bCOUNT\s*\("), has(r"status_name"), has(r"\bGROUP\s+BY\b")],
    },
    {
        "id": "IB02", "category": "group_by",
        "question": "Show incident count by severity",
        "checks": [has(r"\bCOUNT\s*\("), has(r"severity_name"), has(r"\bGROUP\s+BY\b")],
    },
    {
        "id": "IB03", "category": "group_by",
        "question": "Show incident count by category",
        "checks": [has(r"\bCOUNT\s*\("), has(r"category_name"), has(r"\bGROUP\s+BY\b")],
    },
    {
        "id": "IB04", "category": "group_by",
        "question": "Show incident count by department",
        "checks": [has(r"\bCOUNT\s*\("), has(r"department_name"), has(r"\bGROUP\s+BY\b")],
    },
    {
        "id": "IB05", "category": "group_by",
        "question": "Which category has the most incidents?",
        "checks": [has(r"\bCOUNT\s*\("), has(r"category_name"), has(r"\bGROUP\s+BY\b"), has(r"\bORDER\s+BY\b")],
    },
    {
        "id": "IB06", "category": "group_by",
        "question": "Which department has the most incidents?",
        "checks": [has(r"\bCOUNT\s*\("), has(r"department_name"), has(r"\bGROUP\s+BY\b"), has(r"\bORDER\s+BY\b")],
    },
    {
        "id": "IB07", "category": "group_by",
        "question": "Show incident count by location",
        "checks": [has(r"\bCOUNT\s*\("), has(r"location_name"), has(r"\bGROUP\s+BY\b")],
    },
    {
        "id": "IB08", "category": "group_by",
        "question": "Show top 5 incident categories",
        "checks": [has(r"\bCOUNT\s*\("), has(r"category_name"), has(r"\bGROUP\s+BY\b"), has(r"\bLIMIT\s+5\b")],
    },

    # ═══════════════════════════════════════════════════════════════
    # CATEGORY C: Date filters (8 questions)
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "IC01", "category": "date_filter",
        "question": "How many incidents were created this month?",
        "checks": [has(r"\bCOUNT\s*\("), has(r"DATE_TRUNC\s*\(\s*'month'"), has_none(r"GROUP\s+BY")],
    },
    {
        "id": "IC02", "category": "date_filter",
        "question": "How many incidents were created this year?",
        "checks": [has(r"\bCOUNT\s*\("), has(r"EXTRACT\s*\(\s*YEAR|DATE_TRUNC\s*\(\s*'year'")],
    },
    {
        "id": "IC03", "category": "date_filter",
        "question": "How many incidents were created this week?",
        "checks": [has(r"\bCOUNT\s*\("), has(r"DATE_TRUNC\s*\(\s*'week'")],
    },
    {
        "id": "IC04", "category": "date_filter",
        "question": "How many incidents were created last month?",
        "checks": [has(r"\bCOUNT\s*\("), has(r"DATE_TRUNC\s*\(\s*'month'"), has(r"DATEADD\s*\(\s*month")],
    },
    {
        "id": "IC05", "category": "date_filter",
        "question": "How many incidents were created last week?",
        "checks": [has(r"\bCOUNT\s*\("), has(r"DATE_TRUNC\s*\(\s*'week'"), has(r"DATEADD\s*\(\s*week")],
    },
    {
        "id": "IC06", "category": "date_filter",
        "question": "How many incidents were created in the last 30 days?",
        "checks": [has(r"\bCOUNT\s*\("), has(r"DATEADD\s*\(\s*day\s*,\s*-30")],
    },
    {
        "id": "IC07", "category": "date_filter",
        "question": "How many incidents were completed this month?",
        "checks": [has(r"\bCOUNT\s*\("), has(r"completed_date|completed"), has(r"DATE_TRUNC\s*\(\s*'month'")],
    },
    {
        "id": "IC08", "category": "date_filter",
        "question": "How many incidents were created in the last 7 days?",
        "checks": [has(r"\bCOUNT\s*\("), has(r"DATEADD\s*\(\s*day\s*,\s*-7")],
    },

    # ═══════════════════════════════════════════════════════════════
    # CATEGORY D: Trend analysis (6 questions)
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "ID01", "category": "trend",
        "question": "Show the monthly incident trend",
        "checks": [has(r"\bCOUNT\s*\("), has(r"DATE_TRUNC\s*\(\s*'month'"), has(r"\bGROUP\s+BY\b"), has(r"\bORDER\s+BY\b")],
    },
    {
        "id": "ID02", "category": "trend",
        "question": "Show the weekly incident trend for this year",
        "checks": [has(r"\bCOUNT\s*\("), has(r"DATE_TRUNC\s*\(\s*'week'"), has(r"\bGROUP\s+BY\b")],
    },
    {
        "id": "ID03", "category": "trend",
        "question": "Show the daily incident trend this month",
        "checks": [has(r"\bCOUNT\s*\("), has(r"DATE_TRUNC\s*\(\s*'day'"), has(r"\bGROUP\s+BY\b")],
    },
    {
        "id": "ID04", "category": "trend",
        "question": "Show monthly trend of completed incidents",
        "checks": [has(r"\bCOUNT\s*\("), has(r"DATE_TRUNC\s*\(\s*'month'"), has(r"completed"), has(r"\bGROUP\s+BY\b")],
    },
    {
        "id": "ID05", "category": "trend",
        "question": "Show monthly incident count by severity",
        "checks": [has(r"\bCOUNT\s*\("), has(r"severity_name"), has(r"DATE_TRUNC\s*\(\s*'month'"), has(r"\bGROUP\s+BY\b")],
    },
    {
        "id": "ID06", "category": "trend",
        "question": "Show weekly trend of open incidents",
        "checks": [has(r"\bCOUNT\s*\("), has(r"DATE_TRUNC\s*\(\s*'week'"), has(r"pending|draft"), has(r"\bGROUP\s+BY\b")],
    },

    # ═══════════════════════════════════════════════════════════════
    # CATEGORY E: Cost analysis (5 questions)
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "IE01", "category": "cost",
        "question": "What is the average actual cost per incident?",
        "checks": [has(r"\bAVG\s*\("), has(r"actual_cost")],
    },
    {
        "id": "IE02", "category": "cost",
        "question": "Show average cost by category",
        "checks": [has(r"\bAVG\s*\("), has(r"actual_cost"), has(r"category_name"), has(r"\bGROUP\s+BY\b")],
    },
    {
        "id": "IE03", "category": "cost",
        "question": "Show average cost by severity",
        "checks": [has(r"\bAVG\s*\("), has(r"actual_cost"), has(r"severity_name"), has(r"\bGROUP\s+BY\b")],
    },
    {
        "id": "IE04", "category": "cost",
        "question": "What is the total actual cost of all incidents?",
        "checks": [has(r"\bSUM\s*\("), has(r"actual_cost")],
    },
    {
        "id": "IE05", "category": "cost",
        "question": "Show top 5 categories by average cost",
        "checks": [has(r"\bAVG\s*\("), has(r"actual_cost"), has(r"category_name"), has(r"\bORDER\s+BY\b"), has(r"\bLIMIT\s+5\b")],
    },

    # ═══════════════════════════════════════════════════════════════
    # CATEGORY F: Combined filters (6 questions)
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "IF01", "category": "combined",
        "question": "How many high severity open incidents are there?",
        "checks": [has(r"\bCOUNT\s*\("), has(r"severity_name"), has(r"high"), has(r"status_name"), has(r"pending|draft")],
    },
    {
        "id": "IF02", "category": "combined",
        "question": "How many critical incidents are pending?",
        "checks": [has(r"\bCOUNT\s*\("), has(r"severity_name"), has(r"critical"), has(r"status_name"), has(r"pending")],
    },
    {
        "id": "IF03", "category": "combined",
        "question": "How many completed high severity incidents are there?",
        "checks": [has(r"\bCOUNT\s*\("), has(r"severity_name"), has(r"high"), has(r"status_name"), has(r"completed")],
    },
    {
        "id": "IF04", "category": "combined",
        "question": "How many VIP guest incidents are there?",
        "checks": [has(r"\bCOUNT\s*\("), has(r"\bvip\b")],
    },
    {
        "id": "IF05", "category": "combined",
        "question": "How many high severity incidents were created this month?",
        "checks": [has(r"\bCOUNT\s*\("), has(r"severity_name"), has(r"high"), has(r"DATE_TRUNC\s*\(\s*'month'")],
    },
    {
        "id": "IF06", "category": "combined",
        "question": "How many open critical incidents are there?",
        "checks": [has(r"\bCOUNT\s*\("), has(r"severity_name"), has(r"critical"), has(r"pending|draft")],
    },

    # ═══════════════════════════════════════════════════════════════
    # CATEGORY G: Percentages (4 questions)
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "IG01", "category": "percentage",
        "question": "What percentage of incidents are completed?",
        "checks": [has(r"CAST|FLOAT|::float"), has(r"completed"), has(r"NULLIF|100")],
    },
    {
        "id": "IG02", "category": "percentage",
        "question": "What percentage of incidents are open?",
        "checks": [has(r"CAST|FLOAT|::float"), has(r"pending|draft"), has(r"NULLIF|100")],
    },
    {
        "id": "IG03", "category": "percentage",
        "question": "What percentage of incidents are high or critical severity?",
        "checks": [has(r"CAST|FLOAT|::float"), has(r"high|critical"), has(r"severity_name")],
    },
    {
        "id": "IG04", "category": "percentage",
        "question": "What percentage of incidents created this month are completed?",
        "checks": [has(r"CAST|FLOAT|::float"), has(r"completed"), has(r"DATE_TRUNC\s*\(\s*'month'")],
    },

    # ═══════════════════════════════════════════════════════════════
    # CATEGORY H: Listing/recent (5 questions)
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "IH01", "category": "listing",
        "question": "Show the 10 most recent incidents",
        "checks": [has(r"\bORDER\s+BY\b"), has(r"created_date"), has(r"\bDESC\b"), has(r"\bLIMIT\s+10\b")],
    },
    {
        "id": "IH02", "category": "listing",
        "question": "Show the 5 most recent completed incidents",
        "checks": [has(r"\bORDER\s+BY\b"), has(r"completed"), has(r"\bLIMIT\s+5\b")],
    },
    {
        "id": "IH03", "category": "listing",
        "question": "Show recent high severity incidents",
        "checks": [has(r"severity_name"), has(r"high"), has(r"\bORDER\s+BY\b"), has(r"\bDESC\b")],
    },
    {
        "id": "IH04", "category": "listing",
        "question": "Show recent incidents with their categories and status",
        "checks": [has(r"category_name"), has(r"status_name"), has(r"\bORDER\s+BY\b")],
    },
    {
        "id": "IH05", "category": "listing",
        "question": "Show the most recent VIP guest incidents",
        "checks": [has(r"\bvip\b"), has(r"\bORDER\s+BY\b"), has(r"\bDESC\b")],
    },
]


def call_api(question: str, dry_run: bool) -> dict:
    payload = {
        "text": question,
        "context": {},
        "sql": {"dialect": "redshift", "tables": []},
        "execution": {"dry_run": dry_run, "max_rows": 100, "redshift_target": "incident"},
        "model": {"max_tokens": 300},
        "trace": {"request_id": f"incident-test", "source": "test"},
    }
    resp = requests.post(f"{API_URL}/nlq/execute", json=payload, timeout=120)
    return resp.json()


def run_tests(dry_run: bool, sql_only: bool):
    passed = 0
    failed = 0
    results = []

    print(f"\n{'='*70}")
    print(f"  Incident 50-Question Test Suite  |  dry_run={dry_run}  |  {API_URL}")
    print(f"{'='*70}\n")

    for q in QUESTIONS:
        qid = q["id"]
        question = q["question"]
        try:
            r = call_api(question, dry_run)
            sql = r.get("sql", {}).get("query", "") or r.get("query", "") or ""
            error = r.get("detail", "") or r.get("error", "")
        except Exception as e:
            sql = ""
            error = str(e)

        if sql_only:
            print(f"[{qid}] {question}")
            print(f"  SQL: {sql}")
            print()
            continue

        if error and not sql:
            status = "FAIL"
            reason = f"API error: {error[:80]}"
            failed += 1
        else:
            checks = q.get("checks", [])
            failures = [i for i, c in enumerate(checks) if not c(sql)]
            if failures:
                status = "FAIL"
                reason = f"check(s) {failures} failed. SQL: {sql[:120]}"
                failed += 1
            else:
                status = "PASS"
                reason = sql[:100]
                passed += 1

        icon = "✓" if status == "PASS" else "✗"
        print(f"  {icon} [{qid}] {question}")
        if status == "FAIL":
            print(f"    → {reason}")

        results.append({"id": qid, "question": question, "status": status, "sql": sql, "reason": reason if status == "FAIL" else ""})

    if not sql_only:
        total = passed + failed
        print(f"\n{'='*70}")
        print(f"  Results: {passed}/{total} passed ({100*passed//total}%)")
        if failed:
            print(f"  FAILED: {[r['id'] for r in results if r['status']=='FAIL']}")
        print(f"{'='*70}\n")

    return passed, failed, results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Run with Redshift execution")
    parser.add_argument("--sql-only", action="store_true", help="Print SQL only, no assertions")
    args = parser.parse_args()

    dry_run = not args.live
    passed, failed, _ = run_tests(dry_run=dry_run, sql_only=args.sql_only)
    sys.exit(0 if failed == 0 else 1)
