"""Atom-level semantic cache with polarity/slot protection.

Redis backend (optional): set REDIS_URL to enable shared cache across workers.
Falls back to in-process dict when Redis is unavailable or not configured.
Each worker keeps a local embedding index for fast cosine similarity; the
plan payloads and polarity tokens are sourced from Redis so all workers
share the same data without duplicating LLM calls.
"""
import base64
import json
import logging
import os
import re
import time
import hashlib
from typing import Optional
import numpy as np

from ..schema import ContextDeeplinkResponse

logger = logging.getLogger(__name__)

# In-process stores (always populated; also used when Redis is absent)
_CACHE: dict[str, dict] = {}  # key -> {embedding, plan, polarity, ts}
_STATS = {"hits": 0, "misses": 0, "stores": 0, "invalidations": 0}
_EMBED_MODEL = None

SIMILARITY_THRESHOLD = float(os.environ.get("CACHE_SIMILARITY_THRESHOLD", "0.85"))
POLARITY_STRICT_THRESHOLD = float(os.environ.get("POLARITY_STRICT_THRESHOLD", "0.92"))

_POLARITY_OPPOSITES = [
    ({"too bright", "bright", "high brightness", "blinding"}, {"too dim", "dim", "low brightness", "dark screen"}),
    ({"too loud", "loud", "high volume"}, {"too quiet", "quiet", "low volume", "silent"}),
    ({"overheating", "hot", "heat"}, {"not charging", "cold"}),
    ({"too fast", "speed fast"}, {"too slow", "slow", "lag", "sluggish"}),
    ({"enable", "turn on", "activate"}, {"disable", "turn off", "deactivate"}),
    ({"not charging", "won't charge"}, {"overcharging", "fast drain while charging"}),
    ({"battery full too fast"}, {"battery drains fast", "battery drain", "rapid drain"}),
]

_POLARITY_NEGATIONS = re.compile(
    r"\b(not|no|never|don\'t|doesn\'t|won\'t|can\'t|cannot|isn\'t|aren\'t)\b",
    re.I,
)

# ── Redis client (None when not configured) ──────────────────────────────────

_REDIS = None
_REDIS_PREFIX = "troubleir:cache:"


def _get_redis():
    global _REDIS
    if _REDIS is not None:
        return _REDIS
    url = os.environ.get("REDIS_URL", "")
    if not url:
        return None
    try:
        import redis as redis_lib
        client = redis_lib.from_url(url, decode_responses=False, socket_connect_timeout=2)
        client.ping()
        _REDIS = client
        logger.info("Redis cache backend connected: %s", url)
    except Exception as exc:
        logger.warning("Redis unavailable, falling back to in-memory cache: %s", exc)
        _REDIS = None
    return _REDIS


# ── Embedding helpers ─────────────────────────────────────────────────────────

def _get_embed_model():
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        from sentence_transformers import SentenceTransformer
        model_name = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        _EMBED_MODEL = SentenceTransformer(model_name)
    return _EMBED_MODEL


def _embed(text: str) -> np.ndarray:
    return _get_embed_model().encode([text], normalize_embeddings=True, show_progress_bar=False)[0]


def _vec_to_b64(vec: np.ndarray) -> str:
    return base64.b64encode(vec.astype(np.float32).tobytes()).decode()


def _b64_to_vec(s: str) -> np.ndarray:
    return np.frombuffer(base64.b64decode(s), dtype=np.float32)


# ── Polarity helpers ──────────────────────────────────────────────────────────

def _extract_polarity_tokens(text: str) -> set[str]:
    text_lower = text.lower()
    tokens = set(re.findall(r"\w+", text_lower))
    if _POLARITY_NEGATIONS.search(text_lower):
        tokens.add("__negated__")
    return tokens


def _polarity_matches(query_tokens: set[str], cached_polarity: set[str]) -> bool:
    for pos_set, neg_set in _POLARITY_OPPOSITES:
        if bool(query_tokens & pos_set) and bool(cached_polarity & neg_set):
            return False
        if bool(query_tokens & neg_set) and bool(cached_polarity & pos_set):
            return False
    if ("__negated__" in query_tokens) != ("__negated__" in cached_polarity):
        return False
    return True


def _make_atom_key(canonical: str) -> str:
    return hashlib.md5(canonical.lower().strip().encode()).hexdigest()


# ── Redis serialisation ───────────────────────────────────────────────────────

def _entry_to_redis(entry: dict) -> bytes:
    payload = {
        "canonical": entry["canonical"],
        "embedding": _vec_to_b64(entry["embedding"]),
        "polarity": list(entry.get("polarity", set())),
        "plan": entry["plan"],
        "dependencies": entry.get("dependencies", []),
        "ts": entry["ts"],
    }
    return json.dumps(payload).encode()


def _entry_from_redis(data: bytes) -> dict:
    payload = json.loads(data)
    payload["embedding"] = _b64_to_vec(payload["embedding"])
    payload["polarity"] = set(payload["polarity"])
    return payload


# ── Public API ────────────────────────────────────────────────────────────────

def lookup(canonical: str, raw_query: str) -> Optional[ContextDeeplinkResponse]:
    if not _CACHE:
        return None

    q_vec = _embed(canonical)
    q_tokens = _extract_polarity_tokens(raw_query)

    best_sim = 0.0
    best_entry = None

    for entry in _CACHE.values():
        sim = float(np.dot(q_vec, entry["embedding"]))
        if sim < SIMILARITY_THRESHOLD:
            continue
        if not _polarity_matches(q_tokens, entry.get("polarity", set())):
            continue
        if sim > best_sim:
            best_sim = sim
            best_entry = entry

    if best_entry is None:
        _STATS["misses"] += 1
        return None

    _STATS["hits"] += 1
    best_entry["last_hit"] = time.time()
    return ContextDeeplinkResponse(**best_entry["plan"])


def store(
    canonical: str,
    plan: ContextDeeplinkResponse,
    dependencies: list[str] | None = None,
) -> None:
    key = _make_atom_key(canonical)
    vec = _embed(canonical)
    polarity = _extract_polarity_tokens(canonical)
    entry = {
        "canonical": canonical,
        "embedding": vec,
        "polarity": polarity,
        "plan": plan.model_dump(),
        "dependencies": dependencies or [],
        "ts": time.time(),
        "hits": 0,
    }
    _CACHE[key] = entry
    _STATS["stores"] += 1

    r = _get_redis()
    if r is not None:
        try:
            r.set(_REDIS_PREFIX + key, _entry_to_redis(entry))
        except Exception as exc:
            logger.warning("Redis write failed: %s", exc)


def invalidate_by_dependency(deeplink_uri: str) -> int:
    to_remove = [k for k, v in _CACHE.items() if deeplink_uri in v.get("dependencies", [])]
    for k in to_remove:
        del _CACHE[k]
        r = _get_redis()
        if r is not None:
            try:
                r.delete(_REDIS_PREFIX + k)
            except Exception as exc:
                logger.warning("Redis delete failed: %s", exc)
    _STATS["invalidations"] += len(to_remove)
    return len(to_remove)


def get_cache_stats() -> dict:
    total = _STATS["hits"] + _STATS["misses"]
    hit_rate = round(_STATS["hits"] / total, 3) if total else 0.0
    return {
        "size": len(_CACHE),
        "hits": _STATS["hits"],
        "misses": _STATS["misses"],
        "stores": _STATS["stores"],
        "invalidations": _STATS["invalidations"],
        "hit_rate": hit_rate,
        "backend": "redis" if _get_redis() is not None else "memory",
        "keys": list(_CACHE.keys())[:10],
    }


def save_cache(path: str = "data/processed/cache.json") -> None:
    """Persist cache to disk as JSON (Redis users can skip this)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    serializable = {}
    for k, v in _CACHE.items():
        row = {kk: vv for kk, vv in v.items() if kk != "embedding"}
        if isinstance(row.get("polarity"), set):
            row["polarity"] = list(row["polarity"])
        serializable[k] = row
    with open(path, "w") as f:
        json.dump(serializable, f, indent=2)


def load_cache(path: str = "data/processed/cache.json") -> None:
    """Load cache: Redis first (all workers sync from shared store), then disk."""
    r = _get_redis()
    if r is not None:
        try:
            keys = r.keys(_REDIS_PREFIX + "*")
            if keys:
                logger.info("Loading %d entries from Redis cache...", len(keys))
                for rk in keys:
                    try:
                        data = r.get(rk)
                        if data:
                            entry = _entry_from_redis(data)
                            atom_key = rk.decode().removeprefix(_REDIS_PREFIX)
                            _CACHE[atom_key] = entry
                    except Exception as exc:
                        logger.warning("Failed to load Redis key %s: %s", rk, exc)
                return
        except Exception as exc:
            logger.warning("Redis scan failed, falling back to disk: %s", exc)

    # Disk fallback
    if not os.path.exists(path):
        return
    with open(path) as f:
        data = json.load(f)
    for k, v in data.items():
        v["embedding"] = _embed(v["canonical"])
        if isinstance(v.get("polarity"), list):
            v["polarity"] = set(v["polarity"])
        _CACHE[k] = v
    logger.info("Loaded %d entries from disk cache.", len(data))
