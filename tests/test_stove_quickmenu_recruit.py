"""Recruit navigation is scoped to the observed quickmenu over Summon."""
import json
import numpy as np
from PIL import Image
import pytest
from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree,target_box
from driver_epic_seven.vision import Vision


@pytest.mark.fixtures
def test_native_recruit_requires_summon_quickmenu_composition(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    run=ROOT/'var/runs/20261027T081838Z_d968bc8e'
    paths=[(run/f'agent_{n:06}.png',n in (111,114,117)) for n in (79,82,102,105,108,111,114,117)]
    paths += [(ROOT/'var/runs'/r/f'agent_{n:06}.png',False) for r,n in (
       ('20261027T080001Z_4bad03e5',3),('20261027T060242Z_390d2724',55),('20261027T073707Z_93ef3e05',4),
       ('20261027T005115Z_8d1b189a',22),('20261027T024311Z_f1c0e142',69),('20261027T055624Z_d8a1e216',10))]
    if not all(p.exists() for p,_ in paths):pytest.skip('Private quickmenu Recruit fixtures unavailable.')
    bundle=ROOT/'resources/epic-seven';vision=Vision(bundle/'vision.json',bundle);out=[]
    class Offline(CustomRecognition):
        def analyze(self,ctx,argv):
            filtered={}
            def recognize(name):
                r=ctx.run_recognition(name,argv.image)
                if 'SummonQuickmenu' in name:filtered[name]=[{'box':list(row.box),'score':row.score} for row in r.filtered_results] if r else []
                return r
            out.append({'analysis':vision.inspect(argv.image,recognize),'filtered':filtered})
            return self.AnalyzeResult(box=[0,0,1,1],detail=out[-1])
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('QuickmenuRecruitFixture',Offline())
    assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    cases=[]
    for p,want in paths:
        f=np.asarray(Image.open(p).convert('RGB'))[:,:,::-1].copy();cases.append((str(p),f,want))
        if p==run/'agent_000111.png':
            cases.append((str(p)+'/dimmed',(f*.45).astype(np.uint8),False))
            for label,(x,y,w,h) in [('title',(54,10,115,45)),('close',(1150,6,49,50)),('composition',(986,100,187,86)),('recruit',(1105,216,70,81))]:
                changed=f.copy();changed[y:y+h,x:x+w]=0;cases.append((str(p)+'/missing_'+label,changed,False))
    for name,f,want in cases:
        before=len(out);assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='QuickmenuRecruitFixture'),f).wait().succeeded
        assert len(out)==before+1
        a=out[-1]['analysis'];tree=build_tree({**a,'window':{'process_name':'EpicSeven.exe','client_size':[1212,682]}},vision.spec)
        assert bool(target_box(tree,'summon_quickmenu_recruit')) is want,(name,a)
        if want:
            assert a['state']=='summon_quickmenu'
            assert target_box(tree,'summon_quickmenu_recruit')==[1113,224,54,65]
            assert tree['nodes']['visual:summon_quickmenu_recruit']['fields']['enabled']['value'] is None
            for consuming_target in ('result_confirm','victorika_acquisition_confirm','prequel_dap005_start'):
                assert target_box(tree,consuming_target) is None
    (tmp_path/'quickmenu-recruit-replay.json').write_text(json.dumps([
        {'case':c[0],'expected':c[2],**a} for c,a in zip(cases,out)],indent=2),encoding='utf-8')
