"""Finite plan contracts and durable boundaries; Maa owns all transitions.

A checkpoint never turns a timeout, an accepted input or a victory into mission
credit. It records intent before dispatch and remains conservative after crashes.
"""
from copy import deepcopy
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import time


COUNTERS = ('actions', 'starts', 'energy', 'treatments', 'recovery')
TREATMENTS = {'story_skip', 'story_hold', 'prequel_story_skip', 'prequel_story_hold',
              'informational_ack', 'notice', 'rewards', 'story_reward', 'confirm_skip'}


def finite_integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError('Limite finito inválido: '+name)
    return value


def graph_limits(graph):
    """Upper bounds from native Maa max_hit, without changing calibrated gestures."""
    limits = dict.fromkeys(COUNTERS, 0)
    for name, node in graph.items():
        if node.get('action', 'DoNothing') == 'DoNothing':
            continue
        hits = finite_integer(node.get('max_hit'), name, 1)
        params = node.get('custom_recognition_param', {})
        path = params.get('path', {})
        limits['actions'] += hits
        if path.get('consuming') or params.get('target') == 'stage_start':
            if hits != 1 or node.get('repeat', 1) != 1:
                raise ValueError('Consumidor do plano admite envio único.')
            if path.get('kind') in ('prequel_start', 'prequel_story_start', 'abyss_start', 'altar_start') or params.get('target') == 'stage_start':
                limits['starts'] += 1
        if path.get('kind') in TREATMENTS or any(part in name for part in ('.Before.', '.After.', 'Finish.')):
            limits['treatments'] += hits
        if 'Recovery.' in name or 'Recover.' in name:
            if path.get('consuming') or params.get('target') == 'stage_start':
                raise ValueError('Recuperação não pode conter consumidor.')
            limits['recovery'] += hits
    return limits


def contract(kind, units, graph, *, energy=0, max_actions=None):
    """Pure compiled contract. Runtime binds identity and absolute deadline later."""
    units = deepcopy(list(units))
    seen = set()
    for unit in units:
        identity = unit.get('unit_id')
        if not isinstance(identity, str) or not identity or identity in seen:
            raise ValueError('Identidade de unidade ausente ou duplicada.')
        if set(unit.get('depends_on', ())) - seen:
            raise ValueError('Dependência ausente ou fora de ordem no plano.')
        seen.add(identity)
    limits = graph_limits(graph)
    limits['energy'] = finite_integer(energy, 'energy')
    if max_actions is not None:
        limits['actions'] = min(limits['actions'], finite_integer(max_actions, 'actions', 1))
    return {'schema_version': 1, 'kind': kind, 'units': units, 'limits': limits,
            'max_attempts_per_unit': 1, 'automatic_retry': False,
            'mission_credit_requires_receipt': True, 'navigation_engine': 'Maa'}


def with_retry_budget(specification, budget):
    """Explicit initial allowance; never inferred from unused energy or defeat."""
    if budget is None:return specification
    if specification.get('retry_budget')==budget:return specification
    if not isinstance(budget,dict):raise ValueError('Retry budget must be explicit finite fields.')
    result=deepcopy(specification)
    attempts=finite_integer(budget.get('max_attempts'),'max_attempts',1)
    if attempts>3:raise ValueError('At most three attempts per unit are supported.')
    starts=finite_integer(budget.get('max_starts'),'max_starts')
    energy=finite_integer(budget.get('max_total_energy'),'max_total_energy')
    actions=finite_integer(budget.get('max_actions'),'max_actions',1)
    if (not specification['limits']['starts']<=starts<=specification['limits']['starts']*attempts
            or energy<specification['limits']['energy'] or actions<specification['limits']['actions']):
        raise ValueError('Retry budget does not cover the original plan or exceeds attempt count.')
    result['limits'].update(starts=starts,energy=energy,actions=actions,
                            treatments=specification['limits']['treatments']*attempts,
                            recovery=specification['limits']['recovery']*attempts)
    result['max_attempts_per_unit']=attempts
    result['retry_budget']=deepcopy(budget)
    return result


def sequential_units(stage_ids, *, prefix='', capability='campaign'):
    result = []
    for stage in stage_ids:
        unit = {'unit_id': prefix+stage, 'capability': capability, 'entity_id': stage,
                'depends_on': [result[-1]['unit_id']] if result else [],
                'ledger_name':'path_battles' if prefix=='prequel:' else 'campaign',
                'ledger_scopes':[prefix+stage]}
        result.append(unit)
    return result


def disposition(entries):
    """Read-only resume advice. A caller must compile a consumer-free continuation."""
    if not entries:
        return 'new'
    last = entries[-1]
    if last.get('result_status', last.get('status')) == 'defeat':
        return 'explicit_defeat_policy'
    if last.get('status') in ('returned', 'verified'):
        return 'completed'
    return 'reconcile_without_consumer'


class PlanCheckpoint:
    def __init__(self, path):
        self.path = Path(path)

    def read(self):
        return json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else None

    def save(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        with temporary.open('w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        temporary.replace(self.path)

    def begin(self, specification, identity, timeout, *, now=None, retry=False, resume=False):
        now = time.time() if now is None else now
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 1 <= timeout <= 3600:
            raise ValueError('Prazo finito do plano deve estar entre 1 e 3600 segundos.')
        fingerprint = sha256(json.dumps(specification, sort_keys=True).encode()).hexdigest()
        prior = self.read()
        if prior:
            if prior['fingerprint'] != fingerprint or prior['identity']['objective_id'] != identity.objective_id:
                raise ValueError('Identidade ou conteúdo do plano diverge do checkpoint.')
            # Recovery is a separate consumer-free operation. Reposting the original
            # graph after a crash could repeat a claim or an already finished Start.
            if resume and prior.get('state') in ('running', 'uncertain'):
                if now >= prior['deadline_epoch_seconds']:
                    raise ValueError('Prazo original do plano expirou.')
                prior.update(identity=identity.as_dict(), state='running')
                self.save(prior)
                return prior
            if not retry or prior.get('state') != 'defeat':
                raise ValueError('Plano já registrado; reconciliar unidades sem repetir consumidores.')
            if prior['identity']['attempt_id'] == identity.attempt_id:
                raise ValueError('Nova tentativa exige identidade própria.')
            if now >= prior['deadline_epoch_seconds']:
                raise ValueError('Prazo original do plano expirou.')
            if prior['attempts'] >= specification['max_attempts_per_unit']:
                raise ValueError('Limite de tentativas do plano atingido.')
            prior.update(identity=identity.as_dict(), state='running', attempts=prior['attempts']+1)
            self.save(prior)
            return prior
        data = {'schema_version': 1, 'fingerprint': fingerprint, 'identity': identity.as_dict(),
                'specification': deepcopy(specification), 'state': 'running', 'attempts': 1,
                'deadline_epoch_seconds': now+timeout, 'used': dict.fromkeys(COUNTERS, 0),
                'events': []}
        self.save(data)
        return data

    def charge(self, node, params, *, input_action=True, now=None, proof=None):
        data = self.read()
        now = time.time() if now is None else now
        if not data or data['state'] != 'running' or now >= data['deadline_epoch_seconds']:
            raise ValueError('Plano ausente, encerrado ou com prazo expirado.')
        if not input_action:
            return
        path = params.get('path', {})
        costs = dict.fromkeys(COUNTERS, 0); costs['actions'] = 1
        if path.get('kind') in ('prequel_start', 'prequel_story_start', 'abyss_start', 'altar_start') or params.get('target') == 'stage_start':
            costs['starts'] = 1
            costs['energy'] = path.get('energy', 0)
        if path.get('kind') in TREATMENTS or any(part in node for part in ('.Before.', '.After.', 'Finish.')):
            costs['treatments'] = 1
        if 'Recovery.' in node or 'Recover.' in node:
            costs['recovery'] = 1
        for key, value in costs.items():
            finite_integer(value, key)
            if data['used'][key]+value > data['specification']['limits'][key]:
                raise ValueError('Orçamento do plano atingido: '+key)
        for key, value in costs.items():
            data['used'][key] += value
        data['events'].append({'node': node, 'phase': 'dispatch_reserved', 'costs': costs, 'epoch_seconds': now, 'proof': deepcopy(proof or {}),
                               'identity':deepcopy(data['identity']), 'semantic_target':deepcopy(path)})
        self.save(data)

    def finish(self, result=None, error=None):
        data = self.read()
        data['state'] = ('uncertain' if error else 'defeat' if (result or {}).get('battle_result') == 'defeat'
                         else 'completed' if (result or {}).get('completed') is True else 'uncertain')
        data['result'] = {key: (result or {}).get(key) for key in
                          ('completed', 'completion_node', 'battle_result', 'evidence_dir', 'input_decisions')}
        current_nodes=[row['name'] for row in (result or {}).get('nodes', []) if row.get('completed')]
        data['completed_nodes']=list(dict.fromkeys(data.get('completed_nodes',[])+current_nodes))
        after=(result or {}).get('after') or {}
        data['observation_reference'] = {key:after.get(key) for key in ('observation_id','window','epoch_seconds')}
        data['error'] = str(error) if error else None
        data.setdefault('checkpoints',[]).append({'identity':deepcopy(data['identity']),
            'result':deepcopy(data['result']),'completed_nodes':current_nodes,
            'observation_reference':deepcopy(data['observation_reference']),
            'state':data['state'],'error':data['error'],'epoch_seconds':time.time()})
        self.save(data)
        return {'path': str(self.path), 'state': data['state'], 'used': data['used'],
                'deadline_epoch_seconds': data['deadline_epoch_seconds']}


def run_plan(runtime, specification, graph, entry, success, timeout, *, resume=False, checkpoint_complete=True):
    """One Maa task under a durable budget; never schedules or retries units."""
    from .path_execution import run_graph
    checkpoint = begin_runtime_plan(runtime, specification, timeout, resume=resume)
    try:
        remaining=min(timeout,checkpoint.read()['deadline_epoch_seconds']-time.time())
        if remaining<1:raise ValueError('Prazo do plano expirou antes da tarefa Maa.')
        result = run_graph(runtime, graph, entry, success, remaining)
        proof = checkpoint.finish(result if checkpoint_complete else {**result,'completed':False})
        return {**result, 'finite_plan': checkpoint.read()['specification'], 'plan_checkpoint': proof}
    except Exception as exc:
        try:checkpoint.finish(error=exc)
        except Exception as checkpoint_error:
            exc.add_note('Checkpoint persistence failed: '+str(checkpoint_error))
        raise
    finally:
        runtime.active_plan_checkpoint = None


def resume_campaign(first, last, max_energy, entries, *, allow_defeat_retry=False, uncertain_retry_stage=None):
    """Compile remaining units once; an existing entry gets no Start/Row/Ready.

    Completed units are omitted. Pending units receive only their calibrated
    completion graph, followed by still-new units. Maa owns recovery branches.
    """
    from .prequel import campaign_graph, finish_graph, stage
    from .composition import append_fragment, validate_graph
    plan, original = campaign_graph(first, last, max_energy)
    nodes = {}; previous = None; entry = 'Plan.Resume.Entry'; remaining = []
    energy = 0; starts = 0
    for stage_id in plan['stage_ids']:
        rows = entries.get('prequel:'+stage_id, [])
        state = disposition(rows)
        if state == 'completed':
            continue
        if state == 'explicit_defeat_policy' and not allow_defeat_retry:
            raise ValueError('Derrota exige política explícita de ajuste; retomada não repete Start.')
        unknown_retry = (state == 'reconcile_without_consumer' and stage_id == uncertain_retry_stage
                         and rows and rows[-1].get('status') in ('reserved', 'sent', 'entered', 'uncertain')
                         and rows[-1].get('result_status') is None)
        if state == 'new' or (state=='explicit_defeat_policy' and allow_defeat_retry) or unknown_retry:
            _, fragment = campaign_graph(stage_id, stage_id, stage(stage_id)['energy'])
            energy += stage(stage_id)['energy']; starts += 1
        else:
            fragment = finish_graph(stage_id, rows[-1].get('result_status', rows[-1]['status']) == 'victory')
        names = append_fragment(nodes, fragment, 'Resume.'+stage_id+'.')
        if previous:
            nodes[previous]['next'] = [names['Path.Campaign.Entry']]
        else:
            nodes[entry] = {'recognition': 'DirectHit', 'action': 'DoNothing', 'next': [names['Path.Campaign.Entry']]}
        previous = names['Path.Campaign.Done']; remaining.append(stage_id)
    if not remaining:
        raise ValueError('Todas as unidades já foram concluídas; nenhum consumidor será repetido.')
    nodes['Plan.Resume.Done'] = deepcopy(nodes[previous]); nodes['Plan.Resume.Done'].pop('next', None)
    nodes[previous]['next'] = ['Plan.Resume.Done']
    validate_graph(nodes, entry, ['Plan.Resume.Done'])
    plan.update(stage_ids=remaining, energy_limit=energy, max_starts=starts)
    return plan, nodes, entry, 'Plan.Resume.Done'


def begin_runtime_plan(runtime, specification, timeout, *, resume=False):
    """Bind a checkpoint for a caller that already owns its single Maa task."""
    identity = runtime.execution_identity
    token = sha256(identity.plan_id.encode()).hexdigest()
    checkpoint = PlanCheckpoint(Path(runtime.config['path_ledger']).parent/'plans'/(token+'.json'))
    specification=with_retry_budget(specification,getattr(runtime,'execution_plan_budget',None))
    checkpoint.begin(specification, identity, timeout,
                     retry=bool(getattr(runtime, 'execution_retry', None)), resume=resume)
    runtime.active_plan_checkpoint = checkpoint
    return checkpoint


def existing_runtime_plan(runtime):
    token=sha256(runtime.execution_identity.plan_id.encode()).hexdigest()
    path=Path(runtime.config['path_ledger']).parent/'plans'/(token+'.json')
    return PlanCheckpoint(path).read()


def resume_chapter(config, from_stage, max_energy, entries, *, allow_defeat_retry=False):
    """Build one Maa remainder; pending entries have only result/return nodes."""
    from .chapters import compile_chapter
    from .composition import append_fragment, validate_graph
    from .execution import annotate_campaign_result
    plan, original=compile_chapter(config,from_stage,max_energy)
    graph={};previous=None;remaining=[];energy=0;starts=0
    for stage_id in plan['stage_ids']:
        rows=entries.get(stage_id,[]);state=disposition(rows)
        if state=='completed':continue
        if state=='explicit_defeat_policy' and not allow_defeat_retry:
            raise ValueError('Derrota exige política explícita; retomada não repete Start.')
        if state=='new' or (state=='explicit_defeat_policy' and allow_defeat_retry):
            prefix='Chapter.'+stage_id+'.'
            fragment={name.removeprefix(prefix):deepcopy(node) for name,node in original.items() if name.startswith(prefix)}
            # Extracted references still have chapter prefixes; remove only local
            # edges and close this stage's continuation before composition.
            for node in fragment.values():
                for field in ('next','on_error'):
                    if field in node:
                        node[field]=[target.removeprefix(prefix) if target.startswith(prefix) else 'Unit.Done' for target in node[field]]
            fragment['Unit.Done']={'recognition':'DirectHit','action':'DoNothing'}
            entry='Stage.Entry';success='Unit.Done';starts+=1
            from .stages import load_stages
            energy+=load_stages(config['stage_file'])[stage_id]['energy']
        else:
            fragment=json.loads((config['resource_dir']/'pipeline/battle_finish.json').read_text(encoding='utf-8'))
            fragment={k:v for k,v in fragment.items() if not k.startswith('$')}
            annotate_campaign_result(fragment,stage_id,rows[-1]['key'],require_three_stars=True)
            entry='Finish.Entry';success='Finish.VerifyDone'
        names=append_fragment(graph,fragment,'Resume.'+stage_id+'.')
        if previous:graph[previous]['next']=[names[entry]]
        else:graph['Plan.Resume.Entry']={'recognition':'DirectHit','action':'DoNothing','next':[names[entry]]}
        previous=names[success];remaining.append(stage_id)
    if not remaining:raise ValueError('Todas as unidades já concluídas; não repetir Start.')
    graph['Plan.Resume.Done']=deepcopy(graph[previous]);graph['Plan.Resume.Done'].pop('next',None)
    graph[previous]['next']=['Plan.Resume.Done']
    validate_graph(graph,'Plan.Resume.Entry',['Plan.Resume.Done'])
    plan.update(stage_ids=remaining,energy_limit=energy,max_starts=starts)
    return plan,graph,'Plan.Resume.Entry','Plan.Resume.Done'
