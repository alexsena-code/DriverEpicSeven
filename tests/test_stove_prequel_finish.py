"""Read prequel result/preparation with no generic battle-start target."""
from copy import deepcopy
import json
import time
import numpy as np
from PIL import Image
import pytest
from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree, operation_view, target_box, fact
from driver_epic_seven.vision import Vision


def saved_preparation():
    p=ROOT/'var/runs/20261027T005115Z_8d1b189a/agent_000033.json'
    if not p.exists():pytest.skip('Private STOVE preparation unavailable.')
    d=json.loads(p.read_text(encoding='utf-8'))['result'];d['state']='prequel_preparation'
    d['matches']['prequel_ready_header']={'hit':True,'box':[58,15,77,34],'score':1}
    d['matches']['prequel_story_team']={'hit':True,'box':[176,80,89,26],'score':1}
    return d


@pytest.mark.fixtures
def test_preparation_start_read_control_requires_current_cost_and_identity_labels():
    from driver_epic_seven.prequel import target
    d=saved_preparation();v=operation_view({'ui_tree':build_tree(d)})
    assert v['view']=='prequel_preparation'
    c=v['items'][0]
    assert c['location']=='Burning Village'
    assert c['story_title']=='The Advance of the Archdemon Corps'
    assert c['cost']=={'currency':'energy','cost':8,'available':83}
    assert c['team_cp']==9381 and c['team_label']=="The Lady's Escort Knight"
    assert c['stage_id'] is None and c['hero_instances'] is None and c['earned_stars'] is None
    assert [i['text'] for i in v['items'][1:]]==['Initial Clear','Story Clear','Have 1 or more Heroes survive']
    assert v['controls'][0]['semantic_id']=='start_quest' and v['controls'][0]['consuming'] is True
    assert v['controls'][0]['enabled'] is None
    ticket={'wdp002':{'epoch_seconds':time.time(),'window':d['window']}}
    params={'kind':'prequel_start','stage_id':'wdp002','max_energy':8}
    assert target(v,params,d,ticket)==v['controls'][0]['box']
    for text in ('8/83','Burning Village','Start Quest'):
        partial=deepcopy(d);partial['text']=[r for r in partial['text'] if r['text']!=text]
        view=operation_view({'ui_tree':build_tree(partial)})
        if text=='Burning Village':
            # Location/title distinguish preparation from formation's shared
            # Ready/Team shell; without them the composition is unproven.
            assert view=={} and target(view,params,partial,ticket) is None
            continue
        assert view['view']=='prequel_preparation' and view['items'][0]['team_cp']==9381
        assert target(view,params,partial,ticket) is None
        if text=='8/83':assert view['items'][0]['cost'] is None
        if text=='Start Quest':assert not view['controls']
    ambiguous=deepcopy(d);ambiguous['text'].append({'text':'9/83','score':.99,'box':[934,619,45,22]})
    view=operation_view({'ui_tree':build_tree(ambiguous)})
    assert view['items'][0]['cost'] is None and target(view,params,ambiguous,ticket) is None
    ambiguous=deepcopy(d);ambiguous['text'].append({'text':'Another Story Title','score':.99,'box':[878,111,147,18]})
    view=operation_view({'ui_tree':build_tree(ambiguous)})
    assert view=={} and target(view,params,ambiguous,ticket) is None


@pytest.mark.fixtures
def test_native_story_reward_ready_and_preparation_are_distinct(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    run=ROOT/'var/runs/20261027T005115Z_8d1b189a'
    expected={25:'story_reward',27:'prequel_ready_map',33:'prequel_preparation',15:'unknown',19:'unknown',22:'unknown',39:'unknown',42:'unknown'}
    if not all((run/f'agent_{n:06}.png').exists() for n in expected):pytest.skip('Private STOVE frames unavailable.')
    bundle=ROOT/'resources/epic-seven';v=Vision(bundle/'vision.json',bundle)
    v.spec['states']={k:s for k,s in v.spec['states'].items() if k in ('story_reward','prequel_ready_map','prequel_preparation')}
    names={n for state in v.spec['states'].values() for s in state.get('variants',[state]) for c in ('all','any','none') for n in s.get(c,[])}
    v.spec['templates']={k:s for k,s in v.spec['templates'].items() if k in names};v.spec['ocr']={};results=[]
    class Offline(CustomRecognition):
        def analyze(self,context,argv):
            results.append(v.inspect(argv.image,lambda n:context.run_recognition(n,argv.image)))
            return self.AnalyzeResult(box=[0,0,1,1],detail=results[-1])
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('PrequelFinishFixture',Offline())
    assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    cases=[]
    for n,state in expected.items():
        f=np.asarray(Image.open(run/f'agent_{n:06}.png').convert('RGB'))[:,:,::-1].copy()
        cases.append((str(n),n,f,state))
        if state!='unknown':cases.append((f'{n}/dimmed',n,(f*.55).astype(np.uint8),'unknown'))
    for name,n,f,state in cases:
        assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='PrequelFinishFixture'),f).wait().succeeded
        a=results[-1]
        if a['state']!=state:pytest.fail(name+'\n'+json.dumps(a,indent=2))
        saved=json.loads((run/f'agent_{n:06}.json').read_text(encoding='utf-8'))['result']
        tree=build_tree({**saved,**a},v.spec)
        assert target_box(tree,'map_ready_label') is None
        assert target_box(tree,'prequel_ready_header') is None
        if state=='story_reward':
            assert target_box(tree,'story_reward_close')==[552,444,107,28]
            assert tree['nodes']['visual:story_reward_close']['fields']['enabled']==fact()
        else:assert target_box(tree,'story_reward_close') is None
        if state=='prequel_ready_map':
            view=operation_view({'ui_tree':tree})
            assert view['view']=='prequel_ready_map' and not view['controls']
            assert [x['ordinal'] for x in view['items'] if x['semantic_id']=='stage_row']==[2,3,4,5]
    (tmp_path/'prequel-finish-replay.json').write_text(json.dumps([
        {'case':c[0],'expected':c[3],'observed':a} for c,a in zip(cases,results)],indent=2),encoding='utf-8')
