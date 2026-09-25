"""Output linter tests."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from troubleir.compiler.lint import lint_response
from troubleir.schema import ContextDeeplinkResponse, Goal, Action, StepGroup, Deeplink, actionCategory


def _clean_response():
    return ContextDeeplinkResponse(contexts=[
        Goal(
            goal="Follow these steps to perform this Battery Troubleshooting",
            title="Battery drain",
            score=0.85,
            actions=[
                Action(
                    actionName="Battery Settings",
                    description="It will show battery usage by app",
                    category=actionCategory.auto,
                    stepGroups=[StepGroup(
                        steps=["Go to Settings.", "Tap Battery and device care.", "Tap Battery."],
                        actionableDeeplink=Deeplink(
                            deeplink="bixby://masked/act/com.samsung.android.settings.battery.usage",
                            description="Battery usage details",
                            message="Open battery usage"
                        )
                    )]
                ),
                Action(
                    actionName="Reset Settings",
                    description="It will restore all settings to default",
                    category=actionCategory.critical,
                    stepGroups=[StepGroup(
                        steps=["Go to Settings.", "Tap General management.", "Tap Reset."],
                        actionableDeeplink=Deeplink(deeplink="bixby://dummy_positive", description="Reset", message="")
                    )]
                )
            ]
        )
    ])


def test_clean_response_passes():
    r = _clean_response()
    passed, violations = lint_response(r)
    assert passed, f"Expected clean response to pass lint. Got: {violations}"


def test_url_leak_fails():
    r = _clean_response()
    r.contexts[0].actions[0].stepGroups[0].steps = [
        "Go to https://samsung.com/support for help"
    ]
    passed, violations = lint_response(r)
    assert not passed
    assert any("URL" in v for v in violations)


def test_wrong_ordering_fails():
    # critical before auto is a violation
    r = _clean_response()
    # Swap order to put critical first
    r.contexts[0].actions = list(reversed(r.contexts[0].actions))
    passed, violations = lint_response(r)
    assert not passed
    assert any("ordering" in v.lower() for v in violations)


def test_no_match_skips_lint():
    r = ContextDeeplinkResponse(contexts=[], fallback="no_match")
    passed, violations = lint_response(r)
    assert passed
    assert violations == []


if __name__ == "__main__":
    test_clean_response_passes()
    print("  Clean response: PASS")
    test_url_leak_fails()
    print("  URL leak detection: PASS")
    test_wrong_ordering_fails()
    print("  Ordering violation: PASS")
    test_no_match_skips_lint()
    print("  No-match skip: PASS")
    print("All lint tests passed.")
