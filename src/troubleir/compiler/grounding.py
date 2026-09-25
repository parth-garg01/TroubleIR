"""Grounding validator: each action step must trace to source SIIS evidence."""
import re
from typing import Optional
from ..schema import Action, DiagnosticCode


def _tokenize(text: str) -> set[str]:
    stopwords = {"the", "a", "an", "to", "in", "on", "at", "of", "and", "or", "is", "it", "you", "your"}
    return set(re.findall(r"\w+", text.lower())) - stopwords


def _sentence_split(text: str) -> list[str]:
    return re.split(r"(?<=[.!?])\s+", text.strip())


def check_grounding(action: Action, siis_text: str) -> dict:
    """
    Check if action steps have grounding in siis_text.
    Returns: {grounded: bool, coverage: float, diagnostics: list[str]}
    """
    if not siis_text:
        return {"grounded": False, "coverage": 0.0, "diagnostics": [f"{DiagnosticCode.UNGROUNDED_OPERATION}: No SIIS evidence provided"]}

    siis_tokens = _tokenize(siis_text)
    all_steps = []
    for sg in action.stepGroups:
        all_steps.extend(sg.steps)

    if not all_steps:
        return {"grounded": True, "coverage": 1.0, "diagnostics": []}

    grounded_count = 0
    diagnostics = []

    for step in all_steps:
        step_tokens = _tokenize(step)
        if not step_tokens:
            grounded_count += 1
            continue
        overlap = len(step_tokens & siis_tokens) / len(step_tokens)
        if overlap >= 0.3:
            grounded_count += 1
        else:
            diagnostics.append(f"{DiagnosticCode.UNGROUNDED_OPERATION}: Low grounding ({overlap:.0%}) for step: '{step[:60]}'")

    coverage = grounded_count / len(all_steps)
    return {
        "grounded": coverage >= 0.6,
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
