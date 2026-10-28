from copy import deepcopy
import pytest

from driver_epic_seven.observed_ui import build_tree, operation_view, query_operation_control, node, fact
from driver_epic_seven.reading import ReadContext
from driver_epic_seven.abyss import target
from test_operational_ui import arena_ready, observation


def test_optional_cp_preserves_panel_control_and_other_current_fields():
    data = arena_ready()
    data['text'] = [r for r in data['text'] if r['text'] != '231,905']
    tree = build_tree(data)
    view = operation_view({'ui_tree': tree})
    assert view['view'] == 'arena_preparation'
    assert view['items'][0]['team_cp'] is None
    assert view['items'][0]['team_instance_id'] is None
    assert view['items'][0]['cost']['cost'] == 1
    found = query_operation_control(tree, 'arena_preparation', 'start')
    assert found['observed'] and found['actionability']['eligible'] is None
    assert 'enabled_unknown' in found['actionability']['blockers']
    assert found['node']['fields']['enabled']['value'] is None


def test_control_resolution_is_scoped_to_parent_and_current_observation():
    tree = build_tree(arena_ready())
    source = {'kind':'derived','pointer':'/text','rule':'test_other_panel'}
    other = node('other', 'panel', tree['root_id'], view=fact('other',source), adapter=fact('operations',source))
    tree['nodes']['other'] = other
    tree['nodes'][tree['root_id']]['children'].append('other')
    button = deepcopy(tree['nodes']['operation:arena_preparation/start'])
    button.update(id='other/start', parent_id='other')
    tree['nodes'][button['id']] = button; other['children'].append(button['id'])
    found = query_operation_control(tree, 'arena_preparation', 'start')
    assert found['node']['parent_id'] == 'operation:arena_preparation'
    with pytest.raises(ValueError, match='outra observação'):
        query_operation_control(tree, 'arena_preparation', 'start', observation_id='stale')


def test_selected_member_overlay_blocks_underlying_preparation():
    data = arena_ready(); data['state'] = 'battle_ready'
    data['matches'] = {'formation_remove': {'hit':True,'box':[218,336,42,19]},
                       'formation_details': {'hit':True,'box':[305,328,38,39]}}
    tree = build_tree(data)
    assert operation_view({'ui_tree':tree}) == {}
    assert query_operation_control(tree,'formation_selection','remove_member')['observed']


def test_abyss_preparation_does_not_require_optional_cp_but_keeps_identity_and_cost():
    current = {'view':'abyss_preparation','items':[{'semantic_id':'context','floor':1,
               'cost':{'currency':'energy','cost':10,'available':20},'team_cp':None}]}
    params = {'kind':'abyss_prepared','stage_id':'abyss001'}
    assert target(current,params,{},None)
    for key in ('floor','cost'):
        altered = deepcopy(current); altered['items'][0][key] = None
        assert target(altered,params,{},None) is None


def test_read_context_filters_invalid_numbers_and_preserves_sources_without_io():
    rows = [('Valid',[1,1,20,10]),('Bad',[1,1,float('nan'),10])]
    data = observation(*rows)
    data['text'].extend([{'text':'bad-score','box':[1,1,20,10],'score':float('nan')},
                         {'text':'bad-score','box':[1,1,20,10],'score':'high'}])
    c = ReadContext(data,'screen',lambda _: pytest.fail('query must not add nodes'))
    row = c.one('Valid')
    assert len(c.rows) == 1 and c.value(row)['sources'][0]['pointer'] == '/text/0'
    assert c.one('Missing') is None and c.value(None) == fact()
