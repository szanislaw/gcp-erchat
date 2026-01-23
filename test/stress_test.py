#!/usr/bin/env python3
"""
Comprehensive Stress Test Suite for NLQ → Athena SQL API
=========================================================
Tests: Concurrency, Load, Edge Cases, Error Handling, Performance, Memory

Run with: python stress_test.py [--server-url URL] [--concurrent N] [--duration SECONDS]
"""

import asyncio
import aiohttp
import time
import statistics
import traceback
import sys
import argparse
import json
import random
import gc
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import resource
import psutil
import os

# Default configuration
DEFAULT_SERVER_URL = "http://localhost:8000"
DEFAULT_CONCURRENT_USERS = 10
DEFAULT_DURATION_SECONDS = 60
DEFAULT_RAMP_UP_SECONDS = 5


@dataclass
class TestResult:
    """Holds individual test result data"""
    test_name: str
    success: bool
    latency_ms: float
    status_code: int
    error_message: str = ""
    response_data: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class TestMetrics:
    """Aggregated metrics for a test category"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    latencies: List[float] = field(default_factory=list)
    errors: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    status_codes: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def avg_latency(self) -> float:
        if not self.latencies:
            return 0.0
        return statistics.mean(self.latencies)
    
    @property
    def p50_latency(self) -> float:
        if not self.latencies:
            return 0.0
        return statistics.median(self.latencies)
    
    @property
    def p95_latency(self) -> float:
        if len(self.latencies) < 2:
            return self.avg_latency
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[idx]
    
    @property
    def p99_latency(self) -> float:
        if len(self.latencies) < 2:
            return self.avg_latency
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.99)
        return sorted_latencies[idx]
    
    @property
    def max_latency(self) -> float:
        if not self.latencies:
            return 0.0
        return max(self.latencies)


# ============================================================================
# TEST DATA
# ============================================================================

VALID_REQUEST_TEMPLATE = {
    "text": "Show me all incidents",
    "context": {
        "account_uuid": "00000000-0000-0000-0000-000000000000",  # Super user
        "property_uuid": "00000000-0000-0000-0000-000000000000",  # Super user
        "language": "en"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": True, "max_rows": 10, "timeout_ms": 5000},
    "model": {"name": "Ellbendls/Qwen-2.5-3b-Text_to_SQL", "temperature": 0.0, "max_tokens": 256},
    "trace": {"request_id": None, "source": "stress-test"}
}

TEST_QUESTIONS = [
    "Show me all incidents",
    "Get the last 10 incidents",
    "What incidents happened at The Peninsula Manila?",
    "Show me incidents from today",
    "What are the most recent incidents?",
    "Show incidents created in the last 7 days",
    "Show all pending incidents",
    "What incidents are related to Room Cleanliness?",
    "Show me high severity incidents that are still pending",
    "How many incidents are there?",
    "Count incidents by department",
    "What is the total potential cost of all incidents?",
    "How many incidents does each property have?",
    "Show me the top 5 incidents by actual cost",
    "Which department has the most incidents?",
    "List incidents ordered by severity",
    "Show recent Housekeeping incidents with medium severity",
    "What is the average actual cost for completed incidents by category?",
    "Give me a list of problems reported at room 1018",
    "How much money was spent on compensations?",
]

EDGE_CASE_QUERIES = [
    "",  # Empty query
    "   ",  # Whitespace only
    "a",  # Single character
    "SELECT * FROM users; DROP TABLE incidents;--",  # SQL injection attempt
    "'; DELETE FROM incidents; --",  # SQL injection
    "<script>alert('xss')</script>",  # XSS attempt
    "A" * 10000,  # Very long query
    "🔥 Show incidents 🚀 with emojis 💻",  # Unicode/emoji
    "查询所有事件",  # Chinese characters
    "SELECT\n*\nFROM\nincidents",  # Multi-line
    "show incidents WHERE 1=1 OR 'a'='a'",  # SQL injection variant
    "null",  # Null string
    "undefined",  # Undefined string
    "true",  # Boolean string
    "123456789",  # Number only
    "SELECT * FROM system_tables",  # Unauthorized table attempt
    "DROP DATABASE peninsula",  # DDL attempt
    "UPDATE incidents SET status='deleted'",  # DML attempt
]

MALFORMED_REQUESTS = [
    {},  # Empty request
    {"text": None},  # Null text
    {"text": 123},  # Wrong type
    {"text": "test", "context": None},  # Null context
    {"text": "test", "context": {}},  # Empty context
    {"text": "test", "context": {"account_uuid": "invalid"}},  # Invalid UUID
    {"text": "test", "context": {"account_uuid": "acc-00000000-0000-0000-0000-000000000000"}},  # Missing property_uuid
]


# ============================================================================
# ASYNC HTTP CLIENT
# ============================================================================

async def make_request(
    session: aiohttp.ClientSession,
    url: str,
    payload: Dict,
    timeout: float = 30.0
) -> Tuple[int, Dict, float]:
    """Make async HTTP request and return (status_code, response_dict, latency_ms)"""
    start = time.time()
    try:
        async with session.post(
            url,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as response:
            latency_ms = (time.time() - start) * 1000
            try:
                data = await response.json()
            except:
                data = {"error": await response.text()}
            return response.status, data, latency_ms
    except asyncio.TimeoutError:
        latency_ms = (time.time() - start) * 1000
        return 408, {"error": "Request timeout"}, latency_ms
    except aiohttp.ClientError as e:
        latency_ms = (time.time() - start) * 1000
        return 500, {"error": str(e)}, latency_ms
    except Exception as e:
        latency_ms = (time.time() - start) * 1000
        return 500, {"error": f"Unexpected error: {str(e)}"}, latency_ms


# ============================================================================
# TEST CATEGORIES
# ============================================================================

class StressTestSuite:
    """Comprehensive stress test suite"""
    
    def __init__(self, server_url: str, verbose: bool = True):
        self.server_url = server_url.rstrip("/")
        self.execute_url = f"{self.server_url}/nlq/execute"
        self.suggestions_url = f"{self.server_url}/nlq/suggestions"
        self.schema_url = f"{self.server_url}/nlq/schema"
        self.logs_url = f"{self.server_url}/logs"
        self.verbose = verbose
        self.results: Dict[str, TestMetrics] = defaultdict(TestMetrics)
        self.all_results: List[TestResult] = []
        
    def log(self, msg: str):
        if self.verbose:
            print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)
    
    async def check_server_health(self) -> bool:
        """Check if server is running"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.server_url,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status in [200, 404]
        except:
            return False

    # --------------------------------------------------------------------------
    # FUNCTIONAL TESTS
    # --------------------------------------------------------------------------
    
    async def test_basic_functionality(self) -> TestMetrics:
        """Test basic NLQ functionality with valid requests"""
        category = "basic_functionality"
        self.log(f"Running {category} tests...")
        
        async with aiohttp.ClientSession() as session:
            for i, question in enumerate(TEST_QUESTIONS[:5]):  # Test first 5
                payload = VALID_REQUEST_TEMPLATE.copy()
                payload["text"] = question
                payload["trace"] = {"request_id": f"func-test-{i}", "source": "stress-test"}
                
                status, data, latency = await make_request(session, self.execute_url, payload)
                
                success = status == 200 and data.get("success", False)
                result = TestResult(
                    test_name=f"basic_{i}",
                    success=success,
                    latency_ms=latency,
                    status_code=status,
                    error_message="" if success else str(data.get("error", data.get("detail", "Unknown"))),
                    response_data=data
                )
                
                self.all_results.append(result)
                self.results[category].total_requests += 1
                self.results[category].latencies.append(latency)
                self.results[category].status_codes[status] += 1
                
                if success:
                    self.results[category].successful_requests += 1
                    self.log(f"  ✓ Q{i+1}: {question[:40]}... ({latency:.0f}ms)")
                else:
                    self.results[category].failed_requests += 1
                    self.results[category].errors[result.error_message[:50]] += 1
                    self.log(f"  ✗ Q{i+1}: {result.error_message[:50]}")
        
        return self.results[category]

    async def test_edge_cases(self) -> TestMetrics:
        """Test edge cases and boundary conditions"""
        category = "edge_cases"
        self.log(f"Running {category} tests...")
        
        async with aiohttp.ClientSession() as session:
            for i, query in enumerate(EDGE_CASE_QUERIES):
                payload = VALID_REQUEST_TEMPLATE.copy()
                payload["text"] = query
                payload["trace"] = {"request_id": f"edge-test-{i}", "source": "stress-test"}
                
                status, data, latency = await make_request(session, self.execute_url, payload)
                
                # Edge cases should fail gracefully (4xx) not crash (5xx)
                success = status < 500
                result = TestResult(
                    test_name=f"edge_{i}",
                    success=success,
                    latency_ms=latency,
                    status_code=status,
                    error_message="" if status < 400 else str(data.get("detail", data.get("error", ""))),
                    response_data=data
                )
                
                self.all_results.append(result)
                self.results[category].total_requests += 1
                self.results[category].latencies.append(latency)
                self.results[category].status_codes[status] += 1
                
                if success:
                    self.results[category].successful_requests += 1
                else:
                    self.results[category].failed_requests += 1
                    self.results[category].errors[f"Status {status}"] += 1
                
                query_preview = repr(query[:30]) if query else "empty"
                self.log(f"  {'✓' if success else '✗'} Edge case {i+1}: {query_preview} → {status}")
        
        return self.results[category]

    async def test_malformed_requests(self) -> TestMetrics:
        """Test malformed/invalid request handling"""
        category = "malformed_requests"
        self.log(f"Running {category} tests...")
        
        async with aiohttp.ClientSession() as session:
            for i, payload in enumerate(MALFORMED_REQUESTS):
                status, data, latency = await make_request(session, self.execute_url, payload)
                
                # Should return 4xx (validation error), not 5xx (crash)
                success = 400 <= status < 500
                result = TestResult(
                    test_name=f"malformed_{i}",
                    success=success,
                    latency_ms=latency,
                    status_code=status,
                    error_message=str(data.get("detail", data.get("error", "")))[:100],
                    response_data=data
                )
                
                self.all_results.append(result)
                self.results[category].total_requests += 1
                self.results[category].latencies.append(latency)
                self.results[category].status_codes[status] += 1
                
                if success:
                    self.results[category].successful_requests += 1
                    self.log(f"  ✓ Malformed {i+1}: Properly rejected with {status}")
                else:
                    self.results[category].failed_requests += 1
                    self.results[category].errors[f"Unexpected status {status}"] += 1
                    self.log(f"  ✗ Malformed {i+1}: Got {status} (expected 4xx)")
        
        return self.results[category]

    async def test_sql_injection(self) -> TestMetrics:
        """Test SQL injection prevention"""
        category = "sql_injection"
        self.log(f"Running {category} tests...")
        
        injection_payloads = [
            "'; DROP TABLE incidents; --",
            "1 OR 1=1",
            "1; DELETE FROM incidents WHERE 1=1; --",
            "UNION SELECT * FROM system_tables",
            "'; INSERT INTO incidents VALUES(1); --",
            "1' AND (SELECT COUNT(*) FROM incidents) > 0 --",
            "admin'--",
            "1 UNION ALL SELECT password FROM users",
        ]
        
        async with aiohttp.ClientSession() as session:
            for i, injection in enumerate(injection_payloads):
                payload = VALID_REQUEST_TEMPLATE.copy()
                payload["text"] = f"Show incidents where id = {injection}"
                
                status, data, latency = await make_request(session, self.execute_url, payload)
                
                # Check that injection didn't succeed
                success = status in [200, 400, 403, 422]
                if status == 200 and data.get("success"):
                    # Check that dangerous operations weren't executed
                    sql = data.get("sql", {}).get("query", "").lower()
                    if any(kw in sql for kw in ["drop", "delete", "insert", "update", "union select"]):
                        success = False
                
                result = TestResult(
                    test_name=f"injection_{i}",
                    success=success,
                    latency_ms=latency,
                    status_code=status,
                    response_data=data
                )
                
                self.all_results.append(result)
                self.results[category].total_requests += 1
                self.results[category].latencies.append(latency)
                self.results[category].status_codes[status] += 1
                
                if success:
                    self.results[category].successful_requests += 1
                    self.log(f"  ✓ Injection {i+1}: Blocked/Safe")
                else:
                    self.results[category].failed_requests += 1
                    self.results[category].errors["Potential injection vulnerability"] += 1
                    self.log(f"  ✗ Injection {i+1}: POTENTIAL VULNERABILITY")
        
        return self.results[category]

    # --------------------------------------------------------------------------
    # LOAD TESTS
    # --------------------------------------------------------------------------
    
    async def test_concurrent_requests(self, num_concurrent: int = 10) -> TestMetrics:
        """Test concurrent request handling"""
        category = "concurrent_requests"
        self.log(f"Running {category} tests with {num_concurrent} concurrent requests...")
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(num_concurrent):
                payload = VALID_REQUEST_TEMPLATE.copy()
                payload["text"] = random.choice(TEST_QUESTIONS)
                payload["trace"] = {"request_id": f"concurrent-{i}", "source": "stress-test"}
                tasks.append(make_request(session, self.execute_url, payload))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, res in enumerate(results):
                if isinstance(res, Exception):
                    status, data, latency = 500, {"error": str(res)}, 0
                else:
                    status, data, latency = res
                
                success = status == 200 and data.get("success", False)
                
                self.results[category].total_requests += 1
                self.results[category].latencies.append(latency)
                self.results[category].status_codes[status] += 1
                
                if success:
                    self.results[category].successful_requests += 1
                else:
                    self.results[category].failed_requests += 1
                    error = str(data.get("error", data.get("detail", "Unknown")))[:50]
                    self.results[category].errors[error] += 1
        
        self.log(f"  Completed: {self.results[category].successful_requests}/{num_concurrent} successful")
        return self.results[category]

    async def test_sustained_load(
        self, 
        requests_per_second: float = 2, 
        duration_seconds: int = 30
    ) -> TestMetrics:
        """Test sustained load over time"""
        category = "sustained_load"
        self.log(f"Running {category} tests: {requests_per_second} req/s for {duration_seconds}s...")
        
        interval = 1.0 / requests_per_second
        end_time = time.time() + duration_seconds
        request_count = 0
        
        async with aiohttp.ClientSession() as session:
            while time.time() < end_time:
                start_time = time.time()
                
                payload = VALID_REQUEST_TEMPLATE.copy()
                payload["text"] = random.choice(TEST_QUESTIONS)
                payload["trace"] = {"request_id": f"sustained-{request_count}", "source": "stress-test"}
                
                status, data, latency = await make_request(session, self.execute_url, payload, timeout=10)
                
                success = status == 200 and data.get("success", False)
                
                self.results[category].total_requests += 1
                self.results[category].latencies.append(latency)
                self.results[category].status_codes[status] += 1
                
                if success:
                    self.results[category].successful_requests += 1
                else:
                    self.results[category].failed_requests += 1
                    error = str(data.get("error", data.get("detail", "Unknown")))[:50]
                    self.results[category].errors[error] += 1
                
                request_count += 1
                
                # Rate limiting
                elapsed = time.time() - start_time
                sleep_time = max(0, interval - elapsed)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
        
        self.log(f"  Completed {request_count} requests: {self.results[category].successful_requests} successful")
        return self.results[category]

    async def test_burst_traffic(self, burst_size: int = 50) -> TestMetrics:
        """Test handling of sudden traffic burst"""
        category = "burst_traffic"
        self.log(f"Running {category} tests with burst of {burst_size} requests...")
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(burst_size):
                payload = VALID_REQUEST_TEMPLATE.copy()
                payload["text"] = random.choice(TEST_QUESTIONS)
                payload["trace"] = {"request_id": f"burst-{i}", "source": "stress-test"}
                tasks.append(make_request(session, self.execute_url, payload, timeout=60))
            
            start = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start
            
            for res in results:
                if isinstance(res, Exception):
                    status, data, latency = 500, {"error": str(res)}, 0
                else:
                    status, data, latency = res
                
                success = status == 200 and data.get("success", False)
                
                self.results[category].total_requests += 1
                self.results[category].latencies.append(latency)
                self.results[category].status_codes[status] += 1
                
                if success:
                    self.results[category].successful_requests += 1
                else:
                    self.results[category].failed_requests += 1
        
        self.log(f"  Burst of {burst_size} requests completed in {total_time:.1f}s")
        self.log(f"  Throughput: {burst_size/total_time:.2f} req/s")
        return self.results[category]

    # --------------------------------------------------------------------------
    # OTHER ENDPOINTS
    # --------------------------------------------------------------------------
    
    async def test_other_endpoints(self) -> TestMetrics:
        """Test suggestions, schema, and logs endpoints"""
        category = "other_endpoints"
        self.log(f"Running {category} tests...")
        
        async with aiohttp.ClientSession() as session:
            # Test suggestions endpoint
            async with session.get(self.suggestions_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                status = resp.status
                self.results[category].total_requests += 1
                self.results[category].status_codes[status] += 1
                if status == 200:
                    self.results[category].successful_requests += 1
                    self.log(f"  ✓ GET /nlq/suggestions: {status}")
                else:
                    self.results[category].failed_requests += 1
                    self.log(f"  ✗ GET /nlq/suggestions: {status}")
            
            # Test schema endpoint
            async with session.get(self.schema_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                status = resp.status
                self.results[category].total_requests += 1
                self.results[category].status_codes[status] += 1
                if status == 200:
                    self.results[category].successful_requests += 1
                    self.log(f"  ✓ GET /nlq/schema: {status}")
                else:
                    self.results[category].failed_requests += 1
                    self.log(f"  ✗ GET /nlq/schema: {status}")
            
            # Test logs endpoint
            async with session.get(self.logs_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                status = resp.status
                self.results[category].total_requests += 1
                self.results[category].status_codes[status] += 1
                if status == 200:
                    self.results[category].successful_requests += 1
                    self.log(f"  ✓ GET /logs: {status}")
                else:
                    self.results[category].failed_requests += 1
                    self.log(f"  ✗ GET /logs: {status}")
        
        return self.results[category]

    # --------------------------------------------------------------------------
    # MEMORY & RESOURCE TESTS
    # --------------------------------------------------------------------------
    
    def test_memory_usage(self) -> Dict[str, Any]:
        """Check current memory usage"""
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        
        return {
            "rss_mb": mem_info.rss / (1024 * 1024),
            "vms_mb": mem_info.vms / (1024 * 1024),
            "percent": process.memory_percent()
        }

    # --------------------------------------------------------------------------
    # REPORTING
    # --------------------------------------------------------------------------
    
    def generate_report(self) -> str:
        """Generate comprehensive test report"""
        lines = [
            "",
            "=" * 80,
            "STRESS TEST RESULTS SUMMARY",
            "=" * 80,
            f"Server: {self.server_url}",
            f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]
        
        total_requests = 0
        total_successful = 0
        all_latencies = []
        
        for category, metrics in self.results.items():
            total_requests += metrics.total_requests
            total_successful += metrics.successful_requests
            all_latencies.extend(metrics.latencies)
            
            lines.append("-" * 80)
            lines.append(f"Category: {category.upper()}")
            lines.append("-" * 80)
            lines.append(f"  Total Requests:    {metrics.total_requests}")
            lines.append(f"  Successful:        {metrics.successful_requests}")
            lines.append(f"  Failed:            {metrics.failed_requests}")
            lines.append(f"  Success Rate:      {metrics.success_rate:.1f}%")
            
            if metrics.latencies:
                lines.append(f"  Avg Latency:       {metrics.avg_latency:.0f}ms")
                lines.append(f"  P50 Latency:       {metrics.p50_latency:.0f}ms")
                lines.append(f"  P95 Latency:       {metrics.p95_latency:.0f}ms")
                lines.append(f"  P99 Latency:       {metrics.p99_latency:.0f}ms")
                lines.append(f"  Max Latency:       {metrics.max_latency:.0f}ms")
            
            if metrics.status_codes:
                lines.append(f"  Status Codes:      {dict(metrics.status_codes)}")
            
            if metrics.errors:
                lines.append(f"  Top Errors:")
                for error, count in sorted(metrics.errors.items(), key=lambda x: -x[1])[:5]:
                    lines.append(f"    - {error}: {count}")
            
            lines.append("")
        
        # Overall summary
        lines.append("=" * 80)
        lines.append("OVERALL SUMMARY")
        lines.append("=" * 80)
        lines.append(f"  Total Requests:    {total_requests}")
        lines.append(f"  Total Successful:  {total_successful}")
        lines.append(f"  Overall Success:   {(total_successful/total_requests*100) if total_requests else 0:.1f}%")
        
        if all_latencies:
            lines.append(f"  Overall Avg Lat:   {statistics.mean(all_latencies):.0f}ms")
            sorted_lat = sorted(all_latencies)
            lines.append(f"  Overall P95 Lat:   {sorted_lat[int(len(sorted_lat)*0.95)]:.0f}ms")
        
        mem = self.test_memory_usage()
        lines.append(f"  Memory Usage:      {mem['rss_mb']:.1f}MB ({mem['percent']:.1f}%)")
        
        lines.append("")
        lines.append("=" * 80)
        
        return "\n".join(lines)


# ============================================================================
# MAIN
# ============================================================================

async def run_all_tests(server_url: str, concurrent: int = 10, duration: int = 30):
    """Run all stress tests"""
    suite = StressTestSuite(server_url, verbose=True)
    
    print("\n" + "=" * 80)
    print("NLQ → ATHENA SQL API STRESS TEST")
    print("=" * 80)
    print(f"Server URL: {server_url}")
    print(f"Concurrent Users: {concurrent}")
    print(f"Load Test Duration: {duration}s")
    print("=" * 80 + "\n")
    
    # Check server health
    print("[HEALTH CHECK]")
    if not await suite.check_server_health():
        print("  ✗ Server is not responding. Please start the server first.")
        print(f"    Try: uvicorn app.main:app --host 0.0.0.0 --port 8000")
        return None
    print("  ✓ Server is healthy\n")
    
    # Run test categories
    print("\n[FUNCTIONAL TESTS]")
    print("-" * 40)
    await suite.test_basic_functionality()
    await suite.test_edge_cases()
    await suite.test_malformed_requests()
    await suite.test_sql_injection()
    
    print("\n[LOAD TESTS]")
    print("-" * 40)
    await suite.test_concurrent_requests(concurrent)
    await suite.test_burst_traffic(concurrent * 2)
    await suite.test_sustained_load(requests_per_second=1, duration_seconds=min(duration, 30))
    
    print("\n[OTHER ENDPOINTS]")
    print("-" * 40)
    await suite.test_other_endpoints()
    
    # Generate and print report
    report = suite.generate_report()
    print(report)
    
    # Save report to file
    report_file = f"stress_test_report_{int(time.time())}.txt"
    with open(report_file, "w") as f:
        f.write(report)
    print(f"\nReport saved to: {report_file}")
    
    return suite


def main():
    parser = argparse.ArgumentParser(description="Stress test the NLQ API")
    parser.add_argument(
        "--server-url", 
        default=DEFAULT_SERVER_URL,
        help=f"Server URL (default: {DEFAULT_SERVER_URL})"
    )
    parser.add_argument(
        "--concurrent", 
        type=int, 
        default=DEFAULT_CONCURRENT_USERS,
        help=f"Number of concurrent users (default: {DEFAULT_CONCURRENT_USERS})"
    )
    parser.add_argument(
        "--duration", 
        type=int, 
        default=DEFAULT_DURATION_SECONDS,
        help=f"Duration for sustained load test in seconds (default: {DEFAULT_DURATION_SECONDS})"
    )
    
    args = parser.parse_args()
    
    try:
        asyncio.run(run_all_tests(
            server_url=args.server_url,
            concurrent=args.concurrent,
            duration=args.duration
        ))
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)


if __name__ == "__main__":
    main()
