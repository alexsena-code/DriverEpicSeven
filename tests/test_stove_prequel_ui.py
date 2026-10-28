"""Prequel map labels are current visual evidence, never a stage executor."""
from copy import deepcopy
import json

import numpy as np
from PIL import Image
import pytest

from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree, operation_view, target_box, fact
from driver_epic_seven.vision import Vision


def saved_map():
    path=ROOT/'var/runs/20261027T005115Z_8d1b189a/agent_000015.json'
    if not path.exists():
        pytest.skip('Private STOVE prequel map is not installed.')
    data=json.loads(path.read_text(encoding='utf-8'))['result']
    data['state']='prequel_story_map'
    data['matches']['prequel_episode_header']={'hit':True,'box':[60,17,200,32],'score':1.0}
    data['matches']['prequel_view_story']={'hit':True,'box':[1000,607,105,38],'score':1.0}
    return data


def view(data):
    return operation_view({'ui_tree':build_tree(data)})


@pytest.mark.fixtures
@pytest.mark.parametrize('process',['EpicSeven.exe','EpicSeven_Steam.exe'])
def test_prequel_ocr_maps_visible_lines_but_not_selection_unlock_or_cost(process):
    data=saved_map();data['window']['process_name']=process;before=deepcopy(data)
    tree=build_tree(data);v=operation_view({'ui_tree':tree})
    assert v['view']=='prequel_story_map' and not v['controls']
    context=v['items'][0]
    assert context['episode_label']=='6th World Episode'
    assert context['chapter_number']==1 and context['chapter_label']=="Chapter 1.Acolyte's Appearance"
    assert context['selected_description']=="Victorika tries to get her family back, but things don't go as planned."
    assert context['chapter_star_counter_label']=='0/9'
    assert context['selected_stage_id'] is None and context['selected_row_ordinal'] is None
    assert context['current_entry_cost'] is None and context['earned_stars'] is None
    rows=[i for i in v['items'] if i['semantic_id']=='stage_row']
    assert [r['ordinal'] for r in rows]==[1,2,3,4]
    assert rows[0]['title']=='The Pathetic Lady and the Worldly Knight'
    assert rows[1]['title']=='The Advance of the Archdemon Corps'
    for row in rows:
        assert all(row[key] is None for key in ('selected','locked','completed','stage_id','earned_stars'))
    assert tree['nodes']['operation:prequel_story_map/row:1']['fields']['selected']==fact()
    assert data==before


@pytest.mark.fixtures
def test_prequel_rejects_unverified_context_missing_anchors_and_overlay():
    base=saved_map();cases=[]
    d=deepcopy(base);d['window']['process_name']='Other.exe';cases.append(d)
    d=deepcopy(base);d['window']['client_size']=[1280,720];cases.append(d)
    d=deepcopy(base);d['state']='unknown';cases.append(d)
    d=deepcopy(base);d['matches']['prequel_view_story']['hit']=False;cases.append(d)
    d=deepcopy(base);d['text']=[r for r in d['text'] if r['text']!='Story'];cases.append(d)
    d=deepcopy(base);d['text']=[r for r in d['text'] if 'Chapter' not in r['text']];cases.append(d)
    d=deepcopy(base);d['text'].extend([{'text':'Cancel','box':[400,420,80,25],'score':.99},
                                   {'text':'Confirm','box':[700,420,90,25],'score':.99}]);cases.append(d)
    for data in cases:
        assert view(data)=={}
    duplicate=deepcopy(base)
    duplicate['text'].append({'text':'2. Another candidate','box':[90,345,240,22],'score':.99})
    assert not any(i.get('ordinal')==2 for i in view(duplicate)['items'])


@pytest.mark.fixtures
def test_native_prequel_pair_is_read_only_and_rejects_other_screens(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    data=saved_map()
    run=ROOT/'var/runs/20261027T005115Z_8d1b189a'
    bundle=ROOT/'resources/epic-seven';vision=Vision(bundle/'vision.json',bundle)
    names={n for clause in ('all','any','none')
           for n in vision.spec['states']['prequel_story_map'].get(clause,[])}
    vision.spec['templates']={k:v for k,v in vision.spec['templates'].items() if k in names}
    vision.spec['states']={'prequel_story_map':vision.spec['states']['prequel_story_map']}
    vision.spec['ocr']={};results=[]
    class Offline(CustomRecognition):
        def analyze(self,context,argv):
            results.append(vision.inspect(argv.image,lambda n:context.run_recognition(n,argv.image)))
            return self.AnalyzeResult(box=[0,0,1,1],detail=results[-1])
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('StovePrequelFixture',Offline())
    assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    cases=[]
    for n in (15,19,22,4,7):
        path=run/f'agent_{n:06}.png'
        if path.exists():cases.append((path.name,np.asarray(Image.open(path).convert('RGB'))[:,:,::-1].copy(),
                                      'prequel_story_map' if n==15 else 'unknown'))
    frame=cases[0][1]
    cases.append(('dimmed',(frame*.55).astype(np.uint8),'unknown'))
    for x1,y1,x2,y2 in ((45,8,280,63),(980,590,1125,665)):
        covered=frame.copy();covered[y1:y2,x1:x2]=0
        cases.append((f'covered-{x1}',covered,'unknown'))
    for name,pixels,expected in cases:
        assert tasker.post_recognition('Custom',JCustomRecognition(
            custom_recognition='StovePrequelFixture'),pixels).wait().succeeded
        assert results[-1]['state']==expected,(name,results[-1])
        tree=build_tree({**data,**results[-1]},vision.spec)
        assert target_box(tree,'prequel_view_story') is None
    (tmp_path/'stove-prequel-replay.json').write_text(json.dumps([
        {'case':c[0],'expected':c[2],'observed':r} for c,r in zip(cases,results)],indent=2),encoding='utf-8')
