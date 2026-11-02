from copy import deepcopy
import json
import time
from types import SimpleNamespace
import pytest
from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree,operation_view,auto_state
from driver_epic_seven.operational_theater import ANCHORS,fast_analysis
from driver_epic_seven.theater import target,compile_theater,prepare
from driver_epic_seven.execution import wrap_graph

WINDOW={'process_name':'EpicSeven.exe','client_size':[1212,682],'pid':1,'hwnd':2,
        'window_title':'Epic Seven','window_class':'GLFW30'}
RESOURCE=ROOT/'resources/epic-seven'


def observation(rows=(),matches=None):
    d={'state':'unknown','window':deepcopy(WINDOW),'epoch_seconds':time.time(),'matches':matches or {},
       'text':[{'text':text,'box':box,'score':.99} for text,box in rows]}
    d['ui_tree']=build_tree(d)
    return d


def main_screen(act=6,balance=32):
    return observation([('Moonlight Theater',[61,20,195,25]),('Cast Board',[123,621,99,22]),
        ('Watch',[760,616,60,27]),(f'1/{balance}',[660,619,41,21]),
        (f'Act {act}. A generic title',[41,460,280,20]),('A generic series',[41,409,230,20]),
        (f'Act {act-1}',[900,254,48,23]),('Rewards Available',[901,282,131,16])])


def popup(balance=32):
    return observation([('Use Theater Ticket',[480,128,250,32]),('Entry Ticket',[610,289,110,25]),
        ('Theater Ticket',[610,316,150,25]),(f'Owned: {balance}',[513,369,90,24]),
        ('Confirm',[666,488,75,23]),('Cancel',[474,488,63,23])])


def params(kind,act=6):return {'kind':kind,'task_id':'theater:test:1','act':act,'series':'A generic series'}


def test_reader_generic_main_and_specific_ticket_confirmation_with_provenance():
    d=main_screen();current=operation_view(d)
    assert current['view']=='theater_main'
    info=current['items'][0]
    assert info['act']==6 and info['series']=='A generic series'
    assert info['ticket_cost']=={'cost':1,'available':32} and info['completed_acts']==[5]
    assert info['season'] is None and info['stage_id'] is None
    p=popup();assert operation_view(p)['view']=='theater_ticket'
    assert operation_view(p)['items'][0]['owned']==32
    assert all(n['fields']['enabled']['value'] is None for n in p['ui_tree']['nodes'].values())


@pytest.mark.parametrize('missing',['Moonlight Theater','Cast Board','Watch','1/32','Act 6. A generic title','A generic series'])
def test_main_requires_complete_composition(missing):
    d=main_screen();d['text']=[r for r in d['text'] if r['text']!=missing];d['ui_tree']=build_tree(d)
    assert operation_view(d).get('view')!='theater_main'


def test_watch_confirmation_and_completion_are_bound_to_current_context():
    prepared={};before=main_screen();p=params('theater_watch')
    assert target(before,p,prepared)==[760,616,60,27]
    assert target(before,{**p,'act':7},prepared) is None
    prepare(prepared,p,before)
    assert target(popup(),params('theater_confirm'),prepared)==[666,488,75,23]
    assert target(popup(31),params('theater_confirm'),prepared) is None
    prepare(prepared,params('theater_confirm'),popup())
    assert target(popup(),params('theater_confirm'),prepared) is None
    after=main_screen(7,31)
    assert target(after,params('theater_done'),prepared)==[0,0,1,1]
    assert target(main_screen(7,32),params('theater_done'),prepared) is None
    assert target(main_screen(6,31),params('theater_done'),prepared) is None


def test_story_requires_all_current_anchors_and_keeps_act_unknown():
    matches={k:{'hit':True,'box':[1,2,3,4]} for k in ANCHORS['normal']}
    d=observation(matches=matches)
    assert operation_view(d)['view']=='theater_story'
    assert operation_view(d)['items'][0]['stage_id'] is None
    for key in matches:
        changed=deepcopy(matches);changed[key]['hit']=False
        assert operation_view(observation(matches=changed)).get('view')!='theater_story'


def test_compiler_has_finite_single_confirm_per_act_and_no_skip_or_reward_claim():
    nodes,entry,success=compile_theater(RESOURCE,acts=2,max_tickets=2,timeout=300,act=6,series='Any',scope='theater:test',taps_per_act=20)
    assert entry=='Theater.Entry' and success=='Theater.Done'
    consumers=[n for n in nodes.values() if n.get('custom_recognition_param',{}).get('path',{}).get('consuming')]
    assert len(consumers)==2 and all(n['max_hit']==1 for n in consumers)
    assert nodes['Theater.1.Tap']['max_hit']==20
    assert nodes['Theater.1.Auto']['max_hit']==1
    assert nodes['Theater.1.Auto']['custom_recognition_param']['auto_state'] is False
    assert nodes['Theater.1.Auto']['next']==['Theater.1.AutoVerified']
    assert nodes['Theater.1.Done']['next']==['Theater.2.Entry']
    assert not any(s in str(nodes) for s in ('story_skip','Receive','next_difficulty','result_confirm'))
    assert wrap_graph(nodes)['Theater.1.Confirm']['custom_action']=='OperationBoundary'


@pytest.mark.parametrize('settings',[{'acts':0},{'acts':21},{'max_tickets':0},{'timeout':1801},{'taps_per_act':0},{'act':None},{'series':''}])
def test_invalid_limits_fail_before_dispatch(settings):
    args=dict(acts=1,max_tickets=1,timeout=300,act=6,series='Any',scope='theater:test')
    args.update(settings)
    with pytest.raises(ValueError):compile_theater(RESOURCE,**args)


def test_fast_story_path_never_changes_other_requests_or_rescues_filtered_negatives():
    class Vision:
        spec={'templates':{k:{} for keys in ANCHORS.values() for k in keys}}
        def match_template(self,k,frame,matcher):return {'hit':False}
    assert fast_analysis(Vision(),None,None,{'observe':True}) is None
    assert fast_analysis(Vision(),None,None,{'path':params('theater_tap')}) is None


@pytest.mark.fixtures
def test_saved_main_ticket_and_next_act_readonly():
    cases=[('20261102T141127Z_29c95ffa/agent_000001.json','theater_main'),
           ('20261102T141127Z_29c95ffa/agent_000004.json','theater_ticket'),
           ('20261102T142310Z_95fe0ddc/path_failure_after.json','theater_main')]
    for name,expected in cases:
        p=ROOT/'var/runs'/name
        if not p.exists():pytest.skip('Private Theater fixtures unavailable')
        d=json.loads(p.read_text(encoding='utf-8'));d=d.get('result',d);d.pop('ui_tree',None)
        assert operation_view({'ui_tree':build_tree(d)})['view']==expected


@pytest.mark.fixtures
def test_native_dialogue_anchors_keep_main_modal_and_combat_negative(tmp_path):
    import numpy as np
    from PIL import Image
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    from driver_epic_seven.vision import Vision
    cases=[('20261102T141127Z_29c95ffa/agent_000006.png',True),
           ('20261102T141127Z_29c95ffa/agent_000009.png',True),
           ('20261102T142013Z_37b36da0/path_failure_after.png',True),
           ('20261102T141127Z_29c95ffa/agent_000001.png',False),
           ('20261102T141127Z_29c95ffa/agent_000004.png',False),
           ('20261102T141841Z_2269f868/path_failure_after.png',False),
           ('20261102T142202Z_759fb9cb/path_failure_after.png',False)]
    cases += [('../theater-routine-20261102/act6-story-variant.png',True)]
    cases += [('../theater-routine-20261102/act6-story-motion.png',True)]
    cases += [('../theater-routine-20261102/act6-story-forest.png',True)]
    if not all((ROOT/'var/runs'/p).exists() for p,_ in cases):pytest.skip('Private Theater captures unavailable')
    vision=Vision(RESOURCE/'vision.json',RESOURCE);out=[]
    class Reader(CustomRecognition):
        def analyze(self,ctx,argv):
            from driver_epic_seven.stages import StageInspector
            def ocr(roi):return StageInspector._ocr(lambda kind,args:ctx.run_recognition_direct(kind,args,argv.image),roi)
            analysis=fast_analysis(vision,argv.image,lambda n:ctx.run_recognition(n,argv.image),{'path':params('theater_tap')},ocr)
            out.append(analysis)
            return self.AnalyzeResult(box=[0,0,1,1],detail={'hit':analysis is not None})
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();reader=Reader();resource.register_custom_recognition('TheaterFixture',reader)
    assert resource.post_bundle(RESOURCE).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    for path,expected in cases:
        frame=np.asarray(Image.open(ROOT/'var/runs'/path).convert('RGB'))[:,:,::-1].copy()
        assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='TheaterFixture'),frame).wait().succeeded
        assert (out[-1] is not None) is expected,path
        if expected:
            d={**out[-1],'window':WINDOW};d['ui_tree']=build_tree(d)
            assert operation_view(d)['view']=='theater_story'
            # A dimmed overlay must not reuse the normal glyph colors.
            assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='TheaterFixture'),(frame*.3).astype(np.uint8)).wait().succeeded
            assert out[-1] is None



def test_continuation_has_no_watch_confirmation_or_consumer_and_preserves_ledger_scope():
    from driver_epic_seven.theater import continuation
    nodes,entry,done=continuation(RESOURCE,'theater:original:7',{'act':12,'series':'Any'},timeout=300,taps_per_act=50)
    assert not any(n.endswith(('.Watch','.Confirm')) for n in nodes)
    paths=[n.get('custom_recognition_param',{}).get('path',{}) for n in nodes.values()]
    assert not any(p.get('consuming') for p in paths)
    assert {p['task_id'] for p in paths if p}=={'theater:original:7'}
    assert nodes['Theater.1.Entry']['next']==['Theater.1.Done','Theater.1.Started']



def test_pending_resume_refuses_changed_window_and_never_builds_a_new_consumer(tmp_path):
    from driver_epic_seven.theater import run
    from driver_epic_seven.attempts import AttemptLedger
    ledger=AttemptLedger(tmp_path/'actions.json',1)
    ledger.reserve('theater:original:1','key',1)
    ledger.record('theater:original:1','key','reserved',identity={'old':'identity'},proof={'operation_context':{
        'window':{**WINDOW,'pid':999},'act':6,'series':'A generic series','available':32}})
    runtime=SimpleNamespace(path_attempts=ledger,observe=lambda *a,**kw:main_screen())
    with pytest.raises(ValueError,match='janela mudou'):
        run(runtime,acts=1,max_tickets=0,timeout=60,finish_current=True)
    assert ledger.read()['stages']['theater:original:1'][0]['status']=='reserved'


@pytest.mark.parametrize('pending',[False,True])
def test_launcher_new_batch_or_continuation_passes_resource_limits_without_live_runtime(tmp_path,monkeypatch,pending):
    import importlib.util,sys,ctypes
    from driver_epic_seven import cli,config
    spec=importlib.util.spec_from_file_location('theater_launcher_under_test',ROOT/'tools/theater_launcher.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    ledger=tmp_path/'ledger.json'
    ledger.write_text(json.dumps({'stages':{'theater:pending:1':[{'status':'sent'}]} if pending else {}}))
    monkeypatch.setattr(config,'load_config',lambda:{'path_ledger':ledger,'runs_dir':tmp_path/'runs'})
    monkeypatch.setattr(ctypes.windll.shell32,'IsUserAnAdmin',lambda:True)
    monkeypatch.setattr(sys,'argv',['theater_launcher.py','--acts','2','--max-tickets','2','--minutes','1'])
    received=[]
    monkeypatch.setattr(cli,'execute',lambda args:received.append(args) or {'completed':True,'completed_acts':1,'evidence_dir':'test'})
    assert module.main()==0
    args=received[0]
    assert args.command=='theater' and args.timeout==60
    assert args.finish_current is pending
    assert args.acts==(1 if pending else 2) and args.max_tickets==(0 if pending else 2)



@pytest.mark.fixtures
def test_generic_recognition_real_stalls_and_overlay_negatives(tmp_path):
    import numpy as np
    from PIL import Image
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    from driver_epic_seven.vision import Vision
    from driver_epic_seven.stages import StageInspector
    cases=[('var/theater-generic-20261102/blocked-dialogue.png','theater_story'),
           ('var/theater-generic-20261102/blocked-intro.png','theater_intro'),
           ('var/theater-routine-20261102/act6-story-forest.png','theater_story'),
           ('var/theater-routine-20261102/act6-story-motion.png','theater_story'),
           ('var/runs/20261102T141127Z_29c95ffa/agent_000001.png',None),
           ('var/runs/20261102T141127Z_29c95ffa/agent_000004.png',None),
           ('var/runs/20261102T165252Z_927f4220/live.png',None),
           ('var/runs/20261102T141841Z_2269f868/path_failure_after.png',None),
           ('var/runs/20261102T142202Z_759fb9cb/path_failure_after.png',None)]
    cases += [('var/theater-generic-20261102/outside-theater.png',None)]
    if not all((ROOT/path).exists() for path,_ in cases):pytest.skip('Private generic Theater fixtures unavailable')
    vision=Vision(RESOURCE/'vision.json',RESOURCE);out=[]
    class Reader(CustomRecognition):
        def analyze(self,ctx,argv):
            def ocr(roi):return StageInspector._ocr(lambda kind,args:ctx.run_recognition_direct(kind,args,argv.image),roi)
            analysis=fast_analysis(vision,argv.image,lambda n:ctx.run_recognition(n,argv.image),{'path':params('theater_tap')},ocr)
            out.append(analysis)
            return self.AnalyzeResult(box=[0,0,1,1],detail={'analysis':analysis})
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();reader=Reader();resource.register_custom_recognition('TheaterGenericFixture',reader)
    assert resource.post_bundle(RESOURCE).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    reports=[]
    for path,expected in cases:
        image=np.asarray(Image.open(ROOT/path).convert('RGB'))[:,:,::-1].copy()
        variants=[('original',image,expected)]
        if expected:
            variants += [(f'dim{scale}',(image*scale).astype(np.uint8),None) for scale in (.3,.5,.7)]
            covered=image.copy();covered[17:58,1047:1191]=150
            variants.append(('covered_controls',covered,None))
        for label,frame,want in variants:
            assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='TheaterGenericFixture'),frame).wait().succeeded
            analysis=out[-1];current={}
            if analysis is not None:current=operation_view({'ui_tree':build_tree({**analysis,'window':WINDOW})})
            reports.append({'case':path,'variant':label,'expected':want,'current':current,'analysis':analysis})
            assert current.get('view')==want,(path,label,current,analysis)
    (tmp_path/'generic-replay.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')


def test_generic_shape_cannot_use_an_unfiltered_candidate():
    from driver_epic_seven.operational_theater import shape_match
    raw=SimpleNamespace(hit=True,filtered_results=[],best_result=SimpleNamespace(box=[1047,17,43,40],score=1))
    assert shape_match(None,None,lambda name:raw,'play')['hit'] is False


def test_intro_is_a_nonconsuming_target_only_inside_confirmed_theater_context():
    matches={key:{'hit':True} for key in ('theater_story_play_shape','theater_story_history_shape','theater_intro_text')}
    d=observation([('Act 9',[549,250,113,49]),('Tap the screen again to skip.',[496,620,218,18])],matches)
    assert operation_view(d)['view']=='theater_intro'
    assert target(d,params('theater_tap'),{}) is None
    prepared={'theater:theater:test:1':{'confirmed':True,'window':WINDOW}}
    assert target(d,params('theater_tap',act=9),prepared)==[1100,610,1,1]
    assert target(d,params('theater_tap',act=6),prepared) is None
