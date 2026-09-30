# TroubleIR

**Samsung PRISM Theme 02: Smart Guided Troubleshooting Engine**

TroubleIR turns a vague Galaxy device complaint into a verified, step-by-step troubleshooting plan grounded in real Samsung support knowledge. It is not a chatbot. It is a compiler: the user's words go in, a structured, validated, executable plan comes out.

Cold run: under 10 seconds. Repeat query cache hit: under 300 ms.

---

## Quickstart

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env and set GROQ_API_KEY

# 3. Run the server
set PYTHONPATH=src
python -m uvicorn troubleir.api.main:app --host 0.0.0.0 --port 8000 --reload

# 4. Open http://localhost:8000
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | (required) | Groq API key |
| `MODEL_NAME` | `qwen/qwen3-8b-fast` | Groq model ID |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence Transformers model |
| `CACHE_SIMILARITY_THRESHOLD` | `0.85` | Cosine similarity threshold for cache hits |
| `GROUNDING_MIN_COVERAGE` | `0.6` | Fraction of actions that must pass grounding |
| `GROUNDING_STEP_THRESHOLD` | `0.3` | Minimum IDF-weighted overlap per step |
| `RETRIEVAL_TOP_K` | `20` | Number of SIIS documents to retrieve |
| `ALLOWED_ORIGINS` | `http://localhost:8000,http://127.0.0.1:8000` | Comma-separated CORS allowed origins |
| `DEBUG_TOKEN` | (empty, disables debug routes) | Bearer token for protected admin endpoints |
| `REDIS_URL` | (empty, uses in-memory) | Redis connection string for shared cache |
| `WORKERS` | `(2 * CPU cores) + 1` | Number of gunicorn workers (max 8) |

## Running tests

```bash
# Unit tests (no server needed)
set PYTHONPATH=src
python -m pytest tests/test_schema.py tests/test_cache.py tests/test_lint.py tests/test_grounding.py -v

# API integration tests (server must be running on port 8000)
python -m pytest tests/test_api.py -v
```

---

## The problem it solves

When a Galaxy user says "my battery is draining too fast," they need specific actions, not a wall of text. Current support flows either dump generic documentation or require the user to navigate menus manually. TroubleIR closes that gap: it understands natural language, pulls the relevant Samsung SIIS knowledge, extracts actionable steps, verifies every step is grounded in evidence, maps each step to a real Settings deeplink, and returns a clean plan the device can act on directly.

---

## What makes it novel

Most RAG systems stop at retrieval. They find relevant documents and hand the text to an LLM to summarize. TroubleIR goes several steps further:

**Grounding validation.** Every step the LLM extracts is checked against the SIIS evidence using IDF-weighted term overlap. If a step is not supported by the retrieved document, it is rejected with diagnostic code E204. The LLM cannot hallucinate steps and have them pass through silently.

**Polarity-aware cache.** Two queries can be semantically similar but mean opposite things ("battery draining too fast" vs "battery charging too slowly"). A naive cache would serve the wrong plan. TroubleIR extracts the intent polarity and blocks cache reuse when it conflicts, so every cache hit is actually relevant.

**Two-stage sub-300 ms cache.** A raw query probe runs before any Groq call, returning cached plans in ~20-50 ms for repeat or near-identical queries. A second canonical probe catches paraphrases after enrichment. Only a double miss pays the full extraction cost.

**Deterministic deeplink binding.** The LLM only touches language: extraction and enrichment. Every downstream step, including deeplink resolution, grounding, lint, and schema validation, is deterministic code. The pipeline uses the official 578-deeplink Samsung catalog with `voiceassist://` URIs verbatim. It never constructs or guesses a URI.

**Validation deeplinks.** Each resolved step includes not just an actionable deeplink to open the setting, but also a validation deeplink that lets the device confirm the setting was actually changed. This is the full `StepGroup` schema as specified in the hackathon dataset.

**SettingsGraph traversal.** Deeplinks are resolved through a graph of the Settings hierarchy. Parent-menu matches (paths that land on a category page rather than a specific setting) are rejected with E310. Only leaf-level settings pass.

**Structured output with schema lint.** The final output is a `ContextDeeplinkResponse` validated by Pydantic v2 against the official schema. A separate lint pass checks ordering rules (auto before manual before critical), URL leak detection (E402), and schema field correctness (E403). The response is never delivered if it fails lint.

---

## How it works

```
User complaint (natural language)
        |
        v
  Raw query cache probe   embed + cosine only, no LLM call (~20-50 ms)
        |
   Cache hit? --> return cached plan immediately  (under 300 ms)
        |
       No
        |
        v
  Query Enrichment
  LLM generates 10 canonical paraphrases for robust cache keying
        |
        v
  Canonical cache lookup
  Cosine similarity >= 0.85 + polarity guard (catches paraphrases of cached queries)
        |
   Cache hit? --> return cached plan immediately
        |
       No
        |
        v
  SIIS Retrieval
  BM25 + Sentence Transformers hybrid search over 20 Samsung support articles
        |
        v
  LLM Extraction
  Groq / qwen3-8b-fast produces structured Goal / Action / StepGroup output
        |
        v
  IDF-weighted Grounding Validator
  Rejects steps not supported by SIIS evidence (E204)
        |
        v
  Deeplink Binding
  SettingsGraph resolves each action to a voiceassist:// URI
  Rejects parent-menu paths (E310)
        |
        v
  Schema Lint
  Pydantic v2 validation, URL leak check (E402), ordering rules (E403)
        |
        v
  Cache Store + Response
```

---

## Diagnostic codes

| Code | Meaning |
|------|---------|
| E204 | Step not supported by SIIS evidence (grounding failure) |
| E310 | Deeplink resolves to a parent menu, not a leaf setting |
| E401 | Invalid deeplink URI format |
| E402 | HTTP URL found in steps (should be deeplinks only) |
| E403 | Pydantic schema validation failed |
| E501 | Cache polarity mismatch: similar query, opposite intent |
| E502 | Cache slot exists but query slots do not match |
| E601 | Cached plan references a deeplink that has since changed |
| E701 | Goal score below acceptable threshold |

---

## Security

The API was hardened before submission:

**CORS lockdown.** The server does not accept requests from arbitrary origins. Allowed origins are set via the `ALLOWED_ORIGINS` environment variable and default to `localhost:8000` only. Set this to your actual domain before deploying.

**Rate limiting.** All expensive endpoints are rate-limited per IP using `slowapi`:
- `/v1/troubleshoot`: 20 requests per minute
- `/v1/catalog/search` and `/v1/catalog/list`: 30 per minute
- `/v1/graph/screens`: 60 per minute

This protects against both denial-of-service and accidental LLM cost runaway.

**Protected admin endpoints.** `/v1/debug/config`, `/v1/cache/stats`, and `/v1/cache/invalidate` require a `Bearer` token. Set `DEBUG_TOKEN` in `.env` to enable them. If the token is not set, the endpoints return 404 rather than leaking configuration.

**Input length caps.** Query length is capped at 2000 characters and SIIS override at 8000 characters at the Pydantic validation layer.

**No secrets in the repo.** The `.env` file is gitignored. The `GROQ_API_KEY` is never committed. All sensitive configuration is loaded at runtime from environment variables only.

**Error sanitization.** The `/v1/troubleshoot` endpoint logs full tracebacks server-side but returns only `"Internal server error"` to the caller, so stack traces and internal paths are never exposed.

---

## Official hackathon data

The project uses the official Samsung PRISM dataset exactly as provided:

- **578 deeplinks** with `voiceassist://masked/act/...` URIs. Every URI is used verbatim from the catalog. The pipeline never constructs or guesses a URI.
- **20 SIIS knowledge-base articles** keyed on `original_query` for retrieval.
- **Validation deeplinks** populated from `validation.deeplink` and `validation.key` in the catalog, so every `StepGroup` carries both an actionable and a validation deeplink where the catalog provides one.
- **Schema compliance**: the output matches the official `schema.py` exactly (`Goal`, `Action`, `StepGroup`, `Deeplink`, `ValidationDeepLink`, `actionCategory`). All 25 unit tests pass.

---

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
    cache.py         Polarity-aware semantic cache with Redis and in-memory backends
    orchestrator.py  End-to-end pipeline coordination (two-stage cache, enrichment, extraction)
    retrieval.py     BM25 + dense hybrid retrieval
    mapping.py       Deeplink catalog loader and retrieval
    siis.py          SIIS knowledge base loader
  graph/
    builder.py       SettingsGraph construction and screen index
  config.py          Centralised environment-driven configuration
  schema.py          Pydantic models for all data structures

data/raw/
  siis_responses.json   20 official SIIS knowledge-base articles
  deeplinks.json        578 official Settings deeplinks with voiceassist:// URIs

prism-docs/
  schema.py             Official hackathon output schema
  deeplinks.json        Official deeplink catalog (source)
  siis_responses.json   Official SIIS dataset (source)
  sample_output.json    Official sample output for reference
  input.txt             Official input examples

results.jsonl           Appendix B: 5 worked end-to-end examples in official schema format
metrics.md              Appendix C: evaluation report (schema compliance, accuracy, latency, cost, ablation)
samples/
  01_screen_flash_blank.json         Sample output for tablet screen flash and blank query
  02_screen_black_wont_turn_on.json  Sample output for black screen not turning on
  03_screen_cracked.json             Sample output for cracked screen
  04_screen_flicker_on_charger.json  Sample output for display flicker when charging
  05_touch_screen_laggy.json         Sample output for laggy touch responsiveness

demo/static/
  index.html            Scroll-driven frontend demo (GSAP + Lenis)
  favicon.svg           Samsung blue SVG favicon

tests/
  test_schema.py        Pydantic schema round-trip tests
  test_cache.py         Cache similarity and polarity tests
  test_lint.py          Lint rule unit tests
  test_grounding.py     IDF-weighted grounding validator (9 scenarios)
  test_api.py           Full API integration tests

gunicorn.conf.py        Multi-worker production server configuration
```

---

## Demo frontend

The demo at `demo/static/index.html` is a scroll-driven single-page walkthrough that shows a reviewer how the pipeline works before they run a single command.

Each scroll section corresponds to a real pipeline stage. The interactive section at the bottom lets you type a real complaint and compile it live against the running API. Results include:

- Action cards with step-by-step instructions, deeplink badges, and inline breadcrumb paths
- A live Settings navigation tree pulled from `/v1/graph/screens`, with the traversed path highlighted and destination nodes rendered as filled buttons
- A relevance score bar chart showing the LLM's confidence score for each action
- A **Download JSON** button that saves the full response in the official hackathon schema format

The engineering diagnostics panel (bottom-right toggle) shows latency, model, cost, lint result, canonical query, and variation count.

---

## Scalability

The default single-worker setup is enough for demos and low-traffic deployments. Here is how to scale it when you need to.

### Multiple workers (gunicorn)

The repo includes a `gunicorn.conf.py` that runs the app with multiple uvicorn workers:

```bash
# Linux / Mac (gunicorn does not run natively on Windows)
set PYTHONPATH=src
gunicorn -c gunicorn.conf.py troubleir.api.main:app
```

Default worker count is `(2 * CPU cores) + 1`, capped at 8. Override with the `WORKERS` environment variable.

The key setting is `preload_app = True`. This loads the Sentence Transformers model (about 90 MB) once in the master process before forking. Workers inherit it via copy-on-write, so you get 4 or 8 workers for the memory cost of one. Without this, each worker would download and allocate the model independently.

### Two-stage cache (sub-300 ms hits)

The cache runs two probes per incoming query:

1. **Raw probe**: embeds the query and runs a cosine search before any Groq call. Exact or near-exact repeat queries return in ~20-50 ms, well under the 300 ms target.
2. **Canonical probe**: if the raw probe misses, query enrichment runs (one Groq call) and the canonical form is checked. This catches paraphrases of previously seen queries without paying the full cold-path cost.

Only on a double miss does the full extraction pipeline run.

### Shared cache across workers (Redis)

By default the cache lives in each worker's memory separately. If one worker compiles a plan for "battery draining," only that worker benefits from the cache hit. The other workers each run a cold Groq call when they see the same query.

Setting `REDIS_URL` switches to a shared cache:

```bash
REDIS_URL=redis://localhost:6379/0
```

On store, the plan and polarity tokens are written to Redis. On startup, every worker loads all existing entries from Redis so it starts warm. The embedding vectors for cosine similarity are kept in local memory (no per-lookup Redis round-trip), so lookup speed is unchanged.

If Redis is unreachable at startup, the server falls back to in-memory automatically and logs a warning. The cache backend is reported in `GET /v1/cache/stats` as `"backend": "redis"` or `"backend": "memory"`.

### What this gives you

| Setup | Concurrent requests | Cache sharing | Cache hit latency | Memory |
|-------|---------------------|---------------|-------------------|--------|
| Single uvicorn worker | ~1-2 | N/A | ~42 ms (raw probe) | baseline |
| gunicorn, 4 workers, no Redis | ~4-8 | No (per-worker) | ~42 ms | ~1x (preload_app) |
| gunicorn, 4 workers, Redis | ~4-8 | Yes (all workers) | ~42 ms | ~1x (preload_app) |

For the Samsung PRISM demo (a handful of reviewers, mostly sequential queries), a single uvicorn worker is fine. The gunicorn + Redis setup is there for a real support-traffic deployment.

---

## Tech stack

- FastAPI 0.111 + Uvicorn 0.30
- slowapi 0.1.9 for rate limiting
- Groq SDK (qwen3-8b-fast)
- Pydantic v2 for schema validation and lint
- Sentence Transformers 6.1 for dense embeddings
- rank-bm25 for BM25 sparse retrieval
- Redis (optional) for shared cache across workers
- gunicorn for multi-worker production deployments
- GSAP 3.12.5 + Lenis 1.1.14 for the frontend
- Space Grotesk + IBM Plex Mono typography
