"""A scoped promotional dismiss target must never become a hero acquisition claim."""
import json
import numpy as np
from PIL import Image
import pytest
from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree, operation_view, target_box
from driver_epic_seven.vision import Vision


def test_promotional_target_is_bound_to_its_own_state_without_acquisition_claim():
    spec=json.loads((ROOT/'resources/epic-seven/vision.json').read_text(encoding='utf-8'))
    d={'state':'renoa_promotional_presentation','window':{'process_name':'EpicSeven.exe','client_size':[1212,682]},
       'matches':{key:{'hit':True} for key in spec['states']['renoa_promotional_presentation']['all']}}
    d['matches']['renoa_promotional_confirm'].update(box=[1045,612,77,31],score=.9996,text='Confirm')
    tree=build_tree(d,spec)
    assert target_box(tree,'renoa_promotional_confirm')==[1045,612,77,31]
    presentation=operation_view({'ui_tree':tree})
    assert presentation['view']=='hero_presentation' and presentation['mode']=='promotion'
    assert presentation['items'][0]['acquired'] is None
    assert presentation['items'][0]['summon_performed'] is None
    for state in ('unknown','victorika_acquisition_result','story_confirmation'):
        d['state']=state
        assert target_box(build_tree(d,spec),'renoa_promotional_confirm') is None


@pytest.mark.fixtures
def test_native_renoa_identity_and_current_confirm_reject_other_presentations(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    run=ROOT/'var/runs/20261027T055006Z_d1c129f7'
    paths=[(run/f'agent_{n:06}.png',True) for n in (7,10,13)]
    paths += [(ROOT/'var/runs'/r/f'agent_{n:06}.png',False) for r,n in (
       ('20261027T034529Z_6b3c4cd0',151),('20261027T034529Z_6b3c4cd0',156),
       ('20261027T045511Z_1ec60bbf',96),('20261027T005115Z_8d1b189a',19),('20261027T005115Z_8d1b189a',22))]
    if not all(p.exists() for p,_ in paths):pytest.skip('Private Renoa promotional fixtures unavailable.')
    bundle=ROOT/'resources/epic-seven';vision=Vision(bundle/'vision.json',bundle);out=[]
    class Offline(CustomRecognition):
        def analyze(self,ctx,argv):
            filtered={}
            def recognize(name):
                raw=ctx.run_recognition(name,argv.image)
                if 'Renoa' in name:
                    filtered[name]=[{'box':list(r.box),'score':getattr(r,'score',None),'text':getattr(r,'text',None)} for r in raw.filtered_results] if raw else []
                return raw
            out.append({'analysis':vision.inspect(argv.image,recognize),'filtered':filtered})
            return self.AnalyzeResult(box=[0,0,1,1],detail=out[-1])
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('RenoaPromoFixture',Offline())
    assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    cases=[]
    for p,want in paths:
        f=np.asarray(Image.open(p).convert('RGB'))[:,:,::-1].copy();cases.append((str(p),f,want))
        if p==run/'agent_000007.png':
            cases.append((str(p)+'/dimmed',(f*.45).astype(np.uint8),False))
            dark=f.copy();dark[596:657,1007:1144]=(dark[596:657,1007:1144]*.45).astype(np.uint8)
            cases.append((str(p)+'/dark_confirm',dark,False))
            for name,(x,y,w,h) in [('name',(228,128,152,61)),('traits',(198,71,203,52)),('description',(124,283,374,63))]:
                altered=f.copy();altered[y:y+h,x:x+w]=0;cases.append((str(p)+'/missing_'+name,altered,False))
    for name,f,want in cases:
        before=len(out);assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='RenoaPromoFixture'),f).wait().succeeded
        assert len(out)==before+1
        a=out[-1]['analysis'];tree=build_tree({**a,'window':{'process_name':'EpicSeven.exe','client_size':[1212,682]}},vision.spec)
        assert bool(target_box(tree,'renoa_promotional_confirm')) is want,(name,a)
        if want:
            assert a['state']=='renoa_promotional_presentation'
            assert target_box(tree,'renoa_promotional_confirm')==[1045,612,77,31]
            assert len(out[-1]['filtered']['Stove.OCR.RenoaPromotionalConfirm'])==1
            presentation=operation_view({'ui_tree':tree})
            assert presentation['view']=='hero_presentation' and presentation['mode']=='promotion'
            assert presentation['items'][0]['acquired'] is None
            assert target_box(tree,'victorika_acquisition_confirm') is None
    (tmp_path/'renoa-promo-replay.json').write_text(json.dumps([
        {'case':c[0],'expected':c[2],**a} for c,a in zip(cases,out)],indent=2),encoding='utf-8')
