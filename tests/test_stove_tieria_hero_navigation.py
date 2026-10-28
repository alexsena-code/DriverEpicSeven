"""Tieria growth entries navigate only, with no requirement on current level."""
import json
import numpy as np
from PIL import Image
import pytest
from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree,target_box
from driver_epic_seven.vision import Vision


@pytest.mark.fixtures
def test_tieria_growth_entries_require_hero_identity_and_current_composition(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    run=ROOT/'var/runs/20261027T091000Z_a714adef'
    paths=[(run/f'agent_{n:06}.png',n in (15,18,21)) for n in (3,6,15,18,21)]
    paths += [(ROOT/'var/runs'/r/f'agent_{n:06}.png',False) for r,n in (
       ('20261027T065733Z_52d8869f',3),('20261027T065733Z_52d8869f',90),('20261027T074608Z_0b4c4ba2',3),
       ('20261027T085923Z_aaae21c1',5),('20261027T084618Z_f4017642',33),('20261027T005115Z_8d1b189a',22),
       ('20261027T060242Z_390d2724',55),('20261027T073707Z_93ef3e05',4))]
    if not all(p.exists() for p,_ in paths):pytest.skip('Private Tieria Hero fixtures unavailable.')
    bundle=ROOT/'resources/epic-seven';vision=Vision(bundle/'vision.json',bundle);out=[]
    targets={'tieria_hero_awaken_entry':[772,577,48,47],'tieria_hero_level_up_entry':[568,578,51,45]}
    class Offline(CustomRecognition):
        def analyze(self,ctx,argv):
            filtered={}
            def recognize(name):
                r=ctx.run_recognition(name,argv.image)
                if 'TieriaHero' in name or name=='Stove.Template.VictorikaHeroTab':
                    filtered[name]=[{'box':list(row.box),'score':row.score,'text':getattr(row,'text',None)} for row in r.filtered_results] if r else []
                return r
            out.append({'analysis':vision.inspect(argv.image,recognize),'filtered':filtered})
            return self.AnalyzeResult(box=[0,0,1,1],detail=out[-1])
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('TieriaHeroNavigationFixture',Offline())
    assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    cases=[]
    for p,want in paths:
        f=np.asarray(Image.open(p).convert('RGB'))[:,:,::-1].copy();cases.append((str(p),f,want))
        if p==run/'agent_000015.png':
            cases.append((str(p)+'/dimmed',(f*.45).astype(np.uint8),False))
            for label,(x,y,w,h) in [('hero_tab',(0,62,80,61)),('name',(94,106,282,44)),('traits',(90,69,262,45)),('awaken',(764,569,64,63)),('level_up',(560,570,67,61))]:
                changed=f.copy();changed[y:y+h,x:x+w]=0;cases.append((str(p)+'/missing_'+label,changed,False))
            changed=f.copy();changed[175:236,95:344]=0;cases.append((str(p)+'/level_not_used',changed,True))
    for name,f,want in cases:
        before=len(out);assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='TieriaHeroNavigationFixture'),f).wait().succeeded
        assert len(out)==before+1
        a=out[-1]['analysis'];tree=build_tree({**a,'window':{'process_name':'EpicSeven.exe','client_size':[1212,682]}},vision.spec)
        for key,box in targets.items():
            assert bool(target_box(tree,key)) is want,(name,key,a)
            if want:
                assert a['state']=='tieria_hero_growth'
                assert target_box(tree,key)==box
                assert tree['nodes']['visual:'+key]['fields']['enabled']['value'] is None
        if want:assert len(a['matches']['tieria_hero_name']['filtered_candidates'])==1
    (tmp_path/'tieria-hero-navigation-replay.json').write_text(json.dumps([
        {'case':c[0],'expected':c[2],**a} for c,a in zip(cases,out)],indent=2),encoding='utf-8')
