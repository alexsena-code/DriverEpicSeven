"""Explicit finite retry permits, accepted only after a proven defeat."""
import time
from .battle_operations import same_window


def check_retry(entries, identity, policy, cost, window, *, limit=3, now=None):
    now=time.time() if now is None else now
    if not isinstance(policy,dict) or not entries:raise ValueError('Nova tentativa exige plano explícito e derrota comprovada.')
    previous=entries[-1];old=previous.get('identity',{})
    defeat=[e for e in previous.get('events',[]) if e['phase']=='defeat']
    if previous.get('result_status',previous['status'])!='defeat' or not defeat:
        raise ValueError('Somente derrota comprovada autoriza nova tentativa; resultado incerto ou vitória não autorizam.')
    proof=defeat[-1].get('proof',{})
    if not proof.get('observation_id') or not same_window(proof.get('window'),window):
        raise ValueError('Prova/janela da derrota ausente ou incompatível.')
    same_plan = old.get('plan_id') == identity.plan_id
    new_plan = policy.get('kind') == 'defeat_new_plan'
    if new_plan:
        stage_id=proof.get('target',{}).get('stage_id')
        if not stage_id:
            # Older campaign result events carry the phase in their compiled
            # Maa node, while the confirmed entry carries the stage target.
            # Require both independent links; do not rewrite the ledger.
            candidate=policy.get('stage_id')
            events=previous.get('events',[])
            entered=any(e.get('phase')=='effect_verified' for e in events)
            reserved=[e for e in events if e.get('phase')=='reserved']
            node=proof.get('node','')
            if (candidate and node in (f'Chapter.{candidate}.Finish.Defeat',
                                       f'Resume.{candidate}.Finish.Defeat')
                    and entered and any(e.get('proof',{}).get('target',{}).get('stage_id')==candidate for e in reserved)):
                stage_id=candidate
        if (same_plan or not old.get('plan_id') or policy.get('previous_plan_id')!=old['plan_id']
                or not stage_id or policy.get('stage_id')!=stage_id):
            raise ValueError('Novo plano após derrota exige fase e plano anterior explicitamente vinculados.')
    if (not old or old.get('attempt_id')!=policy.get('previous_attempt_id')
            or old.get('attempt_id')==identity.attempt_id
            or old.get('objective_id')!=identity.objective_id or (not same_plan and not new_plan)):
        raise ValueError('Nova tentativa exige identidade nova no mesmo objetivo/plano e vínculo com a derrota anterior.')
    attempts=policy.get('max_attempts');budget=policy.get('max_total_cost');deadline=policy.get('deadline_epoch_seconds')
    if type(attempts) is not int or not 1<=attempts<=min(3,limit) or len(entries)>=attempts:
        raise ValueError('Limite finito de tentativas atingido ou inválido.')
    if type(deadline) not in (int,float) or not now<deadline<=now+3600:
        raise ValueError('Prazo da nova tentativa expirado ou inválido.')
    if (type(cost) is not int or cost<0 or type(budget) is not int
            or any(type(e.get('cost')) is not int or e['cost']<0 for e in entries)
            or budget<sum(e['cost'] for e in entries)+cost):
        raise ValueError('Orçamento total insuficiente para a nova tentativa.')
    permit={'previous_attempt_id':old['attempt_id'],'max_attempts':attempts,'max_total_cost':budget,
            'deadline_epoch_seconds':deadline,'defeat_observation_id':proof['observation_id']}
    if new_plan:permit.update(kind='defeat_new_plan',previous_plan_id=old['plan_id'],stage_id=stage_id)
    return permit


def check_uncertain_retry(entries, identity, policy, cost, window, stage_id, *, limit=3, now=None):
    """Explicit, finite retry after a documented uncertain entry; never infer defeat."""
    now = time.time() if now is None else now
    if not isinstance(policy, dict) or policy.get('kind') != 'uncertain' or policy.get('stage_id') != stage_id or not entries:
        raise ValueError('Nova tentativa incerta exige autorização explícita para a fase.')
    previous = entries[-1]
    if previous.get('status') not in ('reserved', 'sent', 'entered', 'uncertain') or previous.get('result_status') is not None:
        raise ValueError('A tentativa anterior não é uma entrada sem resultado conhecido.')
    old = previous.get('identity', {})
    events = [e for e in previous.get('events', []) if e.get('phase') in ('patch_interruption_observed','uncertain_result_observed')]
    proof = events[-1].get('proof', {}) if events else {}
    original = next((e.get('proof', {}).get('window') for e in previous.get('events', [])
                     if e.get('phase') in ('dispatch_accepted','dispatch_attempted')), None)
    observed = (proof.get('current_map_observation') and proof.get('current_map_observation_id')
                if events and events[-1].get('phase')=='patch_interruption_observed' else
                proof.get('current_observation') and proof.get('current_observation_id') and same_window(proof.get('window'),window))
    if (not events or proof.get('result') != 'unknown' or not observed
            or (events[-1].get('phase')=='patch_interruption_observed' and not proof.get('patch_observation'))
            or not same_window(original, window)):
        raise ValueError('Interrupção e contexto da janela não foram reconciliados.')
    if (old.get('attempt_id') != policy.get('previous_attempt_id') or old.get('attempt_id') == identity.attempt_id
            or not old.get('objective_id') or old['objective_id'] != identity.objective_id):
        raise ValueError('Tentativa deve referenciar a entrada anterior e manter o objetivo.')
    attempts, budget, deadline = policy.get('max_attempts'), policy.get('max_total_cost'), policy.get('deadline_epoch_seconds')
    if type(attempts) is not int or not 1 <= attempts <= min(3, limit) or len(entries) >= attempts:
        raise ValueError('Limite de tentativas atingido ou inválido.')
    if type(deadline) not in (int, float) or not now < deadline <= now + 3600:
        raise ValueError('Prazo inválido ou expirado.')
    if (type(cost) is not int or cost < 0 or type(budget) is not int
            or any(type(e.get('cost')) is not int or e['cost'] < 0 for e in entries)
            or budget < sum(e['cost'] for e in entries) + cost):
        raise ValueError('Orçamento total insuficiente para a nova tentativa.')
    return {'kind':'uncertain', 'previous_attempt_id':old['attempt_id'], 'stage_id':stage_id,
            'max_attempts':attempts, 'max_total_cost':budget, 'deadline_epoch_seconds':deadline,
            'interruption_evidence':proof.get('patch_observation'),
            'observation_evidence':proof.get('current_map_observation') or proof.get('current_observation')}
