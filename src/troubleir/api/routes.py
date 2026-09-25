"""API route definitions."""
import time
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..pipeline.orchestrator import run_pipeline
from ..pipeline.cache import get_cache_stats, invalidate_by_dependency, save_cache
from ..graph.builder import get_screen_index

router = APIRouter()


class TroubleshootRequest(BaseModel):
    query: str
    siis_response: Optional[str] = None


class InvalidateRequest(BaseModel):
    deeplink_uri: str


@router.get("/health")
async def health():
    return {"status": "ok", "service": "TroubleIR"}


@router.post("/v1/troubleshoot")
async def troubleshoot(req: TroubleshootRequest):
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="query must not be empty")

    result = run_pipeline(req.query.strip(), siis_response_override=req.siis_response)
    return result.model_dump()


@router.get("/v1/cache/stats")
async def cache_stats():
    return get_cache_stats()


@router.post("/v1/cache/invalidate")
async def cache_invalidate(req: InvalidateRequest):
    removed = invalidate_by_dependency(req.deeplink_uri)
    save_cache()
    return {"removed": removed, "deeplink_uri": req.deeplink_uri}


@router.get("/v1/graph/screens")
async def get_screens():
    """Return the SettingsGraph screen index for visualization."""
    index = get_screen_index()
    return {"screens": index}
