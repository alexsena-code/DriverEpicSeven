"""Unit-specific physical Lydia target; not a generic tracker or executor."""
import json
import numpy as np
from PIL import Image
import pytest
from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree, target_box, fact, auto_state
from driver_epic_seven.vision import Vision


@pytest.mark.fixtures
def test_lydia_target_requires_name_body_and_current_battle_context(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    run=ROOT/'var/runs/20261027T013137Z_d2916078'
    positives=(4,13,20,22,24)
    if not all((run/f'agent_{n:06}.png').exists() for n in positives):pytest.skip('Private Lydia frames unavailable.')
    bundle=ROOT/'resources/epic-seven';v=Vision(bundle/'vision.json',bundle)
    v.spec['states']={k:s for k,s in v.spec['states'].items() if k in ('battle_running','battle_mercenary_lydia')}
    names={n for state in v.spec['states'].values() for s in state.get('variants',[state]) for c in ('all','any','none') for n in s.get(c,[])}
    v.spec['templates']={k:s for k,s in v.spec['templates'].items() if k in names};v.spec['ocr']={};out=[]
    class Offline(CustomRecognition):
        def analyze(self,ctx,argv):
            out.append(v.inspect(argv.image,lambda n:ctx.run_recognition(n,argv.image)))
            return self.AnalyzeResult(box=[0,0,1,1],detail=out[-1])
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('LydiaFixture',Offline())
    assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    cases=[]
    for n in positives:
        f=np.asarray(Image.open(run/f'agent_{n:06}.png').convert('RGB'))[:,:,::-1].copy();cases.append((str(n),f,True))
    f=cases[-1][1];cases.append(('dimmed',(f*.55).astype(np.uint8),False))
    for x1,y1,x2,y2 in ((275,0,470,40),(856,286,1024,539),(1150,8,1200,55)):
        a=f.copy();a[y1:y2,x1:x2]=0;cases.append((f'covered-{x1}',a,False))
    for p in [run/'agent_000001.png',ROOT/'var/runs/20261027T005115Z_8d1b189a/agent_000042.png',
              ROOT/'var/runs/20261027T004547Z_58a7ec10/agent_000003.png',
              ROOT/'var/runs/20261027T005115Z_8d1b189a/agent_000004.png',
              ROOT/'var/runs/20261027T011501Z_1691e5c9/agent_000009.png']:
        cases.append((str(p),np.asarray(Image.open(p).convert('RGB'))[:,:,::-1].copy(),False))
    for name,f,expected in cases:
        before=len(out)
        assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='LydiaFixture'),f).wait().succeeded
        assert len(out)==before+1
        a=out[-1];tree=build_tree({**a,'window':{'client_size':[1212,682]}},v.spec);box=target_box(tree,'mercenary_lydia_body')
        if expected:
            assert a['state']=='battle_mercenary_lydia',(name,a)
            assert box==a['matches']['mercenary_lydia_body']['box'] and box[2:]==[120,205]
            assert tree['nodes']['visual:mercenary_lydia_body']['fields']['enabled']==fact()
        else:assert box is None and a['state']!='battle_mercenary_lydia',(name,a)
        assert auto_state({'ui_tree':tree}) is None
    (tmp_path/'lydia-target-replay.json').write_text(json.dumps([
        {'case':c[0],'expected_target':c[2],'observed':a} for c,a in zip(cases,out)],indent=2),encoding='utf-8')
