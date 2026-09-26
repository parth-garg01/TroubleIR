"""Deeplink catalog loader with BM25 + dense retrieval for screen matching."""
import json
import os
import re
from functools import lru_cache
from typing import Optional
import numpy as np
from rank_bm25 import BM25Okapi

_catalog: list[dict] = []
_bm25: Optional[BM25Okapi] = None
_embeddings: Optional[np.ndarray] = None
_embed_model = None


def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        model_name = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        _embed_model = SentenceTransformer(model_name)
    return _embed_model


@lru_cache(maxsize=1)
def load_catalog(path: str = "data/raw/deeplinks.json") -> list[dict]:
    global _catalog, _bm25, _embeddings
    with open(path) as f:
        raw = json.load(f)
    _catalog = raw["deeplinks"] if isinstance(raw, dict) else raw

    # Build BM25 index on description + qna_description
    tokenized = [
        re.findall(r"\w+", (d.get("description", "") + " " + d.get("qna_description", "")).lower())
        for d in _catalog
    ]
    _bm25 = BM25Okapi(tokenized)

    # Build dense embedding index
    texts = [d.get("description", "") + ". " + d.get("qna_description", "") for d in _catalog]
    model = _get_embed_model()
    _embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)

    return _catalog


def get_catalog() -> list[dict]:
    return _catalog if _catalog else load_catalog()


def embed_query(text: str) -> np.ndarray:
    model = _get_embed_model()
    vec = model.encode([text], normalize_embeddings=True, show_progress_bar=False)
    return vec[0]


def retrieve_deeplinks(query: str, top_k: int = 10) -> list[dict]:
    """Hybrid BM25 + dense retrieval of relevant deeplinks."""
    cat = get_catalog()
    if not cat:
        return []

    tokens = re.findall(r"\w+", query.lower())

    # BM25 scores
    bm25_scores = np.array(_bm25.get_scores(tokens))

    # Dense scores
    q_vec = embed_query(query)
    dense_scores = (_embeddings @ q_vec).astype(float)

    # Normalize each to [0,1]
    def norm(arr):
        mn, mx = arr.min(), arr.max()
        if mx == mn:
            return np.zeros_like(arr)
        return (arr - mn) / (mx - mn)

    hybrid = 0.4 * norm(bm25_scores) + 0.6 * norm(dense_scores)
    top_idx = np.argsort(-hybrid)[:top_k]
    return [cat[i] for i in top_idx]


def find_deeplink_for_screen(screen_name: str) -> Optional[dict]:
    """Find the single best catalog entry for a named settings screen."""
    results = retrieve_deeplinks(screen_name, top_k=1)
    return results[0] if results else None
