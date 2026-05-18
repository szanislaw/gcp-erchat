"""
50-question test suite covering all major query patterns.
Designed to be high-confidence: every question maps to a well-understood
SQL pattern with tight structural assertions.

Usage:
  python test/test_50_questions.py              # live Redshift
  python test/test_50_questions.py --dry-run    # SQL generation only
  python test/test_50_questions.py --sql-only   # print SQL, no assertions
"""

import requests
import json
import re
import sys
import time
import argparse
from dataclasses import dataclass
from typing import List

import os
API_URL = os.environ.get("API_URL", "http://localhost:8000")
PROPERTY_UUID = "40868b01-a833-4818-9356-de0e0c9cf37f"  # The Peninsula Hong Kong

# ── check helpers ─────────────────────────────────────────────────────────────

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
        rf"""{col}\s*=\s*['"]{{0,1}}{re.escape(val)}['"]{{0,1}}""", sql, re.IGNORECASE
    ))

# ── corpus ────────────────────────────────────────────────────────────────────

QUESTIONS = [
    # ═══════════════════════════════════════════════════════════════════════════
    # CATEGORY A: Simple counts (no date filter) — 8 questions
    # Very high confidence: single COUNT, property filter, no GROUP BY
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "A01",
        "question": "How many total incidents are there?",
        "checks": [has(r"\bCOUNT\s*\("), has(r"\bincident_combine\b"), has_none(r"\bGROUP\s+BY\b")],
        "notes": "Plain COUNT(*) with no GROUP BY",
    },
    {
        "id": "A02",
        "question": "How many high severity incidents?",
        "checks": [has(r"\bCOUNT\s*\("), col_eq("severity_name", "high")],
        "notes": "COUNT + severity_name='high'",
    },
    {
        "id": "A03",
        "question": "How many pending incidents are there?",
        "checks": [has(r"\bCOUNT\s*\("), col_eq("status_name", "pending")],
        "notes": "COUNT + status_name='pending'",
    },
    {
        "id": "A04",
        "question": "How many completed incidents?",
        "checks": [has(r"\bCOUNT\s*\("), col_eq("status_name", "completed")],
        "notes": "COUNT + status_name='completed'",
    },
    {
        "id": "A05",
        "question": "How many cancelled incidents?",
        "checks": [has(r"\bCOUNT\s*\("), col_eq("status_name", "cancelled")],
        "notes": "COUNT + status_name='cancelled'",
    },
    {
        "id": "A06",
        "question": "How many VIP incidents are there?",
        "checks": [has(r"\bCOUNT\s*\("), has(r"\bvip\b")],
        "notes": "COUNT + vip filter",
    },
    {
        "id": "A07",
        "question": "What is the total cost of all incidents?",
        "checks": [has(r"\bSUM\s*\("), has(r"actual_cost"), has_none(r"\bGROUP\s+BY\b")],
        "notes": "SUM(actual_cost) with no GROUP BY",
    },
    {
        "id": "A08",
        "question": "What is the average incident cost?",
        "checks": [has(r"\bAVG\s*\("), has(r"actual_cost"), has_none(r"\bGROUP\s+BY\b")],
        "notes": "AVG(actual_cost) with no GROUP BY",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # CATEGORY B: GROUP BY aggregations — 10 questions
    # COUNT or SUM + GROUP BY a categorical column
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "B01",
        "question": "Show incident count by severity",
        "checks": [has(r"\bCOUNT\s*\("), has(r"\bGROUP\s+BY\b"), has(r"severity_name")],
        "notes": "GROUP BY severity_name",
    },
    {
        "id": "B02",
        "question": "Show incident count by status",
        "checks": [has(r"\bCOUNT\s*\("), has(r"\bGROUP\s+BY\b"), has(r"status_name")],
        "notes": "GROUP BY status_name",
    },
    {
        "id": "B03",
        "question": "How many incidents per category?",
        "checks": [has(r"\bCOUNT\s*\("), has(r"\bGROUP\s+BY\b"), has(r"category_name")],
        "notes": "GROUP BY category_name",
    },
    {
        "id": "B04",
        "question": "How many incidents does each department have?",
        "checks": [has(r"\bCOUNT\s*\("), has(r"\bGROUP\s+BY\b"), has(r"department_name")],
        "notes": "GROUP BY department_name",
    },
    {
        "id": "B05",
        "question": "Show incidents by location",
        "checks": [has(r"\bCOUNT\s*\("), has(r"\bGROUP\s+BY\b"), has(r"location_name")],
        "notes": "GROUP BY location_name",
    },
    {
        "id": "B06",
        "question": "Show total cost by category",
        "checks": [has(r"\bSUM\s*\("), has(r"actual_cost"), has(r"\bGROUP\s+BY\b"), has(r"category_name")],
        "notes": "SUM(actual_cost) GROUP BY category_name",
    },
    {
        "id": "B07",
        "question": "Show total cost by department",
        "checks": [has(r"\bSUM\s*\("), has(r"actual_cost"), has(r"\bGROUP\s+BY\b"), has(r"department_name")],
        "notes": "SUM(actual_cost) GROUP BY department_name",
    },
    {
        "id": "B08",
        "question": "Show average cost by severity",
        "checks": [has(r"\bAVG\s*\("), has(r"actual_cost"), has(r"\bGROUP\s+BY\b"), has(r"severity_name")],
        "notes": "AVG(actual_cost) GROUP BY severity_name",
    },
    {
        "id": "B09",
        "question": "Show average cost by status",
        "checks": [has(r"\bAVG\s*\("), has(r"actual_cost"), has(r"\bGROUP\s+BY\b"), has(r"status_name")],
        "notes": "AVG(actual_cost) GROUP BY status_name",
    },
    {
        "id": "B10",
        "question": "Show incident count by profile",
        "checks": [has(r"\bCOUNT\s*\("), has(r"\bGROUP\s+BY\b"), has(r"profile_name")],
        "notes": "GROUP BY profile_name",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # CATEGORY C: Top / bottom N — 10 questions
    # GROUP BY + ORDER BY + LIMIT, with optional filter
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "C01",
        "question": "Which category has the most incidents?",
        "checks": [
            has(r"\bCOUNT\s*\("), has(r"\bGROUP\s+BY\b"), has(r"category_name"),
            has(r"\bORDER\s+BY\b"), has(r"\bDESC\b"), has(r"\bLIMIT\s+1\b"),
        ],
        "notes": "GROUP BY category ORDER BY COUNT DESC LIMIT 1",
    },
    {
        "id": "C02",
        "question": "Which location has the highest number of incidents?",
        "checks": [
            has(r"\bCOUNT\s*\("), has(r"\bGROUP\s+BY\b"), has(r"location_name"),
            has(r"\bORDER\s+BY\b"), has(r"\bDESC\b"), has(r"\bLIMIT\s+1\b"),
        ],
        "notes": "GROUP BY location ORDER BY COUNT DESC LIMIT 1",
    },
    {
        "id": "C03",
        "question": "Which department has the most pending incidents?",
        "checks": [
            has(r"\bCOUNT\s*\("), has(r"\bGROUP\s+BY\b"), has(r"department_name"),
            col_eq("status_name", "pending"), has(r"\bORDER\s+BY\b"), has(r"\bDESC\b"),
        ],
        "notes": "status='pending' GROUP BY dept ORDER BY COUNT DESC",
    },
    {
        "id": "C04",
        "question": "Which department has the most high severity incidents?",
        "checks": [
            has(r"\bCOUNT\s*\("), has(r"\bGROUP\s+BY\b"), has(r"department_name"),
            col_eq("severity_name", "high"), has(r"\bORDER\s+BY\b"), has(r"\bDESC\b"),
        ],
        "notes": "severity='high' GROUP BY dept ORDER BY COUNT DESC",
    },
    {
        "id": "C05",
        "question": "Which department resolves the most incidents?",
        "checks": [
            has(r"\bCOUNT\s*\("), has(r"\bGROUP\s+BY\b"), has(r"department_name"),
            col_eq("status_name", "completed"), has(r"\bORDER\s+BY\b"), has(r"\bDESC\b"),
        ],
        "notes": "status='completed' GROUP BY dept ORDER BY COUNT DESC",
    },
    {
        "id": "C06",
        "question": "Which location has the most VIP incidents?",
        "checks": [
            has(r"\bCOUNT\s*\("), has(r"\bGROUP\s+BY\b"), has(r"location_name"),
            has(r"\bvip\b"), has(r"\bORDER\s+BY\b"), has(r"\bDESC\b"),
        ],
        "notes": "vip filter GROUP BY location ORDER BY COUNT DESC",
    },
    {
        "id": "C07",
        "question": "What are the top 5 incident categories?",
        "checks": [
            has(r"\bCOUNT\s*\("), has(r"\bGROUP\s+BY\b"), has(r"category_name"),
            has(r"\bORDER\s+BY\b"), has(r"\bDESC\b"), has(r"\bLIMIT\s+5\b"),
        ],
        "notes": "GROUP BY category ORDER BY COUNT DESC LIMIT 5",
    },
    {
        "id": "C08",
        "question": "What are the top 5 locations with the most incidents?",
        "checks": [
            has(r"\bCOUNT\s*\("), has(r"\bGROUP\s+BY\b"), has(r"location_name"),
            has(r"\bORDER\s+BY\b"), has(r"\bDESC\b"), has(r"\bLIMIT\s+5\b"),
        ],
        "notes": "GROUP BY location ORDER BY COUNT DESC LIMIT 5",
    },
    {
        "id": "C09",
        "question": "Which location reports the fewest incidents?",
        "checks": [
            has(r"\bCOUNT\s*\("), has(r"\bGROUP\s+BY\b"), has(r"location_name"),
            has(r"\bORDER\s+BY\b"), has(r"\bASC\b"), has(r"\bLIMIT\s+1\b"),
        ],
        "notes": "GROUP BY location ORDER BY COUNT ASC LIMIT 1",
    },
    {
        "id": "C10",
        "question": "Which category has the most recurring incidents?",
        "checks": [
            has(r"\bCOUNT\s*\("), has(r"\bGROUP\s+BY\b"), has(r"category_name"),
            has(r"\bORDER\s+BY\b"), has(r"\bDESC\b"),
        ],
        "notes": "Recurring = most frequent. GROUP BY category ORDER BY COUNT DESC",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # CATEGORY D: Date-filtered queries — 12 questions
    # this week (date_trunc week), this month (date_trunc month), last week
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "D01",
        "question": "How many incidents were created this week?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'week'"),
            has_none(r"\bcreated_date\s*[><=]"),
        ],
        "notes": "COUNT + date_trunc('week') on snapshotdate",
    },
    {
        "id": "D02",
        "question": "How many incidents this month?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'month'"),
        ],
        "notes": "COUNT + date_trunc('month') on snapshotdate",
    },
    {
        "id": "D03",
        "question": "How many high severity incidents this week?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            col_eq("severity_name", "high"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'week'"),
        ],
        "notes": "severity='high' + this-week filter",
    },
    {
        "id": "D04",
        "question": "How many high severity incidents this month?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            col_eq("severity_name", "high"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'month'"),
        ],
        "notes": "severity='high' + this-month filter",
    },
    {
        "id": "D05",
        "question": "How many VIP incidents this week?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bvip\b"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'week'"),
        ],
        "notes": "COUNT + vip + this-week filter",
    },
    {
        "id": "D06",
        "question": "How many VIP incidents this month?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bvip\b"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'month'"),
        ],
        "notes": "COUNT + vip + this-month filter",
    },
    {
        "id": "D07",
        "question": "Show incident count by category this week",
        "checks": [
            has(r"\bCOUNT\s*\("), has(r"\bGROUP\s+BY\b"), has(r"category_name"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'week'"),
        ],
        "notes": "GROUP BY category + this-week filter",
    },
    {
        "id": "D08",
        "question": "Show incident count by category this month",
        "checks": [
            has(r"\bCOUNT\s*\("), has(r"\bGROUP\s+BY\b"), has(r"category_name"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'month'"),
        ],
        "notes": "GROUP BY category + this-month filter",
    },
    {
        "id": "D09",
        "question": "Which department has the most incidents this month?",
        "checks": [
            has(r"\bCOUNT\s*\("), has(r"\bGROUP\s+BY\b"), has(r"department_name"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'month'"),
            has(r"\bORDER\s+BY\b"), has(r"\bDESC\b"),
        ],
        "notes": "GROUP BY dept + this-month + ORDER BY COUNT DESC",
    },
    {
        "id": "D10",
        "question": "What are the top 5 incident categories this month?",
        "checks": [
            has(r"\bCOUNT\s*\("), has(r"\bGROUP\s+BY\b"), has(r"category_name"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'month'"),
            has(r"\bLIMIT\s+5\b"),
        ],
        "notes": "GROUP BY category + this-month + LIMIT 5",
    },
    {
        "id": "D11",
        "question": "Show pending incidents this week",
        "checks": [
            col_eq("status_name", "pending"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'week'"),
        ],
        "notes": "status='pending' + this-week filter",
    },
    {
        "id": "D12",
        "question": "How many incidents were created last week?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_add\s*\(\s*'week'\s*,\s*-1"),
            has(r"date_trunc\s*\(\s*'week'"),
        ],
        "notes": "COUNT + last-week calendar boundary (date_add('week',-1,...) AND < date_trunc('week'))",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # CATEGORY E: Percentage calculations — 4 questions
    # CAST(COUNT(CASE WHEN...) * 100.0 / NULLIF(COUNT(*), 0) AS DOUBLE)
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "E01",
        "question": "What percentage of incidents are high severity?",
        "checks": [
            has(r"(100\.0|100\s*\*|CAST\s*\(|ROUND\s*\()"),
            has_any(
                r"COUNT\s*\(\s*CASE\s+WHEN.*severity_name",
                r"SUM\s*\(\s*CASE\s+WHEN.*severity_name",
            ),
            has(r"high"),
        ],
        "notes": "Percentage formula with severity_name='high' condition",
    },
    {
        "id": "E02",
        "question": "What percentage of incidents are VIP?",
        "checks": [
            has(r"(100\.0|100\s*\*|CAST\s*\(|ROUND\s*\()"),
            has_any(
                r"COUNT\s*\(\s*CASE\s+WHEN.*vip",
                r"SUM\s*\(\s*CASE\s+WHEN.*vip",
            ),
        ],
        "notes": "Percentage formula with vip condition",
    },
    {
        "id": "E03",
        "question": "What percentage of incidents are completed?",
        "checks": [
            has(r"(100\.0|100\s*\*|CAST\s*\(|ROUND\s*\()"),
            has_any(
                r"COUNT\s*\(\s*CASE\s+WHEN.*status_name",
                r"SUM\s*\(\s*CASE\s+WHEN.*status_name",
            ),
            has(r"completed"),
        ],
        "notes": "Percentage formula with status_name='completed'",
    },
    {
        "id": "E04",
        "question": "What percentage of incidents are cancelled?",
        "checks": [
            has(r"(100\.0|100\s*\*|CAST\s*\(|ROUND\s*\()"),
            has_any(
                r"COUNT\s*\(\s*CASE\s+WHEN.*status_name",
                r"SUM\s*\(\s*CASE\s+WHEN.*status_name",
            ),
            has(r"cancelled"),
        ],
        "notes": "Percentage formula with status_name='cancelled'",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # CATEGORY F: Trend / rising / decreasing (CTE) — 6 questions
    # Must use WITH ... AS (...) two-CTE pattern + date_trunc('month')
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "F01",
        "question": "Which categories have rising incident trends?",
        "checks": [
            has(r"\bWITH\b"), has(r"category_name"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'month'"), has(r"\bGROUP\s+BY\b"),
        ],
        "notes": "CTE comparing curr vs prev month for category_name",
    },
    {
        "id": "F02",
        "question": "Which locations have rising incident trends?",
        "checks": [
            has(r"\bWITH\b"), has(r"location_name"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'month'"), has(r"\bGROUP\s+BY\b"),
        ],
        "notes": "CTE comparing curr vs prev month for location_name",
    },
    {
        "id": "F03",
        "question": "Which departments have rising incident trends?",
        "checks": [
            has(r"\bWITH\b"), has(r"department_name"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'month'"),
        ],
        "notes": "CTE comparing curr vs prev month for department_name",
    },
    {
        "id": "F04",
        "question": "Which department shows the fastest incident growth?",
        "checks": [
            has(r"\bWITH\b"), has(r"department_name"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"\bORDER\s+BY\b"), has(r"\bDESC\b"),
        ],
        "notes": "CTE for dept, ORDER BY change DESC LIMIT 1",
    },
    {
        "id": "F05",
        "question": "Which departments have decreasing incidents?",
        "checks": [
            has(r"\bWITH\b"), has(r"department_name"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'month'"),
        ],
        "notes": "CTE for dept, WHERE curr < prev",
    },
    {
        "id": "F06",
        "question": "Which locations show increasing incident trends?",
        "checks": [
            has(r"\bWITH\b"), has(r"location_name"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_trunc\s*\(\s*'month'"),
        ],
        "notes": "CTE for location, WHERE curr > prev",
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


def call_api(question: str, dry_run: bool = False) -> dict:
    is_trend = any(kw in question.lower() for kw in _TREND_KEYWORDS)
    payload = {
        "text": question,
        "context": {"property_uuid": PROPERTY_UUID, "language": "en"},
        "sql": {"dialect": "redshift", "tables": []},
        "execution": {"dry_run": dry_run, "max_rows": 100},
        "model": {"max_tokens": 500 if is_trend else 300},
        "trace": {"source": "test_50"},
    }
    for attempt in range(5):
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
    print(f"  50-Question Test Suite  ({len(QUESTIONS)} questions)"
          f"  [{'dry-run' if dry_run else 'LIVE Redshift'}]")
    print(f"{'='*72}\n")

    categories = {
        "A": "Simple counts",
        "B": "GROUP BY aggregations",
        "C": "Top/bottom N",
        "D": "Date-filtered",
        "E": "Percentage",
        "F": "Trend / CTE",
    }
    current_cat = None

    for item in QUESTIONS:
        cat = item["id"][0]
        if cat != current_cat:
            current_cat = cat
            print(f"\n── {categories[cat]} ──")

        print(f"  [{item['id']}] {item['question'][:58]}", end="  ", flush=True)

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
                    print(f"\n       SQL: {r.sql}")
                    results.append(r)
                    continue

                r.passed_checks = sum(1 for c in item["checks"] if c(r.sql))

                if not dry_run:
                    exec_data = data.get("execution", {}).get("data")
                    if exec_data is not None:
                        r.rows_returned = exec_data.get("row_count", 0) if isinstance(exec_data, dict) else len(exec_data)

                if r.passed_checks == r.total_checks:
                    r.score = "PASS"
                elif r.passed_checks >= (r.total_checks + 1) // 2:
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
            print(f"         SQL: {r.sql[:140]}")
        if r.error:
            print(f"         ERR: {r.error[:120]}")

    return results


def print_summary(results: List[Result]):
    passed  = sum(1 for r in results if r.score == "PASS")
    partial = sum(1 for r in results if r.score == "PARTIAL")
    failed  = sum(1 for r in results if r.score == "FAIL")
    total   = len(results)
    score_pct = (passed + partial * 0.5) / total * 100 if total else 0

    # Per-category breakdown
    cats = sorted({r.id[0] for r in results})
    print(f"\n{'='*72}")
    print(f"  Summary: {passed}/{total} PASS  {partial} PARTIAL  {failed} FAIL  "
          f"({score_pct:.0f}%)")
    print(f"  {'─'*60}")
    cat_names = {"A":"Simple counts","B":"GROUP BY","C":"Top/bottom N",
                 "D":"Date-filtered","E":"Percentage","F":"Trend/CTE"}
    for cat in cats:
        cat_results = [r for r in results if r.id[0] == cat]
        cp = sum(1 for r in cat_results if r.score == "PASS")
        ct = len(cat_results)
        print(f"  {cat} {cat_names.get(cat,''):20s}  {cp}/{ct} PASS")
    print(f"{'='*72}")

    fails = [r for r in results if r.score in ("FAIL", "PARTIAL")]
    if fails:
        print(f"\nFailed / Partial ({len(fails)}):")
        for r in fails:
            print(f"\n  [{r.id}] {r.question}")
            print(f"  Expected: {r.notes}")
            print(f"  Score:    {r.score} ({r.passed_checks}/{r.total_checks} checks)")
            if r.sql:
                print(f"  SQL:      {r.sql[:200]}")
            if r.error:
                print(f"  Error:    {r.error}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip Redshift execution, SQL structure check only")
    parser.add_argument("--sql-only", action="store_true",
                        help="Print generated SQL without assertions")
    args = parser.parse_args()

    results = run_tests(dry_run=args.dry_run, sql_only=args.sql_only)
    if not args.sql_only:
        print_summary(results)
