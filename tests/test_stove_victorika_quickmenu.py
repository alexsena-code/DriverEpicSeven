"""Quickmenu target is available only in the calibrated Victorika Hero-page context."""
import json
import numpy as np
from PIL import Image
import pytest
from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree,target_box
from driver_epic_seven.vision import Vision


@pytest.mark.fixtures
def test_native_victorika_quickmenu_requires_hero_tab_current_name_level_and_card(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    run=ROOT/'var/runs/20261027T074608Z_0b4c4ba2'
    paths=[(run/f'agent_{n:06}.png',True) for n in (3,6,9)]
    paths += [(ROOT/'var/runs'/r/f'agent_{n:06}.png',False) for r,n in (
       ('20261027T064500Z_ea02d489',22),('20261027T065733Z_52d8869f',3),('20261027T034529Z_6b3c4cd0',156),
       ('20261027T073707Z_93ef3e05',4),('20261027T055624Z_d8a1e216',10),('20261027T060242Z_390d2724',10),
       ('20261027T060242Z_390d2724',6),('20261027T005115Z_8d1b189a',22),('20261027T060242Z_390d2724',49),
       ('20261027T065733Z_52d8869f',12),('20261027T060242Z_390d2724',136))]
    if not all(p.exists() for p,_ in paths):pytest.skip('Private Victorika quickmenu fixtures unavailable.')
    bundle=ROOT/'resources/epic-seven';vision=Vision(bundle/'vision.json',bundle);out=[]
    assert vision.spec['templates']['victorika_hero_quickmenu']==vision.spec['templates']['lobby_menu_grid']
    class Offline(CustomRecognition):
        def analyze(self,ctx,argv):
            filtered={}
            def recognize(name):
                r=ctx.run_recognition(name,argv.image)
                if 'VictorikaHero' in name or 'VictorikaEquipmentCurrent' in name or name in ('Stove.Template.LobbyMenuGrid','Stove.Template.EquipmentTutorialVictorikaCard'):
                    filtered[name]=[{'box':list(row.box),'score':row.score,'text':getattr(row,'text',None)} for row in r.filtered_results] if r else []
                return r
            out.append({'analysis':vision.inspect(argv.image,recognize),'filtered':filtered})
            return self.AnalyzeResult(box=[0,0,1,1],detail=out[-1])
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('VictorikaQuickmenuFixture',Offline())
    assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    cases=[]
    for p,want in paths:
        f=np.asarray(Image.open(p).convert('RGB'))[:,:,::-1].copy();cases.append((str(p),f,want))
        if p==run/'agent_000003.png':
            cases.append((str(p)+'/dimmed',(f*.45).astype(np.uint8),False))
            for label,(x,y,w,h) in [('tab',(0,62,80,61)),('card',(943,232,136,65)),('menu',(1148,5,55,55)),('name',(98,104,162,47)),('level',(96,176,141,40))]:
                changed=f.copy();changed[y:y+h,x:x+w]=0;cases.append((str(p)+'/missing_'+label,changed,False))
    for name,f,want in cases:
        before=len(out);assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='VictorikaQuickmenuFixture'),f).wait().succeeded
        assert len(out)==before+1
        a=out[-1]['analysis'];tree=build_tree({**a,'window':{'process_name':'EpicSeven.exe','client_size':[1212,682]}},vision.spec)
        assert bool(target_box(tree,'victorika_hero_quickmenu')) is want,(name,a)
        if want:
            assert a['state']=='victorika_hero_menu'
            assert target_box(tree,'victorika_hero_quickmenu')==[1158,13,35,36]
            assert tree['nodes']['visual:victorika_hero_quickmenu']['fields']['enabled']['value'] is None
            assert target_box(tree,'equipment_tutorial_skip') is None
    (tmp_path/'victorika-quickmenu-replay.json').write_text(json.dumps([
        {'case':c[0],'expected':c[2],**a} for c,a in zip(cases,out)],indent=2),encoding='utf-8')
