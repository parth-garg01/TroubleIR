"""Query enrichment: normalize + generate paraphrases for cache keying."""
import re
import json
import os
from typing import Tuple
from groq import Groq
from ..config import GROQ_API_KEY, MODEL_NAME, ENRICHMENT_VARIATIONS

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=GROQ_API_KEY or os.environ["GROQ_API_KEY"])
    return _client


_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.I)
_MARKDOWN_RE = re.compile(r"`[^`]+`|```[\s\S]*?```|\[([^\]]+)\]\([^\)]+\)")


def _scrub_urls(text: str) -> str:
    text = _URL_RE.sub("", text)
    text = _MARKDOWN_RE.sub(r"\1", text)
    return text.strip()


_ENRICH_PROMPT = """\
You are a Samsung Galaxy support assistant.

Given a user complaint, return a JSON object with:
1. "canonical": a normalized technical 5-10 word summary (no URLs, no markdown)
2. "variations": a list of exactly 10 distinct paraphrases covering:
   - formal technical phrasing
   - casual everyday language
   - keyword-only style
   - frustrated/emotional phrasing
   - typo-inclusive phrasing
   - question phrasing
   - short snippet style
   - regional/colloquial phrasing
   - context-rich phrasing
   - one alternative symptom description

Rules:
- No URLs, no markdown links, no web addresses in any field
- All text must be plain string content only
- Return only valid JSON, no commentary

User complaint: {query}"""


def enrich_query(query: str) -> Tuple[str, list[str]]:
    """Return (canonical_query, [10 paraphrase variations])."""
    prompt = _ENRICH_PROMPT.format(query=query)
    resp = _get_client().chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
        temperature=0.3,
    )
    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return query, []
    canonical = _scrub_urls(data.get("canonical", query))
    variations = [_scrub_urls(v) for v in data.get("variations", [])][:10]
    return canonical, variations
