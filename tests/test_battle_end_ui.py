"""Result footer outranks a retained combat HUD without inventing victory."""
from copy import deepcopy

import pytest

from driver_epic_seven.observed_ui import build_tree, operation_view, screen_state


def footer():
    return {'state':'battle_running','window':{'process_name':'EpicSeven.exe','client_size':[1212,682]},
            'matches':{'path_battle_exit_lobby':{'hit':True,'box':[187,600,130,55],'score':.99},
                       'battle_help':{'hit':True,'box':[934,13,39,39],'score':.99},
                       'battle_pause':{'hit':True,'box':[1160,12,34,35],'score':.99}},
            'text':[{'text':text,'box':box,'score':.99} for text,box in (
                ('Next Difficulty',[1059,547,111,25]),('10/837',[975,549,64,22]),
                ('Lobby',[222,610,59,30]),('Try again',[1074,613,86,28]),
                ('Leave',[92,615,56,23]),('9/837',[978,615,55,23]))]}


def view(data):return operation_view({'ui_tree':build_tree(data)})


@pytest.mark.parametrize('process',['EpicSeven.exe','EpicSeven_Steam.exe'])
def test_exit_operation_takes_precedence_over_raw_running_hud_and_keeps_outcome_unknown(process):
    data=footer();data['window']['process_name']=process;original=deepcopy(data);tree=build_tree(data);current=operation_view({'ui_tree':tree})
    assert screen_state({'ui_tree':tree})=='battle_running'
    assert current['view']=='battle_exit' and current['mode'] is None
    context=current['items'][0]
    assert all(context[key] is None for key in ('outcome','mode_identity','stage_id','battle_id','victory_announced','mission_credit'))
    assert context['repeat_cost']=={'currency':None,'cost':9,'available':837}
    assert context['next_difficulty_cost']=={'currency':None,'cost':10,'available':837}
    controls={c['semantic_id']:c for c in current['controls']}
    assert controls['lobby']['consuming'] is False and controls['leave']['consuming'] is False
    assert controls['lobby']['box']==[187,600,130,55] and controls['lobby']['navigation_destinations']==[{'view':'lobby'}]
    assert controls['next_difficulty']['consuming'] is True and controls['try_again']['consuming'] is True
    assert controls['try_again']['cost']==context['repeat_cost']
    assert all(c['enabled'] is None for c in controls.values()) and data==original


@pytest.mark.parametrize('missing',['Lobby','Leave','Next Difficulty','Try again','10/837','9/837'])
def test_each_label_and_ratio_is_required_to_identify_footer(missing):
    data=footer();data['text']=[r for r in data['text'] if r['text']!=missing]
    assert view(data).get('view')!='battle_exit'


@pytest.mark.parametrize('mutation',['dim','wrong_box','duplicate_cost','wrong_window','overlay'])
def test_unproven_or_occluded_footer_cannot_expose_result_navigation(mutation):
    data=footer()
    if mutation=='dim':data['matches']['path_battle_exit_lobby']['hit']=False
    elif mutation=='wrong_box':data['matches']['path_battle_exit_lobby']['box'][0]=10
    elif mutation=='duplicate_cost':data['text'].append({'text':'8/837','box':[975,614,55,23],'score':.99})
    elif mutation=='wrong_window':data['window']['process_name']='Other.exe'
    else:data['text'].append({'text':'X Tap to close','box':[550,645,110,24],'score':.99})
    assert view(data).get('view')!='battle_exit'
