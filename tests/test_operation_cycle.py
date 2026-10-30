from copy import deepcopy
from types import SimpleNamespace
import time

import pytest

from driver_epic_seven.attempts import AttemptLedger
from driver_epic_seven.contracts import Identity, Status
from driver_epic_seven.execution import OperationCycle, wrap_graph, native_action
from driver_epic_seven.observed_ui import build_tree
from driver_epic_seven.observer import SharedObserver


WINDOW={'hwnd':1,'pid':2,'process_name':'EpicSeven.exe','window_class':'GLFW30','client_size':[1212,682]}


def context(tmp_path):
    ledger=AttemptLedger(tmp_path/'actions.json',1)
    r=SimpleNamespace(path_attempts=ledger,path_battles=AttemptLedger(ledger.path,2),attempts=ledger,
        path_prepared={},path_group_actions=set(),path_completion_scopes={},start_reservations={},
        execution_identity=Identity('objective','plan','operation','attempt'),
        guard=lambda **_:deepcopy(WINDOW),observer=SharedObserver())
    data={'state':'unknown','window':deepcopy(WINDOW),'epoch_seconds':time.time()}
    data['ui_tree']=build_tree(data)
    params={'path':{'kind':'free_covenant','task_id':'task','consuming':True,'energy':0}}
    return r,OperationCycle(r),data,params


def test_reservation_and_attempt_are_durable_before_native_send(tmp_path):
    r,cycle,data,params=context(tmp_path)
    def send():
        entry=AttemptLedger(r.path_attempts.path).read()['stages']['task'][0]
        assert entry['status']=='reserved'
        assert [e['phase'] for e in entry['events']]==[Status.RESERVED,Status.ATTEMPTED]
        assert entry['events'][0]['proof']['observation_id']==data['ui_tree']['observation_id']
        return True
    assert cycle.dispatch('diagnostic_name',params,data,send)
    entry=r.path_attempts.read()['stages']['task'][0]
    assert entry['status']=='sent'
    assert entry['identity']==r.execution_identity.as_dict()
    assert [e['phase'] for e in entry['events']][-1]==Status.ACCEPTED
    assert not any(e['phase'] in (Status.RESULT,Status.RETURNED) for e in entry['events'])


@pytest.mark.parametrize('failure_at',[1,2,3])
def test_persistence_failure_before_send_blocks_input(tmp_path,monkeypatch,failure_at):
    r,cycle,data,params=context(tmp_path); saves=[];sent=[]
    original=r.path_attempts.save
    def save(value):
        saves.append(value)
        if len(saves)==failure_at:raise OSError('disk full')
        original(value)
    monkeypatch.setattr(r.path_attempts,'save',save)
    with pytest.raises(OSError):cycle.dispatch('n',params,data,lambda:sent.append(True))
    assert not sent


def test_failure_after_send_is_conservative_and_never_replays(tmp_path):
    r,cycle,data,params=context(tmp_path);sent=[]
    def fail():sent.append(True);raise OSError('disconnected')
    with pytest.raises(OSError):cycle.dispatch('n',params,data,fail)
    assert r.path_attempts.read()['stages']['task'][0]['status']=='reserved'
    assert r.path_attempts.read()['stages']['task'][0]['events'][-1]['phase']==Status.UNCERTAIN
    for attempt in ('attempt','new-attempt'):
        r.execution_identity=Identity('objective','plan','operation',attempt)
        with pytest.raises(ValueError):OperationCycle(r).dispatch('renamed-node',params,data,lambda:sent.append(True))
    assert len(sent)==1


def test_optional_reads_and_wrap_do_not_mutate_or_reserve(tmp_path):
    r,cycle,data,params=context(tmp_path)
    graph={'n':{'recognition':'Custom','custom_recognition':'ScreenTarget',
                'custom_recognition_param':params,'action':'Click','max_hit':1}}
    original=deepcopy(graph)
    wrapped=wrap_graph(graph)
    for _ in range(3):build_tree(data)
    assert graph==original and wrapped['n']['action']=='Custom'
    assert not r.path_attempts.path.exists() and not r.path_prepared


def test_target_offset_is_only_applied_by_native_action_and_consumers_cannot_repeat():
    graph={'n':{'recognition':'Custom','custom_recognition':'ScreenTarget','action':'Click',
                'target':True,'target_offset':[10,20,0,0],'max_hit':1,
                'custom_recognition_param':{'path':{'kind':'free_covenant','consuming':True}}}}
    wrapped=wrap_graph(graph)['n']
    assert wrapped['target_offset']==[0,0,0,0]
    assert wrapped['custom_action_param']['native_parameters']['target_offset']==[10,20,0,0]
    graph['n']['repeat']=2
    with pytest.raises(ValueError,match='envio único'):wrap_graph(graph)


def test_window_change_expiry_and_stop_guard_never_send(tmp_path):
    r,cycle,data,params=context(tmp_path);sent=[]
    data['window']['pid']=3
    with pytest.raises(ValueError):cycle.dispatch('n',params,data,lambda:sent.append(True))
    data['window']=deepcopy(WINDOW);data['epoch_seconds']-=31
    with pytest.raises(ValueError):cycle.dispatch('n',params,data,lambda:sent.append(True))
    data['epoch_seconds']=time.time()
    def stop(**_):raise RuntimeError('STOP')
    r.guard=stop
    with pytest.raises(RuntimeError):cycle.dispatch('n',params,data,lambda:sent.append(True))
    assert not sent and not r.path_attempts.path.exists()


def test_result_return_and_late_acceptance_stay_separate(tmp_path):
    r,cycle,data,params=context(tmp_path)
    cycle.dispatch('start',params,data,lambda:True)
    scope='task';key=r.path_attempts.read()['stages'][scope][0]['key']
    proof=cycle.proof(data,'result')
    r.path_attempts.record(scope,key,Status.RESULT,identity=r.execution_identity.as_dict(),proof=proof,status='victory')
    r.path_attempts.record(scope,key,Status.ACCEPTED,identity=r.execution_identity.as_dict(),proof={'node':'late'},status='sent')
    assert r.path_attempts.read()['stages'][scope][0]['status']=='victory'
    r.path_attempts.record(scope,key,Status.RETURNED,identity=r.execution_identity.as_dict(),proof=proof,status='returned')
    other=deepcopy(proof);other['window']['pid']=3
    with pytest.raises(ValueError):cycle._mark(r.path_attempts,scope,'victory',Status.RESULT,other)
    assert r.path_attempts.read()['stages'][scope][0]['status']=='returned'


def test_native_action_is_single_sdk_call_with_same_box_and_no_next():
    calls=[]
    ctx=SimpleNamespace(run_action_direct=lambda *a:(calls.append(a) or SimpleNamespace(success=True)))
    spec={'native_action':'LongPress','native_parameters':{'duration':100,'next':['Forbidden']}}
    assert native_action(ctx,spec,[1,2,3,4],{'observation_id':'proof'})
    assert len(calls)==1 and calls[0][0]=='LongPress' and calls[0][1].duration==100
    assert calls[0][2]==[1,2,3,4] and not hasattr(calls[0][1],'next')


def test_persistence_failure_after_accepted_input_retains_attempt_and_blocks_replay(tmp_path,monkeypatch):
    r,cycle,data,params=context(tmp_path);sent=[];saves=[];original=r.path_attempts.save
    def save(value):
        saves.append(True)
        if len(saves)==4:raise OSError('disk full after dispatch')
        original(value)
    monkeypatch.setattr(r.path_attempts,'save',save)
    with pytest.raises(OSError):cycle.dispatch('n',params,data,lambda:(sent.append(True) or True))
    entry=r.path_attempts.read()['stages']['task'][0]
    assert entry['status']=='reserved' and entry['events'][-1]['phase']==Status.ATTEMPTED
    with pytest.raises(ValueError):cycle.dispatch('n',params,data,lambda:sent.append(True))
    assert len(sent)==1


def test_legacy_campaign_uncertain_entry_and_return_without_result_do_not_admit_start(tmp_path):
    r,cycle,data,_=context(tmp_path)
    r.attempts=AttemptLedger(tmp_path/'campaign.json',3)
    r.attempts.reserve('stage','legacy-task',8)
    r.attempts.mark('stage','legacy-task','sent')
    cycle._mark(r.attempts,'stage','returned',Status.RETURNED,cycle.proof(data,'back'))
    assert r.attempts.read()['stages']['stage'][0]['status']=='sent'
    r.stage_inspector=SimpleNamespace(get=lambda _: {'energy':8})
    for identity in ('new-session','another-session'):
        r.execution_identity=Identity('goal','plan','operation',identity)
        with pytest.raises(ValueError,match='sem resultado'):
            OperationCycle(r).dispatch('new-node',{'target':'stage_start','stage_id':'stage'},data,
                                       lambda:pytest.fail('Uncertain Start repeated'))


@pytest.mark.parametrize('kind',['equipment_enhanced','formation_applied'])
def test_applied_non_battle_effect_can_reach_verified_return(tmp_path,kind):
    r,cycle,data,params=context(tmp_path)
    scope='change';r.path_attempts.reserve(scope,'attempt:'+scope,0)
    r.path_attempts.record(scope,'attempt:'+scope,Status.RESERVED,identity=r.execution_identity.as_dict(),proof={})
    cycle._observe_effect({'kind':kind,'task_id':scope},data,cycle.proof(data,'effect'),r.execution_identity)
    assert r.path_attempts.read()['stages'][scope][0]['status']=='applied'
    cycle._observe_effect({'kind':'equipment_returned' if kind.startswith('equipment') else 'formation_returned','task_id':scope},
        data,cycle.proof(data,'return'),r.execution_identity)
    assert r.path_attempts.read()['stages'][scope][0]['status']=='returned'


def test_campaign_return_requires_current_result_proof_not_a_legacy_victory_flag(tmp_path):
    r,cycle,data,_=context(tmp_path);scope='campaign-stage';key='legacy-attempt'
    r.attempts.reserve(scope,key,8);r.attempts.mark(scope,key,'victory')
    params={'execution':{'ledger':'campaign','scope':scope,'key':key,'phase':Status.RETURNED,'status':'returned','requires_result':True}}
    sent=[]
    with pytest.raises(ValueError,match='prova de vit'):
        cycle.dispatch('Return',params,data,lambda:sent.append(True),input_action=False)
    assert not sent and r.attempts.read()['stages'][scope][0]['status']=='victory'
    r.attempts.record(scope,key,Status.RESULT,identity=r.execution_identity.as_dict(),
        proof=cycle.proof(data,'CurrentVictory'),status='victory')
    assert cycle.dispatch('Return',params,data,lambda:sent.append(True) or True,input_action=False)
    assert sent==[True] and r.attempts.read()['stages'][scope][0]['status']=='returned'
