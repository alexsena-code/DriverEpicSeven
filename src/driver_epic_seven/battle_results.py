"""Shared finite result handling for calibrated battle units; never Start/Again."""
from .path_execution import recognition
from .interruptions import treatment


def target(current, params, observation, prepared, *, family, destinations):
    kind=params['kind'].removeprefix(family+'_')
    contexts=[i for i in current.get('items',[]) if i.get('semantic_id')=='context']
    info=contexts[0] if len(contexts)==1 else {}
    if kind=='defeat':
        from .observed_ui import screen_state
        return [0,0,1,1] if screen_state(observation)=='battle_failed' else None
    ticket=(prepared or {}).get(family+'_victory:'+params['stage_id'])
    if kind=='done':
        return [0,0,1,1] if (current.get('view') in destinations and ticket
            and all(ticket['window'].get(k)==observation.get('window',{}).get(k)
                    for k in ('hwnd','pid','process_name','window_class','client_size'))) else None
    if kind=='exit':
        if current.get('view')!='battle_exit' or not ticket:return None
        controls=[c for c in current.get('controls',[]) if c.get('semantic_id')=='lobby' and c.get('consuming') is False]
        return controls[0].get('box') if len(controls)==1 else None
    if kind=='advance':
        if current.get('view')!='battle_clear_banner' or info.get('result')!='victory':return None
        controls=[c for c in current.get('controls',[]) if c.get('semantic_id')=='advance' and c.get('consuming') is False]
        return controls[0].get('box') if len(controls)==1 else None
    if kind=='victory':
        return [0,0,1,1] if (current.get('view') in ('battle_clear_result','otherworld_result')
                             and info.get('result')=='victory') else None
    return None


def graph(prefix, identity, task_id, *, family):
    after=[prefix+'Defeat',prefix+'Done',prefix+'Advance',prefix+'Notice',prefix+'Rewards',prefix+'Exit']
    choices=[*after,prefix+'Auto']
    nodes={prefix+'Done':recognition({'kind':family+'_done','stage_id':identity,'task_id':task_id}),
           prefix+'Defeat':recognition({'kind':family+'_defeat','stage_id':identity,'task_id':task_id}),
           prefix+'Advance':recognition({'kind':family+'_advance','stage_id':identity,'task_id':task_id},'LongPress',
               duration=100,hits=1,post_delay=700,timeout=240000,next_nodes=after),
           prefix+'Notice':treatment('notice',after,hits=8,timeout=240000,post_delay=600),
           prefix+'Rewards':treatment('rewards',after,hits=1,timeout=240000,post_delay=700),
           prefix+'Exit':recognition({'kind':family+'_exit','stage_id':identity},'LongPress',duration=100,
               hits=1,post_delay=700,timeout=240000,next_nodes=[prefix+'Done',prefix+'Notice']),
           prefix+'Auto':treatment('auto',after,hits=1,timeout=240000,post_delay=200)}
    return nodes,choices
