"""Replay a specific STOVE lobby tutorial; other lobby screens stay unknown."""
import json

import numpy as np
from PIL import Image
import pytest

from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree, target_box, fact
from driver_epic_seven.vision import Vision


@pytest.mark.fixtures
def test_skip_tutorial_requires_current_episode_instruction_and_episode_anchor(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum

    run = ROOT/'var/runs/20261027T003836Z_6bfd84bc'
    positive_numbers = (25,27)
    negative_numbers = (3,7,13,17,20,22,24)
    paths = [run/f'agent_{n:06}.png' for n in positive_numbers+negative_numbers]
    if not all(p.exists() for p in paths):
        pytest.skip('Private STOVE lobby/tutorial frames are not installed.')
    bundle = ROOT/'resources/epic-seven'
    vision = Vision(bundle/'vision.json',bundle)
    names = {'tutorial_skip','tutorial_episode_instruction','episode_button'}
    vision.spec['templates'] = {k:v for k,v in vision.spec['templates'].items() if k in names}
    vision.spec['states'] = {'tutorial_episode_prompt':vision.spec['states']['tutorial_episode_prompt']}
    vision.spec['ocr'] = {}
    results = []

    class Offline(CustomRecognition):
        def analyze(self,context,argv):
            results.append(vision.inspect(argv.image,lambda n:context.run_recognition(n,argv.image)))
            return self.AnalyzeResult(box=[0,0,1,1],detail=results[-1])

    Tasker.set_stdout_level(LoggingLevelEnum.Off)
    Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu()
    resource.register_custom_recognition('StoveTutorialFixture',Offline())
    assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker()
    assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    cases=[]
    for number in positive_numbers+negative_numbers:
        path=run/f'agent_{number:06}.png'
        frame=np.asarray(Image.open(path).convert('RGB'))[:,:,::-1].copy()
        expected='tutorial_episode_prompt' if number in positive_numbers else 'unknown'
        cases.append((path.name,frame,expected))
        if number in positive_numbers:
            cases.append((path.name+'/dimmed',(frame*.55).astype(np.uint8),'unknown'))
            for x1,y1,x2,y2 in ((1020,8,1185,63),(665,140,1005,235),(1040,140,1205,215)):
                covered=frame.copy();covered[y1:y2,x1:x2]=0
                cases.append((path.name+f'/covered-{x1}-{y1}',covered,'unknown'))
    for name,frame,expected in cases:
        assert tasker.post_recognition('Custom',JCustomRecognition(
            custom_recognition='StoveTutorialFixture'),frame).wait().succeeded
        result=results[-1]
        assert result['state']==expected,(name,result)
        tree=build_tree({**result,'window':{'client_size':[1212,682]}},vision.spec)
        if expected=='tutorial_episode_prompt':
            assert target_box(tree,'tutorial_skip')==[1040,19,125,28]
            assert target_box(tree,'episode_button')==[1066,158,108,36]
            assert tree['nodes']['visual:tutorial_skip']['fields']['enabled']==fact()
        else:
            assert target_box(tree,'tutorial_skip') is None
            assert target_box(tree,'episode_button') is None
    (tmp_path/'stove-tutorial-replay.json').write_text(json.dumps([
        {'case':c[0],'expected':c[2],'observed':r} for c,r in zip(cases,results)],indent=2),encoding='utf-8')
