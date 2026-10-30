"""Offline runtime fences. Constructing these objects never discovers a window."""
from copy import deepcopy
from threading import Event
from types import SimpleNamespace
import time

import pytest

from driver_epic_seven.config import load_config
from driver_epic_seven.evidence import Evidence
from driver_epic_seven.observed_ui import build_tree
from driver_epic_seven.observer import SharedObserver
from driver_epic_seven.runtime import Runtime
from test_guards import WINDOW
from test_operation_cycle import context


def offline_runtime(tmp_path):
    r = object.__new__(Runtime)
    r.config = load_config()
    r.config['stop_file'] = tmp_path/'STOP'
    r.evidence = Evidence(tmp_path/'runs')
    r.observer = SharedObserver(r.evidence.write)
    r.original = deepcopy(WINDOW)
    r.fatal = None
    r._execution_cancel = Event()
    r.execution_dispatched = False
    r.tasker = SimpleNamespace(running=False)
    r.windows = SimpleNamespace(inspect=lambda _: deepcopy(WINDOW))
    data = {'state': 'lobby', 'window': deepcopy(WINDOW), 'epoch_seconds': time.time(),
            'captured_at_epoch_seconds': time.time()}
    data['ui_tree'] = build_tree(data)
    r.observer.publish(data, 'offline_test_only')
    return r


@pytest.mark.parametrize('reason', ['cancel', 'stop', 'window', 'fatal'])
def test_guard_invalidates_old_tree_and_blocks_input(tmp_path, reason):
    r = offline_runtime(tmp_path)
    if reason == 'cancel': r.cancel_execution()
    elif reason == 'stop': r.config['stop_file'].touch()
    elif reason == 'window': r.windows.inspect = lambda _: {**WINDOW, 'pid': 999}
    else: r.fatal = 'failed recognition'
    with pytest.raises(RuntimeError): r.guard(input_active=True)
    assert not r.observer.snapshot(30000)['validity']['valid']


def test_cancel_is_nonblocking_and_only_the_wait_owner_stops_maa(tmp_path):
    r = offline_runtime(tmp_path)
    stops = []
    def stop():
        stops.append(True)
        r.tasker.running=False
        return SimpleNamespace(done=True)
    r.tasker = SimpleNamespace(running=True, post_stop=stop)
    r.cancel_execution()
    assert stops == [] and r.execution_cancelled
    job = SimpleNamespace(job_id=1, done=False)
    with pytest.raises(RuntimeError, match='cancelada'): r.wait(job, 10, task=True)
    assert stops == [True]
    assert r.observer.snapshot()['invalidated_reason'] == 'execution_cancelled'


def test_cancel_after_reservation_does_not_release_consumer_for_replay(tmp_path):
    r, cycle, data, params = context(tmp_path)
    sends = []
    guards = []
    def guard(**_):
        guards.append(True)
        if len(guards) > 1: raise RuntimeError('cancelled before native send')
        return data['window']
    r.guard = guard
    with pytest.raises(RuntimeError): cycle.dispatch('Send', params, data, lambda: sends.append(True))
    assert sends == []
    row = r.path_attempts.read()['stages']['task'][0]
    assert row['events'][-1]['phase'] == 'uncertain'
    r.guard = lambda **_: data['window']
    with pytest.raises(ValueError): cycle.dispatch('Send', params, data, lambda: sends.append(True))
    assert sends == []


def test_capture_and_recognition_failures_invalidate_previous_snapshot(tmp_path):
    r = offline_runtime(tmp_path)
    r.ctrl = SimpleNamespace(post_screencap=lambda: (_ for _ in ()).throw(OSError('test capture failed')))
    with pytest.raises(OSError): r.capture()
    assert r.observer.snapshot()['invalidated_reason'] == 'capture_failed'
    r._observe = lambda *a, **k: (_ for _ in ()).throw(ValueError('test recognition failed'))
    with pytest.raises(ValueError): r.observe()
    assert r.observer.snapshot()['invalidated_reason'] == 'observation_failed'


def test_prepare_cannot_clear_cancel_while_maa_runs(tmp_path):
    from driver_epic_seven.contracts import Identity
    r = offline_runtime(tmp_path)
    r.cancel_execution()
    r.tasker.running = True
    with pytest.raises(RuntimeError): r.prepare_execution(Identity())
    assert r.execution_cancelled
    r.tasker.running = False
    r.prepare_execution(Identity())
    assert not r.execution_cancelled


def test_story_completion_settles_effect_before_return_without_inventing_victory(tmp_path):
    from driver_epic_seven.contracts import Status
    r, cycle, data, params = context(tmp_path)
    r.path_battles.reserve('prequel:ijp001', 'story', 0)
    r.path_battles.record('prequel:ijp001', 'story', Status.ACCEPTED,
        identity=r.execution_identity.as_dict(), proof={}, status='sent')
    cycle.dispatch('Story.Done', {'path': {'kind': 'prequel_story_done', 'stage_id': 'ijp001'}},
                   data, lambda: True, input_action=False)
    row = r.path_battles.read()['stages']['prequel:ijp001'][0]
    assert row['status'] == 'returned'
    assert row.get('result_status') is None
    assert [e['phase'] for e in row['events']][-2:] == [Status.RESULT, Status.RETURNED]


def test_next_group_alone_cannot_prove_reward_receipt(monkeypatch):
    from driver_epic_seven import path_claims
    monkeypatch.setattr(path_claims, 'quest_view', lambda _: {'group_id': 'group_guide_03'})
    params = {'kind': 'group_claim_done', 'group_id': 'group_guide_02', 'next_group_id': 'group_guide_03'}
    data = {'window': WINDOW}
    assert path_claims.target(data, params, {}) is None
    assert path_claims.target(data, params, {'group_receipt:group_guide_02': {'window': {**WINDOW, 'pid': 99}}}) is None
    assert path_claims.target(data, params, {'group_receipt:group_guide_02': {'window': WINDOW}}) == [0, 0, 1, 1]


def test_close_keeps_lease_and_lock_if_maa_stop_is_unproven(tmp_path):
    r = offline_runtime(tmp_path)
    closed=[]
    r.tasker.running=True
    r.ctrl=None
    r.window_profile=SimpleNamespace(close=lambda:closed.append('profile'))
    r.lock=SimpleNamespace(close=lambda:closed.append('lock'))
    def fail_stop(): raise RuntimeError('unproven stop')
    r.stop_task=fail_stop
    with pytest.raises(RuntimeError,match='unproven'):r.close()
    assert closed==[]
    r.tasker.running=False
    r.close()
    assert closed==['profile','lock']


def test_runtime_chapter_resume_uses_original_deadline_without_pending_start(tmp_path):
    from driver_epic_seven.attempts import AttemptLedger
    from driver_epic_seven.chapters import compile_chapter
    from driver_epic_seven.contracts import Identity
    from driver_epic_seven.plans import begin_runtime_plan
    r=offline_runtime(tmp_path)
    r.config['path_ledger']=tmp_path/'path.json'
    r.execution_identity=Identity('objective','chapter-plan','resume','new-attempt')
    r.execution_retry=None
    plan,_=compile_chapter(r.config,'pes006',100)
    cp=begin_runtime_plan(r,plan['finite_plan'],3)
    deadline=cp.read()['deadline_epoch_seconds']
    cp.finish(error='simulated interruption')
    r.active_plan_checkpoint=None
    r.attempts=AttemptLedger(tmp_path/'campaign.json')
    r.attempts.reserve('pes006','old',10)
    data={'state':'episode_map','window':WINDOW,'epoch_seconds':time.time()}
    data['ui_tree']=build_tree(data)
    r.observe=lambda *a,**k:deepcopy(data)
    r.guard=lambda **k:deepcopy(WINDOW)
    waits=[]
    def post(entry,graph):
        assert entry=='Plan.Resume.Entry'
        assert not any(n.get('custom_recognition_param',{}).get('target')=='stage_start' for n in graph.values())
        terminal=SimpleNamespace(name='Plan.Resume.Done',completed=True,action=None)
        return SimpleNamespace(get=lambda:SimpleNamespace(nodes=[terminal]))
    r.post_task=post
    r.wait=lambda job,timeout,**k:waits.append(timeout)
    result=r.run_chapter('pes006',100,30)
    assert result['completed'] and result['max_starts']==0
    assert 0<waits[0]<=3 and cp.read()['deadline_epoch_seconds']==deadline
    assert r.active_plan_checkpoint is None
