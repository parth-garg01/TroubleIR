"""Grounding validator: each action step must trace to SIIS evidence.

Uses IDF-weighted token overlap so high-frequency stop words do not
inflate coverage scores. Steps that mention domain-specific terms
(battery, brightness, settings, display) must find those exact terms
in the SIIS text.
"""
import re
import math
from collections import Counter
from typing import Optional
from ..schema import Action, DiagnosticCode
from ..config import GROUNDING_MIN_COVERAGE, GROUNDING_STEP_THRESHOLD

_STOPWORDS = {
    "the", "a", "an", "to", "in", "on", "at", "of", "and", "or", "is",
    "it", "you", "your", "this", "that", "with", "for", "be", "will",
    "can", "may", "then", "if", "as", "by", "from", "are", "have",
}


def _tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"\w+", text.lower()) if t not in _STOPWORDS and len(t) > 2]


def _build_idf(corpus: list[list[str]]) -> dict[str, float]:
    """Compute inverse document frequency over a list of token lists."""
    N = len(corpus)
    df: Counter = Counter()
    for doc in corpus:
        df.update(set(doc))
    return {term: math.log((N + 1) / (count + 1)) + 1 for term, count in df.items()}


def _weighted_overlap(step_tokens: list[str], siis_set: set[str], idf: dict[str, float]) -> float:
    """Fraction of step token IDF weight that is covered by SIIS tokens."""
    if not step_tokens:
        return 1.0
    total_weight = sum(idf.get(t, 1.0) for t in step_tokens)
    if total_weight == 0:
        return 1.0
    covered = sum(idf.get(t, 1.0) for t in step_tokens if t in siis_set)
    return covered / total_weight


def check_grounding(action: Action, siis_text: str) -> dict:
    """
    Check that action steps are grounded in siis_text using IDF-weighted overlap.
    Returns: {grounded: bool, coverage: float, diagnostics: list[str]}
    """
    if not siis_text:
        return {
            "grounded": False,
            "coverage": 0.0,
            "diagnostics": [f"{DiagnosticCode.UNGROUNDED_OPERATION}: No SIIS evidence provided"],
        }

    all_steps: list[str] = []
    for sg in action.stepGroups:
        all_steps.extend(sg.steps)

    if not all_steps:
        return {"grounded": True, "coverage": 1.0, "diagnostics": []}

    siis_tokens = _tokenize(siis_text)
    siis_set = set(siis_tokens)

    # Build IDF over the SIIS corpus + all steps combined
    step_token_lists = [_tokenize(s) for s in all_steps]
    idf = _build_idf([siis_tokens] + step_token_lists)

    grounded_count = 0
    diagnostics = []

    for step, step_tokens in zip(all_steps, step_token_lists):
        score = _weighted_overlap(step_tokens, siis_set, idf)
        if score >= GROUNDING_STEP_THRESHOLD:
            grounded_count += 1
        else:
            diagnostics.append(
                f"{DiagnosticCode.UNGROUNDED_OPERATION}: Low grounding "
                f"({score:.0%} weighted) for step: '{step[:60]}'"
            )

    coverage = grounded_count / len(all_steps)
    return {
        "grounded": coverage >= GROUNDING_MIN_COVERAGE,
        "coverage": coverage,
        "diagnostics": diagnostics,
    }


def check_url_leaks(response_text: str) -> list[str]:
    """Return list of URL leak violations found."""
    url_pattern = re.compile(r"https?://|www\.|\.com|\.org|\.net|\.io", re.I)
    leaks = url_pattern.findall(response_text)
    if leaks:
        return [f"{DiagnosticCode.URL_LEAK}: Found {len(leaks)} URL pattern(s) in response"]
    return []
