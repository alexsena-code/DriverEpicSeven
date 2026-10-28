"""Adventure labels are requirements, not proof of account star progress."""
from copy import deepcopy
import json

import pytest

from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree, operation_view, fact


def preparation():
    rows = [('Start Quest', [1030,610,120,25]),
            ('Secluded Laboratory', [876,71,178,23]),
            ('Hidden Plan', [877,112,92,18]), ('No Record', [1097,109,91,25]),
            ('Initial Clear', [914,162,92,24]),
            ('Clear with No Continues', [914,190,193,21]),
            ('Have 1 Ice Hero in the Team', [914,219,223,20])]
    return {'state':'battle_ready', 'window':{'client_size':[1212,682]}, 'epoch_seconds':1,
            'text':[{'text':text, 'box':box, 'score':.99} for text,box in rows]}


def test_requirement_labels_do_not_assert_stars_or_stage_identity():
    tree = build_tree(preparation())
    data = operation_view({'ui_tree':tree})
    assert data['view'] == 'campaign_preparation'
    context, *objectives = data['items']
    assert context['story_title'] == 'Hidden Plan' and context['record_label'] == 'No Record'
    assert context['stage_id'] is None and context['earned_stars'] is None
    assert context['objectives_complete'] is None
    assert [o['condition'] for o in objectives] == ['clear_enter_count',
        'clearnocontinue_enter_count', 'party_enter_attribute_count']
    assert objectives[2]['parameters'] == {'count':1, 'attribute':'ice'}
    assert all(o['completed'] is None and o['status'] is None for o in objectives)
    assert not data['controls']  # Requirement mapping does not enable a generic Start.
    f = tree['nodes']['operation:campaign_preparation/objective:3']['fields']
    assert f['text']['sources'][0]['pointer'] == '/text/6'
    assert f['completed'] == fact()


def test_current_inspector_identity_is_required_for_linked_stage():
    o = preparation()
    o['stage'] = {'requested_id':'epi009','identity_verified':False}
    assert operation_view(o)['items'][0]['stage_id'] is None
    o['stage']['identity_verified'] = True
    assert operation_view(o)['items'][0]['stage_id'] == 'epi009'


def test_ambiguous_or_missing_objective_and_unmapped_condition_stay_unknown():
    o = preparation()
    o['text'].append({'text':'Have 2 Fire Heroes in the Team','box':[914,219,240,20],'score':.99})
    third = operation_view(o)['items'][3]
    assert third['text'] is None and third['condition'] is None and third['completed'] is None
    o = preparation()
    o['text'][-1]['text'] = 'Clear with 2 Knights'
    third = operation_view(o)['items'][3]
    assert third['text'] == 'Clear with 2 Knights' and third['parameters'] is None


def test_wrong_resolution_state_low_confidence_or_closeable_overlay_do_not_expose_objectives():
    variants=[]
    o=preparation(); o['state']='orbis_guide'; variants.append(o)
    o=preparation(); o['window']['client_size']=[1280,720]; variants.append(o)
    o=preparation(); o['text'][0]['score']=.5; variants.append(o)
    o=preparation(); o['text'].append({'text':'Tap to close','box':[550,500,120,25],'score':.99}); variants.append(o)
    o=preparation(); o['text'].extend([
        {'text':'Cancel','box':[380,500,80,25],'score':.99},
        {'text':'Confirm','box':[600,500,90,25],'score':.99}]); variants.append(o)
    for observation in variants:
        assert operation_view(observation) == {}


@pytest.mark.fixtures
def test_native_preparation_ocr_replay_preserves_sources_and_does_not_mutate_evidence():
    path=ROOT/'var/runs/20261026T232415Z_779607cb/agent_000003.json'
    if not path.exists():
        pytest.skip('Private saved preparation not available.')
    original=json.loads(path.read_text(encoding='utf-8'))['result']
    before=deepcopy(original)
    data=operation_view({'ui_tree':build_tree(original)})
    assert data['view']=='campaign_preparation'
    assert data['items'][3]['parameters']=={'count':1,'attribute':'ice'}
    assert data['items'][0]['stage_id'] is None
    assert original==before
