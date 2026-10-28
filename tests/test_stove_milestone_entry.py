"""Milestone entry requires current title/icon and the calibrated unobscured lobby."""
import json
import numpy as np
from PIL import Image
import pytest
from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree,target_box
from driver_epic_seven.vision import Vision


@pytest.mark.fixtures
def test_native_milestone_entry_and_menu_notification_invariance(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    run=ROOT/'var/runs/20261027T055624Z_d8a1e216'
    paths=[(run/f'agent_{n:06}.png',True) for n in (10,11,13,16)]+[(run/f'agent_{n:06}.png',False) for n in (3,4,7)]
    paths += [(ROOT/'var/runs'/r/f'agent_{n:06}.png',False) for r,n in (
        ('20261027T004547Z_58a7ec10',3),('20261027T004547Z_58a7ec10',6),
        ('20261027T005115Z_8d1b189a',19),('20261027T005115Z_8d1b189a',22),
        ('20261027T024311Z_f1c0e142',66),('20261027T024311Z_f1c0e142',72))]
    if not all(p.exists() for p,_ in paths):pytest.skip('Private current Milestone lobby fixtures unavailable.')
    bundle=ROOT/'resources/epic-seven';vision=Vision(bundle/'vision.json',bundle);out=[]
    class Offline(CustomRecognition):
        def analyze(self,ctx,argv):
            filtered={}
            def recognize(name):
                raw=ctx.run_recognition(name,argv.image)
                if name in ('Stove.Template.LobbyMenuGrid','Stove.Template.MilestoneLobbyEntry'):
                    filtered[name]=[{'box':list(r.box),'score':r.score} for r in raw.filtered_results] if raw else []
                return raw
            out.append({'analysis':vision.inspect(argv.image,recognize),'filtered':filtered})
            return self.AnalyzeResult(box=[0,0,1,1],detail=out[-1])
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('MilestoneLobbyFixture',Offline())
    assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    cases=[]
    for p,want in paths:
        f=np.asarray(Image.open(p).convert('RGB'))[:,:,::-1].copy();cases.append((str(p),f,want))
        if p==run/'agent_000010.png':
            cases.append((str(p)+'/dimmed',(f*.45).astype(np.uint8),False))
            for label,(x,y,w,h) in [('window',(742,72,96,61)),('menu',(1148,5,55,55)),('milestone_icon',(20,140,65,40)),('milestone_title',(0,181,104,36))]:
                changed=f.copy();changed[y:y+h,x:x+w]=0;cases.append((str(p)+'/missing_'+label,changed,False))
            for color in ((0,0,0),(255,0,255)):
                changed=f.copy();changed[13:31,1158:1176]=color;cases.append((str(p)+'/ignored_badge_'+str(color),changed,True))
    for name,f,want in cases:
        before=len(out);assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='MilestoneLobbyFixture'),f).wait().succeeded
        assert len(out)==before+1
        a=out[-1]['analysis'];tree=build_tree({**a,'window':{'process_name':'EpicSeven.exe','client_size':[1212,682]}},vision.spec)
        assert bool(target_box(tree,'milestone_lobby_entry')) is want,(name,a)
        if want:
            assert a['state']=='lobby'
            assert target_box(tree,'milestone_lobby_entry')==[6,143,96,73]
            assert target_box(tree,'episode_button')==[1066,158,108,36]
            assert tree['nodes']['visual:milestone_lobby_entry']['fields']['enabled']['value'] is None
        if name in {str(run/f'agent_{n:06}.png') for n in (3,4,7)}:
            assert a['state'] not in ('lobby','lobby_idle')
            assert target_box(tree,'episode_button') is None
    (tmp_path/'milestone-entry-replay.json').write_text(json.dumps([
        {'case':c[0],'expected':c[2],**a} for c,a in zip(cases,out)],indent=2),encoding='utf-8')
