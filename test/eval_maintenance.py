"""
Maintenance-order NLQ evaluation suite.

Tests the pipeline against real natural-language questions for the
maintenance_order schema (master_maintenance_status, master_job_priority,
department, property_location).

Scores each result:
  PASS    — all structural checks pass + Redshift execution succeeded
  PARTIAL — structural checks pass but execution failed (SQL generated, DB error)
  FAIL    — structural checks failed (wrong table, missing JOIN, bad date syntax…)

Usage:
  python test/eval_maintenance.py                     # live execution
  python test/eval_maintenance.py --dry-run           # SQL generation only (no DB)
  python test/eval_maintenance.py --category date     # one category
  python test/eval_maintenance.py --verbose           # print full SQL for each question
  python test/eval_maintenance.py --sql-only          # print SQL, skip assertions
  API_URL=http://34.126.131.59:8000 python test/eval_maintenance.py
"""

import os
import re
import sys
import json
import time
import argparse
import requests
from dataclasses import dataclass, field
from typing import List, Callable, Optional

API_URL = os.environ.get("API_URL", "http://localhost:8000")

# Override with a real property UUID from your tenant for live tests.
# Leave empty to send queries without a property filter (broader results).
PROPERTY_UUID = os.environ.get("PROPERTY_UUID", "")

REDSHIFT_TARGET = os.environ.get("REDSHIFT_TARGET", "default")


# ─── Check helpers ────────────────────────────────────────────────────────────

def _named(fn, name: str):
    fn.__name__ = name
    return fn

def has(pattern: str, flags=re.IGNORECASE) -> Callable[[str], bool]:
    return _named(lambda sql: bool(re.search(pattern, sql, flags)),
                  f"has({pattern[:40]})")

def has_all(*patterns: str) -> Callable[[str], bool]:
    return _named(lambda sql: all(re.search(p, sql, re.IGNORECASE) for p in patterns),
                  f"has_all({','.join(p[:20] for p in patterns)})")

def has_any(*patterns: str) -> Callable[[str], bool]:
    return _named(lambda sql: any(re.search(p, sql, re.IGNORECASE) for p in patterns),
                  f"has_any({','.join(p[:20] for p in patterns)})")

def has_none(*patterns: str) -> Callable[[str], bool]:
    return _named(lambda sql: not any(re.search(p, sql, re.IGNORECASE) for p in patterns),
                  f"has_none({','.join(p[:20] for p in patterns)})")

def no_raw_fk(*cols: str) -> Callable[[str], bool]:
    patterns = [rf"\bWHERE\b.*\b{c}\s*=\s*\d" for c in cols]
    return _named(lambda sql: not any(re.search(p, sql, re.IGNORECASE) for p in patterns),
                  f"no_raw_fk({','.join(cols)})")

def uses_redshift_dates(sql: str) -> bool:
    """Fail if Athena date functions appear in generated SQL."""
    return not bool(re.search(r"\bdate_add\s*\(|\bdate_parse\s*\(", sql, re.IGNORECASE))

def no_snapshotdate(sql: str) -> bool:
    return "snapshotdate" not in sql.lower()


# ─── Question corpus ──────────────────────────────────────────────────────────

QUESTIONS = [

    # ═══════════════════════════════════════════════════════════════════════════
    # A — Simple counts (no date filter, no JOIN required)
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "A01", "category": "simple_count",
        "question": "How many total maintenance orders are there?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bmaintenance_order\b"),
            has_none(r"\bGROUP\s+BY\b"),
        ],
        "notes": "Plain COUNT(*) from maintenance_order, no GROUP BY",
    },
    {
        "id": "A02", "category": "simple_count",
        "question": "How many maintenance orders are currently open?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bmaster_maintenance_status\b"),
            has(r"\bstatus_name\b"),
            no_raw_fk("status"),
        ],
        "notes": "Must JOIN master_maintenance_status and filter by status_name",
    },
    {
        "id": "A03", "category": "simple_count",
        "question": "How many maintenance orders have been completed?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bmaster_maintenance_status\b"),
            has(r"\bstatus_name\b"),
        ],
        "notes": "Completed status via JOIN to master_maintenance_status",
    },
    {
        "id": "A04", "category": "simple_count",
        "question": "How many maintenance orders are cancelled?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bmaster_maintenance_status\b"),
            has(r"\bstatus_name\b"),
        ],
        "notes": "Cancelled status via JOIN",
    },
    {
        "id": "A05", "category": "simple_count",
        "question": "How many high priority maintenance orders are there?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bmaster_job_priority\b"),
            has(r"\bpriority_name\b"),
            no_raw_fk("priority"),
        ],
        "notes": "Must JOIN master_job_priority, filter priority_name",
    },
    {
        "id": "A06", "category": "simple_count",
        "question": "How many low priority maintenance orders exist?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bmaster_job_priority\b"),
            has(r"\bpriority_name\b"),
        ],
        "notes": "Low priority via JOIN to master_job_priority",
    },
    {
        "id": "A07", "category": "simple_count",
        "question": "How many urgent maintenance orders are there?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bmaster_job_priority\b"),
            has(r"\bpriority_name\b"),
        ],
        "notes": "Urgent priority via JOIN",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # C — Status / priority breakdown (GROUP BY)
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "C01", "category": "group_by",
        "question": "Show maintenance order count by status",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bmaster_maintenance_status\b"),
            has(r"\bstatus_name\b"),
            has(r"\bGROUP\s+BY\b"),
        ],
        "notes": "GROUP BY status_name via JOIN",
    },
    {
        "id": "C02", "category": "group_by",
        "question": "Show maintenance order count by priority",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bmaster_job_priority\b"),
            has(r"\bpriority_name\b"),
            has(r"\bGROUP\s+BY\b"),
        ],
        "notes": "GROUP BY priority_name via JOIN",
    },
    {
        "id": "C03", "category": "group_by",
        "question": "What is the distribution of maintenance orders by status and priority?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bmaster_maintenance_status\b"),
            has(r"\bmaster_job_priority\b"),
            has(r"\bGROUP\s+BY\b"),
        ],
        "notes": "Multi-JOIN, GROUP BY status + priority",
    },
    {
        "id": "C04", "category": "group_by",
        "question": "Which status has the most maintenance orders?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bmaster_maintenance_status\b"),
            has(r"\bstatus_name\b"),
            has(r"\bORDER\s+BY\b"),
            has(r"\bDESC\b"),
        ],
        "notes": "TOP 1 status by count",
    },
    {
        "id": "C05", "category": "group_by",
        "question": "Show high priority open maintenance orders",
        "checks": [
            has(r"\bmaintenance_order\b"),
            has(r"\bmaster_maintenance_status\b"),
            has(r"\bmaster_job_priority\b"),
            has(r"\bstatus_name\b"),
            has(r"\bpriority_name\b"),
        ],
        "notes": "Filter both status (open) and priority (high)",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # D — Date filtering (validates Redshift date syntax)
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "D01", "category": "date_filter",
        "question": "How many maintenance orders were created this month?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bcreated_date\b"),
            has(r"DATE_TRUNC\s*\(\s*'month'"),
            uses_redshift_dates,
            no_snapshotdate,
        ],
        "notes": "DATE_TRUNC('month', CURRENT_DATE) on created_date",
    },
    {
        "id": "D02", "category": "date_filter",
        "question": "How many maintenance orders were created this week?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bcreated_date\b"),
            has(r"DATE_TRUNC\s*\(\s*'week'"),
            uses_redshift_dates,
        ],
        "notes": "DATE_TRUNC('week', CURRENT_DATE) on created_date",
    },
    {
        "id": "D03", "category": "date_filter",
        "question": "Show maintenance orders created in the last 30 days",
        "checks": [
            has(r"\bcreated_date\b"),
            has(r"DATEADD\s*\(\s*day\s*,\s*-30"),
            uses_redshift_dates,
            no_snapshotdate,
        ],
        "notes": "DATEADD(day, -30, CURRENT_DATE) rolling window",
    },
    {
        "id": "D04", "category": "date_filter",
        "question": "How many maintenance orders were created last week?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bcreated_date\b"),
            has(r"DATE_TRUNC\s*\(\s*'week'"),
            uses_redshift_dates,
        ],
        "notes": "Last week = Mon-Sun calendar boundary via DATE_TRUNC",
    },
    {
        "id": "D05", "category": "date_filter",
        "question": "How many maintenance orders were completed this year?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has_any(r"\bcompleted_date\b", r"\bcreated_date\b"),
            has_any(r"EXTRACT\s*\(\s*YEAR", r"DATE_TRUNC\s*\(\s*'year'"),
            uses_redshift_dates,
        ],
        "notes": "Year filter on date column",
    },
    {
        "id": "D06", "category": "date_filter",
        "question": "Show orders created in the last 7 days",
        "checks": [
            has(r"\bcreated_date\b"),
            has(r"DATEADD\s*\(\s*day\s*,\s*-7"),
            uses_redshift_dates,
            no_snapshotdate,
        ],
        "notes": "DATEADD(day, -7, CURRENT_DATE) rolling window",
    },
    {
        "id": "D07", "category": "date_filter",
        "question": "How many maintenance orders were cancelled last month?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            # Accept either: status JOIN approach OR cancelled_date column filter (both valid)
            has_any(r"\bmaster_maintenance_status\b", r"\bcancelled_date\b"),
            has(r"DATE_TRUNC\s*\(\s*'month'|DATEADD\s*\(\s*month"),
            uses_redshift_dates,
        ],
        "notes": "Status filter + last month date range (accepts cancelled_date filter as alternative)",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # E — Trend queries (DATE_TRUNC GROUP BY)
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "E01", "category": "trend",
        "question": "Show the monthly trend of maintenance orders created",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bcreated_date\b"),
            has(r"DATE_TRUNC\s*\(\s*'month'"),
            has(r"\bGROUP\s+BY\b"),
            has(r"\bORDER\s+BY\b"),
            uses_redshift_dates,
        ],
        "notes": "GROUP BY DATE_TRUNC('month', created_date) with ORDER BY",
    },
    {
        "id": "E02", "category": "trend",
        "question": "Show weekly maintenance order trend for this year",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bcreated_date\b"),
            has(r"DATE_TRUNC\s*\(\s*'week'"),
            has(r"\bGROUP\s+BY\b"),
            uses_redshift_dates,
        ],
        "notes": "GROUP BY DATE_TRUNC('week', created_date)",
    },
    {
        "id": "E03", "category": "trend",
        "question": "How many maintenance orders were created each day this month?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bcreated_date\b"),
            has(r"DATE_TRUNC\s*\(\s*'day'"),
            has(r"\bGROUP\s+BY\b"),
        ],
        "notes": "GROUP BY DATE_TRUNC('day', created_date)",
    },
    {
        "id": "E04", "category": "trend",
        "question": "Show trend of high priority orders by month",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bmaster_job_priority\b"),
            has(r"\bpriority_name\b"),
            has(r"DATE_TRUNC\s*\(\s*'month'"),
            has(r"\bGROUP\s+BY\b"),
        ],
        "notes": "Priority filter + monthly GROUP BY",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # F — Location queries
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "F01", "category": "location",
        "question": "Show maintenance order count by location",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bJOIN\s+property_location\b"),
            has(r"\bGROUP\s+BY\b"),
        ],
        "notes": "JOIN property_location, GROUP BY location",
    },
    {
        "id": "F02", "category": "location",
        "question": "Which location has the most maintenance orders?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bJOIN\s+property_location\b"),
            has(r"\bORDER\s+BY\b"),
            has(r"\bDESC\b"),
        ],
        "notes": "TOP 1 location by count",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # G — Aggregations / metrics
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "G01", "category": "aggregation",
        "question": "What percentage of maintenance orders are completed?",
        "checks": [
            has(r"\bCAST\b|\bFLOAT\b|\b100\.0\b|\bNULLIF\b"),
            has(r"\bmaster_maintenance_status\b"),
            has(r"\bstatus_name\b"),
        ],
        "notes": "Percentage calc: CAST(COUNT(CASE WHEN...) AS FLOAT) * 100 / NULLIF(COUNT(*), 0)",
    },
    {
        "id": "G02", "category": "aggregation",
        "question": "What is the most common maintenance order type?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bGROUP\s+BY\b"),
            has(r"\bORDER\s+BY\b"),
            has(r"\bDESC\b"),
            has(r"LIMIT\s+1\b"),
        ],
        "notes": "GROUP BY type, ORDER BY COUNT DESC LIMIT 1",
    },
    {
        "id": "G03", "category": "aggregation",
        "question": "Show the 10 most recent maintenance orders",
        "checks": [
            has(r"\bORDER\s+BY\b.*\bcreated_date\b|\bcreated_date\b.*\bORDER\s+BY\b"),
            has(r"\bDESC\b"),
            has(r"LIMIT\s+10\b"),
            has_none(r"\bWHERE\b.*\bDATE"),  # no date filter for "recent"
        ],
        "notes": "ORDER BY created_date DESC LIMIT 10 — no date WHERE clause",
    },
    {
        "id": "G04", "category": "aggregation",
        "question": "How many maintenance orders were created vs completed this month?",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has_any(r"\bCASE\s+WHEN\b", r"\bCTE\b|\bWITH\b"),
            has_any(r"\bcreated_date\b", r"\bcompleted_date\b"),
            has(r"DATE_TRUNC\s*\(\s*'month'"),
        ],
        "notes": "Compare two counts in same query — CASE WHEN or CTE",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # H — Hallucination guards (things the model historically gets wrong)
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "H04", "category": "hallucination_guard",
        "question": "What are the most recent 5 completed maintenance orders?",
        "checks": [
            has(r"\bmaster_maintenance_status\b"),
            has(r"\bstatus_name\b"),
            has(r"\bORDER\s+BY\b.*\bcreated_date\b|\bcreated_date\b.*\bORDER\s+BY\b"),
            has(r"LIMIT\s+[15]\b"),
            no_raw_fk("status"),
            no_snapshotdate,
        ],
        "notes": "Status JOIN (not raw int), ORDER BY created_date DESC, LIMIT 5",
    },
    {
        "id": "H05", "category": "hallucination_guard",
        "question": "Show cancelled orders from last month grouped by priority",
        "checks": [
            has(r"\bmaster_maintenance_status\b"),
            has(r"\bmaster_job_priority\b"),
            has(r"\bpriority_name\b"),
            has(r"\bstatus_name\b"),
            has(r"DATE_TRUNC\s*\(\s*'month'"),
            has(r"\bGROUP\s+BY\b"),
            uses_redshift_dates,
            no_snapshotdate,
        ],
        "notes": "Status + priority JOIN + last month date + GROUP BY",
    },
]


# ─── API call ─────────────────────────────────────────────────────────────────

def call_api(question: str, dry_run: bool) -> dict:
    payload = {
        "text": question,
        "context": {
            "property_uuid": PROPERTY_UUID,
            "user_uuid": "",
            "language": "en",
        },
        "sql": {"dialect": "redshift", "tables": []},
        "execution": {
            "dry_run": dry_run,
            "max_rows": 5,
            "redshift_target": REDSHIFT_TARGET,
        },
        "model": {"max_tokens": 256},
        "trace": {"source": "eval_maintenance"},
    }
    resp = requests.post(f"{API_URL}/nlq/execute", json=payload, timeout=120)
    return resp.json(), resp.status_code


# ─── Result dataclass ─────────────────────────────────────────────────────────

@dataclass
class Result:
    id: str
    category: str
    question: str
    notes: str
    sql: str
    status: str            # PASS / PARTIAL / FAIL / ERROR
    failed_checks: List[str] = field(default_factory=list)
    exec_error: Optional[str] = None
    latency_ms: int = 0
    row_count: Optional[int] = None


# ─── Evaluation logic ─────────────────────────────────────────────────────────

def evaluate(q: dict, dry_run: bool, verbose: bool, sql_only: bool) -> Result:
    t0 = time.time()
    try:
        data, status_code = call_api(q["question"], dry_run)
    except Exception as e:
        return Result(
            id=q["id"], category=q["category"], question=q["question"],
            notes=q.get("notes", ""), sql="", status="ERROR",
            exec_error=str(e), latency_ms=int((time.time() - t0) * 1000),
        )

    sql = ""
    exec_error = None
    row_count = None

    if status_code == 200 and data.get("success"):
        sql = data.get("sql", {}).get("query", "")
        exec_info = data.get("execution", {})
        row_count = exec_info.get("row_count")
        lat = data.get("trace", {}).get("latency_ms", {})
        latency_ms = lat.get("total_ms", int((time.time() - t0) * 1000))
    else:
        exec_error = data.get("detail") or data.get("error") or f"HTTP {status_code}"
        latency_ms = int((time.time() - t0) * 1000)

    if sql_only:
        print(f"\n[{q['id']}] {q['question']}")
        print(f"  SQL: {sql or '(none)'}")
        return Result(
            id=q["id"], category=q["category"], question=q["question"],
            notes=q.get("notes", ""), sql=sql, status="SKIP", latency_ms=latency_ms,
        )

    # Run structural checks
    failed_checks = []
    if sql:
        for check_fn in q.get("checks", []):
            try:
                if not check_fn(sql):
                    # Attempt to name the check from its source
                    name = getattr(check_fn, "__name__", repr(check_fn))
                    failed_checks.append(name)
            except Exception as e:
                failed_checks.append(f"check_error({e})")

    # Determine status
    if not sql and exec_error:
        status = "ERROR"
    elif failed_checks:
        status = "FAIL"
    elif exec_error and not dry_run:
        status = "PARTIAL"   # SQL generated OK but Redshift rejected it
    else:
        status = "PASS"

    result = Result(
        id=q["id"], category=q["category"], question=q["question"],
        notes=q.get("notes", ""), sql=sql, status=status,
        failed_checks=failed_checks, exec_error=exec_error,
        latency_ms=latency_ms, row_count=row_count,
    )

    # Live feedback
    icon = {"PASS": "✓", "PARTIAL": "~", "FAIL": "✗", "ERROR": "!", "SKIP": " "}[status]
    color = {"PASS": "\033[32m", "PARTIAL": "\033[33m", "FAIL": "\033[31m",
             "ERROR": "\033[31m", "SKIP": ""}[status]
    reset = "\033[0m"
    row_str = f"  {row_count} rows" if row_count is not None else ""
    print(f"  {color}{icon}{reset} [{q['id']}] {q['question'][:65]:<65}  {latency_ms:>5}ms{row_str}")

    if verbose and sql:
        print(f"      SQL: {sql[:160]}")
    if failed_checks:
        print(f"      FAILED CHECKS: {', '.join(failed_checks)}")
    if exec_error and status in ("PARTIAL", "ERROR"):
        print(f"      ERROR: {exec_error[:120]}")

    return result


# ─── Report ────────────────────────────────────────────────────────────────────

def print_report(results: List[Result], dry_run: bool):
    total = len([r for r in results if r.status != "SKIP"])
    by_status = {}
    for r in results:
        by_status.setdefault(r.status, []).append(r)

    passes   = len(by_status.get("PASS", []))
    partials = len(by_status.get("PARTIAL", []))
    fails    = len(by_status.get("FAIL", []))
    errors   = len(by_status.get("ERROR", []))

    print("\n" + "═" * 72)
    print("  MAINTENANCE NLQ EVAL — SUMMARY")
    print("═" * 72)
    print(f"  Total questions : {total}")
    print(f"  PASS            : {passes}  ({100*passes//total if total else 0}%)")
    if not dry_run:
        print(f"  PARTIAL         : {partials}  (SQL ok, Redshift error)")
    print(f"  FAIL            : {fails}  (structural checks failed)")
    print(f"  ERROR           : {errors}  (API/network error)")

    # By category
    cats = {}
    for r in results:
        if r.status == "SKIP":
            continue
        cats.setdefault(r.category, {"pass": 0, "total": 0})
        cats[r.category]["total"] += 1
        if r.status == "PASS":
            cats[r.category]["pass"] += 1

    print("\n  BY CATEGORY:")
    for cat, s in sorted(cats.items()):
        pct = 100 * s["pass"] // s["total"] if s["total"] else 0
        bar = ("█" * (pct // 10)).ljust(10)
        print(f"    {cat:<22} {s['pass']:>2}/{s['total']:<2}  [{bar}] {pct}%")

    # Failed questions detail
    failed = [r for r in results if r.status in ("FAIL", "PARTIAL", "ERROR")]
    if failed:
        print(f"\n  FAILURES ({len(failed)}):")
        for r in failed:
            print(f"    [{r.id}] {r.status}  {r.question[:60]}")
            if r.failed_checks:
                print(f"          checks: {', '.join(r.failed_checks)}")
            if r.exec_error:
                print(f"          error:  {r.exec_error[:100]}")
            if r.sql:
                print(f"          sql:    {r.sql[:120]}")

    print("═" * 72)


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Maintenance NLQ evaluation suite")
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip Redshift execution — SQL generation only")
    parser.add_argument("--category", metavar="CAT",
                        help="Run only this category (e.g. department, date_filter)")
    parser.add_argument("--id", metavar="ID",
                        help="Run a single question by ID (e.g. B01)")
    parser.add_argument("--verbose", action="store_true",
                        help="Print generated SQL for each question")
    parser.add_argument("--sql-only", action="store_true",
                        help="Print SQL only, skip assertions")
    args = parser.parse_args()

    questions = QUESTIONS
    if args.category:
        questions = [q for q in questions if q["category"] == args.category]
    if args.id:
        questions = [q for q in questions if q["id"] == args.id]

    if not questions:
        print("No questions matched filters.")
        sys.exit(1)

    mode = "dry-run (SQL only)" if args.dry_run else "live (SQL + Redshift execution)"
    print(f"\nMaintenance NLQ Eval — {len(questions)} questions — {mode}")
    print(f"API: {API_URL}   target: {REDSHIFT_TARGET}   property_uuid: {PROPERTY_UUID or '(none)'}\n")

    # Health check
    try:
        r = requests.get(f"{API_URL}/health", timeout=10)
        if r.status_code != 200:
            print(f"WARNING: /health returned {r.status_code}")
    except Exception as e:
        print(f"ERROR: Cannot reach API at {API_URL}: {e}")
        sys.exit(1)

    results = []
    for q in questions:
        result = evaluate(q, dry_run=args.dry_run, verbose=args.verbose, sql_only=args.sql_only)
        results.append(result)

    if not args.sql_only:
        print_report(results, dry_run=args.dry_run)

    # Exit code: non-zero if any failures
    fail_count = sum(1 for r in results if r.status in ("FAIL", "ERROR"))
    sys.exit(1 if fail_count > 0 else 0)


if __name__ == "__main__":
    main()
