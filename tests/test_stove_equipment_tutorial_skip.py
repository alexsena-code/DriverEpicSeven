"""Equipment tutorial Skip requires its instruction and current highlighted hero card."""
import json
import numpy as np
from PIL import Image
import pytest
from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree,target_box
from driver_epic_seven.vision import Vision


@pytest.mark.fixtures
def test_native_equipment_tutorial_skip_rejects_other_guides_and_missing_context(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    run=ROOT/'var/runs/20261027T073707Z_93ef3e05'
    paths=[(run/f'agent_{n:06}.png',True) for n in (1,4)]
    paths += [(ROOT/'var/runs/20261027T065733Z_52d8869f'/f'agent_{n:06}.png',True) for n in (99,102)]
    paths += [(ROOT/'var/runs'/r/f'agent_{n:06}.png',False) for r,n in (
      ('20261027T064500Z_ea02d489',13),('20261027T064500Z_ea02d489',22),('20261027T065733Z_52d8869f',3),
      ('20261027T055624Z_d8a1e216',3),('20261027T003836Z_6bfd84bc',25),('20261027T060242Z_390d2724',136),
      ('20261027T060242Z_390d2724',3),('20261027T005115Z_8d1b189a',22),('20261027T055006Z_d1c129f7',13),('20261027T060242Z_390d2724',55))]
    if not all(p.exists() for p,_ in paths):pytest.skip('Private equipment tutorial fixtures unavailable.')
    bundle=ROOT/'resources/epic-seven';vision=Vision(bundle/'vision.json',bundle);out=[]
    assert vision.spec['templates']['equipment_tutorial_skip']==vision.spec['templates']['tutorial_skip']
    class Offline(CustomRecognition):
        def analyze(self,ctx,argv):
            filtered={}
            def recognize(name):
                raw=ctx.run_recognition(name,argv.image)
                if 'EquipmentTutorial' in name or name=='Stove.Template.TutorialSkip':
                    filtered[name]=[{'box':list(r.box),'score':r.score} for r in raw.filtered_results] if raw else []
                return raw
            out.append({'analysis':vision.inspect(argv.image,recognize),'filtered':filtered})
            return self.AnalyzeResult(box=[0,0,1,1],detail=out[-1])
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('EquipmentTutorialSkipFixture',Offline())
    assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    cases=[]
    for p,want in paths:
        f=np.asarray(Image.open(p).convert('RGB'))[:,:,::-1].copy();cases.append((str(p),f,want))
        if p==run/'agent_000001.png':
            cases.append((str(p)+'/dimmed',(f*.45).astype(np.uint8),False))
            for label,(x,y,w,h) in [('instruction',(586,226,322,90)),('card',(924,224,285,83)),('skip',(1020,8,165,55))]:
                changed=f.copy();changed[y:y+h,x:x+w]=0;cases.append((str(p)+'/missing_'+label,changed,False))
    for name,f,want in cases:
        before=len(out);assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='EquipmentTutorialSkipFixture'),f).wait().succeeded
        assert len(out)==before+1
        a=out[-1]['analysis'];tree=build_tree({**a,'window':{'process_name':'EpicSeven.exe','client_size':[1212,682]}},vision.spec)
        assert bool(target_box(tree,'equipment_tutorial_skip')) is want,(name,a)
        if want:
            assert a['state']=='equipment_tutorial_prompt'
            assert target_box(tree,'equipment_tutorial_skip')==[1040,19,125,28]
            assert tree['nodes']['visual:equipment_tutorial_skip']['fields']['enabled']['value'] is None
            assert target_box(tree,'arbiter_roster_row_10') is None
    (tmp_path/'equipment-tutorial-skip-replay.json').write_text(json.dumps([
        {'case':c[0],'expected':c[2],**a} for c,a in zip(cases,out)],indent=2),encoding='utf-8')
