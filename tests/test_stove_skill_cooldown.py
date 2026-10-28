"""Cooldown OCR is a current label; missing text never means ready or enabled."""
from copy import deepcopy
import json
import pytest
from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree, operation_view, auto_state, fact


def saved(number):
    p=ROOT/'var/runs/20261027T020703Z_0dc452c4'/f'agent_{number:06}.json'
    if not p.exists():pytest.skip('Private Hugo cooldown frames unavailable.')
    return json.loads(p.read_text(encoding='utf-8'))['result']


def view(data):return operation_view({'ui_tree':build_tree(data)})


@pytest.mark.fixtures
@pytest.mark.parametrize('number,expected',[(1,{3:1}),(4,{2:2}),(7,{2:1,3:2})])
def test_cooldown_text_and_count_use_current_slot_and_keep_missing_unknown(number,expected):
    d=saved(number);original=deepcopy(d);tree=build_tree(d);v=operation_view({'ui_tree':tree})
    assert v['view']=='battle_skill_selection' and not v['controls']
    context=v['items'][0]
    assert context['actor_label']=='Guard Captain Krau'
    assert context['highlighted_slot'] is None  # Saved original markers did not recognize it.
    for key in ('selected_slot','auto_enabled','auto_available','turn_accepts_input','action_completed'):
        assert context[key] is None
    slots=[item for item in v['items'] if item['semantic_id']=='skill_slot']
    assert len(slots)==3
    for item in slots:
        want=expected.get(item['slot'])
        assert item['cooldown_turns']==want
        assert item['cooldown_text']==(f'{want} turn(s)' if want is not None else None)
        assert item['enabled'] is None and item['selected'] is None and item['action_completed'] is None
        field=tree['nodes'][f"operation:battle_skill_selection/slot:{item['slot']}"]['fields']['cooldown_text']
        if want is None:assert field==fact()
        else:
            index=int(field['sources'][0]['pointer'].split('/')[-1])
            assert d['text'][index]['text']==item['cooldown_text']
            assert field['confidence']==d['text'][index]['score']
    assert auto_state({'ui_tree':tree}) is None and d==original


@pytest.mark.fixtures
def test_ambiguous_low_confidence_or_outside_slot_cooldowns_stay_unknown():
    base=saved(7)
    for mutate in ('duplicate','low_score','outside'):
        d=deepcopy(base);row=next(r for r in d['text'] if r['text']=='1 turn(s)')
        if mutate=='duplicate':d['text'].append({**row,'text':'3 turn(s)'})
        elif mutate=='low_score':row['score']=.89
        else:row['box']=[500,400,75,22]
        slots={i['slot']:i for i in view(d)['items'] if i['semantic_id']=='skill_slot'}
        assert slots[2]['cooldown_text'] is None and slots[2]['cooldown_turns'] is None
        assert slots[3]['cooldown_turns']==2
    d=deepcopy(base);d['state']='unknown';assert view(d)=={}
    d=deepcopy(base);d['matches']['battle_pause']['hit']=False;assert view(d)=={}
    d=deepcopy(base);d['text']=[];assert view(d)=={}  # No carryover from an earlier read.
