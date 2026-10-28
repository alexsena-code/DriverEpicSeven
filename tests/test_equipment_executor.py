from copy import deepcopy
import time

import pytest

from driver_epic_seven.equipment_operations import target,graph


def ticket(task='guide_02_003_001'):
    return {'equipment:'+task:{'hero_name':'Arbiter Vildred','window':{'pid':1},'epoch_seconds':time.time(),
                              'item_name':'Observed Weapon','before_level':0,'current_cp':24000,'candidate_cp':30000}}


def test_enhance_requires_known_weapon_continuity_current_cost_and_exp_budget():
    current={'view':'item_enhancement','items':[{'semantic_id':'context','item_kind':'equipment','gold_cost':17280,'gold_balance':100000,'proposed_exp':1500}],
             'controls':[{'semantic_id':'enhance','consuming':True,'box':[600,600,100,30]}]}
    params={'kind':'equipment_enhance','task_id':'guide_02_003_001','hero_name':'Arbiter Vildred','max_gold':20000}
    proof=ticket()
    assert target(current,params,{'window':{'pid':1}},proof)==[600,600,100,30]
    assert target(current,params,{'window':{'pid':1}},{}) is None
    for key,value in [('gold_cost',None),('gold_cost',20001),('gold_balance',None),('gold_balance',10000),('proposed_exp',0),('item_kind','artifact')]:
        changed=deepcopy(current);changed['items'][0][key]=value
        assert target(changed,params,{'window':{'pid':1}},proof) is None
    for key,value in [('window',{'pid':2}),('hero_name','Other'),('before_level',None),('item_name',None),('epoch_seconds',time.time()-121)]:
        changed=deepcopy(proof);changed['equipment:guide_02_003_001'][key]=value
        assert target(current,params,{'window':{'pid':1}},changed) is None


def test_equip_preview_must_improve_current_hero_and_final_comparison_must_match():
    params={'kind':'equipment_review_change','task_id':'guide_02_004_001','hero_name':'Arbiter Vildred'}
    current={'view':'equip_all_preview','items':[{'semantic_id':'context','current_cp':24000,'candidate_cp':30000}],
             'controls':[{'semantic_id':'review_change','box':[500,600,100,30]}]}
    proof=ticket(params['task_id'])
    assert target(current,params,{'window':{'pid':1}},proof)==[500,600,100,30]
    assert target(current,params,{'window':{'pid':1}},{}) is None
    current['items'][0]['candidate_cp']=23000
    assert target(current,params,{'window':{'pid':1}},proof) is None
    hero={'view':'hero_equipment','items':[{'semantic_id':'context','hero_name':'Arbiter Vildred'}],'controls':[]}
    assert target(hero,{**params,'kind':'equipment_weapon'},{'window':{'pid':1}},proof) is None


@pytest.mark.parametrize('task',['guide_02_003_001','guide_02_004_001'])
def test_preview_has_no_consuming_actions_and_application_is_single_dispatch(task):
    for preview in (False,True):
        plan,nodes,_,_=graph(task,{'hero_name':'Arbiter Vildred','max_gold':20000},preview=preview)
        consuming=[n for n in nodes.values() if n.get('custom_recognition_param',{}).get('path',{}).get('consuming')]
        assert len(consuming)==(0 if preview else 1)
        assert all(n['max_hit']==1 for n in consuming)
    with pytest.raises(ValueError):graph('unknown',{'hero_name':'Arbiter Vildred'})
