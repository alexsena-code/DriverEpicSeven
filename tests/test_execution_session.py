"""Pure mock tests: no window, Maa controller or resource is constructed."""
from threading import Event, Thread
from types import SimpleNamespace

import pytest

from driver_epic_seven.contracts import ApplicationError, Request
from driver_epic_seven.evidence import Evidence
from driver_epic_seven.execution_session import ExecutionSession
from driver_epic_seven.observer import SharedObserver


def setup_session(tmp_path, *, dispatched=False):
    started, release = Event(), Event()
    runtime = SimpleNamespace(evidence=Evidence(tmp_path), observer=SharedObserver(),
                              execution_dispatched=dispatched, cancels=0)
    def execute(request, rt):
        started.set()
        assert release.wait(3)
        return {'completed': True, 'execution': {'status': 'completed', 'identity': request.identity.as_dict()}}
    def cancel():
        runtime.cancels += 1
        release.set()
    runtime.cancel_execution = cancel
    session = ExecutionSession(SimpleNamespace(execute=execute), runtime)
    return session, runtime, started, release


def test_one_emitter_responsive_status_and_close_waits(tmp_path):
    session, runtime, started, release = setup_session(tmp_path)
    request = Request('run')
    session.submit(request, 'first')
    assert started.wait(1)
    status = session.status()
    assert status['running'] and status['identity'] == request.identity.as_dict()
    with pytest.raises(ApplicationError, match='andamento'):
        session.submit(Request('observe'), 'second')
    status['identity']['operation_id'] = 'mutated'
    assert session.status()['identity'] == request.identity.as_dict()
    session.close()
    assert not session.status()['running'] and runtime.cancels == 1
    with pytest.raises(ApplicationError, match='encerrada'):
        session.submit(Request('observe'))


@pytest.mark.parametrize('dispatched, expected', [(False, 'cancelled'), (True, 'uncertain')])
def test_cancel_retains_dispatch_and_identity_without_replay(tmp_path, dispatched, expected):
    session, runtime, started, release = setup_session(tmp_path, dispatched=dispatched)
    request = Request('run')
    session.submit(request, 'cancel-me')
    assert started.wait(1)
    session.cancel()
    session.cancel()
    result = session.wait()
    assert result['status'] == expected
    assert result['error']['proof'] == {'input_attempted': dispatched, 'replay_authorized': False}
    assert runtime.execution_dispatched is dispatched and runtime.cancels == 1
    events = runtime.observer.snapshot()['events']
    assert [e['kind'] for e in events if e['kind'].startswith('execution_')] == [
        'execution_started', 'execution_cancel_requested', 'execution_finished']
    assert all(e['identity'] == request.identity.as_dict() for e in events if 'identity' in e)


def test_close_never_returns_before_worker_stops(tmp_path):
    session, runtime, started, release = setup_session(tmp_path)
    runtime.cancel_execution = lambda: None
    session.submit(Request('run'))
    assert started.wait(1)
    closed = Event()
    closing = Thread(target=lambda: (session.close(), closed.set()))
    closing.start()
    assert not closed.wait(.03)
    release.set()
    closing.join(1)
    assert closed.is_set() and not session.status()['running']


def test_status_projects_checkpoint_limits_and_exact_ledger_progress(tmp_path):
    session, runtime, started, release = setup_session(tmp_path)
    runtime.active_plan_checkpoint = SimpleNamespace(read=lambda: {
        'identity': {'objective_id': 'offline-objective'}, 'state': 'running',
        'specification': {'units': [{'unit_id': 'known'}, {'unit_id': 'pending'}],
                          'limits': {'actions': 10, 'energy': 40}},
        'used': {'actions': 3, 'energy': 8}, 'deadline_epoch_seconds': 123})
    runtime.attempts = SimpleNamespace(read=lambda: {'stages': {'known': [{'status': 'verified'}],
        'pending': [{'status': 'sent'}]}})
    plan = session.status()['plan']
    assert plan['remaining'] == {'actions': 7, 'energy': 32}
    assert plan['units'][0]['completion_verified']
    assert plan['pending_units'] == ['pending'] and plan['account_progress'] is None


def test_status_resolves_named_multiscopes_with_bound_identity_and_receipts(tmp_path):
    session, runtime, started, release = setup_session(tmp_path)
    identity = {'objective_id': 'objective', 'plan_id': 'plan'}
    def row(*, objective='objective', plan='plan', proof=True):
        return {'status': 'returned', 'key': 'reservation',
                'identity': {'objective_id': objective, 'plan_id': plan},
                'events': [{'phase': 'return_verified', 'proof': {'observation_id': 'observed',
                    'window': {'hwnd': 1, 'pid': 2}}}] if proof else []}
    runtime.active_plan_checkpoint = SimpleNamespace(read=lambda: {
        'identity': identity, 'state': 'running', 'used': {},
        'specification': {'units': [
            {'unit_id': 'mission-campaign', 'ledger_name': 'path_battles', 'ledger_scopes': ['prequel:a', 'prequel:b']},
            {'unit_id': 'missing', 'ledger_name': 'path_battles', 'ledger_scopes': ['prequel:a', 'prequel:missing']},
            {'unit_id': 'wrong-objective', 'ledger_name': 'campaign', 'ledger_scopes': ['other']},
            {'unit_id': 'wrong-plan', 'ledger_name': 'campaign', 'ledger_scopes': ['other-plan']},
            {'unit_id': 'no-proof', 'ledger_name': 'path_attempts', 'ledger_scopes': ['unproven']},
            {'unit_id': 'claim', 'ledger_name': 'path_attempts', 'ledger_scopes': ['claim:group:mission']},
            {'unit_id': 'wrong-ledger', 'ledger_name': 'campaign', 'ledger_scopes': ['prequel:a']},
        ], 'limits': {}}})
    runtime.path_battles = SimpleNamespace(read=lambda: {'stages': {'prequel:a': [row()], 'prequel:b': [row()]}})
    runtime.attempts = SimpleNamespace(read=lambda: {'stages': {'other': [row(objective='unrelated')],
        'other-plan': [row(plan='unrelated')]}})
    runtime.path_attempts = SimpleNamespace(read=lambda: {'stages': {'claim:group:mission': [row()],
        'unproven': [row(proof=False)], 'other': [row()]}})
    plan = session.status()['plan']
    units = {unit['unit_id']: unit for unit in plan['units']}
    assert units['mission-campaign']['completion_verified'] and units['claim']['completion_verified']
    assert set(plan['pending_units']) == {'missing', 'wrong-objective', 'wrong-plan', 'no-proof', 'wrong-ledger'}
    assert units['wrong-objective']['ledger_evidence'][0]['identity_matches'] is False
    assert units['missing']['ledger_evidence'][1]['identity_matches'] is None
    assert len(units['mission-campaign']['ledger_evidence']) == 2


def test_legacy_unit_lookup_cannot_borrow_progress_from_unrelated_plan(tmp_path):
    session, runtime, started, release = setup_session(tmp_path)
    runtime.active_plan_checkpoint = SimpleNamespace(read=lambda: {
        'identity': {'objective_id': 'objective', 'plan_id': 'current'},
        'specification': {'units': [{'unit_id': 'stage'}], 'limits': {}}, 'used': {}})
    runtime.attempts = SimpleNamespace(read=lambda: {'stages': {'stage': [{'status': 'verified',
        'identity': {'objective_id': 'objective', 'plan_id': 'other'}}]}})
    assert session.status()['plan']['pending_units'] == ['stage']


@pytest.mark.parametrize('failure_owner', ['observer', 'evidence'])
def test_initial_lifecycle_persistence_failure_never_starts_or_blocks_worker(tmp_path, failure_owner):
    session, runtime, started, release = setup_session(tmp_path)
    original = runtime.observer.event if failure_owner == 'observer' else runtime.evidence.write
    def fail(*args, **kwargs):
        raise OSError('initial disk failure')
    if failure_owner == 'observer':
        runtime.observer.event = fail
    else:
        runtime.evidence.write = fail
    with pytest.raises(ApplicationError, match='initial disk failure') as failed:
        session.submit(Request('run'), 'no-worker')
    assert failed.value.status.value == 'precondition_blocked'
    assert not session.status()['running'] and not started.is_set()
    assert session.status()['error']['proof']['input_attempted'] is False
    if failure_owner == 'observer':
        runtime.observer.event = original
    else:
        runtime.evidence.write = original
    session.submit(Request('run'), 'recovered')
    assert started.wait(1)
    release.set()
    session.wait()
    session.close()


def test_worker_failure_survives_failed_invalidation_and_final_write(tmp_path):
    session, runtime, started, release = setup_session(tmp_path, dispatched=True)
    def execute(request, rt):
        started.set()
        assert release.wait(3)
        raise RuntimeError('original application failure')
    session.application.execute = execute
    session.submit(Request('run'), 'failed-worker')
    assert started.wait(1)
    runtime.observer.invalidate = lambda *a, **k: (_ for _ in ()).throw(OSError('invalidation disk failure'))
    runtime.evidence.write = lambda *a, **k: (_ for _ in ()).throw(OSError('finish disk failure'))
    release.set()
    status = session.wait()
    assert not status['running'] and status['status'] == 'uncertain'
    assert status['error']['error'] == 'original application failure'
    assert [e['phase'] for e in status['error']['proof']['persistence_errors']] == [
        'failure_invalidation', 'execution_finished']
    session.close()


def test_success_with_failed_finish_persistence_is_conservative(tmp_path):
    session, runtime, started, release = setup_session(tmp_path, dispatched=True)
    session.submit(Request('run'), 'finish-fails')
    assert started.wait(1)
    runtime.evidence.write = lambda *a, **k: (_ for _ in ()).throw(OSError('finish disk failure'))
    release.set()
    status = session.wait()
    assert not status['running'] and status['status'] == 'uncertain'
    assert status['result']['completed'] is True
    assert status['error']['proof']['replay_authorized'] is False
