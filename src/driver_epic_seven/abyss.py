"""One bounded Abyss entry using the mapped panels and shared result flow."""
import time

from .path_execution import recognition
from .battle_results import graph as result_graph, target as result_target


def target(current,params,observation,prepared):
    if params.get('stage_id')!='abyss001':return None
    contexts=[i for i in current.get('items',[]) if i.get('semantic_id')=='context']
    info=contexts[0] if len(contexts)==1 else {}
    kind=params['kind']
    def control(name):
        found=[c for c in current.get('controls',[]) if c.get('semantic_id')==name]
        return found[0].get('box') if len(found)==1 else None
    if kind in ('abyss_done','abyss_advance','abyss_exit','abyss_victory'):
        return result_target(current,params,observation,prepared,family='abyss',destinations=('abyss_floors','abyss_hub','lobby'))
    if kind=='abyss_result_back':
        return control('back') if current.get('view')=='abyss_result' and info.get('floor')==1 and info.get('result')=='victory' else None
    if kind=='abyss_normal':
        return control('normal') if current.get('view')=='abyss_hub' else None
    if kind=='abyss_open':
        rows=[i for i in current.get('items',[]) if i.get('semantic_id')=='abyss_floor' and i.get('value')==1 and i.get('status')=='available']
        return control('select_team') if current.get('view')=='abyss_floors' and info.get('floor')==1 and len(rows)==1 else None
    cost=info.get('cost')
    if (current.get('view')!='abyss_preparation' or info.get('floor')!=1
            or not cost or cost.get('currency')!='energy' or cost.get('cost')!=10
            or cost.get('available',-1)<10):return None
    if kind=='abyss_prepared':return [0,0,1,1]
    ticket=(prepared or {}).get('abyss:abyss001')
    if (kind=='abyss_start' and params.get('max_energy',0)>=10 and ticket
            and isinstance(info.get('team_cp'),int) and info['team_cp']>0
            and 0<=time.time()-ticket['epoch_seconds']<=30 and ticket['window']==observation.get('window')):
        return control('start')
    return None


def graph(task_id,max_energy,*,prepare=False,finish=False):
    if task_id!='guide_02_005_001':raise ValueError('Abyss limitado à unidade requerida no grupo 2.')
    if not prepare and not finish and max_energy<10:raise ValueError('Orçamento insuficiente para Abyss 1.')
    p='Path.Abyss.abyss001.'
    nodes,choices=result_graph(p,'abyss001',task_id,family='abyss')
    for node in nodes.values():
        if node.get('next'):node['next'].insert(0,p+'ResultBack')
    choices.insert(0,p+'ResultBack')
    nodes[p+'ResultBack']=recognition({'kind':'abyss_result_back','stage_id':'abyss001','task_id':task_id},
        'LongPress',duration=100,next_nodes=[p+'Done',p+'Notice'],post_delay=700,timeout=240000)
    nodes[p+'Entry']={'recognition':'DirectHit','action':'DoNothing','timeout':240000,'next':choices if finish else [p+'Normal',p+'Open',p+'Prepared']}
    if not finish:
        nodes[p+'Normal']=recognition({'kind':'abyss_normal','stage_id':'abyss001'},'LongPress',duration=100,
            next_nodes=[p+'Open'],post_delay=700,timeout=15000)
        nodes[p+'Open']=recognition({'kind':'abyss_open','stage_id':'abyss001'},'LongPress',duration=100,
            next_nodes=[p+'Prepared'],post_delay=700,timeout=15000)
        nodes[p+'Prepared']=recognition({'kind':'abyss_prepared','stage_id':'abyss001'},
            next_nodes=[] if prepare else [p+'Start'])
        if not prepare:
            nodes[p+'Start']=recognition({'kind':'abyss_start','stage_id':'abyss001','task_id':task_id,
                'consuming':True,'energy':10,'max_energy':max_energy},'LongPress',duration=100,
                next_nodes=choices,post_delay=700,timeout=240000)
    return {'stage_id':'abyss001','task_id':task_id,'energy_limit':0 if prepare or finish else 10,
            'max_starts':0 if prepare or finish else 1},nodes,p+'Entry',p+'Prepared' if prepare else p+'Done'
