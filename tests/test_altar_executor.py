import time
from copy import deepcopy

import pytest

from driver_epic_seven.altar import graph, stage, target


def preparation():
    return {'view':'spirit_altar_preparation','items':[{'semantic_id':'context','altar_name':'Dark Spirit Altar',
            'stage_label':'Dark Spirit Altar - Easy','difficulty':'easy','identity_conflict':False,'cost':{'currency':'energy','cost':9,'available':846},'team_cp':36643}],
            'controls':[{'semantic_id':'start','box':[1049,615,46,24],'consuming':True}]}


def test_altar_start_requires_current_identity_cost_team_and_recent_available_entry():
    window={'hwnd':1,'pid':2,'process_name':'EpicSeven.exe','window_class':'GLFW30','client_size':[1212,682]}
    ticket={'altar:cmon001':{'epoch_seconds':time.time(),'window':window}}
    params={'kind':'altar_start','stage_id':'cmon001','max_energy':9}
    assert target(preparation(),params,{'window':window},ticket)==[1049,615,46,24]
    no_short=preparation();no_short['items'][0]['identity_conflict']=None
    assert target(no_short,params,{'window':window},ticket)==[1049,615,46,24]
    assert target(preparation(),params,{'window':window},{}) is None
    old=deepcopy(ticket);old['altar:cmon001']['epoch_seconds']-=31
    assert target(preparation(),params,{'window':window},old) is None
    for key,value in [('altar_name','Flame Spirit Altar'),('difficulty','hard'),('identity_conflict',True),('cost',None),('team_cp',0)]:
        view=preparation();view['items'][0][key]=value
        assert target(view,params,{'window':window},ticket) is None
    assert target(preparation(),params,{'window':{**window,'pid':99}},ticket) is None


def test_altar_graph_never_restarts_or_uses_next_difficulty_and_finish_has_no_start():
    plan,nodes,entry,success=graph('cmon001','guide_01_004_001',9)
    assert plan['max_starts']==1 and plan['energy_limit']==9
    starts=[n for n in nodes.values() if n.get('custom_recognition_param',{}).get('path',{}).get('kind')=='altar_start']
    assert len(starts)==1 and starts[0]['max_hit']==1
    assert len([n for n in nodes if n.endswith('.Auto')])==1
    plan,resume,_,_=graph('cmon001','guide_01_004_001',0,finish=True)
    assert plan['max_starts']==0 and not any(n.endswith('.Start') for n in resume)
    assert not any('next_difficulty' in str(n) or 'try_again' in str(n) for n in nodes.values())
    with pytest.raises(ValueError):graph('cmon001','guide_01_004_001',8)
    with pytest.raises(ValueError):graph('cmon001','guide_01_006_001',9)
    assert stage('cmon001')['energy']==9


def test_only_explicit_current_victory_can_finish_altar():
    params={'kind':'altar_victory','stage_id':'cmon001'}
    assert target({'view':'otherworld_result','items':[{'semantic_id':'context','result':'victory'}]},params,{},None)
    for result in ('defeat',None):
        assert target({'view':'otherworld_result','items':[{'semantic_id':'context','result':result}]},params,{},None) is None
