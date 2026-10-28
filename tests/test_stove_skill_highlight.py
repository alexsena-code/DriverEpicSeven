"""A highlighted skill border is not Auto, readiness, or an action receipt."""
import json
import numpy as np
from PIL import Image
import pytest
from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree, operation_view, target_box, auto_state, fact
from driver_epic_seven.vision import Vision


def test_conflicting_skill_highlights_keep_the_selected_slot_unknown():
    d={'state':'battle_running','window':{'process_name':'EpicSeven.exe','client_size':[1212,682]},
       'matches':{'battle_help':{'hit':True},'battle_pause':{'hit':True},
                  'skill_highlight_1':{'hit':True,'box':[923,580,92,100]},
                  'skill_highlight_2':{'hit':True,'box':[1019,580,92,100]}}}
    tree=build_tree(d);v=operation_view({'ui_tree':tree});c=v['items'][0]
    assert v['view']=='battle_skill_selection' and not v['controls']
    assert c['highlighted_slot'] is None and c['highlighted_candidates']==[1,2]
    assert c['selected_slot'] is None and c['auto_available'] is None
    assert tree['nodes']['operation:battle_skill_selection/context']['fields']['highlighted_slot']==fact()
    d['state']='unknown'
    assert operation_view({'ui_tree':build_tree(d)})=={}


@pytest.mark.fixtures
def test_native_skill_border_phases_and_negative_screens(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    samples=[('20261027T013137Z_d2916078',4,1),('20261027T013137Z_d2916078',7,1),
             ('20261027T013137Z_d2916078',9,2),('20261027T013137Z_d2916078',13,2),
             ('20261027T010445Z_262a2dda',16,3),('20261027T010445Z_262a2dda',19,3),
             ('20261027T020703Z_0dc452c4',1,2),('20261027T020703Z_0dc452c4',4,1),
             ('20261027T020703Z_0dc452c4',7,1),
             ('20261027T013137Z_d2916078',1,None),('20261027T012018Z_f4ee88cc',11,None),
             ('20261026T232625Z_eef54186',267,None),('20261027T005115Z_8d1b189a',33,None),
             ('20261027T005115Z_8d1b189a',4,None)]
    if not all((ROOT/'var/runs'/r/f'agent_{n:06}.png').exists() for r,n,_ in samples):
        pytest.skip('Private skill-frame phases unavailable.')
    b=ROOT/'resources/epic-seven';v=Vision(b/'vision.json',b)
    v.spec['states']={k:s for k,s in v.spec['states'].items() if k in ('battle_running','battle_nightmare_keeper','battle_mercenary_lydia')}
    names={n for state in v.spec['states'].values() for s in state.get('variants',[state]) for c in ('all','any','none') for n in s.get(c,[])}
    names.update(f'skill_highlight_{i}' for i in (1,2,3))
    v.spec['templates']={k:s for k,s in v.spec['templates'].items() if k in names};v.spec['ocr']={};out=[]
    class Offline(CustomRecognition):
        def analyze(self,ctx,argv):
            out.append(v.inspect(argv.image,lambda n:ctx.run_recognition(n,argv.image)))
            return self.AnalyzeResult(box=[0,0,1,1],detail=out[-1])
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('SkillHighlightFixture',Offline())
    assert resource.post_bundle(b).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    cases=[]
    for run,n,want in samples:
        p=ROOT/'var/runs'/run/f'agent_{n:06}.png';f=np.asarray(Image.open(p).convert('RGB'))[:,:,::-1].copy()
        cases.append((str(p),f,want))
        if want is not None:cases.append((str(p)+'/dimmed',(f*.55).astype(np.uint8),None))
    for name,f,want in cases:
        before=len(out)
        assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='SkillHighlightFixture'),f).wait().succeeded
        assert len(out)==before+1
        a=out[-1];tree=build_tree({**a,'window':{'process_name':'EpicSeven.exe','client_size':[1212,682]}},v.spec)
        data=operation_view({'ui_tree':tree})
        if want is None:assert data=={},(name,a)
        else:
            assert data['view']=='battle_skill_selection'
            c=data['items'][0]
            assert c['highlighted_slot']==want and c['highlighted_candidates']==[want]
            for field in ('selected_slot','auto_enabled','auto_available','turn_accepts_input','action_completed','skill_id','hero_instance_id'):
                assert c[field] is None
            assert not data['controls']
        assert auto_state({'ui_tree':tree}) is None
        for slot in (1,2,3):assert target_box(tree,f'skill_highlight_{slot}') is None
    (tmp_path/'skill-highlight-replay.json').write_text(json.dumps([
        {'case':c[0],'expected_highlight':c[2],'observed':a} for c,a in zip(cases,out)],indent=2),encoding='utf-8')
