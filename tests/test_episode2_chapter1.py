import json
from copy import deepcopy
import pytest
from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree, operation_view
from driver_epic_seven.prequel import stage, campaign_graph, target


def test_timing_badge_filter_is_confined_to_the_current_right_hand_field():
    from driver_epic_seven.reading import is_preparation_time_record
    assert is_preparation_time_record({'text':'e No Record','box':[1084,112,102,20]})
    assert is_preparation_time_record({'text':'No Record','box':[1100,112,85,20]})
    assert not is_preparation_time_record({'text':'No Record','box':[878,112,85,20]})
    assert not is_preparation_time_record({'text':'Another No Record','box':[1084,112,102,20]})
    assert not is_preparation_time_record({'text':'e No Record','box':[1084,200,102,20]})


@pytest.mark.fixtures
def test_sks007_timing_badge_does_not_replace_title_or_relax_start_guards(tmp_path):
    import time
    import numpy as np
    from PIL import Image
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    from driver_epic_seven.prequel import augment_title
    folder=ROOT/'var/admin-episode5-20261031as'
    source=folder/'sks007-preparation-observation.json'
    if not source.exists():pytest.skip('Private timing-badge preparation unavailable.')
    original=json.loads(source.read_text(encoding='utf-8'))
    image=np.asarray(Image.open(folder/'sks007-preparation.png').convert('RGB'))[:,:,::-1].copy()
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu()
    assert resource.post_bundle(ROOT/'resources/epic-seven').wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    def recognize(kind,args):
        return tasker.post_recognition(kind,args,image).wait().get().nodes[-1].recognition
    args={'kind':'prequel_start','stage_id':'sks007','max_energy':20}
    good=deepcopy(original);augment_title(good,args,recognize)
    assert good['campaign_title_reread']['accepted'] is True
    current=operation_view({'ui_tree':build_tree(good)})
    assert current['items'][0]['story_title']=='Reality, Ideals, and Struggle'
    ticket={'sks007':{'epoch_seconds':time.time(),'window':good['window']}}
    assert target(current,args,good,ticket)
    assert target(current,args,good,{}) is None
    assert target(current,{**args,'stage_id':'sks008'},good,ticket) is None
    for field,bad in [('location','Another Exit'),('cost',{'currency':'energy','cost':8,'available':287})]:
        wrong=deepcopy(current);wrong['items'][0][field]=bad
        assert target(wrong,args,good,ticket) is None
    for filename in ('sks007-supporter-merged.json','sks007-supporter-glued.json'):
        merged=folder/filename
        if not merged.exists():continue
        supporter=json.loads(merged.read_text(encoding='utf-8'))
        assert any('No Record' in r['text'] for r in supporter['text'])
        image=np.asarray(Image.open(merged.with_suffix('.png')).convert('RGB'))[:,:,::-1].copy()
        args={'kind':'prequel_supporter','stage_id':'sks007'}
        augment_title(supporter,args,recognize)
        assert supporter['campaign_title_reread']['accepted'] is True
        assert supporter['campaign_title_reread']['roi']==[875,110,225,30]
        assert target({},args,supporter)
        assert target({},{**args,'stage_id':'sks008'},supporter) is None


@pytest.mark.fixtures
def test_native_title_strip_recovers_roman_suffix_without_accepting_wrong_stage(tmp_path):
    import numpy as np
    from PIL import Image
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    from driver_epic_seven.prequel import augment_title
    run=ROOT/'var/runs/20261030T032227Z_f4969f8d'
    if not (run/'path_failure_after.json').exists():pytest.skip('Private chapter nine supporter unavailable.')
    data=json.loads((run/'path_failure_after.json').read_text(encoding='utf-8'))
    image=np.asarray(Image.open(run/'path_failure_after.png').convert('RGB'))[:,:,::-1].copy()
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu()
    assert resource.post_bundle(ROOT/'resources/epic-seven').wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    def recognize(kind,args):
        return tasker.post_recognition(kind,args,image).wait().get().nodes[-1].recognition
    args={'kind':'prequel_supporter','stage_id':'com004'}
    good=deepcopy(data);augment_title(good,args,recognize)
    assert good['campaign_title_reread']['accepted'] is True
    assert good['campaign_title_reread']['original_rows'][0]['text']=='Desperate Struggle'
    assert target({},args,good)
    wrong=deepcopy(data);augment_title(wrong,{**args,'stage_id':'com008'},recognize)
    assert wrong['campaign_title_reread']['accepted'] is False
    assert target({},{**args,'stage_id':'com008'},wrong) is None
    # Zero I/II inference from a requested title; only the pixels supply it.
    absent=deepcopy(data);absent['matches']['prequel_ready_header']['hit']=False
    augment_title(absent,args,lambda *a:pytest.fail('No title OCR on an unproven panel'))
    assert 'campaign_title_reread' not in absent
    prep=ROOT/'var/runs/20261030T033241Z_ecf12945/path_failure_after.json'
    if prep.exists():
        import time
        prepared=json.loads(prep.read_text(encoding='utf-8'))
        image=np.asarray(Image.open(prep.with_suffix('.png')).convert('RGB'))[:,:,::-1].copy()
        start={'kind':'prequel_start','stage_id':'com004','max_energy':8}
        augment_title(prepared,start,recognize)
        current=operation_view({'ui_tree':build_tree(prepared)})
        assert current['items'][0]['story_title']=='Desperate Struggle I'
        ticket={'com004':{'epoch_seconds':time.time(),'window':prepared['window']}}
        assert target(current,start,prepared,ticket)
    location_fixture=ROOT/'var/runs/20261030T033504Z_bc104a59/path_failure_after.json'
    if location_fixture.exists():
        supporter=json.loads(location_fixture.read_text(encoding='utf-8'))
        image=np.asarray(Image.open(location_fixture.with_suffix('.png')).convert('RGB'))[:,:,::-1].copy()
        augment_title(supporter,args,recognize)
        assert supporter['campaign_location_reread']['accepted'] is True
        assert supporter['campaign_title_reread']['accepted'] is True
        assert target({},args,supporter)
    short_fixture=ROOT/'var/runs/20261030T040439Z_f3e6c314/path_failure_after.json'
    if short_fixture.exists():
        short=json.loads(short_fixture.read_text(encoding='utf-8'))
        image=np.asarray(Image.open(short_fixture.with_suffix('.png')).convert('RGB'))[:,:,::-1].copy()
        params={'kind':'prequel_supporter','stage_id':'dis005'}
        augment_title(short,params,recognize)
        assert short['campaign_title_reread']['accepted'] is True
        assert short['campaign_title_reread']['tight']['candidates'][0]['text']=='Honor II'
        assert target({},params,short)
        assert target({},{**params,'stage_id':'dis004'},short) is None
        shifted_fixture=ROOT/'var/runs/20261030T041416Z_4530836b/path_failure_after.json'
        if shifted_fixture.exists():
            shifted=json.loads(shifted_fixture.read_text(encoding='utf-8'))
            image=np.asarray(Image.open(shifted_fixture.with_suffix('.png')).convert('RGB'))[:,:,::-1].copy()
            augment_title(shifted,params,recognize)
            assert shifted['campaign_title_reread']['accepted'] is True
            assert target({},params,shifted)


@pytest.mark.parametrize('actual,expected,accepted', [
    ('0 Captain! My Captain!', 'O Captain! My Captain!', True),
    ('O Captain! My Captain!', 'O Captain! My Captain!', True),
    ('0 Captain! Another Captain!', 'O Captain! My Captain!', False),
    ('Captain 0', 'Captain 1', False),
    ('Loyalty Il', 'Loyalty II', True),
    ('Honorll', 'Honor II', True),
    ('HonorlIl', 'Honor II', False),
    ('Loyalty 1', 'Loyalty I', True),
    ('Loyalty I', 'Loyalty II', False),
    ('Loyalty', 'Loyalty I', False),
    ('Another l', 'Loyalty I', False),
    ('', 'O Captain! My Captain!', False),
])
def test_title_glyph_tolerance_is_scoped(actual, expected, accepted):
    from driver_epic_seven.prequel import title_match
    assert bool(title_match(actual, expected)) is accepted


@pytest.mark.fixtures
def test_chapter_nine_punctuation_partial_fields_and_start_guards():
    import time
    path=ROOT/'var/runs/20261030T031043Z_291ebc75/agent_000013.json'
    if not path.exists():pytest.skip('Private chapter nine preparation unavailable.')
    data=json.loads(path.read_text(encoding='utf-8'))['result']
    def read(d):return operation_view({'ui_tree':build_tree(d)})
    view=read(data);info=view['items'][0]
    assert view['view']=='prequel_preparation'
    assert info['story_title']=='0 Captain! My Captain!' and info['team_cp']==525264
    params={'kind':'prequel_start','stage_id':'com001','max_energy':8}
    ticket={'com001':{'epoch_seconds':time.time(),'window':data['window']}}
    assert target(view,params,data,ticket)
    for field,bad in [('location','Another Passage'),('story_title','0 Captain! Another Captain!'),
                      ('story_title',None),('cost',None),('visible_hero_levels',None)]:
        wrong=deepcopy(view);wrong['items'][0][field]=bad
        assert target(wrong,params,data,ticket) is None
    assert target(view,params,data,{}) is None
    for text in ('0 Captain! My Captain!', "Stranger's Passage"):
        partial=deepcopy(data);partial['text']=[r for r in partial['text'] if r['text']!=text]
        current=read(partial)
        assert current['view']=='prequel_preparation' and current['items'][0]['cost']['cost']==8
        assert target(current,params,partial,ticket) is None
    no_header=deepcopy(data);no_header['matches']['prequel_ready_header']['hit']=False
    assert read(no_header).get('view')!='prequel_preparation'


@pytest.mark.fixtures
def test_chapter_nine_supporter_glyph_still_requires_exact_location():
    path=ROOT/'var/runs/20261030T031043Z_291ebc75/agent_000011.json'
    if not path.exists():pytest.skip('Private chapter nine supporter unavailable.')
    data=json.loads(path.read_text(encoding='utf-8'))['result']
    args={'kind':'prequel_supporter','stage_id':'com001'}
    assert target({},args,data)
    for original,replacement in [("Stranger's Passage",'Another Passage'),
                                  ('0 Captain! My Captain!','0 Captain! Another Captain!')]:
        wrong=deepcopy(data)
        for row in wrong['text']:
            if row['text']==original:row['text']=replacement
        assert target({},args,wrong) is None


def test_episode_two_catalog_is_shared_and_finite():
    first = stage('jer001')
    assert (first['episode'], first['chapter'], first['ordinal']) == (2,1,1)
    assert (first['map_title'], first['location'], first['energy']) == ("Usurper's Tears",'Abandoned Ferry Port',8)
    plan, graph = campaign_graph('jer001','jer010',84)
    assert plan['max_starts']==10 and plan['energy_limit']==84
    assert sum(name.endswith('.Start') for name in graph)==10


def test_episode_two_chapter_two_remaining_plan_is_finite():
    plan,graph=campaign_graph('mel007','mel010',36)
    assert plan['stage_ids']==['mel007','mel008','mel009','mel010']
    assert plan['energy_limit']==36 and plan['max_starts']==4
    assert sum(name.endswith('.Start') for name in graph)==4
    with pytest.raises(ValueError):campaign_graph('mel007','mel010',35)
    with pytest.raises(ValueError):campaign_graph('mel005','mel010',100)


@pytest.mark.parametrize('chapter',range(3,11))
def test_episode_two_static_next_chapters_reuse_finite_compiler_without_claiming_access(chapter):
    from driver_epic_seven.prequel import campaign_catalog
    entries=sorted((s for s in campaign_catalog().values() if s['episode']==2 and s['chapter']==chapter),key=lambda s:s['ordinal'])
    assert entries and all(type(s['energy']) is int and s['energy']>0 for s in entries)
    cost=sum(s['energy'] for s in entries)
    plan,graph=campaign_graph(entries[0]['id'],entries[-1]['id'],cost)
    assert plan['energy_limit']==cost and plan['max_starts']==len(entries)
    assert sum(k.endswith('.Start') for k in graph)==len(entries)
    assert all(n['max_hit']==1 for k,n in graph.items() if k.endswith('.Start'))


@pytest.mark.fixtures
def test_native_episode_two_plain_header_and_current_chapter_two_map(tmp_path):
    import numpy as np
    from PIL import Image
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    from driver_epic_seven.vision import Vision
    run=ROOT/'var/runs/20261029T163233Z_68ef9287'
    if not (run/'observation.json').exists():pytest.skip('Private chapter two map unavailable.')
    saved=json.loads((run/'observation.json').read_text(encoding='utf8'))
    v=Vision(ROOT/'resources/epic-seven/vision.json',ROOT/'resources/epic-seven')
    found=[]
    class Replay(CustomRecognition):
        def analyze(self,context,argv):
            found.append(v.inspect(argv.image,lambda n:context.run_recognition(n,argv.image)))
            return self.AnalyzeResult(box=[0,0,1,1],detail=found[-1])
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('ChapterTwoMap',Replay())
    assert resource.post_bundle(ROOT/'resources/epic-seven').wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    frame=np.asarray(Image.open(run/'agent_000001.png').convert('RGB'))[:,:,::-1].copy()
    cases=[('positive',frame,True),('dimmed',(frame*.55).astype(np.uint8),False)]
    for name,box in [('missing_heading',(55,8,195,56)),('missing_ready',(980,590,1140,665))]:
        image=frame.copy();x,y,x2,y2=box;image[y:y2,x:x2]=0;cases.append((name,image,False))
    for name,image,positive in cases:
        assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='ChapterTwoMap'),image).wait().succeeded
        a={**saved,**found[-1]};a['ui_tree']=build_tree(a,v.spec)
        view=operation_view(a)
        if positive:
            assert a['state']=='episode_map' and view['view']=='prequel_ready_map'
            assert view['items'][0]['chapter_number']==2
            assert target(view,{'kind':'prequel_ready','stage_id':'mel007'})
            assert target(view,{'kind':'prequel_ready','stage_id':'jer007'}) is None
            wrong=deepcopy(a);wrong['text']=[{**r,'text':'Episode 1'} if r['text']=='Episode 2' else r for r in wrong['text']]
            wrong['ui_tree']=build_tree(wrong,v.spec)
            assert target(operation_view(wrong),{'kind':'prequel_ready','stage_id':'mel007'}) is None
        else:assert a['state']!='episode_map',name


@pytest.mark.fixtures
def test_episode_two_map_uses_current_anchors_and_rejects_wrong_episode_stage():
    path=ROOT/'var/runs/20261029T150252Z_351071f6/agent_000035.json'
    if not path.exists():pytest.skip('Private episode 2 map unavailable.')
    data=json.loads(path.read_text(encoding='utf-8'))['result']
    def read(d):return operation_view({'ui_tree':build_tree(d)})
    view=read(deepcopy(data))
    assert view['view']=='prequel_ready_map'
    assert view['items'][0]['episode_label']=='Episode 2' and view['items'][0]['chapter_number']==1
    assert any(r.get('ordinal')==1 and r.get('title')=="Usurper's Tears" for r in view['items'])
    altered=deepcopy(data)
    altered['text']=[{**r,'text':'Episode 1'} if r['text']=='Episode 2' else r for r in altered['text']]
    assert read(altered)['items'][0]['episode_label']=='Episode 1'
    assert target(read(altered),{'kind':'prequel_row','stage_id':'jer001'},altered) is None
    altered=deepcopy(data);altered['matches']['map_episode_header']['hit']=False
    assert read(altered).get('view')!='prequel_ready_map'


def test_stage_row_rejects_wrong_episode():
    current={'view':'prequel_ready_map','items':[{'semantic_id':'context','chapter_number':1,'episode_label':'Episode 2'},
        {'semantic_id':'stage_row','ordinal':1,'title':"Usurper's Tears",'available':True,'box':[90,209,170,24]}]}
    params={'kind':'prequel_row','stage_id':'jer001'}
    assert target(current,params)==[90,209,170,24]
    current['items'][0]['episode_label']='Episode 1'
    assert target(current,params) is None


@pytest.mark.fixtures
def test_native_side_alert_template_branch_requires_current_heading_and_close(tmp_path):
    import numpy as np
    from PIL import Image
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    from driver_epic_seven.vision import Vision
    source=ROOT/'var/runs/20261029T163456Z_d5250004/before.png'
    if not source.exists():pytest.skip('Private live side alert unavailable.')
    v=Vision(ROOT/'resources/epic-seven/vision.json',ROOT/'resources/epic-seven')
    # Keep the original template branch's positives and missing-anchor negatives.
    # The OCR composition is exercised separately against the full production spec.
    template_variant=next(s for s in v.spec['states']['side_story_alert']['variants']
                          if set(s['all'])=={'side_alert_header','side_alert_close'})
    v.spec['states']={'side_story_alert':template_variant}
    names=set(v.spec['states']['side_story_alert']['all'])
    v.spec['templates']={k:s for k,s in v.spec['templates'].items() if k in names};v.spec['ocr']={}
    outputs=[]
    class Replay(CustomRecognition):
        def analyze(self,context,argv):
            a=v.inspect(argv.image,lambda n:context.run_recognition(n,argv.image))
            a['window']={'client_size':[1212,682]};a['ui_tree']=build_tree(a,v.spec)
            outputs.append(v.target(a,{'state':'side_story_alert','target':'side_alert_close'}))
            return self.AnalyzeResult(box=[0,0,1,1],detail=a)
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('SideAlertFixture',Replay())
    assert resource.post_bundle(ROOT/'resources/epic-seven').wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    frame=np.asarray(Image.open(source).convert('RGB'))[:,:,::-1].copy()
    cases=[frame,(frame*.5).astype(np.uint8)]
    for box in ((450,125,770,175),(535,505,675,565)):
        image=frame.copy();x,y,x2,y2=box;image[y:y2,x:x2]=0;cases.append(image)
    for image in cases:
        assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='SideAlertFixture'),image).wait().succeeded
    assert outputs[0] is not None
    assert outputs[1:]==[None,None,None]


def test_new_episode_does_not_change_free_story_recovery_mission(monkeypatch):
    from driver_epic_seven import prequel
    catalog=prequel.campaign_catalog()
    original=prequel.campaign_graph('tar001','tar001',0)[1]
    assert any('Recovery.' in name for name in original)
    # An unrelated episode with the same chapter and a longer sequence must
    # never determine the mission used to recover this free story.
    extended={**catalog,'foreign':{**catalog['jer010'],'id':'foreign','chapter':3,'ordinal':99}}
    monkeypatch.setattr(prequel,'campaign_catalog',lambda:extended)
    full=prequel.campaign_graph('tar001','tar001',0)[1]
    assert full==original


@pytest.mark.fixtures
def test_native_split_available_map_row_requires_current_number_title_and_map(tmp_path):
    import numpy as np
    from PIL import Image
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    from driver_epic_seven.prequel import augment_title
    run=ROOT/'var/admin-campaign-20261030o'
    if not (run/'pow001-map-observation.json').exists():pytest.skip('Private split map row unavailable.')
    original=json.loads((run/'pow001-map-observation.json').read_text(encoding='utf-8'))
    frame=np.asarray(Image.open(run/'pow001-map.png').convert('RGB'))[:,:,::-1].copy()
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();assert resource.post_bundle(ROOT/'resources/epic-seven').wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    params={'kind':'prequel_row','stage_id':'pow001'}
    def read(data):return operation_view({'ui_tree':build_tree(data)})
    assert target(read(original),params,original) is None
    data=deepcopy(original)
    augment_title(data,params,lambda kind,args:tasker.post_recognition(kind,args,frame).wait().get().nodes[-1].recognition)
    assert data['campaign_row_reread']['accepted']
    assert target(read(data),params,data)
    assert target(read(data),{'kind':'prequel_ready','stage_id':'pow001'},data)
    for label in ('2. First Things First','1. Another Story','First Things First'):
        wrong=deepcopy(original)
        # Exercise recognition rejection independently of the native positive.
        from unittest.mock import patch
        with patch('driver_epic_seven.stages.StageInspector._ocr',return_value=[{'text':label,'score':.99,'box':[85,203,200,32]}]):
            augment_title(wrong,params,lambda *args:None)
        assert not wrong['campaign_row_reread']['accepted']
        assert target(read(wrong),params,wrong) is None
    for control in ('map_episode_header','map_ready_label','path_prequel_available'):
        wrong=deepcopy(original);wrong['matches'][control]['hit']=False
        augment_title(wrong,params,lambda *args:pytest.fail('Unknown map must not reread a row.'))
        assert 'campaign_row_reread' not in wrong
    for label in ('Episode 2','Episode 4'):
        wrong=deepcopy(original)
        wrong['text']=[{**r,'text':label} if r['text']=='Episode 3' else r for r in wrong['text']]
        augment_title(wrong,params,lambda *args:pytest.fail('Wrong episode must not reread a row.'))
        assert target(read(wrong),params,wrong) is None


@pytest.mark.fixtures
def test_native_side_alert_with_covered_title_requires_both_lines_and_close(tmp_path):
    import numpy as np
    from PIL import Image
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    from driver_epic_seven.vision import Vision
    from driver_epic_seven.story_performance import candidate_matcher
    bundle=ROOT/'resources/epic-seven'
    current=ROOT/'var/runs/20261030T064818Z_22f4010d/path_failure_after.png'
    original=ROOT/'var/runs/20261026T011654Z_ce82e175/phase3_diagnosis.png'
    if not current.exists() or not original.exists():pytest.skip('Private side alert captures unavailable.')
    vision=Vision(bundle/'vision.json',bundle)
    params={'state':'side_story_alert','target':'side_alert_close','read_text':True}
    outputs=[]
    class Replay(CustomRecognition):
        def analyze(self,context,argv):
            calls=[]
            def recognize(name):
                calls.append(name)
                return context.run_recognition(name,argv.image)
            matcher=candidate_matcher(vision,argv.image,recognize,params)
            analysis=vision.inspect(argv.image,matcher) if matcher else {'state':'unknown','matches':{}}
            analysis['window']={'process_name':'EpicSeven.exe','client_size':[1212,682]}
            analysis['ui_tree']=build_tree(analysis,vision.spec)
            outputs.append({'state':analysis['state'],'target':vision.target(analysis,params),
                            'matches':analysis['matches'],'native_calls':calls})
            return self.AnalyzeResult(box=[0,0,1,1],detail=outputs[-1])
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('SideAlertCoveredTitle',Replay())
    assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    frame=np.asarray(Image.open(current).convert('RGB'))[:,:,::-1].copy()
    cases=[('banner',frame,True),('original',np.asarray(Image.open(original).convert('RGB'))[:,:,::-1].copy(),True)]
    for label,box,expected in [('title',(495,130,720,175),True),('cards',(310,300,910,455),True),
            ('first_line',(350,208,860,235),False),('second_line',(345,235,870,260),False),
            ('close',(535,505,680,550),False)]:
        image=frame.copy();x,y,x2,y2=box;image[y:y2,x:x2]=0;cases.append((label,image,expected))
    cases += [(f'dimmed-{factor}',(frame*factor).astype(np.uint8),False) for factor in (.70,.45)]
    for name in ('00_lobby.png','24_story_confirmation.png','34_story_dimmed.png'):
        path=ROOT/'tests/fixtures/local'/name
        if path.exists():cases.append((name,np.asarray(Image.open(path).convert('RGB'))[:,:,::-1].copy(),False))
    for label,image,expected in cases:
        assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='SideAlertCoveredTitle'),image).wait().succeeded
        result=outputs[-1]
        assert (result['state']=='side_story_alert') is expected,(label,result)
        assert (result['target'] is not None) is expected,(label,result)
        if label=='banner':
            assert not result['matches']['side_alert_header']['hit']
            assert all(result['matches'][k]['hit'] for k in ('side_alert_unlocked_text','side_alert_list_hint','side_alert_close'))
        if label=='close':assert 'OCR.SideAlertBody' not in result['native_calls']
    (tmp_path/'side-alert-covered-title.json').write_text(json.dumps(outputs),encoding='utf-8')


@pytest.mark.fixtures
def test_observed_chapter_header_merged_with_arrow_preserves_identity_guards():
    path=ROOT/'var/admin-campaign-20261030s/epi003-merged-chapter.json'
    if not path.exists():pytest.skip('Private merged chapter OCR unavailable.')
    original=json.loads(path.read_text(encoding='utf8'))
    def read(data):return operation_view({'ui_tree':build_tree(data)})
    current=read(original)
    assert current['view']=='prequel_ready_map'
    assert current['items'][0]['chapter_number']==6
    assert current['items'][0]['chapter_label']=='<Chapter 6.The Right Decision >'
    args={'kind':'prequel_row','stage_id':'epi003'}
    assert target(current,args,original)
    for heading in ('<Chapter 7.The Right Decision >','XChapter 6.The Right Decision >',
                    '<<Chapter 6.The Right Decision >'):
        wrong=deepcopy(original)
        wrong['text']=[{**r,'text':heading} if 'Chapter' in r['text'] else r for r in wrong['text']]
        assert target(read(wrong),args,wrong) is None
    for anchor in ('map_episode_header','map_ready_label','path_prequel_available'):
        wrong=deepcopy(original);wrong['matches'][anchor]['hit']=False
        assert target(read(wrong),args,wrong) is None


@pytest.mark.fixtures
def test_wrapped_supporter_title_requires_complete_aligned_current_text():
    path=ROOT/'var/runs/20261030T092758Z_a4f85e77/path_failure_after.json'
    if not path.exists():pytest.skip('Private wrapped supporter title unavailable.')
    original=json.loads(path.read_text(encoding='utf8'))
    args={'kind':'prequel_supporter','stage_id':'epi004'}
    assert target({},args,original)
    for missing in ('Smile','The Lady with the Gentle',"Starlight's Home",'Select Team'):
        wrong=deepcopy(original);wrong['text']=[r for r in wrong['text'] if r['text']!=missing]
        assert target({},args,wrong) is None
    wrong=deepcopy(original)
    for r in wrong['text']:
        if r['text']=='Smile':r['box'][1]=107
    assert target({},args,wrong) is None
    wrong=deepcopy(original)
    for r in wrong['text']:
        if r['text']=='Smile':r['score']=.89
    assert target({},args,wrong) is None
    assert target({},{**args,'stage_id':'epi005'},original) is None


@pytest.mark.fixtures
def test_wrapped_preparation_title_above_old_boundary_keeps_start_guards():
    import time
    path=ROOT/'var/runs/20261030T093452Z_220afd30/path_failure_after.json'
    if not path.exists():pytest.skip('Private wrapped preparation title unavailable.')
    original=json.loads(path.read_text(encoding='utf8'))
    def read(data):return operation_view({'ui_tree':build_tree(data)})
    current=read(original);info=current['items'][0]
    assert info['story_title']=='The Lady with the Gentle Smile'
    assert info['location']=="Starlight's Home" and info['cost']['cost']==8
    params={'kind':'prequel_start','stage_id':'epi004','max_energy':8}
    ticket={'epi004':{'epoch_seconds':time.time(),'window':original['window']}}
    assert target(current,params,original,ticket)
    assert target(current,params,original,{}) is None
    for missing in ('The Lady with the Gentle','Smile'):
        wrong=deepcopy(original);wrong['text']=[r for r in wrong['text'] if r['text']!=missing]
        assert target(read(wrong),params,wrong,ticket) is None
    wrong=deepcopy(original)
    first=next(r for r in wrong['text'] if r['text']=='The Lady with the Gentle')
    wrong['text'].append(deepcopy(first))
    assert read(wrong)['items'][0]['story_title'] is None
    assert target(read(wrong),params,wrong,ticket) is None
    for field,bad in [('cost',{'currency':'energy','cost':9,'available':303}),
                      ('location','Another Home'),('visible_hero_levels',None)]:
        altered=deepcopy(current);altered['items'][0][field]=bad
        assert target(altered,params,original,ticket) is None


@pytest.mark.fixtures
def test_win002_calibrated_location_is_exact_and_scoped_to_this_stage():
    from driver_epic_seven.prequel import stage
    path=ROOT/'var/admin-campaign-20261030aa/win002-supporter.json'
    if not path.exists():pytest.skip('Private win002 supporter unavailable.')
    original=json.loads(path.read_text(encoding='utf8'))
    expected=stage('win002')
    assert expected['location']=='Path of a Fierce Fight'
    assert expected['location_source_text']=='The Path of a Fierce Fight'
    args={'kind':'prequel_supporter','stage_id':'win002'}
    assert target({},args,original)
    assert target({},{'kind':'prequel_supporter','stage_id':'win003'},original) is None
    for actual in ('The Path of a Fierce Fight','Path of Another Fight','Path of a Fierce'):
        wrong=deepcopy(original)
        wrong['text']=[{**r,'text':actual} if r['text']==expected['location'] else r for r in wrong['text']]
        assert target({},args,wrong) is None
    for missing in ('An Obstacle','Select Team',expected['location']):
        wrong=deepcopy(original);wrong['text']=[r for r in wrong['text'] if r['text']!=missing]
        assert target({},args,wrong) is None
