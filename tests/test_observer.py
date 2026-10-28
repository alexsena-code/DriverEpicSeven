from copy import deepcopy
import time
from types import SimpleNamespace

import pytest

from driver_epic_seven.observer import SharedObserver, read_snapshot_file
from driver_epic_seven.observed_ui import build_tree, fact
from driver_epic_seven.runtime import Runtime


def observation(state="lobby", captured=1000):
    data = {"state": state, "epoch_seconds": 1000, "window": {
        "hwnd": 1, "pid": 2, "process_name": "EpicSeven_Steam.exe", "window_title": "Epic Seven",
        "window_class": "GLFW30", "client_size": [1212, 682], "minimized": False}}
    if captured is not None:
        data["captured_at_epoch_seconds"] = captured
    data["ui_tree"] = build_tree(data)
    return data


def test_cache_owns_copy_and_only_semantic_changes_emit_events():
    observer = SharedObserver()
    first = observation()
    observer.publish(first, "driver_observe")
    first["ui_tree"]["nodes"]["screen"]["fields"]["match_score"] = fact(.98, {"kind": "recognition", "pointer": "/matches/test"})
    observer.publish(first, "driver_observe")
    snapshot = observer.snapshot(now=1000.1)
    assert snapshot["validity"]["valid"]
    assert snapshot["snapshot_revision"] == 2
    assert len(snapshot["events"]) == 1
    snapshot["snapshot"]["ui_tree"]["nodes"].clear()
    assert observer.snapshot(now=1000.1)["snapshot"]["ui_tree"]["nodes"]
    observer.publish(observation("orbis_guide"), "maa_pipeline")
    changes = observer.snapshot(after_sequence=1, now=1000.1)["events"]
    assert len(changes) == 1 and changes[0]["after_state"] == "orbis_guide"


def test_export_reader_recomputes_age_instead_of_trusting_saved_validity(tmp_path):
    import json
    observer = SharedObserver()
    observer.publish(observation(), "driver_observe")
    saved = observer.snapshot(now=1000.1)
    assert saved["validity"]["valid"]
    path = tmp_path / "observer.json"
    path.write_text(json.dumps(saved), encoding="utf-8")
    assert not read_snapshot_file(path, now=1001)["validity"]["valid"]
    observer.invalidate("disconnected")
    path.write_text(json.dumps(observer.snapshot(now=1000.1)), encoding="utf-8")
    assert "disconnected" in read_snapshot_file(path, now=1000.1)["validity"]["reasons"]


def test_expired_missing_capture_time_and_invalidated_are_not_fresh():
    observer = SharedObserver()
    observer.publish(observation(), "driver_observe")
    assert not observer.snapshot(now=1001)["validity"]["valid"]
    assert not observer.snapshot(now=999)["validity"]["valid"]
    observer.invalidate("primitive_action_started")
    assert "primitive_action_started" in observer.snapshot(now=1000.1)["validity"]["reasons"]
    observer.publish(observation(captured=None), "maa_pipeline")
    assert observer.snapshot(now=1000.1)["validity"]["reasons"] == ["capture_time_unknown"]


def test_window_identity_size_and_minimization_invalidate_read():
    observer = SharedObserver()
    data = observation()
    observer.publish(data, "driver_observe")
    for key, value in (("pid", 9), ("client_size", [1280, 720]), ("minimized", True)):
        window = {**data["window"], key: value}
        assert "window_changed" in observer.snapshot(window=window, now=1000.1)["validity"]["reasons"]


def test_late_callback_cannot_make_disconnected_snapshot_current():
    observer = SharedObserver()
    observer.publish(observation(), "driver_observe")
    observer.invalidate("disconnected")
    observer.publish(observation("orbis_guide"), "maa_pipeline")
    observer.invalidate("pipeline_action_started")
    snapshot = observer.snapshot(now=1000.1)
    assert snapshot["snapshot_revision"] == 1
    assert snapshot["validity"]["reasons"] == ["disconnected"]


def test_event_history_is_bounded_and_reports_lost_cursor():
    observer = SharedObserver()
    for i in range(70):
        observer.event("test", index=i)
    snapshot = observer.snapshot()
    assert len(snapshot["events"]) == 64 and snapshot["history_lost"]
    assert not observer.snapshot(after_sequence=69)["history_lost"]
    assert len(observer.snapshot(after_sequence=69)["events"]) == 1


def test_fresh_runtime_query_reuses_tree_without_capture():
    runtime = object.__new__(Runtime)
    runtime.observer = SharedObserver()
    data = observation(captured=time.time())
    runtime.observer.publish(data, "driver_observe")
    runtime.guard = lambda: data["window"]
    runtime.observe = lambda *args: pytest.fail("cache query must not capture")
    assert runtime.read_snapshot()["validity"]["valid"]
    assert runtime.observer.metrics["cache_hits"] == 1


def test_pipeline_busy_does_not_start_competing_capture():
    runtime = object.__new__(Runtime)
    runtime.observer = SharedObserver()
    runtime.guard = lambda: observation()["window"]
    runtime.tasker = SimpleNamespace(running=True)
    runtime.observe = lambda *args: pytest.fail("pipeline already owns capture")
    assert not runtime.read_snapshot(refresh=False)["validity"]["valid"]
    with pytest.raises(RuntimeError, match="Pipeline ativo"):
        runtime.read_snapshot()


def test_refresh_and_primitive_keep_current_observation_guards():
    runtime = object.__new__(Runtime)
    runtime.observer = SharedObserver()
    old = observation(captured=time.time() - 10)
    runtime.observer.publish(old, "driver_observe")
    runtime.guard = lambda **kwargs: old["window"]
    runtime.tasker = SimpleNamespace(running=False)
    calls = []
    def fresh(name):
        calls.append(name)
        current = observation("unknown", captured=time.time())
        runtime.observer.publish(current, "driver_observe")
        return current
    runtime.observe = fresh
    assert runtime.read_snapshot()["validity"]["valid"]
    assert calls == ["observer_refresh"]
    runtime.ctrl = SimpleNamespace(post_click=lambda *args: pytest.fail("must not click stale target"))
    with pytest.raises(ValueError, match="Tela desconhecida"):
        runtime.primitive("click", target="orbis_button")
    assert calls == ["observer_refresh", "before"]
