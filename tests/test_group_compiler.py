from copy import deepcopy

import pytest

from driver_epic_seven import path_group
from driver_epic_seven.path_planning import route_level


def plan_and_view():
    hero='Arbiter Vildred'
    settings={'max_energy':50,'max_gold':10000,'tasks':{
        'guide_02_001_001':{'from_stage':'ijp001','to_stage':'ijp008','max_energy':40},
        'guide_02_005_001':{'max_energy':10},
        'guide_02_004_001':{'hero_name':hero},
        'guide_02_003_001':{'hero_name':hero,'max_gold':10000,'material_limits':{'Lesser Equipment Charm':1}}}}
    view={'group_id':'group_guide_02','group_counter':{'current':1,'total':5},'visible_tasks':[
        {'task_id':t['task_id'],'status':'incomplete','claim_ready':False} for t in route_level(2)['tasks']
        if t['task_id']!='guide_02_002_001']}
    return settings,view


def test_complete_group_compiles_one_closed_finite_graph_and_keeps_review_boundary(monkeypatch):
    settings,view=plan_and_view();monkeypatch.setattr(path_group,'quest_view',lambda _:view)
    plan,nodes=path_group.compile_group(2,{},settings,['guide_02_002_001'])
    assert plan['energy_limit']==50 and plan['gold_limit']==10000 and plan['next_group_id']=='group_guide_03'
    assert plan['agent_checkpoint'] is True and len(plan['claim_completion_scopes'])==2
    assert all(destination in nodes for n in nodes.values() for destination in n.get('next',[]))
    starts=[]
    for name,node in nodes.items():
        if node.get('action','DoNothing')=='DoNothing':continue
        assert node['custom_recognition']=='ScreenTarget' and node['max_hit']<=12
        if node['custom_recognition_param'].get('path',{}).get('consuming'):
            assert node['max_hit']==1
            starts.append(name)
    assert len(starts)==13  # 8 campaign entries, Abyss, equip, enhance, two claims.
    assert not nodes['Path.Group.Done'].get('next')
    assert nodes['Path.Group.Done']['custom_recognition_param']['path']['group_id']=='group_guide_03'


def test_missing_unknown_task_choices_or_underfunded_plan_fail_without_any_runtime(monkeypatch):
    settings,view=plan_and_view();monkeypatch.setattr(path_group,'quest_view',lambda _:view)
    for variant in ('missing','energy','gold','foreign','ledger'):
        altered=deepcopy(settings);verified=['guide_02_002_001']
        if variant=='missing':altered['tasks'].pop('guide_02_003_001')
        if variant=='energy':altered['max_energy']=49
        if variant=='gold':altered['max_gold']=9999
        if variant=='foreign':altered['tasks']['guide_01_006_001']={}
        if variant=='ledger':verified.append('guide_02_001_001')
        with pytest.raises(ValueError):path_group.compile_group(2,{},altered,verified)


def test_full_claimed_group_compiles_only_reward_and_never_replays_units(monkeypatch):
    _,view=plan_and_view();view['group_counter']={'current':5,'total':5};view['visible_tasks']=[]
    monkeypatch.setattr(path_group,'quest_view',lambda _:view)
    plan,nodes=path_group.compile_group(2,{}, {'max_energy':0})
    assert plan['energy_limit']==0 and plan['max_starts']==0
    consuming=[n['custom_recognition_param']['path']['kind'] for n in nodes.values()
               if n.get('custom_recognition_param',{}).get('path',{}).get('consuming')]
    assert consuming==['group_claim']
