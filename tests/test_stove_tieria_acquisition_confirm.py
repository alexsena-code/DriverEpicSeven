"""Tieria result Confirm requires identity/context and the normal shared button."""
import json
import numpy as np
from PIL import Image
import pytest
from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree,target_box
from driver_epic_seven.vision import Vision


@pytest.mark.fixtures
def test_tieria_confirm_rejects_other_heroes_and_dim_button(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    run=ROOT/'var/runs/20261027T085923Z_aaae21c1'
    paths=[(run/f'agent_{n:06}.png',True) for n in (5,8,11)]
    paths += [(ROOT/'var/runs'/r/f'agent_{n:06}.png',False) for r,n in (
       ('20261027T084618Z_f4017642',30),('20261027T084618Z_f4017642',33),('20261027T005115Z_8d1b189a',22),
       ('20261027T034529Z_6b3c4cd0',151),('20261027T034529Z_6b3c4cd0',156),
       ('20261027T055006Z_d1c129f7',7),('20261027T045511Z_1ec60bbf',96),
       ('20261027T060242Z_390d2724',55),('20261027T073707Z_93ef3e05',4),('20261027T055624Z_d8a1e216',10))]
    if not all(p.exists() for p,_ in paths):pytest.skip('Private Tieria acquisition fixtures unavailable.')
    bundle=ROOT/'resources/epic-seven';vision=Vision(bundle/'vision.json',bundle);out=[]
    class Offline(CustomRecognition):
        def analyze(self,ctx,argv):
            filtered={}
            def recognize(name):
                r=ctx.run_recognition(name,argv.image)
                if 'TieriaAcquisition' in name or name in ('Stove.Template.VictorikaAcquisitionConfirmNormal','Stove.OCR.RenoaPromotionalConfirm'):
                    filtered[name]=[{'box':list(row.box),'score':row.score,'text':getattr(row,'text',None)} for row in r.filtered_results] if r else []
                return r
            out.append({'analysis':vision.inspect(argv.image,recognize),'filtered':filtered})
            return self.AnalyzeResult(box=[0,0,1,1],detail=out[-1])
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('TieriaAcquisitionConfirmFixture',Offline())
    assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    dark=np.asarray(Image.open(ROOT/'var/runs/20261027T034529Z_6b3c4cd0/agent_000151.png').convert('RGB'))[:,:,::-1].copy()
    cases=[]
    for p,want in paths:
        f=np.asarray(Image.open(p).convert('RGB'))[:,:,::-1].copy();cases.append((str(p),f,want))
        if p==run/'agent_000005.png':
            cases.append((str(p)+'/dimmed',(f*.45).astype(np.uint8),False))
            for label,(x,y,w,h) in [('name',(23,55,353,59)),('traits',(20,13,269,49)),('description',(19,106,224,80)),('confirm',(1000,596,145,65))]:
                changed=f.copy();changed[y:y+h,x:x+w]=0;cases.append((str(p)+'/missing_'+label,changed,False))
            changed=f.copy();changed[596:661,1000:1145]=dark[596:661,1000:1145];cases.append((str(p)+'/dark_confirm',changed,False))
    for name,f,want in cases:
        before=len(out);assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='TieriaAcquisitionConfirmFixture'),f).wait().succeeded
        assert len(out)==before+1
        a=out[-1]['analysis'];tree=build_tree({**a,'window':{'process_name':'EpicSeven.exe','client_size':[1212,682]}},vision.spec)
        assert bool(target_box(tree,'tieria_acquisition_confirm')) is want,(name,a)
        if want:
            assert a['state']=='tieria_acquisition_presentation'
            assert target_box(tree,'tieria_acquisition_confirm')==[1036,611,78,32]
            assert tree['nodes']['visual:tieria_acquisition_confirm']['fields']['enabled']['value'] is None
            assert len(a['matches']['tieria_acquisition_confirm']['filtered_candidates'])==1
            assert target_box(tree,'renoa_promotional_confirm') is None
            assert target_box(tree,'victorika_acquisition_confirm') is None
    (tmp_path/'tieria-acquisition-confirm-replay.json').write_text(json.dumps([
        {'case':c[0],'expected':c[2],**a} for c,a in zip(cases,out)],indent=2),encoding='utf-8')
