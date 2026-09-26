"""SIIS knowledge base lookup: retrieve relevant support article for a query."""
import json
import re
import os
from functools import lru_cache
from typing import Optional
import numpy as np
from rank_bm25 import BM25Okapi

_siis_data: dict = {}
_bm25_siis: Optional[BM25Okapi] = None
_siis_keys: list[str] = []
_siis_embed_matrix: Optional[np.ndarray] = None
_embed_model = None


def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        model_name = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        _embed_model = SentenceTransformer(model_name)
    return _embed_model


def load_siis(path: str = "data/raw/siis_responses.json") -> None:
    global _siis_data, _bm25_siis, _siis_keys, _siis_embed_matrix

    with open(path) as f:
        raw = json.load(f)

    # Official format: { "responses": [{ "id", "original_query", "siis_response": { "title", "content" } }] }
    # Legacy format: { key: { "title", "content" } }
    if isinstance(raw, dict) and "responses" in raw:
        for item in raw["responses"]:
            sr = item["siis_response"]
            _siis_data[item["id"]] = {
                "title": sr["title"],
                "content": sr["content"],
                "original_query": item.get("original_query", ""),
            }
    else:
        _siis_data = raw

    _siis_keys = list(_siis_data.keys())

    # Index on original_query (if present) + title + content for better matching
    index_texts = [
        _siis_data[k].get("original_query", "") + " " + _siis_data[k]["title"] + " " + _siis_data[k]["content"][:300]
        for k in _siis_keys
    ]
    tokenized = [re.findall(r"\w+", t.lower()) for t in index_texts]
    _bm25_siis = BM25Okapi(tokenized)

    model = _get_embed_model()
    _siis_embed_matrix = model.encode(
        index_texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    )


def get_siis_text(query: str, siis_path: str = "data/raw/siis_responses.json") -> Optional[str]:
    """Return the best-matching SIIS KB article content for query."""
    if not _siis_data:
        load_siis(siis_path)

    if not _siis_keys:
        return None

    tokens = re.findall(r"\w+", query.lower())
    bm25_scores = np.array(_bm25_siis.get_scores(tokens))

    model = _get_embed_model()
    q_vec = model.encode([query], normalize_embeddings=True, show_progress_bar=False)[0]
    dense_scores = (_siis_embed_matrix @ q_vec).astype(float)

    def norm(arr):
        mn, mx = arr.min(), arr.max()
        if mx == mn:
            return np.zeros_like(arr)
        return (arr - mn) / (mx - mn)

    hybrid = 0.4 * norm(bm25_scores) + 0.6 * norm(dense_scores)
    best_idx = int(np.argmax(hybrid))

    if hybrid[best_idx] < 0.1:
        return None

    best_key = _siis_keys[best_idx]
    return _siis_data[best_key]["content"]
