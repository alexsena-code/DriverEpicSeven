"""Earned stars require the current CLEAR graphic and checks, never preparation labels."""
from copy import deepcopy
import json
import numpy as np
from PIL import Image
import pytest
from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree, operation_view, target_box, fact
from driver_epic_seven.vision import Vision


@pytest.mark.fixtures
def test_native_clear_heading_survives_result_animation_and_missing_anchors_are_rejected(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    run=ROOT/'var/runs/20261029T164550Z_b18bd1fc'
    sources=[run/name for name in ('012_Path.Campaign.mel010.Clear.png','agent_000006.png','agent_000007.png')]
    sources.append(ROOT/'tests/fixtures/local/26_stage_clear.png')
    current=ROOT/'var/runs/20261030T033722Z_e29bdbc1/observation.png'
    if current.exists():sources.append(current)
    if not all(p.exists() for p in sources):pytest.skip('Private animated CLEAR calibration frames unavailable.')
    v=Vision(ROOT/'resources/epic-seven/vision.json',ROOT/'resources/epic-seven')
    v.spec['states']={'stage_clear':v.spec['states']['stage_clear']}
    needed=set(v.spec['states']['stage_clear']['all'])|{'clear_three_stars','clear_objective_check_1','clear_objective_check_2','clear_objective_check_3'}
    v.spec['templates']={k:s for k,s in v.spec['templates'].items() if k in needed}
    v.spec['ocr']={'clear_heading':v.spec['ocr']['clear_heading']};found=[]
    class Replay(CustomRecognition):
        def analyze(self,context,argv):
            found.append(v.inspect(argv.image,lambda n:context.run_recognition(n,argv.image)))
            return self.AnalyzeResult(box=[0,0,1,1],detail=found[-1])
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('ClearAnimation',Replay())
    assert resource.post_bundle(ROOT/'resources/epic-seven').wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    for index,path in enumerate(sources):
        frame=np.asarray(Image.open(path).convert('RGB'))[:,:,::-1].copy()
        cases=[('positive',frame,True),('dimmed',(frame*.5).astype(np.uint8),False)]
        for label,box in [('missing_heading',(450,390,760,455)),('missing_continue',(1140,605,1208,675))]:
            image=frame.copy();x,y,x2,y2=box;image[y:y2,x:x2]=0;cases.append((label,image,False))
        for label,image,positive in cases:
            assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='ClearAnimation'),image).wait().succeeded
            a=found[-1]
            assert (a['state']=='stage_clear') is positive,(path.name,label,a['matches'])
            if positive and index<3:
                a.update(window={'process_name':'EpicSeven.exe','client_size':[1212,682]},text=[])
                view=operation_view({'ui_tree':build_tree(a,v.spec)})
                assert view['items'][0]['earned_stars']==3


def sample_observation():
    matches={name:{'hit':True} for name in ('clear_initial','clear_continue','clear_heading')}
    matches['clear_three_stars']={'hit':True,'box':[490,245,230,135]}
    text=[]
    for slot,x in enumerate((237,554,872),1):
        matches[f'clear_objective_check_{slot}']={'hit':True,'box':[209+(slot-1)*317,532,27,21]}
        text.append({'text':'Stage Mission','score':.99,'box':[x,535,121,21]})
        label=('Initial Clear','Story Clear','Have 1 or more Heroes')[slot-1]
        text.append({'text':label,'score':.99,'box':[x,557,184,22]})
        if slot==3:text.append({'text':'survive','score':.99,'box':[x,580,60,18]})
    return {'state':'stage_clear','window':{'process_name':'EpicSeven.exe','client_size':[1212,682]},
            'matches':matches,'text':text}


def result(data):
    tree=build_tree(data);view=operation_view({'ui_tree':tree})
    return tree,view,next((i for i in view.get('items',[]) if i['semantic_id']=='context'),None)


def test_three_stars_and_objectives_have_distinct_current_evidence():
    data=sample_observation();original=deepcopy(data)
    tree,view,context=result(data)
    assert view['view']=='campaign_result' and view['controls']==[]
    assert context['earned_stars']==3 and context['objectives_complete'] is True
    assert context['stage_id'] is None and context['reward_claimed'] is None and context['next_stage_id'] is None
    objectives=[i for i in view['items'] if i['semantic_id']=='stage_objective']
    assert [i['completed'] for i in objectives]==[True,True,True]
    assert objectives[2]['text']=='Have 1 or more Heroes survive'
    sources=tree['nodes']['operation:campaign_result/objective:3']['fields']['completed']['sources']
    assert any(s['pointer']=='/matches/clear_objective_check_3' for s in sources)
    assert sum(s['kind']=='ocr' for s in sources)==3  # Header and two current description lines.
    stars=tree['nodes']['operation:campaign_result/context']['fields']['earned_stars']['sources']
    assert sum(s['pointer'].startswith('/matches/clear_objective_check_') for s in stars)==3
    assert any(s['pointer']=='/matches/clear_three_stars' for s in stars)
    assert data==original
    # Observation with no full-screen OCR still proves stars, but cannot name completed objectives.
    data['text']=[]
    _,view,context=result(data)
    assert context['earned_stars']==3 and context['objectives_complete'] is None
    assert all(i['completed'] is None for i in view['items'] if i['semantic_id']=='stage_objective')


@pytest.mark.parametrize('missing',['clear_three_stars','clear_objective_check_1','clear_objective_check_2','clear_objective_check_3'])
def test_missing_result_marker_is_unknown_not_a_lower_star_count(missing):
    data=sample_observation();data['matches'][missing]['hit']=False
    tree,view,context=result(data)
    assert context['earned_stars'] is None
    assert tree['nodes']['operation:campaign_result/context']['fields']['earned_stars']==fact()
    if missing.startswith('clear_objective_check'):
        slot=int(missing[-1])
        item=next(i for i in view['items'] if i.get('slot')==slot)
        assert item['completed'] is None and item['check_visible'] is None and item['status'] is None


@pytest.mark.parametrize('mutation',['duplicate','low_score','partial','outside','wrong_header'])
def test_objective_completion_rejects_ambiguous_or_incomplete_text(mutation):
    data=sample_observation()
    row=next(r for r in data['text'] if r['text']=='survive')
    if mutation=='duplicate':data['text'].append(deepcopy(row))
    elif mutation=='low_score':row['score']=.89
    elif mutation=='partial':data['text'].remove(row)
    elif mutation=='outside':row['box']=[600,600,60,18]
    else:next(r for r in data['text'] if r['text']=='Stage Mission' and r['box'][0]==872)['text']='Ready'
    _,view,context=result(data)
    assert context['earned_stars']==3 and context['objectives_complete'] is None
    assert next(i for i in view['items'] if i.get('slot')==3)['completed'] is None


def test_result_context_is_scoped_and_marker_must_be_in_calibrated_slot():
    for change in ('unknown','preparation','steam','clear_heading'):
        data=sample_observation()
        if change=='unknown':data['state']='unknown'
        elif change=='preparation':data['state']='prequel_preparation'
        elif change=='steam':data['window']['process_name']='Other.exe'
        else:data['matches']['clear_heading']['hit']=False
        assert result(data)[1]=={}
    data=sample_observation();data['matches']['clear_objective_check_3']['box']=[209,532,27,21]
    assert result(data)[2]['earned_stars'] is None


@pytest.mark.fixtures
def test_native_result_markers_on_two_clear_results_and_preparation_negatives(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    from driver_epic_seven.stages import StageInspector
    samples=[('20261027T012018Z_f4ee88cc',11,True),('20261027T021700Z_167013b0',8,True),
             ('20261027T024311Z_f1c0e142',34,True),
             ('20261027T012018Z_f4ee88cc',35,False),('20261027T005115Z_8d1b189a',33,False),
             ('20261027T012018Z_f4ee88cc',14,False)]
    if not all((ROOT/'var/runs'/r/f'agent_{n:06}.png').exists() for r,n,_ in samples):
        pytest.skip('Private current STOVE result fixtures unavailable.')
    bundle=ROOT/'resources/epic-seven';vision=Vision(bundle/'vision.json',bundle);analyses=[]
    names={'clear_initial','clear_continue','clear_heading','clear_three_stars'}|{f'clear_objective_check_{i}' for i in (1,2,3)}
    vision.spec['states']={'stage_clear':vision.spec['states']['stage_clear']}
    vision.spec['templates']={k:s for k,s in vision.spec['templates'].items() if k in names}
    class Offline(CustomRecognition):
        def analyze(self,ctx,argv):
            current=vision.inspect(argv.image,lambda n:ctx.run_recognition(n,argv.image))
            # OCR is rerun on this saved image only, never borrowed from another observation.
            current['text']=StageInspector._ocr(lambda k,p:ctx.run_recognition_direct(k,p,argv.image),[180,525,900,80])
            analyses.append(current)
            return self.AnalyzeResult(box=[0,0,1,1],detail=current)
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('ClearResultFixture',Offline())
    assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    cases=[]
    for run,n,positive in samples:
        frame=np.asarray(Image.open(ROOT/'var/runs'/run/f'agent_{n:06}.png').convert('RGB'))[:,:,::-1].copy()
        cases.append((run+'/'+str(n),frame,positive))
        if positive:
            cases.append((run+'/dimmed',(frame*.45).astype(np.uint8),False))
        if n==11:
            for slot,(x1,x2) in enumerate(((490,568),(570,643),(645,720)),1):
                changed=frame.copy();changed[245:380,x1:x2]=0
                cases.append((f'missing_star_{slot}',changed,False))
            for slot,x in enumerate((209,526,843),1):
                changed=frame.copy();changed[532:553,x:x+28]=0
                cases.append((f'missing_check_{slot}',changed,False))
    for name,frame,positive in cases:
        before=len(analyses)
        assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='ClearResultFixture'),frame).wait().succeeded
        assert len(analyses)==before+1
        data={**analyses[-1],'window':{'process_name':'EpicSeven.exe','client_size':[1212,682]}}
        tree,view,context=result(data)
        if positive:
            assert context['earned_stars']==3 and context['objectives_complete'] is True,(name,data)
            assert [i['completed'] for i in view['items'] if i['semantic_id']=='stage_objective']==[True]*3
        else:
            assert context is None or context['earned_stars'] is None,(name,data)
        for marker in ('clear_three_stars','clear_objective_check_1','clear_objective_check_2','clear_objective_check_3'):
            assert target_box(tree,marker) is None
    (tmp_path/'clear-result-replay.json').write_text(json.dumps([
        {'case':c[0],'expected_three_stars':c[2],'observed':a} for c,a in zip(cases,analyses)],indent=2),encoding='utf-8')
