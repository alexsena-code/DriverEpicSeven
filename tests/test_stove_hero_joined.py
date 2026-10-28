"""The current availability notice is not a complete roster or an owned instance."""
from copy import deepcopy
import json
import numpy as np
from PIL import Image
import pytest
from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree,operation_view,target_box
from driver_epic_seven.vision import Vision

RUN=ROOT/'var/runs/20261027T024311Z_f1c0e142'
NAMES=('hero_joined_title','hero_joined_description','hero_joined_ok')


def saved_notice():
    if not (RUN/'agent_000048.json').exists():pytest.skip('Private Victorika notice unavailable.')
    d=json.loads((RUN/'agent_000048.json').read_text(encoding='utf-8'))['result']
    d['state']='hero_joined_notice'
    d['matches'].update({name:{'hit':True} for name in NAMES})
    return d


@pytest.mark.fixtures
def test_current_victorika_notice_has_scoped_availability_and_unknown_roster():
    d=saved_notice();original=deepcopy(d);tree=build_tree(d);v=operation_view({'ui_tree':tree})
    assert v['view']=='hero_joined_notice'
    context=v['items'][0]
    assert context['hero_name']=='Inexperienced Victorika' and context['hero_catalog_id']=='c0166'
    assert context['availability_announced'] is True and context['team_assignment_announced'] is True
    for key in ('owned_instance_id','owned_roster','selected','team_slot','acknowledgement_completed'):
        assert context[key] is None
    assert len(v['controls'])==1
    assert v['controls'][0]['text']=='OK' and v['controls'][0]['enabled'] is None
    assert v['controls'][0]['consuming'] is False
    control=tree['nodes']['operation:hero_joined_notice/acknowledge']
    assert control['layout_reference']['path']=='/Layer/window_frame/btn_ok'
    assert d==original
    # Each complete text line and native marker belongs to this same notice.
    for mutation in ('missing_description','duplicate_title','npc_name','low_score','wrong_state','missing_match','steam'):
        d=deepcopy(original)
        if mutation=='missing_description':d['text']=[r for r in d['text'] if not r['text'].startswith('You can now assign')]
        elif mutation=='duplicate_title':d['text'].append(deepcopy(next(r for r in d['text'] if r['text'].endswith('has Joined'))))
        elif mutation=='npc_name':next(r for r in d['text'] if r['text'].endswith('has Joined'))['text']='Guard Captain Krau'
        elif mutation=='low_score':next(r for r in d['text'] if r['text'].startswith('You can now assign'))['score']=.89
        elif mutation=='wrong_state':d['state']='battle_running'
        elif mutation=='missing_match':d['matches']['hero_joined_description']['hit']=False
        else:d['window']['process_name']='Other.exe'
        view=operation_view({'ui_tree':build_tree(d)})
        assert view.get('view')!='hero_joined_notice'


@pytest.mark.fixtures
def test_native_notice_pair_and_negative_result_story_and_map(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    paths=[(RUN/f'agent_{n:06}.png',n in (47,48)) for n in (47,48,34,51,53)]
    paths += [(ROOT/'var/runs/20261027T012018Z_f4ee88cc/agent_000040.png',False),
              (ROOT/'var/runs/20261027T005115Z_8d1b189a/agent_000033.png',False)]
    if not all(p.exists() for p,_ in paths):pytest.skip('Private notice positive/negative fixtures unavailable.')
    bundle=ROOT/'resources/epic-seven';v=Vision(bundle/'vision.json',bundle);out=[]
    class Offline(CustomRecognition):
        def analyze(self,ctx,argv):
            out.append(v.inspect(argv.image,lambda n:ctx.run_recognition(n,argv.image)))
            return self.AnalyzeResult(box=[0,0,1,1],detail=out[-1])
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('HeroJoinedFixture',Offline())
    assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    cases=[]
    for p,want in paths:
        frame=np.asarray(Image.open(p).convert('RGB'))[:,:,::-1].copy();cases.append((str(p),frame,want))
        if want:
            cases.append((str(p)+'/dimmed',(frame*.45).astype(np.uint8),False))
            altered=frame.copy();altered[355:430,345:870]=0;cases.append((str(p)+'/without_description',altered,False))
    for name,frame,want in cases:
        before=len(out)
        assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='HeroJoinedFixture'),frame).wait().succeeded
        assert len(out)==before+1
        a=out[-1]
        assert (a['state']=='hero_joined_notice') is want,(name,a)
        tree=build_tree({**a,'window':{'process_name':'EpicSeven.exe','client_size':[1212,682]}},v.spec)
        for marker in NAMES:assert target_box(tree,marker) is None
        if name.endswith('agent_000048.png'):
            d=saved_notice();d.update(a)
            assert operation_view({'ui_tree':build_tree(d)})['items'][0]['availability_announced'] is True
    (tmp_path/'hero-joined-replay.json').write_text(json.dumps([
        {'case':c[0],'expected_notice':c[2],'observed':a} for c,a in zip(cases,out)],indent=2),encoding='utf-8')
