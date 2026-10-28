"""Friendship close requires the current title, separate1/2 badges and close prompt."""
import json
import numpy as np
from PIL import Image
import pytest
from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree,target_box
from driver_epic_seven.vision import Vision


@pytest.mark.fixtures
def test_native_friendship_result_close_rejects_other_results_and_changed_levels(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    run=ROOT/'var/runs/20261027T080001Z_4bad03e5'
    paths=[(run/f'agent_{n:06}.png',n in (48,51,54)) for n in (36,44,46,48,51,54)]
    paths += [(ROOT/'var/runs'/r/f'agent_{n:06}.png',False) for r,n in (
       ('20261027T060242Z_390d2724',55),('20261027T060242Z_390d2724',71),('20261027T073707Z_93ef3e05',4),
       ('20261027T005115Z_8d1b189a',22),('20261027T024311Z_f1c0e142',69),('20261027T055624Z_d8a1e216',10))]
    if not all(p.exists() for p,_ in paths):pytest.skip('Private friendship result fixtures unavailable.')
    bundle=ROOT/'resources/epic-seven';vision=Vision(bundle/'vision.json',bundle);out=[]
    class Offline(CustomRecognition):
        def analyze(self,ctx,argv):
            filtered={}
            def recognize(name):
                r=ctx.run_recognition(name,argv.image)
                if 'Friendship' in name:filtered[name]=[{'box':list(row.box),'score':row.score} for row in r.filtered_results] if r else []
                return r
            out.append({'analysis':vision.inspect(argv.image,recognize),'filtered':filtered})
            return self.AnalyzeResult(box=[0,0,1,1],detail=out[-1])
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('FriendshipResultFixture',Offline())
    assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    cases=[]
    for p,want in paths:
        f=np.asarray(Image.open(p).convert('RGB'))[:,:,::-1].copy();cases.append((str(p),f,want))
        if p==run/'agent_000048.png':
            cases.append((str(p)+'/dimmed',(f*.45).astype(np.uint8),False))
            for label,(x,y,w,h) in [('title',(499,127,436,58)),('level1',(441,297,23,26)),('level2',(773,297,23,26)),('close',(646,505,142,70))]:
                changed=f.copy();changed[y:y+h,x:x+w]=0;cases.append((str(p)+'/missing_'+label,changed,False))
            changed=f.copy();changed[297:323,441:464]=f[297:323,773:796];cases.append((str(p)+'/wrong_before_level',changed,False))
    for name,f,want in cases:
        before=len(out);assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='FriendshipResultFixture'),f).wait().succeeded
        assert len(out)==before+1
        a=out[-1]['analysis'];tree=build_tree({**a,'window':{'process_name':'EpicSeven.exe','client_size':[1212,682]}},vision.spec)
        assert bool(target_box(tree,'friendship_result_close')) is want,(name,a)
        if want:
            assert a['state']=='friendship_result_1_to_2'
            assert target_box(tree,'friendship_result_close')==[656,515,122,50]
            assert tree['nodes']['visual:friendship_result_close']['fields']['enabled']['value'] is None
            assert target_box(tree,'result_confirm') is None
    (tmp_path/'friendship-result-replay.json').write_text(json.dumps([
        {'case':c[0],'expected':c[2],**a} for c,a in zip(cases,out)],indent=2),encoding='utf-8')
