"""Integration tests for the TroubleIR FastAPI endpoints.

Requires the server to be running at http://127.0.0.1:8000.
Run with: py -m pytest tests/test_api.py -v
"""
import os
import pytest
import requests

BASE = "http://127.0.0.1:8000"

needs_llm = pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set; skipping LLM-dependent test",
)


def _get(path: str, **kwargs):
    return requests.get(f"{BASE}{path}", timeout=5, **kwargs)


def _post(path: str, json: dict, **kwargs):
    return requests.post(f"{BASE}{path}", json=json, timeout=60, **kwargs)


# ── health ──────────────────────────────────────────────────────────────────

def test_health_ok():
    r = _get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["service"] == "TroubleIR"


def test_health_detailed():
    r = _get("/v1/health/detailed")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "catalog" in body["components"]
    assert body["components"]["catalog"]["loaded"] is True
    assert body["components"]["catalog"]["entries"] > 0


# ── catalog ──────────────────────────────────────────────────────────────────

def test_catalog_list_default_page():
    r = _get("/v1/catalog/list")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 0
    assert len(body["results"]) <= body["page_size"]
    assert body["page"] == 1


def test_catalog_list_pagination():
    r1 = _get("/v1/catalog/list", params={"page": 1, "page_size": 5})
    r2 = _get("/v1/catalog/list", params={"page": 2, "page_size": 5})
    assert r1.status_code == 200
    assert r2.status_code == 200
    ids1 = [e["deeplink"] for e in r1.json()["results"]]
    ids2 = [e["deeplink"] for e in r2.json()["results"]]
    assert set(ids1).isdisjoint(set(ids2)), "Pages should not overlap"


def test_catalog_search():
    r = _get("/v1/catalog/search", params={"q": "battery"})
    assert r.status_code == 200
    body = r.json()
    assert "results" in body
    assert body["count"] >= 0


def test_catalog_search_requires_query():
    r = _get("/v1/catalog/search")
    assert r.status_code == 422


# ── cache ────────────────────────────────────────────────────────────────────

def test_cache_stats_structure():
    r = _get("/v1/cache/stats")
    assert r.status_code == 200
    body = r.json()
    assert "size" in body
    assert "hit_rate" in body
    assert isinstance(body["size"], int)
    assert 0.0 <= body["hit_rate"] <= 1.0


def test_cache_invalidate_unknown_uri():
    r = _post("/v1/cache/invalidate", json={"deeplink_uri": "voiceassist://masked/act/nonexistent"})
    assert r.status_code == 200
    assert r.json()["removed"] == 0


# ── graph ─────────────────────────────────────────────────────────────────────

def test_graph_screens():
    r = _get("/v1/graph/screens")
    assert r.status_code == 200
    body = r.json()
    assert "screens" in body
    assert isinstance(body["screens"], dict)
    assert body["count"] > 0


# ── troubleshoot ──────────────────────────────────────────────────────────────

def test_troubleshoot_empty_query_rejected():
    r = _post("/v1/troubleshoot", json={"query": ""})
    assert r.status_code == 422


@needs_llm
def test_troubleshoot_out_of_scope_returns_no_match():
    r = _post("/v1/troubleshoot", json={"query": "My washing machine is broken"})
    assert r.status_code == 200
    body = r.json()
    resp = body.get("response", {})
    assert resp.get("fallback") == "no_match" or len(resp.get("contexts", [])) == 0


@needs_llm
def test_troubleshoot_response_schema():
    r = _post("/v1/troubleshoot", json={"query": "screen too bright at night"})
    assert r.status_code == 200
    body = r.json()
    assert "query" in body
    assert "response" in body
    assert "meta" in body
    meta = body["meta"]
    assert "latency_ms" in meta
    assert "cache_hit" in meta
    assert isinstance(meta["latency_ms"], int)
    assert isinstance(meta["cache_hit"], bool)


@needs_llm
def test_troubleshoot_warm_cache_faster():
    query = "battery draining quickly after software update"
    r1 = _post("/v1/troubleshoot", json={"query": query})
    r2 = _post("/v1/troubleshoot", json={"query": query})
    assert r1.status_code == 200
    assert r2.status_code == 200
    meta2 = r2.json()["meta"]
    assert meta2["cache_hit"] is True, "Second identical request should be a cache hit"
