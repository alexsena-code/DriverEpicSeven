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


def test_chapter_six_candidates_keep_episode_and_identity():
    first = stage('taw002')
    assert (first['episode'], first['chapter'], first['ordinal']) == (1, 6, 1)
    assert (first['title'], first['location'], first['energy']) == ('A Brazen Knight', 'Declaration Field', 8)
    plan, graph = campaign_graph('taw002', 'tae010', 64)
    assert plan['energy_limit'] == 64 and plan['max_starts'] == 8
    assert sum(name.endswith('.Start') for name in graph) == 8


def test_episode_four_story_uses_resolved_zero_cost_and_no_battle_start():
    record=stage('kae003')
    assert record['energy']==0 and record['source_type']=='story'
    assert record['energy_source']['use_enterpoint']=='0'
    plan,graph=campaign_graph('kae003','kae003',0)
    assert plan['energy_limit']==0
    start=graph['Path.Campaign.kae003.Start']['custom_recognition_param']['path']
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
