from copy import deepcopy
import time
import pytest
from driver_epic_seven.contracts import Identity
from driver_epic_seven.retries import check_uncertain_retry
from driver_epic_seven.plans import resume_campaign
from test_operation_cycle import WINDOW


def prior():
    return [{'key':'old','status':'sent','cost':8,
             'identity':Identity('goal','old-plan','old-operation','old').as_dict(),
             'events':[{'phase':'dispatch_accepted','proof':{'window':WINDOW}},
                       {'phase':'patch_interruption_observed','proof':{'result':'unknown',
                           'patch_observation':'patch.json','current_map_observation':'map.json',
                           'current_map_observation_id':'map-id'}}]}]


def permit():
    return {'kind':'uncertain','stage_id':'tae009','previous_attempt_id':'old',
            'max_attempts':2,'max_total_cost':16,'deadline_epoch_seconds':time.time()+300}


def test_explicit_uncertain_retry_keeps_history_and_finite_limits():
    p=check_uncertain_retry(prior(),Identity('goal','new-plan','new-operation','new'),permit(),8,WINDOW,'tae009')
    assert p['kind']=='uncertain' and p['previous_attempt_id']=='old' and p['max_total_cost']==16


@pytest.mark.parametrize('changed',['no_policy','stage','window','event','victory','defeat','attempt','objective','count','budget','deadline'])
def test_uncertain_retry_refuses_missing_proof_or_limit(changed):
    entries=prior();policy=permit();identity=Identity('goal','new-plan','op','new');window=WINDOW
    if changed=='no_policy':policy={}
    if changed=='stage':policy['stage_id']='tae010'
    if changed=='window':window={**WINDOW,'pid':999}
    if changed=='event':entries[0]['events'].pop()
    if changed in ('victory','defeat'):entries[0]['result_status']=changed
    if changed=='attempt':identity=Identity('goal','new-plan','op','old')
    if changed=='objective':identity=Identity('other','new-plan','op','new')
    if changed=='count':policy['max_attempts']=1
    if changed=='budget':policy['max_total_cost']=15
    if changed=='deadline':policy['deadline_epoch_seconds']=time.time()-1
    with pytest.raises(ValueError):check_uncertain_retry(entries,identity,policy,8,window,'tae009')


def test_unknown_attempt_only_gets_start_in_explicit_stage_scoped_plan():
    entries={'prequel:tae009':prior()}
    _, safe, _, _=resume_campaign('tae009','tae010',16,entries)
    assert not any('.tae009.Start' in name for name in safe)
    _, authorized, _, _=resume_campaign('tae009','tae010',16,entries,uncertain_retry_stage='tae009')
    assert sum('.tae009.Start' in name for name in authorized)==1


def test_retry_reservation_preserves_uncertain_attempt_and_is_single_use(tmp_path):
    from test_operation_cycle import context
    runtime, cycle, observation, _ = context(tmp_path)
    runtime.path_battles.save({'stages': {'prequel:tae009': prior()}})
    runtime.execution_identity = Identity('goal','new-plan','op','new')
    runtime.execution_retry = permit()
    params = {'path': {'kind':'prequel_start','stage_id':'tae009','energy':8,'consuming':True}}
    def send():
        rows=runtime.path_battles.read()['stages']['prequel:tae009']
        assert rows[0]['status']=='sent' and rows[0].get('result_status') is None
        assert rows[1]['status']=='reserved'
        assert rows[1]['events'][0]['proof']['retry_authorization']['kind']=='uncertain'
        return True
    assert cycle.dispatch('retry',params,observation,send)
    with pytest.raises(ValueError):
        cycle.dispatch('retry-again',params,observation,lambda:pytest.fail('duplicate start'))


def test_third_attempt_requires_current_uncertain_evidence_and_stops_at_three():
    rows=prior()
    rows.append({'key':'second','status':'sent','cost':8,
                 'identity':Identity('goal','plan2','op2','second').as_dict(),
                 'events':[{'phase':'dispatch_accepted','proof':{'window':WINDOW}},
                           {'phase':'uncertain_result_observed','proof':{'result':'unknown','window':WINDOW,
                               'current_observation':'current.json','current_observation_id':'current-id'}}]})
    p={**permit(),'previous_attempt_id':'second','max_attempts':3,'max_total_cost':24}
    assert check_uncertain_retry(rows,Identity('goal','plan3','op3','third'),p,8,WINDOW,'tae009')['max_attempts']==3
    stale=deepcopy(rows);stale[-1]['events'][-1]['proof']['window']={**WINDOW,'pid':999}
    with pytest.raises(ValueError):check_uncertain_retry(stale,Identity('goal','plan3','op3','third'),p,8,WINDOW,'tae009')
    rows.append({'status':'sent','cost':8,'identity':Identity('goal','plan3','op3','third').as_dict(),'events':rows[-1]['events']})
    p['previous_attempt_id']='third'
    with pytest.raises(ValueError):check_uncertain_retry(rows,Identity('goal','plan4','op4','fourth'),p,8,WINDOW,'tae009')


@pytest.mark.parametrize('mutation',[None,'policy_stage','missing_proof','window','no_policy'])
def test_abyss_uncertain_retry_requires_explicit_current_bound_permission(tmp_path,mutation):
    from test_operation_cycle import context
    from driver_epic_seven.attempts import AttemptLedger
    runtime,cycle,observation,_=context(tmp_path)
    runtime.path_attempts=AttemptLedger(tmp_path/'abyss-actions.json',3)
    rows=prior();rows[0]['cost']=10
    rows[0]['events'][-1]={'phase':'uncertain_result_observed','proof':{'result':'unknown','window':WINDOW,
        'current_observation':'abyss-preparation.json','current_observation_id':'current-id'}}
    runtime.execution_identity=Identity('goal','new-plan','op','new')
    runtime.execution_retry={**permit(),'stage_id':'abyss051','max_total_cost':20}
    if mutation=='policy_stage':runtime.execution_retry['stage_id']='abyss052'
    elif mutation=='missing_proof':rows[0]['events'].pop()
    elif mutation=='window':rows[0]['events'][-1]['proof']['window']={**WINDOW,'pid':999}
    elif mutation=='no_policy':runtime.execution_retry=None
    runtime.path_attempts.save({'stages':{'abyss-run':rows}})
    params={'path':{'kind':'abyss_start','stage_id':'abyss051','task_id':'abyss-run','energy':10,'consuming':True}}
    sent=[]
    if mutation:
        with pytest.raises(ValueError):cycle.dispatch('retry',params,observation,lambda:sent.append(True))
        assert sent==[] and len(runtime.path_attempts.read()['stages']['abyss-run'])==1
    else:
        assert cycle.dispatch('retry',params,observation,lambda:sent.append(True) or True)
        actual=runtime.path_attempts.read()['stages']['abyss-run']
        assert len(actual)==2 and actual[0]==rows[0] and len(sent)==1
        assert actual[1]['events'][0]['proof']['retry_authorization']['kind']=='uncertain'
        with pytest.raises(ValueError):cycle.dispatch('retry-again',params,observation,lambda:sent.append(True))
        assert len(sent)==1
