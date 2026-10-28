"""TAG and a current Rinak counter do not prove selection, readiness or an owned kit."""
from copy import deepcopy
import json

import pytest

from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree, operation_view, target_box, fact


RUN = ROOT / 'var/runs/20261027T045511Z_1ec60bbf'


def saved(number):
    path = RUN / f'agent_{number:06}.json'
    if not path.exists():
        pytest.skip('Private STOVE TAG and Rinak frames unavailable.')
    return json.loads(path.read_text(encoding='utf-8'))['result']


def view(data):
    return operation_view({'ui_tree': build_tree(data)})


@pytest.mark.fixtures
def test_tag_prompt_keeps_hud_ancestry_and_action_result_unknown():
    data = saved(30)
    original = deepcopy(data)
    tree = build_tree(data)
    current = operation_view({'ui_tree': tree})
    assert current['view'] == 'battle_tag_tutorial'
    context = current['items'][0]
    assert context['prompt_text'] == 'Change Heroes using Tag'
    assert context['opponent_label'] == 'Nilgal'
    assert context['static_binding_hint'] == 'btn_tag'
    for key in ('hud_control_path', 'actor_before', 'actor_after', 'swap_completed', 'hero_instance_id'):
        assert context[key] is None
    assert len(current['controls']) == 1
    label = current['controls'][0]
    assert label['text'] == 'TAG' and label['enabled'] is None
    assert target_box(tree, 'tag_label') is None
    assert tree['nodes']['operation:battle_tag_tutorial/tag_label'].get('layout_reference') is None
    assert data == original
    # All three current lines belong to the same observed composition.
    for mutation in ('missing_prompt', 'duplicate_label', 'low_score', 'wrong_boss', 'wrong_state', 'steam', 'size'):
        data = deepcopy(original)
        row = next(row for row in data['text'] if row['text'] == 'TAG')
        if mutation == 'missing_prompt':
            data['text'] = [r for r in data['text'] if r['text'] != 'Change Heroes using Tag']
        elif mutation == 'duplicate_label':
            data['text'].append(deepcopy(row))
        elif mutation == 'low_score':
            row['score'] = .89
        elif mutation == 'wrong_boss':
            next(r for r in data['text'] if r['text'] == 'Nilgal')['text'] = 'Another enemy'
        elif mutation == 'wrong_state':
            data['state'] = 'battle_running'
        elif mutation == 'steam':
            data['window']['process_name'] = 'Other.exe'
        else:
            data['window']['client_size'] = [1280, 720]
        assert view(data).get('view') != 'battle_tag_tutorial'


@pytest.mark.fixtures
@pytest.mark.parametrize('number,count,cooldown', [(33, 0, None), (36, 3, 3)])
def test_rinak_resource_is_current_text_not_static_skill_or_readiness(number, count, cooldown):
    data = saved(number)
    original = deepcopy(data)
    tree = build_tree(data)
    current = operation_view({'ui_tree': tree})
    assert current['view'] == 'battle_skill_selection' and not current['controls']
    context = current['items'][0]
    assert context['actor_label'] == 'Rinak'
    assert context['actor_hp_text'] == '915/915'
    assert context['resource_counter_text'] == f'{count}/5'
    assert context['resource_counter'] == {'current': count, 'maximum': 5}
    for key in ('resource_kind', 'runtime_variant_id', 'hero_instance_id', 'skill_id', 'selected_slot',
                'turn_accepts_input', 'auto_enabled', 'auto_available', 'action_completed', 'enabled'):
        assert context[key] is None
    slots = {item['slot']: item for item in current['items'] if item['semantic_id'] == 'skill_slot'}
    assert slots[3]['cooldown_turns'] == cooldown
    assert all(item['selected'] is None and item['enabled'] is None for item in slots.values())
    fields = tree['nodes']['operation:battle_skill_selection/context']['fields']
    for key in ('actor_hp_text', 'resource_counter_text', 'resource_counter'):
        pointer = next(s['pointer'] for s in fields[key]['sources'] if s['kind'] == 'ocr')
        row = data['text'][int(pointer.split('/')[-1])]
        assert row['text'] == ('915/915' if key == 'actor_hp_text' else f'{count}/5')
    assert fields['runtime_variant_id'] == fact()
    assert data == original


@pytest.mark.fixtures
def test_resource_counter_rejects_ambiguous_misplaced_or_other_actor_rows():
    original = saved(36)
    for mutation in ('duplicate', 'low_score', 'hp_region', 'invalid_range', 'other_actor', 'duplicate_actor'):
        data = deepcopy(original)
        row = next(r for r in data['text'] if r['text'] == '3/5')
        if mutation == 'duplicate':
            data['text'].append({**row, 'text': '4/5'})
        elif mutation == 'low_score':
            row['score'] = .89
        elif mutation == 'hp_region':
            row['box'] = [305, 635, 28, 15]
        elif mutation == 'invalid_range':
            row['text'] = '6/5'
        elif mutation == 'other_actor':
            next(r for r in data['text'] if r['text'] == 'Rinak')['text'] = 'Victorika'
        else:
            data['text'].append(deepcopy(next(r for r in data['text'] if r['text'] == 'Rinak')))
        context = view(data)['items'][0]  # Existing current cooldown still identifies the panel.
        assert context['resource_counter_text'] is None and context['resource_counter'] is None
    for mutation in ('unknown', 'no_hud', 'steam', 'empty'):
        data = deepcopy(original)
        if mutation == 'unknown':
            data['state'] = 'unknown'
        elif mutation == 'no_hud':
            data['matches']['battle_pause']['hit'] = False
        elif mutation == 'steam':
            data['window']['process_name'] = 'Other.exe'
        else:
            data['text'] = []
        assert view(data) == {}
