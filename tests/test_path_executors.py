from copy import deepcopy
import json
from pathlib import Path
import time

import pytest

from driver_epic_seven.config import ROOT
from driver_epic_seven.prequel import stage, campaign_graph, target, reserve_entry, finish_graph
from driver_epic_seven.path_execution import free_summon_graph, path_target
from driver_epic_seven.observed_ui import build_tree, operation_view


@pytest.mark.parametrize('reached', [False, True])
def test_terminal_proof_survives_later_capture_failure_without_retry(reached):
    from types import SimpleNamespace
    from driver_epic_seven.path_execution import run_graph
    calls=[]
    evidence=SimpleNamespace(path=Path('evidence'), write=lambda *args:calls.append(args))
    terminal=SimpleNamespace(name='Done',completed=reached,action=None)
    job=SimpleNamespace(get=lambda:SimpleNamespace(nodes=[terminal]))
    def unavailable(*args,**kwargs):
        raise RuntimeError('Window minimized after terminal recognition')
    runtime=SimpleNamespace(guard=lambda **kwargs:None,evidence=evidence,
        tasker=SimpleNamespace(post_task=lambda *args:job),wait=lambda *args,**kwargs:None,
        observe=unavailable)
    result=run_graph(runtime,{},'Entry','Done')
    assert result['completed'] is reached and result['postcondition_verified'] is reached
    assert result['needs_review'] is True and result['after'] is None
    assert result['observation_error']=='Window minimized after terminal recognition'
    assert [name for name,_ in calls]==['path_graph','path_result']


def test_rank_maximum_energy_reuses_existing_ack_without_claiming_recovery():
    rows=[('Rank up!',[547,183,118,35]),
          ('Maximum Energy has been increased',[449,263,312,21]),
          ('161> 172',[502,330,213,34]),('Tap to close',[554,430,105,21]),
          ('X Tap to close',[547,645,113,20])]
    def read(items):
        data={'state':'unknown','matches':{},'window':{'process_name':'EpicSeven.exe','client_size':[1212,682]},
              'text':[{'text':s,'box':b,'score':.99} for s,b in items]}
        data['ui_tree']=build_tree(data)
        return data
    data=read(rows);current=operation_view(data)
    assert current['view']=='rank_up_result' and current['mode']=='maximum_energy'
    context=current['items'][0]
    assert context['maximum_energy_before']==161 and context['maximum_energy_after']==172
    assert context['rank'] is None and context['recovered_energy'] is None
    assert path_target(data,{'kind':'informational_ack'},None)==[554,430,105,21]
    for missing in (0,1,3):
        assert path_target(read([r for i,r in enumerate(rows) if i!=missing]),
                           {'kind':'informational_ack'},None) is None
    assert operation_view(read([r for i,r in enumerate(rows) if i!=2]))['items'][0]['maximum_energy_after'] is None


def test_prequel_identity_uses_mission_binding_instead_of_old_map_caption():
    s=stage('tar007')
    assert s['title']=='One Last Strike' and s['location']=='A Rift in the Frustration'
    assert s['location_source_text']=='3-7. A Rift in the Frustration'
    assert s['mission_binding_id']=='ep0_3_7' and s['account_progress'] is None
    s=stage('dap005')
    assert s['title']=='An Unpermitted Future' and s['location']=='Corrupted Forest'


def test_campaign_is_finite_has_one_start_and_auto_click_per_stage_and_no_map_before_victory():
    plan,graph=campaign_graph('tar007','tar008',16)
    assert plan['energy_limit']==16 and plan['max_starts']==2
    starts=[n for k,n in graph.items() if k.endswith('.Start')]
    assert len(starts)==2 and all(n['max_hit']==1 for n in starts)
    assert all(n['max_hit']==1 for k,n in graph.items() if k.endswith('.Before.Auto'))
    for k,n in graph.items():
        if '.Before.' in k or k.endswith('.Start'):
            assert not any(v.endswith('.Map') for v in n.get('next',[]))
    with pytest.raises(ValueError):campaign_graph('tar007','tar008',15)
    with pytest.raises(ValueError):campaign_graph('tar007','ijp001',100)
    with pytest.raises(ValueError):campaign_graph('tar008','tar007',100)


def prepared():
    return {'view':'prequel_preparation','items':[{'semantic_id':'context','location':'A Rift in the Frustration',
            'story_title':'One Last Strike','team_cp':33677,'cost':{'currency':'energy','cost':8,'available':781}}],
            'controls':[{'semantic_id':'start_quest','consuming':True,'box':[1030,610,110,25]}]}


def test_start_requires_fresh_same_window_available_map_proof_and_exact_cost():
    now=time.time();window={'hwnd':1,'pid':2,'process_name':'EpicSeven.exe','window_class':'GLFW30','client_size':[1212,682]}
    ticket={'tar007':{'epoch_seconds':now,'window':window}}
    params={'kind':'prequel_start','stage_id':'tar007','max_energy':8}
    assert target(prepared(),params,{'window':window},ticket)==[1030,610,110,25]
    assert target(prepared(),params,{'window':window},{}) is None
    old=deepcopy(ticket);old['tar007']['epoch_seconds']-=31
    assert target(prepared(),params,{'window':window},old) is None
    other={**window,'pid':3}
    assert target(prepared(),params,{'window':other},ticket) is None
    for field,bad in [('story_title','Other stage'),('location','Other location'),('team_cp',None)]:
        current=prepared();current['items'][0][field]=bad
        assert target(current,params,{'window':window},ticket) is None
    current=prepared();current['items'][0]['cost']['cost']=18
    assert target(current,params,{'window':window},ticket) is None


def test_free_executor_is_one_dispatch_and_never_substitutes_a_paid_summon():
    graph=free_summon_graph('guide_01_006_001')
    actions=[n for n in graph.values() if n['action']!='DoNothing']
    assert len(actions)==1 and actions[0]['max_hit']==1
    with pytest.raises(ValueError):free_summon_graph('guide_29_003_001')


def test_resume_has_zero_starts_and_new_request_cannot_duplicate_reserved_or_finished_entry(tmp_path):
    from driver_epic_seven.attempts import AttemptLedger
    ledger=AttemptLedger(tmp_path/'actions.json',2)
    reserve_entry(ledger,'tar008','first-job',8)
    reserve_entry(ledger,'tar008','first-job',8)
    assert len(ledger.read()['stages']['prequel:tar008'])==1
    for status in ('reserved','sent','victory','returned','defeat'):
        ledger.mark('prequel:tar008','first-job',status)
        with pytest.raises(ValueError):reserve_entry(ledger,'tar008','second-job',8)
    for victory in (False,True):
        graph=finish_graph('tar008',victory)
        assert not any(key.endswith('.Start') for key in graph)
        assert not any(n.get('custom_recognition_param',{}).get('path',{}).get('consuming') for n in graph.values())


def test_explicit_account_profiles_keep_their_entry_journals_separate(tmp_path):
    from driver_epic_seven.attempts import AttemptLedger
    from driver_epic_seven.config import load_config
    journals=[]
    for account in ('stove','steam'):
        profile=tmp_path/(account+'.json')
        profile.write_text(json.dumps({'path_ledger':str(tmp_path/(account+'-actions.json'))}),encoding='utf-8')
        journals.append(AttemptLedger(load_config(str(profile))['path_ledger'],2))
    reserve_entry(journals[0],'tar008','stove-first',8)
    assert journals[1].read()=={'stages':{}}
    reserve_entry(journals[1],'tar008','steam-first',8)
    assert journals[0].read()['stages']['prequel:tar008'][0]['key']=='stove-first'
    with pytest.raises(ValueError):reserve_entry(journals[0],'tar008','stove-second',8)


def test_abyss_unlock_ack_requires_current_heading_body_and_close_together():
    rows=[('Abyss',[564,160,84,34]),
          ('You can enter Abyss.Test your strength in the depths of the Abyss!',[330,370,551,20]),
          ('Tapto close',[554,486,104,20])]
    def read(items):
        data={'state':'unknown','matches':{},'window':{'process_name':'EpicSeven.exe','client_size':[1212,682]},
              'text':[{'text':s,'box':b,'score':.99} for s,b in items]}
        data['ui_tree']=build_tree(data)
        return data
    data=read(rows)
    assert operation_view(data)['view']=='system_unlock_notice'
    assert path_target(data,{'kind':'informational_ack'},None)==[554,486,104,20]
    for missing in range(3):
        assert path_target(read([r for i,r in enumerate(rows) if i!=missing]),
                           {'kind':'informational_ack'},None) is None


@pytest.mark.fixtures
def test_current_own_team_preparation_is_read_without_connecting_or_starting():
    p=ROOT/'var/runs/20261027T225814Z_7e7003d1/path_failure_after.json'
    if not p.exists():pytest.skip('Private current own-team preparation unavailable.')
    data=json.loads(p.read_text(encoding='utf-8'));data.pop('ui_tree',None)
    current=operation_view({'ui_tree':build_tree(data)})
    assert current['view']=='prequel_preparation' and current['mode']=='adventure_own_team'
    assert current['items'][0]['location']=='A Rift in the Frustration'
    assert current['items'][0]['story_title']=='One Last Strike'
    assert current['items'][0]['team_cp']==33677
