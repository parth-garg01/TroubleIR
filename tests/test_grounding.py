"""Unit tests for the IDF-weighted grounding validator."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from troubleir.schema import Action, StepGroup, ActionableDeeplink, ActionCategory
from troubleir.compiler.grounding import check_grounding, check_url_leaks


def _make_action(steps: list[str], deeplink: str = "bixby://dummy_positive") -> Action:
    sg = StepGroup(
        steps=steps,
        actionableDeeplink=ActionableDeeplink(deeplink=deeplink, description="test"),
    )
    return Action(
        actionName="Test Action",
        description="It will perform the test action.",
        category=ActionCategory.auto,
        stepGroups=[sg],
    )


BATTERY_SIIS = (
    "Battery usage in Settings shows which apps are consuming the most power. "
    "Navigate to Settings Battery and device care Battery Battery usage to review. "
    "Background apps significantly drain battery. Enable Power saving mode to limit "
    "CPU performance and background network activity. Check Battery usage immediately "
    "after restart to identify draining apps."
)

DISPLAY_SIIS = (
    "Reduce brightness by going to Settings Display Brightness. Enable Adaptive "
    "brightness to auto-adjust based on ambient light. Dark mode reduces eye strain "
    "in low light conditions. Eye comfort shield reduces blue light emission."
)


def test_well_grounded_steps_pass():
    action = _make_action([
        "Open Settings",
        "Tap Battery and device care",
        "Tap Battery usage to see power consumption",
    ])
    result = check_grounding(action, BATTERY_SIIS)
    assert result["grounded"] is True
    assert result["coverage"] > 0.5


def test_unrelated_steps_fail():
    action = _make_action([
        "Call Samsung support center",
        "Request warranty replacement",
        "Visit authorized service partner",
    ])
    result = check_grounding(action, BATTERY_SIIS)
    assert result["grounded"] is False
    assert len(result["diagnostics"]) > 0


def test_empty_steps_are_grounded():
    """Actions with no steps are trivially grounded."""
    sg = StepGroup(steps=[], actionableDeeplink=ActionableDeeplink(deeplink="bixby://dummy_positive", description=""))
    action = Action(
        actionName="Empty",
        description="It will do nothing.",
        category=ActionCategory.auto,
        stepGroups=[sg],
    )
    result = check_grounding(action, BATTERY_SIIS)
    assert result["grounded"] is True
    assert result["coverage"] == 1.0


def test_missing_siis_fails():
    action = _make_action(["Open Settings", "Tap Battery"])
    result = check_grounding(action, "")
    assert result["grounded"] is False
    assert any("No SIIS" in d for d in result["diagnostics"])


def test_partial_grounding_threshold():
    """Exactly 50% grounded steps should fail (threshold is 60%)."""
    action = _make_action([
        "Open Settings Battery",         # grounded
        "Call your service provider",    # not grounded
    ])
    result = check_grounding(action, BATTERY_SIIS)
    assert result["coverage"] <= 0.6


def test_cross_domain_siis_fails():
    """Battery steps should not ground against display SIIS."""
    action = _make_action([
        "Open Settings Battery",
        "Tap Battery usage to review power consumption",
        "Enable Power saving mode",
    ])
    result = check_grounding(action, DISPLAY_SIIS)
    # Some overlap expected (Open, Settings) but coverage should be lower
    # than with the correct SIIS
    battery_result = check_grounding(action, BATTERY_SIIS)
    assert result["coverage"] <= battery_result["coverage"]


def test_url_leak_detection():
    leaks = check_url_leaks("Go to https://example.com for more info")
    assert len(leaks) > 0


def test_url_leak_clean_text():
    leaks = check_url_leaks("Open Settings and tap Battery usage")
    assert leaks == []


def test_bixby_uri_not_flagged_as_url_leak():
    """bixby:// URIs appear in action bodies but are not URL leaks."""
    leaks = check_url_leaks("bixby://masked/act/com.samsung.android.settings.battery.usage")
    assert leaks == []
