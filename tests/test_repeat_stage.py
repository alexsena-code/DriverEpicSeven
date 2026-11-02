from copy import deepcopy
from pathlib import Path
import pytest
from driver_epic_seven.repeat_stage import graph, target, run
from driver_epic_seven.observed_ui import build_tree
from driver_epic_seven.execution import wrap_graph
from test_battle_end_ui import footer

RESOURCE=Path(__file__).resolve().parents[1]/'resources/epic-seven'


def test_finite_graph_has_single_use_starts_and_entry_before_each_result():
    nodes,entry,done=graph(3,9,27,600,'repeat:test',RESOURCE)
    assert entry=='Repeat.Entry' and done=='Repeat.3.Done'
    assert 'next' not in nodes[done]
    starts=[n for n in nodes.values() if n.get('custom_recognition_param',{}).get('path',{}).get('consuming')]
    assert len(starts)==3
    assert all(n['max_hit']==1 and n['action']=='LongPress' for n in starts)
    assert len({n['custom_recognition_param']['path']['task_id'] for n in starts})==3
    assert nodes['Repeat.1.Start']['next']==['Repeat.1.Entered']
    assert nodes['Repeat.1.Done']['next']==['Repeat.2.Start']
    assert not any(word in str(nodes) for word in ['next_difficulty','stage_start','result_confirm'])
    assert wrap_graph(nodes)['Repeat.1.Start']['custom_action']=='OperationBoundary'


@pytest.mark.parametrize('count,cost,budget,timeout',[(0,9,20,60),(101,9,9999,60),(2,9,17,60),(1,None,20,60),(1,0,20,60),(1,9,20,1801)])
def test_invalid_budget_never_builds_graph(count,cost,budget,timeout):
    with pytest.raises(ValueError):graph(count,cost,budget,timeout,'repeat:test',RESOURCE)


def test_current_tree_target_requires_cost_balance_and_footer_and_never_accepts_footer_as_entry():
    data=footer();data['ui_tree']=build_tree(data)
    params={'kind':'repeat_start','energy':9}
    assert target(data,params)==[1074,613,86,28]
    assert target(data,{'kind':'repeat_entered'}) is None
    assert target(data,{**params,'energy':10}) is None
    poor=footer();poor['text'][-1]['text']='9/8';poor['ui_tree']=build_tree(poor)
    assert target(poor,params) is None
    missing=footer();missing['text']=[];missing['ui_tree']=build_tree(missing)
    assert target(missing,params) is None


def test_unresolved_repeat_refuses_before_capture_or_dispatch():
    from types import SimpleNamespace
    ledger=SimpleNamespace(read=lambda:{'stages':{'repeat:old:1':[{'status':'sent'}]}})
    runtime=SimpleNamespace(path_attempts=ledger)
    with pytest.raises(ValueError,match='pendente'):run(runtime,1,9,60)


@pytest.mark.parametrize('manual',[False,True])
def test_entry_proof_accepts_active_combat_including_manual_skill_panel(manual):
    from driver_epic_seven.observed_ui import operation_view
    data=footer();data['text']=[];del data['matches']['path_battle_exit_lobby']
    if manual:
        data['matches']['skill_highlight_1']={'hit':True,'box':[925,600,70,50],'score':.99}
    data['ui_tree']=build_tree(data)
    if manual:assert operation_view(data)['view']=='battle_skill_selection'
    assert target(data,{'kind':'repeat_entered'})==[0,0,1,1]
