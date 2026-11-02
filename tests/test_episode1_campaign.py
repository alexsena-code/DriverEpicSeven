import json
import pytest
from copy import deepcopy

from driver_epic_seven.prequel import campaign_graph, stage, target
from driver_epic_seven.vision import classify


@pytest.mark.fixtures
def test_numeric_episode_story_map_requires_both_native_controls_and_no_overlay():
    from driver_epic_seven.config import ROOT
    from driver_epic_seven.observed_ui import build_tree, operation_view
    source=ROOT/'var/admin-episode4-20261030aj/episode4-story-map.json'
    if not source.exists():pytest.skip('Private Episode 4 story map unavailable.')
    observation=json.loads(source.read_text(encoding='utf-8'))
    spec=json.loads((ROOT/'resources/epic-seven/vision.json').read_text(encoding='utf-8'))
    matches=observation['matches']
    assert classify(matches,spec['states'])=='prequel_story_map'
    observation['state']='prequel_story_map'
    observation['ui_tree']=build_tree(observation,spec)
    view=operation_view(observation)
    assert view['view']=='prequel_story_map'
    context=next(row for row in view['items'] if row['semantic_id']=='context')
    assert context['episode_label']=='Episode 4'
    assert context['chapter_number']==4
    assert any(row.get('text')=='View Story' for row in view['items'])
    for anchor in ('map_episode_header','prequel_view_story'):
        wrong=deepcopy(matches);wrong[anchor]={'hit':False}
        assert classify(wrong,spec['states'])!='prequel_story_map'
    for overlay in ('story_confirm_question','story_reward_header','received_reward_header'):
        wrong=deepcopy(matches);wrong[overlay]={'hit':True}
        assert classify(wrong,spec['states'])!='prequel_story_map'


@pytest.mark.parametrize('identity,ordinal,title,location,energy', [('nog001',1,'Toward Solidarity','Icewind Coast',8),('nog002',2,'The Truth of a Promise','Slope of Promises',8),('nog003',3,'Righteous Cause','The Garden of Noias, Main Gate',8),('nog004',4,'New Final Study','Entrance of Calling',8),('nog005',5,'Solemn Practice','Prayer Room of Foundation',20),('nog006',6,'Reason of Obsession','Hallway of Mission',8),('nog007',7,'Final Step','The Ground for the Mortals',8),('nog008',8,'The End of Absolute Desire','Genesis Hall',8)])
def test_real_episode5_chapter10_catalog_does_not_collide_with_chapter9_group(identity,ordinal,title,location,energy):
    from driver_epic_seven.prequel import chapter_matches
    from driver_epic_seven.config import ROOT
    record=stage(identity)
    assert (record['chapter'],record['map_chapter'],record['ordinal'])==(11,'10',ordinal)
    assert (record['title'],record['location'],record['energy'])==(title,location,energy)
    assert record['chapter_title']=='Meaning of Imperfection'
    assert chapter_matches({'chapter_code':'10'},record)
    assert not chapter_matches({'chapter_code':'9'},record)
    plan,graph=campaign_graph(identity,identity,energy)
    assert plan['energy_limit']==energy and plan['max_starts']==1
    assert 'Path.Campaign.pab001.Start' not in graph
    requirements=json.loads((ROOT/'data/stages/star-requirements.json').read_text(encoding='utf-8'))['stages'][identity]
    assert [m['condition'] for m in requirements['missions']]==['clear_enter_count','clearnocontinue_enter_count','party_enter_aliverole_count']
    assert requirements['missions'][2]['parameters']==f'enter={identity},aliverole=all,count=3'


@pytest.mark.fixtures
@pytest.mark.parametrize('identity,ordinal,title,location,wrong_title', [('nog001',1,'Toward Solidarity','Icewind Coast','The Truth of a Promise'),('nog002',2,'The Truth of a Promise','Slope of Promises','Toward Solidarity'),('nog003',3,'Righteous Cause','The Garden of Noias,Main Gate','Toward Solidarity'),('nog004',4,'New Final Study','Entrance of Calling','Righteous Cause'),('nog005',5,'Solemn Practice','Prayer Room of Foundation','New Final Study'),('nog006',6,'Reason of Obsession','Hallway of Mission','Solemn Practice'),('nog007',7,'Final Step','The Ground for the Mortals','Reason of Obsession'),('nog008',8,'The End of Absolute Desire','Genesis Hall','Final Step')])
def test_real_chapter10_first_stage_current_map_supporter_and_preparation(identity,ordinal,title,location,wrong_title):
    from driver_epic_seven.config import ROOT
    from driver_epic_seven.observed_ui import operation_view
    folder=ROOT/'var/admin-episode5-20261031bf'
    files=[('pab008-completion.json' if ordinal==1 else identity+'-map-before.json'),identity+'-supporter-before.json',identity+'-preparation-before.json']
    if not all((folder/f).exists() for f in files):pytest.skip('Private current Chapter 10 observations unavailable.')
    map_data,supporter,prepared=[json.loads((folder/f).read_text(encoding='utf-8')) for f in files]
    current=operation_view(map_data)
    args={'kind':'prequel_ready','stage_id':identity}
    assert target(current,args,map_data) is not None
    for field,wrong in [('chapter_code','9'),('chapter_code','11'),('episode_label','Episode 4')]:
        negative=deepcopy(current)
        next(i for i in negative['items'] if i['semantic_id']=='context')[field]=wrong
        assert target(negative,args,map_data) is None
    negative=deepcopy(current)
    next(i for i in negative['items'] if i['semantic_id']=='context')['selected_description']='different'
    next(i for i in negative['items'] if i['semantic_id']=='stage_row' and i['ordinal']==ordinal)['title']='different'
    assert target(negative,args,map_data) is None
    args={'kind':'prequel_supporter','stage_id':identity}
    assert target({},args,supporter) is not None
    if identity=='nog005':
        banner=json.loads((folder/'nog005-supporter-banner-before.json').read_text(encoding='utf-8'))
        assert target({},args,banner) is None
    for original,wrong in [(title,wrong_title),(location,'Passage of Origin'),('Select Team','Ready')]:
        negative=deepcopy(supporter)
        next(r for r in negative['text'] if r['text']==original)['text']=wrong
        assert target({},args,negative) is None
    view=operation_view(prepared)
    args={'kind':'prequel_prepared','stage_id':identity}
    assert target(view,args,prepared) is not None
    if identity=='nog008':
        banner=json.loads((folder/'nog008-preparation-banner-before.json').read_text(encoding='utf-8'))
        assert target(operation_view(banner),args,banner) is None
    wrong_cost=8 if identity=='nog005' else 20
    for field,wrong in [('story_title',wrong_title),('location','Passage of Origin'),('cost',{'currency':'energy','cost':wrong_cost,'available':70})]:
        negative=deepcopy(view)
        next(i for i in negative['items'] if i['semantic_id']=='context')[field]=wrong
        assert target(negative,args,prepared) is None


def test_chapter_six_candidates_keep_episode_and_identity():
    first = stage('taw002')
    assert (first['episode'], first['chapter'], first['ordinal']) == (1, 6, 1)
    assert (first['title'], first['location'], first['energy']) == ('A Brazen Knight', 'Declaration Field', 8)
    plan, graph = campaign_graph('taw002', 'tae010', 64)
    assert plan['energy_limit'] == 64 and plan['max_starts'] == 8
    assert sum(name.endswith('.Start') for name in graph) == 8


@pytest.mark.parametrize('identity', ['kae003', 'sks006', 'skn006', 'crs003', 'pab001', 'pab008'])
def test_resolved_story_uses_zero_cost_and_no_battle_start(identity):
    record=stage(identity)
    assert record['energy']==0 and record['source_type']=='story'
    assert record['energy_source']['use_enterpoint']=='0'
    plan,graph=campaign_graph(identity,identity,0)
    assert plan['energy_limit']==0
    start=graph['Path.Campaign.'+identity+'.Start']['custom_recognition_param']['path']
    assert start['kind']=='prequel_story_start' and start['energy']==0
    assert all(node.get('custom_recognition_param',{}).get('path',{}).get('kind')!='prequel_start'
               for node in graph.values())


def test_episode_guard_refuses_same_chapter_wrong_episode():
    current = {'view': 'prequel_ready_map', 'items': [
        {'semantic_id': 'context', 'chapter_number': 6, 'episode_label': 'Episode 1',
         'selected_description': 'They finally found Krau, but he challenges Ras to a fight?'},
        {'semantic_id': 'stage_row', 'ordinal': 1, 'title': 'A Brazen Knight',
         'available': True, 'box': [90, 200, 200, 30]},
        {'semantic_id': 'ready_label', 'text': 'Ready', 'box': [1000, 610, 100, 30]}]}
    args = {'kind': 'prequel_ready', 'stage_id': 'taw002'}
    assert target(current, args) == [1000, 610, 100, 30]
    current['items'][0]['episode_label'] = '6th World Episode'
    assert target(current, args) is None


@pytest.mark.parametrize('actual,number,expected,accepted', [
    ('8S', 8, {'chapter': 9, 'map_chapter': '8S'}, True),
    ('8', 8, {'chapter': 9, 'map_chapter': '8S'}, False),
    ('9', 9, {'chapter': 9, 'map_chapter': '8S'}, False),
    ('8S', 8, {'chapter': 8}, False),
    (None, 8, {'chapter': 9, 'map_chapter': '8S'}, False),
    (None, 9, {'chapter': 9}, True),
])
def test_visible_chapter_code_is_not_catalog_group_index(actual, number, expected, accepted):
    from driver_epic_seven.prequel import chapter_matches
    assert chapter_matches({'chapter_code': actual, 'chapter_number': number}, expected) is accepted


@pytest.mark.fixtures
def test_live_chapter_8s_keeps_suffix_and_scoped_campaign_identity():
    from driver_epic_seven.config import ROOT
    from driver_epic_seven.observed_ui import build_tree, operation_view
    path = ROOT/'var/runs/20261101T025717Z_fb41d1e8/agent_000034.json'
    if not path.exists():pytest.skip('Private Episode 5 chapter 8S observation unavailable.')
    original=json.loads(path.read_text(encoding='utf-8'))['result']
    args={'kind':'prequel_ready','stage_id':'crs001'}
    def read(data):
        data['ui_tree']=build_tree(data)
        return operation_view(data)
    view=read(deepcopy(original))
    context=view['items'][0]
    assert view['view']=='prequel_ready_map'
    assert context['chapter_number']==8 and context['chapter_code']=='8S'
    assert '8S' in context['chapter_label']
    assert target(view,args) is not None
    for label in ['Chapter 8. The Final Stretch', 'Chapter 9. The Final Stretch', 'Chapter 8X. The Final Stretch']:
        wrong=deepcopy(original)
        next(r for r in wrong['text'] if 'Chapter' in r['text'])['text']=label
        assert target(read(wrong),args) is None
    wrong=deepcopy(original)
    next(r for r in wrong['text'] if r['text']=='Episode 5')['text']='Episode 4'
    assert target(read(wrong),args) is None
    wrong=deepcopy(original);wrong['matches']['map_ready_label']['hit']=False
    assert target(read(wrong),args) is None


@pytest.mark.fixtures
@pytest.mark.parametrize('identity,filename,location,prefix', [
    ('crs001','crs001-supporter-before.json','Royal Training Ground','8S-1. '),
    ('crs002','crs002-supporter-before.json','Divine Shelter of Darkness','8S-2. '),
    ('crs004','crs004-supporter-before.json',"Shadow Sovran's Chamber",'8S-4. '),
    ('crs005','crs005-supporter-before.json','Shaded Trail','8S-5. '),
])
def test_8s_supporter_uses_observed_location_without_catalog_ordinal_prefix(identity,filename,location,prefix):
    from driver_epic_seven.config import ROOT
    path=ROOT/'var/admin-episode5-20261031bc'/filename
    if not path.exists():pytest.skip('Private chapter 8S supporter observation unavailable.')
    data=json.loads(path.read_text(encoding='utf-8'))
    args={'kind':'prequel_supporter','stage_id':identity}
    assert stage(identity)['location']==location
    assert target({},args,data) is not None
    wrong=deepcopy(data)
    next(r for r in wrong['text'] if r['text']==location)['text']=prefix+location
    assert target({},args,wrong) is None


def test_episode_heading_requires_ready_and_rejects_overlay():
    from driver_epic_seven.config import ROOT
    import json
    spec = json.loads((ROOT / 'resources/epic-seven/vision.json').read_text(encoding='utf-8'))['states']['prequel_ready_map']
    names = {name for variant in spec['variants'] for field in ('all', 'any', 'none') for name in variant.get(field, [])}
    matches = {name: {'hit': False} for name in names}
    matches['episode1_heading']['hit'] = True
    assert classify(matches, {'map': spec}) == 'unknown'
    matches['map_ready_label']['hit'] = True
    assert classify(matches, {'map': spec}) == 'map'
    for overlay in ('story_reward_header', 'story_confirm_question', 'received_reward_header'):
        matches[overlay]['hit'] = True
        assert classify(matches, {'map': spec}) == 'unknown'
        matches[overlay]['hit'] = False


def test_supporter_requires_matching_stage_unambiguous_button_and_no_loading():
    from copy import deepcopy
    from driver_epic_seven.observed_ui import build_tree
    data = {'state': 'supporter_selection', 'matches': {}, 'window': {'client_size': [1212, 682]},
            'text': [{'text': text, 'box': box, 'score': .99} for text, box in [
                ('Declaration Field', [878, 78, 143, 23]),
                ('A Brazen Knight', [878, 117, 121, 24]),
                ('Select Team', [965, 616, 114, 25])]]}
    args = {'kind': 'prequel_supporter', 'stage_id': 'taw002'}
    def read(value):
        value['ui_tree'] = build_tree(value)
        return target({}, args, value)
    assert read(deepcopy(data)) == [965, 616, 114, 25]
    wrong = deepcopy(data); wrong['text'][1]['text'] = 'Another Stage'
    assert read(wrong) is None
    loading = deepcopy(data); loading['text'].append({'text': 'Loading', 'box': [400, 430, 80, 20], 'score': .99})
    assert read(loading) is None
    duplicate = deepcopy(data); duplicate['text'].append(deepcopy(duplicate['text'][-1]))
    assert read(duplicate) is None
    wrong = deepcopy(data); wrong['state'] = 'battle_ready'
    assert read(wrong) is None


def test_story_receipt_requires_both_text_and_close_without_decision_overlay():
    from driver_epic_seven.config import ROOT
    import json
    spec = json.loads((ROOT / 'resources/epic-seven/vision.json').read_text(encoding='utf-8'))['states']['story_reward']
    names = {name for variant in spec['variants'] for field in ('all', 'none') for name in variant.get(field, [])}
    matches = {name: {'hit': False} for name in names}
    matches['story_clear_receipt_text']['hit'] = True
    assert classify(matches, {'receipt': spec}) == 'unknown'
    matches['story_reward_close']['hit'] = True
    assert classify(matches, {'receipt': spec}) == 'receipt'
    for overlay in ('story_confirm_question', 'received_reward_header'):
        matches[overlay]['hit'] = True
        assert classify(matches, {'receipt': spec}) == 'unknown'
        matches[overlay]['hit'] = False


def test_suffixed_story_receipt_keeps_chapter_identity_and_required_controls():
    """Synthetic OCR contract cases, not a claim of a live 8S receipt."""
    from driver_epic_seven.observed_ui import build_tree, operation_view
    record=stage('crs003')
    data={'state':'story_reward','matches':{},'window':{
        'client_size':[1212,682],'process_name':'EpicSeven.exe',
        'window_title':'Epic Seven','window_class':'GLFW30'},
        'text':[{'text':text,'box':box,'score':.99} for text,box in [
            ('Story Clear',[500,150,180,30]),
            ('You have received Story Clear Reward.',[400,230,430,25]),
            ('Chapter 8S.',[580,290,160,25]),
            (record['location'],[550,330,400,25]),
            (record['title'],[550,365,300,25]),
            ('Tap to close',[530,470,180,25])]]}
    def read(value):
        value['ui_tree']=build_tree(value)
        return operation_view(value)
    args={'kind':'prequel_story_receipt','stage_id':'crs003'}
    current=read(deepcopy(data))
    assert current['view']=='story_reward'
    assert current['items'][0]['chapter_text']=='Chapter 8S.'
    assert target(current,args) == [530,470,180,25]
    for chapter in ['Chapter 8.','Chapter 9.','Chapter 8X.']:
        wrong=deepcopy(data);wrong['text'][2]['text']=chapter
        assert target(read(wrong),args) is None
    for missing in ['Story Clear','You have received Story Clear Reward.','Tap to close',record['location'],record['title']]:
        wrong=deepcopy(data);wrong['text']=[r for r in wrong['text'] if r['text']!=missing]
        assert target(read(wrong),args) is None


@pytest.mark.fixtures
@pytest.mark.parametrize('source,kind,identity', [
    ('var/admin-episode5-20261031bc/crs006-supporter-before.json','prequel_supporter','crs006'),
    ('var/admin-episode5-20261031bd/crs006-preparation.json','prequel_prepared','crs006'),
    ('var/admin-episode5-20261031bd/crs007-preparation-before.json','prequel_prepared','crs007'),
    ('var/admin-episode5-20261031bd/crs008-preparation-before.json','prequel_prepared','crs008'),
])
def test_native_wrapped_numeric_title_requires_current_prefix_location_and_suffix(tmp_path,source,kind,identity):
    import numpy as np
    from PIL import Image
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    from driver_epic_seven.config import ROOT
    from driver_epic_seven.prequel import augment_title
    from driver_epic_seven.reading import ReadContext
    from driver_epic_seven.observed_ui import build_tree,operation_view
    def read(data):return operation_view({'ui_tree':build_tree(data)})
    path=ROOT/source
    if not path.exists():pytest.skip('Private wrapped numeric title unavailable.')
    original=json.loads(path.read_text(encoding='utf-8'))
    pixels=np.asarray(Image.open(path.with_suffix('.png')).convert('RGB'))[:,:,::-1].copy()
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu()
    assert resource.post_bundle(ROOT/'resources/epic-seven').wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    frame=pixels
    def recognize(kind,args):
        return tasker.post_recognition(kind,args,frame).wait().get().nodes[-1].recognition
    record=stage(identity);suffix=record['title'].rsplit(' ',1)[1]
    args={'kind':kind,'stage_id':identity}
    assert target(read(original),args,original) is None
    good=deepcopy(original);augment_title(good,args,recognize)
    proof=good['campaign_numeric_title_reread']
    assert proof['accepted'] is True and proof['candidates'][0]['text']==suffix
    assert target(read(good),args,good)
    assert original['text']==json.loads(path.read_text(encoding='utf-8'))['text']
    wrong=deepcopy(original)
    next(r for r in wrong['text'] if r['text']==record['location'])['text']='Another Trail'
    calls=[]
    def wrong_location_recognition(kind,params):
        calls.append(list(params.roi))
        return None
    augment_title(wrong,args,wrong_location_recognition)
    assert 'campaign_numeric_title_reread' not in wrong
    assert all(roi[1]<100 for roi in calls)  # Existing location reread is independent.
    assert target(read(wrong),args,wrong) is None
    frame=pixels.copy();frame[126:155,875:929]=0
    covered=deepcopy(original);augment_title(covered,args,recognize)
    assert covered['campaign_numeric_title_reread']['accepted'] is False
    assert target(read(covered),args,covered) is None
    for text,score,x,y in [(str(int(suffix)+1),.99,878,126),(suffix,.89,878,126),(suffix,.99,1100,126),(suffix,.99,878,100)]:
        altered=deepcopy(original)
        altered['text'].append({'text':text,'score':score,'box':[x,y,50,28]})
        assert target(read(altered),args,altered) is None
    lines=ReadContext(good,'screen',lambda n:None).preparation_title_rows()
    assert ' '.join(r['text'] for _,r in lines).endswith('Truth '+suffix)
    if kind=='prequel_prepared':
        import time
        start={**args,'kind':'prequel_start','max_energy':record['energy']}
        ticket={identity:{'epoch_seconds':time.time(),'window':good['window']}}
        assert target(read(good),start,good,ticket)
        assert target(read(good),start,good,{}) is None
        assert target(read(good),{**start,'max_energy':record['energy']-1},good,ticket) is None


def test_map_reads_chapter_when_ocr_omits_space():
    import json
    import pytest
    from driver_epic_seven.config import ROOT
    from driver_epic_seven.observed_ui import build_tree, operation_view
    path = ROOT / 'var/runs/20261029T131551Z_3e5e4fe8/agent_000001.json'
    if not path.exists():
        pytest.skip('Private episode 1 map observation unavailable.')
    data = json.loads(path.read_text(encoding='utf-8'))['result']
    for row in data['text']:
        if row['text'].startswith('Chapter 6'):
            row['text'] = row['text'].replace('Chapter 6', 'Chapter6', 1)
    view = operation_view({'ui_tree': build_tree(data)})
    assert view['view'] == 'prequel_ready_map'
    assert view['items'][0]['episode_label'] == 'Episode 1'
    assert view['items'][0]['chapter_number'] == 6


@pytest.mark.fixtures
def test_episode_one_final_result_accepts_only_proven_episode_two_return():
    from copy import deepcopy
    from driver_epic_seven.config import ROOT
    from driver_epic_seven.observed_ui import build_tree, operation_view
    path=ROOT/'var/runs/20261029T150252Z_351071f6/agent_000035.json'
    if not path.exists():pytest.skip('Private episode 2 return observation unavailable.')
    d=json.loads(path.read_text(encoding='utf-8'))['result']
    params={'kind':'prequel_map_return','stage_id':'tae010'}
    ticket={'prequel_victory:tae010':{'window':d['window']}}
    def read(data, proof=ticket):
        data['ui_tree']=build_tree(data)
        return target(operation_view(data),params,data,proof)
    assert read(deepcopy(d))==[0,0,1,1]
    missing=deepcopy(d);missing['text']=[r for r in missing['text'] if r['text']!='Episode 2']
    assert read(missing) is None
    missing=deepcopy(d);missing['state']='unknown'
    assert read(missing) is None
    wrong=deepcopy(ticket);wrong['prequel_victory:tae010']['window']['pid']+=1
    assert read(deepcopy(d),wrong) is None
    assert read(deepcopy(d),{}) is None


@pytest.mark.fixtures
@pytest.mark.parametrize('identity,folder,filename',[('pab001','admin-episode5-20261031bd','pab001-map-before.json'),('pab008','admin-episode5-20261031bf','pab008-map-before.json')])
def test_current_chapter9_story_uses_display_code_and_zero_cost(identity,folder,filename):
    from driver_epic_seven.config import ROOT
    from driver_epic_seven.observed_ui import operation_view
    path=ROOT/'var'/folder/filename
    if not path.exists():pytest.skip('Private current Chapter 9 story observation unavailable.')
    observation=json.loads(path.read_text(encoding='utf-8'))
    view=operation_view(observation)
    record=stage(identity)
    assert record['chapter']==10 and record['map_chapter']=='9'
    assert record['chapter_title']=='The Debt'
    args={'kind':'prequel_story_start','stage_id':identity}
    assert target(view,args) is not None
    assert target(view,{'kind':'prequel_story_row','stage_id':identity}) is not None
    for field,wrong in [('chapter_code','10'),('chapter_code','8S'),('episode_label','Episode 4'),('selected_description','different'),('selected_kind_label','Stage')]:
        negative=deepcopy(view)
        context=next(i for i in negative['items'] if i['semantic_id']=='context')
        context[field]=wrong
        assert target(negative,args) is None
    negative=deepcopy(view)
    negative['items']=[i for i in negative['items'] if i['semantic_id']!='view_story_label']
    assert target(negative,args) is None


@pytest.mark.fixtures
def test_current_chapter9_second_stage_identity_at_supporter():
    from driver_epic_seven.config import ROOT
    from driver_epic_seven.prequel import chapter_matches
    path=ROOT/'var/admin-episode5-20261031bd/pab002-supporter-before.json'
    if not path.exists():pytest.skip('Private current Chapter 9 supporter observation unavailable.')
    data=json.loads(path.read_text(encoding='utf-8'))
    record=stage('pab002')
    assert record['chapter']==10 and record['map_chapter']=='9'
    assert record['chapter_title']=='The Debt' and record['energy']==8
    assert chapter_matches({'chapter_code':'9','chapter_number':9},record)
    assert not chapter_matches({'chapter_code':'10','chapter_number':10},record)
    assert not chapter_matches({'chapter_code':'8S','chapter_number':8},record)
    args={'kind':'prequel_supporter','stage_id':'pab002'}
    assert target({},args,data) is not None
    for original,replacement in [('The Passage I','The Passage II'),('Passage of Division','Frozen Heart'),('Select Team','Ready')]:
        wrong=deepcopy(data)
        next(r for r in wrong['text'] if r['text']==original)['text']=replacement
        assert target({},args,wrong) is None


@pytest.mark.fixtures
@pytest.mark.parametrize('identity,filename,wrong_title', [('pab003','pab003-preparation-before.json','Abigail'),('pab005','pab005-preparation-before.json','Elvira'),('pab007','pab007-preparation-before.json','Elvira')])
def test_current_chapter9_boss_preparation_keeps_identity_and_cost(identity,filename,wrong_title):
    from driver_epic_seven.config import ROOT
    from driver_epic_seven.observed_ui import operation_view
    from driver_epic_seven.prequel import chapter_matches
    path=ROOT/'var'/('admin-episode5-20261031bf' if identity=='pab007' else 'admin-episode5-20261031bd')/filename
    if not path.exists():pytest.skip('Private current Chapter 9 boss preparation unavailable.')
    data=json.loads(path.read_text(encoding='utf-8'))
    view=operation_view(data)
    record=stage(identity)
    assert record['chapter']==10 and record['map_chapter']=='9'
    assert record['chapter_title']=='The Debt' and record['energy']==8
    assert chapter_matches({'chapter_code':'9','chapter_number':9},record)
    for wrong in ['10','8S']:
        assert not chapter_matches({'chapter_code':wrong},record)
    args={'kind':'prequel_prepared','stage_id':identity}
    assert target(view,args,data) is not None
    for field,wrong in [('story_title',wrong_title),('location','Passage of Division'),('cost',{'currency':'energy','cost':20,'available':31})]:
        negative=deepcopy(view)
        context=next(i for i in negative['items'] if i['semantic_id']=='context')
        context[field]=wrong
        assert target(negative,args,data) is None


@pytest.mark.fixtures
def test_current_chapter9_passage_two_supporter_roman_title_and_location():
    from driver_epic_seven.config import ROOT
    from driver_epic_seven.prequel import chapter_matches
    path=ROOT/'var/admin-episode5-20261031bd/pab004-supporter-before.json'
    if not path.exists():pytest.skip('Private current Passage II supporter observation unavailable.')
    data=json.loads(path.read_text(encoding='utf-8'))
    record=stage('pab004')
    assert record['chapter']==10 and record['map_chapter']=='9'
    assert record['chapter_title']=='The Debt' and record['energy']==8
    assert chapter_matches({'chapter_code':'9','chapter_number':9},record)
    assert not chapter_matches({'chapter_code':'10'},record)
    args={'kind':'prequel_supporter','stage_id':'pab004'}
    assert target({},args,data) is not None
    wrong=deepcopy(data)
    next(r for r in wrong['text'] if r['text']=='Passage of Grief')['text']='Passage of Division'
    assert target({},args,wrong) is None
    for replacement in ['The Passage I','The Passage III','The Passage']:
        wrong=deepcopy(data)
        next(r for r in wrong['text'] if r['text'].startswith('The Passage'))['text']=replacement
        assert target({},args,wrong) is None


@pytest.mark.fixtures
@pytest.mark.parametrize('source,kind,expected_roi', [('var/admin-episode5-20261031bd/pab006-preparation-before.json','prequel_prepared',[880,112,128,34]),('var/admin-episode5-20261031be/pab006-supporter-before.json','prequel_supporter',[870,108,128,34])])
def test_current_passage_three_native_title_and_twenty_energy(tmp_path,source,kind,expected_roi):
    import time,numpy as np
    from PIL import Image
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    from driver_epic_seven.config import ROOT
    from driver_epic_seven.prequel import augment_title,chapter_matches,title_match
    from driver_epic_seven.observed_ui import build_tree,operation_view
    path=ROOT/source
    if not path.exists():pytest.skip('Private current Passage III preparation unavailable.')
    original=json.loads(path.read_text(encoding='utf-8'))
    frame=np.asarray(Image.open(path.with_suffix('.png')).convert('RGB'))[:,:,::-1].copy()
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu()
    assert resource.post_bundle(ROOT/'resources/epic-seven').wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    def recognize(kind,args):return tasker.post_recognition(kind,args,frame).wait().get().nodes[-1].recognition
    def read(data):return operation_view({'ui_tree':build_tree(data)})
    args={'kind':kind,'stage_id':'pab006'}
    record=stage('pab006')
    assert record['chapter']==10 and record['map_chapter']=='9' and record['energy']==20
    assert chapter_matches({'chapter_code':'9'},record)
    assert not chapter_matches({'chapter_code':'10'},record)
    good=deepcopy(original);augment_title(good,args,recognize)
    proof=good['campaign_title_reread']
    assert proof['accepted'] is True and proof['tight']['roi']==expected_roi,proof
    assert title_match(proof['tight']['candidates'][0]['text'],record['title'])
    assert proof['tight']['candidates'][0]['score']>=.90
    assert original['text']==json.loads(path.read_text(encoding='utf-8'))['text']
    assert target(read(good),args,good)
    for shifted_y in [95,150]:
        wrong=deepcopy(original)
        line=next(r for r in wrong['text'] if r['text'].startswith('The Passage'))
        line['box'][1]=shifted_y
        augment_title(wrong,args,recognize)
        assert target(read(wrong),args,wrong) is None
    if kind=='prequel_prepared':
        start={**args,'kind':'prequel_start','max_energy':20}
        ticket={'pab006':{'epoch_seconds':time.time(),'window':good['window']}}
        assert target(read(good),start,good,ticket)
        assert target(read(good),start,good,{}) is None
        assert target(read(good),{**start,'max_energy':19},good,ticket) is None
    if kind=='prequel_prepared':
        negative=deepcopy(read(good))
        next(i for i in negative['items'] if i['semantic_id']=='context')['story_title']='The Passage II'
        assert target(negative,args,good) is None
    else:
        wrong=deepcopy(good)
        next(r for r in wrong['text'] if r.get('source')=='campaign_title_reread')['text']='The Passage II'
        assert target(read(wrong),args,wrong) is None
    frame[100:155,870:1100]=0
    covered=deepcopy(original);augment_title(covered,args,recognize)
    assert target(read(covered),args,covered) is None
