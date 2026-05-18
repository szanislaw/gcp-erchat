"""
End-to-end test for the 42 target questions.
Tests are executed against the real Athena backend (dry_run=False by default).
Each question is scored PASS/FAIL based on:
  1. SQL generation succeeds
  2. SQL contains expected patterns (structure check)
  3. Athena returns a result (no query error) — only when dry_run=False

Usage:
  python test/test_target_questions.py              # full execution
  python test/test_target_questions.py --dry-run    # SQL generation only, no Redshift call
  python test/test_target_questions.py --sql-only   # only print SQL, no assertions
"""

import requests
import json
import re
import sys
import time
import argparse
from dataclasses import dataclass, field
from typing import List, Optional

API_URL = "http://localhost:8000"
PROPERTY_UUID = "40868b01-a833-4818-9356-de0e0c9cf37f"  # The Peninsula Hong Kong


# ── helpers ──────────────────────────────────────────────────────────────────

def has(pattern, flags=re.IGNORECASE):
    return lambda sql: bool(re.search(pattern, sql, flags))

def has_all(*patterns):
    return lambda sql: all(re.search(p, sql, re.IGNORECASE) for p in patterns)

def has_any(*patterns):
    return lambda sql: any(re.search(p, sql, re.IGNORECASE) for p in patterns)

def has_none(*patterns):
    return lambda sql: not any(re.search(p, sql, re.IGNORECASE) for p in patterns)

def col_eq(col, val):
    return lambda sql: bool(re.search(
        rf"""{col}\s*=\s*['""]{{0,1}}{re.escape(val)}['""]{{0,1}}""", sql, re.IGNORECASE
    ))


# ── corpus ────────────────────────────────────────────────────────────────────

QUESTIONS = [
    # ── Date-filtered counts (this week) ─────────────────────────────────────
    {
        "id": "DW_01", "question": "How many incidents were created this week?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'week'"),
            has_none(r"\bcreated_date\s*[><=]", r"\bincident_time\s*[><=]"),
        ],
        "notes": "COUNT with date_trunc('week') on snapshotdate. NOT using created_date in WHERE.",
    },
    {
        "id": "DW_02", "question": "How many total incidents this week",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'week'"),
        ],
        "notes": "Same as DW_01 — plain COUNT with this-week date_trunc filter.",
    },
    {
        "id": "DW_03", "question": "Show high severity incidents this week",
        "checks": [
            has(r"severity_name"),
            col_eq("severity_name", "high"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'week'"),
        ],
        "notes": "severity='high' AND this-week date filter.",
    },
    {
        "id": "DW_04", "question": "Show pending incidents with location this week",
        "checks": [
            col_eq("status_name", "pending"),
            has(r"location_name"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'week'"),
        ],
        "notes": "status='pending', location_name in SELECT, this-week filter.",
    },
    {
        "id": "DW_05", "question": "Show cancelled incidents this week",
        "checks": [
            col_eq("status_name", "cancelled"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'week'"),
        ],
        "notes": "status='cancelled' + this-week filter.",
    },
    {
        "id": "DW_06", "question": "How many VIP incidents this week",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bvip\b"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'week'"),
        ],
        "notes": "COUNT + vip filter + this-week filter.",
    },
    {
        "id": "DW_07", "question": "Count of incidents by category this week",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bGROUP\s+BY\b"),
            has(r"category_name"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'week'"),
        ],
        "notes": "GROUP BY category_name + this-week filter.",
    },

    # ── Date-filtered counts (this month) ────────────────────────────────────
    {
        "id": "DM_01", "question": "How many incidents were created this month?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'month'"),
            has_none(r"\bcreated_date\s*[><=]"),
        ],
        "notes": "COUNT with date_trunc('month') on snapshotdate.",
    },
    {
        "id": "DM_02", "question": "How many total incidents this month",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'month'"),
        ],
        "notes": "Plain COUNT + this-month filter.",
    },
    {
        "id": "DM_03", "question": "Show high severity incidents this month",
        "checks": [
            col_eq("severity_name", "high"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'month'"),
        ],
        "notes": "severity='high' + this-month filter.",
    },
    {
        "id": "DM_04", "question": "Show pending incidents with location this month",
        "checks": [
            col_eq("status_name", "pending"),
            has(r"location_name"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'month'"),
        ],
        "notes": "status='pending' + location_name + this-month filter.",
    },
    {
        "id": "DM_05", "question": "Show cancelled incidents this month",
        "checks": [
            col_eq("status_name", "cancelled"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'month'"),
        ],
        "notes": "status='cancelled' + this-month filter.",
    },
    {
        "id": "DM_06", "question": "How many VIP incidents this month",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bvip\b"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'month'"),
        ],
        "notes": "COUNT + vip filter + this-month filter.",
    },
    {
        "id": "DM_07", "question": "What are the top 5 incident categories this month?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bGROUP\s+BY\b"),
            has(r"category_name"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'month'"),
            has(r"\bLIMIT\s+5\b"),
        ],
        "notes": "GROUP BY category + this-month + LIMIT 5.",
    },
    {
        "id": "DM_08", "question": "What are the top 5 incident locations this month?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bGROUP\s+BY\b"),
            has(r"location_name"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'month'"),
            has(r"\bLIMIT\s+5\b"),
        ],
        "notes": "GROUP BY location + this-month + LIMIT 5.",
    },
    {
        "id": "DM_09", "question": "Which department has the most incidents this month?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bGROUP\s+BY\b"),
            has(r"department_name"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'month'"),
            has(r"\bORDER\s+BY\b"),
            has(r"\bDESC\b"),
        ],
        "notes": "GROUP BY dept + this-month + ORDER BY COUNT DESC.",
    },

    # ── Last week ─────────────────────────────────────────────────────────────
    {
        "id": "LW_01", "question": "Show total incidents created last week",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_add\s*\(\s*'week'\s*,\s*-1"),
            has(r"date_trunc\s*\(\s*'week'"),
        ],
        "notes": "COUNT + last-week filter: >= date_add('week',-1, date_trunc('week')) AND < date_trunc('week').",
    },

    # ── Simple filters (no date) ──────────────────────────────────────────────
    {
        "id": "SF_01", "question": "Show all high severity incidents.",
        "checks": [
            col_eq("severity_name", "high"),
            has_none(r"\bGROUP\s+BY\b"),
        ],
        "notes": "Plain SELECT with severity_name='high', no GROUP BY.",
    },
    {
        "id": "SF_02", "question": "Show low severity incidents.",
        "checks": [
            col_eq("severity_name", "low"),
        ],
        "notes": "Plain SELECT with severity_name='low'.",
    },
    {
        "id": "SF_03", "question": "Show incidents by location.",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bGROUP\s+BY\b"),
            has(r"location_name"),
        ],
        "notes": "GROUP BY location_name with COUNT.",
    },

    # ── Top/Bottom aggregations ───────────────────────────────────────────────
    {
        "id": "AG_01", "question": "Which category has the most incidents?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bGROUP\s+BY\b"),
            has(r"category_name"),
            has(r"\bORDER\s+BY\b"),
            has(r"\bDESC\b"),
            has(r"\bLIMIT\s+1\b"),
        ],
        "notes": "GROUP BY category ORDER BY COUNT DESC LIMIT 1.",
    },
    {
        "id": "AG_02", "question": "Which severity level occurs most frequently?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bGROUP\s+BY\b"),
            has(r"severity_name"),
            has(r"\bORDER\s+BY\b"),
            has(r"\bDESC\b"),
            has(r"\bLIMIT\s+1\b"),
        ],
        "notes": "GROUP BY severity ORDER BY COUNT DESC LIMIT 1.",
    },
    {
        "id": "AG_03", "question": "Which location has the highest number of incidents?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bGROUP\s+BY\b"),
            has(r"location_name"),
            has(r"\bORDER\s+BY\b"),
            has(r"\bDESC\b"),
            has(r"\bLIMIT\s+1\b"),
        ],
        "notes": "GROUP BY location ORDER BY COUNT DESC LIMIT 1.",
    },
    {
        "id": "AG_04", "question": "Which department reports the least incidents?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bGROUP\s+BY\b"),
            has(r"department_name"),
            has(r"\bORDER\s+BY\b"),
            has(r"\bASC\b"),
            has(r"\bLIMIT\s+1\b"),
        ],
        "notes": "GROUP BY dept ORDER BY COUNT ASC LIMIT 1.",
    },
    {
        "id": "AG_05", "question": "Which location reports the least incidents?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bGROUP\s+BY\b"),
            has(r"location_name"),
            has(r"\bORDER\s+BY\b"),
            has(r"\bASC\b"),
            has(r"\bLIMIT\s+1\b"),
        ],
        "notes": "GROUP BY location ORDER BY COUNT ASC LIMIT 1.",
    },
    {
        "id": "AG_06", "question": "Which category has the most recurring incidents?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bGROUP\s+BY\b"),
            has(r"category_name"),
            has(r"\bORDER\s+BY\b"),
            has(r"\bDESC\b"),
        ],
        "notes": "Recurring = most frequent. GROUP BY category ORDER BY COUNT DESC.",
    },
    {
        "id": "AG_07", "question": "Which department resolves the most incidents?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bGROUP\s+BY\b"),
            has(r"department_name"),
            col_eq("status_name", "completed"),
            has(r"\bORDER\s+BY\b"),
            has(r"\bDESC\b"),
        ],
        "notes": "status='completed' GROUP BY dept ORDER BY COUNT DESC LIMIT 1.",
    },
    {
        "id": "AG_08", "question": "Which location has the most VIP incidents?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bGROUP\s+BY\b"),
            has(r"location_name"),
            has(r"\bvip\b"),
            has(r"\bORDER\s+BY\b"),
            has(r"\bDESC\b"),
        ],
        "notes": "vip filter + GROUP BY location ORDER BY COUNT DESC.",
    },
    {
        "id": "AG_09", "question": "Which location has the most cancelled incidents?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bGROUP\s+BY\b"),
            has(r"location_name"),
            col_eq("status_name", "cancelled"),
            has(r"\bORDER\s+BY\b"),
            has(r"\bDESC\b"),
        ],
        "notes": "status='cancelled' GROUP BY location ORDER BY COUNT DESC.",
    },
    {
        "id": "AG_10", "question": "Which department has the most pending incidents?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bGROUP\s+BY\b"),
            has(r"department_name"),
            col_eq("status_name", "pending"),
            has(r"\bORDER\s+BY\b"),
            has(r"\bDESC\b"),
        ],
        "notes": "status='pending' GROUP BY dept ORDER BY COUNT DESC.",
    },
    {
        "id": "AG_11", "question": "Which department has the most high severity incidents?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bGROUP\s+BY\b"),
            has(r"department_name"),
            col_eq("severity_name", "high"),
            has(r"\bORDER\s+BY\b"),
            has(r"\bDESC\b"),
        ],
        "notes": "severity='high' GROUP BY dept ORDER BY COUNT DESC.",
    },
    {
        "id": "AG_12", "question": "Which locations require attention due to frequent incidents?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bGROUP\s+BY\b"),
            has(r"location_name"),
            has(r"\bORDER\s+BY\b"),
            has(r"\bDESC\b"),
        ],
        "notes": "GROUP BY location ORDER BY COUNT DESC (most frequent = needs attention).",
    },

    # ── Percentage calculations ───────────────────────────────────────────────
    {
        "id": "PC_01", "question": "What percentage of incidents are high severity?",
        "checks": [
            has(r"(100\.0|100\s*\*|CAST\s*\(|ROUND\s*\()"),
            has_any(
                r"COUNT\s*\(\s*CASE\s+WHEN.*severity_name.*THEN",
                r"SUM\s*\(\s*CASE\s+WHEN.*severity_name.*THEN",
            ),
            has(r"high"),
        ],
        "notes": "CAST(COUNT(CASE WHEN severity_name='high' THEN 1 END)*100.0/NULLIF(COUNT(*),0) AS DOUBLE).",
    },
    {
        "id": "PC_02", "question": "What percentage of incidents are VIP incidents?",
        "checks": [
            has(r"(100\.0|100\s*\*|CAST\s*\(|ROUND\s*\()"),
            has_any(
                r"COUNT\s*\(\s*CASE\s+WHEN.*vip",
                r"SUM\s*\(\s*CASE\s+WHEN.*vip",
            ),
        ],
        "notes": "Percentage with vip condition.",
    },
    {
        "id": "PC_03", "question": "What percentage of incidents are completed?",
        "checks": [
            has(r"(100\.0|100\s*\*|CAST\s*\(|ROUND\s*\()"),
            has_any(
                r"COUNT\s*\(\s*CASE\s+WHEN.*status_name.*THEN",
                r"SUM\s*\(\s*CASE\s+WHEN.*status_name.*THEN",
            ),
            has(r"completed"),
        ],
        "notes": "Percentage with status='completed'.",
    },
    {
        "id": "PC_04", "question": "What percentage of incidents are cancelled?",
        "checks": [
            has(r"(100\.0|100\s*\*|CAST\s*\(|ROUND\s*\()"),
            has_any(
                r"COUNT\s*\(\s*CASE\s+WHEN.*status_name.*THEN",
                r"SUM\s*\(\s*CASE\s+WHEN.*status_name.*THEN",
            ),
            has(r"cancelled"),
        ],
        "notes": "Percentage with status='cancelled'.",
    },

    # ── Trend / rising / decreasing ───────────────────────────────────────────
    {
        "id": "TR_01", "question": "Which locations have rising incident trends?",
        "checks": [
            has(r"\bWITH\b"),
            has(r"location_name"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'month'"),
            has(r"\bGROUP\s+BY\b"),
        ],
        "notes": "CTE comparing current vs prev month for location_name, WHERE curr > prev.",
    },
    {
        "id": "TR_02", "question": "Which departments have rising incident costs?",
        "checks": [
            has(r"\bWITH\b"),
            has(r"department_name"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'month'"),
        ],
        "notes": "CTE comparing current vs prev month costs (SUM) for department_name.",
    },
    {
        "id": "TR_03", "question": "Which locations show increasing incident trends?",
        "checks": [
            has(r"\bWITH\b"),
            has(r"location_name"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'month'"),
        ],
        "notes": "Same structure as TR_01.",
    },
    {
        "id": "TR_04", "question": "Which department shows the fastest incident growth?",
        "checks": [
            has(r"\bWITH\b"),
            has(r"department_name"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"\bORDER\s+BY\b"),
            has(r"\bDESC\b"),
        ],
        "notes": "CTE comparing periods for dept, ORDER BY change DESC LIMIT 1.",
    },
    {
        "id": "TR_05", "question": "Which departments have decreasing incidents?",
        "checks": [
            has(r"\bWITH\b"),
            has(r"department_name"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'month'"),
        ],
        "notes": "CTE comparing periods for dept, WHERE curr < prev.",
    },
    {
        "id": "TR_06", "question": "Which locations have decreasing incidents?",
        "checks": [
            has(r"\bWITH\b"),
            has(r"location_name"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'month'"),
        ],
        "notes": "CTE comparing periods for location, WHERE curr < prev.",
    },
]


# ── runner ────────────────────────────────────────────────────────────────────

@dataclass
class Result:
    id: str
    question: str
    notes: str
    sql: str = ""
    score: str = "FAIL"
    passed_checks: int = 0
    total_checks: int = 0
    error: str = ""
    latency_ms: int = 0
    rows_returned: int = -1


_TREND_KEYWORDS = {"rising", "increasing", "decreasing", "growth", "fastest", "trend"}


def call_api(question: str, dry_run: bool = False, max_retries: int = 5) -> dict:
    # Trend questions need more tokens to generate two-CTE SQL
    is_trend = any(kw in question.lower() for kw in _TREND_KEYWORDS)
    payload = {
        "text": question,
        "context": {"property_uuid": PROPERTY_UUID, "language": "en"},
        "sql": {"dialect": "redshift", "tables": []},
        "execution": {"dry_run": dry_run, "max_rows": 100},
        "model": {"max_tokens": 500 if is_trend else 300},
        "trace": {"source": "target_test"},
    }
    for attempt in range(max_retries):
        resp = requests.post(f"{API_URL}/nlq/execute", json=payload, timeout=180)
        if resp.status_code == 429:
            retry_after = float(resp.headers.get("Retry-After", 1))
            time.sleep(retry_after + 0.1)
            continue
        return resp.json()
    return resp.json()


def run_tests(dry_run: bool = False, sql_only: bool = False) -> List[Result]:
    results = []

    print(f"\n{'='*72}")
    print(f"  Target Question Tests  ({len(QUESTIONS)} questions)"
          f"  [{'dry-run' if dry_run else 'LIVE Redshift'}]")
    print(f"{'='*72}\n")

    for item in QUESTIONS:
        print(f"[{item['id']}] {item['question'][:60]}", end="  ", flush=True)

        r = Result(
            id=item["id"],
            question=item["question"],
            notes=item["notes"],
            total_checks=len(item["checks"]),
        )

        try:
            t0 = time.time()
            data = call_api(item["question"], dry_run=dry_run)
            r.latency_ms = int((time.time() - t0) * 1000)

            if not data.get("success"):
                r.error = data.get("error", data.get("detail", "unknown"))[:200]
                r.score = "FAIL"
            else:
                r.sql = data["sql"]["query"]

                if sql_only:
                    print(f"\n  SQL: {r.sql}")
                    results.append(r)
                    continue

                passed = sum(1 for c in item["checks"] if c(r.sql))
                r.passed_checks = passed
                r.total_checks = len(item["checks"])

                # Check execution data if not dry_run
                if not dry_run and data.get("execution", {}).get("data") is not None:
                    rows = data["execution"]["data"]
                    r.rows_returned = len(rows) if isinstance(rows, list) else 0

                if r.passed_checks == r.total_checks:
                    r.score = "PASS"
                elif r.passed_checks >= r.total_checks // 2 + 1:
                    r.score = "PARTIAL"
                else:
                    r.score = "FAIL"

        except Exception as e:
            r.error = str(e)[:200]
            r.score = "FAIL"

        results.append(r)

        icon = {"PASS": "✓", "PARTIAL": "~", "FAIL": "✗"}.get(r.score, "?")
        row_info = f"  rows={r.rows_returned}" if r.rows_returned >= 0 else ""
        print(f"{icon} ({r.passed_checks}/{r.total_checks})  {r.latency_ms}ms{row_info}")

        if r.score != "PASS" and r.sql:
            print(f"       SQL: {r.sql[:140]}")
        if r.error:
            print(f"       ERR: {r.error[:120]}")

    return results


def print_summary(results: List[Result]):
    passed = sum(1 for r in results if r.score == "PASS")
    partial = sum(1 for r in results if r.score == "PARTIAL")
    failed = sum(1 for r in results if r.score == "FAIL")
    total = len(results)
    score_pct = (passed + partial * 0.5) / total * 100 if total else 0

    print(f"\n{'='*72}")
    print(f"  Summary: {passed}/{total} PASS  {partial} PARTIAL  {failed} FAIL")
    print(f"  Score: {score_pct:.0f}%")
    print(f"{'='*72}")

    fails = [r for r in results if r.score in ("FAIL", "PARTIAL")]
    if fails:
        print(f"\nFailed / Partial ({len(fails)}):")
        for r in fails:
            print(f"\n  [{r.id}] {r.question}")
            print(f"  Expected: {r.notes}")
            print(f"  Score:    {r.score} ({r.passed_checks}/{r.total_checks} checks)")
            if r.sql:
                print(f"  SQL:      {r.sql[:160]}")
            if r.error:
                print(f"  Error:    {r.error}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip Redshift execution, check SQL structure only")
    parser.add_argument("--sql-only", action="store_true",
                        help="Just print generated SQL, skip assertions")
    args = parser.parse_args()

    results = run_tests(dry_run=args.dry_run, sql_only=args.sql_only)
    if not args.sql_only:
        print_summary(results)
