"""Screen resolution: reject parent-menu matches, resolve to deepest specific screen."""
import re
from typing import Optional
from .builder import get_screen_index


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


def resolve_screen(candidate: str, preferred_keywords: list[str] | None = None) -> dict:
    """
    Given a candidate screen name, return:
      - resolved_path: full path to the deepest matching screen
      - rejected: True if only a parent menu was found
      - rejection_reason: why it was rejected
    """
    index = get_screen_index()
    candidate_lower = candidate.lower()
    candidate_tokens = _tokenize(candidate)

    # Direct match
    if candidate_lower in index:
        path = index[candidate_lower]
        # Check if a deeper child also matches given keywords
        if preferred_keywords:
            deeper = _find_deeper_match(path, preferred_keywords, index)
            if deeper and len(deeper) > len(path):
                return {"resolved_path": deeper, "rejected": False, "rejection_reason": None}
        return {"resolved_path": path, "rejected": False, "rejection_reason": None}

    # Fuzzy match by token overlap
    best_score = 0.0
    best_key = None
    for key, path in index.items():
        key_tokens = _tokenize(key)
        if not key_tokens:
            continue
        overlap = len(candidate_tokens & key_tokens) / len(candidate_tokens | key_tokens)
        if overlap > best_score:
            best_score = overlap
            best_key = key

    if best_score > 0.3 and best_key:
        path = index[best_key]
        return {"resolved_path": path, "rejected": False, "rejection_reason": None}

    # Only top-level match (e.g. "Display" when we need "Display > Navigation bar")
    if preferred_keywords:
        deeper = _search_by_keywords(preferred_keywords, index)
        if deeper:
            parent_path = index.get(candidate_lower, [candidate])
            if len(deeper) > len(parent_path):
                return {
                    "resolved_path": deeper,
                    "rejected": True,
                    "rejection_reason": f"E310: parent_menu match rejected, resolved deeper to {' > '.join(deeper)}",
                }

    return {"resolved_path": [candidate], "rejected": False, "rejection_reason": None}


def _find_deeper_match(parent_path: list[str], keywords: list[str], index: dict) -> Optional[list[str]]:
    """Find a child path that matches the keywords better than the parent."""
    kw_tokens = set(w.lower() for kw in keywords for w in re.findall(r"\w+", kw))
    best_len = len(parent_path)
    best_path = None
    for key, path in index.items():
        if len(path) <= best_len:
            continue
        if not all(p in path for p in parent_path):
            continue
        key_tokens = _tokenize(key)
        if kw_tokens & key_tokens:
            best_len = len(path)
            best_path = path
    return best_path


def _search_by_keywords(keywords: list[str], index: dict) -> Optional[list[str]]:
    kw_tokens = set(w.lower() for kw in keywords for w in re.findall(r"\w+", kw))
    best_score = 0.0
    best_path = None
    for key, path in index.items():
        key_tokens = _tokenize(key)
        overlap = len(kw_tokens & key_tokens) / (len(kw_tokens | key_tokens) or 1)
        if overlap > best_score:
            best_score = overlap
            best_path = path
    return best_path if best_score > 0.2 else None


def is_parent_menu(candidate_path: list[str], target_path: list[str]) -> bool:
    """Return True if candidate is an ancestor of target."""
    if len(candidate_path) >= len(target_path):
        return False
    return target_path[:len(candidate_path)] == candidate_path
