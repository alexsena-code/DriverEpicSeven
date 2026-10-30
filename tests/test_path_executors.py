from copy import deepcopy
import json
from pathlib import Path
import time

import pytest

from driver_epic_seven.config import ROOT
from driver_epic_seven.prequel import stage, campaign_graph, target, reserve_entry, finish_graph
from driver_epic_seven.path_execution import free_summon_graph, path_target
from driver_epic_seven.observed_ui import build_tree, operation_view


@pytest.mark.parametrize('reached', [False, True])
def test_terminal_proof_survives_later_capture_failure_without_retry(reached):
    from types import SimpleNamespace
    from driver_epic_seven.path_execution import run_graph
    calls=[]
    evidence=SimpleNamespace(path=Path('evidence'), write=lambda *args:calls.append(args))
    terminal=SimpleNamespace(name='Done',completed=reached,action=None)
    job=SimpleNamespace(get=lambda:SimpleNamespace(nodes=[terminal]))
    def unavailable(*args,**kwargs):
        raise RuntimeError('Window minimized after terminal recognition')
    runtime=SimpleNamespace(guard=lambda **kwargs:None,evidence=evidence,
        tasker=SimpleNamespace(post_task=lambda *args:job),wait=lambda *args,**kwargs:None,
        observe=unavailable)
    result=run_graph(runtime,{'Entry':{'action':'DoNothing','next':['Done']},
                              'Done':{'action':'DoNothing'}},'Entry','Done')
    assert result['completed'] is reached and result['postcondition_verified'] is reached
    assert result['needs_review'] is True and result['after'] is None
    assert result['observation_error']=='Window minimized after terminal recognition'
    assert [name for name,_ in calls]==['path_graph','path_result']


def test_rank_maximum_energy_reuses_existing_ack_without_claiming_recovery():
    rows=[('Rank up!',[547,183,118,35]),
          ('Maximum Energy has been increased',[449,263,312,21]),
          ('161> 172',[502,330,213,34]),('Tap to close',[554,430,105,21]),
          ('X Tap to close',[547,645,113,20])]
    def read(items):
        data={'state':'unknown','matches':{},'window':{'process_name':'EpicSeven.exe','client_size':[1212,682]},
              'text':[{'text':s,'box':b,'score':.99} for s,b in items]}
        data['ui_tree']=build_tree(data)
        return data
    data=read(rows);current=operation_view(data)
    assert current['view']=='rank_up_result' and current['mode']=='maximum_energy'
    context=current['items'][0]
    assert context['maximum_energy_before']==161 and context['maximum_energy_after']==172
    assert context['rank'] is None and context['recovered_energy'] is None
    assert path_target(data,{'kind':'informational_ack'},None)==[554,430,105,21]
    for missing in (0,1,3):
        assert path_target(read([r for i,r in enumerate(rows) if i!=missing]),
                           {'kind':'informational_ack'},None) is None
    assert operation_view(read([r for i,r in enumerate(rows) if i!=2]))['items'][0]['maximum_energy_after'] is None


def test_prequel_identity_uses_mission_binding_instead_of_old_map_caption():
    s=stage('tar007')
    assert s['title']=='One Last Strike' and s['location']=='A Rift in the Frustration'
    assert s['location_source_text']=='3-7. A Rift in the Frustration'
    assert s['mission_binding_id']=='ep0_3_7' and s['account_progress'] is None
    s=stage('dap005')
    assert s['title']=='An Unpermitted Future' and s['location']=='Corrupted Forest'


def test_campaign_is_finite_has_one_start_and_auto_click_per_stage_and_no_map_before_victory():
    plan,graph=campaign_graph('tar007','tar008',16)
    assert plan['energy_limit']==16 and plan['max_starts']==2
    starts=[n for k,n in graph.items() if k.endswith('.Start')]
    assert len(starts)==2 and all(n['max_hit']==1 for n in starts)
    assert all(n['max_hit']==1 for k,n in graph.items() if k.endswith('.Before.Auto'))
    for k,n in graph.items():
        if '.Before.' in k or k.endswith('.Start'):
            assert not any(v.endswith('.Map') for v in n.get('next',[]))
    with pytest.raises(ValueError):campaign_graph('tar007','tar008',15)
    with pytest.raises(ValueError):campaign_graph('tar007','ijp001',100)
    with pytest.raises(ValueError):campaign_graph('tar008','tar007',100)


def prepared():
    return {'view':'prequel_preparation','items':[{'semantic_id':'context','location':'A Rift in the Frustration',
            'preparation_composition_verified':True,'visible_hero_levels':[50],
            'story_title':'One Last Strike','team_cp':33677,'cost':{'currency':'energy','cost':8,'available':781}}],
            'controls':[{'semantic_id':'start_quest','consuming':True,'box':[1030,610,110,25]}]}


def test_start_requires_fresh_same_window_available_map_proof_and_exact_cost():
    now=time.time();window={'hwnd':1,'pid':2,'process_name':'EpicSeven.exe','window_class':'GLFW30','client_size':[1212,682]}
    ticket={'tar007':{'epoch_seconds':now,'window':window}}
    params={'kind':'prequel_start','stage_id':'tar007','max_energy':8}
    assert target(prepared(),params,{'window':window},ticket)==[1030,610,110,25]
    assert target(prepared(),params,{'window':window},{}) is None
    old=deepcopy(ticket);old['tar007']['epoch_seconds']-=31
    assert target(prepared(),params,{'window':window},old) is None
    other={**window,'pid':3}
    assert target(prepared(),params,{'window':other},ticket) is None
    for field,bad in [('story_title','Other stage'),('location','Other location'),('visible_hero_levels',None)]:
        current=prepared();current['items'][0][field]=bad
        assert target(current,params,{'window':window},ticket) is None
    current=prepared();current['items'][0]['cost']['cost']=18
    assert target(current,params,{'window':window},ticket) is None


def test_free_executor_is_one_dispatch_and_never_substitutes_a_paid_summon():
    graph=free_summon_graph('guide_01_006_001')
    actions=[n for n in graph.values() if n['action']!='DoNothing']
    assert len(actions)==1 and actions[0]['max_hit']==1
    with pytest.raises(ValueError):free_summon_graph('guide_29_003_001')


def test_resume_has_zero_starts_and_new_request_cannot_duplicate_reserved_or_finished_entry(tmp_path):
    from driver_epic_seven.attempts import AttemptLedger
    ledger=AttemptLedger(tmp_path/'actions.json',2)
    reserve_entry(ledger,'tar008','first-job',8)
    reserve_entry(ledger,'tar008','first-job',8)
    assert len(ledger.read()['stages']['prequel:tar008'])==1
    for status in ('reserved','sent','victory','returned','defeat'):
        ledger.mark('prequel:tar008','first-job',status)
        with pytest.raises(ValueError):reserve_entry(ledger,'tar008','second-job',8)
    for victory in (False,True):
        graph=finish_graph('tar008',victory)
        assert not any(key.endswith('.Start') for key in graph)
        assert not any(n.get('custom_recognition_param',{}).get('path',{}).get('consuming') for n in graph.values())


def test_explicit_account_profiles_keep_their_entry_journals_separate(tmp_path):
    from driver_epic_seven.attempts import AttemptLedger
    from driver_epic_seven.config import load_config
    journals=[]
    for account in ('stove','steam'):
        profile=tmp_path/(account+'.json')
        profile.write_text(json.dumps({'path_ledger':str(tmp_path/(account+'-actions.json'))}),encoding='utf-8')
        journals.append(AttemptLedger(load_config(str(profile))['path_ledger'],2))
    reserve_entry(journals[0],'tar008','stove-first',8)
    assert journals[1].read()=={'stages':{}}
    reserve_entry(journals[1],'tar008','steam-first',8)
    assert journals[0].read()['stages']['prequel:tar008'][0]['key']=='stove-first'
    with pytest.raises(ValueError):reserve_entry(journals[0],'tar008','stove-second',8)


def test_abyss_unlock_ack_requires_current_heading_body_and_close_together():
    rows=[('Abyss',[564,160,84,34]),
          ('You can enter Abyss.Test your strength in the depths of the Abyss!',[330,370,551,20]),
          ('Tapto close',[554,486,104,20])]
    def read(items):
        data={'state':'unknown','matches':{},'window':{'process_name':'EpicSeven.exe','client_size':[1212,682]},
              'text':[{'text':s,'box':b,'score':.99} for s,b in items]}
        data['ui_tree']=build_tree(data)
        return data
    data=read(rows)
    assert operation_view(data)['view']=='system_unlock_notice'
    assert path_target(data,{'kind':'informational_ack'},None)==[554,486,104,20]
    for missing in range(3):
        assert path_target(read([r for i,r in enumerate(rows) if i!=missing]),
                           {'kind':'informational_ack'},None) is None


@pytest.mark.fixtures
def test_current_own_team_preparation_is_read_without_connecting_or_starting():
    p=ROOT/'var/runs/20261027T225814Z_7e7003d1/path_failure_after.json'
    if not p.exists():pytest.skip('Private current own-team preparation unavailable.')
    data=json.loads(p.read_text(encoding='utf-8'));data.pop('ui_tree',None)
    current=operation_view({'ui_tree':build_tree(data)})
    assert current['view']=='prequel_preparation' and current['mode']=='adventure_own_team'
    assert current['items'][0]['location']=='A Rift in the Frustration'
    assert current['items'][0]['story_title']=='One Last Strike'
    assert current['items'][0]['team_cp']==33677


@pytest.mark.fixtures
def test_observed_episode_three_map_and_episode_two_final_return_share_guarded_reader():
    path=ROOT/'var/runs/20261030T041811Z_874f006c/agent_000020.json'
    if not path.exists():pytest.skip('Private episode three opening map unavailable.')
    data=json.loads(path.read_text(encoding='utf-8'))['result']
    def read(d):return operation_view({'ui_tree':build_tree(d)})
    current=read(data)
    assert current['view']=='prequel_ready_map'
    assert current['items'][0]['episode_label']=='Episode 3'
    assert current['items'][0]['chapter_number']==1
    assert target(current,{'kind':'prequel_ready','stage_id':'lfs001'},data)
    assert target(current,{'kind':'prequel_ready','stage_id':'jer001'},data) is None
    proof={'prequel_victory:dis010':{'window':data['window']}}
    assert target(current,{'kind':'prequel_map_return','stage_id':'dis010'},data,proof)
    assert target(current,{'kind':'prequel_map_return','stage_id':'dis010'},data,{}) is None
    for label in ('Episode 2','Episode 4'):
        wrong=deepcopy(data)
        for r in wrong['text']:
            if r['text']=='Episode 3':r['text']=label
        assert target(read(wrong),{'kind':'prequel_ready','stage_id':'lfs001'},wrong) is None
    plan,graph=campaign_graph('lfs001','lfs010',88)
    assert plan['max_starts']==10 and plan['energy_limit']==88
    assert sum(n.endswith('.Start') for n in graph)==10


@pytest.mark.fixtures
def test_current_boss_map_enemy_panel_keeps_stage_and_return_guards():
    path=ROOT/'var/runs/20261030T045816Z_05101aea/agent_000005.json'
    if not path.exists():pytest.skip('Private episode three boss map unavailable.')
    data=json.loads(path.read_text(encoding='utf-8'))['result']
    def read(d):return operation_view({'ui_tree':build_tree(d)})
    current=read(data)
    assert current['view']=='prequel_ready_map'
    assert current['items'][0]['episode_label']=='Episode 3'
    assert target(current,{'kind':'prequel_ready','stage_id':'lfs005'},data)
    assert target(current,{'kind':'prequel_ready','stage_id':'lfs006'},data) is None
    proof={'prequel_victory:lfs004':{'window':data['window']}}
    assert target(current,{'kind':'prequel_map_return','stage_id':'lfs004'},data,proof)
    for text in ('Enemies','Ready','Story'):
        wrong=deepcopy(data);wrong['text']=[r for r in wrong['text'] if r['text']!=text]
        assert target(read(wrong),{'kind':'prequel_ready','stage_id':'lfs005'},wrong) is None


@pytest.mark.fixtures
def test_native_map_header_glyphs_keep_map_and_episode_guards_over_new_background(tmp_path):
    import numpy as np
    from PIL import Image
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    from driver_epic_seven.vision import Vision
    run=ROOT/'var/admin-campaign-20261030t'
    if not (run/'politis-map-live.json').exists():pytest.skip('Private current map background unavailable.')
    saved=json.loads((run/'politis-map-live.json').read_text(encoding='utf8'))['analysis']
    vision=Vision(ROOT/'resources/epic-seven/vision.json',ROOT/'resources/epic-seven')
    vision.spec['templates']={k:v for k,v in vision.spec['templates'].items()
                             if k in ('map_episode_header','map_ready_label','path_prequel_available')}
    vision.spec['states']={'episode_map':vision.spec['states']['episode_map']};vision.spec['ocr']={}
    found=[]
    class Replay(CustomRecognition):
        def analyze(self,context,argv):
            a={**saved,**vision.inspect(argv.image,lambda n:context.run_recognition(n,argv.image))}
            a['ui_tree']=build_tree(a,vision.spec);found.append(a)
            return self.AnalyzeResult(box=[0,0,1,1],detail=a)
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('MapHeaderGlyphs',Replay())
    assert resource.post_bundle(ROOT/'resources/epic-seven').wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    frame=np.asarray(Image.open(run/'politis-map-live.png').convert('RGB'))[:,:,::-1].copy()
    cases=[('positive',frame,True)]
    cases += [(f'dimmed-{factor}',(frame*factor).astype(np.uint8),False) for factor in (.7,.45)]
    for label,box in [('header',(55,8,180,60)),('ready',(980,590,1140,665))]:
        image=frame.copy();x,y,x2,y2=box;image[y:y2,x:x2]=0;cases.append((label,image,False))
    for label,image,positive in cases:
        assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='MapHeaderGlyphs'),image).wait().succeeded
        a=found[-1];current=operation_view(a)
        assert (target(current,{'kind':'prequel_row','stage_id':'epi004'},a) is not None) is positive,(label,a['state'])
        if positive:
            assert a['state']=='episode_map' and current['items'][0]['chapter_number']==6
            assert target(current,{'kind':'prequel_row','stage_id':'epi005'},a) is None
            proof={'prequel_victory:epi003':{'window':a['window']}}
            assert target(current,{'kind':'prequel_map_return','stage_id':'epi003'},a,proof)
            wrong=deepcopy(a);wrong['text']=[{**r,'text':'Episode 2'} if r['text']=='Episode 3' else r for r in wrong['text']]
            wrong['ui_tree']=build_tree(wrong,vision.spec)
            assert target(operation_view(wrong),{'kind':'prequel_row','stage_id':'epi004'},wrong) is None


def test_supporter_retry_is_bounded_navigation_with_single_start():
    plan,graph=campaign_graph('win002','win002',8)
    prefix='Path.Campaign.win002.'
    supporter=graph[prefix+'Supporter'];start=graph[prefix+'Start']
    assert supporter['max_hit']==2
    assert supporter['next']==[prefix+'Defeat',prefix+'After.SideAlert',prefix+'After.CancelFriend',
                               prefix+'Start',prefix+'Supporter']
    assert supporter['custom_recognition_param']['path']=={'kind':'prequel_supporter','stage_id':'win002'}
    assert start['max_hit']==1 and prefix+'Supporter' not in start['next']
    assert plan['max_starts']==1 and plan['energy_limit']==8


def test_campaign_catalog_includes_six_without_turning_unknown_tile_cost_into_free_story():
    from driver_epic_seven.prequel import campaign_catalog
    catalog=campaign_catalog()
    assert {r['episode'] for r in catalog.values()}==set(range(7))
    assert sum(r['episode']==6 for r in catalog.values())==32
    assert stage('trd001')['title']=='Strange Companion'
    assert stage('ma1002')['title']=='Gospels of the Night'
    assert stage('ma1002')['location']=='Forest of Shadows'
    assert stage('ma1002')['energy']==8
    assert stage('ma1001')['energy']==0 and stage('ma1001')['source_type']=='story'
    stars=json.loads((ROOT/'data/stages/star-requirements.json').read_text(encoding='utf-8'))['stages']
    assert stars['ma1001']['status']=='partial'
    assert all(m['status']=='absent_reference' for m in stars['ma1001']['missions'])
    assert stars['ma1002']['missions'][2]['condition']=='party_enter_role_count'
    assert stars['ma1002']['missions'][2]['parameters']=='enter=ma1002,role=warrior,count=1'
    for identity in ('ma2005','ma3004'):
        assert stage(identity)['source_type']=='tile' and stage(identity)['energy'] is None
        with pytest.raises(ValueError):campaign_graph(identity,identity,100)
    plan,graph=campaign_graph('trd001','trd010',92)
    assert plan['max_starts']==10 and plan['energy_limit']==92
    assert sum(name.endswith('.Start') for name in graph)==10
    plan,graph=campaign_graph('ma1001','ma1001',0)
    assert plan['max_starts']==1 and plan['energy_limit']==0
    starts=[n['custom_recognition_param']['path'] for name,n in graph.items() if name.endswith('.Start')]
    assert len(starts)==1 and starts[0]['kind']=='prequel_story_start' and starts[0]['energy']==0


@pytest.mark.fixtures
def test_episode4_current_map_and_catalog_identity_keep_cross_episode_guards():
    path=ROOT/'var/runs/20261030T192122Z_bd1277b8/agent_000001.json'
    if not path.exists():pytest.skip('Private episode four opening map unavailable.')
    original=json.loads(path.read_text(encoding='utf-8'))['result']
    def read(d):return operation_view({'ui_tree':build_tree(d)})
    current=read(original)
    assert current['view']=='prequel_ready_map'
    assert current['items'][0]['episode_label']=='Episode 4'
    assert current['items'][0]['chapter_number']==1
    assert target(current,{'kind':'prequel_row','stage_id':'trd001'},original)
    assert target(current,{'kind':'prequel_row','stage_id':'lfs001'},original) is None
    for episode in (2,3,5,6):
        wrong=deepcopy(original)
        wrong['text']=[{**r,'text':f'Episode {episode}'} if r['text']=='Episode 4' else r for r in wrong['text']]
        assert read(wrong)['items'][0]['episode_label']==f'Episode {episode}'
        assert target(read(wrong),{'kind':'prequel_row','stage_id':'trd001'},wrong) is None
    for missing in ('Story','Ready','Obtainable Rewards'):
        wrong=deepcopy(original);wrong['text']=[r for r in wrong['text'] if r['text']!=missing]
        assert target(read(wrong),{'kind':'prequel_row','stage_id':'trd001'},wrong) is None
    wrong=deepcopy(original);wrong['matches']['map_episode_header']['hit']=False
    assert target(read(wrong),{'kind':'prequel_row','stage_id':'trd001'},wrong) is None
