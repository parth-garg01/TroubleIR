"""Atom-level semantic cache with polarity/slot protection."""
import json
import os
import re
import time
import hashlib
from typing import Optional
import numpy as np

from ..schema import ContextDeeplinkResponse


_CACHE: dict[str, dict] = {}  # atom_key -> {embedding, plan, ts, dependencies, polarity}
_EMBED_MODEL = None
_STATS = {"hits": 0, "misses": 0, "stores": 0, "invalidations": 0}

SIMILARITY_THRESHOLD = float(os.environ.get("CACHE_SIMILARITY_THRESHOLD", "0.85"))
POLARITY_STRICT_THRESHOLD = float(os.environ.get("POLARITY_STRICT_THRESHOLD", "0.92"))

# Polarity word pairs - opposite intents that look semantically similar
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
    re.I
)


def _get_embed_model():
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        from sentence_transformers import SentenceTransformer
        model_name = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        _EMBED_MODEL = SentenceTransformer(model_name)
    return _EMBED_MODEL


def _embed(text: str) -> np.ndarray:
    model = _get_embed_model()
    return model.encode([text], normalize_embeddings=True, show_progress_bar=False)[0]


def _extract_polarity_tokens(text: str) -> set[str]:
    text_lower = text.lower()
    tokens = set(re.findall(r"\w+", text_lower))
    # check negation context
    if _POLARITY_NEGATIONS.search(text_lower):
        tokens.add("__negated__")
    return tokens


def _polarity_matches(query_tokens: set[str], cached_polarity: set[str]) -> bool:
    """Return False if opposite polarity is detected."""
    for pos_set, neg_set in _POLARITY_OPPOSITES:
        query_is_pos = bool(query_tokens & pos_set)
        query_is_neg = bool(query_tokens & neg_set)
        cached_is_pos = bool(cached_polarity & pos_set)
        cached_is_neg = bool(cached_polarity & neg_set)
        if query_is_pos and cached_is_neg:
            return False
        if query_is_neg and cached_is_pos:
            return False
    # Negation asymmetry
    q_neg = "__negated__" in query_tokens
    c_neg = "__negated__" in cached_polarity
    if q_neg != c_neg:
        return False
    return True


def _make_atom_key(canonical: str) -> str:
    return hashlib.md5(canonical.lower().strip().encode()).hexdigest()


def lookup(canonical: str, raw_query: str) -> Optional[ContextDeeplinkResponse]:
    """Look up cached plan with polarity and slot protection."""
    if not _CACHE:
        return None

    q_vec = _embed(canonical)
    q_tokens = _extract_polarity_tokens(raw_query)

    best_sim = 0.0
    best_entry = None

    for key, entry in _CACHE.items():
        cached_vec = entry["embedding"]
        sim = float(np.dot(q_vec, cached_vec))
        if sim < SIMILARITY_THRESHOLD:
            continue
        # Polarity guard
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
    """Store a verified plan in the atom cache."""
    key = _make_atom_key(canonical)
    vec = _embed(canonical)
    polarity = _extract_polarity_tokens(canonical)
    _CACHE[key] = {
        "canonical": canonical,
        "embedding": vec,
        "polarity": polarity,
        "plan": plan.model_dump(),
        "dependencies": dependencies or [],
        "ts": time.time(),
        "hits": 0,
    }
    _STATS["stores"] += 1


def invalidate_by_dependency(deeplink_uri: str) -> int:
    """Remove all cached plans that depend on a specific deeplink URI. Returns count removed."""
    to_remove = [k for k, v in _CACHE.items() if deeplink_uri in v.get("dependencies", [])]
    for k in to_remove:
        del _CACHE[k]
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
        "keys": list(_CACHE.keys())[:10],
    }


def save_cache(path: str = "data/processed/cache.json") -> None:
    """Persist cache to disk (embeddings excluded - rebuild on load)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    serializable = {k: {kk: vv for kk, vv in v.items() if kk not in ("embedding",)} for k, v in _CACHE.items()}
    for v in serializable.values():
        if isinstance(v.get("polarity"), set):
            v["polarity"] = list(v["polarity"])
    with open(path, "w") as f:
        json.dump(serializable, f, indent=2)


def load_cache(path: str = "data/processed/cache.json") -> None:
    """Load persisted cache and rebuild embeddings."""
    if not os.path.exists(path):
        return
    with open(path) as f:
        data = json.load(f)
    for k, v in data.items():
        vec = _embed(v["canonical"])
        v["embedding"] = vec
        if isinstance(v.get("polarity"), list):
            v["polarity"] = set(v["polarity"])
        _CACHE[k] = v
