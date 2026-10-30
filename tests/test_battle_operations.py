"""Mandatory battle evidence remains independent of optional CP and objectives."""
from copy import deepcopy
import time

import pytest

from driver_epic_seven import abyss, altar, prequel
from driver_epic_seven.battle_operations import energy_verified, team_verified
from test_operation_cycle import context


@pytest.mark.parametrize('family',['abyss','altar','prequel'])
def test_cp_unknown_keeps_start_but_missing_team_identity_cost_or_balance_blocks(family):
    if family=='abyss':
        current={'view':'abyss_preparation','items':[{'semantic_id':'context','floor':32,
            'cost':{'currency':'energy','cost':10,'available':20}}],
            'controls':[{'semantic_id':'start','consuming':True,'box':[1,2,3,4]}]}
        params={'kind':'abyss_start','stage_id':'abyss032','floor':32,'mode':'normal','expected_energy':10,'max_energy':10}
        key='abyss:abyss032'; target=abyss.target
    elif family=='altar':
        from test_altar_executor import preparation
        current=preparation();params={'kind':'altar_start','stage_id':'cmon001','max_energy':9}
        key='altar:cmon001';target=altar.target
    else:
        from test_path_executors import prepared
        current=prepared();params={'kind':'prequel_start','stage_id':'tar007','max_energy':8}
        key='tar007';target=prequel.target
    window={'pid':1};ticket={key:{'window':window,'epoch_seconds':time.time()}}
    info=current['items'][0]
    info.update(team_cp=None,preparation_composition_verified=True,visible_hero_levels=[42,50])
    assert target(current,params,{'window':window},ticket)
    for field,bad in [('visible_hero_levels',None),('visible_hero_levels',[]),('visible_hero_levels',[0]),
                      ('preparation_composition_verified',None),('cost',None),
                      ('cost',{'currency':'energy','cost':10,'available':0})]:
        changed=deepcopy(current);changed['items'][0][field]=bad
        changed['items'][0]['team_cp']=999999
        assert target(changed,params,{'window':window},ticket) is None


@pytest.mark.parametrize('floor',[1,31,32,33])
def test_same_abyss_operation_parameters_are_explicit_and_finish_prepare_never_consume(floor):
    for mode in ('prepare','finish'):
        plan,nodes,entry,done=abyss.graph('objective-'+str(floor),0,floor=floor,mode='normal',
            expected_energy=10,**{mode:True})
        assert plan['stage_id']==f'abyss{floor:03}' and plan['max_starts']==0
        assert not any(n.get('custom_recognition_param',{}).get('path',{}).get('consuming') for n in nodes.values())
        assert entry in nodes and done in nodes
    with pytest.raises(ValueError):abyss.graph('objective',10,floor=floor,mode='challenge',expected_energy=10)


def test_next_floor_32_to_33_is_separate_navigation_with_no_start():
    plan,nodes,_,_=abyss.graph('navigation',0,floor=32,mode='normal',expected_energy=10,prepare=True,next_floor=True)
    assert plan['stage_id']=='abyss033' and plan['energy_limit']==plan['max_starts']==0
    assert not any(n.get('custom_recognition_param',{}).get('path',{}).get('consuming') for n in nodes.values())
    result={'view':'abyss_result','items':[{'semantic_id':'context','floor':32,'result':'victory'}],
            'controls':[{'semantic_id':'next_floor','consuming':False,'box':[5,6,7,8]}]}
    params={'kind':'abyss_next_floor','stage_id':'abyss032','floor':32,'mode':'normal','expected_energy':10}
    assert abyss.target(result,params,{},None)==[5,6,7,8]
    result['items'][0]['floor']=31
    assert abyss.target(result,params,{},None) is None


def test_new_objective_cannot_bypass_pending_physical_battle(tmp_path):
    r,cycle,data,_=context(tmp_path)
    first={'path':{'kind':'abyss_start','stage_id':'abyss032','task_id':'first','consuming':True,'energy':10}}
    assert cycle.dispatch('start',first,data,lambda:True)
    second=deepcopy(first);second['path']['task_id']='another-objective'
    with pytest.raises(ValueError,match='outro objetivo'):
        cycle.dispatch('start-new',second,data,lambda:pytest.fail('pending battle repeated'))
    assert len(r.path_attempts.read()['stages'])==1


def test_legacy_start_key_also_blocks_new_objective(tmp_path):
    r,cycle,data,_=context(tmp_path)
    r.path_attempts.reserve('legacy','run/Path.Abyss.abyss032.Start',10)
    params={'path':{'kind':'abyss_start','stage_id':'abyss032','task_id':'new','consuming':True,'energy':10}}
    with pytest.raises(ValueError,match='outro objetivo'):cycle.dispatch('n',params,data,lambda:False)


def test_optional_cp_is_never_a_replacement_for_mandatory_proofs():
    assert not team_verified({'team_cp':90000})
    for cost in (None,{'currency':'energy','cost':True,'available':10},
                 {'currency':'energy','cost':10,'available':True},
                 {'currency':'flags','cost':10,'available':20}):
        assert not energy_verified(cost,10,10)


def test_finish_does_not_require_a_new_cost_or_compile_any_consumer():
    plan,nodes,_,_=abyss.graph('pending',0,floor=32,mode='normal',expected_energy=None,finish=True)
    assert plan['energy_limit']==plan['max_starts']==0
    assert not any(n.get('custom_recognition_param',{}).get('path',{}).get('consuming') for n in nodes.values())


def test_altar_prepare_is_idempotent_at_the_same_current_preparation():
    _,nodes,entry,success=altar.graph('cmon002','objective',0,prepare=True)
    assert nodes[entry]['next'][0]==success
    assert all(n.get('action','DoNothing')=='DoNothing' for k,n in nodes.items() if k==success)


def test_finish_requires_the_reserved_stage_and_victory_window_before_dispatch(tmp_path,monkeypatch):
    from driver_epic_seven.battle_operations import run_unit
    from driver_epic_seven import path_execution
    r,_,data,_=context(tmp_path);r.original=data['window']
    r.path_attempts.reserve('task','run/Path.Abyss.abyss031.Start',10)
    monkeypatch.setattr(path_execution,'run_graph',lambda *a,**k:pytest.fail('mismatched finish dispatched'))
    compilation=abyss.graph('task',0,floor=32,mode='normal',expected_energy=None,finish=True)
    with pytest.raises(ValueError,match='outra batalha'):run_unit(r,'abyss','abyss032','task',compilation,finish=True)
    r.path_attempts.mark('task','run/Path.Abyss.abyss031.Start','victory')
    compilation=abyss.graph('task',0,floor=31,mode='normal',expected_energy=None,finish=True)
    with pytest.raises(ValueError,match='janela'):run_unit(r,'abyss','abyss031','task',compilation,finish=True)
