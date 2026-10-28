from types import SimpleNamespace

import pytest

from driver_epic_seven.runtime import Runtime
from driver_epic_seven.quests import navigation_context


def key_runtime(state):
    runtime = object.__new__(Runtime)
    runtime.vision = SimpleNamespace(spec={"states": {"lobby": {}, "quick_menu": {}}})
    runtime.observe = lambda name: {"state": state, "epoch_seconds": 1000,
                                   "window": {"client_size": [1212, 682]}}
    runtime.guard = lambda **kwargs: None
    runtime.calls = []
    def post_action(name, params):
        runtime.calls.append((name, params))
        return SimpleNamespace(succeeded=True)
    runtime.tasker = SimpleNamespace(post_action=post_action)
    runtime.ctrl = SimpleNamespace(post_click_key=lambda *a: pytest.fail("Unbounded ClickKey path must not be used"))
    runtime.wait = lambda job: job
    runtime.wait_state = lambda state: {"state": state, "epoch_seconds": 1001,
                                       "window": {"client_size": [1212, 682]}}
    runtime.evidence = SimpleNamespace(path="test", write=lambda *args: None)
    return runtime


def test_tab_uses_one_bounded_native_press_and_checks_destination():
    runtime = key_runtime("quick_menu")
    result = runtime.primitive("key", key="tab", from_state="quick_menu", expect="lobby")
    assert len(runtime.calls) == 1
    name, params = runtime.calls[0]
    assert name == "LongPressKey" and params.key == [9] and params.duration == 100
    assert result["postcondition_verified"] and result["after_state"] == "lobby"
    assert result["duration_ms"] == 100


@pytest.mark.parametrize("state,key", [("chat_panel", "c"), ("chat_notifications", "g"),
                                      ("battle_running", "tab"), ("story_confirmation", "1"),
                                      ("lobby", "enter")])
def test_navigation_key_guards_reject_before_any_input(state, key):
    runtime = key_runtime(state)
    with pytest.raises(ValueError):
        runtime.primitive("key", key=key, from_state=state)
    assert runtime.calls == []


@pytest.mark.parametrize("state,kind", [("battle_categories", "battle_categories"),
                                      ("hero_screen", "hero_menu"),
                                      ("options_screen", "settings_menu"),
                                      ("quick_menu", "navigation_menu")])
def test_navigation_menu_never_becomes_verified_battle_from_catalog_data(state, kind):
    result = navigation_context({"state": state, "stage": {
        "identity_verified": True, "requested_id": "pen002", "expected_energy": 8,
        "energy": {"cost": 8, "available": 1000}}})
    assert result["kind"] == kind
    assert not result["battle_identity_verified"] and not result["cost_verified"]
    assert result["stage_id"] is None
