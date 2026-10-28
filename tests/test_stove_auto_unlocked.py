"""Auto proofs are visual variants; locked skills and activation glow are unknown."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
import pytest
from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree,auto_state,fact,target_box
from driver_epic_seven.vision import Vision
from driver_epic_seven.runtime import Runtime


@pytest.mark.parametrize('on,manual,unlocked,expected',[(False,True,False,None),(False,True,True,False),
    (True,False,False,True),(True,True,False,None),(True,True,True,None),(False,False,True,None)])
@pytest.mark.parametrize('process',['EpicSeven.exe','EpicSeven_Steam.exe'])
def test_auto_keeps_ambiguity_and_requires_unlocked_manual_pair(process,on,manual,unlocked,expected):
    d={'state':'battle_running','window':{'process_name':process,'client_size':[1212,682]},
       'matches':{'auto_hud_on':{'hit':on},'auto_manual_skills':{'hit':manual},'auto_unlocked_off':{'hit':unlocked}}}
    tree=build_tree(d);assert auto_state({'ui_tree':tree}) is expected
    assert tree['nodes']['battle:auto']['fields']['enabled']==fact()
    if expected is False:
        assert {s['pointer'] for s in tree['nodes']['battle:auto']['fields']['value']['sources']}=={'/matches/auto_manual_skills','/matches/auto_unlocked_off'}
    if expected is True:
        runtime=Runtime.__new__(Runtime);runtime.observe=lambda name:{**d,'ui_tree':tree}
        assert runtime.ensure_auto()['changed'] is False  # No controller/tasker is installed on this stub.


@pytest.mark.parametrize('process',['EpicSeven.exe','EpicSeven_Steam.exe'])
def test_calibrated_legacy_off_proof_does_not_require_manual_or_unlocked_variant(process):
    d={'state':'battle_running','window':{'process_name':process,'client_size':[1212,682]},
       'matches':{'auto_hud_off':{'hit':True}}}
    tree=build_tree(d)
    assert auto_state({'ui_tree':tree}) is False
    assert {s['pointer'] for s in tree['nodes']['battle:auto']['fields']['value']['sources']}=={'/matches/auto_hud_off'}


@pytest.mark.parametrize('process',['EpicSeven.exe','EpicSeven_Steam.exe'])
def test_single_check_hint_never_promotes_auto_value_or_action_target(process):
    d={'state':'battle_running','window':{'process_name':process,'client_size':[1212,682]},
       'matches':{'auto_single_check_hint':{'hit':True,'box':[937,650,29,28]}}}
    tree=build_tree(d)
    assert auto_state({'ui_tree':tree}) is None
    assert target_box(tree,'auto_single_check_hint') is None


@pytest.mark.fixtures
def test_native_stove_auto_saved_unlock_on_off_and_locked_negatives(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    run=ROOT/'var/runs/20261027T060242Z_390d2724'
    paths=[(run/f'agent_{n:06}.png',want) for n,want in ((136,None),(139,False),(141,None),(142,None),(143,True),(144,True))]
    paths += [(ROOT/'var/runs'/r/f'agent_{n:06}.png',None) for r,n in (
      ('20261027T005115Z_8d1b189a',43),('20261027T005115Z_8d1b189a',45),('20261027T013137Z_d2916078',7),
      ('20261027T020703Z_0dc452c4',1),('20261027T034529Z_6b3c4cd0',83),('20261027T045511Z_1ec60bbf',74),
      ('20261027T055624Z_d8a1e216',10),('20261027T012018Z_f4ee88cc',11))]
    if not all(p.exists() for p,_ in paths):pytest.skip('Private STOVE Auto unlock evidence unavailable.')
    bundle=ROOT/'resources/epic-seven';vision=Vision(bundle/'vision.json',bundle);out=[]
    class Offline(CustomRecognition):
        def analyze(self,ctx,argv):
            filtered={}
            def recognize(name):
                raw=ctx.run_recognition(name,argv.image)
                if 'Auto' in name or name=='Stove.Template.BattlePause':
                    filtered[name]=[{'box':list(r.box),'score':r.score} for r in raw.filtered_results] if raw else []
                return raw
            out.append({'analysis':vision.inspect(argv.image,recognize),'filtered':filtered})
            return self.AnalyzeResult(box=[0,0,1,1],detail=out[-1])
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('StoveAutoFixture',Offline())
    assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    cases=[]
    for p,want in paths:
        f=np.asarray(Image.open(p).convert('RGB'))[:,:,::-1].copy();cases.append((str(p),f,want))
        if want is not None:
            cases.append((str(p)+'/dimmed',(f*.45).astype(np.uint8),None))
            covered=f.copy();covered[575:682,800:1212]=0;cases.append((str(p)+'/covered_hud',covered,None))
            if want is False:
                old=np.asarray(Image.open(ROOT/'var/runs/20261027T013137Z_d2916078/agent_000007.png').convert('RGB'))[:,:,::-1]
                changed=f.copy();changed[4:67,1038:1098]=old[4:67,1038:1098];cases.append((str(p)+'/locked_icon',changed,None))
            else:
                for left in (936,1010,1084,1158):
                    changed=f.copy();changed[647:676,left:left+27]=0;cases.append((str(p)+f'/missing_check{left}',changed,None))
    for name,f,want in cases:
        before=len(out);assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='StoveAutoFixture'),f).wait().succeeded
        assert len(out)==before+1
        a=out[-1]['analysis'];tree=build_tree({**a,'window':{'process_name':'EpicSeven.exe','client_size':[1212,682]}},vision.spec)
        assert auto_state({'ui_tree':tree}) is want,(name,a)
        if want is not None:assert tree['nodes']['battle:auto']['fields']['enabled']==fact()
    (tmp_path/'stove-auto-replay.json').write_text(json.dumps([
        {'case':c[0],'expected':c[2],**a} for c,a in zip(cases,out)],indent=2),encoding='utf-8')
