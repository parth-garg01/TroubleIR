"""Benchmark warm and cold path latencies."""
import sys
import os
import time
import json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dotenv import load_dotenv
load_dotenv()

from troubleir.pipeline.mapping import load_catalog
from troubleir.pipeline.siis import load_siis
from troubleir.pipeline.cache import load_cache, store
from troubleir.pipeline.orchestrator import run_pipeline
from troubleir.pipeline.cache import lookup

WARM_QUERIES = [
    "battery drains too fast",
    "screen too bright at night",
    "battery draining after update",
    "display too bright in dark room",
    "my phone battery keeps dying",
]

COLD_QUERIES = [
    "Phone overheating while gaming",
    "Camera photos are blurry",
    "Apps keep crashing on my Galaxy",
]

N_WARM = 10
N_COLD = 3


def benchmark_cold():
    """Run cold path and measure latency. Expensive - runs LLM calls."""
    latencies = []
    for q in COLD_QUERIES[:N_COLD]:
        t0 = time.perf_counter()
        result = run_pipeline(q)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        latencies.append(elapsed_ms)
        print(f"  Cold [{q[:40]}]: {elapsed_ms}ms | cache={result.meta.get('cache_hit')}")
    return latencies


def benchmark_warm():
    """Run warm path (cache hits) and measure latency."""
    # First, seed the cache with one cold run
    print("  Seeding cache for warm benchmark...")
    run_pipeline("battery drains too fast")

    latencies = []
    for q in WARM_QUERIES:
        t0 = time.perf_counter()
        result = run_pipeline(q)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        latencies.append(elapsed_ms)
        hit = result.meta.get("cache_hit", False)
        print(f"  Warm [{q[:40]}]: {elapsed_ms}ms | hit={hit}")
    return latencies


def percentile(data, p):
    return int(np.percentile(data, p)) if data else 0


def main():
    print("Initializing...")
    load_catalog()
    load_siis()
    load_cache()

    print("\n--- COLD PATH ---")
    cold_lat = benchmark_cold()

    print("\n--- WARM PATH ---")
    warm_lat = benchmark_warm()

    results = {
        "cold": {"p50": percentile(cold_lat, 50), "p95": percentile(cold_lat, 95), "n": len(cold_lat)},
        "warm": {"p50": percentile(warm_lat, 50), "p95": percentile(warm_lat, 95), "n": len(warm_lat)},
        "targets": {"warm_p95_ms": 300, "cold_p95_ms": 8000},
    }

    os.makedirs("experiments/results", exist_ok=True)
    with open("experiments/results/latency.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\n=== LATENCY RESULTS ===")
    print(f"Warm  P50={results['warm']['p50']}ms  P95={results['warm']['p95']}ms  (target P95 <= 300ms)")
    print(f"Cold  P50={results['cold']['p50']}ms  P95={results['cold']['p95']}ms  (target P95 <= 8000ms)")
    warm_ok = results['warm']['p95'] <= 300
    cold_ok = results['cold']['p95'] <= 8000
    print(f"Warm target: {'PASS' if warm_ok else 'FAIL'}")
    print(f"Cold target: {'PASS' if cold_ok else 'FAIL'}")

if __name__ == '__main__':
    main()
