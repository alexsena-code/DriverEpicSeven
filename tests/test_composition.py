from copy import deepcopy
import pytest

from driver_epic_seven.composition import append_fragment, validate_graph
from driver_epic_seven.interruptions import treatment
from driver_epic_seven.prequel import campaign_graph, finish_graph
from driver_epic_seven.abyss import graph as abyss_graph
from driver_epic_seven.altar import graph as altar_graph


def test_prefixes_error_and_geometry_references_without_mutating_semantic_parameters():
    fragment={'Entry':{'action':'DoNothing','next':['Click']},
        'Click':{'recognition':'Custom','custom_recognition':'ScreenTarget','action':'Click',
                 'target':'Entry','roi':'Entry','max_hit':1,'on_error':['Done'],'next':['Done'],
                 'custom_recognition_param':{'target':'semantic_game_button'}},
        'Done':{'action':'DoNothing'}}
    original=deepcopy(fragment); graph={}
    names=append_fragment(graph,fragment,'unit.')
    assert names['Done']=='unit.Done'
    assert graph['unit.Click']['on_error']==['unit.Done']
    assert graph['unit.Click']['target']==graph['unit.Click']['roi']=='unit.Entry'
    assert graph['unit.Click']['custom_recognition_param']['target']=='semantic_game_button'
    assert fragment==original
    validate_graph(graph,'unit.Entry',['unit.Done'])


@pytest.mark.parametrize('edge',['Missing',{'name':'Entry'},'[JumpBack]Entry'])
def test_unsupported_or_open_references_are_rejected_before_post(edge):
    with pytest.raises(ValueError):append_fragment({}, {'Entry':{'next':[edge]}}, 'x.')


@pytest.mark.parametrize('identity',['ijp001','ijp007','ijp008','tar007'])
@pytest.mark.parametrize('victory',[False,True])
def test_resume_emits_no_consumers_or_error_routes_back_to_start(identity,victory):
    nodes=finish_graph(identity,victory)
    validate_graph(nodes,'Path.Campaign.Entry',['Path.Campaign.Done'],resume=True)
    assert all(not n.get('custom_recognition_param',{}).get('path',{}).get('consuming') for n in nodes.values())


def test_two_modes_and_campaign_reuse_treatments_with_explicit_limits():
    _,abyss,_,_=abyss_graph('guide_02_005_001',10,floor=1,mode='normal',expected_energy=10)
    _,altar,_,_=altar_graph('cmon001','guide_01_004_001',10)
    _,campaign=campaign_graph('tar007','tar007',8)
    for nodes in (abyss,altar,campaign):
        auto=[n for k,n in nodes.items() if k.endswith('.Auto')]
        assert len(auto)==1 and auto[0]['custom_recognition_param']['auto_state'] is False
        assert auto[0]['max_hit']==1
    confirm=treatment('confirm_skip',['Again'],hits=2,timeout=12000)
    assert confirm['custom_recognition_param']['state']=='story_confirmation'
    assert confirm['pre_wait_freezes']['time']==350
    cancel=treatment('cancel_friend',['Again'],hits=1,timeout=12000)
    assert cancel['custom_recognition_param']['target']=='friend_cancel'
    with pytest.raises(ValueError):treatment('confirm',['Again'],hits=1,timeout=1000)
    with pytest.raises(ValueError):treatment('auto',['Again'],hits=2,timeout=1000)
    with pytest.raises(ValueError):treatment('notice',['Again'],hits=0,timeout=1000)


@pytest.mark.parametrize('identity',['tar007','taw002','jer001'])
@pytest.mark.parametrize('resume,victory',[(False,False),(True,False),(True,True)])
def test_campaign_closure_reobserves_clear_at_most_three_times_without_restart(identity,resume,victory):
    plan,graph=campaign_graph(identity,identity,stage_energy(identity),resume=resume,victory_observed=victory)
    prefix='Path.Campaign.'+identity+'.'
    clear=graph[prefix+'Clear']
    assert clear['max_hit']==3 and prefix+'Clear' in clear['next']
    assert prefix+'Clear' in graph[prefix+'After.Rank']['next']
    assert clear.get('repeat',1)==1 and clear['post_delay']==500
    # A recognized defeat retains precedence over story and broad notices.
    choices=graph['Path.Campaign.Entry' if resume else prefix+'Start']['next']
    assert choices[0]==prefix+'Defeat'
    assert choices.index(prefix+('After.Skip' if victory else 'Before.Skip')) < choices.index(prefix+('After.Rank' if victory else 'Before.Rank'))
    for node in graph.values():
        if node.get('custom_recognition_param',{}).get('path',{}).get('consuming'):
            assert node['max_hit']==1 and node.get('repeat',1)==1
    if resume:
        assert plan['energy_limit']==0 and plan['max_starts']==0
        assert not any(name.endswith('.Start') for name in graph)
        if victory:assert prefix+'Clear' in choices


def stage_energy(identity):
    from driver_epic_seven.prequel import stage
    return stage(identity)['energy']


@pytest.mark.parametrize('identity',['wdp001','mel009'])
@pytest.mark.parametrize('resume,victory',[(False,False),(True,False),(True,True)])
@pytest.mark.parametrize('suffix,state,target',[('SideAlert','side_story_alert','side_alert_close'),('CancelFriend','friend_request','friend_cancel')])
def test_side_alert_uses_calibrated_close_in_campaign_and_victory_resume(identity,resume,victory,suffix,state,target):
    _,graph=campaign_graph(identity,identity,stage_energy(identity),resume=resume,victory_observed=victory)
    prefix='Path.Campaign.'+identity+'.';name=prefix+'After.'+suffix
    alert=graph[name]
    assert alert['custom_recognition_param']['state']==state
    assert alert['custom_recognition_param']['target']==target
    assert alert['max_hit']==3 and alert.get('repeat',1)==1
    choices=graph['Path.Campaign.Entry' if resume else prefix+'Start']['next']
    assert name in choices
    assert name in alert['next']
    assert not alert['custom_recognition_param'].get('path',{}).get('consuming')
    if resume:validate_graph(graph,'Path.Campaign.Entry',['Path.Campaign.Done'],resume=True)
    if stage_energy(identity)>0:
        assert alert['next'][0]==prefix+'Defeat'
        assert prefix+'Before.Auto' in alert['next']
