"""A physical boss target needs its current body, exact name and combat HUD."""
import json
import numpy as np
from PIL import Image
import pytest
from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree, target_box, fact, auto_state
from driver_epic_seven.vision import Vision


@pytest.mark.fixtures
def test_nightmare_target_uses_current_box_and_rejects_incomplete_context(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    run=ROOT/'var/runs/20261027T010445Z_262a2dda'
    numbers=(7,9,11,13,16,19)
    if not all((run/f'agent_{n:06}.png').exists() for n in numbers):
        pytest.skip('Private STOVE boss-target frames are not installed.')
    bundle=ROOT/'resources/epic-seven';v=Vision(bundle/'vision.json',bundle)
    v.spec['states']={k:s for k,s in v.spec['states'].items() if k in ('battle_running','battle_nightmare_keeper')}
    names={n for state in v.spec['states'].values() for s in state.get('variants',[state]) for clause in ('all','any','none') for n in s.get(clause,[])}
    v.spec['templates']={k:s for k,s in v.spec['templates'].items() if k in names};v.spec['ocr']={};results=[]
    class Offline(CustomRecognition):
        def analyze(self,context,argv):
            results.append(v.inspect(argv.image,lambda n:context.run_recognition(n,argv.image)))
            return self.AnalyzeResult(box=[0,0,1,1],detail=results[-1])
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('StoveBossFixture',Offline())
    assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    cases=[]
    for n in numbers:
        f=np.asarray(Image.open(run/f'agent_{n:06}.png').convert('RGB'))[:,:,::-1].copy()
        cases.append((str(n),f,True))
    post_attack=ROOT/'var/runs/20261027T011501Z_1691e5c9'
    for n in (6,7,9):
        path=post_attack/f'agent_{n:06}.png'
        if path.exists():
            f=np.asarray(Image.open(path).convert('RGB'))[:,:,::-1].copy()
            cases.append((f'postattack/{n}',f,True))
    f=cases[-1][1]
    cases.append(('dimmed',(f*.55).astype(np.uint8),False))
    for x1,y1,x2,y2 in ((275,0,475,38),(930,8,975,60),(955,245,1165,440)):
        covered=f.copy();covered[y1:y2,x1:x2]=0
        cases.append((f'covered-{x1}',covered,False))
    for folder,n in [('20261027T005115Z_8d1b189a',33),('20261027T005115Z_8d1b189a',39),
                     ('20261027T005115Z_8d1b189a',42),('20261027T005115Z_8d1b189a',45),
                     ('20261027T005115Z_8d1b189a',4),('20261027T005115Z_8d1b189a',7),
                     ('20261027T004547Z_58a7ec10',3),('20261027T004547Z_58a7ec10',7)]:
        p=ROOT/'var/runs'/folder/f'agent_{n:06}.png'
        if p.exists():cases.append((folder+'/'+p.name,np.asarray(Image.open(p).convert('RGB'))[:,:,::-1].copy(),False))
    for name,frame,expected in cases:
        assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='StoveBossFixture'),frame).wait().succeeded
        a=results[-1];tree=build_tree({**a,'window':{'client_size':[1212,682]}},v.spec)
        box=target_box(tree,'nightmare_keeper_body')
        if expected:
            assert a['state']=='battle_nightmare_keeper',(name,a)
            assert box==a['matches']['nightmare_keeper_body']['box']
            assert 955<=box[0] and 245<=box[1] and box[0]+box[2]<=1165 and box[1]+box[3]<=440
            assert tree['nodes']['visual:nightmare_keeper_body']['fields']['enabled']==fact()
        else:
            assert a['state']!='battle_nightmare_keeper' and box is None,(name,a)
        assert auto_state({'ui_tree':tree}) is None
    (tmp_path/'stove-boss-replay.json').write_text(json.dumps([
        {'case':c[0],'expected_target':c[2],'observed':r} for c,r in zip(cases,results)],indent=2),encoding='utf-8')
