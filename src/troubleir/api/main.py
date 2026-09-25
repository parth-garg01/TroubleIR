"""FastAPI application entry point."""
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

import os
# Validate required env vars early
if not os.environ.get("GROQ_API_KEY"):
    raise RuntimeError("GROQ_API_KEY is not set. Create a .env file with your Groq API key.")

from .routes import router
from ..pipeline.mapping import load_catalog
from ..pipeline.siis import load_siis
from ..pipeline.cache import load_cache
from ..graph.builder import save_graph


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize all indexes and caches on startup."""
    print("Loading deeplinks catalog...")
    load_catalog()
    print("Loading SIIS knowledge base...")
    load_siis()
    print("Loading persistent cache (if any)...")
    load_cache()
    print("Building SettingsGraph...")
    save_graph()
    print("TroubleIR ready.")
    yield


app = FastAPI(
    title="TroubleIR - Samsung Smart Guided Troubleshooting Engine",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# Serve static demo UI
static_dir = Path(__file__).parent.parent.parent.parent / "demo" / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
