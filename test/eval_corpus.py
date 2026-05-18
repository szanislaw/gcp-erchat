"""
NL-to-SQL Evaluation Corpus
Tests the pipeline against 40 questions across 8 SQL categories.
Scores each generated SQL as PASS / PARTIAL / FAIL based on expected patterns.
"""

import requests, json, re, sys, time
from dataclasses import dataclass, field
from typing import Optional

API_URL = "http://localhost:8000"
# Use a real property UUID (The Peninsula Hong Kong)
PROPERTY_UUID = "40868b01-a833-4818-9356-de0e0c9cf37f"

# ──────────────────────────────────────────────────────────────────────────────
# Corpus definition
# Each entry: question, category, and a list of check functions (sql: str → bool)
# ──────────────────────────────────────────────────────────────────────────────

def has(pattern, flags=re.IGNORECASE):
    return lambda sql: bool(re.search(pattern, sql, flags))

def has_all(*patterns):
    return lambda sql: all(re.search(p, sql, re.IGNORECASE) for p in patterns)

def has_none(*patterns):
    return lambda sql: not any(re.search(p, sql, re.IGNORECASE) for p in patterns)

def col_eq(col, val):
    """Column = 'value' check (handles single or double quotes)."""
    return lambda sql: bool(re.search(rf"""{col}\s*=\s*['"]{{0,1}}{re.escape(val)}['"]{{0,1}}""", sql, re.IGNORECASE))

CORPUS = [
    # ── TIER 1: Simple COUNT ──────────────────────────────────────────────────
    {
        "id": "T1_01",
        "question": "How many total incidents are there?",
        "category": "simple_count",
        "checks": [has(r"\bCOUNT\s*\("), has(r"\bincident_combine\b"), has_none(r"\bGROUP\s+BY\b")],
        "notes": "Should be a single COUNT with no GROUP BY",
    },
    {
        "id": "T1_02",
        "question": "How many high severity incidents?",
        "category": "simple_count",
        "checks": [has(r"\bCOUNT\s*\("), has(r"severity_name"), col_eq("severity_name", "high")],
        "notes": "Must use severity_name = 'high' (lowercase)",
    },
    {
        "id": "T1_03",
        "question": "How many pending incidents are there?",
        "category": "simple_count",
        "checks": [has(r"\bCOUNT\s*\("), has(r"status_name"), col_eq("status_name", "pending")],
        "notes": "Must use status_name = 'pending'",
    },
    {
        "id": "T1_04",
        "question": "How many incidents were reported by guests?",
        "category": "simple_count",
        "checks": [has(r"\bCOUNT\s*\("), has(r"profile_name"), col_eq("profile_name", "guest")],
        "notes": "Must filter profile_name = 'guest'",
    },
    {
        "id": "T1_05",
        "question": "How many critical incidents exist?",
        "category": "simple_count",
        "checks": [has(r"\bCOUNT\s*\("), col_eq("severity_name", "critical")],
        "notes": "Must use severity_name = 'critical'",
    },

    # ── TIER 2: GROUP BY ──────────────────────────────────────────────────────
    {
        "id": "T2_01",
        "question": "Show incident count by severity",
        "category": "group_by",
        "checks": [has(r"\bCOUNT\s*\("), has(r"\bGROUP\s+BY\b"), has(r"severity_name")],
        "notes": "GROUP BY severity_name with COUNT",
    },
    {
        "id": "T2_02",
        "question": "How many incidents per category?",
        "category": "group_by",
        "checks": [has(r"\bCOUNT\s*\("), has(r"\bGROUP\s+BY\b"), has(r"category_name")],
        "notes": "GROUP BY category_name",
    },
    {
        "id": "T2_03",
        "question": "Show incident breakdown by status",
        "category": "group_by",
        "checks": [has(r"\bCOUNT\s*\("), has(r"\bGROUP\s+BY\b"), has(r"status_name")],
        "notes": "GROUP BY status_name",
    },
    {
        "id": "T2_04",
        "question": "How many incidents does each department have?",
        "category": "group_by",
        "checks": [has(r"\bCOUNT\s*\("), has(r"\bGROUP\s+BY\b"), has(r"department_name")],
        "notes": "GROUP BY department_name",
    },
    {
        "id": "T2_05",
        "question": "What is the incident count per property?",
        "category": "group_by",
        "checks": [has(r"\bCOUNT\s*\("), has(r"\bGROUP\s+BY\b"), has(r"property_name")],
        "notes": "GROUP BY property_name",
    },

    # ── TIER 3: Date filtering ────────────────────────────────────────────────
    {
        "id": "T3_01",
        "question": "How many incidents in the last 7 days?",
        "category": "date_filter",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_add\s*\(\s*'day'\s*,\s*-7"),
            has_none(r"\bcreated_date\s*[><=]", r"\bincident_time\s*[><=]"),
        ],
        "notes": "Must use date_parse(snapshotdate), date_add('day', -7, ...). Never compare created_date or incident_time in WHERE.",
    },
    {
        "id": "T3_02",
        "question": "Show incidents from the last 30 days",
        "category": "date_filter",
        "checks": [
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_add\s*\(\s*'day'\s*,\s*-30"),
            has_none(r"\bcreated_date\s*[><=]", r"\bincident_time\s*[><=]"),
        ],
        "notes": "date_parse + date_add('day', -30)",
    },
    {
        "id": "T3_03",
        "question": "How many incidents happened this year?",
        "category": "date_filter",
        "checks": [
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"(\byear\s*\(|date_part\s*\(\s*'year'|EXTRACT\s*\(\s*YEAR)"),
            has_none(r"\bcreated_date\s*[><=]"),
        ],
        "notes": "Use year() or date_part('year', ...) or EXTRACT(YEAR FROM ...) on date_parse(snapshotdate, ...)",
    },
    {
        "id": "T3_04",
        "question": "How many incidents occurred in 2025?",
        "category": "date_filter",
        "checks": [
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"\byear\s*\("),
            has(r"2025"),
            has_none(r"\bcreated_date\s*[><=]"),
        ],
        "notes": "year(date_parse(snapshotdate, ...)) = 2025",
    },
    {
        "id": "T3_05",
        "question": "Show monthly incident count for this year",
        "category": "date_filter",
        "checks": [
            has(r"\bGROUP\s+BY\b"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"\b(month|date_trunc)\b"),
        ],
        "notes": "GROUP BY month, date_parse(snapshotdate)",
    },

    # ── TIER 4: Specific values / property ────────────────────────────────────
    {
        "id": "T4_01",
        "question": "Show incidents at The Peninsula Hong Kong",
        "category": "property_filter",
        "checks": [has(r"property_name"), col_eq("property_name", "The Peninsula Hong Kong")],
        "notes": "Must filter property_name = 'The Peninsula Hong Kong'",
    },
    {
        "id": "T4_02",
        "question": "How many incidents at Peninsula London?",
        "category": "property_filter",
        "checks": [has(r"property_name"), has(r"Peninsula London")],
        "notes": "Normalise Peninsula London → The Peninsula London",
    },
    {
        "id": "T4_03",
        "question": "Show all room condition incidents",
        "category": "property_filter",
        "checks": [has(r"category_name"), has(r"Room Condition", re.IGNORECASE)],
        "notes": "category_name = 'Room Condition'",
    },
    {
        "id": "T4_04",
        "question": "Show incidents from the engineering department",
        "category": "property_filter",
        "checks": [has(r"department_name"), has(r"Engineering", re.IGNORECASE)],
        "notes": "department_name = 'Engineering' (or LIKE %Engineering%)",
    },
    {
        "id": "T4_05",
        "question": "How many incidents involved VIP guests?",
        "category": "property_filter",
        "checks": [has(r"\bvip\b"), has_none(r"vip\s*IS\s*NULL", r"vip\s*=\s*''")],
        "notes": "Query on vip column — vip IS NOT NULL or vip != ''",
    },

    # ── TIER 5: Aggregation / cost ────────────────────────────────────────────
    {
        "id": "T5_01",
        "question": "What is the total actual cost of all incidents?",
        "category": "aggregation",
        "checks": [has(r"\bSUM\s*\("), has(r"actual_cost")],
        "notes": "SUM(actual_cost)",
    },
    {
        "id": "T5_02",
        "question": "What is the average actual cost per incident?",
        "category": "aggregation",
        "checks": [has(r"\bAVG\s*\("), has(r"actual_cost")],
        "notes": "AVG(actual_cost)",
    },
    {
        "id": "T5_03",
        "question": "What is the maximum potential cost across all incidents?",
        "category": "aggregation",
        "checks": [has(r"\bMAX\s*\("), has(r"potential_cost")],
        "notes": "MAX(potential_cost)",
    },
    {
        "id": "T5_04",
        "question": "Which department has the highest number of incidents?",
        "category": "aggregation",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bGROUP\s+BY\b"),
            has(r"department_name"),
            has(r"\bORDER\s+BY\b"),
            has(r"\bDESC\b"),
        ],
        "notes": "GROUP BY department_name ORDER BY count DESC LIMIT",
    },
    {
        "id": "T5_05",
        "question": "What are the top 5 categories by incident count?",
        "category": "aggregation",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bGROUP\s+BY\b"),
            has(r"category_name"),
            has(r"\bORDER\s+BY\b"),
            has(r"\bLIMIT\s+5\b"),
        ],
        "notes": "GROUP BY category_name ORDER BY count DESC LIMIT 5",
    },

    # ── TIER 6: Multi-condition ───────────────────────────────────────────────
    {
        "id": "T6_01",
        "question": "Show high severity pending incidents",
        "category": "multi_condition",
        "checks": [
            col_eq("severity_name", "high"),
            col_eq("status_name", "pending"),
        ],
        "notes": "Both conditions required",
    },
    {
        "id": "T6_02",
        "question": "How many critical incidents are still open?",
        "category": "multi_condition",
        "checks": [
            has(r"\bCOUNT\s*\("),
            col_eq("severity_name", "critical"),
            has(r"status_name"),
            has(r"pending"),
        ],
        "notes": "critical + pending (open = pending)",
    },
    {
        "id": "T6_03",
        "question": "Show completed high severity incidents from housekeeping",
        "category": "multi_condition",
        "checks": [
            col_eq("status_name", "completed"),
            col_eq("severity_name", "high"),
            has(r"(department_name|category_name)"),
            has(r"[Hh]ousekeeping"),
        ],
        "notes": "Three conditions: completed + high + housekeeping dept",
    },
    {
        "id": "T6_04",
        "question": "How many incidents involve angry guests?",
        "category": "multi_condition",
        "checks": [has(r"\bCOUNT\s*\("), has(r"temperament_text"), has(r"[Aa]ngry")],
        "notes": "temperament_text = 'Angry'",
    },
    {
        "id": "T6_05",
        "question": "Show low severity completed incidents in the last 14 days",
        "category": "multi_condition",
        "checks": [
            col_eq("severity_name", "low"),
            col_eq("status_name", "completed"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"date_add\s*\(\s*'day'\s*,\s*-14|INTERVAL\s*'14"),
        ],
        "notes": "Three conditions: low + completed + 14-day date filter",
    },

    # ── TIER 7: Recent / latest ───────────────────────────────────────────────
    {
        "id": "T7_01",
        "question": "Show me the 10 most recent incidents",
        "category": "recent",
        "checks": [
            has(r"\bORDER\s+BY\b"),
            has(r"created_date|incident_time"),
            has(r"\bDESC\b"),
            has(r"\bLIMIT\s+10\b"),
            has_none(r"date_parse\s*\(\s*snapshotdate.*[><=]"),
        ],
        "notes": "ORDER BY created_date DESC LIMIT 10, NO date filter",
    },
    {
        "id": "T7_02",
        "question": "What were the latest 5 high severity incidents?",
        "category": "recent",
        "checks": [
            has(r"\bORDER\s+BY\b"),
            has(r"\bDESC\b"),
            has(r"\bLIMIT\s+5\b"),
            col_eq("severity_name", "high"),
            has_none(r"date_parse\s*\(\s*snapshotdate.*[><=]"),
        ],
        "notes": "ORDER BY DESC LIMIT 5 + severity filter, NO date filter",
    },
    {
        "id": "T7_03",
        "question": "Show the most recent completed incident",
        "category": "recent",
        "checks": [
            has(r"\bORDER\s+BY\b"),
            has(r"\bDESC\b"),
            has(r"\bLIMIT\s+1\b"),
            col_eq("status_name", "completed"),
        ],
        "notes": "ORDER BY DESC LIMIT 1 + completed filter",
    },

    # ── TIER 8: Trend / time series ───────────────────────────────────────────
    {
        "id": "T8_01",
        "question": "Show the number of incidents per month",
        "category": "trend",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bGROUP\s+BY\b"),
            has(r"(date_trunc\s*\(\s*'month'|month\s*\()"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
        ],
        "notes": "GROUP BY month using date_trunc or month() on date_parse(snapshotdate)",
    },
    {
        "id": "T8_02",
        "question": "Show weekly incident trend for the last 4 weeks",
        "category": "trend",
        "checks": [
            has(r"\bGROUP\s+BY\b"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            has(r"(date_trunc\s*\(\s*'week'|week\s*\()"),
            has(r"date_add\s*\(\s*'(day|week)'"),
        ],
        "notes": "GROUP BY week + 4-week date filter",
    },
    {
        "id": "T8_03",
        "question": "How many incidents per day in the last 7 days?",
        "category": "trend",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bGROUP\s+BY\b"),
            has(r"(\w+\.)?snapshotdate"),
            has(r"date_add\s*\(\s*'day'\s*,\s*-7"),
        ],
        "notes": "GROUP BY snapshotdate + 7-day filter",
    },
    {
        "id": "T8_04",
        "question": "What is the monthly trend of high severity incidents?",
        "category": "trend",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bGROUP\s+BY\b"),
            has(r"date_parse\s*\(\s*(\w+\.)?snapshotdate"),
            col_eq("severity_name", "high"),
        ],
        "notes": "GROUP BY month + severity_name = 'high' filter",
    },
    {
        "id": "T8_05",
        "question": "Show incident counts by property for each month",
        "category": "trend",
        "checks": [
            has(r"\bCOUNT\s*\("),
            has(r"\bGROUP\s+BY\b"),
            has(r"property"),
            has(r"(date_trunc|month\s*\()"),
        ],
        "notes": "GROUP BY property AND month",
    },
]

# ──────────────────────────────────────────────────────────────────────────────
# Runner
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Result:
    id: str
    question: str
    category: str
    notes: str
    sql: str = ""
    score: str = "FAIL"          # PASS / PARTIAL / FAIL
    passed_checks: int = 0
    total_checks: int = 0
    error: str = ""
    latency_ms: int = 0


def call_api(question: str, max_retries: int = 5) -> dict:
    payload = {
        "text": question,
        "context": {"property_uuid": PROPERTY_UUID, "language": "en"},
        "sql": {"dialect": "redshift", "tables": []},
        "execution": {"dry_run": True, "max_rows": 100},
        "model": {"max_tokens": 256},
        "trace": {"source": "eval"},
    }
    for attempt in range(max_retries):
        resp = requests.post(f"{API_URL}/nlq/execute", json=payload, timeout=120)
        if resp.status_code == 429:
            retry_after = float(resp.headers.get("Retry-After", 1))
            time.sleep(retry_after + 0.1)
            continue
        return resp.json()
    return resp.json()


def evaluate(sql: str, checks: list) -> tuple[int, int]:
    passed = sum(1 for c in checks if c(sql))
    return passed, len(checks)


def run_corpus(questions=None, verbose=True) -> list[Result]:
    corpus = questions or CORPUS
    results = []

    print(f"\n{'='*70}")
    print(f"  NL-to-SQL Evaluation  ({len(corpus)} questions)")
    print(f"{'='*70}\n")

    for item in corpus:
        if verbose:
            print(f"[{item['id']}] {item['question'][:60]}", end="  ", flush=True)

        r = Result(
            id=item["id"],
            question=item["question"],
            category=item["category"],
            notes=item["notes"],
            total_checks=len(item["checks"]),
        )

        try:
            t0 = time.time()
            data = call_api(item["question"])
            r.latency_ms = int((time.time() - t0) * 1000)

            if not data.get("success"):
                r.error = data.get("error", data.get("detail", "unknown"))
                r.score = "FAIL"
            else:
                r.sql = data["sql"]["query"]
                r.passed_checks, r.total_checks = evaluate(r.sql, item["checks"])
                if r.passed_checks == r.total_checks:
                    r.score = "PASS"
                elif r.passed_checks >= r.total_checks // 2 + 1:
                    r.score = "PARTIAL"
                else:
                    r.score = "FAIL"
        except Exception as e:
            r.error = str(e)
            r.score = "FAIL"

        results.append(r)

        if verbose:
            icon = {"PASS": "✓", "PARTIAL": "~", "FAIL": "✗"}[r.score]
            print(f"{icon} ({r.passed_checks}/{r.total_checks})  {r.latency_ms}ms")
            if r.score != "PASS" and r.sql:
                print(f"       SQL: {r.sql[:120]}")
            if r.error:
                print(f"       ERR: {r.error[:100]}")

    return results


def print_summary(results: list[Result]):
    by_cat: dict[str, list] = {}
    for r in results:
        by_cat.setdefault(r.category, []).append(r)

    passed = sum(1 for r in results if r.score == "PASS")
    partial = sum(1 for r in results if r.score == "PARTIAL")
    failed = sum(1 for r in results if r.score == "FAIL")
    total = len(results)

    print(f"\n{'='*70}")
    print(f"  Summary: {passed}/{total} PASS  {partial} PARTIAL  {failed} FAIL")
    print(f"  Score: {(passed + partial*0.5) / total * 100:.0f}%")
    print(f"{'='*70}")

    print("\nBy category:")
    for cat, items in sorted(by_cat.items()):
        p = sum(1 for r in items if r.score == "PASS")
        pa = sum(1 for r in items if r.score == "PARTIAL")
        f = sum(1 for r in items if r.score == "FAIL")
        print(f"  {cat:<20} {p}/{len(items)} pass  {pa} partial  {f} fail")

    fails = [r for r in results if r.score in ("FAIL", "PARTIAL")]
    if fails:
        print(f"\nFailed / Partial ({len(fails)}):")
        for r in fails:
            print(f"\n  [{r.id}] {r.question}")
            print(f"  Expected: {r.notes}")
            print(f"  Score:    {r.score} ({r.passed_checks}/{r.total_checks} checks)")
            if r.sql:
                print(f"  SQL:      {r.sql}")
            if r.error:
                print(f"  Error:    {r.error}")


if __name__ == "__main__":
    results = run_corpus()
    print_summary(results)
