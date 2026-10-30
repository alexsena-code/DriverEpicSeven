"""One bounded Abyss entry using the mapped panels and shared result flow."""
from .path_execution import recognition
from .battle_results import graph as result_graph, target as result_target
from .battle_operations import context, control as resolve_control, energy_verified, fresh_ticket, team_verified
from .composition import validate_graph


def identity(floor, mode):
    if type(floor) is not int or floor < 1 or mode != 'normal':
        raise ValueError('Abyss exige andar positivo e variante normal; Challenge não calibrado.')
    return f'abyss{floor:03}'


def target(current,params,observation,prepared):
    floor=params.get('floor');mode=params.get('mode')
    if params.get('stage_id')!=identity(floor,mode):return None
    info=context(current)
    kind=params['kind']
    def control(name):
        return resolve_control(current,name)
    if kind in ('abyss_done','abyss_advance','abyss_exit','abyss_victory','abyss_defeat'):
        return result_target(current,params,observation,prepared,family='abyss',destinations=('abyss_floors','abyss_hub','lobby'))
    if kind=='abyss_result_back':
        return control('back') if current.get('view')=='abyss_result' and info.get('floor')==floor and info.get('result')=='victory' else None
    if kind=='abyss_next_floor':
        return resolve_control(current,'next_floor',False) if (current.get('view')=='abyss_result'
            and info.get('floor')==floor and info.get('result')=='victory') else None
    if kind=='abyss_next_prepared':
        return [0,0,1,1] if (current.get('view')=='abyss_preparation' and info.get('floor')==floor+1
            and energy_verified(info.get('cost'),params.get('expected_energy'))) else None
    if kind=='abyss_normal':
        return control('normal') if current.get('view')=='abyss_hub' else None
    if kind=='abyss_open':
        rows=[i for i in current.get('items',[]) if i.get('semantic_id')=='abyss_floor' and i.get('value')==floor and i.get('status')=='available']
        return control('select_team') if current.get('view')=='abyss_floors' and info.get('floor')==floor and len(rows)==1 else None
    cost=info.get('cost')
    if (current.get('view')!='abyss_preparation' or info.get('floor')!=floor
            or not energy_verified(cost,params.get('expected_energy'))):return None
    if kind=='abyss_prepared':return [0,0,1,1]
    ticket=(prepared or {}).get('abyss:'+params['stage_id'])
    if (kind=='abyss_start' and energy_verified(cost,params.get('expected_energy'),params.get('max_energy',0))
            and team_verified(info) and fresh_ticket(ticket,observation)):
        return resolve_control(current,'start',True)
    return None


def graph(task_id,max_energy,*,floor,mode,expected_energy,prepare=False,finish=False,next_floor=False):
    stage_id=identity(floor,mode)
    if not isinstance(task_id,str) or not task_id.strip():raise ValueError('Escopo persistente ausente.')
    if prepare and finish or next_floor and not prepare:
        raise ValueError('Next Floor é preparação separada, sem Start.')
    if not finish and (type(expected_energy) is not int or expected_energy<=0):
        raise ValueError('Custo esperado de Abyss desconhecido.')
    if not prepare and not finish and (type(max_energy) is not int or max_energy<expected_energy):
        raise ValueError('Orçamento insuficiente para uma entrada de Abyss.')
    p='Path.Abyss.'+stage_id+'.'
    common={'stage_id':stage_id,'floor':floor,'mode':mode,'expected_energy':expected_energy}
    if next_floor:
        nodes={p+'Entry':{'recognition':'DirectHit','action':'DoNothing','next':[p+'NextFloor']},
               p+'NextFloor':recognition({'kind':'abyss_next_floor',**common},'LongPress',duration=100,
                   next_nodes=[p+'Prepared'],post_delay=700,timeout=15000),
               p+'Prepared':recognition({'kind':'abyss_next_prepared',**common})}
        return {'stage_id':identity(floor+1,mode),'max_starts':0,'energy_limit':0},nodes,p+'Entry',p+'Prepared'
    nodes,choices=result_graph(p,stage_id,task_id,family='abyss')
    for node in nodes.values():
        path=node.get('custom_recognition_param',{}).get('path')
        if path and path.get('kind','').startswith('abyss_'):path.update(common)
    for node in nodes.values():
        if node.get('next'):node['next'].insert(0,p+'ResultBack')
    choices.insert(0,p+'ResultBack')
    nodes[p+'ResultBack']=recognition({'kind':'abyss_result_back',**common,'task_id':task_id},
        'LongPress',duration=100,next_nodes=[p+'Done',p+'Notice'],post_delay=700,timeout=240000)
    nodes[p+'Entry']={'recognition':'DirectHit','action':'DoNothing','timeout':240000,'next':choices if finish else [p+'Normal',p+'Open',p+'Prepared']}
    if not finish:
        nodes[p+'Normal']=recognition({'kind':'abyss_normal',**common},'LongPress',duration=100,
            next_nodes=[p+'Open'],post_delay=700,timeout=15000)
        nodes[p+'Open']=recognition({'kind':'abyss_open',**common},'LongPress',duration=100,
            next_nodes=[p+'Prepared'],post_delay=700,timeout=15000)
        nodes[p+'Prepared']=recognition({'kind':'abyss_prepared',**common},
            next_nodes=[] if prepare else [p+'Start'])
        if not prepare:
            nodes[p+'Start']=recognition({'kind':'abyss_start',**common,'task_id':task_id,
                'consuming':True,'energy':expected_energy,'max_energy':max_energy},'LongPress',duration=100,
                next_nodes=choices,post_delay=700,timeout=240000)
    validate_graph(nodes,p+'Entry',resume=finish or prepare)
    return {'stage_id':stage_id,'floor':floor,'mode':mode,'task_id':task_id,'energy_limit':0 if prepare or finish else expected_energy,
            'max_starts':0 if prepare or finish else 1},nodes,p+'Entry',p+'Prepared' if prepare else p+'Done'
