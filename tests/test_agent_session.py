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
    assert [event['kind'] for event in messages[2]['events']] == ['execution_started', 'execution_finished']


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


def test_async_jsonl_consults_and_cancels_during_blocked_application(tmp_path, monkeypatch):
    from threading import Event
    from driver_epic_seven.application import Application
    from driver_epic_seven.contracts import Identity
    runtime = FakeRuntime(tmp_path)
    started, release = Event(), Event()
    identity = Identity().as_dict()
    def blocking_execute(self, request, rt):
        runtime.execution_dispatched = True
        started.set()
        assert release.wait(3)
        return {'completed': False, 'execution': {'status': 'uncertain', 'identity': request.identity.as_dict()}}
    monkeypatch.setattr(Application, 'execute', blocking_execute)
    runtime.cancel_execution = release.set
    original_guard = runtime.guard
    def guard(**kwargs):
        assert not started.is_set() or release.is_set(), 'Consultation called window guard while busy'
        return original_guard(**kwargs)
    runtime.guard = guard
    def requests():
        yield json.dumps({'id': 'long', 'args': ['run', 'orbis_roundtrip'], 'identity': identity, 'async': True})
        assert started.wait(1)
        yield json.dumps({'id': 'status', 'args': ['status']})
        yield json.dumps({'id': 'events', 'args': ['events', '--after-sequence', '0']})
        yield json.dumps({'id': 'snapshot', 'args': ['snapshot']})
        yield json.dumps({'id': 'second', 'args': ['observe'], 'async': True})
        yield json.dumps({'id': 'cancel', 'args': ['cancel']})
        yield json.dumps({'id': 'end', 'args': ['disconnect']})
    output = StringIO()
    serve({}, requests(), output, lambda config: runtime)
    messages = {m['id']: m for m in map(json.loads, output.getvalue().splitlines()) if 'id' in m}
    assert messages['long']['session_execution']['identity'] == identity
    assert messages['status']['session_execution']['running']
    assert messages['status']['session_execution']['request_id'] == 'long'
    assert any(e['kind'] == 'execution_started' and e['identity'] == identity for e in messages['events']['events'])
    assert messages['snapshot']['metrics']['driver_captures'] == 0
    assert not messages['second']['ok'] and messages['second']['execution_error']['status'] == 'precondition_blocked'
    final = json.loads((runtime.evidence.path / 'execution.json').read_text(encoding='utf-8'))
    assert final['status'] == 'uncertain' and final['error']['proof']['replay_authorized'] is False
    assert runtime.closed == 1 and messages['end']['type'] == 'disconnected'


def test_async_disconnect_waits_before_runtime_close(tmp_path, monkeypatch):
    from threading import Event
    from driver_epic_seven.application import Application
    runtime = FakeRuntime(tmp_path)
    started, release, finished = Event(), Event(), Event()
    def execute_blocked(self, request, rt):
        started.set()
        assert release.wait(3)
        assert runtime.closed == 0
        finished.set()
        return {'completed': False}
    monkeypatch.setattr(Application, 'execute', execute_blocked)
    runtime.cancel_execution = release.set
    def requests():
        yield json.dumps({'args': ['observe'], 'async': True})
        assert started.wait(1)
        yield json.dumps({'args': ['disconnect']})
    output = StringIO()
    serve({}, requests(), output, lambda config: runtime)
    assert finished.is_set() and runtime.closed == 1


def test_event_cursor_loss_and_invalid_cursor_are_explicit(tmp_path):
    runtime = FakeRuntime(tmp_path)
    for i in range(70):
        runtime.observer.event('test', index=i)
    messages = session(runtime, [{'args': ['events', '--after-sequence', '0']},
                                 {'args': ['events', '--after-sequence', '-1']}])
    assert messages[1]['history_lost'] and len(messages[1]['events']) == 64
    assert messages[1]['events'][0]['sequence'] == 7
    assert not messages[2]['ok']


def test_cli_readonly_status_and_events_use_saved_contract_without_runtime(tmp_path, monkeypatch):
    import driver_epic_seven.runtime as runtime_module
    monkeypatch.setattr(runtime_module, 'Runtime', lambda *a: pytest.fail('Unexpected connection'))
    runtime = FakeRuntime(tmp_path)
    status = {'running': True, 'status': 'running', 'identity': {'operation_id': 'offline'}}
    runtime.evidence.write('execution', status)
    runtime.observer.event('execution_started', identity=status['identity'])
    assert execute(parser().parse_args(['status', '--file', str(runtime.evidence.path / 'execution.json')])) == status
    result = execute(parser().parse_args(['events', '--file', str(runtime.evidence.path / 'observer.json')]))
    assert result['events'][0]['identity'] == status['identity']
    with pytest.raises(ValueError, match='conexão agent'):
        execute(parser().parse_args(['cancel']))


def test_capabilities_consultation_does_not_replace_running_identity(tmp_path, monkeypatch):
    from threading import Event
    from driver_epic_seven.application import Application
    runtime = FakeRuntime(tmp_path)
    started, release = Event(), Event()
    def execute_mock(self, request, rt=None):
        if request.operation == 'capabilities':
            assert rt is None
            return {'mapped_families_are_executors': False, 'account_access': None}
        started.set()
        assert release.wait(3)
        return {'completed': False}
    monkeypatch.setattr(Application, 'execute', execute_mock)
    runtime.cancel_execution = release.set
    def requests():
        yield json.dumps({'id': 'long', 'args': ['observe'], 'async': True})
        assert started.wait(1)
        yield json.dumps({'id': 'caps', 'args': ['capabilities']})
        yield json.dumps({'args': ['disconnect']})
    output = StringIO()
    serve({}, requests(), output, lambda config: runtime)
    messages = list(map(json.loads, output.getvalue().splitlines()))
    assert messages[2]['capabilities']['mapped_families_are_executors'] is False
    assert messages[2]['session_execution']['request_id'] == 'long'
    assert messages[2]['session_execution']['running']


def test_status_projects_async_failure_with_original_execution_correlation(tmp_path, monkeypatch):
    from threading import Event
    from driver_epic_seven.application import Application
    runtime = FakeRuntime(tmp_path)
    failed = Event()
    def execute_failed(self, request, rt):
        failed.set()
        raise RuntimeError('original async failure')
    monkeypatch.setattr(Application, 'execute', execute_failed)
    def requests():
        yield json.dumps({'id': 'original-request', 'args': ['observe'], 'async': True})
        assert failed.wait(1)
        # synchronize on the worker's terminal lifecycle publication
        for _ in range(100):
            saved = json.loads((runtime.evidence.path / 'execution.json').read_text(encoding='utf-8'))
            if not saved['running']:
                break
            time.sleep(.001)
        assert not saved['running']
        yield json.dumps({'id': 'query-request', 'args': ['status']})
    output = StringIO()
    serve({}, requests(), output, lambda config: runtime)
    response = list(map(json.loads, output.getvalue().splitlines()))[-1]
    assert response['id'] == 'query-request' and response['ok'] is False
    assert response['error'] == 'original async failure'
    assert response['execution_error']['request_id'] == 'original-request'
    assert response['execution_error']['identity'] == response['session_execution']['identity']


def test_transport_disk_failure_preserves_rejection_and_closes_without_dispatch(tmp_path):
    runtime = FakeRuntime(tmp_path)
    def fail_write(*args, **kwargs):
        raise OSError('disk unavailable')
    runtime.evidence.write = fail_write
    runtime.observer._writer = fail_write
    output = StringIO()
    # FakeRuntime.close also writes; isolate shutdown from its test-only writer.
    def close():
        runtime.closed += 1
    runtime.close = close
    serve({}, StringIO(json.dumps({'id': 'disk', 'args': ['observe']})+'\n'), output,
          lambda config: runtime)
    response = list(map(json.loads, output.getvalue().splitlines()))[-1]
    assert response['id'] == 'disk' and not response['ok']
    assert 'disk unavailable' in response['error']
    assert response['execution_error']['proof']['input_attempted'] is False
    assert response['persistence_errors'] and response['evidence']['response_file'] is None
    assert runtime.calls == [] and runtime.closed == 1


def test_cli_explicit_identity_and_plan_budget_match_common_request():
    from driver_epic_seven.cli import request_from_args
    from driver_epic_seven.contracts import Identity
    identity = Identity()
    budget = {'max_attempts': 2, 'max_starts': 2, 'max_total_energy': 16, 'max_actions': 100}
    args = parser().parse_args(['--execution-identity', json.dumps(identity.as_dict()),
                                '--plan-budget', json.dumps(budget), 'observe'])
    request = request_from_args(args)
    assert request.identity == identity and json.loads(request.parameters['plan_budget']) == budget
    assert 'execution_identity' not in request.parameters
    assert request_from_args(args, identity).identity == identity
    with pytest.raises(ValueError, match='conflita'):
        request_from_args(args, Identity())


@pytest.mark.parametrize('encoded', ['{}', 'null', '[]', 'bad json', '{"objective_id":"x"}'])
def test_cli_identity_requires_four_explicit_ids(encoded):
    from driver_epic_seven.cli import request_from_args
    with pytest.raises(ValueError, match='quatro IDs'):
        request_from_args(parser().parse_args(['--execution-identity', encoded, 'observe']))


def test_jsonl_explicit_identity_rejects_cli_conflict_before_dispatch(tmp_path):
    from driver_epic_seven.contracts import Identity
    runtime = FakeRuntime(tmp_path)
    explicit, conflicting = Identity(), Identity()
    responses = session(runtime, [{'identity': explicit.as_dict(), 'args': [
        '--execution-identity', json.dumps(conflicting.as_dict()), 'observe']}])
    assert not responses[1]['ok'] and 'conflita' in responses[1]['error']
    assert runtime.calls == []


def test_cli_and_jsonl_execute_same_identity_and_plan_budget(tmp_path, monkeypatch):
    from driver_epic_seven.application import Application
    from driver_epic_seven.cli import execute_live
    from driver_epic_seven.contracts import Identity
    identity = Identity()
    budget = {'max_attempts': 2, 'max_starts': 2, 'max_total_energy': 16, 'max_actions': 100}
    argv = ['--execution-identity', json.dumps(identity.as_dict()), '--plan-budget', json.dumps(budget), 'observe']
    requests = []
    def execute_mock(self, request, runtime):
        requests.append(request)
        return {'completed': True}
    monkeypatch.setattr(Application, 'execute', execute_mock)
    runtime = FakeRuntime(tmp_path)
    runtime.config = {}
    execute_live(parser().parse_args(argv), runtime)
    session(runtime, [{'identity': identity.as_dict(), 'args': argv}])
    assert len(requests) == 2
    assert requests[0].identity == requests[1].identity == identity
    assert requests[0].operation == requests[1].operation == 'observe'
    assert dict(requests[0].parameters) == dict(requests[1].parameters)
