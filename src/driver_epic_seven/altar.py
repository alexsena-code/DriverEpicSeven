"""Finite Spirit Altar units over the shared, current UI tree."""
import json

from .config import ROOT
from .path_execution import recognition
from .stages import normalize
from .battle_operations import energy_verified, fresh_ticket, team_verified
from .composition import validate_graph


def stage(identity):
    entries=json.loads((ROOT/'data/stages/spirit-altars.json').read_text(encoding='utf-8'))['stages']
    if identity not in entries:
        raise ValueError('Altar/dificuldade ausente do catálogo estático.')
    return entries[identity]


def target(current, params, observation, prepared):
    expected=stage(params['stage_id'])
    contexts=[i for i in current.get('items',[]) if i.get('semantic_id')=='context']
    info=contexts[0] if len(contexts)==1 else {}
    kind=params['kind']
    if kind in ('altar_done','altar_exit','altar_advance','altar_victory','altar_defeat'):
        from .battle_results import target as result_target
        return result_target(current,params,observation,prepared,family='altar',destinations=('spirit_altar_hub','lobby'))
    if kind=='altar_open':
        if current.get('view')!='spirit_altar_hub':return None
        rows=[i for i in current.get('items',[]) if i.get('difficulty')==expected['difficulty'].lower()
              and normalize(i.get('altar_name') or '')==normalize(expected['altar_name']) and i.get('available') is True]
        if len(rows)!=1:return None
        controls=[c for c in current.get('controls',[]) if c.get('semantic_id')=='open_difficulty:'+expected['difficulty'].lower()
                  and c.get('consuming') is False]
        return controls[0].get('box') if len(controls)==1 else None
    if current.get('view')!='spirit_altar_preparation':return None
    cost=info.get('cost')
    if (normalize(info.get('altar_name') or '')!=normalize(expected['altar_name'])
            or normalize(info.get('stage_label') or '')!=normalize(expected['label'])
            or info.get('difficulty')!=expected['difficulty'].lower() or info.get('identity_conflict') is True
            or not energy_verified(cost,expected['energy'])):return None
    if kind=='altar_prepared':return [0,0,1,1]
    if kind=='altar_start':
        ticket=(prepared or {}).get('altar:'+expected['id'])
        if (not energy_verified(cost,expected['energy'],params.get('max_energy',0))
                or not team_verified(info) or not fresh_ticket(ticket,observation)):return None
        controls=[c for c in current.get('controls',[]) if c.get('semantic_id')=='start' and c.get('consuming') is True]
        return controls[0].get('box') if len(controls)==1 else None
    return None


def graph(identity, task_id, max_energy, *, finish=False, prepare=False):
    expected=stage(identity)
    if not isinstance(task_id,str) or not task_id.strip():raise ValueError('Escopo persistente ausente.')
    if prepare and finish:raise ValueError('Preparação e retomada são operações distintas.')
    if not prepare and not finish and max_energy<expected['energy']:
        raise ValueError('Orçamento insuficiente para uma entrada no Altar.')
    p='Path.Altar.'+identity+'.'
    from .battle_results import graph as result_graph
    nodes,choices=result_graph(p,identity,task_id,family='altar')
    nodes[p+'Entry']={'recognition':'DirectHit','action':'DoNothing','next':choices if finish else [p+'Prepared',p+'Open']}
    if not finish:
        nodes[p+'Open']=recognition({'kind':'altar_open','stage_id':identity},'LongPress',duration=100,
            next_nodes=[p+'Prepared',p+'Open'],hits=2,post_delay=700,timeout=30000)
        nodes[p+'Prepared']=recognition({'kind':'altar_prepared','stage_id':identity},
            next_nodes=[] if prepare else [p+'Start'])
        if not prepare:
            nodes[p+'Start']=recognition({'kind':'altar_start','stage_id':identity,'task_id':task_id,
                'max_energy':max_energy,'energy':expected['energy'],'consuming':True},'LongPress',duration=100,
                next_nodes=choices,post_delay=600,timeout=240000)
    validate_graph(nodes,p+'Entry',resume=finish or prepare)
    return {'stage_id':identity,'task_id':task_id,'max_starts':0 if prepare or finish else 1,
            'energy_limit':0 if prepare or finish else expected['energy']},nodes,p+'Entry',p+'Prepared' if prepare else p+'Done'
