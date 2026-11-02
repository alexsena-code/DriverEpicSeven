"""Bounded Theater compiler and targets on the shared UI tree; Maa executes."""
from copy import deepcopy
import json
from .battle_operations import context, control, fresh_ticket, same_window
from .observed_ui import operation_view, screen_state, auto_state


def target(observation, params, prepared):
    view=operation_view(observation);kind=params['kind'];info=context(view)
    ticket=(prepared or {}).get('theater:'+params['task_id'])
    if kind=='theater_watch':
        cost=info.get('ticket_cost') or {}
        if (view.get('view')=='theater_main' and info.get('act')==params['act']
                and info.get('series')==params['series'] and cost.get('cost')==1
                and type(cost.get('available')) is int and cost['available']>=1):
            return control(view,'watch',False)
        return None
    if kind=='theater_confirm':
        if (view.get('view')=='theater_ticket' and fresh_ticket(ticket,observation)
                and not ticket.get('confirmed') and ticket.get('act')==params['act']
                and ticket.get('series')==params['series']
                and info.get('owned')==ticket.get('available') and info['owned']>=1):
            return control(view,'confirm',True)
        return None
    if not (ticket and ticket.get('confirmed') and same_window(ticket.get('window'),observation.get('window'))):
        return None
    if view.get('view')=='theater_intro' and info.get('act')!=params['act']:
        return None
    if kind=='theater_started':
        return [0,0,1,1] if view.get('view') in ('theater_story','theater_intro') or screen_state(observation)=='battle_running' else None
    if kind=='theater_tap':
        return control(view,'advance',False) if view.get('view') in ('theater_story','theater_intro') else None
    if kind=='theater_clear':
        return control(view,'advance',False) if (view.get('view')=='battle_clear_banner'
            and info.get('victory_announced') is True) else None
    if kind=='theater_auto_on':
        return [0,0,1,1] if screen_state(observation)=='battle_running' and auto_state(observation) is True else None
    if kind=='theater_done':
        cost=info.get('ticket_cost') or {}
        if (view.get('view')=='theater_main' and info.get('act')==params['act']+1
                and info.get('series')==params['series']
                and params['act'] in (info.get('completed_acts') or [])
                and cost.get('available')==ticket['available']-1):
            return [0,0,1,1]
    return None


def prepare(prepared, path, analysis):
    key='theater:'+path['task_id']
    if path['kind']=='theater_watch':
        info=context(operation_view(analysis))
        prepared[key]={'window':deepcopy(analysis['window']),'epoch_seconds':analysis['epoch_seconds'],
            'act':info['act'],'series':info['series'],'available':info['ticket_cost']['available'],'confirmed':False}
    elif path['kind']=='theater_confirm':
        prepared[key]['confirmed']=True


def compile_theater(resource_dir, *, acts, max_tickets, timeout, act, series, scope, taps_per_act=600):
    from .composition import append_fragment,validate_graph
    if type(acts) is not int or not 1<=acts<=20:
        raise ValueError('Quantidade de atos deve estar entre 1 e 20.')
    if type(max_tickets) is not int or not acts<=max_tickets<=100:
        raise ValueError('O limite de ingressos deve cobrir um por ato, até 100.')
    if type(timeout) is not int or not 1<=timeout<=1800:
        raise ValueError('Prazo deve estar entre 1 e 1800 segundos.')
    if type(taps_per_act) is not int or not 1<=taps_per_act<=1500:
        raise ValueError('Limite de toques por ato inválido.')
    if type(act) is not int or act<1 or not isinstance(series,str) or not series.strip():
        raise ValueError('Ato e título atuais não comprovados.')
    source=json.loads((resource_dir/'pipeline/theater.json').read_text(encoding='utf-8'))
    graph={'Theater.Entry':{'recognition':'DirectHit','action':'DoNothing','next':['Theater.1.Entry']}}
    for index in range(1,acts+1):
        names=append_fragment(graph,source,f'Theater.{index}.')
        unit=scope+':'+str(index)
        for old,name in names.items():
            node=graph[name]
            params=node.get('custom_recognition_param',{})
            path=params.get('path')
            if path:
                path.update(task_id=unit,act=act+index-1,series=series)
            node['timeout']=min(timeout*1000,120000)
            if old=='Tap':node['max_hit']=taps_per_act
            if old in ('Started','Done'):
                params['execution']={'ledger':'path','scope':unit,
                    'phase':'entry_verified' if old=='Started' else 'return_verified',
                    'status':'entered' if old=='Started' else 'verified'}
        graph[names['Done']]['next']=[f'Theater.{index+1}.Entry'] if index<acts else ['Theater.Done']
    graph['Theater.Done']={'recognition':'DirectHit','action':'DoNothing','max_hit':1}
    validate_graph(graph,'Theater.Entry',['Theater.Done'])
    return graph,'Theater.Entry','Theater.Done'


def continuation(resource_dir, scope, saved, *, timeout, taps_per_act):
    """Close one pending unit: no Watch, Confirm, resource consumer or new start."""
    graph,entry,success=compile_theater(resource_dir,acts=1,max_tickets=1,timeout=timeout,
        act=saved['act'],series=saved['series'],scope='theater:continuation',taps_per_act=taps_per_act)
    del graph['Theater.1.Watch'];del graph['Theater.1.Confirm']
    graph['Theater.1.Entry']['next']=['Theater.1.Done','Theater.1.Started']
    for node in graph.values():
        params=node.get('custom_recognition_param',{})
        if params.get('path'):params['path']['task_id']=scope
        if params.get('execution'):params['execution']['scope']=scope
    from .composition import validate_graph
    validate_graph(graph,entry,[success],resume=True)
    return graph,entry,success


def run(runtime, *, acts, max_tickets, timeout, taps_per_act=600, finish_current=False):
    from .path_execution import run_graph
    pending=[(scope,rows[-1]) for scope,rows in runtime.path_attempts.read()['stages'].items()
             if scope.startswith('theater:') and rows and rows[-1]['status']!='verified']
    if pending and not finish_current:
        raise ValueError('Há ato pendente no diário. Use --finish-current com --acts 1 --max-tickets 0; não repetir Confirm.')
    before=runtime.observe('theater_before',read_text=True)
    current=operation_view(before);info=context(current)
    if finish_current:
        if acts!=1 or max_tickets!=0 or len(pending)!=1:
            raise ValueError('Continuação exige um único ato pendente, --acts 1 e --max-tickets 0.')
        scope,row=pending[0]
        tickets=[e.get('proof',{}).get('operation_context') for e in row.get('events',[]) if e.get('phase')=='reserved']
        saved=tickets[0] if len(tickets)==1 else None
        if not (saved and same_window(saved.get('window'),before.get('window'))):
            raise ValueError('A janela mudou ou o contexto do ingresso está ausente; conferir manualmente, sem nova confirmação.')
        runtime.path_prepared['theater:'+scope]={**deepcopy(saved),'confirmed':True}
        nodes,entry,success=continuation(runtime.config['resource_dir'],scope,saved,timeout=timeout,taps_per_act=taps_per_act)
        runtime.path_attempts.record(scope,row['key'],'resume_without_consumer',identity=row['identity'],
            proof={'window':before['window'],'observation_id':before['ui_tree']['observation_id'],'max_ticket_consumptions':0})
        first_act,series=saved['act'],saved['series']
    else:
        if current.get('view')!='theater_main':
            raise ValueError('Abra Moonlight Theater e selecione um ato com Watch disponível.')
        first_act,series=info.get('act'),info.get('series')
        nodes,entry,success=compile_theater(runtime.config['resource_dir'],acts=acts,max_tickets=max_tickets,
            timeout=timeout,act=first_act,series=series,
            scope='theater:'+runtime.execution_identity.operation_id,taps_per_act=taps_per_act)
    runtime.evidence.write('theater_plan',{'acts':acts,'max_tickets':max_tickets,'timeout':timeout,
        'first_act':first_act,'series':series,'taps_per_act':taps_per_act,'post_delay_ms':100,
        'max_ticket_consumptions':0 if finish_current else acts,'finish_current':finish_current,
        'unattended_status':'draft','auto_activation_live_validated':False})
    result=run_graph(runtime,nodes,entry,success,timeout)
    done=[n for n in result['nodes'] if n['name'].startswith('Theater.') and n['name'].endswith('.Done') and n['name']!='Theater.Done' and n['completed']]
    final={**result,'operation':'theater','completed_acts':len(done),'requested_acts':acts,
           'max_tickets':max_tickets,'finish_current':finish_current,'auto_activation_live_validated':False}
    runtime.evidence.write('theater_result',final)
    return final
