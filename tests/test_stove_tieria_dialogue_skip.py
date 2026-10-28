"""Tieria Connection dialogue Skip requires its current identity, line and History."""
import json
import numpy as np
from PIL import Image
import pytest
from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree,target_box
from driver_epic_seven.vision import Vision


@pytest.mark.fixtures
def test_specific_dialogue_target_stays_separate_from_generic_story(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    run=ROOT/'var/runs/20261027T084618Z_f4017642'
    paths=[(run/f'agent_{n:06}.png',n in (33,36,39)) for n in (3,30,33,36,39)]
    paths += [(ROOT/'var/runs'/r/f'agent_{n:06}.png',False) for r,n in (
       ('20261027T005115Z_8d1b189a',19),('20261027T005115Z_8d1b189a',22),('20261027T012018Z_f4ee88cc',40),
       ('20261027T034529Z_6b3c4cd0',151),('20261027T034529Z_6b3c4cd0',156),
       ('20261027T060242Z_390d2724',55),('20261027T073707Z_93ef3e05',4),('20261027T055624Z_d8a1e216',10))]
    if not all(p.exists() for p,_ in paths):pytest.skip('Private Tieria dialogue fixtures unavailable.')
    bundle=ROOT/'resources/epic-seven';vision=Vision(bundle/'vision.json',bundle);out=[]
    class Offline(CustomRecognition):
        def analyze(self,ctx,argv):
            filtered={}
            def recognize(name):
                r=ctx.run_recognition(name,argv.image)
                if 'Tieria' in name or name=='Stove.Template.StorySkip':filtered[name]=[{'box':list(row.box),'score':row.score} for row in r.filtered_results] if r else []
                return r
            out.append({'analysis':vision.inspect(argv.image,recognize),'filtered':filtered})
            return self.AnalyzeResult(box=[0,0,1,1],detail=out[-1])
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('TieriaDialogueSkipFixture',Offline())
    assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    cases=[]
    for p,want in paths:
        f=np.asarray(Image.open(p).convert('RGB'))[:,:,::-1].copy();cases.append((str(p),f,want))
        if p==run/'agent_000033.png':
            cases.append((str(p)+'/dimmed',(f*.45).astype(np.uint8),False))
            for label,(x,y,w,h) in [('name',(511,482,191,48)),('line',(236,551,744,49)),('history',(1015,12,52,49)),('skip',(1100,8,108,65))]:
                changed=f.copy();changed[y:y+h,x:x+w]=0;cases.append((str(p)+'/missing_'+label,changed,False))
    for name,f,want in cases:
        before=len(out);assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='TieriaDialogueSkipFixture'),f).wait().succeeded
        assert len(out)==before+1
        a=out[-1]['analysis'];tree=build_tree({**a,'window':{'process_name':'EpicSeven.exe','client_size':[1212,682]}},vision.spec)
        assert bool(target_box(tree,'tieria_connection_dialogue_skip')) is want,(name,a)
        if want:
            assert a['state']=='tieria_connection_dialogue'
            assert target_box(tree,'tieria_connection_dialogue_skip')==[1123,21,66,31]
            assert tree['nodes']['visual:tieria_connection_dialogue_skip']['fields']['enabled']['value'] is None
            # History glyphs are shared by the now-calibrated gray header.
            # Their presence does not replace this dialogue's full composition
            # or expose the generic story executor on the specific dialogue.
            assert target_box(tree,'story_skip') is None
    (tmp_path/'tieria-dialogue-skip-replay.json').write_text(json.dumps([
        {'case':c[0],'expected':c[2],**a} for c,a in zip(cases,out)],indent=2),encoding='utf-8')
