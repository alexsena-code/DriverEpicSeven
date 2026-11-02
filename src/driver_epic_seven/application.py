"""Shared local application. Transports adapt arguments; Maa owns execution."""
import json
from types import SimpleNamespace

from .contracts import Request, Outcome, Status, ApplicationError
from .pipelines import registry


class Parameters(SimpleNamespace):
    def __getattr__(self, name):
        raise ApplicationError('Parâmetro explícito ausente: '+name)


def capabilities(config):
    """Read existing sources only; mapped families are never executable claims."""
    from .path_planning import catalog
    cat = catalog(config)
    return {'read_only': True, 'requires_current_action_guards': True,
            'routines': registry(config),
            'mapped_families': sorted(set(cat.families.values())),
            'mapped_families_source': str(config['operation_map_file']),
            'mapped_families_are_executors': False,
            'validation_scope': 'docs/validation.md', 'account_access': None,
            'operations': {
                'theater': {'parameters':['acts','max_tickets','timeout','taps_per_act','finish_current'],
                            'defaults':{'timeout':1800,'taps_per_act':600,'finish_current':False},'scope':'draft_paid_watch_dialogue_battle_clear_next_act'},
                'repeat-stage': {'parameters':['count','max_resource','timeout'],
                                 'defaults':{'timeout':1800},'scope':'draft_current_result_try_again'},
                'chapter': {'parameters':['from_stage','max_energy','timeout','finish_current'],
                            'defaults':{'timeout':600,'finish_current':False},'scope':'finite_chapter'},
                'path.campaign': {'parameters':['from_stage','to_stage','max_energy','timeout'],
                                  'defaults':{'timeout':600},'scope':'finite_prequel_segment'},
                'path.run-group': {'parameters':['level','plan','timeout'],
                                   'defaults':{'timeout':1200},'scope':'calibrated_selected_units_and_receipts'},
                'path.recover': {'parameters':['task_id'],'defaults':{},'scope':'calibrated_navigation_only'},
                'path.abyss': {'parameters':['floor','mode','expected_energy','max_energy','scope','prepare','finish_current','timeout','next_floor','task_id'],
                               'defaults':{'floor':1,'mode':'normal','expected_energy':10,'max_energy':0,'prepare':False,'finish_current':False,
                                           'timeout':300,'next_floor':False,'task_id':'guide_02_005_001'},
                               'scope':'normal_floor_parameter_guards'},
                'path.altar': {'parameters':['stage_id','max_energy','scope','prepare','finish_current','timeout','task_id'],
                               'defaults':{'max_energy':0,'prepare':False,'finish_current':False,'timeout':240,
                                           'task_id':'guide_01_004_001'},'scope':'catalogued_altar_stage'},
                'path.equipment': {'parameters':['equipment_action','hero_name','scope','max_gold','material_limits',
                                                 'auto_level','preview','apply_preview','finish_current'],
                                   'defaults':{'max_gold':0,'auto_level':3,'preview':False,'apply_preview':False,'finish_current':False},
                                   'scope':'equip_all_or_enhance_weapon_with_current_item_and_cost_proof'},
                'path.formation': {'parameters':['formation_action','scope','source','destination','member_name','finish_current'],
                                   'defaults':{'finish_current':False},'scope':'calibrated_positions_and_observed_member'},
                'path.navigate': {'parameters':['view','control','expect_view','expect_mode'],
                                  'defaults':{},'scope':'current_calibrated_nonconsuming_control_and_destination'},
                'path.collect': {'parameters':['level','task_id','allow_ready_group'],
                                 'defaults':{'allow_ready_group':False},'scope':'guarded_mission_receipt_and_counter'},
                'path.collect-group': {'parameters':['level','allow_ready_group'],
                                       'defaults':{'allow_ready_group':False},'scope':'group_receipt_and_next_group'},
                'path.finish-stage': {'parameters':['stage_id','timeout'],'defaults':{'timeout':300},
                                      'scope':'pending_prequel_result_and_return_without_start'},
                'battle-auto': {'parameters':['desired'],'defaults':{},'scope':'on_only_when_positively_off'}},
            'session_controls': {'commands':['status','events','snapshot','capabilities','cancel','disconnect'],
                                 'async_parameter':True,'single_emitter':True,'queries_capture':False},
            'plan_contract': {'budgets':['starts','energy','actions','treatments','recovery','attempts','deadline'],
                              'durable_checkpoint':True,'automatic_retry':False,
                              'retry_budget_parameter':'plan_budget',
                              'retry_budget_fields':['max_attempts','max_starts','max_total_energy','max_actions'],
                              'retry_budget_default':None,
                              'identity_fields':['objective_id','plan_id','operation_id','attempt_id'],
                              'resume_requires_original_identity':True,'account_progress':None}}



class Application:
    def __init__(self, config):
        self.config = config

    def execute(self, request, runtime=None):
        if not isinstance(request, Request):
            raise ApplicationError('A aplicação exige um Request.')
        if request.operation == 'capabilities':
            return capabilities(self.config)
        if runtime is None:
            raise ApplicationError('A operação exige uma sessão conectada.', Status.BLOCKED, request.identity)
        if getattr(runtime,'execution_cancelled',False):
            raise ApplicationError('Execução cancelada antes do envio.',Status.CANCELLED,request.identity)
        family, _, operation = request.operation.partition('.')
        values = dict(request.parameters)
        values['command'] = family
        if operation:
            values[family+'_operation'] = operation
        plan_budget=values.pop('plan_budget',None)
        runtime.execution_plan_budget=json.loads(plan_budget) if isinstance(plan_budget,str) else plan_budget
        runtime.execution_identity = request.identity
        runtime.execution_dispatched = False
        retry=values.get('retry_policy')
        runtime.execution_retry=json.loads(retry) if isinstance(retry,str) else retry
        try:
            result = _execute_operation(Parameters(**values), runtime)
        except ApplicationError as exc:
            if exc.identity is None:exc.identity=request.identity
            raise
        except (ValueError,RuntimeError,OSError) as exc:
            status=(Status.UNCERTAIN if runtime.execution_dispatched else Status.CANCELLED
                    if getattr(runtime,'execution_cancelled',False) else Status.BLOCKED)
            raise ApplicationError(str(exc),status,request.identity,
                                   {'input_attempted':runtime.execution_dispatched,
                                    'diagnostics':list(getattr(exc,'__notes__',[]))}) from exc
        if getattr(runtime,'execution_cancelled',False):
            status=Status.UNCERTAIN if runtime.execution_dispatched else Status.CANCELLED
            raise ApplicationError('Execução cancelada; reconciliar entradas já enviadas.',status,request.identity,
                                   {'input_attempted':runtime.execution_dispatched})
        if result is None:
            raise ApplicationError('Operação não disponível: '+request.operation, identity=request.identity)
        if result.get('battle_result')=='defeat':
            status=Status.DEFEAT
        elif 'ui_tree' in result:
            status = Status.OBSERVED
        elif result.get('completed') is True or result.get('postcondition_verified') is True:
            status = Status.COMPLETED
        elif result.get('completed') is False or result.get('needs_review'):
            status = Status.UNCERTAIN
        elif result.get('dispatch_succeeded') is True:
            status = Status.ACCEPTED
        else:
            status = Status.OBSERVED
        return {**result, 'execution': Outcome(request.identity, status, {
            key: result[key] for key in ('completed', 'postcondition_verified', 'dispatch_succeeded',
                                        'observation_error', 'evidence_dir') if key in result}).as_dict()}


def _execute_operation(args, runtime):
    """The same guarded operations for one-shot CLI and persistent sessions."""
    if args.command == 'theater':
        from .theater import run
        return run(runtime, acts=args.acts, max_tickets=args.max_tickets, timeout=args.timeout, taps_per_act=args.taps_per_act, finish_current=args.finish_current)
    if args.command == 'repeat-stage':
        from .repeat_stage import run
        return run(runtime, args.count, args.max_resource, args.timeout)
    if args.command=='path' and args.path_operation=='formation':
        from .formation_operations import graph
        from .path_execution import run_graph
        prior=runtime.path_attempts.read()['stages'].get(args.scope,[])
        if prior and not args.finish_current:
            raise ValueError('Mudança de formação já registrada neste escopo; conferir efeito sem repetir.')
        if args.finish_current:
            from .battle_operations import same_window
            contexts=[e.get('proof',{}).get('operation_context') for e in prior[-1].get('events',[]) if e['phase']=='reserved'] if prior else []
            if len(contexts)!=1 or not contexts[0]:raise ValueError('Contexto da mudança ausente; reconciliar evidências sem nova mutação.')
            ticket=dict(contexts[0])
            if not same_window(ticket.get('window'),runtime.original) or any(ticket.get(k)!=getattr(args,k) for k in ('source','destination','member_name')):
                raise ValueError('Parâmetros/janela divergem da mudança registrada.')
            ticket.update(epoch_seconds=__import__('time').time(),applied=prior[-1]['status'] in ('applied','returned'))
            runtime.path_prepared['formation:'+args.scope]=ticket
        nodes,entry,success=graph(args.scope,args.formation_action,source=args.source,
            destination=args.destination,member_name=args.member_name,finish=args.finish_current)
        return {**run_graph(runtime,nodes,entry,success,180),'formation_operation':args.formation_action,'max_starts':0}
    if args.command=='path' and args.path_operation=='equipment':
        from .equipment_operations import graph
        from .path_execution import run_graph
        from .path_planning import catalog,equipment_operation
        operation=args.equipment_action or equipment_operation(catalog(runtime.config).tasks.get(args.task_id,{}))
        scope=args.scope or args.task_id
        if not scope:raise ValueError('A operação de equipamento exige escopo persistente.')
        prior=runtime.path_attempts.read()['stages'].get(scope,[])
        if prior and not args.finish_current:raise ValueError('Aplicação já registrada; conferir efeito e usar --finish-current sem repetir.')
        if args.finish_current:
            if not prior:raise ValueError('Não há aplicação pendente para reconciliar.')
            from .battle_operations import same_window
            snapshots=[e.get('proof',{}).get('operation_context') for e in prior[-1].get('events',[]) if e['phase']=='reserved']
            if len(snapshots)!=1 or not snapshots[0] or not same_window(snapshots[0].get('window'),runtime.original):
                raise ValueError('Contexto/janela da aplicação ausente ou incompatível; não repetir.')
            ticket=dict(snapshots[0]);ticket['epoch_seconds']=__import__('time').time()
            ticket['applied']=prior[-1]['status'] in ('applied','returned')
            runtime.path_prepared['equipment:'+scope]=ticket
        limits=json.loads(args.material_limits) if isinstance(args.material_limits,str) else args.material_limits or {}
        plan,nodes,entry,success=graph(scope,{'hero_name':args.hero_name,'max_gold':args.max_gold,
            'auto_level':args.auto_level,'material_limits':limits},operation=operation,preview=args.preview,finish=args.finish_current)
        if args.apply_preview:
            apply='Path.Equipment.'+('Equip' if operation=='equip_all' else 'Enhance')+'.Apply'
            entry='Path.Equipment.ApplyEntry'
            nodes[entry]={'recognition':'DirectHit','action':'DoNothing','next':[apply]}
        result=run_graph(runtime,nodes,entry,success,120)
        effect='no_better_equipment' if (result.get('completion_node') or '').endswith('.NoBetter') else ('preview' if args.preview else 'applied_and_returned' if result['completed'] else 'uncertain')
        return {**result,**plan,'equipment_effect':effect}
    if args.command=='path' and args.path_operation=='run-group':
        from pathlib import Path
        from .path_group import compile_group
        from .path_planning import group_id,policy
        from .path_execution import run_graph
        settings=json.loads(Path(args.plan).read_text(encoding='utf-8'))
        limit=settings.get('max_actions',policy()['limits']['max_actions_per_level'])
        if not isinstance(limit,int) or isinstance(limit,bool) or not 1<=limit<=200:
            raise ValueError('Limite de ações do grupo inválido.')
        before=runtime.observe('group_before',read_text=True)
        prefix='claim:'+group_id(args.level)+':'
        ledger=runtime.path_attempts.read()['stages']
        verified=[scope[len(prefix):] for scope,rows in ledger.items()
                  if scope.startswith(prefix) and rows and rows[-1]['status']=='verified']
        from .plans import existing_runtime_plan
        previous=existing_runtime_plan(runtime)
        if previous and previous['specification'].get('requested_settings')!=settings:
            raise ValueError('Grupo retomado exige as escolhas originais do plano.')
        pending_claims=[scope for scope,rows in ledger.items()
                        if (scope.startswith('claim:'+group_id(args.level)+':') or scope=='group_reward:'+group_id(args.level))
                        and rows and rows[-1]['status'] in ('reserved','sent')]
        if pending_claims:
            if not previous or len(pending_claims)!=1:
                raise ValueError('Resgate pendente sem checkpoint único; reconciliar sem repetir Receive.')
            from .path_claims import restore_ticket, graph as claim_graph
            from .plans import run_plan
            scope=pending_claims[0];target=restore_ticket(runtime,scope,previous)
            _,nodes=claim_graph(target['group_id'],target.get('mission_id'),target['before_count'],target['total'],
                                next_group_id=target.get('next_group_id'),resume=True)
            runtime.path_completion_scopes={'Path.Claim.Done':scope}
            try:
                result=run_plan(runtime,previous['specification'],nodes,'Path.Claim.Entry','Path.Claim.Done',args.timeout,
                                resume=True,checkpoint_complete=target['kind']=='group_claim')
                return {**result,'completed':result['completed'] if target['kind']=='group_claim' else False,
                        'postcondition_verified':result['completed'] if target['kind']=='group_claim' else False,
                        'claim_reconciled':result['completed'],'group_completed':result['completed'] if target['kind']=='group_claim' else False,
                        'agent_checkpoint':True,'continuation':'read_group_and_resume_same_plan'}
            finally:runtime.path_completion_scopes={}
        from .observed_ui import quest_view
        checkpoint_view=None
        if quest_view(before).get('group_id')!=group_id(args.level) and previous:
            checkpoint_view=previous['specification'].get('initial_group_view')
        plan,nodes=compile_group(args.level,before,settings,verified,
                                 {**ledger,**runtime.path_battles.read()['stages']},checkpoint_view=checkpoint_view)
        for node in nodes.values():
            params=node.get('custom_recognition_param',{}).get('path',{})
            if not params.get('consuming'):continue
            scope=params.get('task_id') or 'prequel:'+params.get('stage_id','')
            if ledger.get(scope):
                raise ValueError('O plano contém envio já registrado: '+scope+'. Conferir o resultado antes de continuar.')
        actions={name for name,node in nodes.items() if node.get('action','DoNothing')!='DoNothing'}
        if any(nodes[name].get('custom_recognition')!='ScreenTarget' for name in actions):
            raise ValueError('Ação do grupo sem guarda atual ScreenTarget.')
        runtime.path_completion_scopes=plan['claim_completion_scopes']
        runtime.path_group_actions=actions;runtime.path_group_action_limit=limit;runtime.path_group_action_count=0
        runtime.evidence.write('group_plan',{**plan,'max_actions':limit,'settings':settings})
        try:
            from .plans import run_plan, existing_runtime_plan
            previous=existing_runtime_plan(runtime);specification=plan['finite_plan']
            if previous:
                original=previous['specification']
                if original.get('kind')!='path.run-group' or original.get('requested_settings')!=settings:
                    raise ValueError('Retomada do grupo diverge do objetivo/plano original.')
                specification=original
            result=run_plan(runtime,specification,nodes,'Path.Group.Entry','Path.Group.Done',args.timeout,resume=previous is not None)
            return {**result,**plan,'finite_plan':result['finite_plan'],'max_actions':limit,'input_decisions':runtime.path_group_action_count}
        finally:
            runtime.path_completion_scopes={};runtime.path_group_actions=set();runtime.path_group_action_limit=None
    if args.command=='path' and args.path_operation=='abyss':
        from .abyss import graph,identity
        from .battle_operations import run_unit
        scope=args.scope or args.task_id
        compilation=graph(scope,args.max_energy,floor=args.floor,mode=args.mode,
            expected_energy=args.expected_energy,prepare=args.prepare,finish=args.finish_current,next_floor=args.next_floor)
        return run_unit(runtime,'abyss',identity(args.floor,args.mode),scope,compilation,
                        prepare=args.prepare,finish=args.finish_current,timeout=args.timeout)
    if args.command=='path' and args.path_operation=='recover':
        from .path_execution import recovery_graph,run_graph
        from .path_planning import catalog,executor_for
        task=catalog(runtime.config).tasks.get(args.task_id)
        if not task or task['path']!='heir':raise ValueError('Missão ausente do Caminho.')
        graph=recovery_graph(task['group'],task['id'],executor_for(task))
        return {**run_graph(runtime,graph,'Path.Recover.Entry','Path.Recover.Done',60),
                'task_id':task['id'],'max_starts':0,'consuming_actions':0,'recovery':'calibrated_navigation_only'}
    if args.command=='path' and args.path_operation=='acknowledge':
        from .path_execution import acknowledge_graph, run_graph
        return run_graph(runtime,acknowledge_graph(args.view,args.expect_view),
                         'Path.Acknowledge.Entry','Path.Acknowledge.Done',30)
    if args.command=='path' and args.path_operation in ('collect','collect-group'):
        from .path_planning import group_id,route_level,next_progression
        from .observed_ui import quest_view
        from .path_claims import graph
        from .path_execution import run_graph
        if not args.allow_ready_group:
            raise ValueError('Receive pode coletar várias missões prontas do grupo; requer --allow-ready-group.')
        before=runtime.observe('claim_before',read_text=True)
        q=quest_view(before);identity=group_id(args.level);count=q.get('group_counter')
        if q.get('group_id')!=identity or not count:
            raise ValueError('Grupo/contador atual não comprovado.')
        is_group=args.path_operation=='collect-group'
        ready=[t for t in q['visible_tasks'] if t.get('claim_ready') is True and t.get('row_fully_visible') is True
               and (args.task_id is None or t['task_id']==args.task_id)]
        if not is_group and not ready:raise ValueError('Nenhuma recompensa pronta comprovada nessa leitura.')
        mission=None if is_group else ready[0]['task_id']
        following=next_progression(identity,runtime.config)['next_group'] if is_group else None
        if is_group and following is None:
            raise ValueError('O grupo final ainda exige prova própria de resgate, sem próximo grupo.')
        scope,nodes=graph(identity,mission,count['current'],count['total'],next_group_id=following)
        prior=runtime.path_attempts.read()['stages']
        pending=[s for s,rows in prior.items() if (s.startswith('claim:'+identity+':') or s=='group_reward:'+identity)
                 and rows and rows[-1]['status'] in ('reserved','sent')]
        if prior.get(scope) or pending:
            raise ValueError('Resgate já registrado ou pendente de verificação; não repetir Receive.')
        result=run_graph(runtime,nodes,'Path.Claim.Entry','Path.Claim.Done',90)
        if result['completed']:
            latest=runtime.path_attempts.read()['stages'].get(scope,[])
            if latest:runtime.path_attempts.mark(scope,latest[-1]['key'],'verified')
        return {**result,'group_id':identity,'mission_id':mission,'next_group_id':following,
                'verified_scope':'group_reward_and_next_group' if is_group else 'group_count_and_claimed_task_or_full_group'}
    if args.command=='path' and args.path_operation=='altar':
        from .altar import graph
        from .battle_operations import run_unit
        # Mission compatibility is a plan concern, outside the Altar capability.
        from .path_planning import catalog
        task=catalog(runtime.config).tasks.get(args.task_id,{})
        if not args.scope and args.stage_id not in str(task.get('parameters',{}).get('enter','')).split(';'):
            raise ValueError('Este altar não atende à missão solicitada.')
        scope=args.scope or args.task_id
        compilation=graph(args.stage_id,scope,args.max_energy,finish=args.finish_current,prepare=args.prepare)
        return run_unit(runtime,'altar',args.stage_id,scope,compilation,
                        prepare=args.prepare,finish=args.finish_current,timeout=args.timeout)
    if args.command == 'path' and args.path_operation == 'inspect':
        from .path_planning import plan_level
        return plan_level(runtime.observe('path_read', read_text=True), args.level, runtime.config)
    if args.command == 'path' and args.path_operation in ('open','go','navigate'):
        from .path_execution import open_path_graph, go_graph, run_graph
        if args.path_operation == 'open':
            return run_graph(runtime,open_path_graph(),'Path.Open.Entry','Path.Open.Done',45)
        if args.path_operation == 'navigate':
            from .path_execution import navigation_graph
            return run_graph(runtime,navigation_graph(args.view,args.control,args.expect_view,args.expect_mode),
                             'Path.Navigate.Entry','Path.Navigate.Done')
        from .path_planning import catalog, executor_for
        task = catalog(runtime.config).tasks.get(args.task_id)
        if not task or task['path'] != 'heir':
            raise ValueError('Missão ausente do Caminho do Herdeiro.')
        return run_graph(runtime,go_graph(task['group'],task['id'],executor_for(task)),
                         'Path.Go.Entry','Path.Go.Done')
    if args.command == 'path' and args.path_operation == 'execute':
        from .path_execution import free_summon_graph, run_graph
        return run_graph(runtime,free_summon_graph(args.task_id),'Path.Summon.Entry','Path.Summon.Result',60)
    if args.command == 'path' and args.path_operation == 'prepare':
        from .prequel import prepare_graph
        from .path_execution import run_graph
        return run_graph(runtime,prepare_graph(args.stage_id),'Prequel.Prepare.Entry','Prequel.Prepare.Done',35)
    if args.command=='path' and args.path_operation=='campaign':
        from .prequel import campaign_graph
        from .path_execution import run_graph
        plan,graph=campaign_graph(args.from_stage,args.to_stage,args.max_energy)
        prior=runtime.path_battles.read()['stages']
        from .prequel import corrected_team_retry
        from .plans import run_plan, resume_campaign
        resume=any(prior.get('prequel:'+identity) and not corrected_team_retry(prior['prequel:'+identity]) for identity in plan['stage_ids'])
        specification=plan['finite_plan'];entry='Path.Campaign.Entry';success='Path.Campaign.Done'
        if resume:
            policy=runtime.execution_retry or {}
            plan,graph,entry,success=resume_campaign(args.from_stage,args.to_stage,args.max_energy,prior,
                allow_defeat_retry=bool(policy) and policy.get('kind')!='uncertain',
                uncertain_retry_stage=policy.get('stage_id') if policy.get('kind')=='uncertain' else None)
            from .battle_operations import same_window
            for stage_id in plan['stage_ids']:
                rows=prior.get('prequel:'+stage_id,[])
                if rows and rows[-1].get('result_status',rows[-1]['status'])=='victory':
                    if not same_window(rows[-1].get('verification_window'),runtime.original):
                        raise ValueError('Janela da vitória anterior mudou; reconciliar resultado atual sem Start.')
                    runtime.path_prepared['prequel_victory:'+stage_id]={'window':runtime.original}
        runtime.evidence.write('path_campaign_plan',plan)
        result=run_plan(runtime,specification,graph,entry,success,args.timeout,resume=resume)
        return {**result,**plan,'finite_plan':result['finite_plan']}
    if args.command=='path' and args.path_operation=='finish-stage':
        from .prequel import finish_graph
        from .path_execution import run_graph
        prior=runtime.path_battles.read()['stages'].get('prequel:'+args.stage_id,[])
        if not prior or prior[-1]['status'] not in ('reserved','sent','entered','victory'):
            raise ValueError('Não há uma reserva pendente desta fase para concluir.')
        if prior[-1].get('result_status',prior[-1]['status'])=='victory':
            from .battle_operations import same_window
            if not same_window(prior[-1].get('verification_window'),runtime.original):
                raise ValueError('Janela da vitória anterior mudou; reler resultado antes de retornar.')
            runtime.path_prepared['prequel_victory:'+args.stage_id]={'window':runtime.original}
        return {**run_graph(runtime,finish_graph(args.stage_id,prior[-1]['status']=='victory'),'Path.Campaign.Entry','Path.Campaign.Done',args.timeout),
                'stage_ids':[args.stage_id],'max_starts':0,'energy_limit':0}
    if args.command == 'battle-auto':
        return runtime.ensure_auto()
    if args.command == "observe":
        return runtime.observe()
    if args.command == "read-screen":
        return runtime.observe(read_text=True, text_roi=args.roi)
    if args.command == "session":
        return runtime.session_operation(args.session_operation)
    if args.command == "quest":
        if args.quest_operation == "read":
            return runtime.read_quest()
        return runtime.quest_action(args.quest_operation, getattr(args, "identity", None),
                                    getattr(args, "observation", None), getattr(args, "expect", None),
                                    getattr(args, "allow_ready_group", False), getattr(args, "expect_text", None),
                                    getattr(args, "destination_kind", None))
    if args.command == "swipe":
        return runtime.primitive("swipe", point=args.begin, end_point=args.end,
            duration_ms=args.duration_ms, observation=args.observation, from_state=args.from_state)
    if args.command == "finish-battle":
        return runtime.finish_battle(args.timeout)
    if args.command == "chapter":
        return runtime.run_chapter(args.from_stage,args.max_energy,args.timeout,args.finish_current)
    if args.command=="stage":
        return runtime.stage_operation(args.stage_operation,args.stage_id,vars(args).get("max_energy"),vars(args).get("allow_replay",False))
    if args.command == "run":
        return runtime.run(args.routine)
    if args.command == "wait-state":
        if not 0 < args.timeout <= 60:
            raise ValueError("Espera deve estar entre 0 e 60 segundos.")
        return runtime.wait_state(args.state, args.timeout)
    if args.command == "click":
        return runtime.primitive("click", target=args.target, point=args.point,
            observation=args.observation, from_state=args.from_state, expect=args.expect)
    if args.command == "hold":
        return runtime.primitive("hold",point=args.point,observation=args.observation,
            from_state=args.from_state,expect=args.expect,duration_ms=args.duration_ms)
    if args.command == "skill-double-tap":
        from .gestures import SKILL_POINTS
        return runtime.primitive("skill_double_tap", point=SKILL_POINTS[args.slot - 1],
            observation=args.observation, from_state=args.from_state)
    if args.command == "key":
        return runtime.primitive("key", key=args.key, observation=args.observation,
            from_state=args.from_state, expect=args.expect, key_duration_ms=args.duration_ms)

