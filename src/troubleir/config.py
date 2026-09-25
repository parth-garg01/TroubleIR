"""Central configuration — all env-driven constants live here."""
import os


GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")
MODEL_NAME: str = os.environ.get("MODEL_NAME", "qwen/qwen3.8-27b")
EMBEDDING_MODEL: str = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

CACHE_SIMILARITY_THRESHOLD: float = float(os.environ.get("CACHE_SIMILARITY_THRESHOLD", "0.85"))
POLARITY_STRICT_THRESHOLD: float = float(os.environ.get("POLARITY_STRICT_THRESHOLD", "0.92"))
GROUNDING_MIN_COVERAGE: float = float(os.environ.get("GROUNDING_MIN_COVERAGE", "0.6"))
GROUNDING_STEP_THRESHOLD: float = float(os.environ.get("GROUNDING_STEP_THRESHOLD", "0.3"))

DEEPLINKS_PATH: str = os.environ.get("DEEPLINKS_PATH", "data/raw/deeplinks.json")
SIIS_PATH: str = os.environ.get("SIIS_PATH", "data/raw/siis_responses.json")
CACHE_PATH: str = os.environ.get("CACHE_PATH", "data/processed/cache.json")
GRAPH_PATH: str = os.environ.get("GRAPH_PATH", "data/processed/settings_graph.json")

MAX_QUERY_LEN: int = int(os.environ.get("MAX_QUERY_LEN", "2000"))
MAX_SIIS_OVERRIDE_LEN: int = int(os.environ.get("MAX_SIIS_OVERRIDE_LEN", "8000"))

RETRIEVAL_TOP_K: int = int(os.environ.get("RETRIEVAL_TOP_K", "20"))
ENRICHMENT_VARIATIONS: int = int(os.environ.get("ENRICHMENT_VARIATIONS", "10"))

LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")
