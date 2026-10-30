"""STOVE story control replay; never creates a controller or captures the game."""
import json

import numpy as np
from PIL import Image
import pytest

from driver_epic_seven.config import ROOT
from driver_epic_seven.vision import Vision


@pytest.mark.fixtures
def test_saved_stove_skip_and_history_require_both_positive_controls(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum

    run = ROOT / 'var/runs/20261027T003313Z_8040ba21'
    positives = [run / f'agent_{number:06}.png' for number in (1, 2, 3, 5)]
    light_run = ROOT / 'var/runs/20261027T005115Z_8d1b189a'
    positives += [light_run / f'agent_{number:06}.png' for number in (19,20)
                  if (light_run / f'agent_{number:06}.png').exists()]
    gray_run = ROOT / 'var/runs/20261027T233054Z_89604c75'
    positives += [gray_run / f'agent_{number:06}.png' for number in (1,2)
                  if (gray_run / f'agent_{number:06}.png').exists()]
    town=ROOT/'var/runs/20261030T044651Z_4975d8f8/observation.png'
    if town.exists():positives.append(town)
    snow=ROOT/'var/admin-campaign-20261030q/wis001-story-live.png'
    if snow.exists():positives.append(snow)
    roof_run=ROOT/'var/runs/20261030T193537Z_99cd4ea6'
    roofs=[roof_run/f'agent_{number:06}.png' for number in (47,54)]
    positives += [path for path in roofs if path.exists()]
    markets=[ROOT/'var/runs/20261030T214551Z_b837e52d/agent_000010.png',
             ROOT/'var/runs/20261030T215208Z_c13d8ed7/agent_000001.png',
             ROOT/'var/runs/20261030T215208Z_c13d8ed7/agent_000004.png']
    positives += [path for path in markets if path.exists()]
    if not all(path.exists() for path in positives):
        pytest.skip('Private STOVE calibration frames are not installed.')
    bundle = ROOT / 'resources/epic-seven'
    vision = Vision(bundle / 'vision.json', bundle)
    production_story=vision.spec['states']['story']
    # This fixture deliberately tests the story subset if the profile grows.
    names = {'story_skip', 'story_history', 'path_story_skip_gray', 'path_story_history_gray'}
    vision.spec['templates'] = {k:v for k,v in vision.spec['templates'].items() if k in names}
    vision.spec['states'] = {'story': {'all':['story_skip','story_history']}}
    vision.spec['ocr'] = {}
    found = []

    class Offline(CustomRecognition):
        def analyze(self, context, argv):
            found.append(vision.inspect(argv.image, lambda n: context.run_recognition(n, argv.image)))
            return self.AnalyzeResult(box=[0,0,1,1], detail=found[-1])

    Tasker.set_stdout_level(LoggingLevelEnum.Off)
    Tasker.set_log_dir(tmp_path / 'maa')
    resource = Resource()
    resource.set_cpu()
    resource.register_custom_recognition('StoveStoryFixture', Offline())
    assert resource.post_bundle(bundle).wait().succeeded
    tasker = Tasker()
    assert Library.framework().MaaTaskerBindResource(tasker._handle, resource._handle)
    cases = []
    for path in positives:
        frame = np.asarray(Image.open(path).convert('RGB'))[:,:,::-1].copy()
        cases.append((str(path), frame, 'story'))
        for factor in (.70, .45):
            cases.append((path.name+f'/dimmed-{factor}', (frame*factor).astype(np.uint8), 'unknown'))
        for box in ((1100,8,1208,73),(1010,8,1080,73)):
            covered = frame.copy()
            x1,y1,x2,y2 = box
            covered[y1:y2,x1:x2] = 0
            cases.append((path.name+f'/covered-{x1}', covered, 'unknown'))
    # These are compatibility negatives, not STOVE modal validation.
    local = ROOT / 'tests/fixtures/local'
    for name in ('00_lobby.png','24_story_confirmation.png','34_story_dimmed.png','45_story_intro.png'):
        path = local / name
        if path.exists():
            cases.append(('steam-negative/'+name,
                          np.asarray(Image.open(path).convert('RGB'))[:,:,::-1].copy(), 'unknown'))
    modal = light_run / 'agent_000022.png'
    if modal.exists():
        cases.append(('stove-light-room-modal',
                      np.asarray(Image.open(modal).convert('RGB'))[:,:,::-1].copy(), 'unknown'))
    roof_modal=roof_run/'agent_000049.png'
    if roof_modal.exists():
        cases.append(('roof-story-confirmation-modal',
                      np.asarray(Image.open(roof_modal).convert('RGB'))[:,:,::-1].copy(), 'unknown'))
    for name, frame, expected in cases:
        assert tasker.post_recognition('Custom', JCustomRecognition(
            custom_recognition='StoveStoryFixture'), frame).wait().succeeded
        assert found[-1]['state'] == expected, (name, {
            key:{k:v for k,v in value.items() if k in ('hit','score','pixel_mae')}
            for key,value in found[-1]['matches'].items()})
        if name in (str(town),str(snow)):
            from driver_epic_seven.vision import classify
            assert classify(found[-1]['matches'],{'story':production_story})=='story'
        if expected == 'story' and (str(gray_run) in name or name in map(str,roofs+markets)):
            assert found[-1]['matches']['path_story_skip_gray']['hit']
            assert found[-1]['matches']['path_story_history_gray']['hit']
    report = [{'case':case[0], 'expected':case[2], 'observed':result}
              for case,result in zip(cases,found)]
    (tmp_path/'stove-story-replay.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


@pytest.mark.fixtures
def test_current_story_can_combine_verified_control_variants():
    from copy import deepcopy
    from driver_epic_seven.vision import classify
    from driver_epic_seven.observed_ui import build_tree, operation_view
    from driver_epic_seven.interruptions import story_target
    path=ROOT/'var/runs/20261030T035220Z_b37e5050/live.json'
    if not path.exists():pytest.skip('Private mixed-control story unavailable.')
    data=json.loads(path.read_text(encoding='utf-8'))['analysis']
    vision=Vision(ROOT/'resources/epic-seven/vision.json',ROOT/'resources/epic-seven')
    spec={'story':vision.spec['states']['story']}
    matches=data['matches']
    assert matches['story_skip']['source_node']=='Stove.Template.StorySkip'
    assert matches['story_history']['source_node']=='Template.StoryHistory'
    data['state']=classify(matches,spec)
    assert data['state']=='story'
    data['ui_tree']=build_tree(data,vision.spec)
    assert operation_view(data)['view']=='story_dialogue'
    assert story_target(data,{'kind':'story_skip'})
    for missing in ('story_skip','story_history'):
        wrong=deepcopy(matches);wrong[missing]={'hit':False}
        assert classify(wrong,spec)=='unknown'
    wrong=deepcopy(matches);wrong['story_confirm_question']={'hit':True}
    assert classify(wrong,spec)=='unknown'


@pytest.mark.fixtures
def test_stove_skip_confirmation_requires_exact_question_and_button(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    from driver_epic_seven.observed_ui import build_tree, target_box, fact

    run = ROOT / 'var/runs/20261027T003836Z_6bfd84bc'
    paths = [(run / f'agent_{n:06}.png', state) for n,state in
             [(1,'story'),(3,'story_confirmation'),(5,'story_confirmation'),(7,'unknown')]]
    if not all(p.exists() for p,_ in paths):
        pytest.skip('Private STOVE confirmation/cutscene frames are not installed.')
    bundle = ROOT/'resources/epic-seven'
    vision = Vision(bundle/'vision.json', bundle)
    names = {'story_skip','story_history','story_confirm_question','story_confirm_button','tieria_dialogue_line'}
    vision.spec['templates'] = {k:v for k,v in vision.spec['templates'].items() if k in names}
    vision.spec['states'] = {k:v for k,v in vision.spec['states'].items()
                             if k in ('story','story_confirmation')}
    vision.spec['ocr'] = {}
    results = []

    class Offline(CustomRecognition):
        def analyze(self, context, argv):
            results.append(vision.inspect(argv.image, lambda n: context.run_recognition(n,argv.image)))
            return self.AnalyzeResult(box=[0,0,1,1], detail=results[-1])

    Tasker.set_stdout_level(LoggingLevelEnum.Off)
    Tasker.set_log_dir(tmp_path/'maa')
    resource = Resource(); resource.set_cpu()
    resource.register_custom_recognition('StoveConfirmFixture',Offline())
    assert resource.post_bundle(bundle).wait().succeeded
    tasker = Tasker()
    assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    cases = []
    for path,state in paths:
        frame = np.asarray(Image.open(path).convert('RGB'))[:,:,::-1].copy()
        cases.append((path.name,frame,state))
        if state == 'story_confirmation':
            cases.append((path.name+'/dimmed',(frame*.55).astype(np.uint8),'unknown'))
            for x1,y1,x2,y2 in ((410,275,805,340),(650,405,770,470)):
                partial = frame.copy(); partial[y1:y2,x1:x2] = 0
                cases.append((path.name+f'/missing-{x1}',partial,'unknown'))
    for name,frame,expected in cases:
        assert tasker.post_recognition('Custom',JCustomRecognition(
            custom_recognition='StoveConfirmFixture'),frame).wait().succeeded
        result = results[-1]
        assert result['state'] == expected, (name,result)
        tree = build_tree({**result,'window':{'client_size':[1212,682]}},vision.spec)
        if expected == 'story_confirmation':
            assert target_box(tree,'story_confirm_button') == [671,422,76,28]
            assert target_box(tree,'story_skip') is None
            assert tree['nodes']['visual:story_confirm_button']['fields']['enabled'] == fact()
        elif expected == 'unknown':
            assert target_box(tree,'story_confirm_button') is None
    (tmp_path/'stove-confirm-replay.json').write_text(json.dumps([
        {'case':c[0],'expected':c[2],'observed':r} for c,r in zip(cases,results)],indent=2),encoding='utf-8')
