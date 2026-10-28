from copy import deepcopy

import pytest

from driver_epic_seven.observed_ui import build_tree, operation_view
from driver_epic_seven.path_execution import path_target, acknowledge_graph


@pytest.mark.parametrize('counter', ['3/28','3 /28','3 / 28'])
def test_checkin_reuses_composed_notice_and_nonconsuming_confirmation(counter):
    rows=[('Collaboration Check-in Reward!', [140,50,565,46]),
          ('Rewards Received: '+counter,[905,559,226,21]),('Confirm',[977,615,75,25])]
    def observation(values):
        data={'state':'unknown','matches':{},'window':{'process_name':'EpicSeven.exe','client_size':[1212,682]},
              'text':[{'text':t,'box':b,'score':.99} for t,b in values]}
        data['ui_tree']=build_tree(data)
        return data
    data=observation(rows)
    assert operation_view(data)['view']=='checkin_notice'
    assert path_target(data,{'kind':'informational_ack','view':'checkin_notice'},None)==[977,615,75,25]
    for missing in range(3):
        assert path_target(observation([r for i,r in enumerate(rows) if i!=missing]),
                           {'kind':'informational_ack','view':'checkin_notice'},None) is None
    assert path_target(data,{'kind':'informational_ack','view':'received_reward'},None) is None
    covered=deepcopy(data)
    covered['text'].append({'text':'Confirm','box':[1080,615,75,25],'score':.99})
    covered['ui_tree']=build_tree(covered)
    assert path_target(covered,{'kind':'informational_ack','view':'checkin_notice'},None) is None


def test_acknowledge_never_retries_or_accepts_consuming_confirmations():
    graph=acknowledge_graph('checkin_notice','lobby')
    actions=[n for n in graph.values() if n['action']!='DoNothing']
    assert len(actions)==1 and actions[0]['max_hit']==1
    assert graph['Path.Acknowledge.Done']['custom_recognition_param']['path']['view']=='lobby'
    for view in ('mail_receive_confirmation','formation_auto_assign','equipment_change_confirmation','unknown'):
        with pytest.raises(ValueError):acknowledge_graph(view,'lobby')


def test_recovery_checks_destination_first_and_only_reuses_finite_navigation():
    from driver_epic_seven.path_execution import recovery_graph
    graph=recovery_graph('group_guide_02','guide_02_001_001','campaign')
    assert graph['Path.Recover.Entry']['next'][0]=='Path.Recover.Done'
    assert graph['Path.Open.Done']['next']==['Path.Go.Entry']
    assert graph['Path.Go.Done']['next']==['Path.Recover.Done']
    for item in graph.values():
        if item['action']!='DoNothing':
            params=item['custom_recognition_param']['path']
            assert params['kind'] in ('navigation','mission_go','informational_ack','mapped_back')
            assert not params.get('consuming') and item['max_hit']<=4
    for group,task,executor in [('group_guide_01','guide_02_001_001','campaign'),
                              ('group_guide_02','guide_02_001_001','summon'),
                              ('group_guide_02','guide_02_005_001','unsupported')]:
        with pytest.raises(ValueError):recovery_graph(group,task,executor)


def test_new_player_checkin_success_is_content_not_a_new_confirmation_executor():
    rows=[('New Player Check-In Event',[107,48,353,29]),('Success!',[936,501,127,26]),
          ('All rewards will be sent to your mailbox.Once you receive all the',[99,566,451,19]),
          ('Confirm',[960,586,73,23])]
    def read(values):
        data={'state':'unknown','matches':{},'window':{'process_name':'EpicSeven.exe','client_size':[1212,682]},
              'text':[{'text':t,'box':b,'score':.99} for t,b in values]}
        data['ui_tree']=build_tree(data)
        return data
    data=read(rows)
    assert operation_view(data)['mode']=='new_player'
    assert path_target(data,{'kind':'informational_ack','view':'checkin_notice'},None)==[960,586,73,23]
    for missing in range(4):
        assert path_target(read([r for i,r in enumerate(rows) if i!=missing]),
                           {'kind':'informational_ack','view':'checkin_notice'},None) is None


def test_claim_receipt_proves_reordered_task_without_inventing_a_claim_from_counter(monkeypatch):
    from driver_epic_seven import path_claims
    window={'hwnd':1,'pid':2}
    observation={'window':window}
    params={'kind':'claim_done','group_id':'group_guide_02','mission_id':'guide_02_002_001',
            'before_count':0,'total':5}
    current={'group_id':'group_guide_02','group_counter':{'current':1,'total':5},'visible_tasks':[]}
    monkeypatch.setattr(path_claims,'quest_view',lambda _:current)
    assert path_claims.target(observation,params,{}) is None
    ticket={'window':window,'mission_id':params['mission_id'],'before_count':0}
    proof={'mission_receipt:group_guide_02':ticket}
    assert path_claims.target(observation,params,proof)==[0,0,1,1]
    for key,bad in [('window',{'hwnd':1,'pid':3}),('mission_id','other'),('before_count',1)]:
        assert path_claims.target(observation,params,{'mission_receipt:group_guide_02':{**ticket,key:bad}}) is None
    current['group_counter']['current']=0
    assert path_claims.target(observation,params,proof) is None


def test_free_prequel_uses_exact_current_description_and_requires_story_before_return():
    from driver_epic_seven.prequel import stage,target,campaign_graph,finish_graph
    expected=stage('ijp001')
    current={'view':'prequel_story_map','items':[
        {'semantic_id':'context','chapter_number':4,'episode_label':'6th World Episode',
         'selected_kind_label':'Story','selected_description':expected['map_description']},
        {'semantic_id':'view_story_label','text':'View Story','box':[1003,611,97,30]}]}
    params={'kind':'prequel_story_start','stage_id':'ijp001'}
    assert target(current,params)==[1003,611,97,30]
    for key,value in [('chapter_number',3),('selected_description','Other story'),('selected_kind_label','Battle')]:
        changed=deepcopy(current);changed['items'][0][key]=value
        assert target(changed,params) is None
    assert target(current,{'kind':'prequel_story_start','stage_id':'ijp002'}) is None
    done={'kind':'prequel_story_done','stage_id':'ijp001'}
    window={'hwnd':1,'pid':2}
    assert target(current,done,{'window':window},{}) is None
    assert target(current,done,{'window':window},{'story_seen:ijp001':{'window':window}})==[0,0,1,1]
    assert target(current,done,{'window':{'pid':3}},{'story_seen:ijp001':{'window':window}}) is None
    plan,graph=campaign_graph('ijp001','ijp003',16)
    assert plan['energy_limit']==16
    assert graph['Path.Campaign.ijp001.Start']['max_hit']==1
    assert not any('.ijp001.Clear'==key.removeprefix('Path.Campaign') for key in graph)
    resume=finish_graph('ijp001')
    assert not any(key.endswith('.Start') for key in resume)


@pytest.mark.fixtures
def test_diary_reuses_one_heir_control_and_can_open_calibrated_tab():
    import json
    from driver_epic_seven.config import ROOT
    from driver_epic_seven.observed_ui import field_value
    path=ROOT/'var/runs/20261028T090734Z_53771754/agent_000003.json'
    if not path.exists():pytest.skip('Private Diary observation unavailable.')
    # The immutable response contains the actual captured tree, not a mutable alias.
    tree=json.loads(path.read_text(encoding='utf-8'))['snapshot']['snapshot']['ui_tree']
    # Rebuild from the native failure observation preserved before any next request.
    observation_path=ROOT/'var/group2-live/diary-before-control-dedup.json'
    if not observation_path.exists():pytest.skip('Private native Diary evidence unavailable.')
    data=json.loads(observation_path.read_text(encoding='utf-8'))
    data['ui_tree']=build_tree(data)
    controls=[n for n in data['ui_tree']['nodes'].values()
              if n['kind']=='control' and field_value(n,'semantic_id')=='orbis_heir_tab']
    assert len(controls)==1
    assert path_target(data,{'kind':'navigation','view':'orbis_guide','control':'orbis_heir_tab'},None)==[112,196,86,18]


@pytest.mark.fixtures
def test_own_team_preparation_has_one_panel_even_when_generic_ready_also_matches():
    import json
    from driver_epic_seven.config import ROOT
    path=ROOT/'var/group2-live/ijp006-preparation-before-composition-fix.json'
    if not path.exists():pytest.skip('Private own-team preparation unavailable.')
    data=json.loads(path.read_text(encoding='utf-8'))
    for state in ('unknown','battle_ready'):
        current=deepcopy(data);current['state']=state;current['ui_tree']=build_tree(current)
        view=operation_view(current)
        assert view['view']=='prequel_preparation'
        assert view['items'][0]['story_title']=='An Invitation to Despair'
        assert view['items'][0]['cost']['cost']==8
        for missing in ('The Deepest Darkness','An Invitation to Despair'):
            negative=deepcopy(current);negative['text']=[r for r in negative['text'] if r['text']!=missing]
            negative['ui_tree']=build_tree(negative)
            assert operation_view(negative).get('view')!='prequel_preparation'


@pytest.mark.fixtures
def test_artifact_tutorial_reuses_native_skip_and_hides_underlying_map():
    import json
    from driver_epic_seven.config import ROOT
    path=ROOT/'var/group2-live/artifact-tutorial-before-reuse.json'
    if not path.exists():pytest.skip('Private artifact tutorial unavailable.')
    data=json.loads(path.read_text(encoding='utf-8'));data['ui_tree']=build_tree(data)
    assert operation_view(data)['view']=='tutorial'
    assert path_target(data,{'kind':'informational_ack','view':'tutorial'},None)==[1040,19,125,28]
    for missing in ('instruction','button'):
        altered=deepcopy(data)
        if missing=='instruction':altered['text']=[r for r in altered['text'] if 'acquired Artifact' not in r['text']]
        else:altered['matches']['tutorial_skip']['hit']=False
        altered['ui_tree']=build_tree(altered)
        assert path_target(altered,{'kind':'informational_ack','view':'tutorial'},None) is None


def test_equipment_mission_uses_only_declared_glyph_words_and_current_group():
    from driver_epic_seven.quests import mission_label_key
    assert mission_label_key('Eguip any Hero with Eguipment')==mission_label_key('Equip any Hero with Equipment')
    for other in ('Eguip any Hero with Artifact','Equip all Heroes with Equipment','Equlp any Hero with Equipment'):
        assert mission_label_key(other)!=mission_label_key('Equip any Hero with Equipment')


def test_one_team_corrected_attempt_requires_explicit_reconciliation_and_same_current_party(tmp_path,monkeypatch):
    from driver_epic_seven.attempts import AttemptLedger
    from driver_epic_seven.prequel import reserve_entry,corrected_team_retry
    from driver_epic_seven import observed_ui
    ledger=AttemptLedger(tmp_path/'attempts.json',2)
    reserve_entry(ledger,'ijp007','first',8)
    assert not corrected_team_retry(ledger.read()['stages']['prequel:ijp007'])
    data=ledger.read();first=data['stages']['prequel:ijp007'][0]
    first.update(status='blocked_team',team_correction={'user_confirmed':True,'owned_hero':'Arbiter Vildred',
        'expected_cp':70050,'energy_balance':977,'window':{'pid':1},'evidence':['native-before-and-after']})
    ledger.save(data)
    current={'view':'prequel_preparation','items':[{'semantic_id':'context','team_cp':70050,'cost':{'available':977}}]}
    monkeypatch.setattr(observed_ui,'operation_view',lambda _:current)
    for observation in ({'window':{'pid':2}},{}):
        with pytest.raises(ValueError):reserve_entry(ledger,'ijp007','corrected',8,observation)
    current['items'][0]['team_cp']=45650
    with pytest.raises(ValueError):reserve_entry(ledger,'ijp007','corrected',8,{'window':{'pid':1}})
    current['items'][0]['team_cp']=70050
    reserve_entry(ledger,'ijp007','corrected',8,{'window':{'pid':1}})
    assert len(ledger.read()['stages']['prequel:ijp007'])==2
    with pytest.raises(ValueError):reserve_entry(ledger,'ijp007','third',8,{'window':{'pid':1}})
