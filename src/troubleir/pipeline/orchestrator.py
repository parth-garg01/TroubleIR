"""Main pipeline orchestrator: ties all components together."""
import time
import os
from typing import Optional

from ..schema import ContextDeeplinkResponse, TroubleshootResponse
from ..config import MODEL_NAME, RETRIEVAL_TOP_K
from .enrichment import enrich_query
from .extraction import extract_plan
from .mapping import load_catalog, retrieve_deeplinks, get_catalog
from .cache import lookup, store, get_cache_stats
from .siis import get_siis_text, load_siis
from ..compiler.grounding import check_grounding
from ..compiler.lint import lint_response


def _collect_dependencies(response: ContextDeeplinkResponse) -> list[str]:
    """Extract all deeplink URIs referenced in the plan for cache dependency tracking."""
    deps = []
    for goal in response.contexts:
        for action in goal.actions:
            for sg in action.stepGroups:
                if sg.actionableDeeplink:
                    deps.append(sg.actionableDeeplink.deeplink)
    return list(set(deps))


def run_pipeline(query: str, siis_response_override: Optional[str] = None) -> TroubleshootResponse:
    """
    Full TroubleIR pipeline:
    1. Enrich query (normalize + variations)
    2. Cache lookup (warm path - skip LLM)
    3. Retrieve SIIS evidence
    4. LLM extraction (cold path)
    5. Lint + validate
    6. Cache store
    7. Return response with meta
    """
    start_ts = time.perf_counter()
    cost_usd = 0.0

    # Step 1a: Fast cache probe on raw query — no Groq call, just embed + cosine.
    # Repeat or near-identical queries return here in ~20-50 ms.
    cached = lookup(query, query)
    if cached is not None:
        elapsed_ms = int((time.perf_counter() - start_ts) * 1000)
        return TroubleshootResponse(
            query=query,
            query_variations=[],
            response=cached,
            meta={
                "latency_ms": elapsed_ms,
                "cache_hit": True,
                "cache_path": "raw",
                "model": MODEL_NAME,
                "cost_usd": 0.0,
                "canonical": query,
                "diagnostics": [],
            },
        )

    # Step 1b: Enrich (only on cache miss — pays the Groq round-trip once)
    canonical, variations = enrich_query(query)
    cost_usd += 0.0001  # approx enrichment cost

    # Step 2: Cache lookup on canonical form (catches paraphrases of cached queries)
    cached = lookup(canonical, query)
    if cached is not None:
        elapsed_ms = int((time.perf_counter() - start_ts) * 1000)
        return TroubleshootResponse(
            query=query,
            query_variations=variations,
            response=cached,
            meta={
                "latency_ms": elapsed_ms,
                "cache_hit": True,
                "cache_path": "canonical",
                "model": MODEL_NAME,
                "cost_usd": 0.0,
                "canonical": canonical,
                "diagnostics": [],
            },
        )

    # Step 3: Get SIIS evidence
    if siis_response_override:
        siis_text = siis_response_override
    else:
        siis_text = get_siis_text(canonical) or get_siis_text(query) or ""

    # Step 4: LLM extraction (cold path)
    catalog = get_catalog()
    relevant_deeplinks = retrieve_deeplinks(canonical, top_k=RETRIEVAL_TOP_K)

    plan = None
    diagnostics = []

    if not siis_text:
        diagnostics.append("no_siis_context: No knowledge base article found for this query")
    else:
        plan = extract_plan(canonical, siis_text, catalog)
        cost_usd += 0.001  # approx haiku cost for extraction

    if plan is None or not plan.contexts:
        elapsed_ms = int((time.perf_counter() - start_ts) * 1000)
        return TroubleshootResponse(
            query=query,
            query_variations=variations,
            response=ContextDeeplinkResponse(contexts=[], fallback="no_match"),
            meta={
                "latency_ms": elapsed_ms,
                "cache_hit": False,
                "model": MODEL_NAME,
                "cost_usd": cost_usd,
                "canonical": canonical,
                "diagnostics": diagnostics,
            },
        )

    # Step 5: Grounding check
    all_diagnostics = list(diagnostics)
    if siis_text:
        for goal in plan.contexts:
            for action in goal.actions:
                result = check_grounding(action, siis_text)
                all_diagnostics.extend(result.get("diagnostics", []))

    # Step 6: Lint
    passed, lint_issues = lint_response(plan)
    all_diagnostics.extend(lint_issues)

    # Step 7: Cache store (only if passed lint)
    if passed:
        deps = _collect_dependencies(plan)
        store(canonical, plan, dependencies=deps)

    elapsed_ms = int((time.perf_counter() - start_ts) * 1000)
    return TroubleshootResponse(
        query=query,
        query_variations=variations,
        response=plan,
        meta={
            "latency_ms": elapsed_ms,
            "cache_hit": False,
            "model": os.environ.get("MODEL_NAME", "claude-haiku-4-5-20251001"),
            "cost_usd": cost_usd,
            "canonical": canonical,
            "lint_passed": passed,
            "diagnostics": all_diagnostics,
        },
    )
