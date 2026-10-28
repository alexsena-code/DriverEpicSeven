"""Milestone main track is content; native composition and numeric guards stay."""
from copy import deepcopy

import pytest

from driver_epic_seven.observed_ui import build_tree, operation_view


def native_number(value,box):
    return {'hit':True,'box':box,'score':.99,'text':str(value),'ambiguous':False,
            'filtered_candidates':[{'box':box,'score':.99,'text':str(value)}]}


def main(track='A Different Trajectory'):
    return {'state':'unknown','window':{'process_name':'EpicSeven.exe','client_size':[1212,682]},
            'matches':{
                'milestone_read_header':{'hit':True,'box':[63,18,250,27]},
                'milestone_read_currencies':{'hit':True,'box':[1045,12,95,30]},
                'milestone_read_receive':{'hit':True,'box':[1050,610,65,25]},
                'milestone_read_cost':native_number(40,[1060,565,30,20]),
                'milestone_read_essence':native_number(64,[1040,15,35,20])},
            'text':[{'text':text,'box':box,'score':.99} for text,box in (
                ('Milestone of Radiance',[64,20,250,25]),(track,[600,465,200,30]),
                ('Chest Upgrade Probability 10%',[610,527,280,25]))]}


def view(data):return operation_view({'ui_tree':build_tree(data)})


@pytest.mark.parametrize('process',['EpicSeven.exe','EpicSeven_Steam.exe'])
def test_track_name_is_generic_content_without_connection_or_executable_controls(monkeypatch,process):
    from driver_epic_seven.runtime import Runtime
    def forbidden(*args,**kwargs):raise AssertionError('A read-only adapter connected')
    monkeypatch.setattr(Runtime,'__init__',forbidden)
    data=main('Uncatalogued Track');data['window']['process_name']=process;original=deepcopy(data);current=view(data)
    assert current['view']=='milestone_main' and not current['controls']
    context=current['items'][0]
    assert context['track_label']=='Uncatalogued Track'
    assert context['cost']=={'currency':'to_essence','cost':40,'available':64}
    assert context['claim_enabled'] is None and context['claim_completed'] is None
    assert context['progress_step'] is None and context['reward_identity'] is None and data==original


def test_unread_or_ambiguous_track_does_not_hide_proven_numbers():
    for duplicate in (False,True):
        data=main()
        if duplicate:data['text'].append({'text':'Another title','box':[600,500,200,19],'score':.99})
        else:data['text']=[r for r in data['text'] if r['box'][1]!=465]
        current=view(data);context=current['items'][0]
        assert current['view']=='milestone_main' and context['track_label'] is None
        assert context['claim_cost']==40 and context['essence_balance']==64


@pytest.mark.parametrize('key',['milestone_read_header','milestone_read_receive'])
def test_missing_native_composition_cannot_identify_main(key):
    data=main();data['matches'][key]['hit']=False
    assert view(data)=={}


def test_changed_currency_balance_does_not_hide_current_main_or_invent_origin_balance():
    data=main();data['matches']['milestone_read_currencies']['hit']=False
    data['matches']['milestone_read_essence']=native_number(73,[822,21,24,23])
    data['matches']['milestone_read_cost']=native_number(60,[640,571,25,22])
    tree=build_tree(data);current=operation_view({'ui_tree':tree});context=current['items'][0]
    assert current['view']=='milestone_main'
    assert context['cost']=={'currency':'to_essence','cost':60,'available':73}
    assert context['origin_coin_balance'] is None and context['claim_enabled'] is None
    sources=tree['nodes']['operation:milestone_main/context']['fields']['cost']['sources']
    assert all(s['pointer']!='/matches/milestone_read_currencies' for s in sources)
    data['matches']['milestone_read_essence']['hit']=False
    context=view(data)['items'][0]
    assert context['claim_cost']==60 and context['essence_balance'] is None and context['cost'] is None


@pytest.mark.fixtures
def test_current_milestone_checkpoint_reuses_native_readings():
    import json
    from driver_epic_seven.config import ROOT
    path=ROOT/'var/runs/20261028T012258Z_711fed77/agent_000013.json'
    if not path.exists():pytest.skip('Private Milestone checkpoint unavailable.')
    data=json.loads(path.read_text(encoding='utf-8'))['result'];original=deepcopy(data)
    current=view(data);context=current['items'][0]
    assert current['view']=='milestone_main' and context['track_label']=='Dawning Trajectory'
    assert context['cost']=={'currency':'to_essence','cost':60,'available':73}
    assert context['origin_coin_balance'] is None and not current['controls']
    assert data==original


@pytest.mark.parametrize('mutation',['multiple','low_score','absent','negative','decimal'])
def test_numeric_guard_preserves_other_readable_fields(mutation):
    data=main();number=data['matches']['milestone_read_cost']
    if mutation=='multiple':number['filtered_candidates']*=2
    elif mutation=='low_score':number['score']=.97
    elif mutation=='absent':number['hit']=False
    elif mutation=='negative':number['text']='-1'
    else:number['text']='4.5'
    context=view(data)['items'][0]
    assert context['claim_cost'] is None and context['cost'] is None
    assert context['essence_balance']==64 and context['track_label']=='A Different Trajectory'


def test_free_cost_and_limited_receive_are_read_without_inventing_eligibility():
    data=main();data['matches']['milestone_read_cost']=native_number(0,[1060,565,30,20])
    data['matches']['milestone_read_receive']['hit']=False
    data['matches']['milestone_read_receive_limited']={'hit':True,'box':[1050,610,65,25]}
    context=view(data)['items'][0]
    assert context['claim_cost']==0 and context['cost']['cost']==0 and context['claim_enabled'] is None


def test_partial_selector_or_two_button_modal_does_not_fall_through_to_main():
    for partial in (False,True):
        data=main()
        if partial:data['matches']['coreloop_selector_confirmation']={'hit':True,'box':[500,170,180,30]}
        else:data['text'] += [{'text':'Confirm','box':[680,430,80,25],'score':.99},
                             {'text':'Cancel','box':[480,430,80,25],'score':.99}]
        assert view(data)=={}
