"""Confirm belongs only to the normal Victorika receipt, never its dialogue or a summon."""
from copy import deepcopy
import json
import numpy as np
from PIL import Image
import pytest
from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree,operation_view,target_box
from driver_epic_seven.vision import Vision


def test_receipt_reading_keeps_instance_origin_enabled_and_dialogue_unknowns():
    spec=json.loads((ROOT/'resources/epic-seven/vision.json').read_text(encoding='utf-8'))
    keys=('name','traits','new','four_stars','confirm_normal')
    d={'state':'victorika_acquisition_result','window':{'process_name':'EpicSeven.exe','client_size':[1212,682]},
       'matches':{f'victorika_acquisition_{k}':{'hit':True} for k in keys}}
    d['matches']['victorika_acquisition_confirm']={'hit':True,'box':[1036,611,78,32],'text':'Confirm','score':.9991}
    tree=build_tree(d,spec);v=operation_view({'ui_tree':tree});c=v['items'][0]
    assert c['hero_name']=='Victorika' and c['hero_catalog_id']=='c1166' and c['displayed_rarity']==4
    assert c['element_label']=='Fire' and c['role_label']=='Knight' and c['zodiac_label']=='Leo'
    assert c['acquisition_announced'] is True and c['new_badge_visible'] is True
    for name in ('owned_instance_id','complete_roster','acquisition_origin','summon_performed','acknowledgement_completed'):
        assert c[name] is None
    assert v['controls'][0]['enabled'] is None and v['controls'][0]['consuming'] is False
    assert target_box(tree,'victorika_acquisition_confirm')==[1036,611,78,32]
    dialogue=deepcopy(d);dialogue['state']='victorika_acquisition_dialogue'
    dialogue['matches']['victorika_acquisition_speech_name']={'hit':True}
    dialogue['matches']['victorika_acquisition_confirm_normal']['hit']=False
    tree=build_tree(dialogue,spec);v=operation_view({'ui_tree':tree})
    assert v['items'][0]['speech_visible'] is True and not v['controls']
    assert target_box(tree,'victorika_acquisition_confirm') is None


@pytest.mark.fixtures
def test_native_acquisition_confirm_positive_phases_and_dialogue_negatives(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    run=ROOT/'var/runs/20261027T034529Z_6b3c4cd0'
    paths=[(run/f'agent_{n:06}.png',True) for n in (156,157,159,160)]
    paths += [(run/'agent_000151.png',False)]
    paths += [(ROOT/'var/runs/20261027T024311Z_f1c0e142'/f'agent_{n:06}.png',False) for n in (48,63,66,69,75)]
    paths += [(ROOT/'var/runs/20261027T031057Z_dcdc3935/agent_000010.png',False),
              (ROOT/'var/runs/20261027T005115Z_8d1b189a/agent_000022.png',False),
              (ROOT/'var/runs/20261026T232625Z_eef54186/agent_000267.png',False)]
    if not all(p.exists() for p,_ in paths):pytest.skip('Private acquisition fixture frames unavailable.')
    bundle=ROOT/'resources/epic-seven';vision=Vision(bundle/'vision.json',bundle);out=[]
    class Offline(CustomRecognition):
        def analyze(self,ctx,argv):
            filtered={}
            def match(name):
                raw=ctx.run_recognition(name,argv.image)
                if 'VictorikaAcquisition' in name:
                    filtered[name]=[{'box':list(r.box),'score':getattr(r,'score',None),'text':getattr(r,'text',None)} for r in raw.filtered_results] if raw else []
                return raw
            out.append({'analysis':vision.inspect(argv.image,match),'filtered':filtered})
            return self.AnalyzeResult(box=[0,0,1,1],detail=out[-1])
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('AcquisitionConfirmFixture',Offline());assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    cases=[]
    for p,want in paths:
        frame=np.asarray(Image.open(p).convert('RGB'))[:,:,::-1].copy();cases.append((str(p),frame,want))
        if p==run/'agent_000156.png':
            cases.append((str(p)+'/dimmed',(frame*.45).astype(np.uint8),False))
            for label,(x,y,w,h) in [('name',(19,52,211,68)),('new',(247,101,88,89)),('fourth_star',(290,73,22,33)),('confirm',(1007,596,137,61))]:
                changed=frame.copy();changed[y:y+h,x:x+w]=0;cases.append((str(p)+'/missing_'+label,changed,False))
            changed=frame.copy();speech=np.asarray(Image.open(run/'agent_000151.png').convert('RGB'))[:,:,::-1]
            changed[478:531,545:669]=speech[478:531,545:669];cases.append((str(p)+'/speech_with_normal_button',changed,False))
    for name,frame,want in cases:
        before=len(out);assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='AcquisitionConfirmFixture'),frame).wait().succeeded
        assert len(out)==before+1
        a=out[-1]['analysis'];tree=build_tree({**a,'window':{'process_name':'EpicSeven.exe','client_size':[1212,682]}},vision.spec)
        box=target_box(tree,'victorika_acquisition_confirm')
        assert bool(box) is want,(name,a)
        if want:
            assert a['state']=='victorika_acquisition_result'
            assert box==a['matches']['victorika_acquisition_confirm']['box']
            assert len(out[-1]['filtered']['Stove.OCR.VictorikaAcquisitionConfirm'])==1
            v=operation_view({'ui_tree':tree})
            assert v['items'][0]['displayed_rarity']==4 and v['controls'][0]['enabled'] is None
        if name.endswith('agent_000151.png'):
            assert a['state']=='victorika_acquisition_dialogue'
            assert operation_view({'ui_tree':tree})['controls']==[]
    (tmp_path/'acquisition-confirm-replay.json').write_text(json.dumps([
        {'case':c[0],'expected':c[2],**a} for c,a in zip(cases,out)],indent=2),encoding='utf-8')
