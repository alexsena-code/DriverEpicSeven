"""Compile selected, calibrated units into one finite Maa group graph."""
from .composition import append_fragment, validate_graph

from .observed_ui import quest_view
from .path_execution import recognition,open_path_graph,go_graph
from .path_planning import route_level,executor_for,catalog


def target(observation,params):
    q=quest_view(observation)
    if q.get('group_id')!=params['group_id']:return None
    count=q.get('group_counter')
    if params['kind']=='group_guard':
        return [0,0,1,1] if count==params['counter'] else None
    tasks=[t for t in q.get('visible_tasks',[]) if t['task_id']==params.get('task_id')]
    task=tasks[0] if len(tasks)==1 else {}
    if params['kind']=='group_task_ready':
        return [0,0,1,1] if task.get('claim_ready') is True or task.get('status')=='claimed' else None
    if params['kind']=='group_scroll':
        return [0,0,1,1] if count and not task.get('row_fully_visible') else None
    return None


def unit_graph(task,settings,entries=None):
    entries=entries or {}
    executor=executor_for(task)
    if executor=='campaign':
        from .prequel import campaign_graph
        if settings['to_stage']!=task['parameters']['enter']:
            raise ValueError('O trecho não termina na fase exigida pela missão.')
        plan,graph=campaign_graph(settings['from_stage'],settings['to_stage'],settings['max_energy'])
        if any(entries.get('prequel:'+stage) for stage in plan['stage_ids']):
            from .plans import resume_campaign, disposition
            if all(disposition(entries.get('prequel:'+stage,[]))=='completed' for stage in plan['stage_ids']):
                return {'energy_limit':0,'max_starts':0,'stage_ids':plan['stage_ids']},{'Unit.Completed':{'recognition':'DirectHit','action':'DoNothing'}},'Unit.Completed','Unit.Completed'
            return resume_campaign(settings['from_stage'],settings['to_stage'],settings['max_energy'],entries)
        return plan,graph,'Path.Campaign.Entry','Path.Campaign.Done'
    if executor=='abyss':
        from .abyss import graph
        floor=settings.get('floor',int(task['parameters']['count']))
        from .plans import disposition
        state=disposition(entries.get(task['id'],[]))
        if state=='explicit_defeat_policy':raise ValueError('Derrota exige política explícita de ajuste.')
        finish=state=='reconcile_without_consumer'
        if state=='completed':
            return {'energy_limit':0,'max_starts':0},{'Unit.Completed':{'recognition':'DirectHit','action':'DoNothing'}},'Unit.Completed','Unit.Completed'
        return graph(task['id'],settings['max_energy'],floor=floor,mode=settings.get('mode','normal'),
                     expected_energy=settings.get('expected_energy',10),finish=finish)
    if executor in ('equip','equipment_enhance'):
        from .equipment_operations import graph
        from .path_planning import equipment_operation
        from .plans import disposition
        state=disposition(entries.get(task['id'],[]))
        if state=='completed':
            return {'energy_limit':0,'max_starts':0},{'Unit.Completed':{'recognition':'DirectHit','action':'DoNothing'}},'Unit.Completed','Unit.Completed'
        if state!='new':raise ValueError('Mudança de equipamento pendente exige finish-current com contexto persistente antes de retomar grupo.')
        return graph(task['id'],settings,operation=equipment_operation(task))
    raise ValueError('Operação sem unidade calibrada para encadeamento: '+executor)


def compile_group(level,observation,settings,verified_claims=(),entries=None,checkpoint_view=None):
    from .path_claims import graph as claim_graph
    from .path_planning import group_id,next_progression
    identity=group_id(level);route=route_level(level);q=checkpoint_view or quest_view(observation)
    count=q.get('group_counter')
    if q.get('group_id')!=identity or not count:
        raise ValueError('O grupo e seu contador precisam de leitura atual.')
    following=next_progression(level)['next_group']
    if not following:raise ValueError('O grupo final exige um contrato de término próprio.')
    verified_claims=set(verified_claims)
    if len(verified_claims)>count['current'] or verified_claims-{t['task_id'] for t in route['tasks']}:
        raise ValueError('O diário de resgates não confere com o contador atual.')
    live={t['task_id']:t for t in q.get('visible_tasks',[])}
    known=set(verified_claims)
    if count['current']==count['total']:known.update(t['task_id'] for t in route['tasks'])
    for task in live.values():
        if task.get('claim_ready') is True or task.get('status')=='claimed':known.add(task['task_id'])
    requested=settings.get('tasks',{})
    if set(requested)-{t['task_id'] for t in route['tasks']}:raise ValueError('Plano contém missão de outro grupo.')
    pending=[t for t in route['tasks'] if t['task_id'] not in known]
    missing=[t['task_id'] for t in pending if t['task_id'] not in requested]
    if missing:raise ValueError('Faltam escolhas para missões não comprovadas: '+', '.join(missing))
    max_energy=settings.get('max_energy',0)
    if not isinstance(max_energy,int) or isinstance(max_energy,bool) or max_energy<0:raise ValueError('Orçamento de energia inválido.')
    max_gold=settings.get('max_gold',0)
    if not isinstance(max_gold,int) or isinstance(max_gold,bool) or max_gold<0:raise ValueError('Orçamento de ouro inválido.')
    nodes={'Path.Group.Entry':{'recognition':'DirectHit','action':'DoNothing','next':['Path.Group.Guard']},
           'Path.Group.Guard':recognition({'kind':'group_guard','group_id':identity,'counter':count})}
    previous='Path.Group.Guard';energy=0;gold=0;starts=0;completion_scopes={};unit_ledgers={}
    for index,item in enumerate(pending):
        task=catalog().tasks[item['task_id']];p=f'Path.Group.Step{index}.'
        plan,unit,entry,success=unit_graph(task,requested[task['id']],entries)
        unit_ledgers[task['id']]={'ledger_name':'path_battles' if executor_for(task)=='campaign' else 'path_attempts',
            'ledger_scopes':['prequel:'+stage for stage in plan.get('stage_ids',[])] if executor_for(task)=='campaign' else [task['id']]}
        energy+=plan.get('energy_limit',0);starts+=plan.get('max_starts',0)
        gold+=plan.get('gold_limit',0)
        if energy>max_energy:raise ValueError('As unidades excedem o orçamento de energia do grupo.')
        if gold>settings.get('max_gold',0):raise ValueError('As unidades excedem o orçamento de ouro do grupo.')
        names=append_fragment(nodes,unit,p+'Unit.')
        go=append_fragment(nodes,go_graph(identity,task['id'],executor_for(task)),p+'Go.')
        nodes[go['Path.Go.Done']]['next']=[names[entry]]
        ready=p+'AlreadyReady';go_entry=go['Path.Go.Click'];first=p+'Entry'
        nodes[ready]=recognition({'kind':'group_task_ready','group_id':identity,'task_id':task['id']})
        nodes[first]={'recognition':'DirectHit','action':'DoNothing','next':[ready,go_entry,p+'ScrollTop']}
        scroll={'kind':'group_scroll','group_id':identity,'task_id':task['id']}
        for name,begin,end,next_name in [('ScrollTop',[850,320],[850,570],'ScrollDown1'),
                                        ('ScrollDown1',[850,570],[850,320],'ScrollDown2'),
                                        ('ScrollDown2',[850,570],[850,320],None)]:
            nodes[p+name]=recognition(scroll,'Swipe',begin=begin,end=end,duration=400,hits=1,
                post_delay=500,next_nodes=[ready,go_entry]+([p+next_name] if next_name else []),timeout=12000)
        # The task's Go recognizer and all unit controls still revalidate the
        # current tree. No task ID from the catalog is a runtime target.
        nodes[previous]['next']=[first]
        returned=append_fragment(nodes,open_path_graph(),p+'Return.')
        for terminal in success if isinstance(success,(tuple,list)) else [success]:
            nodes[names[terminal]]['next']=[returned['Path.Open.Entry']]
        previous=returned['Path.Open.Done']
        nodes[ready]['next']=[previous]
    # All claims remain separate from satisfying conditions; native counters
    # and receipts are required at each boundary, including the next group.
    ready_ids=[t['task_id'] for t in route['tasks'] if t['task_id'] not in set(verified_claims)]
    if count['current']<count['total']:
        if not ready_ids:raise ValueError('Contador não permite inferir as recompensas prontas.')
        scope,claim=claim_graph(identity,ready_ids[0],count['current'],count['total'])
        names=append_fragment(nodes,claim,'Path.Group.Collect.')
        nodes[previous]['next']=[names['Path.Claim.Entry']]
        previous=names['Path.Claim.Done'];completion_scopes[previous]=scope
    scope,reward=claim_graph(identity,None,count['total'],count['total'],next_group_id=following)
    names=append_fragment(nodes,reward,'Path.Group.Reward.')
    nodes[previous]['next']=[names['Path.Claim.Entry']]
    completion_scopes[names['Path.Claim.Done']]=scope
    nodes[names['Path.Claim.Done']]['next']=['Path.Group.Done']
    nodes['Path.Group.Done']=recognition({'kind':'group_guard','group_id':following,'counter':{'current':0,'total':len(route_level(following)['tasks'])}})
    from .plans import contract
    units=[]
    for task in pending:
        units.append({'unit_id':task['task_id'],'capability':executor_for(catalog().tasks[task['task_id']]),
                      'depends_on':[units[-1]['unit_id']] if units else [],**unit_ledgers[task['task_id']]})
    units.append({'unit_id':'claim:'+identity,'capability':'mission_credit',
                  'ledger_name':'path_attempts','ledger_scopes':[scope for scope in completion_scopes.values() if scope.startswith('claim:')],
                  'depends_on':[u['unit_id'] for u in units]})
    units.append({'unit_id':'group_reward:'+identity,'capability':'group_receipt',
                  'ledger_name':'path_attempts','ledger_scopes':['group_reward:'+identity],
                  'depends_on':['claim:'+identity]})
    names=append_fragment(nodes,open_path_graph(),'Path.Group.Recovery.')
    nodes[names['Path.Open.Done']]['next']=['Path.Group.Guard']
    nodes['Path.Group.Entry']['next']=[names['Path.Open.Entry']]
    finite=contract('path.run-group',units,nodes,energy=energy,max_actions=settings.get('max_actions',200))
    from .plans import with_retry_budget
    finite=with_retry_budget(finite,settings.get('retry_budget'))
    finite['requested_settings']=settings
    finite['initial_group_view']=q
    validate_graph(nodes,'Path.Group.Entry',['Path.Group.Done'])
    return {'finite_plan':finite,'group_id':identity,'next_group_id':following,'energy_limit':energy,'gold_limit':gold,'max_starts':starts,
            'claim_completion_scopes':completion_scopes,'agent_checkpoint':True},nodes
