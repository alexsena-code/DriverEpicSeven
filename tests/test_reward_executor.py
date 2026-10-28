from copy import deepcopy

from driver_epic_seven import path_claims


def quest():
    return {'group_id':'group_guide_01','group_counter':{'current':3,'total':6},'visible_tasks':[
        {'task_id':'guide_01_006_001','claim_ready':True,'row_fully_visible':True,
         'control':'receive','claim_control_box':[1003,321,112,39],'status':'unknown'}]}


def test_collection_requires_native_readiness_same_group_and_same_counter(monkeypatch):
    q=quest();monkeypatch.setattr(path_claims,'quest_view',lambda _:q)
    p={'kind':'mission_claim','group_id':'group_guide_01','mission_id':'guide_01_006_001','before_count':3,'total':6}
    assert path_claims.target({},p)==[1003,321,112,39]
    for field,value in [('claim_ready',None),('claim_ready',False),('row_fully_visible',False),('control','go')]:
        saved=deepcopy(q);q['visible_tasks'][0][field]=value
        assert path_claims.target({},p) is None
        q.clear();q.update(saved)
    q['group_counter']['current']=4
    assert path_claims.target({},p) is None
    q['group_id']='group_guide_02'
    assert path_claims.target({},p) is None


def test_counter_delta_alone_does_not_prove_individual_claim_but_full_group_does(monkeypatch):
    q=quest();monkeypatch.setattr(path_claims,'quest_view',lambda _:q)
    p={'kind':'claim_done','group_id':'group_guide_01','mission_id':'guide_01_006_001','before_count':3,'total':6}
    q['group_counter']['current']=4
    assert path_claims.target({},p) is None
    q['visible_tasks'][0].update(status='claimed',claimed_tick_box=[1038,500,30,23])
    assert path_claims.target({},p)
    q['visible_tasks']=[]
    assert path_claims.target({},p) is None
    q['group_counter']['current']=6
    assert path_claims.target({},p)


def test_group_claim_needs_both_full_counter_and_native_active_control(monkeypatch):
    q=quest();monkeypatch.setattr(path_claims,'quest_view',lambda _:q)
    p={'kind':'group_claim','group_id':'group_guide_01','before_count':6,'total':6}
    q.update(group_claim_control_ready=True,group_receive_box=[1000,200,120,40])
    assert path_claims.target({},p) is None
    q['group_counter']['current']=6
    assert path_claims.target({},p)==[1000,200,120,40]
    q['group_claim_control_ready']=None
    assert path_claims.target({},p) is None


def test_collection_is_one_dispatch_with_only_bounded_receipt_acknowledgements():
    scope,nodes=path_claims.graph('group_guide_01','guide_01_006_001',3,6)
    assert scope=='claim:group_guide_01:guide_01_006_001'
    consuming=[n for n in nodes.values() if n.get('custom_recognition_param',{}).get('path',{}).get('consuming')]
    assert len(consuming)==1 and consuming[0]['max_hit']==1
    assert nodes['Path.Claim.Receipt']['max_hit']==4
    assert 'Path.Claim.Dispatch' not in nodes['Path.Claim.Receipt']['next']
