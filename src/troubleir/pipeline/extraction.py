"""Structure extraction: LLM extracts Goal/Actions from SIIS evidence."""
import json
import re
import os
from typing import Optional
from groq import Groq

from ..schema import (
    ContextDeeplinkResponse,
    Goal,
    Action,
    StepGroup,
    Deeplink,
    ValidationDeepLink,
    actionCategory,
    has_url_leak,
)

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=os.environ["GROQ_API_KEY"])
    return _client


_EXTRACT_PROMPT = """\
You are a Samsung Galaxy support expert. Extract a structured troubleshooting plan.

USER COMPLAINT: {query}

REFERENCE TEXT (SIIS knowledge base):
{siis_text}

AVAILABLE DEEPLINKS (use description/message fields to match, never invent deeplinks):
{deeplink_catalog}

OUTPUT RULES - follow exactly:
1. Return only valid JSON, no markdown fences, no commentary, no URLs
2. goal: exact syntax "Follow these steps to perform this <Topic> Troubleshooting" OR "Follow these steps to perform this <Topic> Configuration"
3. title: 2-3 words, sentence case, identifying the core issue
4. score: float 0.0-1.0 representing confidence
5. actionName: Title Case, represents exactly ONE physical screen
6. description: exactly 5-7 words starting with "It will" explaining the benefit
7. steps: clear imperative UI steps, one physical interaction each, NO URLs, NO external links
8. category: "auto" for standard settings screens, "manual" for physical actions, "critical" for destructive/irreversible operations
9. actionableDeeplink: use ONLY deeplinks from the catalog above matching the screen. Use "voiceassist://dummy_positive" for valid settings screens not in the catalog. Use null for manual/physical actions.
10. Order actions: least disruptive first, critical/destructive LAST
11. NO web URLs anywhere in output
12. stepGroups: group steps that occur on the SAME screen into one StepGroup

Return a single JSON object:
{{
  "goal": "...",
  "title": "...",
  "score": 0.0,
  "actions": [
    {{
      "actionName": "...",
      "description": "It will ...",
      "category": "auto|manual|critical",
      "stepGroups": [
        {{
          "steps": ["...", "..."],
          "actionableDeeplink": {{"deeplink": "voiceassist://masked/act/...", "description": "...", "message": "..."}} or null,
          "validationDeeplink": null
        }}
      ]
    }}
  ]
}}"""


def _find_best_deeplink(action_name: str, steps: list[str], catalog: list[dict]) -> Optional[dict]:
    combined = (action_name + " " + " ".join(steps)).lower()
    best_score = 0
    best_entry = None
    for entry in catalog:
        desc_words = set(re.findall(r"\w+", (entry.get("description", "") + " " + entry.get("qna_description", "")).lower()))
        query_words = set(re.findall(r"\w+", combined))
        if not desc_words:
            continue
        overlap = len(desc_words & query_words) / len(desc_words | query_words)
        if overlap > best_score:
            best_score = overlap
            best_entry = entry
    return best_entry if best_score > 0.08 else None


def _scrub_url_leaks(obj):
    if isinstance(obj, str):
        if has_url_leak(obj):
            return re.sub(r"https?://\S+|www\.\S+", "", obj).strip()
        return obj
    if isinstance(obj, list):
        return [_scrub_url_leaks(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _scrub_url_leaks(v) for k, v in obj.items()}
    return obj


def extract_plan(
    query: str,
    siis_text: str,
    deeplink_catalog: list[dict],
) -> Optional[ContextDeeplinkResponse]:
    catalog_summary = json.dumps(
        [{"deeplink": d["deeplink"], "description": d["description"], "message": d.get("message", "")}
         for d in deeplink_catalog[:30]],
        indent=2
    )
    prompt = _EXTRACT_PROMPT.format(
        query=query,
        siis_text=siis_text[:3000],
        deeplink_catalog=catalog_summary,
    )
    resp = _get_client().chat.completions.create(
        model=os.environ.get("MODEL_NAME", "llama-3.3-70b-versatile"),
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2500,
        temperature=0.1,
    )
    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None

    data = _scrub_url_leaks(data)

    allowed_deeplinks = {d["deeplink"] for d in deeplink_catalog}
    dummy = "voiceassist://dummy_positive"

    actions = []
    for act_data in data.get("actions", []):
        step_groups = []
        for sg_data in act_data.get("stepGroups", []):
            adl = sg_data.get("actionableDeeplink")
            matched_entry = None
            if adl and isinstance(adl, dict):
                dl_str = adl.get("deeplink", "")
                if dl_str in allowed_deeplinks:
                    # Find the catalog entry to get its validation deeplink
                    matched_entry = next((d for d in deeplink_catalog if d["deeplink"] == dl_str), None)
                elif dl_str != dummy:
                    matched_entry = _find_best_deeplink(
                        act_data.get("actionName", ""),
                        sg_data.get("steps", []),
                        deeplink_catalog
                    )
                    if matched_entry:
                        adl = {"deeplink": matched_entry["deeplink"], "description": matched_entry["description"], "message": matched_entry.get("message", "")}
                    else:
                        adl = {"deeplink": dummy, "description": act_data.get("actionName", "Settings screen"), "message": "Open this settings screen"}
                actionable_deeplink = Deeplink(**adl)
            else:
                actionable_deeplink = None

            # Populate validationDeeplink from catalog entry if available
            validation_deeplink = None
            if matched_entry and matched_entry.get("validation"):
                v = matched_entry["validation"]
                validation_deeplink = ValidationDeepLink(deeplink=v["deeplink"], key=v["key"])

            step_groups.append(StepGroup(
                steps=sg_data.get("steps", []),
                actionableDeeplink=actionable_deeplink,
                validationDeeplink=validation_deeplink,
            ))

        cat_str = act_data.get("category", "auto")
        try:
            cat = actionCategory(cat_str)
        except ValueError:
            cat = actionCategory.auto

        desc = act_data.get("description", "It will help resolve this issue")
        if not desc.startswith("It will"):
            desc = "It will " + desc.lstrip()

        actions.append(Action(
            actionName=act_data.get("actionName", "Settings"),
            description=desc,
            stepGroups=step_groups,
            category=cat,
        ))

    order = {"auto": 0, "manual": 1, "critical": 2}
    actions.sort(key=lambda a: order.get(a.category.value if a.category else "auto", 1))

    goal = Goal(
        goal=data.get("goal", "Follow these steps to perform this Troubleshooting"),
        title=data.get("title", "Device issue"),
        actions=actions,
        score=min(1.0, max(0.0, float(data.get("score", 0.8)))),
    )
    return ContextDeeplinkResponse(contexts=[goal])
