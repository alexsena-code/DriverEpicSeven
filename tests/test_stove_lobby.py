"""The anniversary STOVE lobby is a scoped visual variant, not any missing HUD."""
import json

import numpy as np
from PIL import Image
import pytest

from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree, target_box, fact
from driver_epic_seven.vision import Vision


@pytest.mark.fixtures
def test_lobby_and_idle_require_positive_theme_anchors_and_reject_overlays(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum

    run=ROOT/'var/runs/20261027T004547Z_58a7ec10'
    other=ROOT/'var/runs/20261027T003836Z_6bfd84bc'
    paths=[(run/f'agent_{n:06}.png','lobby' if n==3 else 'lobby_idle')
           for n in (3,6,7,8,9,10,11,12)]
    paths += [(other/f'agent_{n:06}.png','unknown') for n in (3,7,13,17,20,22,24,25,27)]
    day=ROOT/'var/runs/20261029T092057Z_aa9a2d96'
    paths += [(day/f'agent_{n:06}.png','lobby' if n==162 else 'lobby_idle')
              for n in (162,163,164,165,166,167,168,169,170,171)]
    paths += [(day/f'agent_{n:06}.png','unknown') for n in (153,155,157,159,160)]
    if not all(p.exists() for p,_ in paths):
        pytest.skip('Private STOVE lobby calibration frames are not installed.')
    bundle=ROOT/'resources/epic-seven'
    vision=Vision(bundle/'vision.json',bundle)
    states={k:v for k,v in vision.spec['states'].items() if k in ('lobby','lobby_idle')}
    names={n for state in states.values() for s in state.get('variants',[state]) for clause in ('all','any','none') for n in s.get(clause,[])}
    vision.spec['templates']={k:v for k,v in vision.spec['templates'].items() if k in names}
    vision.spec['states']=states;vision.spec['ocr']={}
    results=[]

    class Offline(CustomRecognition):
        def analyze(self,context,argv):
            results.append(vision.inspect(argv.image,lambda n:context.run_recognition(n,argv.image)))
            return self.AnalyzeResult(box=[0,0,1,1],detail=results[-1])

    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu()
    resource.register_custom_recognition('StoveLobbyFixture',Offline())
    assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker()
    assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    cases=[]
    for path,state in paths:
        frame=np.asarray(Image.open(path).convert('RGB'))[:,:,::-1].copy()
        cases.append((str(path),frame,state))
        if ((path.parent==run and path.name in ('agent_000003.png','agent_000007.png'))
                or (path.parent==day and path.name in ('agent_000162.png','agent_000167.png'))):
            cases.append((path.name+'/dimmed',(frame*.55).astype(np.uint8),'unknown'))
            boxes=[(742,72,838,133)]
            if state=='lobby_idle':boxes.append((22,12,98,68))
            for x1,y1,x2,y2 in boxes:
                covered=frame.copy();covered[y1:y2,x1:x2]=0
                cases.append((path.name+f'/covered-{x1}',covered,'unknown'))
    for name in ('00_lobby.png','02_lobby_idle.png','56_lobby_idle_day.png','23_story.png'):
        path=ROOT/'tests/fixtures/local'/name
        if path.exists():cases.append(('historical/'+name,
            np.asarray(Image.open(path).convert('RGB'))[:,:,::-1].copy(),
            'lobby' if name=='00_lobby.png' else 'lobby_idle' if 'idle' in name else 'unknown'))
    for name,frame,expected in cases:
        assert tasker.post_recognition('Custom',JCustomRecognition(
            custom_recognition='StoveLobbyFixture'),frame).wait().succeeded
        result=results[-1]
        if result['state'] != expected:
            pytest.fail(name+'\n'+json.dumps(result,indent=2))
        tree=build_tree({**result,'window':{'client_size':[1212,682]}},vision.spec)
        if expected=='lobby_idle':
            assert target_box(tree,'wake_lobby')==[1120,620,1,1]
            assert target_box(tree,'episode_button') is None
            assert tree['nodes']['visual:wake_lobby']['fields']['enabled']==fact()
        elif expected=='lobby':
            assert target_box(tree,'episode_button')==result['matches']['episode_button']['box']
            assert target_box(tree,'wake_lobby') is None
        else:
            assert target_box(tree,'wake_lobby') is None
            assert target_box(tree,'episode_button') is None
    (tmp_path/'stove-lobby-replay.json').write_text(json.dumps([
        {'case':c[0],'expected':c[2],'observed':r} for c,r in zip(cases,results)],indent=2),encoding='utf-8')
