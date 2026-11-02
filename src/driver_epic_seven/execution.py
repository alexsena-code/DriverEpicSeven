"""Persistent action boundary, separate from pure image recognition.

Maa invokes the boundary after its recognition and before a single native
action. No retries, captures, OCR or next-node scheduling happen here.
"""
from copy import deepcopy
from dataclasses import fields
import json
import time

from .contracts import Identity, Status
from .observed_ui import operation_view


def annotate_campaign_result(nodes, scope, key=None, *, require_three_stars=False):
    """Bind known template roles explicitly before any prefixing/copying."""
    roles={'Finish.Clear':('result_verified','victory'), 'Finish.Defeat':('defeat','defeat'),
           'Finish.VerifyDone':('return_verified','returned')}
    for name,(phase,status) in roles.items():
        if name in nodes:
            nodes[name].setdefault('custom_recognition_param',{})['execution']={
                'ledger':'campaign','scope':scope,'key':key,'phase':phase,'status':status,
                'requires_result':phase=='return_verified'}
    if require_three_stars and 'Finish.Clear' in nodes:
        nodes['Finish.Clear']['custom_recognition_param'].update(require_three_stars=True,read_text=True)
        nodes['Finish.CriteriaUnverified']={'recognition':'Custom','custom_recognition':'ScreenTarget',
            'custom_recognition_param':{'state':'stage_clear','read_text':True,'three_star_checkpoint':True,
                'execution':{'ledger':'campaign','scope':scope,'key':key,'phase':'result_verified','status':'victory'}},
            'action':'DoNothing','max_hit':1}
        for node in nodes.values():
            if 'Finish.Clear' in node.get('next',[]) and 'Finish.CriteriaUnverified' not in node['next']:
                node['next'].insert(node['next'].index('Finish.Clear'),'Finish.CriteriaUnverified')


def wrap_graph(graph):
    """Wrap existing ScreenTarget actions while retaining Maa graph controls."""
    result = deepcopy(graph)
    for name, node in result.items():
        if node.get('custom_recognition') != 'ScreenTarget' or node.get('custom_action') == 'OperationBoundary':
            continue
        params = node.get('custom_recognition_param',{})
        if not (params.get('path') or params.get('target')=='stage_start' or params.get('execution')
                or node.get('action','DoNothing')!='DoNothing'):
            continue
        native = node.get('action','DoNothing')
        if not isinstance(native,str):
            raise ValueError('Formato de ação ainda não suportado na fronteira.')
        if params.get('path',{}).get('consuming') and (node.get('repeat',1)!=1 or node.get('max_hit')!=1):
            raise ValueError('Ação consumidora exige envio único no grafo Maa.')
        node['action'] = 'Custom'
        node['custom_action'] = 'OperationBoundary'
        # Resolve the original target/offset exactly once in the native action.
        # The callback must receive the recognition box, not an adjusted target.
        node['target'] = True
        node['target_offset'] = [0,0,0,0]
        node['custom_action_param'] = {'recognition':deepcopy(params),'native_action':native,
                                      'native_parameters':deepcopy(graph[name])}
    return result


def native_action(context, specification, box, detail):
    """One native action on this same Maa context/controller, without next."""
    from maa import pipeline
    kind = specification['native_action']
    if kind == 'DoNothing':
        return True
    classes = {'Click':pipeline.JClick,'LongPress':pipeline.JLongPress,
               'LongPressKey':pipeline.JLongPressKey,'Swipe':pipeline.JSwipe}
    if kind not in classes:
        raise ValueError('Ação nativa não suportada pela fronteira: '+kind)
    cls = classes[kind]
    values = {f.name:deepcopy(specification['native_parameters'][f.name]) for f in fields(cls)
              if f.name in specification['native_parameters']}
    if kind == 'Swipe':
        # Pipeline v1 accepts scalar duration and a single flat end point;
        # the SDK dataclass uses a list for each swipe segment.
        if isinstance(values.get('duration'),int): values['duration']=[values['duration']]
        if isinstance(values.get('end'),list) and values['end'] and isinstance(values['end'][0],(int,float)):
            values['end']=[values['end']]
    action = context.run_action_direct(kind,cls(**values),box,json.dumps(detail))
    return bool(action and action.success)


def boundary_action(runtime):
    """The SDK callback is a refusal-capable boundary, not a log callback."""
    from maa.custom_action import CustomAction
    class OperationBoundary(CustomAction):
        def run(self, context, argv):
            try:
                specification=json.loads(argv.custom_action_param)
                best=argv.reco_detail.best_result
                analysis=best.detail if best else None
                if isinstance(analysis,str):analysis=json.loads(analysis)
                if not isinstance(analysis,dict):
                    raise ValueError('Ação sem prova do reconhecimento correspondente.')
                return runtime.operation_cycle.dispatch(argv.node_name,specification['recognition'],analysis,
                    lambda:native_action(context,specification,argv.box,analysis),
                    input_action=specification['native_action']!='DoNothing')
            except Exception as exc:
                if not getattr(runtime,'execution_cancelled',False):
                    runtime.fatal=str(exc)
                if hasattr(runtime,'observer'):
                    try:runtime.observer.invalidate('operation_boundary_failed')
                    except Exception:pass  # Native callbacks must return a refusal.
                return False
    return OperationBoundary()


class OperationCycle:
    def __init__(self, runtime):
        self.runtime = runtime

    def _identity(self):
        return getattr(self.runtime,'execution_identity',None) or Identity()

    @staticmethod
    def proof(analysis, node):
        tree=analysis.get('ui_tree',{})
        return {'observation_id':tree.get('observation_id'),'window':deepcopy(analysis.get('window')),
                'observed_at_epoch_seconds':analysis.get('epoch_seconds'),
                'node':node,'view':operation_view(analysis).get('view')}

    def _reserve(self, params, identity, proof, analysis):
        r=self.runtime; path=params.get('path',{})
        if not path.get('consuming') and params.get('target')!='stage_start':
            return None
        kind=path.get('kind')
        scope=path.get('task_id') or ('prequel:'+path['stage_id'] if path else params['stage_id'])
        ledger=(r.path_battles if kind in ('prequel_start','prequel_story_start') else r.path_attempts) if path else r.attempts
        if ledger is None:
            raise ValueError('Entrada consumidora sem diário configurado.')
        key=identity.attempt_id+':'+scope
        entries=ledger.read()['stages'].get(scope,[])
        if str(kind).startswith('formation_'):
            for rows in ledger.read()['stages'].values():
                for row in rows:
                    targets=[e.get('proof',{}).get('target',{}) for e in row.get('events',[])]
                    if row['status'] not in ('applied','returned','verified') and any(
                            str(t.get('kind','')).startswith('formation_') for t in targets):
                        raise ValueError('Mudança de formação anterior pendente; reler composição sem repetir a mutação.')
        if kind in ('equipment_enhance','equipment_confirm_change'):
            for other_scope,rows in ledger.read()['stages'].items():
                if other_scope==scope:continue
                for row in rows:
                    if row['status'] in ('applied','returned','verified'):continue
                    targets=[e.get('proof',{}).get('target',{}) for e in row.get('events',[])]
                    same=any(str(t.get('kind','')).startswith('equipment_') and t.get('hero_name')==path.get('hero_name') for t in targets)
                    legacy='.Equipment.' in row['key'] and not targets
                    if same or legacy:raise ValueError('Aplicação anterior pendente neste herói; reconciliar sem repetir sob outro objetivo.')
        # A new objective/scope must not hide an unresolved entry of the same
        # physical battle. Legacy Maa keys retain the stage as a delimited part.
        stage=path.get('stage_id')
        if stage and kind in ('abyss_start','altar_start','prequel_start','prequel_story_start'):
            for other_scope,rows in ledger.read()['stages'].items():
                if other_scope==scope:continue
                for row in rows:
                    targets=[e.get('proof',{}).get('target',{}) for e in row.get('events',[])]
                    same=any(t.get('stage_id')==stage for t in targets) or '.'+stage+'.' in row['key']
                    if same and row.get('result_status',row.get('status'))=='defeat':
                        raise ValueError('Nova tentativa após derrota deve conservar o escopo e usar política finita explícita.')
                    if same and row.get('result_status',row.get('status')) not in ('victory','defeat','returned'):
                        raise ValueError('Entrada pendente da mesma batalha em outro objetivo; reconciliar sem novo Start.')
        # Even the same attempt cannot be dispatched again. A reservation is
        # not permission to replay after a partial write or disconnected host.
        if any(row['key']==key for row in entries):
            raise ValueError('Tentativa já reservada; reconciliar sem repetir a entrada.')
        battle=kind in ('abyss_start','altar_start','prequel_start') or params.get('target')=='stage_start'
        retry=None
        if battle and entries and entries[-1].get('result_status',entries[-1]['status'])=='defeat':
            from .retries import check_retry
            cost=path.get('energy',0) if path else r.stage_inspector.get(params['stage_id'])['energy']
            retry=check_retry(entries,identity,getattr(r,'execution_retry',None),cost,analysis['window'],limit=ledger.limit)
            proof['retry_authorization']=retry
        if kind in ('prequel_start','abyss_start') and entries and (getattr(r,'execution_retry',None) or {}).get('kind') == 'uncertain':
            from .retries import check_uncertain_retry
            retry=check_uncertain_retry(entries, identity, r.execution_retry, path.get('energy',0),
                                        analysis['window'], path['stage_id'], limit=ledger.limit)
            proof['retry_authorization']=retry
        if not path and entries and entries[-1]['status'] in ('reserved','sent','entered','cancelled'):
            raise ValueError('Entrada anterior sem resultado comprovado; reconciliar sem novo Start.')
        cost=path.get('energy',0) if path else r.stage_inspector.get(params['stage_id'])['energy']
        if kind=='theater_confirm':
            cost=1
            proof['resource_cost']={'currency':'theater_ticket','amount':1}
            proof['operation_context']=deepcopy(r.path_prepared.get('theater:'+scope,{}))
        if kind=='equipment_enhance':
            contexts=[i for i in operation_view(analysis).get('items',[]) if i.get('semantic_id')=='context']
            cost=contexts[0]['gold_cost'] if len(contexts)==1 else None
            if not isinstance(cost,int) or cost<0:raise ValueError('Custo de melhoria desconhecido.')
        if kind in ('equipment_enhance','equipment_confirm_change'):
            proof['operation_context']=deepcopy(r.path_prepared.get('equipment:'+scope,{}))
            if kind=='equipment_enhance':
                info=operation_view(analysis).get('items',[{}])[0]
                proof['operation_context'].update(gold_cost=info.get('gold_cost'),gold_balance=info.get('gold_balance'))
        if str(kind).startswith('formation_'):
            proof['operation_context']=deepcopy(r.path_prepared.get('formation:'+scope,{}))
        if kind in ('prequel_start','prequel_story_start'):
            from .prequel import reserve_entry
            if retry:ledger.reserve(scope,key,cost)
            else:reserve_entry(ledger,path['stage_id'],key,cost,analysis)
        else:
            # Existing single-use Path scopes stay single-use across requests.
            if path and entries and not retry:
                raise ValueError('Operação já registrada neste escopo; conferir efeito antes de outro envio.')
            ledger.reserve(scope,key,cost)
        ledger.record(scope,key,Status.RESERVED,identity=identity.as_dict(),proof=proof)
        if not path:
            r.start_reservations[proof['node']]=(scope,key)
            r.current_campaign_reservation=(scope,key)
        return ledger,scope,key

    def dispatch(self, node, params, analysis, send, *, input_action=True):
        r=self.runtime
        current=r.guard(input_active=True)
        if not analysis.get('window') or any(analysis['window'].get(k)!=current.get(k)
                for k in ('hwnd','pid','process_name','window_title','window_class','client_size')):
            raise ValueError('A prova da ação pertence a outra janela.')
        if not 0<=time.time()-analysis.get('epoch_seconds',0)<=30:
            raise ValueError('A prova da ação expirou antes do envio.')
        identity=self._identity(); proof=self.proof(analysis,node)
        checkpoint=getattr(r,'active_plan_checkpoint',None)
        if checkpoint:
            budget_params=deepcopy(params)
            if params.get('target')=='stage_start':
                budget_params.setdefault('path',{})['energy']=r.stage_inspector.get(params['stage_id'])['energy']
            checkpoint.charge(node,budget_params,input_action=input_action,proof=proof)
        path=params.get('path',{})
        proof['target']={k:deepcopy(path[k]) for k in ('kind','stage_id','task_id','group_id','mission_id','hero_name') if k in path}
        if str(path.get('kind','')).startswith('formation_'):
            proof['target'].update({k:deepcopy(path[k]) for k in ('source','destination','member_name') if k in path})
        if not path:proof['target']={k:params[k] for k in ('stage_id','target','state') if k in params}
        if node in r.path_group_actions:
            if r.path_group_action_count>=r.path_group_action_limit:
                raise RuntimeError('Limite de ações do grupo atingido; revisar antes de continuar.')
            r.path_group_action_count+=1
            r.observer.count('group_input_decisions')
        self._observe_effect(path,analysis,proof,identity)
        event=params.get('execution')
        if event:
            ledger=r.attempts if event['ledger']=='campaign' else r.path_attempts
            entries=ledger.read()['stages'].get(event['scope'],[])
            if event.get('key') is not None:entries=[e for e in entries if e['key']==event['key']]
            if event.get('requires_result'):
                from .battle_operations import same_window
                wins=[e.get('proof',{}) for e in entries[-1].get('events',[]) if e['phase']==Status.RESULT] if entries else []
                if (not entries or entries[-1].get('result_status')!='victory' or not any(
                        p.get('observation_id') and same_window(p.get('window'),analysis['window']) for p in wins)):
                    raise ValueError('Retorno sem prova de vitória vinculada à tentativa/janela; não avançar nem repetir Start.')
            self._mark(ledger,event['scope'],event['status'],event['phase'],proof,key=event.get('key'))
        reservation=self._reserve(params,identity,proof,analysis)
        if reservation:
            ledger,scope,key=reservation
            ledger.record(scope,key,Status.ATTEMPTED,identity=identity.as_dict(),proof=proof)
        r.observer.event('operation_dispatch',identity=identity.as_dict(),proof=proof,consuming=bool(reservation))
        try:
            r.guard(input_active=True)
            if input_action:r.execution_dispatched=True
            accepted=bool(send())
        except Exception:
            if reservation:
                ledger.record(scope,key,Status.UNCERTAIN,identity=identity.as_dict(),proof=proof)
            raise
        if reservation:
            ledger.record(scope,key,Status.ACCEPTED if accepted else Status.UNCERTAIN,
                          identity=identity.as_dict(),proof=proof,status='sent' if accepted else None)
        if accepted:
            self._prepare(path,analysis)
            if node in r.path_group_actions:r.observer.count('group_native_input_actions')
            scope=r.path_completion_scopes.get(node)
            if scope:self._mark(r.path_attempts,scope,'verified',Status.COMPLETED,proof)
        return accepted

    def _mark(self, ledger, scope, status, phase, proof, key=None):
        entries=ledger.read()['stages'].get(scope,[])
        if key is not None:entries=[e for e in entries if e['key']==key]
        if entries:
            entry=entries[-1]
            window=entry.get('verification_window') or next((e.get('proof',{}).get('window')
                    for e in entry.get('events',[]) if e.get('phase')==Status.RESERVED),None)
            if window and any(window.get(k)!=proof.get('window',{}).get(k)
                    for k in ('hwnd','pid','process_name','window_title','window_class','client_size')):
                raise ValueError('Janela da prova incompatível com a reserva.')
            identity=entry.get('identity') or self._identity().as_dict()
            ledger.record(scope,entry['key'],phase,identity=identity,proof=proof,status=status)

    def _observe_effect(self, path, analysis, proof, identity):
        """A recognized result remains true even if its following input fails."""
        r=self.runtime; kind=path.get('kind'); stage=path.get('stage_id')
        if kind in ('abyss_advance','abyss_result_back','altar_advance'):
            family='altar' if kind=='altar_advance' else 'abyss'
            r.path_prepared[family+'_victory:'+stage]={'window':analysis['window']}
            self._mark(r.path_attempts,path['task_id'],'victory',Status.RESULT,proof)
        if kind in ('prequel_clear','prequel_map_return','prequel_story_done'):
            if kind=='prequel_clear':r.path_prepared['prequel_victory:'+stage]={'window':analysis['window']}
            if kind=='prequel_story_done':
                # The story receipt + calibrated map guard prove this story's
                # effect; return alone cannot settle a sent battle reservation.
                self._mark(r.path_battles,'prequel:'+stage,'applied',Status.RESULT,proof)
            self._mark(r.path_battles,'prequel:'+stage,
                       'victory' if kind=='prequel_clear' else 'returned',
                       Status.RESULT if kind=='prequel_clear' else Status.RETURNED,proof)
        if kind in ('abyss_done','altar_done'):
            self._mark(r.path_attempts,path['task_id'],'returned',Status.RETURNED,proof)
        if kind in ('equipment_equipped','equipment_enhanced'):
            self._mark(r.path_attempts,path['task_id'],'applied',Status.RESULT,proof)
            ticket=r.path_prepared.get('equipment:'+path['task_id'])
            if ticket:ticket.update(applied=True,epoch_seconds=time.time())
        if kind=='equipment_returned':self._mark(r.path_attempts,path['task_id'],'returned',Status.RETURNED,proof)
        if kind in ('formation_applied','formation_removed'):
            self._mark(r.path_attempts,path['task_id'],'applied',Status.RESULT,proof)
            ticket=r.path_prepared.get('formation:'+path['task_id'])
            if ticket:ticket.update(applied=True,epoch_seconds=time.time())
        if kind in ('formation_removed','formation_returned'):
            self._mark(r.path_attempts,path['task_id'],'returned',Status.RETURNED,proof)
        if kind in ('abyss_defeat','altar_defeat','prequel_defeat'):
            ledger=r.path_battles if kind=='prequel_defeat' else r.path_attempts
            scope='prequel:'+stage if kind=='prequel_defeat' else path['task_id']
            self._mark(ledger,scope,'defeat',Status.DEFEAT,proof)

    def _prepare(self, path, analysis):
        r=self.runtime; kind=path.get('kind'); stage=path.get('stage_id')
        ticket={'epoch_seconds':time.time(),'window':deepcopy(analysis['window'])}
        if str(kind).startswith('theater_'):
            from .theater import prepare
            prepare(r.path_prepared,path,analysis)
        if kind=='abyss_prepared':r.path_prepared['abyss:'+stage]=ticket
        if kind=='prequel_ready':r.path_prepared[stage]=ticket
        if kind in ('altar_open','altar_prepared'):r.path_prepared['altar:'+stage]=ticket
        if kind=='prequel_story_receipt' or (kind in ('prequel_story_skip','prequel_story_hold','story_skip','story_hold')
                and stage and r.path_battles.read()['stages'].get('prequel:'+stage)):
            r.path_prepared['story_seen:'+stage]=ticket
        if kind=='mission_claim':
            r.path_prepared['mission_claim:'+path['group_id']]={**ticket,'mission_id':path['mission_id'],'before_count':path['before_count']}
            r.path_prepared.pop('mission_receipt:'+path['group_id'],None)
        if kind=='mission_receipt':
            r.path_prepared['mission_receipt:'+path['group_id']]=deepcopy(r.path_prepared['mission_claim:'+path['group_id']])
        if kind in ('group_claim','group_receipt'):
            r.path_prepared[('group_claim:' if kind=='group_claim' else 'group_receipt:')+path['group_id']]=ticket
        if str(kind).startswith('formation_'):
            key='formation:'+path['task_id']
            if kind in ('formation_identity','formation_add'):
                r.path_prepared[key]={**ticket,'member_name':path['member_name'],
                    'source':path.get('source'),'destination':path.get('destination'),
                    'identity_verified':kind=='formation_identity'}
        if str(kind).startswith('equipment_'):
            key='equipment:'+path['task_id']
            info=next((i for i in operation_view(analysis).get('items',[]) if i.get('semantic_id')=='context'),{})
            if kind in ('equipment_equip_all','equipment_weapon'):
                r.path_prepared[key]={**ticket,'hero_name':path['hero_name']}
            prepared=r.path_prepared.get(key,{})
            if kind=='equipment_review_change':prepared.update(current_cp=info.get('current_cp'),candidate_cp=info.get('candidate_cp'),
                current_attributes=deepcopy(info.get('current_attributes')),candidate_attributes=deepcopy(info.get('candidate_attributes')),reviewed=True)
            if kind=='equipment_open_enhancement':prepared.update(item_name=info['item_name'],before_level=info.get('enhancement_level'))
            if kind=='equipment_snapshot':prepared.update(epoch_seconds=time.time(),before_level=info.get('enhancement_level'),before_exp_value=deepcopy(info.get('exp_value')))
            if kind=='equipment_enhance':prepared.update(gold_cost=info['gold_cost'],gold_balance=info['gold_balance'])
