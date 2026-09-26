# TroubleIR

**Samsung PRISM Theme 02 / Smart Guided Troubleshooting Engine**

TroubleIR converts vague Galaxy device complaints into verified, step-by-step troubleshooting plans. Each plan is grounded against a Samsung SIIS knowledge base, validated against a SettingsGraph of real deeplinks, and protected by a polarity-aware semantic cache.

---

## What it does

You type something like "my battery is draining too fast." TroubleIR figures out what you actually mean, checks whether it has seen something similar before, pulls relevant Samsung support knowledge, asks an LLM to extract actionable steps, verifies every step is backed by real evidence, maps each action to a live Settings deeplink, and hands you a clean, structured plan you can execute on a Galaxy device. The whole thing takes under 10 seconds on a cold run and under 1 second on a cache hit.

---

## Architecture

```
User complaint (natural language)
        |
        v
  Query Enrichment
  (BM25 + dense embedding variations)
        |
        v
  Semantic Cache lookup
  (cosine sim >= 0.85 + polarity guard)
        |
   hit? yes --> return cached plan
        |
       no
        |
        v
  SIIS Retrieval
  (hybrid BM25 + Sentence Transformers, top-20)
        |
        v
  LLM Extraction
  (Groq / qwen3.8-27b, structured Pydantic output)
        |
        v
  IDF-weighted Grounding Validator
  (rejects steps not supported by SIIS evidence)
        |
        v
  Deeplink Binding
  (SettingsGraph rejects parent-menu paths, E310)
        |
        v
  Schema Lint
  (Pydantic v2, E401 URL leak, E402 schema failure)
        |
        v
  Cache Store + Response
```

## Pipeline stages and diagnostic codes

| Code | Name | Meaning |
|------|------|---------|
| E204 | UNGROUNDED_OPERATION | Step not supported by SIIS evidence |
| E310 | PARENT_MENU_MATCH | Deeplink resolves to a parent menu, not a leaf setting |
| E401 | INVALID_DEEPLINK | Deeplink format rejected by schema |
| E402 | URL_LEAK | HTTP URL found in steps (should be deeplinks only) |
| E403 | SCHEMA_FAILURE | Pydantic validation failed on LLM output |
| E501 | CACHE_POLARITY_MISMATCH | Polarity of cached plan differs from incoming query |
| E502 | CACHE_SLOT_MISMATCH | Cache slot exists but query slots do not match |
| E601 | STALE_DEPENDENCY | Cached plan references a deeplink that has since changed |
| E701 | LOW_RELIABILITY | Goal score below acceptable threshold |

## Project structure

```
src/troubleir/
  api/
    main.py          FastAPI app, CORS config, rate limiter setup, static serving
    routes.py        /v1/troubleshoot, /v1/health, /v1/catalog, /v1/cache, /v1/graph
  compiler/
    grounding.py     IDF-weighted grounding validator
    lint.py          Schema and deeplink lint rules
  pipeline/
    cache.py         Polarity-aware semantic cache with hit-rate tracking
    orchestrator.py  End-to-end pipeline coordination
    retrieval.py     BM25 + dense hybrid retrieval
    mapping.py       Deeplink catalog loader and retrieval
    siis.py          SIIS knowledge base loader
  graph/
    builder.py       SettingsGraph construction and screen index
  config.py          Centralised environment-driven configuration
  schema.py          Pydantic models for all data structures

data/raw/
  siis_responses.json   21 Samsung SIIS knowledge-base articles
  deeplinks.json        62 Samsung Settings deeplinks

demo/static/
  index.html            Scroll-driven frontend (GSAP + Lenis)
  favicon.svg           Samsung blue SVG favicon

tests/
  test_schema.py        Pydantic schema round-trip tests
  test_cache.py         Cache similarity and polarity tests
  test_lint.py          Lint rule unit tests
  test_grounding.py     IDF-weighted grounding validator (9 scenarios)
  test_api.py           Full API integration tests
```

## Quickstart

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables
cp .env.example .env
# edit .env and set GROQ_API_KEY

# 3. Run the server
set PYTHONPATH=src
python -m uvicorn troubleir.api.main:app --host 0.0.0.0 --port 8000 --reload

# 4. Open http://localhost:8000 in your browser
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | (required) | Groq API key |
| `MODEL_NAME` | `qwen/qwen3.8-27b` | Groq model ID |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence Transformers model |
| `CACHE_SIMILARITY_THRESHOLD` | `0.85` | Cosine similarity threshold for cache hits |
| `GROUNDING_MIN_COVERAGE` | `0.6` | Fraction of actions that must pass grounding |
| `GROUNDING_STEP_THRESHOLD` | `0.3` | Minimum IDF-weighted overlap per step |
| `RETRIEVAL_TOP_K` | `20` | Number of SIIS documents to retrieve |
| `ALLOWED_ORIGINS` | `http://localhost:8000,http://127.0.0.1:8000` | Comma-separated CORS allowed origins |
| `DEBUG_TOKEN` | (empty, disables debug routes) | Bearer token for protected admin endpoints |

## Running tests

```bash
# Unit tests only (no server needed)
set PYTHONPATH=src
python -m pytest tests/test_schema.py tests/test_cache.py tests/test_lint.py tests/test_grounding.py -v

# API integration tests (server must be running on port 8000)
python -m pytest tests/test_api.py -v
```

---

## What was built and improved

This section walks through the major pieces added or changed during development. It is aimed at a reviewer reading the project for the first time.

### Demo frontend

The demo at `demo/static/index.html` is a scroll-driven single-page experience that walks a reviewer through every stage of the pipeline before they even open a terminal. It uses GSAP ScrollTrigger for animations and Lenis for smooth scrolling.

Each scroll section corresponds to one real pipeline stage:

- **SIIS Evidence** - shows a source document with highlights and the deeplink bindings extracted from it. Layout is two-column: the article on the left, the extracted bindings on the right.
- **Compiler Pipeline** - animates through the seven deterministic stages, showing each stage name and its output token. Stage dots animate blue as each stage completes.
- **SettingsGraph** - shows the navigation graph with traversal statistics (depth, resolved screens, parent-only matches) and a resolved destination annotation.
- **Action Ordering** - shows how actions are ranked by goal score with a legend explaining auto, manual, and critical categories.
- **Polarity Protection** - demonstrates why two semantically similar queries ("battery is draining too fast" vs "battery is charging too slowly") cannot share a cache entry because their extracted polarities differ.

The interactive section at the bottom lets you type a real complaint and compile it live against the running API. The result panel shows:

- Action cards with step-by-step instructions, deeplink badges, and inline breadcrumb paths
- A **Settings navigation tree** pulled live from `/v1/graph/screens`, showing the full Settings hierarchy with the traversed path highlighted in blue and destination nodes rendered as filled buttons
- A **relevance score bar chart** at the bottom showing the LLM's confidence score for each action

The engineering diagnostics panel (toggled from the bottom-right) shows latency, model, cost, lint result, canonical query, and variation count. It matches the page's cream background rather than using a dark overlay.

Design decisions worth noting:
- No card boxes or bordered containers anywhere on the page. All visual separation uses whitespace, typography weight, and thin lines.
- Two-column alternating layout for every scene section so neither side is ever empty.
- Section padding reduced from 72px to 48px to avoid dead space between sections.
- All text uses Space Grotesk for body and IBM Plex Mono for code and labels. No em dashes in any copy.

### Backend fixes

**Error handling** - the `/v1/troubleshoot` endpoint previously propagated raw Python exception messages to the client. It now logs the full traceback server-side with `logger.exception` and returns only `"Internal server error"` to the caller.

**Schema compatibility** - the test suite was importing `ActionableDeeplink` and `ActionCategory` directly from `schema.py`, which did not export them under those names. Aliases were added at the bottom of `schema.py` so the tests pass without modifying test code.

**Model consistency** - `MODEL_NAME` from `config.py` is now used consistently across all response paths in `orchestrator.py`, so the `meta.model` field in API responses always reflects what is set in the environment rather than a hardcoded fallback.

### Security hardening

The API was open by default. The following was tightened up:

**CORS** - previously `allow_origins=["*"]`. Now reads from `ALLOWED_ORIGINS` environment variable, defaulting to `localhost:8000` only. Set this to your actual domain before deploying.

**Rate limiting** - added `slowapi` rate limiting on all expensive endpoints:
- `/v1/troubleshoot`: 20 requests per minute per IP
- `/v1/catalog/search` and `/v1/catalog/list`: 30 per minute
- `/v1/graph/screens`: 60 per minute

This protects against both DoS and unintended LLM cost runaway.

**Admin endpoints** - `/v1/debug/config`, `/v1/cache/stats`, and `/v1/cache/invalidate` are now behind a `Bearer` token check. Set `DEBUG_TOKEN` in your `.env` and pass `Authorization: Bearer <token>` to access them. If `DEBUG_TOKEN` is not set, the endpoints return 404.

**Input length caps** - query length is capped at 2000 characters and SIIS override at 8000 characters at the Pydantic validation layer, preventing large payload abuse.

---

## Tech stack

- FastAPI 0.111 + Uvicorn 0.30
- slowapi 0.1.9 for rate limiting
- Groq SDK 1.6 (qwen3.8-27b)
- Pydantic v2 for schema validation
- Sentence Transformers 6.1 for dense embeddings
- rank-bm25 for BM25 sparse retrieval
- GSAP 3.12.5 + Lenis 1.1.14 for the frontend
- Space Grotesk + IBM Plex Mono typography
