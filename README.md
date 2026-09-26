# TroubleIR

**Samsung PRISM Theme 02 / Smart Guided Troubleshooting Engine**

TroubleIR converts vague Galaxy device complaints into verified, step-by-step troubleshooting plans. Each plan is grounded against a Samsung SIIS knowledge base, validated against a SettingsGraph of real deeplinks, and protected by a polarity-aware semantic cache.

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

## Project structure

```
src/troubleir/
  api/
    main.py          FastAPI app with static file serving
    routes.py        /v1/troubleshoot, /v1/health, /v1/catalog, /v1/cache
  compiler/
    grounding.py     IDF-weighted grounding validator
    lint.py          Schema and deeplink lint rules
  pipeline/
    cache.py         Polarity-aware semantic cache with hit-rate tracking
    orchestrator.py  End-to-end pipeline coordination
    retrieval.py     BM25 + dense hybrid retrieval
  config.py          Centralised environment-driven configuration

data/raw/
  siis_responses.json   21 Samsung SIIS knowledge-base articles
  deeplinks.json        62 Samsung Settings deeplinks

demo/static/
  index.html            Immersive scroll-driven frontend (GSAP + Lenis)
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

## Running tests

```bash
# Unit tests only
set PYTHONPATH=src
python -m pytest tests/test_schema.py tests/test_cache.py tests/test_lint.py tests/test_grounding.py -v

# API integration tests (server must be running)
python -m pytest tests/test_api.py -v
```

## Tech stack

- FastAPI 0.111 + Uvicorn 0.30
- Groq SDK 1.6 (qwen3.8-27b)
- Pydantic v2 for schema validation
- Sentence Transformers 6.1 for dense embeddings
- rank-bm25 for BM25 sparse retrieval
- GSAP 3.12.5 + Lenis 1.1.14 for the frontend
- Space Grotesk + IBM Plex Mono typography
