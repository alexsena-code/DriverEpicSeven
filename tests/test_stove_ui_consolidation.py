"""Saved STOVE compositions: current facts, overlay priority and unknowns."""
from copy import deepcopy
import json

import pytest

from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import (
    build_tree, operation_view, quest_view, query_control,
    query_operation_control, validate_tree,
)


FINAL = '20261027T091912Z_5e4ad40e'


def saved(run, number):
    path = ROOT / 'var/runs' / run / f'agent_{number:06}.json'
    if not path.exists():
        pytest.skip('Private STOVE capture unavailable.')
    result = json.loads(path.read_text(encoding='utf-8'))['result']
    assert result.get('window') and 'text' in result
    return result


def view(data):
    return operation_view({'ui_tree': build_tree(data)})


@pytest.mark.fixtures
@pytest.mark.parametrize('run,number,expected', [
    (FINAL, 1, 'hero_detail'), (FINAL, 3, 'tutorial'),
    (FINAL, 6, 'hero_awakening'), (FINAL, 9, 'hero_awakening'),
    (FINAL, 13, 'hero_awakening_result'), (FINAL, 16, 'hero_awakening'),
    (FINAL, 22, 'hero_detail'), (FINAL, 24, 'lobby'),
    (FINAL, 28, 'lobby'), (FINAL, 34, 'received_reward'),
    ('20261027T034529Z_6b3c4cd0', 62, 'prequel_preparation'),
    ('20261027T081838Z_d968bc8e', 7, 'system_unlock_notice'),
    ('20261027T081838Z_d968bc8e', 69, 'connection_unlock_notice'),
    ('20261027T081838Z_d968bc8e', 102, 'summon_page'),
    ('20261027T084618Z_f4017642', 3, 'recruit_hub'),
    ('20261027T084618Z_f4017642', 30, 'connections'),
    ('20261027T065733Z_52d8869f', 12, 'inventory'),
    ('20261027T065733Z_52d8869f', 15, 'inventory_item'),
    ('20261027T065733Z_52d8869f', 21, 'mailbox'),
    ('20261027T065733Z_52d8869f', 24, 'mail_receive_confirmation'),
    ('20261027T065733Z_52d8869f', 27, 'received_reward'),
    ('20261027T065733Z_52d8869f', 37, 'mail_detail'),
    ('20261027T065733Z_52d8869f', 54, 'mail_detail'),
    ('20261027T065733Z_52d8869f', 57, 'equipment_receipt'),
    ('20261027T065733Z_52d8869f', 75, 'equip_all_preview'),
    ('20261027T065733Z_52d8869f', 90, 'hero_level_up'),
    ('20261027T065733Z_52d8869f', 93, 'hero_level_result'),
    ('20261027T024311Z_f1c0e142', 66, 'checkin_notice'),
    ('20261027T080001Z_4bad03e5', 27, 'formation_auto_assign'),
    ('20261027T080001Z_4bad03e5', 30, 'prequel_preparation'),
])
def test_saved_compositions_use_the_canonical_tree_without_mutating_evidence(run, number, expected):
    data = saved(run, number)
    original = deepcopy(data)
    tree = build_tree(data)
    validate_tree(tree)
    current = operation_view({'ui_tree': tree})
    assert current['view'] == expected
    assert data == original
    for control in current['controls']:
        assert control['enabled'] is None
        assert control['box_role'] in ('text_anchor','template_extent')
        queried = query_operation_control(tree, expected, control['semantic_id'])
        assert queried['read_only'] and queried['requires_current_action_guards']
    for item in tree['nodes'].values():
        for field in item['fields'].values():
            if field['value'] is not None:
                assert field['sources']


@pytest.mark.fixtures
def test_awakening_proposal_result_and_current_hero_are_separate_facts():
    proposal = view(saved(FINAL, 9))
    assert proposal['mode'] == 'preview'
    context = proposal['items'][0]
    assert context['hero_name'] == 'Free Spirit Tieria'
    assert context['material_ratio'] == {'available': 10, 'cost': 8}
    assert context['material_id'] is None and context['application_completed'] is None
    assert next(c for c in proposal['controls'] if c['semantic_id'] == 'awaken')['consuming'] is True
    result = view(saved(FINAL, 13))
    assert result['items'][0]['result_announced'] is True
    assert result['items'][0]['hero_name'] is None  # No carried hero identity.
    stats = {s['semantic_id']: s for s in result['items'][1:]}
    assert stats['stat:attack']['before'] == '76' and stats['stat:attack']['after'] == '96'
    assert stats['stat:health']['before'] == '262' and stats['stat:health']['after'] == '322'
    assert stats['stat:effectiveness']['change_text'] is None  # OCR below .90.
    overview = view(saved(FINAL, 16))
    assert overview['mode'] == 'overview'
    assert overview['items'][0]['material_ratio'] is None
    assert overview['items'][0]['current_awakened_stars'] is None
    assert next(c for c in overview['controls'] if c['semantic_id'] == 'awaken')['consuming'] is False


@pytest.mark.fixtures
def test_orbis_uses_existing_group_mission_ancestry_and_never_guesses_missing_counters():
    before = saved(FINAL, 31)
    tree = build_tree(before)
    q = quest_view({'ui_tree': tree})
    assert q['group_id'] == 'group_guide_01'
    assert q['group_counter'] == {'current': 1, 'total': 6}
    awakening = next(t for t in q['visible_tasks'] if t['task_id'] == 'guide_01_005_001')
    assert awakening['control'] == 'receive' and awakening['counter'] is None
    assert awakening['condition_satisfied'] is None and awakening['status'] == 'unknown'
    assert query_control(tree, 'group_guide_01', 'guide_01_005_001', 'claim')['read_only']
    after = quest_view({'ui_tree': build_tree(saved(FINAL, 36))})
    assert after['group_counter'] == {'current': 3, 'total': 6}
    covenant = next(t for t in after['visible_tasks'] if t['family'] == 'summoning')
    assert covenant['counter'] == {'current': 0, 'total': 1}
    assert covenant['condition_satisfied'] is False
    altar = next(t for t in after['visible_tasks'] if t['family'] == 'combat_modes')
    assert altar['counter'] is None and altar['row_fully_visible'] is False
    assert after['complete_group_inventory'] is None
    receipt = view(saved(FINAL, 34))['items'][0]
    assert receipt['receipt_announced'] is True
    assert receipt['mission_ids'] is None and receipt['quantities'] is None
    diary = saved('20261027T084618Z_f4017642', 21)
    diary_tree = build_tree(diary)
    diary_view = quest_view({'ui_tree': diary_tree})
    assert diary_view['group_id'] == 'observed_diary'
    assert diary_view['group_counter'] is None  # Header number is not a mission ratio.
    assert diary_tree['nodes']['panel:orbis/observed_diary']['fields']['header_number']['value'] == 60


@pytest.mark.fixtures
def test_current_overlay_hides_underlying_actions_and_incomplete_result_does_not_fall_through():
    hero = saved(FINAL, 22)
    reward = saved(FINAL, 13)
    composite = deepcopy(hero)
    composite['state'] = 'unknown'
    composite['text'] += deepcopy(reward['text'])
    assert view(composite)['view'] == 'hero_awakening_result'
    composite['text'] = [r for r in composite['text'] if not r['text'].startswith('Hero Stat')]
    assert view(composite) == {}
    unlock = view(saved('20261027T081838Z_d968bc8e', 69))
    assert unlock['items'][0]['unlock_announced'] is True
    assert unlock['items'][0]['acquired'] is None
    # A receipt whose heading failed OCR must not expose missions behind it.
    missions = saved(FINAL, 31)
    receipt = saved(FINAL, 34)
    foreground = [r for r in receipt['text'] if 330 <= r['box'][0] < 900 and 120 <= r['box'][1] < 560]
    foreground = [r for r in foreground if r['text'] != 'Received Reward']
    missions['text'] += foreground
    assert quest_view({'ui_tree': build_tree(missions)}).get('group_id') is None


@pytest.mark.fixtures
def test_profile_ambiguity_and_low_confidence_reject_growth_identity_and_cost():
    source = saved(FINAL, 9)
    for mutation in ('process', 'size', 'dimmed', 'combat'):
        data = deepcopy(source)
        if mutation == 'process': data['window']['process_name'] = 'Other.exe'
        elif mutation == 'size': data['window']['client_size'] = [1280, 720]
        elif mutation == 'dimmed':
            for row in data['text']: row['score'] = .89
        else: data['state'] = 'battle_running'
        assert view(data).get('view') != 'hero_awakening'
    for mutation in ('missing_name', 'duplicate_body_name'):
        data = deepcopy(source)
        if mutation == 'missing_name':
            data['text'] = [r for r in data['text'] if r['text'] != 'Free Spirit Tieria']
        else:
            data['text'].append(deepcopy(next(r for r in data['text'] if r['text'] == 'Free Spirit Tieria' and r['box'][1]>100)))
        assert view(data)['view'] == 'hero_awakening'
        assert view(data)['items'][0]['hero_name'] is None
    data = deepcopy(source)
    data['text'].append(deepcopy(next(r for r in data['text'] if r['text'] == '10/8')))
    assert view(data)['items'][0]['material_ratio'] is None


@pytest.mark.fixtures
def test_agent_projects_current_quest_tree_and_change_events_without_capturing(tmp_path):
    from driver_epic_seven.agent_session import agent_view
    from driver_epic_seven.observer import SharedObserver
    observer = SharedObserver()
    for number, expected in ((31, 1), (36, 3)):
        data = saved(FINAL, number)
        data['ui_tree'] = build_tree(data)
        observer.publish(data, 'saved_fixture')
        snapshot = observer.snapshot(now=data['captured_at_epoch_seconds'])
        response = agent_view(snapshot, artifact=tmp_path/'reply.json', observer_file=tmp_path/'observer.json')
        assert response['state'] == 'unknown'
        assert response['ui']['quest_view']['group_counter'] == {'current': expected, 'total': 6}
        assert not response['image']['required']
        assert response['requires_current_action_guards']
    changes = [e for e in response['events'] if e['kind'] == 'tree_changed']
    assert 'group:group_guide_01' in changes[-1]['changed_nodes']
    assert response['metrics']['driver_captures'] == 0 and response['metrics']['recognitions'] == 0
    observer.invalidate('disconnected')
    response = agent_view(observer.snapshot(), artifact=tmp_path/'reply.json', observer_file=tmp_path/'observer.json')
    assert not response['validity']['valid']
    assert 'disconnected' in response['validity']['reasons']
    assert response['ui']['quest_view']['group_counter'] == {'current': 3, 'total': 6}


def test_stove_read_context_rejects_invalid_boxes_and_ambiguous_labels():
    from driver_epic_seven.operational_stove import ReadContext
    rows = [{'text': 'Confirm', 'box': [600, 450, 90, 25], 'score': .99},
            {'text': 'Confirm', 'box': [700, 450, 90, 25], 'score': .99},
            {'text': 'Ghost', 'box': [1200, 450, 90, 25], 'score': .99},
            {'text': 'Ghost', 'box': [float('nan'), 450, 90, 25], 'score': .99},
            {'text': 'Ghost', 'box': [600, 450, 90, 25], 'score': .89}]
    context = ReadContext({'text': rows}, 'screen', lambda _: None)
    assert context.one('Confirm') is None
    assert len(context.find('Confirm')) == 2
    assert context.one('Ghost') is None


@pytest.mark.fixtures
def test_native_chest_markers_require_current_prompt_and_reject_other_reward_screens(tmp_path):
    import numpy as np
    from PIL import Image
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    from driver_epic_seven.vision import Vision, validated_template_match
    from driver_epic_seven.observed_ui import target_box

    run = '20261027T060242Z_390d2724'
    cases = [(run, n, True) for n in (16, 19, 22)]
    cases += [(run, n, False) for n in (6, 10, 26, 49, 55, 62, 71)]
    cases += [(FINAL, n, False) for n in (9, 13, 22, 24, 31, 34)]
    paths = [(ROOT/'var/runs'/r/f'agent_{n:06}.png', r, n, expected) for r,n,expected in cases]
    if not all(p.exists() for p,*_ in paths):
        pytest.skip('Private chest and negative fixtures unavailable.')
    bundle = ROOT/'resources/epic-seven'
    vision = Vision(bundle/'vision.json', bundle)
    key = 'stove_coreloop_chest_presentation'
    spec = vision.spec['templates'][key]
    assert key not in vision.spec['target_states']
    found = []

    class Offline(CustomRecognition):
        def analyze(self, ctx, args):
            raw = ctx.run_recognition(spec['node'], args.image)
            found.append(validated_template_match(args.image, vision.templates[key], raw, spec['max_pixel_mae']))
            return self.AnalyzeResult(box=[0,0,1,1], detail=found[-1])

    Tasker.set_stdout_level(LoggingLevelEnum.Off)
    Tasker.set_log_dir(tmp_path/'maa')
    resource = Resource()
    resource.set_cpu()
    resource.register_custom_recognition('ReadOnlyChestFixture', Offline())
    assert resource.post_bundle(bundle).wait().succeeded
    tasker = Tasker()
    assert Library.framework().MaaTaskerBindResource(tasker._handle, resource._handle)
    report = []
    for path, run_id, number, expected in paths:
        pixels = np.asarray(Image.open(path).convert('RGB'))[:,:,::-1].copy()
        variants = [('original', pixels, expected)]
        if expected:
            variants += [('dimmed', (pixels*.45).astype(np.uint8), False)]
        for label, frame, want in variants:
            assert tasker.post_recognition('Custom', JCustomRecognition(custom_recognition='ReadOnlyChestFixture'), frame).wait().succeeded
            match = found[-1]
            assert match['hit'] is want, (str(path), label, match)
            report.append({'file': str(path), 'variant': label, 'expected': want, 'match': match})
            if label == 'original' and want:
                data = saved(run_id, number)
                data.update(state='unknown', matches={key: match})
                tree = build_tree(data, vision.spec)
                current = operation_view({'ui_tree': tree})
                assert current['view'] == 'milestone_chest_presentation'
                assert current['items'][0]['reward_obtained'] is None
                assert current['items'][0]['rarity'] is None
                assert target_box(tree, key) is None
                data['text'] = []
                assert view(data) == {}
    (tmp_path/'chest-native-replay.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
