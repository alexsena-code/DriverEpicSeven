"""Shared pure guards for battle operations; no capture, input or scheduling."""
import time


WINDOW_FIELDS = ('hwnd', 'pid', 'process_name', 'window_title', 'window_class', 'client_size')


def context(current):
    rows = [i for i in current.get('items', []) if i.get('semantic_id') == 'context']
    return rows[0] if len(rows) == 1 else {}


def control(current, name, consuming=None):
    rows = [c for c in current.get('controls', []) if c.get('semantic_id') == name
            and (consuming is None or c.get('consuming') is consuming)]
    return rows[0].get('box') if len(rows) == 1 else None


def same_window(before, after):
    return bool(before and after and all(before.get(k) == after.get(k) for k in WINDOW_FIELDS))


def fresh_ticket(ticket, observation, seconds=30):
    return bool(ticket and 0 <= time.time() - ticket.get('epoch_seconds', 0) <= seconds
                and same_window(ticket.get('window'), observation.get('window')))


def energy_verified(cost, expected, budget=None):
    if not isinstance(expected, int) or isinstance(expected, bool) or expected < 0:
        return False
    if not isinstance(cost, dict) or cost.get('currency') != 'energy':
        return False
    amount, balance = cost.get('cost'), cost.get('available')
    return bool(type(amount) is int and amount == expected and type(balance) is int and balance >= amount
                and (budget is None or type(budget) is int and budget >= amount))


def team_verified(info):
    """Composition plus current occupied-member evidence; CP proves neither."""
    levels = info.get('visible_hero_levels')
    stories=info.get('visible_story_member_markers')
    members=(isinstance(levels,list) and bool(levels)
             and all(type(level) is int and 1 <= level <= 60 for level in levels))
    story_members=type(stories) is int and 1 <= stories <= 4
    return bool(info.get('preparation_composition_verified') is True
                and (members or story_members))


def run_unit(runtime, family, stage_id, ledger_scope, compilation, *, prepare=False, finish=False, timeout=300):
    """Shared single-entry lifecycle; all recognition/retries stay in Maa."""
    from .path_execution import run_graph
    if not isinstance(ledger_scope,str) or not ledger_scope.strip():
        raise ValueError('A unidade exige escopo persistente explícito.')
    prior=runtime.path_attempts.read()['stages'].get(ledger_scope,[])
    if finish:
        if not prior or prior[-1]['status'] not in ('reserved','sent','entered','victory'):
            raise ValueError('Não há entrada pendente para concluir.')
        last=prior[-1]
        targets=[e.get('proof',{}).get('target',{}) for e in last.get('events',[])]
        if not (any(t.get('stage_id')==stage_id for t in targets) or '.'+stage_id+'.' in last['key']):
            raise ValueError('A reserva pendente pertence a outra batalha ou não possui identidade comprovada.')
        if last.get('result_status',last['status'])=='victory':
            if not same_window(last.get('verification_window'),runtime.original):
                raise ValueError('A janela da prova de vitória não confere; reler o resultado atual.')
            runtime.path_prepared[family+'_victory:'+stage_id]={'window':runtime.original}
    elif not prepare and prior and not getattr(runtime,'execution_retry',None):
        raise ValueError('Entrada já registrada neste escopo; concluir/reconciliar sem repetir Start.')
    plan,nodes,entry,success=compilation
    return {**run_graph(runtime,nodes,entry,success,timeout),**plan}
