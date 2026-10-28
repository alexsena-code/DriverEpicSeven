from copy import deepcopy
import time

import pytest

from driver_epic_seven.abyss import graph,target


def test_abyss_start_is_one_floor_one_budget_and_fresh_preparation():
    window={'hwnd':1,'pid':2}
    view={'view':'abyss_preparation','items':[{'semantic_id':'context','floor':1,'team_cp':24400,
          'cost':{'currency':'energy','cost':10,'available':900}}],
          'controls':[{'semantic_id':'start','box':[1030,610,100,30],'consuming':True}]}
    params={'kind':'abyss_start','stage_id':'abyss001','max_energy':10}
    proof={'abyss:abyss001':{'epoch_seconds':time.time(),'window':window}}
    assert target(view,params,{'window':window},proof)==[1030,610,100,30]
    assert target(view,params,{'window':window},{}) is None
    for key,bad in [('floor',2),('team_cp',0),('cost',{'currency':'energy','cost':30,'available':900})]:
        altered=deepcopy(view);altered['items'][0][key]=bad
        assert target(altered,params,{'window':window},proof) is None
    assert target(view,params,{'window':{'pid':3}},proof) is None
    expired=deepcopy(proof);expired['abyss:abyss001']['epoch_seconds']-=31
    assert target(view,params,{'window':window},expired) is None
    assert target(view,{**params,'max_energy':9},{'window':window},proof) is None


def test_abyss_result_requires_matching_floor_and_never_uses_next_floor_or_replay():
    current={'view':'abyss_result','items':[{'semantic_id':'context','floor':1,'result':'victory'}],
             'controls':[{'semantic_id':'back','box':[100,600,90,30]}]}
    params={'kind':'abyss_result_back','stage_id':'abyss001'}
    assert target(current,params,{},None)==[100,600,90,30]
    current['items'][0]['floor']=2
    assert target(current,params,{},None) is None
    for finish in (False,True):
        plan,nodes,_,_=graph('guide_02_005_001',10,finish=finish)
        assert plan['max_starts']==(0 if finish else 1)
        assert not any('next_floor' in str(n) or 'try_again' in str(n) for n in nodes.values())
        assert len([k for k in nodes if k.endswith('.Start')])==(0 if finish else 1)
    with pytest.raises(ValueError):graph('other',10)
    with pytest.raises(ValueError):graph('guide_02_005_001',9)


@pytest.mark.fixtures
def test_current_abyss_result_outranks_shared_clear_banner():
    import json
    from driver_epic_seven.config import ROOT
    from driver_epic_seven.observed_ui import build_tree, operation_view
    path=ROOT/'var/runs/20261028T110752Z_934de0ce/path_failure_after.json'
    if not path.exists():pytest.skip('Private Abyss result unavailable')
    observation=json.loads(path.read_text(encoding='utf-8'))
    spec=json.loads((ROOT/'resources/epic-seven/vision.json').read_text(encoding='utf-8'))
    observation['ui_tree']=build_tree(observation,spec)
    current=operation_view(observation)
    assert current['view']=='abyss_result'
    assert current['items'][0]['floor']==1 and current['items'][0]['result']=='victory'
    assert target(current,{'kind':'abyss_result_back','stage_id':'abyss001'},observation,{})
    assert target(current,{'kind':'abyss_advance','stage_id':'abyss001'},observation,{}) is None
