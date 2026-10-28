"""Replay only saved Maa OCR; these tests never connect a game controller."""
from copy import deepcopy
import json

import pytest

from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree, operation_view, query_operation_control, fact


EQUIPMENT = '20261026T231721Z_98aecbed'
PROGRESSION = '20261026T232625Z_eef54186'


def saved(run, number):
    path = ROOT/'var/runs'/run/f'agent_{number:06}.json'
    if not path.exists():
        pytest.skip('Private saved observation unavailable; no live capture is used.')
    return json.loads(path.read_text(encoding='utf-8'))['result']


def view(observation):
    return operation_view({'ui_tree': build_tree(observation)})


@pytest.mark.fixtures
@pytest.mark.parametrize('number,expected,cp', [(15,'hero_equipment',106177), (21,'hero_equipment',77532),
    (45,'hero_equipment',25832), (55,'hero_equipment',106177)])
def test_equipment_views_do_not_turn_cp_or_missing_text_into_item_identity(number, expected, cp):
    data = view(saved(EQUIPMENT, number))
    assert data['view'] == expected
    context = data['items'][0]
    assert context['hero_name'] == 'Sigret' and context['cp'] == cp
    assert context['hero_instance_id'] is None
    assert context['equipment_slots'] is None and context['equipped_items'] is None
    assert all(control['enabled'] is None for control in data['controls'])
    controls = {c['semantic_id']: c for c in data['controls']}
    assert controls['equip_all']['consuming'] is False
    if 'unequip_all' in controls:
        assert controls['unequip_all']['consuming'] is True


@pytest.mark.fixtures
def test_equipment_popup_selection_preview_and_final_confirmation_are_distinct():
    detail = view(saved(EQUIPMENT,18))
    assert detail['view'] == 'equipment_detail'
    assert detail['items'][0]['item_name'] == 'Hellish Essence Orb'
    assert detail['items'][0]['equipment_score'] == 80
    selected = view(saved(EQUIPMENT,35))
    assert selected['view'] == 'equipment_selection'
    assert selected['items'][0]['selection_applied'] is None
    assert [c['semantic_id'] for c in selected['controls']] == ['equip']
    preview = view(saved(EQUIPMENT,48))
    assert preview['view'] == 'equip_all_preview'
    assert preview['items'][0]['current_cp'] == 25832
    assert preview['items'][0]['candidate_cp'] == 106177
    assert preview['controls'][0]['consuming'] is False
    tree = build_tree(saved(EQUIPMENT,51))
    confirm = operation_view({'ui_tree': tree})
    assert confirm['view'] == 'equipment_change_confirmation'
    assert confirm['items'][0]['current_cp'] == 25832
    assert confirm['items'][0]['candidate_cp'] == 106177
    assert {c['semantic_id'] for c in confirm['controls']} == {'confirm_change','cancel'}
    control = query_operation_control(tree,'equipment_change_confirmation','confirm_change')['node']
    assert control['fields']['consuming']['value'] is True
    assert control['fields']['enabled'] == fact()
    assert control['fields']['box']['sources'][0]['kind'] == 'ocr'
    assert control['layout_reference']['scope'] == 'static_hint'
    # A partially recognized modal must not expose its underlying preview.
    partial = saved(EQUIPMENT,51)
    partial['text'] = [r for r in partial['text'] if 'will change' not in r['text']]
    assert view(partial) == {}


@pytest.mark.fixtures
def test_no_better_equipment_is_an_observed_message_not_an_optimizer_claim():
    data = view(saved(EQUIPMENT,41))
    assert data['view'] == 'hero_equipment'
    assert data['items'][0]['recommendation_status'] == 'no_better_equipment'
    assert data['items'][0]['equipped_items'] is None


@pytest.mark.fixtures
def test_artifact_exp_and_gold_use_current_preview_regions_not_header_or_stock():
    original = saved(PROGRESSION,43)
    tree = build_tree(original)
    data = operation_view({'ui_tree':tree})
    assert data['view'] == 'item_enhancement'
    assert data['items'][0]['exp'] == 'exp 1,818/360'
    assert data['items'][0]['gold_cost'] == 17280
    assert data['controls'][0]['semantic_id'] == 'enhance'
    assert data['controls'][0]['consuming'] is True
    cost = tree['nodes']['operation:item_enhancement/context']['fields']['gold_cost']
    index = int(cost['sources'][0]['pointer'].split('/')[-1])
    assert original['text'][index]['text'] == '17,280'
    ambiguous = deepcopy(original)
    ambiguous['text'].append({'text':'18,000','box':[480,640,70,20],'score':.99})
    assert view(ambiguous)['items'][0]['gold_cost'] is None
    assert view(saved(PROGRESSION,26))['items'][0]['gold_cost'] is None  # zero was not read


@pytest.mark.fixtures
def test_artifact_result_replaces_underlying_enhance_control_and_preserves_instance_unknown():
    for number, before, after in [(47,1,2),(81,2,3)]:
        data = view(saved(PROGRESSION,number))
        assert data['view'] == 'artifact_skill_result'
        assert data['items'][0]['before_level'] == before
        assert data['items'][0]['after_level'] == after
        assert data['items'][0]['item_instance_id'] is None
        assert [c['semantic_id'] for c in data['controls']] == ['close_result']
    data = view(saved(PROGRESSION,85))
    assert data['view'] == 'artifact_detail'
    assert data['items'][0]['item_name'] == 'Daydream Joker'
    assert data['items'][0]['skill_level'] == 'Lv.3/6'
    assert data['items'][0]['attack'] == 60 and data['items'][0]['health'] == 53


@pytest.mark.fixtures
@pytest.mark.parametrize('number,name', [(104,'Leap Strike'),(140,'Coldhearted Management'),(149,'Wind Cutter')])
def test_skill_confirmation_has_its_own_cost_and_does_not_expose_underlying_button(number,name):
    original = saved(PROGRESSION,number)
    data = view(original)
    assert data['view'] == 'hero_skill_confirmation'
    assert data['items'][0]['selected_skill_name'] == name
    assert data['items'][0]['gold_cost'] == 2000
    assert data['items'][0]['material_count'] == 120
    assert data['items'][0]['material_currency'] is None
    assert {c['semantic_id'] for c in data['controls']} == {'cancel','confirm_enhancement'}
    partial = deepcopy(original)
    partial['text'] = [r for r in partial['text'] if r['text'] != 'Consumed Resources']
    assert view(partial) == {}


@pytest.mark.fixtures
def test_skill_gold_accepts_calibrated_thousands_ocr_but_keeps_ambiguity_unknown():
    assert view(saved(PROGRESSION,107))['items'][0]['gold_cost'] == 4000
    assert view(saved(PROGRESSION,152))['items'][0]['gold_cost'] == 4000
    original = saved(PROGRESSION,107)
    original['text'].append({'text':'5,000','box':[1040,540,50,20],'score':.99})
    assert view(original)['items'][0]['gold_cost'] is None


@pytest.mark.fixtures
def test_quick_result_does_not_reuse_ranked_result_or_infer_npc_from_a_name():
    original = saved(PROGRESSION,184)
    data = view(original)
    assert data['view'] == 'arena_quick_result'
    assert data['items'][0]['result'] == 'victory'
    assert data['items'][0]['opponent_label'] == "Phantom CIC's Training"
    assert data['items'][0]['arena_type'] is None
    assert {c['semantic_id'] for c in data['controls']} == {'confirm_result','battle_results'}
    original['text'] = [r for r in original['text'] if r['text'] != 'Battle Results']
    assert view(original) == {}


@pytest.mark.fixtures
def test_ranked_streak_header_is_an_observed_list_variant_not_selected_opponent():
    original = saved(PROGRESSION,231)
    data = view(original)
    assert data['view'] == 'arena_opponents'
    assert data['items'][0]['consecutive_victories'] == 2
    assert data['items'][0]['flags'] == '3/5'
    assert data['items'][0]['selected_opponent'] is None
    assert all(i.get('selected') is None for i in data['items'][1:])


@pytest.mark.fixtures
def test_npc_battle_result_has_explicit_modality_without_inventing_victory_points():
    data = view(saved(PROGRESSION,268))
    assert data['view'] == 'arena_result'
    assert data['items'][0]['arena_type'] == 'npc'
    assert data['items'][0]['result'] == 'victory'
    assert data['items'][0]['victory_points'] is None
    assert {c['semantic_id'] for c in data['controls']} == {'confirm_result','battle_results'}


@pytest.mark.fixtures
def test_calibrated_abyss_next_floor_opens_preparation_without_starting_it():
    data = view(saved(PROGRESSION,298))
    assert data['view'] == 'abyss_result' and data['items'][0]['floor'] == 32
    next_floor = next(c for c in data['controls'] if c['semantic_id'] == 'next_floor')
    assert next_floor['consuming'] is False
    assert 'start' not in {c['semantic_id'] for c in data['controls']}
    destination = view(saved(PROGRESSION,301))
    assert destination['view'] == 'abyss_preparation'
    assert destination['items'][0]['floor'] == 33
    assert destination['items'][0]['cost'] == {'currency':'energy','cost':10,'available':986}


@pytest.mark.fixtures
def test_new_panels_reject_wrong_resolution_low_confidence_and_known_unrelated_overlay():
    for run,number in [(EQUIPMENT,48),(EQUIPMENT,51),(PROGRESSION,104),(PROGRESSION,184)]:
        original = saved(run,number)
        wrong_size = deepcopy(original); wrong_size['window']['client_size'] = [1280,720]
        assert view(wrong_size) == {}
        low = deepcopy(original)
        for row in low['text']: row['score'] = .5
        assert view(low) == {}
        overlay = deepcopy(original); overlay['state'] = 'orbis_guide'
        assert view(overlay) == {}
