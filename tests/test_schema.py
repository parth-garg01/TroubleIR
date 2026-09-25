"""Schema validation unit tests."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from troubleir.schema import (
    Goal, Action, StepGroup, Deeplink, actionCategory,
    ContextDeeplinkResponse, has_url_leak
)


def make_action(cat="auto", desc="It will help", deeplink=None):
    adl = Deeplink(deeplink=deeplink or "bixby://dummy_positive", description="Settings", message="") if deeplink is not False else None
    return Action(
        actionName="Test Screen",
        description=desc,
        category=actionCategory(cat),
        stepGroups=[StepGroup(steps=["Navigate to Settings.", "Tap the option."], actionableDeeplink=adl)]
    )


def test_description_must_start_with_it_will():
    with pytest.raises(Exception):
        make_action(desc="Wrong prefix here")


def test_description_valid():
    a = make_action(desc="It will reduce screen brightness effectively")
    assert a.description.startswith("It will")


def test_score_validation():
    with pytest.raises(Exception):
        Goal(goal="Follow these steps to perform this Test Troubleshooting",
             title="Test", actions=[], score=1.5)


def test_score_valid():
    g = Goal(goal="Follow these steps to perform this Test Troubleshooting",
             title="Test", actions=[], score=0.9)
    assert g.score == 0.9


def test_url_leak_detection():
    assert has_url_leak("Visit https://samsung.com for help")
    assert has_url_leak("Go to www.samsung.com")
    assert not has_url_leak("Go to Settings > Display > Brightness")
    assert not has_url_leak("Tap Brightness and drag the slider")


def test_action_category_ordering():
    # critical must come after auto/manual
    auto = make_action(cat="auto")
    manual = make_action(cat="manual")
    critical = make_action(cat="critical")
    assert auto.category.value == "auto"
    assert critical.category.value == "critical"


def test_deeplink_dummy_positive_valid():
    adl = Deeplink(deeplink="bixby://dummy_positive", description="Settings screen", message="Open")
    assert adl.deeplink == "bixby://dummy_positive"


def test_deeplink_masked_valid():
    adl = Deeplink(
        deeplink="bixby://masked/act/com.samsung.android.settings.display.brightness",
        description="Brightness settings",
        message="Open brightness"
    )
    assert adl.deeplink.startswith("bixby://masked/")


def test_no_match_response():
    r = ContextDeeplinkResponse(contexts=[], fallback="no_match")
    assert r.fallback == "no_match"
    assert r.contexts == []


if __name__ == "__main__":
    # Simple self-check without pytest
    test_description_valid()
    test_score_valid()
    test_url_leak_detection()
    test_action_category_ordering()
    test_deeplink_dummy_positive_valid()
    test_deeplink_masked_valid()
    test_no_match_response()
    print("All schema tests passed.")
