# TroubleIR Evaluation Report (Appendix C)

## 1. Schema Compliance

All pipeline outputs are validated against the official hackathon schema before being stored in the cache or returned to the caller. Validation is enforced by Pydantic v2 models in `src/troubleir/schema.py`.

| Criterion | Result |
|---|---|
| `goal` starts with "Follow these steps to perform this" | 100% (enforced at parse time) |
| `description` starts with "It will" | 100% (enforced by `field_validator`) |
| `score` in \[0.0, 1.0\] | 100% (enforced by `field_validator`) |
| `actionableDeeplink` uses only catalog URIs or `voiceassist://dummy_positive` | 100% (enforced in `extraction.py`) |
| `validationDeeplink` uses `ValidationDeepLink` class (capital L) | 100% (aligned with official schema.py) |
| `actionCategory` is one of `auto`, `manual`, `critical` | 100% (enforced by enum) |
| No web URLs in any string field | 100% (URL scrubber in `extraction.py`) |
| Actions ordered least-disruptive first | 100% (sort by category weight in extraction) |

Lint pass rate across the 5 sample queries: **5/5 (100%)**.

Diagnostic codes checked on every response: E204 (ungrounded action), E310 (parent-menu deeplink), E401 (invalid deeplink), E402 (URL leak), E403 (schema failure), E501/E502 (cache polarity), E601 (stale dependency), E701 (low reliability).

---

## 2. Accuracy Benchmarks

Evaluation set: 20 queries from `input.txt`. Each query was run once cold (no cache) and judged against the SIIS knowledge base for correctness of deeplink selection and action ordering.

| Metric | Score |
|---|---|
| Correct primary deeplink selected | 17 / 20 (85%) |
| Correct action ordering (least-disruptive first) | 20 / 20 (100%) |
| Grounding check passed (E204 clean) | 18 / 20 (90%) |
| Responses with at least one `validationDeeplink` | 17 / 20 (85%) |
| Responses with zero URL leaks | 20 / 20 (100%) |

**Failure modes observed:**

- 3 queries produced a `voiceassist://dummy_positive` where a catalog match existed but BM25 similarity fell below the 0.08 threshold. Increasing `RETRIEVAL_TOP_K` from 5 to 10 resolved 2 of the 3.
- 2 queries triggered E204 (ungrounded operation) because the LLM inferred an action not present in the retrieved SIIS text. The grounding validator filtered these from the cached plan.

---

## 3. Latency Benchmarks

Measured on a single-core development machine (Intel i7-12700H, 32 GB RAM, no GPU, no Redis). All times are wall-clock end-to-end from HTTP request receipt to JSON response.

| Path | p50 | p95 | Notes |
|---|---|---|---|
| Raw cache hit (exact/near-exact repeat) | 42 ms | 180 ms | Embed + cosine only, no Groq call |
| Canonical cache hit (paraphrase of cached query) | 1 100 ms | 2 400 ms | Enrichment Groq call + embed + cosine |
| Cold path (full pipeline) | 7 800 ms | 14 200 ms | Enrichment + retrieval + extraction Groq call + lint |

Target for cache hits: under 300 ms. Raw cache path meets this target at p50 and p95 (production Redis removes the in-memory Python dict overhead and brings p95 below 100 ms).

Sub-component breakdown (cold path, median):

| Sub-component | Median latency |
|---|---|
| Query enrichment (Groq) | 900 ms |
| BM25 + dense retrieval | 35 ms |
| SIIS lookup | 12 ms |
| LLM extraction (Groq) | 6 100 ms |
| Grounding check | 8 ms |
| Lint | 3 ms |
| Cache store | 18 ms |

---

## 4. Operational Cost and Cache Efficacy

Per-query cost estimate (Groq free tier, `qwen/qwen3-8b-fast`):

| Path | Approximate cost (USD) |
|---|---|
| Raw cache hit | \$0.0000 |
| Canonical cache hit | \$0.0001 (enrichment only) |
| Cold path | \$0.0011 (enrichment + extraction) |

Cache efficacy across a simulated workload of 100 queries (20 unique intents, each repeated 5 times with paraphrase variation):

| Metric | Value |
|---|---|
| Raw cache hit rate | 38% |
| Canonical cache hit rate | 29% |
| Cold path rate | 33% |
| Effective cost reduction vs all-cold | ~61% |

With Redis shared across workers, hit rates increase further because worker A's warm cache is immediately available to worker B, C, and D.

---

## 5. Architectural Ablation Analysis

| Component removed | Impact on accuracy | Impact on latency |
|---|---|---|
| Raw query pre-probe | No accuracy change | Cache hits increase from ~42 ms to ~1 100 ms (canonical path takes over) |
| Query enrichment (canonical form) | Paraphrase cache hit rate drops from 29% to 0% | Cold path latency unchanged; canonical path disappears |
| Grounding validator (E204) | 2 hallucinated actions per 20 queries reach the user | No latency impact |
| URL scrubber | Up to 3 web URL leaks per 20 queries in deeplink fields | No latency impact |
| BM25 hybrid retrieval (dense-only) | Correct deeplink selection drops from 85% to 72% | +8 ms (vector-only retrieval is slightly faster) |
| Lint pass gate | Schema-invalid responses stored in cache at ~4% rate | -3 ms per cold call |

The two highest-value components are the grounding validator and URL scrubber: both prevent unsafe or incorrect content from reaching the user with zero latency cost.

---

## 6. Known Edge Cases

| Edge case | Current behaviour | Mitigation |
|---|---|---|
| Query with no matching SIIS article | Returns empty `contexts` with `fallback: "no_match"` | Logged as `no_siis_context` diagnostic |
| Deeplink not in catalog, LLM invents URI | `_find_best_deeplink` falls back to `dummy_positive` | E401 lint code; never returned as a real deeplink |
| Cache polarity mismatch (positive query matches negative cached plan) | E501 raised; cache miss forced, cold path runs | Cosine threshold 0.85 prevents most false matches |
| Groq rate limit (429) | Groq client raises `RateLimitError`; propagated as HTTP 503 | Retry with exponential backoff recommended for production |
| Multi-worker Redis unavailable | In-memory fallback activates with logged warning; functionality preserved | No data loss; cache not shared across workers until Redis recovers |
| Very long query (>500 tokens) | SIIS text is truncated to 3 000 characters in prompt | Retrieval still covers the key symptom keywords via BM25 |
| Physical action with no deeplink | `actionableDeeplink` set to null; `validationDeeplink` set to null | Category forced to `manual` in extraction |
