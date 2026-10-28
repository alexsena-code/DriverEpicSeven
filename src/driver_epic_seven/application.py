"""Shared local application. Transports adapt arguments; Maa owns execution."""
import json
from types import SimpleNamespace

from .contracts import Request, Outcome, Status, ApplicationError
from .pipelines import registry


def capabilities(config):
    """Read existing sources only; mapped families are never executable claims."""
    from .path_planning import catalog
    cat = catalog(config)
    return {'read_only': True, 'requires_current_action_guards': True,
            'routines': registry(config),
            'mapped_families': sorted(set(cat.families.values())),
            'mapped_families_source': str(config['operation_map_file']),
            'mapped_families_are_executors': False,
            'validation_scope': 'docs/validation.md', 'account_access': None}


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
        family, _, operation = request.operation.partition('.')
        values = dict(request.parameters)
        values['command'] = family
        if operation:
            values[family+'_operation'] = operation
        runtime.execution_identity = request.identity
        result = _execute_operation(SimpleNamespace(**values), runtime)
        if result is None:
            raise ApplicationError('Operação não disponível: '+request.operation, identity=request.identity)
        if 'ui_tree' in result:
            status = Status.OBSERVED
        elif result.get('completed') is True or result.get('postcondition_verified') is True:
            status = Status.COMPLETED
        elif result.get('completed') is False or result.get('needs_review'):
            status = Status.UNCERTAIN
        else:
            status = Status.OBSERVED
        return {**result, 'execution': Outcome(request.identity, status, {
            key: result[key] for key in ('completed', 'postcondition_verified', 'dispatch_succeeded',
                                        'observation_error', 'evidence_dir') if key in result}).as_dict()}


def _execute_operation(args, runtime):
    """The same guarded operations for one-shot CLI and persistent sessions."""
    if args.command=='path' and args.path_operation=='equipment':
        from .equipment_operations import graph
        from .path_execution import run_graph
        prior=runtime.path_attempts.read()['stages'].get(args.task_id,[])
        if prior:raise ValueError('Aplicação já registrada; conferir efeito e missão antes de qualquer novo envio.')
        plan,nodes,entry,success=graph(args.task_id,{'hero_name':args.hero_name,'max_gold':args.max_gold},preview=args.preview)
        if args.apply_preview:
            entry='Path.Equipment.'+('Equip' if args.task_id=='guide_02_004_001' else 'Enhance')+'.Apply'
        result=run_graph(runtime,nodes,entry,success,120)
        if result['completed'] and not args.preview:
            latest=runtime.path_attempts.read()['stages'].get(args.task_id,[])
            if latest:runtime.path_attempts.mark(args.task_id,latest[-1]['key'],'applied')
        return {**result,**plan}
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
        plan,nodes=compile_group(args.level,before,settings,verified)
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
            result=run_graph(runtime,nodes,'Path.Group.Entry','Path.Group.Done',args.timeout)
            return {**result,**plan,'max_actions':limit,'input_decisions':runtime.path_group_action_count}
        finally:
            runtime.path_completion_scopes={};runtime.path_group_actions=set();runtime.path_group_action_limit=None
    if args.command=='path' and args.path_operation=='abyss':
        from .abyss import graph
        from .path_execution import run_graph
        prior=runtime.path_attempts.read()['stages'].get(args.task_id,[])
        if args.finish_current:
            if not prior or prior[-1]['status'] not in ('reserved','sent','victory'):
                raise ValueError('Não há entrada pendente de Abyss para concluir.')
            if prior[-1]['status']=='victory':
                recorded=prior[-1].get('verification_window')
                if not recorded or any(recorded.get(k)!=runtime.original.get(k) for k in ('hwnd','pid','process_name','window_class','client_size')):
                    raise ValueError('A janela da prova de vitória não confere; reler o resultado atual.')
                runtime.path_prepared['abyss_victory:abyss001']={'window':runtime.original}
        elif not args.prepare and prior:
            raise ValueError('Abyss já iniciado para esta missão; conferir resultado e usar --finish-current.')
        plan,nodes,entry,success=graph(args.task_id,args.max_energy,prepare=args.prepare,finish=args.finish_current)
        result=run_graph(runtime,nodes,entry,success,args.timeout)
        if result['completed'] and not args.prepare:
            latest=runtime.path_attempts.read()['stages'].get(args.task_id,[])
            if latest:runtime.path_attempts.mark(args.task_id,latest[-1]['key'],'returned')
        return {**result,**plan}
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
        from .path_execution import run_graph
        prior=runtime.path_attempts.read()['stages'].get(args.task_id,[])
        if args.finish_current:
            if not prior or prior[-1]['status'] not in ('reserved','sent','victory'):
                raise ValueError('Não há entrada pendente de Altar para concluir.')
            if prior[-1]['status']=='victory':
                recorded=prior[-1].get('verification_window')
                if recorded and any(recorded.get(k)!=runtime.original.get(k) for k in ('hwnd','pid','process_name','window_class','client_size')):
                    raise ValueError('A janela mudou desde a prova de vitória; conferir a fase atual.')
                runtime.path_prepared['altar_victory:'+args.stage_id]={'epoch_seconds':0,'window':runtime.original}
        elif not args.prepare and prior:
            raise ValueError('Altar já iniciado para esta missão; conferir resultado e usar --finish-current.')
        plan,nodes,entry,success=graph(args.stage_id,args.task_id,args.max_energy,
                                     finish=args.finish_current,prepare=args.prepare)
        result=run_graph(runtime,nodes,entry,success,args.timeout)
        if result['completed'] and not args.prepare:
            latest=runtime.path_attempts.read()['stages'].get(args.task_id,[])
            if latest:runtime.path_attempts.mark(args.task_id,latest[-1]['key'],'returned')
        return {**result,**plan}
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
        if any(prior.get('prequel:'+identity) and not corrected_team_retry(prior['prequel:'+identity]) for identity in plan['stage_ids']):
            raise ValueError('O trecho contém uma fase já iniciada. Confira o diário e use finish-stage para uma entrada pendente; não repetir Start.')
        runtime.evidence.write('path_campaign_plan',plan)
        return {**run_graph(runtime,graph,'Path.Campaign.Entry','Path.Campaign.Done',args.timeout),**plan}
    if args.command=='path' and args.path_operation=='finish-stage':
        from .prequel import finish_graph
        from .path_execution import run_graph
        prior=runtime.path_battles.read()['stages'].get('prequel:'+args.stage_id,[])
        if not prior or prior[-1]['status'] not in ('reserved','sent','entered','victory'):
            raise ValueError('Não há uma reserva pendente desta fase para concluir.')
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
        return runtime.stage_operation(args.stage_operation,args.stage_id,getattr(args,"max_energy",None),getattr(args,"allow_replay",False))
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

