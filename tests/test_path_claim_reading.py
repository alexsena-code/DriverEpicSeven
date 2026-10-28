"""Ready-to-claim render is distinct from a readable objective counter."""
from copy import deepcopy

import pytest

from driver_epic_seven.observed_ui import build_tree, quest_view, query_control, field_value


def heir(*, control='Receive', counter=None, label_y=303, group='3/6', native=True):
    rows=[('Orbis Guide',[64,65,141,26]),('Path of Heir',[112,196,84,18]),
          ('Path of Heir 1',[641,65,151,25]),('Group Clear Reward',[665,154,160,17]),
          (group,[430,171,49,29]),('Receive',[1021,214,63,21]),
          ('Proceed with Covenant Summon',[303,label_y,234,19]),
          (control,[1020,label_y+26,64,25]),('X Tap to close',[549,646,111,23])]
    if counter:rows.append((counter,[502,label_y+76,29,15]))
    data={'state':'unknown','window':{'process_name':'EpicSeven.exe','client_size':[1212,682]},
          'text':[{'text':t,'box':b,'score':.99} for t,b in rows],
          'matches':{'path_receive_row_1':{'hit':native,'box':[1003,label_y+18,112,39],'score':.99}}}
    return data


def read(data):
    tree=build_tree(data)
    return tree,quest_view({'ui_tree':tree})


@pytest.mark.parametrize('process',['EpicSeven.exe','EpicSeven_Steam.exe'])
def test_active_receive_can_be_ready_while_counter_and_satisfaction_stay_unknown(process):
    data=heir();data['window']['process_name']=process;original=deepcopy(data)
    tree,view=read(data);task=view['visible_tasks'][0]
    assert task['counter'] is None and task['condition_satisfied'] is None and task['status']=='unknown'
    assert task['claim_ready'] is True and task['claim_control_box']==[1003,321,112,39]
    control=query_control(tree,'group_guide_01','guide_01_006_001','claim')['node']
    assert field_value(control,'enabled') is None and field_value(control,'box_role')=='template_extent'
    assert field_value(control,'label_box')==[1020,329,64,25]
    assert any(s['pointer']=='/matches/path_receive_row_1' for s in control['fields']['claim_ready']['sources'])
    assert data==original


@pytest.mark.parametrize('change', ['absent','wrong_row','wrong_x','multiple','invalid_box','dimmed'])
def test_label_without_one_valid_current_marker_cannot_prove_readiness(change):
    data=heir()
    marker=data['matches']['path_receive_row_1']
    if change in ('absent','dimmed'):marker['hit']=False
    elif change=='wrong_row':marker['box'][1]+=123
    elif change=='wrong_x':marker['box'][0]=850
    elif change=='multiple':data['matches']['path_receive_row_2']={'hit':True,'box':[1002,320,114,41],'score':.99}
    elif change=='invalid_box':marker['box'][2]=float('nan')
    if change=='invalid_box':
        with pytest.raises(ValueError,match='Caixa fora'):
            read(data)
        return
    _,view=read(data);task=view['visible_tasks'][0]
    assert task['claim_ready'] is None and task['claim_control_box'] is None


def test_cut_row_or_conflicting_counter_does_not_accept_an_active_marker():
    _,view=read(heir(label_y=551))
    task=view['visible_tasks'][0]
    assert task['row_fully_visible'] is False and task['claim_ready'] is None
    _,view=read(heir(counter='0/1'))
    task=view['visible_tasks'][0]
    assert task['condition_satisfied'] is False and task['claim_ready'] is None


def test_explicit_incomplete_and_claimed_rows_are_not_ready():
    for control,counter in [('Go','0/1'),('Received',None),('Completed',None)]:
        _,view=read(heir(control=control,counter=counter,native=False))
        assert view['visible_tasks'][0]['claim_ready'] is False
        assert view['visible_tasks'][0]['claim_control_box'] is None


def test_group_ready_control_requires_full_counter_and_its_own_native_marker():
    data=heir(group='6/6',native=False)
    _,view=read(data)
    assert view['group_claim_ready'] is True  # Existing counter-derived semantic fact.
    assert view['group_claim_control_ready'] is None
    data['matches']['path_receive_group']={'hit':True,'box':[1003,205,112,39],'score':.99}
    tree,view=read(data)
    assert view['group_claim_control_ready'] is True and view['group_receive_box']==[1003,205,112,39]
    control=query_control(tree,'group_guide_01',None,'claim_group')['node']
    assert field_value(control,'enabled') is None
    data['text'][4]['text']='3/6'
    _,view=read(data)
    assert view['group_claim_control_ready'] is False


def test_claimed_check_requires_same_fully_visible_row_and_complete_counter():
    data=heir(counter='1/1',native=False)
    data['text']=[r for r in data['text'] if not (r['text']=='Receive' and r['box'][1]>285)]
    data['matches']['path_claimed_row_1']={'hit':True,'box':[1037,331,30,23],'score':.99}
    tree,current=read(data);task=current['visible_tasks'][0]
    assert task['status']=='claimed' and task['claim_ready'] is False
    assert task['claimed_tick_box']==[1037,331,30,23] and task['claim_control_box'] is None
    receipt=query_control(tree,'group_guide_01','guide_01_006_001','receipt')['node']
    assert field_value(receipt,'enabled') is None
    for bad in ('counter','row'):
        changed=deepcopy(data)
        if bad=='counter':changed['text']=[r for r in changed['text'] if r['text']!='1/1']
        else:changed['matches']['path_claimed_row_1']['box'][1]+=123
        _,current=read(changed)
        assert current['visible_tasks'][0]['status']=='unknown'
        assert current['visible_tasks'][0]['claimed_tick_box'] is None


def test_next_group_arrow_has_a_static_hint_without_claim_or_unlock_inference():
    data=heir();data['matches']['path_group_next']={'hit':True,'box':[1064,58,41,41],'score':.99}
    tree,current=read(data)
    control=tree['nodes']['panel:orbis/next_group']
    assert field_value(control,'semantic_id')=='orbis_next_group'
    assert field_value(control,'consuming') is False and field_value(control,'enabled') is None
    assert field_value(control,'destination_group_id_hint')=='group_guide_02'
    assert field_value(control,'destination_group_unlocked') is None
    assert current['group_counter']=={'current':3,'total':6} and current['group_claimed'] is False
    data['matches']['path_group_next']['box'][0]=900
    tree,_=read(data)
    assert 'panel:orbis/next_group' not in tree['nodes']
