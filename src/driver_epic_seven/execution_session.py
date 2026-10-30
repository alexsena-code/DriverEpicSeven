"""One local execution worker; consultation never calls Maa or captures."""
from copy import deepcopy
from threading import RLock, Thread

from .contracts import ApplicationError, Status


class ExecutionSession:
    def __init__(self, application, runtime):
        self.application, self.runtime = application, runtime
        self._lock = RLock()
        self._worker = None
        self._closed = False
        self._state = {'running': False, 'status': 'idle', 'identity': None,
                       'request_id': None, 'cancel_requested': False,
                       'result': None, 'error': None, 'file_scope': 'lifecycle',
                       'live_plan_query': 'JSONL status'}

    def _publish(self, kind):
        self.runtime.observer.event(kind, identity=self._state['identity'],
                                    request_id=self._state['request_id'],
                                    status=self._state['status'])
        self.runtime.evidence.write('execution', self._state)

    def _persistence_error(self, exc, phase, *, input_attempted=None):
        """Keep the initiating failure and record persistence loss in memory."""
        attempted = bool(getattr(self.runtime, 'execution_dispatched', False)
                         if input_attempted is None else input_attempted)
        status = Status.UNCERTAIN.value if attempted else Status.BLOCKED.value
        error = self._state.get('error')
        if error is None:
            error = {'identity': self._state['identity'], 'status': status,
                     'error': 'Falha ao persistir evidência: '+str(exc),
                     'proof': {'input_attempted': attempted, 'replay_authorized': False}}
        else:
            error = deepcopy(error)
        error.setdefault('proof', {}).setdefault('persistence_errors', []).append(
            {'phase': phase, 'error': str(exc)})
        self._state.update(error=error, status=error['status'])

    def submit(self, request, request_id=None):
        with self._lock:
            if self._closed:
                raise ApplicationError('Sessão encerrada.', Status.BLOCKED, request.identity)
            if self._state['running']:
                raise ApplicationError('Uma execução já está em andamento; consulte status ou cancele.',
                                       Status.BLOCKED, request.identity)
            prepare = getattr(self.runtime, 'prepare_execution', None)
            if prepare:
                prepare(request.identity)
            self._state = {'running': True, 'status': 'running',
                           'identity': request.identity.as_dict(), 'request_id': request_id,
                           'operation': request.operation, 'cancel_requested': False,
                           'result': None, 'error': None, 'file_scope': 'lifecycle',
                           'live_plan_query': 'JSONL status'}
            try:
                # Failure here must prevent every application input. A partially
                # written lifecycle reservation never leaves a phantom worker.
                self._publish('execution_started')
                self._worker = Thread(target=self._execute, args=(request,), name='epic-seven-execution')
                self._worker.start()
            except Exception as exc:
                self._state['running'] = False
                self._worker = None
                self._persistence_error(exc, 'execution_started', input_attempted=False)
                error = self._state['error']
                raise ApplicationError(error['error'], Status(error['status']), request.identity,
                                       error['proof']) from exc
            return deepcopy(self._state)

    def _execute(self, request):
        result, error = None, None
        try:
            result = self.application.execute(request, self.runtime)
        except Exception as exc:
            error = exc.as_dict() if isinstance(exc, ApplicationError) else {
                'identity': request.identity.as_dict(), 'status': Status.UNCERTAIN.value
                if getattr(self.runtime, 'execution_dispatched', False) else Status.BLOCKED.value,
                'error': str(exc), 'proof': {'input_attempted': bool(
                    getattr(self.runtime, 'execution_dispatched', False))}}
        persistence_errors = []
        if error:
            try:
                self.runtime.observer.invalidate('agent_command_failed')
            except Exception as exc:
                persistence_errors.append(('failure_invalidation', exc))
        with self._lock:
            prior_error = self._state.get('error')
            if prior_error:
                if error is None:
                    error = deepcopy(prior_error)
                else:
                    previous = prior_error.get('proof', {}).get('persistence_errors', [])
                    error.setdefault('proof', {}).setdefault('persistence_errors', []).extend(previous)
            status = (error or (result or {}).get('execution', {})).get('status', 'completed')
            if self._state['cancel_requested']:
                attempted = bool(getattr(self.runtime, 'execution_dispatched', False))
                status = Status.UNCERTAIN.value if attempted else Status.CANCELLED.value
                try:
                    self.runtime.observer.invalidate('execution_cancelled')
                except Exception as exc:
                    persistence_errors.append(('cancellation_invalidation', exc))
                if error is None:
                    error = {'identity': request.identity.as_dict(), 'status': status,
                             'error': 'Execução cancelada; envios anteriores permanecem registrados.',
                             'proof': {'input_attempted': attempted, 'replay_authorized': False}}
                else:
                    error['status'] = status
                    error.setdefault('proof', {}).update(input_attempted=attempted, replay_authorized=False)
            self._state.update(running=False, status=status, result=deepcopy(result), error=error)
            for phase, exc in persistence_errors:
                self._persistence_error(exc, phase)
            try:
                self._publish('execution_finished')
            except Exception as exc:
                self._persistence_error(exc, 'execution_finished')

    def status(self):
        with self._lock:
            state = deepcopy(self._state)
        checkpoint = getattr(self.runtime, 'active_plan_checkpoint', None)
        if checkpoint:
            # Atomic checkpoint/ledger reads only. These never enter Runtime,
            # capture, OCR or the Maa tasker's execution path.
            try:
                plan = checkpoint.read()
                if plan:
                    from .plans import disposition
                    specification = plan.get('specification', {})
                    limits, used = specification.get('limits', {}), plan.get('used', {})
                    ledgers = {}
                    for name, attribute in (('campaign', 'attempts'), ('path_attempts', 'path_attempts'),
                                            ('path_battles', 'path_battles')):
                        ledger = getattr(self.runtime, attribute, None)
                        if ledger:
                            ledgers[name] = ledger.read().get('stages', {})
                    units = []
                    for unit in specification.get('units', []):
                        explicit = 'ledger_name' in unit or 'ledger_scopes' in unit
                        references = ([(unit.get('ledger_name'), scope) for scope in unit.get('ledger_scopes', [])]
                                      if explicit else [(name, unit['unit_id']) for name, ledger in ledgers.items()
                                                       if ledger.get(unit['unit_id'])])
                        expected = plan.get('identity', {})
                        bound_identity = all(expected.get(key) for key in ('objective_id', 'plan_id'))
                        evidence = []
                        for name, scope in references:
                            rows = ledgers.get(name, {}).get(scope, [])
                            latest = rows[-1] if rows else {}
                            matches = (all(latest.get('identity', {}).get(key) == expected[key]
                                           for key in ('objective_id', 'plan_id')) if bound_identity else False)
                            # Compatibility applies only to old, identity-less
                            # snapshots. Modern plans cannot borrow another
                            # objective's progress through the legacy lookup.
                            legacy = not explicit and not bound_identity
                            proven = any(event.get('phase') in ('return_verified', 'completed')
                                and event.get('proof', {}).get('observation_id')
                                and event.get('proof', {}).get('window')
                                for event in latest.get('events', []))
                            decision = disposition(rows) if matches or legacy else 'unknown'
                            evidence.append({'ledger_name': name, 'scope': scope,
                                'disposition': decision, 'identity_matches': matches if rows else None,
                                'completion_verified': bool(rows) and decision == 'completed' and (proven or legacy),
                                'reservation_key': latest.get('key')})
                        decisions = [item['disposition'] for item in evidence]
                        units.append({**deepcopy(unit), 'ledger_disposition':
                            decisions[0] if len(set(decisions)) == 1 else 'unknown',
                            'ledger_evidence': evidence,
                            'completion_verified': bool(evidence) and all(item['completion_verified'] for item in evidence)})
                    state['plan'] = {'identity': plan.get('identity'), 'state': plan.get('state'),
                        'specification': deepcopy(specification), 'units': units,
                        'used': deepcopy(used), 'remaining': {k: max(0, v-used.get(k, 0)) for k, v in limits.items()},
                        'deadline_epoch_seconds': plan.get('deadline_epoch_seconds'),
                        'completed_nodes': deepcopy(plan.get('completed_nodes', [])),
                        'pending_units': [u['unit_id'] for u in units if not u['completion_verified']],
                        'progress_source': 'checkpoint_and_exact_unit_ledger', 'account_progress': None}
            except (OSError, ValueError, KeyError, TypeError) as exc:
                state['plan'] = {'available': False, 'error': str(exc)}
        return state

    def wait(self):
        with self._lock:
            worker = self._worker
        if worker:
            worker.join()
        return self.status()

    def cancel(self):
        with self._lock:
            if self._state['running'] and not self._state['cancel_requested']:
                self._state['cancel_requested'] = True
                # Runtime cancellation only signals its tasker; it must not wait
                # for the running worker or acquire the execution emitter lock.
                cancel = getattr(self.runtime, 'cancel_execution', None)
                if cancel:
                    cancel()
                try:
                    self.runtime.observer.invalidate('cancellation_requested')
                    self._publish('execution_cancel_requested')
                except Exception as exc:
                    self._persistence_error(exc, 'execution_cancel_requested')
            return deepcopy(self._state)

    def close(self):
        with self._lock:
            self._closed = True
        try:
            self.cancel()
        finally:
            result = self.wait()
        return result

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
