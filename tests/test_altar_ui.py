"""Altar reading is generic content in a current, read-only composition."""
from copy import deepcopy
import json

import pytest

from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree, operation_view, validate_tree


def observation(rows):
    return {'state':'unknown','window':{'process_name':'EpicSeven.exe','client_size':[1212,682]},
            'matches':{},'text':[{'text':text,'box':box,'score':.99} for text,box in rows]}


def hub(name='Twilight Spirit Altar'):
    return observation([('Battle',[61,18,67,27]),('Spirit Altar',[35,145,159,35]),
        ('Available Altars',[1020,91,125,18]),(name+' - Easy',[739,162,181,21]),
        ('Available',[738,188,68,17]),(name+' - Hard',[742,368,180,18]),
        ('B Locked',[743,389,81,23]),(name,[987,285,149,22])])


def prep(name='Twilight Spirit Altar'):
    return observation([('Ready',[63,20,67,27]),('Spirit Altar',[21,80,85,17]),
        ('Team1',[39,99,58,17]),('Team 2',[37,155,61,18]),
        (name,[881,78,130,22]),(name+'-Easy',[879,117,167,20]),
        ('Enemies',[883,268,103,22]),('Obtainable Rewards',[886,431,189,21]),
        ('Team CP',[258,599,75,20]),('Start',[1049,615,46,24]),
        ('9/846',[930,618,58,22]),('36,643',[238,625,114,35]),('42',[503,188,17,11])])


def view(data):
    tree=build_tree(data);validate_tree(tree)
    return operation_view({'ui_tree':tree})


@pytest.mark.parametrize('process',['EpicSeven.exe','EpicSeven_Steam.exe'])
def test_hub_uses_current_names_and_explicit_available_rows_without_proving_selection(process):
    data=hub();data['window']['process_name']=process;original=deepcopy(data);current=view(data)
    assert current['view']=='spirit_altar_hub'
    context=current['items'][0]
    assert context['listed_altar_name']=='Twilight Spirit Altar'
    assert context['selected_altar_name'] is None and context['selected_difficulty'] is None
    easy=next(i for i in current['items'] if i['semantic_id']=='difficulty:easy')
    hard=next(i for i in current['items'] if i['semantic_id']=='difficulty:hard')
    assert easy['available'] is True and hard['available'] is False
    assert easy['stage_id'] is None and easy['selected'] is None
    assert [c['semantic_id'] for c in current['controls']]==['open_difficulty:easy']
    assert current['controls'][0]['consuming'] is False and current['controls'][0]['enabled'] is None
    assert data==original


def test_missing_status_or_duplicate_difficulty_does_not_expose_navigation():
    data=hub();data['text']=[r for r in data['text'] if r['text']!='Available']
    current=view(data)
    assert not current['controls'] and current['items'][1]['available'] is None
    data=hub();data['text'] += [{'text':'Other Spirit Altar - Easy','box':[739,267,181,21],'score':.99},
                               {'text':'Available','box':[738,293,68,17],'score':.99}]
    current=view(data)
    assert current['items'][0]['listed_altar_name'] is None and not current['controls']


def test_preparation_retains_cost_cp_and_unknown_team_ownership_without_connecting(monkeypatch):
    from driver_epic_seven.runtime import Runtime
    def forbidden(*args,**kwargs):raise AssertionError('A reader must not connect')
    monkeypatch.setattr(Runtime,'__init__',forbidden)
    data=prep();original=deepcopy(data);current=view(data);context=current['items'][0]
    assert current['view']=='spirit_altar_preparation'
    assert context['altar_name']=='Twilight Spirit Altar' and context['difficulty']=='easy'
    assert context['cost']=={'currency':'energy','cost':9,'available':846} and context['team_cp']==36643
    assert context['team_label'] is None and context['selected_team_id'] is None and context['hero_instances'] is None
    assert context['visible_team_labels']==['Team1','Team 2'] and context['visible_hero_levels']==[42]
    assert context['stage_id'] is None and context['entered'] is None and context['victory'] is None
    assert current['controls'][0]['semantic_id']=='start' and current['controls'][0]['consuming'] is True
    assert current['controls'][0]['enabled'] is None and data==original


def test_unread_cost_and_conflicting_identity_do_not_hide_other_fields():
    data=prep();data['text']=[r for r in data['text'] if r['text']!='9/846']
    current=view(data);context=current['items'][0]
    assert context['cost'] is None and context['team_cp']==36643
    data=prep();data['text'][4]['text']='Different Spirit Altar'
    context=view(data)['items'][0]
    assert context['identity_conflict'] is True and context['altar_name'] is None and context['difficulty'] is None
    assert context['team_cp']==36643 and context['cost']['cost']==9


def test_preparation_handles_current_cp_jitter_and_missing_short_title_without_lowering_confidence():
    data=prep();data['text']=[r for r in data['text'] if r['box']!=[881,78,130,22]]
    cp=next(r for r in data['text'] if r['text']=='36,643');cp['box'][1]=615
    context=view(data)['items'][0]
    assert context['team_cp']==36643 and context['altar_name']=='Twilight Spirit Altar'
    assert context['difficulty']=='easy' and context['identity_conflict'] is None
    cp['score']=.89
    assert view(data)['items'][0]['team_cp'] is None
    cp['score']=.99
    data['text'].append({'text':'15,000','box':[240,612,100,25],'score':.99})
    assert view(data)['items'][0]['team_cp'] is None


@pytest.mark.parametrize('missing',['Ready','Spirit Altar','Enemies','Obtainable Rewards'])
def test_preparation_requires_its_full_composition(missing):
    data=prep();data['text']=[r for r in data['text'] if r['text']!=missing]
    assert view(data)=={}


def test_confirm_overlay_prevents_underlying_altar_controls():
    for data in (prep(),hub()):
        data['text'] += [{'text':'Confirm','box':[680,430,80,25],'score':.99},
                         {'text':'Cancel','box':[480,430,80,25],'score':.99}]
        assert view(data)=={}


def test_generic_clear_banner_uses_two_native_proofs_without_assuming_stars_or_mode():
    data=observation([])
    data['matches']={'path_battle_clear_heading':{'hit':True,'box':[508,254,205,41],'score':.99},
                     'path_battle_clear_dim_hud':{'hit':True,'box':[934,13,39,39],'score':.99}}
    current=view(data);assert current['view']=='battle_clear_banner' and current['mode'] is None
    context=current['items'][0]
    assert context['result']=='victory' and context['victory_announced'] is True
    assert all(context[k] is None for k in ('earned_stars','mode_identity','stage_id','battle_id','reward_claimed','mission_credit'))
    control=current['controls'][0]
    assert control['semantic_id']=='advance' and control['gesture']=='tap'
    assert control['consuming'] is False and control['enabled'] is None
    assert control['box']==[508,254,205,41]
    for key in data['matches']:
        changed=deepcopy(data);changed['matches'][key]['hit']=False
        assert view(changed)=={}
    changed=deepcopy(data);changed['matches']['path_battle_clear_heading']['box'][1]=405
    assert view(changed)=={}  # Three-star campaign CLEAR is a different composition.
    for data in (prep(),hub()):
        data['text'].append({'text':'X Tap to close','box':[550,645,110,24],'score':.99})
        assert view(data)=={}


@pytest.mark.fixtures
@pytest.mark.parametrize('number,expected',[(19,'spirit_altar_hub'),(25,'spirit_altar_preparation')])
def test_saved_altar_compositions_preserve_field_provenance(number,expected):
    p=ROOT/f'var/runs/20261028T003518Z_618dae53/agent_{number:06}.json'
    if not p.exists():pytest.skip('Private current Altar observation unavailable.')
    data=json.loads(p.read_text(encoding='utf-8'))['result'];original=deepcopy(data)
    tree=build_tree(data);assert operation_view({'ui_tree':tree})['view']==expected
    for item in tree['nodes'].values():
        for field in item['fields'].values():
            if field['value'] is not None:assert field['sources']
    assert data==original
