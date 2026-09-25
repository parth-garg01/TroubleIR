"""Run evaluation suite against the TroubleIR pipeline."""
import sys
import os
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dotenv import load_dotenv
load_dotenv()

from troubleir.pipeline.mapping import load_catalog
from troubleir.pipeline.siis import load_siis
from troubleir.pipeline.cache import load_cache
from troubleir.pipeline.orchestrator import run_pipeline
from troubleir.compiler.lint import lint_response

EVAL_QUERIES = [
    ("Battery draining too fast after update", "battery"),
    ("Screen is too bright at night", "display"),
    ("Screen is too dim and hard to read", "display"),
    ("Phone swipe gestures going wrong direction", "display"),
    ("Screen flickers and battery drains", "battery+display"),
    ("My washing machine is making noise", "out_of_scope"),
]

def main():
    print("Initializing indexes...")
    load_catalog()
    load_siis()
    load_cache()

    results = []
    for query, domain in EVAL_QUERIES:
        print(f"\nEval: [{domain}] {query}")
        t0 = time.perf_counter()
        result = run_pipeline(query)
        elapsed = int((time.perf_counter() - t0) * 1000)

        response = result.response
        is_no_match = response.fallback == "no_match" or not response.contexts
        schema_valid, violations = lint_response(response) if not is_no_match else (True, [])

        entry = {
            "query": query,
            "domain": domain,
            "latency_ms": elapsed,
            "cache_hit": result.meta.get("cache_hit", False),
            "no_match": is_no_match,
            "schema_valid": schema_valid,
            "num_goals": len(response.contexts),
            "num_actions": sum(len(g.actions) for g in response.contexts),
            "violations": violations,
        }
        results.append(entry)

        status = "NO_MATCH" if is_no_match else ("PASS" if schema_valid else "FAIL")
        print(f"  Status: {status} | {elapsed}ms | cache={result.meta.get('cache_hit')} | actions={entry['num_actions']}")
        for v in violations:
            print(f"    VIOLATION: {v}")

    os.makedirs("experiments/results", exist_ok=True)
    with open("experiments/results/eval_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\n=== SUMMARY ===")
    passed = sum(1 for r in results if r["schema_valid"] and not r["no_match"])
    no_match = sum(1 for r in results if r["no_match"])
    latencies = [r["latency_ms"] for r in results]
    print(f"Passed: {passed}/{len(results)}")
    print(f"No-match (abstentions): {no_match}")
    print(f"Avg latency: {sum(latencies)//len(latencies)}ms")
    print(f"Results saved to experiments/results/eval_results.json")

if __name__ == '__main__':
    main()
