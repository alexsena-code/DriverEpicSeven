"""A clipped hero name requires the exact observed row and equipment/roster context."""
import json
import numpy as np
from PIL import Image
import pytest
from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree,target_box,operation_view
from driver_epic_seven.vision import Vision


@pytest.mark.fixtures
def test_native_arbiter_row_requires_exact_equipment_context_and_target_identity(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    run=ROOT/'var/runs/20261027T064500Z_ea02d489'
    paths=[(run/f'agent_{n:06}.png',n in (16,19,22)) for n in (7,10,13,16,19,22)]
    paths += [(ROOT/'var/runs'/r/f'agent_{n:06}.png',False) for r,n in (
       ('20261027T031057Z_dcdc3935',10),('20261027T034529Z_6b3c4cd0',156),('20261027T055624Z_d8a1e216',10),
       ('20261027T060242Z_390d2724',49),('20261027T060242Z_390d2724',55),('20261027T024311Z_f1c0e142',69))]
    if not all(p.exists() for p,_ in paths):pytest.skip('Private Arbiter equipment-row fixtures unavailable.')
    bundle=ROOT/'resources/epic-seven';vision=Vision(bundle/'vision.json',bundle);out=[]
    class Offline(CustomRecognition):
        def analyze(self,ctx,argv):
            filtered={}
            def recognize(name):
                r=ctx.run_recognition(name,argv.image)
                if 'Arbiter' in name or 'VictorikaEquipment' in name or 'VictorikaThree' in name:
                    filtered[name]=[{'box':list(row.box),'score':row.score,'text':getattr(row,'text',None)} for row in r.filtered_results] if r else []
                return r
            out.append({'analysis':vision.inspect(argv.image,recognize),'filtered':filtered})
            return self.AnalyzeResult(box=[0,0,1,1],detail=out[-1])
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('ArbiterRowFixture',Offline())
    assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    cases=[]
    for p,want in paths:
        f=np.asarray(Image.open(p).convert('RGB'))[:,:,::-1].copy();cases.append((str(p),f,want))
        if p==run/'agent_000016.png':
            cases.append((str(p)+'/dimmed',(f*.45).astype(np.uint8),False))
            for label,(x,y,w,h) in [('portrait',(1100,307,112,50)),('traits',(960,320,132,37)),('tab',(0,135,81,58)),('name',(98,104,162,47)),('level',(96,176,141,40))]:
                changed=f.copy();changed[y:y+h,x:x+w]=0;cases.append((str(p)+'/missing_'+label,changed,False))
            changed=f.copy();changed[307:357,960:1212]=f[359:409,960:1212];cases.append((str(p)+'/other_hero_row',changed,False))
    for name,f,want in cases:
        before=len(out);assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='ArbiterRowFixture'),f).wait().succeeded
        assert len(out)==before+1
        a=out[-1]['analysis'];tree=build_tree({**a,'window':{'process_name':'EpicSeven.exe','client_size':[1212,682]}},vision.spec)
        assert bool(target_box(tree,'arbiter_roster_row_10')) is want,(name,a)
        if want:
            assert a['state']=='victorika_equipment_arbiter_roster'
            assert target_box(tree,'arbiter_roster_row_10')==[960,307,252,50]
            assert operation_view({'ui_tree':tree})=={}
            assert tree['nodes']['visual:arbiter_roster_row_10']['fields']['enabled']['value'] is None
    (tmp_path/'arbiter-row-replay.json').write_text(json.dumps([
        {'case':c[0],'expected':c[2],**a} for c,a in zip(cases,out)],indent=2),encoding='utf-8')
