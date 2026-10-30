"""Offline finite plan/checkpoint tests; no Runtime, capture or native SDK."""
from copy import deepcopy

import pytest

from driver_epic_seven.contracts import Identity
from driver_epic_seven.plans import (PlanCheckpoint, contract, disposition,
                                     graph_limits, resume_campaign, sequential_units)


def graph():
    return {'Start': {'recognition': 'Custom', 'action': 'Click', 'max_hit': 1,
                      'custom_recognition_param': {'path': {'kind': 'prequel_start',
                          'stage_id': 'ijp002', 'energy': 8, 'consuming': True}}},
            'Recovery.Back': {'recognition': 'Custom', 'action': 'LongPressKey', 'max_hit': 2,
                              'custom_recognition_param': {'path': {'kind': 'navigation'}}}}


def specification():
    return contract('campaign', sequential_units(['ijp002']), graph(), energy=8)


def test_plan_dependencies_and_limits_are_explicit():
    plan = specification()
    assert plan['limits'] == {'actions': 3, 'starts': 1, 'energy': 8, 'treatments': 0, 'recovery': 2}
    assert plan['automatic_retry'] is False
    assert plan['mission_credit_requires_receipt'] is True
    for units in ([{'unit_id': 'a', 'depends_on': ['missing']}],
                  [{'unit_id': 'a'}, {'unit_id': 'a'}]):
        with pytest.raises(ValueError):
            contract('bad', units, graph())
    broken = graph(); broken['Start']['max_hit'] = 2
    with pytest.raises(ValueError): graph_limits(broken)
    broken = graph(); broken['Recovery.Start'] = broken.pop('Start')
    with pytest.raises(ValueError): graph_limits(broken)


def test_checkpoint_charges_before_dispatch_and_survives_new_instance(tmp_path):
    path = tmp_path/'plan.json'; checkpoint = PlanCheckpoint(path); identity = Identity()
    checkpoint.begin(specification(), identity, 30, now=100)
    checkpoint.charge('Start', graph()['Start']['custom_recognition_param'], now=101)
    stored = PlanCheckpoint(path).read()
    assert stored['used']['starts'] == 1 and stored['used']['energy'] == 8
    assert stored['events'][0]['phase'] == 'dispatch_reserved'
    with pytest.raises(ValueError):
        checkpoint.charge('Start', graph()['Start']['custom_recognition_param'], now=102)
    checkpoint.finish(error='capture failed')
    with pytest.raises(ValueError): checkpoint.begin(specification(), identity, 30, now=103)
    resumed = checkpoint.begin(specification(), identity, 30, now=103, resume=True)
    assert resumed['deadline_epoch_seconds'] == 130 and resumed['used']['starts'] == 1
    checkpoint.charge('Recovery.Back', graph()['Recovery.Back']['custom_recognition_param'], now=104)
    with pytest.raises(ValueError): checkpoint.charge('Recovery.Back', {}, now=131)


def test_completed_or_changed_plan_cannot_be_replayed(tmp_path):
    checkpoint = PlanCheckpoint(tmp_path/'plan.json'); identity = Identity()
    checkpoint.begin(specification(), identity, 30, now=100)
    checkpoint.finish({'completed': True})
    for resume in (False, True):
        with pytest.raises(ValueError): checkpoint.begin(specification(), identity, 30, now=101, resume=resume)
    changed = specification(); changed['units'][0]['entity_id'] = 'other'
    with pytest.raises(ValueError): checkpoint.begin(changed, identity, 30, now=101)
    for invalid in (True, 0, -1, float('nan'), float('inf'), 3601):
        with pytest.raises(ValueError): PlanCheckpoint(tmp_path/'other.json').begin(specification(), identity, invalid)


def test_reconciliation_distinguishes_credit_and_uncertainty():
    assert disposition([]) == 'new'
    for status in ('reserved', 'sent', 'entered', 'victory', 'applied'):
        assert disposition([{'status': status}]) == 'reconcile_without_consumer'
    assert disposition([{'status': 'returned'}]) == 'completed'
    assert disposition([{'status': 'defeat'}]) == 'explicit_defeat_policy'


def test_campaign_resume_omits_completed_and_never_restarts_pending():
    entries = {'prequel:ijp001': [{'status': 'returned'}],
               'prequel:ijp002': [{'status': 'sent'}]}
    plan, nodes, entry, success = resume_campaign('ijp001', 'ijp003', 100, entries)
    assert plan['stage_ids'] == ['ijp002', 'ijp003'] and plan['max_starts'] == 1
    assert entry in nodes and success in nodes
    consumers = [node['custom_recognition_param']['path']['stage_id'] for node in nodes.values()
                 if node.get('custom_recognition_param', {}).get('path', {}).get('consuming')]
    assert consumers == ['ijp003']
    assert not any(name.startswith('Resume.ijp001.') for name in nodes)
    entries['prequel:ijp002'] = [{'status': 'defeat'}]
    with pytest.raises(ValueError): resume_campaign('ijp001', 'ijp003', 100, entries)


def test_chapter_resume_omits_completed_and_has_no_pending_start():
    from driver_epic_seven.config import load_config
    from driver_epic_seven.plans import resume_chapter
    plan,nodes,entry,terminal=resume_chapter(load_config(),'pes004',28,
        {'pes004':[{'status':'returned','key':'a'}], 'pes005':[{'status':'sent','key':'b'}]})
    assert plan['stage_ids']==['pes005','pes006'] and plan['max_starts']==1
    assert entry in nodes and terminal in nodes
    starts=[name for name,node in nodes.items() if node.get('custom_recognition_param',{}).get('target')=='stage_start']
    assert starts==['Resume.pes006.Stage.CheckReady']
    assert not any(name.startswith('Resume.pes004.') for name in nodes)


def test_group_resume_compiles_abyss_without_start_and_requires_final_credit(monkeypatch):
    from driver_epic_seven.path_group import unit_graph
    from driver_epic_seven.path_planning import catalog
    task=catalog().tasks['guide_02_005_001']
    plan,nodes,entry,success=unit_graph(task,{'max_energy':10},{task['id']:[{'status':'sent'}]})
    assert plan['max_starts']==0
    assert not any(node.get('custom_recognition_param',{}).get('path',{}).get('consuming') for node in nodes.values())
    assert entry in nodes


def test_explicit_retry_budget_is_finite_and_not_inferred():
    from driver_epic_seven.plans import with_retry_budget
    spec=specification()
    assert spec['max_attempts_per_unit']==1
    budget={'max_attempts':2,'max_starts':2,'max_total_energy':16,'max_actions':6}
    extended=with_retry_budget(spec,budget)
    assert extended['limits']['starts']==2 and extended['limits']['energy']==16
    assert spec['limits']['starts']==1
    for change in ({'max_attempts':4},{'max_starts':3},{'max_total_energy':0},{'max_actions':True}):
        with pytest.raises(ValueError):with_retry_budget(spec,{**budget,**change})


def test_claim_resume_has_no_consumer_and_requires_receipt():
    from driver_epic_seven.path_claims import graph
    _,nodes=graph('group_guide_02','guide_02_002_001',0,5,resume=True)
    assert 'Path.Claim.Dispatch' not in nodes
    assert nodes['Path.Claim.Done']['custom_recognition_param']['path']['requires_receipt'] is True
    assert not any(n.get('custom_recognition_param',{}).get('path',{}).get('consuming') for n in nodes.values())
    _,nodes=graph('group_guide_02',None,5,5,next_group_id='group_guide_03',resume=True)
    assert nodes['Path.Claim.Entry']['next']==['Path.Claim.Done','Path.Claim.Receipt','Path.Claim.Notice','Path.Claim.Next']


def test_restore_claim_ticket_needs_reservation_identity_window_and_target(tmp_path):
    from types import SimpleNamespace
    from driver_epic_seven.attempts import AttemptLedger
    from driver_epic_seven.path_claims import restore_ticket
    from driver_epic_seven.contracts import Status
    identity=Identity();window={'hwnd':1,'pid':2};scope='claim:group_guide_02:task'
    ledger=AttemptLedger(tmp_path/'attempts.json')
    ledger.reserve(scope,'key',0)
    proof={'window':window,'observation_id':'observation-1'}
    ledger.record(scope,'key',Status.RESERVED,identity=identity.as_dict(),proof=proof)
    runtime=SimpleNamespace(path_attempts=ledger,path_prepared={},original=window,execution_identity=identity)
    target={'kind':'mission_claim','task_id':scope,'group_id':'group_guide_02',
            'mission_id':'task','before_count':0,'total':5}
    checkpoint={'events':[{'semantic_target':target,'proof':proof}]}
    assert restore_ticket(runtime,scope,checkpoint)==target
    assert runtime.path_prepared['mission_claim:group_guide_02']['before_count']==0
    with pytest.raises(ValueError):restore_ticket(runtime,scope,{'events':[]})
    runtime.original={'hwnd':2,'pid':2}
    with pytest.raises(ValueError):restore_ticket(runtime,scope,checkpoint)


def test_retry_remainder_restarts_only_proven_defeat_when_explicit():
    entries={'prequel:ijp001':[{'status':'returned'}], 'prequel:ijp002':[{'status':'defeat'}]}
    plan,nodes,_,_=resume_campaign('ijp001','ijp003',100,entries,allow_defeat_retry=True)
    assert plan['stage_ids']==['ijp002','ijp003']
    assert not any(name.startswith('Resume.ijp001.') for name in nodes)
    consumers=[node['custom_recognition_param']['path']['stage_id'] for node in nodes.values()
               if node.get('custom_recognition_param',{}).get('path',{}).get('consuming')]
    assert consumers==['ijp002','ijp003']
    from driver_epic_seven.config import load_config
    from driver_epic_seven.plans import resume_chapter
    plan,nodes,_,_=resume_chapter(load_config(),'pes004',28,
        {'pes004':[{'status':'returned','key':'a'}], 'pes005':[{'status':'defeat','key':'b'}]},allow_defeat_retry=True)
    assert plan['stage_ids']==['pes005','pes006']
    starts=[name for name,node in nodes.items() if node.get('custom_recognition_param',{}).get('target')=='stage_start']
    assert starts==['Resume.pes005.Stage.CheckReady','Resume.pes006.Stage.CheckReady']
