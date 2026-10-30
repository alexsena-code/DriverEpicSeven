from copy import deepcopy
import json

import pytest

from driver_epic_seven.story_performance import needs_story_text


def test_candidate_filter_respects_variants_sources_and_never_promotes_an_observation():
    from types import SimpleNamespace
    from driver_epic_seven.story_performance import candidate_matcher
    spec = {'templates': {'skip': {}, 'history': {}}, 'ocr': {}, 'states': {'story': {'variants': [
        {'all': ['skip','history'], 'source_nodes': {'skip':'Current'}},
        {'all': ['unknown_anchor']} ]}}}
    calls = []
    matches = {'skip': {'hit':True,'source_node':'Other'}, 'history': {'hit':True}}
    def match(name,frame,matcher):
        calls.append(name); matcher(name)
        return matches[name]
    vision = SimpleNamespace(spec=spec,match_template=match)
    native = []
    def recognize(name):native.append(name);return object()
    # The uninterpreted variant cannot prove a negative.
    reader = candidate_matcher(vision, None, recognize, {'path':{'kind':'story_skip'}})
    assert callable(reader)
    reader('skip');reader('skip')
    assert native.count('skip')==1
    spec['states']['story']['variants'].pop()
    assert candidate_matcher(vision,None,recognize,{'path':{'kind':'story_skip'}}) is None
    matches['skip']['source_matches']={'Current':{'hit':True}}
    assert callable(candidate_matcher(vision,None,recognize,{'path':{'kind':'story_skip'}}))
    # Native results never survive another invocation, even with equal pixels.
    assert native.count('skip')==3
    for params in ({'observe':True,'state':'story'}, {'session':True}, {'quest':True},
                   {'path':{'kind':'prequel_start'}}, {'path':{'kind':'informational_ack'}}):
        calls.clear()
        assert callable(candidate_matcher(vision,None,recognize,params)) and calls==[]


@pytest.mark.parametrize('legacy,manual,unlocked,possible',[
    (True,False,False,True),(False,True,True,True),(False,True,False,False),
    (False,False,True,False),(False,False,False,False)])
def test_auto_candidate_full_read_requires_a_possible_positive_off_proof(legacy,manual,unlocked,possible):
    from types import SimpleNamespace
    from driver_epic_seven.story_performance import candidate_matcher
    hits=dict(zip(('auto_hud_off','auto_manual_skills','auto_unlocked_off'),(legacy,manual,unlocked)))
    vision=SimpleNamespace(spec={'states':{'battle_running':{'all':[]}},'templates':{k:{} for k in hits},'ocr':{}},
        match_template=lambda name,frame,matcher:{'hit':hits[name]})
    params={'state':'battle_running','auto_state':False,'target':'battle_auto'}
    assert callable(candidate_matcher(vision,None,lambda name:None,params)) is possible


@pytest.mark.fixtures
def test_runtime_candidate_gate_keeps_native_targets_and_full_positive_reading(tmp_path, monkeypatch):
    """Exercise the production callback against saved pixels; no Windows controller."""
    import numpy as np
    from PIL import Image
    from maa.controller import CustomController
    from maa.pipeline import JCustomRecognition
    from driver_epic_seven.config import ROOT
    from driver_epic_seven.vision import Vision
    from driver_epic_seven.stages import StageInspector
    from driver_epic_seven.path_execution import path_target
    from test_wave3_runtime import offline_runtime
    run = ROOT/'var/runs/20261029T134159Z_64ab46d1'
    paths = [run/name for name in ('057_Path.Campaign.tae004.Before.Skip.png',
        '058_Path.Campaign.tae004.Before.Confirm.png','015_Path.Campaign.taw005.Clear.png')]
    paths += [ROOT/'var/runs/20261027T233054Z_89604c75/agent_000001.png',
              ROOT/'var/runs/20261029T131551Z_3e5e4fe8/observation.png']
    paths += [ROOT/'tests/fixtures/local'/name for name in
              ('23_story.png','24_story_confirmation.png','25_battle_running.png','53_battle_failed.png')]
    paths += [ROOT/f'var/runs/20261027T060242Z_390d2724/agent_{n:06}.png' for n in (136,139,143)]
    paths += [ROOT/'var/runs/20261029T163233Z_68ef9287/agent_000001.png']
    if not all(p.exists() for p in paths):pytest.skip('Private story/result/supporter frames unavailable.')
    class MemoryController(CustomController):
        def connect(self):return True
        def request_uuid(self):return 'offline-story-performance'
        def screencap(self):raise AssertionError('Recognition must use the supplied saved image.')
        def click(self,*args):raise AssertionError('Read-only replay cannot send input.')
        def touch_down(self,*args):raise AssertionError('Read-only replay cannot send input.')
    monkeypatch.setattr('maa.controller.Win32Controller',lambda *args:MemoryController())
    runtime = offline_runtime(tmp_path)
    runtime.vision = Vision(runtime.config['vision_file'],runtime.config['resource_dir'])
    runtime.stage_inspector = StageInspector(runtime.config['stage_file'])
    runtime.path_prepared = {'prequel_victory:tae004':{'window':deepcopy(runtime.original)}}
    runtime._initialize_maa()
    candidates = [{'read_text':True,'path':{'kind':kind,'stage_id':'taw002' if kind=='prequel_supporter' else 'tae004'}} for kind in
                  ('story_skip','story_hold','prequel_defeat','prequel_clear','prequel_supporter','prequel_map_return')]
    candidates += [{'read_text':True,'state':'story_confirmation','target':'story_confirm_button'},
                   {'read_text':True,'state':'battle_running','auto_state':False,'target':'battle_auto'}]
    report = []
    for path in paths:
        frame = np.asarray(Image.open(path).convert('RGB'))[:,:,::-1].copy()
        for dimmed in (False,True):
            image = (frame*.55).astype(np.uint8) if dimmed else frame
            def read(params):
                job = runtime.tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='ScreenTarget',
                    custom_recognition_param=params),image).wait()
                assert job.succeeded and runtime.fatal is None, runtime.fatal
                nodes = job.get().nodes
                return bool(nodes and nodes[-1].recognition and nodes[-1].recognition.hit)
            assert read({'observe':True,'read_text':True})
            baseline = deepcopy(runtime.bridge.latest)
            for params in candidates:
                expected = (path_target(baseline,params['path'],image,runtime.path_prepared) if 'path' in params
                            else runtime.vision.target(baseline,params))
                hit = read(params)
                assert hit is (expected is not None), (path.name,dimmed,params,expected,runtime.fatal)
                if hit:
                    positive = runtime.bridge.latest
                    assert positive['matches']==baseline['matches']
                    assert positive['text']==baseline['text']
                    assert positive['state']==baseline['state']
                    assert 'text_scope' not in positive
                report.append({'case':str(path),'dimmed':dimmed,'candidate':params,'target':expected,'hit':hit})
    assert runtime.fatal is None
    assert runtime.observer.metrics['candidate_rejections']>0
    (tmp_path/'candidate-replay.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


@pytest.mark.parametrize('kind', ['story_skip', 'story_hold', 'prequel_story_skip', 'prequel_story_hold'])
def test_story_candidate_only_omits_text_after_its_state_guard_fails(kind):
    params = {'path': {'kind': kind, 'stage_id': 'taw002'}}
    assert needs_story_text(params, 'story') is True
    for state in ('unknown', 'story_confirmation', 'battle_running', 'stage_clear', 'supporter_selection'):
        assert needs_story_text(params, state) is False


def test_confirm_and_unrelated_operations_keep_positive_and_full_reading():
    confirm = {'state': 'story_confirmation', 'target': 'story_confirm_button'}
    assert needs_story_text(confirm, 'story_confirmation') is True
    assert needs_story_text(confirm, 'story') is False
    assert needs_story_text(confirm, 'unknown') is False
    for params in ({}, {'observe': True}, {'session': True}, {'path': {'kind': 'prequel_start'}},
                   {'state': 'story_confirmation', 'target': 'other'}):
        assert needs_story_text(params, 'unknown') is True


@pytest.mark.fixtures
def test_rejected_story_candidates_keep_same_target_on_saved_observations():
    from driver_epic_seven.config import ROOT
    from driver_epic_seven.observed_ui import build_tree
    from driver_epic_seven.path_execution import path_target
    from driver_epic_seven.vision import Vision

    folder = ROOT / 'var/runs/20261029T134159Z_64ab46d1'
    paths = [folder / name for name in ('057_Path.Campaign.tae004.Before.Skip.json',
             '058_Path.Campaign.tae004.Before.Confirm.json', '015_Path.Campaign.taw005.Clear.json')]
    if not all(path.exists() for path in paths):
        pytest.skip('Private story and result observations are unavailable.')
    vision = Vision(ROOT / 'resources/epic-seven/vision.json', ROOT / 'resources/epic-seven')
    candidates = [{'path': {'kind': 'story_skip', 'stage_id': 'tae004'}},
                  {'state': 'story_confirmation', 'target': 'story_confirm_button'}]
    for path in paths:
        original = json.loads(path.read_text(encoding='utf-8'))
        for params in candidates:
            if needs_story_text(params, original['state']):
                continue
            baseline = deepcopy(original)
            fast = deepcopy(original)
            fast['text'] = []
            baseline['ui_tree'] = build_tree(baseline, vision.spec)
            fast['ui_tree'] = build_tree(fast, vision.spec)
            if 'path' in params:
                old = path_target(baseline, params['path'], None)
                new = path_target(fast, params['path'], None)
            else:
                old = vision.target(baseline, params)
                new = vision.target(fast, params)
            assert old is None and new is None
