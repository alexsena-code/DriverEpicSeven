from copy import deepcopy
import time

import pytest

from driver_epic_seven.abyss import graph,target


def test_abyss_start_is_one_floor_one_budget_and_fresh_preparation():
    window={'hwnd':1,'pid':2}
    view={'view':'abyss_preparation','items':[{'semantic_id':'context','floor':1,'team_cp':24400,
          'preparation_composition_verified':True,'visible_hero_levels':[50],
          'cost':{'currency':'energy','cost':10,'available':900}}],
          'controls':[{'semantic_id':'start','box':[1030,610,100,30],'consuming':True}]}
    params={'kind':'abyss_start','stage_id':'abyss001','max_energy':10,'floor':1,'mode':'normal','expected_energy':10}
    proof={'abyss:abyss001':{'epoch_seconds':time.time(),'window':window}}
    assert target(view,params,{'window':window},proof)==[1030,610,100,30]
    assert target(view,params,{'window':window},{}) is None
    for key,bad in [('floor',2),('visible_hero_levels',None),('cost',{'currency':'energy','cost':30,'available':900})]:
        altered=deepcopy(view);altered['items'][0][key]=bad
        assert target(altered,params,{'window':window},proof) is None
    assert target(view,params,{'window':{'pid':3}},proof) is None
    expired=deepcopy(proof);expired['abyss:abyss001']['epoch_seconds']-=31
    assert target(view,params,{'window':window},expired) is None
    assert target(view,{**params,'max_energy':9},{'window':window},proof) is None


def test_abyss_result_requires_matching_floor_and_never_uses_next_floor_or_replay():
    current={'view':'abyss_result','items':[{'semantic_id':'context','floor':1,'result':'victory'}],
             'controls':[{'semantic_id':'back','box':[100,600,90,30]}]}
    params={'kind':'abyss_result_back','stage_id':'abyss001','floor':1,'mode':'normal','expected_energy':10}
    assert target(current,params,{},None)==[100,600,90,30]
    current['items'][0]['floor']=2
    assert target(current,params,{},None) is None
    for finish in (False,True):
        plan,nodes,_,_=graph('guide_02_005_001',10,floor=1,mode='normal',expected_energy=10,finish=finish)
        assert plan['max_starts']==(0 if finish else 1)
        assert not any('next_floor' in str(n) or 'try_again' in str(n) for n in nodes.values())
        assert len([k for k in nodes if k.endswith('.Start')])==(0 if finish else 1)
    assert graph('other',10,floor=32,mode='normal',expected_energy=10)[0]['stage_id']=='abyss032'
    with pytest.raises(ValueError):graph('guide_02_005_001',9,floor=1,mode='normal',expected_energy=10)


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
    params={'stage_id':'abyss001','floor':1,'mode':'normal','expected_energy':10}
    assert target(current,{'kind':'abyss_result_back',**params},observation,{})
    assert target(current,{'kind':'abyss_advance',**params},observation,{}) is None


@pytest.mark.fixtures
def test_floor51_result_q_g_glyph_still_requires_full_result_composition():
    import json
    from driver_epic_seven.config import ROOT
    from driver_epic_seven.observed_ui import build_tree,operation_view
    path=ROOT/'var/admin-abyss-20261030ad/result51-live.json'
    if not path.exists():pytest.skip('Private floor 51 result unavailable')
    original=json.loads(path.read_text(encoding='utf-8'))['analysis']
    def read(d):return operation_view({'ui_tree':build_tree(d)})
    current=read(original)
    assert current['view']=='abyss_result' and current['items'][0]['floor']==51
    params={'kind':'abyss_result_back','stage_id':'abyss051','floor':51,'mode':'normal','expected_energy':10}
    assert target(current,params,original,{})
    assert target(current,{**params,'stage_id':'abyss052','floor':52},original,{}) is None
    for text in ('CLEAR','Abyss','Floor 51','Conguer Reward'):
        wrong=deepcopy(original);wrong['text']=[r for r in wrong['text'] if r['text']!=text]
        assert read(wrong).get('view')!='abyss_result'
    for label in ('Conquer Reward','Conguer Reward','Conpuer Reward','Conquer Reword'):
        wrong=deepcopy(original)
        wrong['text']=[{**r,'text':label} if r['text']=='Conguer Reward' else r for r in wrong['text']]
        assert (read(wrong).get('view')=='abyss_result') is (label in ('Conquer Reward','Conguer Reward'))
