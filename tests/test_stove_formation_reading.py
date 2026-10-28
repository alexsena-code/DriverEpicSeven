"""Formation reads current list/markers/member pixels; CP cannot prove assignment."""
from copy import deepcopy
import json
import numpy as np
from PIL import Image
import pytest
from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree,operation_view,target_box
from driver_epic_seven.vision import Vision

RUN=ROOT/'var/runs/20261027T031057Z_dcdc3935'


def read(n):
    p=RUN/f'agent_{n:06}.json'
    if not p.exists():pytest.skip('Private STOVE formation fixture unavailable.')
    return json.loads(p.read_text(encoding='utf-8'))['result']


def view(d):return operation_view({'ui_tree':build_tree(d)})


@pytest.mark.fixtures
def test_candidate_and_cp_do_not_prove_member_assignment():
    d=read(16);d['state']='prequel_preparation'
    d['matches'].update({k:{'hit':True} for k in ('prequel_ready_header','prequel_story_team')})
    original=deepcopy(d);v=view(d)
    assert v['view']=='prequel_formation'
    c=v['items'][0]
    assert c['team_cp']==16222 and c['team_label']=='The Visitors of Dun Blyraia'
    assert c['assignment_completed'] is None and c['selected_candidate_id'] is None and c['selected_slot'] is None
    assert c['owned_roster'] is None and c['stage_id'] is None
    candidate=next(i for i in v['items'] if i['semantic_id']=='hero_candidate')
    assert candidate['hero_name']=='Inexperienced Victorika' and candidate['level']==10
    assert candidate['hero_instance_id'] is None and candidate['assigned'] is None and candidate['selected'] is None
    assert not any(i['semantic_id']=='formation_member_appearance' for i in v['items'])
    assert [i['semantic_id'] for i in v['controls']]==['candidate_add','search']
    assert all(i['enabled'] is None for i in v['controls'])
    assert d==original
    d['matches']['formation_victorika_right']={'hit':True,'box':[498,234,77,96]}
    v=view(d);member=next(i for i in v['items'] if i['semantic_id']=='formation_member_appearance')
    assert member['appearance_label']=='Inexperienced Victorika' and member['visual_position']=='right'
    assert member['hero_instance_id'] is None and member['slot_id'] is None and member['selected'] is None
    d['matches']['formation_victorika_right']['box']=[0,0,77,96]
    assert not any(i['semantic_id']=='formation_member_appearance' for i in view(d)['items'])
    d['text'].append(deepcopy(next(r for r in d['text'] if r['text']=='Inexperienced Victorika')))
    assert view(d)=={}


@pytest.mark.fixtures
def test_native_formation_unit_and_negatives(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    cases=[(RUN/f'agent_{n:06}.png','prequel_preparation') for n in (7,10,13,16)]
    cases += [(ROOT/'var/runs/20261027T024311Z_f1c0e142'/f'agent_{n:06}.png',None) for n in (10,34,48,63,75)]
    if not all(p.exists() for p,_ in cases):pytest.skip('Private formation positive/negative frames unavailable.')
    bundle=ROOT/'resources/epic-seven';vision=Vision(bundle/'vision.json',bundle);out=[]
    class Offline(CustomRecognition):
        def analyze(self,ctx,argv):
            out.append(vision.inspect(argv.image,lambda n:ctx.run_recognition(n,argv.image)))
            return self.AnalyzeResult(box=[0,0,1,1],detail=out[-1])
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('FormationReadingFixture',Offline())
    assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    diagnostics=[]
    for p,state in cases:
        frame=np.asarray(Image.open(p).convert('RGB'))[:,:,::-1].copy();before=len(out)
        assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='FormationReadingFixture'),frame).wait().succeeded
        assert len(out)==before+1
        a=out[-1];saved=json.loads(p.with_suffix('.json').read_text(encoding='utf-8'))['result']
        d={**saved,**a};tree=build_tree(d,vision.spec);v=operation_view({'ui_tree':tree})
        if state is None:
            assert v.get('view')!='prequel_formation',(str(p),a)
            assert not any(a['matches'][name]['hit'] for name in ('formation_destination_right','formation_destination_lower','formation_victorika_right'))
        else:
            assert a['state']==state,(str(p),a)
            n=int(p.stem.split('_')[-1])
            if n==7:
                assert v['view']=='prequel_preparation' and v['items'][0]['team_cp']==12486
                assert v['items'][0]['earned_stars'] is None
            else:
                assert v['view']=='prequel_formation'
                markers=[i for i in v['items'] if i['semantic_id']=='formation_destination_marker']
                assert [i['visual_position'] for i in markers]==(['right','lower'] if n==13 else [])
                assert all(i['slot_id'] is None and i['selected'] is None for i in markers)
                members=[i for i in v['items'] if i['semantic_id']=='formation_member_appearance']
                assert bool(members)==(n==16)
                assert len([i for i in v['items'] if i['semantic_id']=='story_member_marker'])==2
                assert v['items'][0]['assignment_completed'] is None
        for name in ('formation_destination_right','formation_destination_lower','formation_victorika_right'):
            assert target_box(tree,name) is None
        diagnostics.append({'source':str(p),'analysis':a,'operation_view':v})
    (tmp_path/'formation-reading-replay.json').write_text(json.dumps(diagnostics,indent=2),encoding='utf-8')
