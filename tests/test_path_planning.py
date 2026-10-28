"""Plans never turn static requirements or hidden rows into account progress."""
from copy import deepcopy
import pytest

from driver_epic_seven.path_planning import roadmap, route_level, group_id, plan_level, next_progression
from driver_epic_seven.path_execution import open_path_graph, go_graph, path_target
from driver_epic_seven.observed_ui import build_tree


def heir(counter='3/6'):
    data={'state':'unknown','window':{'process_name':'EpicSeven.exe','client_size':[1212,682]},
          'matches':{},'text':[{'text':t,'box':b,'score':.99} for t,b in (
              ('Orbis Guide',[65,65,140,26]),('Path of Heir',[112,196,86,18]),
              ('Path of Heir 1',[641,65,151,25]),('Group Clear Reward',[700,150,230,25]),
              (counter,[450,177,35,22]),('Receive',[1021,214,63,21]),
              ('Proceed with Covenant Summon',[303,303,236,19]),('Go',[1039,333,21,18]),
              ('0/1',[306,376,27,18]),('X Tap to close',[550,646,110,23]))]}
    data['ui_tree']=build_tree(data)
    return data


def test_full_catalog_is_routed_without_executing_or_inventing_ownership():
    route=roadmap()
    assert route['coverage']['groups']==65 and route['coverage']['catalog_records']==751
    assert 'unmapped' not in route['coverage']['executors_required']
    assert route['coverage']['time_gated_records']==30
    assert all(g['account_progress'] is None and g['boundary']=='agent_checkpoint_after_this_group' for g in route['groups'])
    final=route_level(65)
    assert final['repeat_groups'] and len(final['tasks'])==430
    assert next_progression(65)['next_group'] is None


@pytest.mark.parametrize('level',[0,66,True,1.5,'not-a-level','group_guide_99'])
def test_invalid_levels_fail_before_any_runtime(level):
    with pytest.raises(ValueError):group_id(level)


def test_partial_current_read_keeps_hidden_missions_unknown_and_cannot_complete_level():
    data=heir(); original=deepcopy(data)
    result=plan_level(data,1)
    assert result['status']=='level_in_progress' and result['input_sent'] is False
    assert len(result['not_visible_tasks'])==5
    task=next(t for t in result['tasks'] if t['task_id']=='guide_01_006_001')
    assert task['status']=='incomplete' and task['counter']=={'current':0,'total':1}
    assert data==original
    with pytest.raises(ValueError):plan_level(data,2)


def test_complete_current_group_yields_agent_checkpoint_not_automatic_next_group():
    result=plan_level(heir('6/6'),1)
    assert result['status']=='agent_checkpoint'
    assert result['group_claimed'] is False
    assert result['progression_after_group']['next_group']=='group_guide_02'
    assert any(x['executor']=='hero_level' and x['parameters']['level']=='15'
               for x in result['progression_after_group']['requirements'])
    assert result['milestone_after_group']['max_chests_per_checkpoint']==3


def test_native_graph_has_only_guarded_finite_navigation_and_no_battle_or_claim():
    graph=open_path_graph()
    assert graph['Path.Open.Entry']['action']=='DoNothing'
    for name,node in graph.items():
        if node['action']!='DoNothing':
            assert node['recognition']=='Custom' and node['max_hit'] in (1,2,4)
            assert node['custom_recognition_param']['path']['kind'] in ('navigation','mapped_back')
    summon=go_graph('group_guide_01','guide_01_006_001','summon')
    assert summon['Path.Go.Click']['max_hit']==1
    assert go_graph('group_guide_01','guide_01_004_001','spirit_altar')['Path.Go.Done']['custom_recognition_param']['path']['view']=='spirit_altar_hub'
    assert 'abyss_floors' in go_graph('group_guide_02','guide_02_005_001','abyss')['Path.Go.Done']['custom_recognition_param']['path']['views']


def test_no_current_path_is_not_a_static_progress_fallback():
    assert plan_level({'ui_tree':build_tree({'state':'unknown'})})['status']=='needs_path_read'
