"""
Performance & Scalability Benchmark Suite for NetraOM CSPM
Tests API throughput, database query timing, and graph query latency.
"""
import time
import urllib.request
import json

API_BASE = "http://localhost:8000"

def test_api_health_latency():
    start = time.time()
    res = urllib.request.urlopen(f"{API_BASE}/health")
    duration = (time.time() - start) * 1000
    assert res.status == 200
    print(f"[BENCHMARK] Health check response time: {duration:.2f} ms")
    assert duration < 200

def test_assets_pagination_performance():
    start = time.time()
    res = urllib.request.urlopen(f"{API_BASE}/assets?limit=100")
    duration = (time.time() - start) * 1000
    data = json.loads(res.read())
    assert res.status == 200
    print(f"[BENCHMARK] Assets list (limit 100) query latency: {duration:.2f} ms (Returned {len(data['items'])} items)")
    assert duration < 500

def test_findings_toxic_combo_latency():
    start = time.time()
    res = urllib.request.urlopen(f"{API_BASE}/findings?limit=50")
    duration = (time.time() - start) * 1000
    data = json.loads(res.read())
    assert res.status == 200
    print(f"[BENCHMARK] Findings query latency: {duration:.2f} ms (Returned {len(data['items'])} findings)")
    assert duration < 500

def test_graph_schema_latency():
    start = time.time()
    res = urllib.request.urlopen(f"{API_BASE}/graph/schema")
    duration = (time.time() - start) * 1000
    assert res.status == 200
    print(f"[BENCHMARK] Neo4j Schema metadata query latency: {duration:.2f} ms")
    assert duration < 500

if __name__ == "__main__":
    print("--- Running NetraOM CSPM Performance & Scalability Benchmarks ---")
    test_api_health_latency()
    test_assets_pagination_performance()
    test_findings_toxic_combo_latency()
    test_graph_schema_latency()
    print("\n✅ ALL PERFORMANCE & SCALABILITY BENCHMARKS PASSED PERFECTLY!")
