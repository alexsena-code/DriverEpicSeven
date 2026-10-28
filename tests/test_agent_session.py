from io import StringIO
import json
from pathlib import Path
import time

import pytest

from driver_epic_seven.agent_session import parse_request, serve
from driver_epic_seven.cli import execute, parser
from driver_epic_seven.evidence import Evidence
from driver_epic_seven.observed_ui import build_tree
from driver_epic_seven.observer import SharedObserver, read_snapshot_file
from driver_epic_seven.runtime import Runtime


class FakeRuntime:
    read_snapshot = Runtime.read_snapshot
    primitive = Runtime.primitive

    def __init__(self, root):
        self.evidence = Evidence(root)
        self.observer = SharedObserver(self.evidence.write)
        self.state = "lobby"
        self.closed = 0
        self.calls = []
        self.tasker = type("Tasker", (), {"running": False})()
        self.window = {"hwnd": 1, "pid": 2, "process_name": "EpicSeven_Steam.exe",
                       "window_title": "Epic Seven", "window_class": "GLFW30",
                       "client_size": [1212, 682], "minimized": False}

    def guard(self, **kwargs):
        return dict(self.window)

    def observe(self, name="observation", **kwargs):
        self.calls.append((name, kwargs))
        self.observer.count("driver_captures")
        self.observer.count("recognitions")
        frame = self.evidence.path / f"{name}.png"
        frame.write_bytes(b"private test frame")
        data = {"state": self.state, "window": dict(self.window), "epoch_seconds": time.time(),
                "captured_at_epoch_seconds": time.time(), "frame": str(frame),
                "observation_file": str(self.evidence.path / f"{name}.json")}
        data["ui_tree"] = build_tree(data)
        self.evidence.write(name, data)
        self.observer.publish(data, "driver_observe")
        return data

    def run(self, routine):
        self.observe("before")
        self.observer.invalidate("pipeline_action_started")
        self.state = "orbis_guide"
        self.observe("pipeline")
        self.state = "lobby"
        self.observe("after")
        self.observer.event("routine_completed", routine=routine)
        return {"routine": routine, "completed": True, "after_state": self.state}

    def close(self):
        self.closed += 1
        self.observer.invalidate("disconnected")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def session(runtime, requests):
    output = StringIO()
    created = []
    def factory(config):
        created.append(config)
        return runtime
    serve({}, StringIO("\n".join(json.dumps(r) for r in requests)), output, factory)
    assert len(created) == 1 and runtime.closed == 1
    return [json.loads(line) for line in output.getvalue().splitlines()]


def test_persistent_protocol_reuses_one_runtime_and_snapshot_never_captures(tmp_path):
    runtime = FakeRuntime(tmp_path)
    messages = session(runtime, [
        {"id": 1, "args": ["snapshot"]},
        {"id": 2, "args": ["observe"]},
        {"id": 3, "args": ["snapshot", "--max-age-ms", "30000"]},
        {"id": 4, "args": ["snapshot", "--max-age-ms", "30000"]},
        {"id": 5, "args": ["disconnect"]},
    ])
    assert messages[0]["type"] == "ready" and not messages[0]["captures_started"]
    empty, observed, cached, cached_again = messages[1:5]
    assert empty["validity"]["reasons"] == ["no_snapshot"]
    assert observed["state"] == "lobby" and not observed["image"]["required"]
    assert observed["image"]["path"] is None
    assert cached["validity"]["valid"] and cached_again["validity"]["valid"]
    assert cached["snapshot_revision"] == observed["snapshot_revision"]
    assert cached["events"] == cached_again["events"] == []
    assert len(runtime.calls) == cached_again["metrics"]["driver_captures"] == 1
    assert messages[-1] == {"id": 5, "type": "disconnected", "ok": True}
    assert "disconnected" in read_snapshot_file(messages[0]["observer_file"])["validity"]["reasons"]


def test_invalid_arguments_preserve_id_and_do_not_dispatch(tmp_path):
    runtime = FakeRuntime(tmp_path)
    messages = session(runtime, [
        {"id": "bad-click", "args": ["click", "--x", "1080", "--y", "630"]},
        {"id": "next-observation", "args": ["observe"]},
        {"id": "end", "args": ["disconnect"]},
    ])
    rejected = messages[1]
    assert rejected["id"] == "bad-click" and rejected["ok"] is False
    assert rejected["operation"] is None
    assert rejected["metrics"]["driver_captures"] == 0
    assert messages[2]["id"] == "next-observation" and messages[2]["ok"]
    assert len(runtime.calls) == 1


def test_projection_preserves_unknowns_and_canonical_provenance_without_embedding_frame(tmp_path):
    runtime = FakeRuntime(tmp_path)
    response = session(runtime, [{"args": ["observe"]}])[1]
    artifact = json.loads(Path(response["evidence"]["response_file"]).read_text(encoding="utf-8"))
    tree = artifact["snapshot"]["snapshot"]["ui_tree"]
    assert response["ui"]["observation_id"] == tree["observation_id"]
    for row in response["ui"]["nodes"]:
        assert row["fields"]["enabled"] is None
        for field, value in row["fields"].items():
            assert value == tree["nodes"][row["id"]]["fields"][field]["value"]
    assert tree["nodes"]["screen"]["fields"]["status"]["sources"]
    assert "private test frame" not in json.dumps(response)
    assert "ui_tree" not in response and response["requires_current_action_guards"]


def test_unknown_and_requested_images_are_explicit_and_preserved(tmp_path):
    runtime = FakeRuntime(tmp_path)
    runtime.state = "unknown"
    response = session(runtime, [{"args": ["observe"], "inspect_image": True}])[1]
    assert response["image"]["required"] and response["image"]["available"]
    assert response["image"]["reasons"] == ["unknown_screen", "requested_visual_inspection"]
    image = Path(response["image"]["path"])
    (runtime.evidence.path / "observation.png").write_bytes(b"later frame")
    assert image.read_bytes() == b"private test frame"


def test_dispatch_still_reobserves_and_rejects_unknown_target_without_retry(tmp_path):
    runtime = FakeRuntime(tmp_path)
    def requests():
        yield json.dumps({"id": 1, "args": ["observe"]}) + "\n"
        runtime.state = "unknown"
        yield json.dumps({"id": 2, "args": ["click", "--target", "orbis_button"]}) + "\n"
    output = StringIO()
    serve({}, requests(), output, lambda config: runtime)
    responses = [json.loads(line) for line in output.getvalue().splitlines()]
    assert [name for name, kwargs in runtime.calls] == ["observation", "before"]
    assert not responses[-1]["ok"]
    assert "Tela desconhecida" in responses[-1]["error"]
    assert "agent_command_failed" in responses[-1]["validity"]["reasons"]
    assert responses[-1]["image"]["required"]


def test_pipeline_transitions_reported_and_next_command_stays_in_same_session(tmp_path):
    runtime = FakeRuntime(tmp_path)
    messages = session(runtime, [{"args": ["run", "orbis_roundtrip"]}, {"args": ["observe"]}])
    report = messages[1]
    assert report["operation"]["completed"] and report["state"] == "lobby"
    assert any(e.get("after_state") == "orbis_guide" for e in report["events"])
    assert any(e["kind"] == "routine_completed" for e in report["events"])
    assert messages[2]["events"] == []


def test_expired_and_changed_window_remain_invalid_without_extra_capture(tmp_path):
    runtime = FakeRuntime(tmp_path)
    def requests():
        yield json.dumps({"args": ["observe"]}) + "\n"
        runtime.observer._latest["captured_at_epoch_seconds"] = time.time() - 31
        yield json.dumps({"args": ["snapshot"]}) + "\n"
        runtime.window["pid"] = 999
        yield json.dumps({"args": ["snapshot"]}) + "\n"
    output = StringIO()
    serve({}, requests(), output, lambda config: runtime)
    messages = [json.loads(line) for line in output.getvalue().splitlines()]
    assert "expired_or_clock_changed" in messages[2]["validity"]["reasons"]
    assert "window_changed" in messages[3]["validity"]["reasons"]
    assert len(runtime.calls) == 1


@pytest.mark.parametrize("cursor_args", [["--after-sequence", "0"], ["--after-sequence=0"]])
def test_explicit_event_cursor_can_replay_history(tmp_path, cursor_args):
    runtime = FakeRuntime(tmp_path)
    messages = session(runtime, [{"args": ["observe"]}, {"args": ["snapshot", *cursor_args]}])
    assert messages[2]["events"] == messages[1]["events"]


def test_malformed_request_recovers_and_eof_closes(tmp_path):
    runtime = FakeRuntime(tmp_path)
    output = StringIO()
    serve({}, StringIO('{"args":null}\n{"id":2,"args":["observe"]}\n'), output, lambda config: runtime)
    messages = [json.loads(line) for line in output.getvalue().splitlines()]
    assert not messages[1]["ok"] and messages[2]["ok"]
    assert len(runtime.calls) == 1 and runtime.closed == 1


@pytest.mark.parametrize("payload", [
    {"args": ["--config", "other.json", "observe"]}, {"args": ["agent"]},
    {"args": ["snapshot", "--file", "other.json"]}, {"args": ["unknown-command"]},
    {"args": ["observe"], "inspect_image": "yes"}, {"args": "observe; shell"},
])
def test_requests_cannot_reconnect_change_config_or_evaluate_shell(payload):
    with pytest.raises(ValueError):
        parse_request(json.dumps(payload))


def test_independent_snapshot_still_requires_explicit_file():
    with pytest.raises(ValueError, match="exige --file"):
        execute(parser().parse_args(["snapshot"]))
