"""Output linter: validate schema compliance before response delivery."""
import json
import re
from typing import Tuple
from ..schema import ContextDeeplinkResponse, TroubleshootResponse, has_url_leak, DiagnosticCode


def lint_response(response: ContextDeeplinkResponse) -> Tuple[bool, list[str]]:
    """
    Run compliance checks on a response. Returns (passed, [violations]).
    Violations are internal diagnostic codes, not surfaced to user.
    """
    violations = []
    raw = json.dumps(response.model_dump())

    # URL leak check
    if has_url_leak(raw):
        violations.append(f"{DiagnosticCode.URL_LEAK}: URL pattern detected in response body")

    for goal in response.contexts:
        # Schema field presence
        if not goal.goal.startswith("Follow these steps"):
            violations.append(f"{DiagnosticCode.SCHEMA_FAILURE}: goal field syntax incorrect: '{goal.goal[:60]}'")

        if not (0.0 <= goal.score <= 1.0):
            violations.append(f"{DiagnosticCode.SCHEMA_FAILURE}: score out of range: {goal.score}")

        for action in goal.actions:
            if not action.description.startswith("It will"):
                violations.append(f"{DiagnosticCode.SCHEMA_FAILURE}: description must start with 'It will': '{action.description[:50]}'")

            if not action.stepGroups:
                violations.append(f"{DiagnosticCode.SCHEMA_FAILURE}: action '{action.actionName}' has no stepGroups")

            for sg in action.stepGroups:
                if not sg.steps:
                    violations.append(f"{DiagnosticCode.SCHEMA_FAILURE}: stepGroup has no steps")

                if sg.actionableDeeplink:
                    dl = sg.actionableDeeplink.deeplink
                    if not dl.startswith("voiceassist://"):
                        violations.append(f"{DiagnosticCode.INVALID_DEEPLINK}: Invalid deeplink URI: {dl}")

        # Ordering check: critical actions must be last
        categories = [a.category.value if a.category else "auto" for a in goal.actions]
        order_map = {"auto": 0, "manual": 1, "critical": 2}
        order_vals = [order_map.get(c, 0) for c in categories]
        for i in range(len(order_vals) - 1):
            if order_vals[i] > order_vals[i + 1]:
                violations.append(
                    f"{DiagnosticCode.SCHEMA_FAILURE}: Action ordering violation - '{categories[i]}' before '{categories[i+1]}' at position {i}"
                )

    return len(violations) == 0, violations
