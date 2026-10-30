"""A new identity alone cannot turn uncertainty or defeat into unlimited replay."""
from copy import deepcopy
import time
import pytest
from driver_epic_seven.contracts import Identity,Status
from driver_epic_seven.retries import check_retry
from test_operation_cycle import context,WINDOW


def entries():
    return [{'key':'old','status':'defeat','result_status':'defeat','cost':10,
             'identity':Identity('goal','plan','operation','old').as_dict(),
             'events':[{'phase':'defeat','proof':{'observation_id':'defeat-image','window':WINDOW}}]}]


def policy():return {'previous_attempt_id':'old','max_attempts':2,'max_total_cost':20,'deadline_epoch_seconds':time.time()+300}


def test_explicit_defeat_permit_is_new_finite_and_same_plan():
    result=check_retry(entries(),Identity('goal','plan','next-operation','new'),policy(),10,WINDOW)
    assert result['defeat_observation_id']=='defeat-image' and result['max_attempts']==2


@pytest.mark.parametrize('changed',[None,'missing_plan','wrong_plan','wrong_stage','unknown','victory','count','budget','goal','attempt','same_plan'])
def test_explicit_new_defeat_plan_carries_stage_history_without_resetting_attempts(changed):
    rows=entries();rows[0]['events'][0]['proof']['target']={'stage_id':'lfs010'}
    p={**policy(),'kind':'defeat_new_plan','previous_plan_id':'plan','stage_id':'lfs010',
       'max_attempts':3,'max_total_cost':30}
    identity=Identity('goal','new-finite-plan','op','new')
    if changed=='missing_plan':p.pop('previous_plan_id')
    if changed=='wrong_plan':p['previous_plan_id']='other'
    if changed=='wrong_stage':p['stage_id']='lfs009'
    if changed in ('unknown','victory'):rows[0].update(status=changed,result_status=changed)
    if changed=='count':rows=rows*3
    if changed=='budget':p['max_total_cost']=19
    if changed=='goal':identity=Identity('other','new-finite-plan','op','new')
    if changed=='attempt':identity=Identity('goal','new-finite-plan','op','old')
    if changed=='same_plan':identity=Identity('goal','plan','op','new')
    if changed is not None:
        with pytest.raises(ValueError):check_retry(rows,identity,p,10,WINDOW)
    else:
        result=check_retry(rows,identity,p,10,WINDOW)
        assert result['kind']=='defeat_new_plan' and result['previous_plan_id']=='plan'
        assert result['stage_id']=='lfs010' and result['max_attempts']==3


@pytest.mark.parametrize('outcome',['reserved','sent','entered','returned','victory','cancelled','uncertain','less_than_three_stars'])
def test_non_defeat_does_not_authorize_retry(outcome):
    rows=entries();rows[0].update(status=outcome,result_status=outcome)
    with pytest.raises(ValueError):check_retry(rows,Identity('goal','plan','op','new'),policy(),10,WINDOW)


@pytest.mark.parametrize('changed',['identity','plan','window','proof','count','budget','deadline','same_attempt','legacy_cost'])
def test_all_retry_limits_and_proof_are_required(changed):
    rows=entries();p=policy();identity=Identity('goal','plan','op','new');window=WINDOW
    if changed=='identity':p['previous_attempt_id']='other'
    if changed=='plan':identity=Identity('goal','different','op','new')
    if changed=='window':window={**WINDOW,'pid':3}
    if changed=='proof':rows[0]['events']=[]
    if changed=='count':p['max_attempts']=1
    if changed=='budget':p['max_total_cost']=19
    if changed=='deadline':p['deadline_epoch_seconds']=time.time()-1
    if changed=='same_attempt':identity=Identity('goal','plan','op','old')
    if changed=='legacy_cost':rows[0]['cost']=None
    with pytest.raises(ValueError):check_retry(rows,identity,p,10,window)


def test_retry_is_persisted_before_send_and_cannot_repeat_or_change_scope(tmp_path):
    r,cycle,data,_=context(tmp_path);r.path_attempts.limit=2
    r.execution_identity=Identity('goal','plan','old-operation','old')
    params={'path':{'kind':'abyss_start','stage_id':'abyss032','task_id':'goal-scope','energy':10,'consuming':True}}
    assert cycle.dispatch('start',params,data,lambda:True)
    cycle._mark(r.path_attempts,'goal-scope','defeat',Status.DEFEAT,cycle.proof(data,'result'))
    r.execution_identity=Identity('goal','plan','new-operation','new');r.execution_retry=policy()
    def send():
        row=r.path_attempts.read()['stages']['goal-scope'][-1]
        assert row['status']=='reserved' and row['events'][0]['proof']['retry_authorization']['previous_attempt_id']=='old'
        return True
    assert cycle.dispatch('retry',params,data,send)
    with pytest.raises(ValueError):cycle.dispatch('repeat',params,data,lambda:pytest.fail('repeated Start'))
    other=deepcopy(params);other['path']['task_id']='new-scope'
    with pytest.raises(ValueError):cycle.dispatch('renamed-scope',other,data,lambda:pytest.fail('pending Start bypassed'))


def test_new_defeat_plan_persists_link_and_cannot_reset_three_entry_ceiling(tmp_path):
    r,cycle,data,_=context(tmp_path);r.path_attempts.limit=3
    params={'path':{'kind':'abyss_start','stage_id':'abyss032','task_id':'boss','energy':10,'consuming':True}}
    r.execution_identity=Identity('goal','expired-plan','op','first')
    assert cycle.dispatch('first',params,data,lambda:True)
    proof={**cycle.proof(data,'result'),'target':{'stage_id':'abyss032'}}
    cycle._mark(r.path_attempts,'boss','defeat',Status.DEFEAT,proof)
    r.execution_identity=Identity('goal','new-plan','op','second')
    r.execution_retry={**policy(),'kind':'defeat_new_plan','previous_plan_id':'expired-plan',
                       'stage_id':'abyss032','previous_attempt_id':'first','max_attempts':3,'max_total_cost':30}
    def second_send():
        rows=r.path_attempts.read()['stages']['boss']
        assert len(rows)==2 and rows[0]['identity']['plan_id']=='expired-plan'
        permit=rows[-1]['events'][0]['proof']['retry_authorization']
        assert permit['previous_plan_id']=='expired-plan' and permit['kind']=='defeat_new_plan'
        return True
    assert cycle.dispatch('second',params,data,second_send)
    cycle._mark(r.path_attempts,'boss','defeat',Status.DEFEAT,proof)
    r.execution_identity=Identity('goal','new-plan','op','third')
    r.execution_retry={**policy(),'previous_attempt_id':'second','max_attempts':3,'max_total_cost':30}
    assert cycle.dispatch('third',params,data,lambda:True)
    cycle._mark(r.path_attempts,'boss','defeat',Status.DEFEAT,proof)
    r.execution_identity=Identity('goal','another-plan','op','fourth')
    r.execution_retry={**policy(),'kind':'defeat_new_plan','previous_plan_id':'new-plan',
                       'stage_id':'abyss032','previous_attempt_id':'third','max_attempts':3,'max_total_cost':40}
    with pytest.raises(ValueError):cycle.dispatch('fourth',params,data,lambda:pytest.fail('Fourth Start'))
    rows=r.path_attempts.read()['stages']['boss']
    assert len(rows)==3 and sum(row['cost'] for row in rows)==30


@pytest.mark.parametrize('family,stage',[('altar','cmon002'),('abyss','abyss032')])
def test_defeat_reaches_public_path_target_without_preparation_or_cp(family,stage):
    from driver_epic_seven.path_execution import path_target
    from driver_epic_seven.observed_ui import build_tree
    d={'state':'battle_failed','window':{'client_size':[1212,682]}}
    d['ui_tree']=build_tree(d)
    assert path_target(d,{'kind':family+'_defeat','stage_id':stage,'floor':32,'mode':'normal'},None,{})==[0,0,1,1]
    for state in ('unknown','stage_clear','battle_running'):
        d={'state':state,'window':{'client_size':[1212,682]}};d['ui_tree']=build_tree(d)
        assert path_target(d,{'kind':family+'_defeat','stage_id':stage,'floor':32,'mode':'normal'},None,{}) is None
