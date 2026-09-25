"""API route definitions."""
import time
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, field_validator

from ..pipeline.orchestrator import run_pipeline
from ..pipeline.cache import get_cache_stats, invalidate_by_dependency, save_cache
from ..pipeline.mapping import get_catalog, retrieve_deeplinks
from ..graph.builder import get_screen_index
from ..config import MAX_QUERY_LEN, MAX_SIIS_OVERRIDE_LEN

router = APIRouter()


class TroubleshootRequest(BaseModel):
    query: str
    siis_response: Optional[str] = None

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("query must not be empty")
        if len(v) > MAX_QUERY_LEN:
            raise ValueError(f"query exceeds {MAX_QUERY_LEN} character limit")
        return v

    @field_validator("siis_response")
    @classmethod
    def siis_size_limit(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v) > MAX_SIIS_OVERRIDE_LEN:
            raise ValueError(f"siis_response exceeds {MAX_SIIS_OVERRIDE_LEN} character limit")
        return v


class InvalidateRequest(BaseModel):
    deeplink_uri: str


@router.get("/health")
async def health():
    return {"status": "ok", "service": "TroubleIR", "version": "0.1.0"}


@router.get("/v1/health/detailed")
async def health_detailed():
    """Component-level health check — catalog, cache, and embedding model readiness."""
    catalog = get_catalog()
    stats = get_cache_stats()
    return {
        "status": "ok",
        "components": {
            "catalog": {"loaded": True, "entries": len(catalog)},
            "cache": {"entries": stats["size"], "hit_rate": stats.get("hit_rate", 0.0)},
        },
    }


@router.post("/v1/troubleshoot")
async def troubleshoot(req: TroubleshootRequest):
    result = run_pipeline(req.query, siis_response_override=req.siis_response)
    return result.model_dump()


@router.get("/v1/cache/stats")
async def cache_stats():
    return get_cache_stats()


@router.post("/v1/cache/invalidate")
async def cache_invalidate(req: InvalidateRequest):
    removed = invalidate_by_dependency(req.deeplink_uri)
    save_cache()
    return {"removed": removed, "deeplink_uri": req.deeplink_uri}


@router.get("/v1/catalog/search")
async def catalog_search(q: str = Query(..., min_length=2, description="Search term"), top_k: int = Query(10, ge=1, le=50)):
    """Search the deeplinks catalog using hybrid BM25 + dense retrieval."""
    results = retrieve_deeplinks(q, top_k=top_k)
    return {"query": q, "results": results[:top_k], "count": len(results)}


@router.get("/v1/catalog/list")
async def catalog_list(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    """Paginate through the full deeplinks catalog."""
    catalog = get_catalog()
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "total": len(catalog),
        "page": page,
        "page_size": page_size,
        "results": catalog[start:end],
    }


@router.get("/v1/graph/screens")
async def get_screens():
    """Return the SettingsGraph screen index for visualization."""
    index = get_screen_index()
    return {"screens": index, "count": len(index)}
