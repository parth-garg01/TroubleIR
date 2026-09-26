"""FastAPI application entry point."""
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

load_dotenv()

import os
if not os.environ.get("GROQ_API_KEY"):
    import warnings
    warnings.warn("GROQ_API_KEY is not set. LLM-dependent endpoints will fail at call time.")

from .routes import router, limiter
from ..pipeline.mapping import load_catalog
from ..pipeline.siis import load_siis
from ..pipeline.cache import load_cache
from ..graph.builder import save_graph


_BANNER = r"""
  _____ ____   ___  _   _ ____  _      ___ ____
 |_   _|  _ \ / _ \| | | | __ )| |    |_ _|  _ \
   | | | |_) | | | | | | |  _ \| |     | || |_) |
   | | |  _ <| |_| | |_| | |_) | |___ | ||  _ <
   |_| |_| \_\\___/ \___/|____/|_____|___|_| \_\

 Samsung PRISM Theme 02 / Smart Guided Troubleshooting Engine
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize all indexes and caches on startup."""
    print(_BANNER)
    print("Loading deeplinks catalog...")
    load_catalog()
    print("Loading SIIS knowledge base...")
    load_siis()
    print("Loading persistent cache (if any)...")
    load_cache()
    print("Building SettingsGraph...")
    save_graph()
    print("\nTroubleIR ready. Open http://localhost:8000\n")
    yield


_ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",") if o.strip()]

app = FastAPI(
    title="TroubleIR - Samsung Smart Guided Troubleshooting Engine",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(router)

# Serve static demo UI
static_dir = Path(__file__).parent.parent.parent.parent / "demo" / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
