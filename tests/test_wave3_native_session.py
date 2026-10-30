"""Consult/cancel a real Maa task with a RAM-only controller, no game access."""
from copy import deepcopy
from threading import Event
from types import MethodType

import pytest

from driver_epic_seven import execution
from driver_epic_seven.application import Application
from driver_epic_seven.contracts import ApplicationError, Identity, Request
from driver_epic_seven.execution_session import ExecutionSession
from driver_epic_seven.runtime import Runtime
from test_wave3_integration import MemoryHarness, heir, receipt

pytestmark = pytest.mark.native


def test_status_and_cancel_respond_while_real_maa_boundary_owns_input(tmp_path, monkeypatch):
    runtime = MemoryHarness(tmp_path, [heir(group='3/6'), receipt(), heir(group='4/6', native=False)])
    runtime.config['stop_file'] = tmp_path/'STOP'
    runtime.execution_cancelled = False
    runtime.stop_task = MethodType(Runtime.stop_task, runtime)
    runtime.wait = MethodType(Runtime.wait, runtime)
    native_sent, release = Event(), Event()
    original = execution.native_action

    def paused_after_native_send(context, specification, box, detail):
        accepted = original(context, specification, box, detail)
        native_sent.set()
        assert release.wait(5), 'Test gate must be released, never left in a native callback.'
        return accepted

    monkeypatch.setattr(execution, 'native_action', paused_after_native_send)
    def prepare(identity):
        assert not runtime.tasker.running
        runtime.execution_cancelled = False
        runtime.execution_identity = identity
        runtime.execution_dispatched = False
    runtime.prepare_execution = prepare
    runtime.cancel_execution = lambda: setattr(runtime, 'execution_cancelled', True)
    request = Request('path.collect', {'allow_ready_group': True, 'level': 1,
        'task_id': 'guide_01_006_001'}, Identity('offline-goal', 'offline-plan', 'claim', 'one'))
    session = ExecutionSession(Application(runtime.config), runtime)
    try:
        session.submit(request, 'native-claim')
        assert native_sent.wait(5)
        counts = deepcopy(runtime.metrics)
        assert session.status()['running'] and not release.is_set()
        snapshot = runtime.observer.snapshot(30000)
        assert snapshot['readonly'] and runtime.metrics == counts
        with pytest.raises(ApplicationError): session.submit(request, 'second-emitter')
        cancelled = session.cancel()
        assert cancelled['cancel_requested'] and not release.is_set()
        release.set()
        outcome = session.wait()
        assert outcome['status'] == 'uncertain'
        assert outcome['error']['proof']['replay_authorized'] is False
        assert not runtime.tasker.running
        rows = runtime.path_attempts.read()['stages']['claim:group_guide_01:guide_01_006_001']
        assert len(rows) == 1 and rows[0]['identity'] == request.identity.as_dict()
        assert any(e['phase'] == 'dispatch_attempted' for e in rows[0]['events'])
        before = runtime.metrics['native_actions']
        runtime.index = 0
        prepare(Identity('offline-goal', 'offline-plan', 'claim-reconcile', 'two'))
        with pytest.raises(ApplicationError): Application(runtime.config).execute(request, runtime)
        assert runtime.metrics['native_actions'] == before
        runtime.write('native_session_proof', {'simulation': True, 'account_progress': None,
            'request_id': 'native-claim', 'identity': request.identity.as_dict(),
            'status_during_task': 'running', 'readonly_query_extra_captures': 0,
            'readonly_query_extra_recognitions': 0, 'second_emitter_blocked': True,
            'cancel_outcome': outcome, 'one_reserved_consumer': True,
            'maa_quiescent_before_close': not runtime.tasker.running})
    finally:
        release.set()
        session.close()
