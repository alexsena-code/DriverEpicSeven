"""Reuse proven native combat anchors without inventing STOVE Auto state."""
import json

import numpy as np
from PIL import Image
import pytest

from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree, auto_state, fact
from driver_epic_seven.vision import Vision


@pytest.mark.fixtures
def test_stove_combat_reuses_markers_and_keeps_auto_unknown(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    run=ROOT/'var/runs/20261027T005115Z_8d1b189a'
    numbers=(33,39,42,43,45)
    if not all((run/f'agent_{n:06}.png').exists() for n in numbers):
        pytest.skip('Private STOVE combat frames are not installed.')
    bundle=ROOT/'resources/epic-seven';v=Vision(bundle/'vision.json',bundle)
    names={n for s in v.spec['states']['battle_running'].get('variants',[v.spec['states']['battle_running']])
           for clause in ('all','any','none') for n in s.get(clause,[])}
    v.spec['templates']={k:s for k,s in v.spec['templates'].items() if k in names}
    v.spec['states']={'battle_running':v.spec['states']['battle_running']};v.spec['ocr']={}
    results=[]
    class Offline(CustomRecognition):
        def analyze(self,context,argv):
            results.append(v.inspect(argv.image,lambda n:context.run_recognition(n,argv.image)))
            return self.AnalyzeResult(box=[0,0,1,1],detail=results[-1])
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('StoveBattleFixture',Offline())
    assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    cases=[]
    for n in numbers:
        frame=np.asarray(Image.open(run/f'agent_{n:06}.png').convert('RGB'))[:,:,::-1].copy()
        state='battle_running' if n in (42,43,45) else 'unknown'
        cases.append((str(n),frame,state))
        if state=='battle_running':
            cases.append((f'{n}/dimmed',(frame*.55).astype(np.uint8),'unknown'))
            covered=frame.copy();covered[8:55,1150:1200]=0
            cases.append((f'{n}/pause-covered',covered,'unknown'))
    for name,frame,expected in cases:
        assert tasker.post_recognition('Custom',JCustomRecognition(
            custom_recognition='StoveBattleFixture'),frame).wait().succeeded
        result=results[-1]
        assert result['state']==expected,(name,result)
        observation={**result,'window':{'client_size':[1212,682]}}
        tree=build_tree(observation,v.spec)
        assert auto_state({'ui_tree':tree}) is None
        if expected=='battle_running':
            assert tree['nodes']['battle:auto']['fields']['value']==fact()
    (tmp_path/'stove-battle-replay.json').write_text(json.dumps([
        {'case':c[0],'expected':c[2],'observed':r} for c,r in zip(cases,results)],indent=2),encoding='utf-8')
