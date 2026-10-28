from copy import deepcopy
import json
from types import SimpleNamespace

import numpy as np
import pytest

from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import (build_tree, operation_view, query_operation_control,
                                          auto_state, fact)
from driver_epic_seven.runtime import Runtime
from driver_epic_seven.vision import Vision, pixel_error


def observation(*rows, state='unknown', matches=None):
    return {'state': state, 'epoch_seconds': 1, 'window': {'client_size': [1212, 682]},
            'matches': matches or {},
            'text': [{'text': text, 'box': box, 'score': .98} for text, box in rows]}


def arena_ready(*extra):
    return observation(('Rookie Arena', [60, 15, 180, 30]), ('Start', [777, 614, 47, 24]),
                       ('231,905', [469, 520, 147, 39]), ('Add Team', [10, 630, 100, 25]),
                       ('129 pts.', [815, 541, 80, 24]), ('5/5', [560, 15, 40, 24]),
                       ('1/5', [685, 616, 34, 23]), *extra)


def test_cost_is_current_button_counter_and_fields_keep_provenance():
    o = arena_ready()
    tree = build_tree(o)
    view = operation_view({'ui_tree': tree})
    assert view['view'] == 'arena_preparation'
    info = view['items'][0]
    assert info['cost'] == {'currency': 'arena_flag', 'cost': 1, 'available': 5}
    assert info['team_cp'] == 231905 and info['arena_type'] == 'normal'
    assert info['team_instance_id'] is None and info['opponent_instance_id'] is None
    start = query_operation_control(tree, 'arena_preparation', 'start')['node']
    assert start['fields']['consuming']['value'] is True
    assert start['fields']['enabled'] == fact()
    assert start['fields']['box_role']['value'] == 'text_anchor'
    assert start['fields']['box']['sources'][0]['pointer'] == '/text/1'
    with pytest.raises(ValueError):
        query_operation_control(tree, 'arena_npc_list', 'start')
    ambiguous = arena_ready(('2/5', [680, 640, 40, 23]))
    assert operation_view(ambiguous)['items'][0]['cost'] is None


def test_entry_warning_does_not_expose_underlying_start():
    o = arena_ready(('Low Level Hero', [500, 175, 220, 30]),
        ('There is a low-level Hero on your team.', [410, 280, 400, 25]),
        ('Confirm', [570, 495, 70, 25]), ('Cancel', [370, 495, 70, 25]),
        ('Do Not Display', [740, 495, 135, 25]))
    view = operation_view(o)
    assert view['view'] == 'arena_entry_warning'
    assert {c['semantic_id'] for c in view['controls']} == {'cancel', 'confirm_entry', 'suppress_and_enter'}
    assert next(c for c in view['controls'] if c['semantic_id'] == 'confirm_entry')['consuming']
    o['text'].append({'text': 'Tap to close', 'box': [550, 645, 120, 25], 'score': .99})
    o['text'] = [r for r in o['text'] if r['text'] != 'Low Level Hero']
    assert operation_view(o) == {}


def test_selected_floor_is_not_the_available_or_last_conquered_floor():
    o = observation(('Abyss', [40, 150, 110, 40]), ('Floor 32', [983, 201, 175, 48]),
        ('Conquer Reward', [1005, 304, 155, 25]), ('Floor 30', [718, 144, 75, 22]),
        ('Conquered', [740, 172, 90, 20]), ('Floor 31', [718, 241, 75, 22]),
        ('Available', [740, 267, 90, 20]), ('Floor 32', [718, 338, 75, 22]),
        ('Cannot proceed.', [740, 367, 140, 20]), ('Move to Floor 31', [993, 624, 134, 17]))
    view = operation_view(o)
    assert view['items'][0]['floor'] == 32
    assert [i['status'] for i in view['items'][1:]] == ['conquered', 'available', 'locked']
    assert all(i['selected'] is None for i in view['items'][1:])
    assert [c['semantic_id'] for c in view['controls']] == ['move_to_floor']
    o['text'].append({'text': 'Floor 33', 'box': [965, 220, 180, 45], 'score': .99})
    assert operation_view(o) == {}  # two possible detail titles


def test_arena_list_keeps_name_fragments_without_promoting_point_labels_or_selection():
    o = observation(('Rookie Arena',[60,15,180,30]), ('Opponents',[310,95,150,30]),
        ('Challenge',[560,614,92,25]), ('Alice',[374,194,90,24]),
        ('O pts.',[374,230,60,24]), ('156 pts.',[374,350,80,24]))
    items = operation_view(o)['items']
    assert [n['text'] for n in items[1:]] == ['Alice']
    assert items[1]['semantic_id'] == 'opponent_label_fragment'
    assert items[1]['selected'] is None and items[0]['selected_opponent'] is None


def test_unrelated_overlay_wrong_size_low_confidence_and_incomplete_frame_stay_unknown():
    o = arena_ready()
    o['state'] = 'orbis_guide'
    assert operation_view(o) == {}
    o['state'] = 'unknown'
    o['window']['client_size'] = [1280, 720]
    assert operation_view(o) == {}
    o['window']['client_size'] = [1212, 682]
    o['text'][0]['score'] = .5
    assert operation_view(o) == {}
    assert operation_view(observation(('Start', [777, 614, 47, 24]), ('1/5', [685, 616, 34, 23]))) == {}


def test_quantity_selection_is_distinct_from_applying_enhancement():
    o = observation(('Select Ingredients', [500, 175, 220, 30]),
        ('Choose ingredient amount', [495, 240, 220, 25]), ('1/697', [560, 310, 100, 35]),
        ('Select', [570, 462, 80, 25]), ('Enhance', [690, 615, 80, 25]),
        ('Enhance Equipment', [60, 15, 220, 30]))
    view = operation_view(o)
    assert view['view'] == 'ingredient_quantity'
    assert view['controls'][0]['semantic_id'] == 'select_quantity'
    assert view['controls'][0]['consuming'] is False


def test_paired_formation_controls_do_not_invent_member_or_slot_identity():
    o = observation(state='battle_ready', matches={
        'formation_remove': {'hit':True,'box':[218,336,42,19]},
        'formation_details': {'hit':True,'box':[305,328,38,39]}})
    tree = build_tree(o)
    selection = tree['nodes']['formation:selection']
    assert selection['fields']['selected_member_id'] == fact()
    assert selection['fields']['selected_slot'] == fact()
    query_operation_control(tree, 'formation_selection', 'remove_member')
    o['matches']['formation_details']['box'] = [305,480,38,39]
    assert 'formation:selection' not in build_tree(o)['nodes']
    o['state'] = 'hero_screen'
    assert 'formation:selection' not in build_tree(o)['nodes']


@pytest.mark.parametrize('on,off,expected', [(True, False, True), (False, True, False),
                                           (False, False, None), (True, True, None)])
def test_auto_requires_positive_unambiguous_hud_and_current_battle(on, off, expected):
    o = observation(state='battle_running', matches={'auto_hud_on': {'hit': on}, 'auto_hud_off': {'hit': off}})
    o['ui_tree'] = build_tree(o)
    assert auto_state(o) is expected
    assert o['ui_tree']['nodes']['battle:auto']['fields']['enabled'] == fact()
    v = Vision.__new__(Vision);v.spec = {}
    assert bool(v.target(o, {'state': 'battle_running', 'auto_state': False, 'target': 'battle_auto'})) == (expected is False)
    o.pop('ui_tree');o['state'] = 'battle_rewards'
    assert auto_state(o) is None


def test_ensure_auto_already_on_or_unknown_never_posts_input():
    runtime = Runtime.__new__(Runtime)
    runtime.observe = lambda name: observation(state='battle_running', matches={'auto_hud_on': {'hit': True}})
    assert runtime.ensure_auto()['changed'] is False
    runtime.observe = lambda name: observation(state='battle_running')
    with pytest.raises(ValueError, match='entrada não enviada'):
        runtime.ensure_auto()


def test_auto_mask_preserves_pixel_validation_of_unmasked_shape():
    template = np.full((4, 4, 3), 200, np.uint8)
    template[1:3, 1:3] = [0, 255, 0]
    frame = np.full((4, 4, 3), 200, np.uint8)
    frame[1:3, 1:3] = 0
    assert pixel_error(frame, template, [0, 0, 4, 4], green_mask=True) == 0
    assert pixel_error(frame//2, template, [0, 0, 4, 4], green_mask=True) == 100
    assert pixel_error(np.zeros_like(frame), np.full_like(frame, [0,255,0]), [0,0,4,4], green_mask=True) == float('inf')


def test_auto_graph_is_bounded_and_guarded_even_during_finish():
    graph = json.loads((ROOT/'resources/epic-seven/pipeline/auto.json').read_text(encoding='utf-8'))
    clicks = [n for n in graph.values() if isinstance(n, dict) and n.get('action') == 'Click']
    assert len(clicks) == 1 and clicks[0]['max_hit'] == 1
    assert clicks[0]['custom_recognition_param'] == {'state':'battle_running', 'auto_state':False, 'target':'battle_auto'}
    finish = json.loads((ROOT/'resources/epic-seven/pipeline/battle_finish.json').read_text(encoding='utf-8'))
    assert finish['Finish.EnableAuto']['max_hit'] == 1
    assert finish['Finish.EnableAuto']['custom_recognition_param']['auto_state'] is False
    assert 'Finish.EnableAuto' in finish['Finish.Entry']['next']


@pytest.mark.fixtures
def test_native_auto_recognition_on_private_on_off_transition_and_negative_frames(tmp_path):
    from PIL import Image
    run = ROOT/'var/runs/20261026T213404Z_9a757f4e'
    if not (run/'agent_000072.png').exists():
        pytest.skip('Private combat captures unavailable; no game connection is used.')
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    from driver_epic_seven.config import load_config
    config = load_config();vision = Vision(config['vision_file'], config['resource_dir'])
    running=vision.spec['states']['battle_running']
    names = {'auto_hud_on','auto_hud_off','auto_single_check_hint'}
    names.update(key for rule in running.get('variants',[running])
                 for clause in ('all','any','none') for key in rule.get(clause,[]))
    vision.spec['templates'] = {k:v for k,v in vision.spec['templates'].items() if k in names}
    vision.spec['states'] = {'battle_running':vision.spec['states']['battle_running']}
    vision.spec['ocr'] = {};found = []
    class Offline(CustomRecognition):
        def analyze(self, context, argv):
            a = vision.inspect(argv.image, lambda name: context.run_recognition(name, argv.image))
            found.append(a)
            return self.AnalyzeResult(box=[0,0,1,1], detail=a)
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource = Resource();resource.set_cpu();resource.register_custom_recognition('AutoFixture', Offline())
    assert resource.post_bundle(config['resource_dir']).wait().succeeded
    tasker = Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle, resource._handle)
    cases = [(run, number, expected) for number, expected in
             [(72,False),(73,False),(75,None),(76,None),(27,True),
              (23,None),(28,None),(65,None),(68,None),(77,None),(81,None),(98,None)]]
    newer = ROOT/'var/runs/20261026T232625Z_eef54186'
    if (newer/'agent_000264.png').exists():
        cases += [(newer, number, expected) for number, expected in
                  [(222,False),(264,False),(267,None),(226,None),(184,None),(256,None),(259,None),(268,None)]]
    if (newer/'agent_000297.png').exists():
        cases += [(newer,296,None),(newer,297,True)]
    for source_run, number, expected in cases:
        frame = np.asarray(Image.open(source_run/f'agent_{number:06}.png').convert('RGB'))[:,:,::-1].copy()
        variants = [(frame, expected)]
        if expected is not None or number in (76,267):
            variants.append(((frame*.45).astype(np.uint8), None))
            covered = frame.copy();covered[575:682, 800:1212] = 0;variants.append((covered,None))
        for pixels, state in variants:
            assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='AutoFixture'),pixels).wait().succeeded
            assert auto_state(observation(state=found[-1]['state'], matches=found[-1]['matches'])) is state
            if number in (76,267) and pixels is frame:
                # A single current check is retained as evidence, but cannot
                # prove the complete Auto control after shared calibration.
                assert found[-1]['matches']['auto_single_check_hint']['hit']
                assert not found[-1]['matches']['auto_hud_on']['hit']
