"""Offline proofs: real Maa scheduler/input boundary, never a Windows controller.

The receipt scenarios use real tree adapters and target guards. The full mixed
group deliberately uses a scripted recognition oracle: it proves composition,
native dispatch, journals and budgets, NOT recognition or account progression.
"""
from collections import Counter, deque
from copy import deepcopy
import json
from importlib.metadata import version
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
import time

import numpy as np
import pytest

from driver_epic_seven.application import Application
from driver_epic_seven.attempts import AttemptLedger
from driver_epic_seven.config import load_config
from driver_epic_seven.contracts import ApplicationError, Identity, Request, Status
from driver_epic_seven.execution import OperationCycle, boundary_action, wrap_graph
from driver_epic_seven.observed_ui import build_tree, fact, node, quest_view
from driver_epic_seven.observer import SharedObserver
from driver_epic_seven.path_execution import path_target
from test_group_compiler import plan_and_view
from test_path_claim_reading import heir

pytestmark = pytest.mark.native


WINDOW = {'hwnd': -215, 'pid': -215, 'process_name': 'EpicSeven.exe',
          'window_title': 'SIMULATED - NO GAME', 'window_class': 'MEMORY',
          'client_size': [1212, 682]}


def receipt():
    return {'state': 'unknown', 'matches': {}, 'text': [
        {'text': text, 'box': box, 'score': .99} for text, box in [
            ('Received Reward', [490, 150, 230, 30]),
            ('You have successfully received the rewards!', [350, 220, 500, 25]),
            ('Tap to close', [550, 490, 110, 25])]]}


def observation(data):
    result = deepcopy(data)
    result.update(window=deepcopy(WINDOW), epoch_seconds=time.time(),
                  captured_at_epoch_seconds=time.time(), simulation=True,
                  account_progress=None)
    result['ui_tree'] = build_tree(result)
    return result


def oracle_observation():
    """Explicit contract fixture, not image recognition or package-derived state."""
    data = observation({'state': 'unknown'})
    tree = data['ui_tree']; source = {'kind': 'derived', 'pointer': '/simulation',
                                    'rule': 'offline_scripted_contract_fixture'}
    panel = node('simulated:panel', 'panel', 'screen', adapter=fact('operations', source),
                 view=fact('simulated_contract', source))
    item = node('simulated:context', 'item', panel['id'], semantic_id=fact('context', source),
                gold_cost=fact(100, source), gold_balance=fact(10000, source),
                item_name=fact('SIMULATED EQUIPMENT', source), enhancement_level=fact(0, source),
                current_cp=fact(1, source), candidate_cp=fact(2, source))
    tree['nodes']['screen']['children'].append(panel['id'])
    panel['children'].append(item['id'])
    tree['nodes'].update({panel['id']: panel, item['id']: item})
    return data


def shortest_path(graph, source, destination):
    queue = deque([(source, [source])]); seen = set()
    while queue:
        current, path = queue.popleft()
        if current == destination:
            return path
        if current in seen:
            continue
        seen.add(current)
        queue.extend((n, path + [n]) for n in graph[current].get('next', []))
    raise AssertionError(f'No Maa route from {source} to {destination}')


def mixed_route(graph, entry, terminal):
    """Choose real directed graph edges, including every consumer and receipt."""
    consumers = [name for name, spec in graph.items()
                 if spec.get('custom_recognition_param', {}).get('path', {}).get('consuming')]
    route = [entry]
    for name in consumers:
        route.extend(shortest_path(graph, route[-1], name)[1:])
        params = graph[name]['custom_recognition_param']['path']
        if params['kind'] in ('mission_claim', 'group_claim'):
            receipt_name = name.removesuffix('Dispatch') + 'Receipt'
            route.extend(shortest_path(graph, name, receipt_name)[1:])
            if params['kind'] == 'group_claim':
                next_name = name.removesuffix('Dispatch') + 'Next'
                route.extend(shortest_path(graph, route[-1], next_name)[1:])
        elif params['kind'] == 'abyss_start':
            route.extend(shortest_path(graph, name, name.removesuffix('Start')+'ResultBack')[1:])
        # Exercise an existing story treatment when this unit exposes one.
        elif params['kind'] in ('prequel_story_start', 'prequel_start'):
            candidates = [n for n, spec in graph.items()
                          if spec.get('custom_recognition_param', {}).get('path', {}).get('stage_id') == params['stage_id']
                          and spec.get('custom_recognition_param', {}).get('path', {}).get('kind') in
                          ('prequel_story_skip', 'prequel_story_hold', 'story_skip')]
            for candidate in candidates:
                try:
                    part = shortest_path(graph, name, candidate)
                except AssertionError:
                    continue
                route.extend(part[1:]); break
            if params['kind'] == 'prequel_story_start':
                prefix = name.removesuffix('Start')
                for checkpoint in (prefix+'Before.Notice', prefix+'Recovery.Path.Open.Lobby'):
                    if checkpoint in graph:
                        route.extend(shortest_path(graph, route[-1], checkpoint)[1:])
            else:
                # A graph edge through a notice can reach Map, but its real
                # target guard requires the victory ticket first. This oracle
                # deliberately bypasses recognition, so it must supply that
                # semantic sequence rather than choosing an impossible shortcut.
                prefix = name.removesuffix('Start')
                for checkpoint in (prefix+'Clear', prefix+'Map'):
                    route.extend(shortest_path(graph, route[-1], checkpoint)[1:])
    route.extend(shortest_path(graph, route[-1], terminal)[1:])
    return [n for n in route if graph[n].get('custom_recognition') == 'ScreenTarget']


class MemoryHarness:
    @property
    def fatal(self):
        return getattr(self, '_fatal', None)

    @fatal.setter
    def fatal(self, value):
        if value is None or not getattr(self, '_fatal', None):
            self._fatal = value

    def __init__(self, root, states, *, oracle=False, refuse=None, refuse_kind=None):
        from maa.controller import CustomController
        from maa.custom_recognition import CustomRecognition
        from maa.define import LoggingLevelEnum
        from maa.resource import Resource
        from maa.tasker import Tasker

        self.root = Path(root); self.root.mkdir(parents=True, exist_ok=True)
        self.maa_version = version('maafw')
        assert self.maa_version.removeprefix('v') == '5.14.3', 'Revalidate the offline proof against the installed SDK version.'
        self.states = states; self.index = 0; self.oracle = oracle; self.refuse = refuse
        self.refuse_kind = refuse_kind; self.params_by_name = {}; self.requests = []; self.graph_hashes = []
        self.inputs = []; self.recognized = []; self.events = []; self.writes = []; self.consuming_inputs = []
        self.metrics = Counter(); self.fatal = None; self.stop = False
        self.config = load_config(); self.config['path_ledger'] = self.root/'actions.json'
        self.path_attempts = AttemptLedger(self.config['path_ledger'], 1)
        self.path_battles = AttemptLedger(self.root/'battles.json', 2)
        self.attempts = AttemptLedger(self.root/'campaign.json', 2)
        self.path_prepared = {}; self.path_group_actions = set(); self.path_completion_scopes = {}
        self.path_group_action_count = 0; self.path_group_action_limit = 200
        self.start_reservations = {}; self.execution_retry = None; self.active_plan_checkpoint = None
        self.execution_identity = Identity('offline-objective', 'offline-plan', 'offline-operation', 'offline-attempt')
        self.execution_dispatched = False; self.original = deepcopy(WINDOW)
        self.evidence = SimpleNamespace(path=self.root, write=self.write)
        self.observer = SharedObserver(self.write)
        self.observer.metrics.update(group_input_decisions=0, group_native_input_actions=0)
        self.operation_cycle = OperationCycle(self)
        owner = self

        class Controller(CustomController):
            def connect(self): return True
            def request_uuid(self): return 'wave3-memory-only'
            def start_app(self, intent): return False
            def stop_app(self, intent): return False
            def screencap(self):
                owner.metrics['memory_captures'] += 1
                return np.zeros((682, 1212, 3), np.uint8)
            def click(self, x, y): return owner.input('click')
            def touch_down(self, *args): return owner.input('down')
            def touch_up(self, *args): return owner.input('up')
            def key_down(self, *args): return owner.input('key_down')
            def key_up(self, *args): return owner.input('key_up')
            def click_key(self, *args): return owner.input('key')
            def swipe(self, *args): return owner.input('swipe')
            def touch_move(self, *args): return True
            def input_text(self, *args): return False

        class Recognition(CustomRecognition):
            def analyze(self, ctx, argv):
                owner.metrics['recognition_reads'] += 1
                params = json.loads(argv.custom_recognition_param)
                if owner.oracle:
                    if not owner.route or argv.node_name != owner.route[0]: return None
                    analysis = oracle_observation(); box = [10, 10, 30, 30]
                    owner.route.pop(0)
                else:
                    analysis = owner.observe('native_recognition')
                    box = path_target(analysis, params.get('path', {}), np.zeros((682,1212,3),np.uint8), owner.path_prepared)
                    if box is None: return None
                owner.recognized.append(argv.node_name)
                owner.write('recognition', {'node': argv.node_name, 'analysis': analysis})
                return self.AnalyzeResult(box=box, detail=analysis)

        bundle = self.root/'bundle'; (bundle/'pipeline').mkdir(parents=True)
        (bundle/'pipeline/test.json').write_text('{"Placeholder":{"action":"DoNothing"}}')
        Tasker.set_stdout_level(LoggingLevelEnum.Off); Tasker.set_log_dir(self.root/'maa')
        self.controller = Controller(); assert self.controller.post_connection().wait().succeeded
        self.resource = Resource(); self.resource.register_custom_recognition('ScreenTarget', Recognition())
        self.resource.register_custom_action('OperationBoundary', boundary_action(self))
        assert self.resource.post_bundle(bundle).wait().succeeded
        self.tasker = Tasker(); assert self.tasker.bind(self.resource, self.controller)

    def write(self, name, data):
        self.writes.append(name)
        (self.root/f'{len(self.writes):04d}_{name}.json').write_text(json.dumps(data, default=str, indent=2), encoding='utf-8')

    def execute(self, request):
        self.metrics['application_requests'] += 1
        details = {'operation': request.operation, 'parameters': dict(request.parameters),
                   'identity': request.identity.as_dict()}
        self.requests.append(details); self.write('request', details)
        return Application(self.config).execute(request, self)

    def guard(self, **kwargs):
        if self.fatal: raise RuntimeError(self.fatal)
        if self.stop: raise RuntimeError('SIMULATED STOP')
        return deepcopy(WINDOW)

    def observe(self, *args, **kwargs):
        self.metrics['observation_reads'] += 1
        return observation(self.states[min(self.index, len(self.states)-1)])

    def input(self, kind):
        self.inputs.append(kind)
        if kind in ('click', 'up', 'key_up', 'key', 'swipe'):
            self.metrics['native_actions'] += 1
            kind = self.params_by_name.get(self.recognized[-1], {}).get('path', {}).get('kind') if self.recognized else None
            params = self.params_by_name.get(self.recognized[-1], {}).get('path', {})
            if params.get('consuming'):
                self.consuming_inputs.append(tuple(params.get(k) for k in ('kind', 'stage_id', 'task_id')))
            if self.refuse == 'uncertain' or kind == self.refuse_kind and self.refuse_kind:
                return False
            self.index += 1
        return True

    def post_task(self, entry, graph):
        self.metrics['maa_tasks'] += 1
        graph = deepcopy(graph)
        self.graph_hashes.append(sha256(json.dumps(graph, sort_keys=True).encode()).hexdigest())
        self.params_by_name = {name: spec.get('custom_recognition_param', {}) for name, spec in graph.items()}
        if self.oracle:
            terminal = 'Path.Group.Done' if 'Path.Group.Done' in graph else 'Path.Claim.Done'
            self.route = mixed_route(graph, entry, terminal)
        # Test timing only; native gestures, target guards and max_hit survive.
        for spec in graph.values():
            spec.update(pre_delay=0, post_delay=0, timeout=300)
        return self.tasker.post_task(entry, wrap_graph(graph))

    def wait(self, job, timeout, **kwargs):
        deadline = time.monotonic()+timeout
        while not job.done:
            if self.fatal:
                self.tasker.post_stop().wait(); raise RuntimeError(self.fatal)
            if time.monotonic() >= deadline:
                self.tasker.post_stop().wait(); raise RuntimeError('SIMULATED timeout')
            time.sleep(.01)
        if self.fatal: raise RuntimeError(self.fatal)

    def report(self, result):
        checkpoint = result.get('plan_checkpoint')
        report = {'simulation': True, 'account_progress': None,
                  'maa_version': self.maa_version, 'capture': 'memory_array',
                  'input': 'CustomController memory only', 'client_size': [1212, 682],
                  'scope': 'motor_contract_oracle' if self.oracle else 'real_tree_and_target_guards',
                  'metrics': dict(self.metrics), 'recognized': self.recognized,
                  'accepted_recognitions': len(self.recognized),
                  'requests': self.requests, 'graph_sha256': self.graph_hashes,
                  'configuration_sha256': sha256(json.dumps(self.config, sort_keys=True, default=str).encode()).hexdigest(),
                  'interventions_per_control': 0,
                  'consuming_inputs': self.consuming_inputs,
                  'ledger': self.path_attempts.read(), 'battle_ledger': self.path_battles.read(),
                  'execution': result.get('execution'), 'plan_checkpoint': checkpoint,
                  'finite_counters': checkpoint.get('used') if checkpoint else None,
                  'observer': self.observer.snapshot()}
        self.write('offline_proof', report)
        return report


def test_native_short_claim_uses_real_targets_receipt_and_correlated_evidence(tmp_path):
    states = [heir(group='3/6'), receipt(), heir(group='4/6', control='Received', native=False)]
    runtime = MemoryHarness(tmp_path, states)
    request = Request('path.collect', {'allow_ready_group': True, 'level': 1,
                                      'task_id': 'guide_01_006_001'})
    result = runtime.execute(request)
    assert result['completed'] and result['execution']['status'] == Status.COMPLETED
    assert runtime.metrics['maa_tasks'] == 1 and runtime.metrics['native_actions'] == 2
    rows = runtime.path_attempts.read()['stages']['claim:group_guide_01:guide_01_006_001']
    assert len(rows) == 1 and rows[0]['status'] == 'verified'
    assert rows[0]['identity'] == request.identity.as_dict()
    proofs = [e['proof'] for e in rows[0]['events'] if e.get('proof')]
    assert all(p['observation_id'] and p['window'] == WINDOW for p in proofs)
    assert runtime.path_battles.read() == {'stages': {}}
    runtime.report(result)


@pytest.mark.parametrize('kind', ['prequel_start', 'equipment_enhance', 'mission_claim'])
def test_full_group_uncertainty_never_replays_start_application_or_receive(tmp_path, monkeypatch, kind):
    from driver_epic_seven import path_group
    settings, view = plan_and_view()
    settings['max_actions'] = 200
    runtime = MemoryHarness(tmp_path, [{'state': 'unknown'}], oracle=True, refuse_kind=kind)
    scope = 'claim:group_guide_02:guide_02_002_001'
    runtime.path_attempts.reserve(scope, 'historical-simulated-receipt', 0)
    runtime.path_attempts.mark(scope, 'historical-simulated-receipt', 'verified')
    monkeypatch.setattr(path_group, 'quest_view', lambda _: deepcopy(view))
    settings_file = tmp_path/'settings.json'; settings_file.write_text(json.dumps(settings))
    request = Request('path.run-group', {'level': 2, 'plan': str(settings_file), 'timeout': 90})
    result = runtime.execute(request)
    assert result['completed'] is False and result['execution']['status'] == Status.UNCERTAIN
    assert result['plan_checkpoint']['state'] == 'uncertain'
    consumers = list(runtime.consuming_inputs)
    runtime.refuse_kind = None
    try:
        runtime.execute(request)
    except ApplicationError:
        pass
    assert runtime.consuming_inputs[:len(consumers)] == consumers
    assert all(count == 1 for count in Counter(runtime.consuming_inputs).values())
    rows = list(runtime.path_attempts.read()['stages'].values()) + list(runtime.path_battles.read()['stages'].values())
    uncertain = [row for entries in rows for row in entries
                 if any(e['phase'] == Status.UNCERTAIN for e in row.get('events', []))]
    assert len(uncertain) == 1
    target = next(e['proof']['target'] for e in uncertain[0]['events'] if e['phase'] == Status.RESERVED)
    assert target['kind'] == kind
    runtime.report(result)


def test_native_ready_group_receipt_and_next_group_use_real_guards(tmp_path):
    ready = heir(group='6/6', native=False)
    ready['matches']['path_receive_group'] = {'hit': True, 'box': [1003,205,112,39], 'score': .99}
    received = heir(group='6/6', native=False)
    received['matches']['path_group_next'] = {'hit': True, 'box': [1064,58,41,41], 'score': .99}
    following = heir(group='0/5', native=False)
    following['text'][2]['text'] = 'Path of Heir 2'
    runtime = MemoryHarness(tmp_path, [ready, receipt(), received, following])
    settings = tmp_path/'settings.json'; settings.write_text('{"max_energy":0}')
    request = Request('path.run-group', {'level': 1, 'plan': str(settings), 'timeout': 15})
    result = runtime.execute(request)
    assert result['completed'] and result['next_group_id'] == 'group_guide_02'
    assert runtime.metrics['maa_tasks'] == 1 and runtime.metrics['native_actions'] == 3
    assert result['plan_checkpoint']['used']['starts'] == 0
    assert result['plan_checkpoint']['used']['energy'] == 0
    assert quest_view(result['after'])['group_counter'] == {'current': 0, 'total': 5}
    rows = runtime.path_attempts.read()['stages']['group_reward:group_guide_01']
    assert len(rows) == 1 and rows[0]['status'] == 'verified'
    assert rows[0]['identity'] == request.identity.as_dict()
    runtime.report(result)


@pytest.mark.parametrize('negative', ['marker_missing', 'counter_unchanged', 'uncertain', 'stop', 'timeout'])
def test_native_claim_failures_never_replay_receive(tmp_path, negative):
    initial = heir(group='3/6', native=negative != 'marker_missing')
    runtime = MemoryHarness(tmp_path, [initial, receipt(), heir(group='3/6', native=False)],
                            refuse='uncertain' if negative == 'uncertain' else None)
    if negative == 'stop': runtime.stop = True
    if negative == 'timeout':
        def timeout(job, *_args, **_kwargs):
            runtime.tasker.post_stop().wait(); raise RuntimeError('SIMULATED timeout')
        runtime.wait = timeout
    request = Request('path.collect', {'allow_ready_group': True, 'level': 1, 'task_id': 'guide_01_006_001'})
    try:
        result = runtime.execute(request)
    except ApplicationError as error:
        result = error.as_dict()
    assert result.get('completed') is not True
    entries = runtime.path_attempts.read()['stages']
    count = sum(len(rows) for rows in entries.values())
    assert count <= 1
    # Any persisted uncertainty must block a fresh request before another send.
    if count:
        before = runtime.metrics['native_actions']
        with pytest.raises(ApplicationError): runtime.execute(request)
        assert runtime.metrics['native_actions'] == before
    runtime.report(result)


def test_full_mixed_group_native_engine_contract_has_all_consumers_and_finite_checkpoint(tmp_path, monkeypatch):
    from driver_epic_seven import path_group
    from driver_epic_seven.path_planning import route_level
    settings, view = plan_and_view()
    settings['max_actions'] = 200
    # Existing Wave2 compiler fixture: eight campaign entries, Abyss, equip and enhance.
    runtime = MemoryHarness(tmp_path, [{'state': 'unknown'}], oracle=True)
    verified = 'guide_02_002_001'; scope = 'claim:group_guide_02:'+verified
    runtime.path_attempts.reserve(scope, 'historical-simulated-receipt', 0)
    runtime.path_attempts.mark(scope, 'historical-simulated-receipt', 'verified')
    # Only the initial quest projection is supplied; the native recognition oracle
    # is a separate, explicitly weaker motor/contract proof than the claim test.
    monkeypatch.setattr(path_group, 'quest_view', lambda _: deepcopy(view))
    plan_file = tmp_path/'settings.json'; plan_file.write_text(json.dumps(settings))
    request = Request('path.run-group', {'level': 2, 'plan': str(plan_file), 'timeout': 90})
    result = runtime.execute(request)
    assert result['completed'] and result['next_group_id'] == 'group_guide_03'
    assert result['execution']['identity'] == request.identity.as_dict()
    assert runtime.metrics['maa_tasks'] == 1 and not runtime.route
    assert runtime.metrics['application_requests'] == 1
    assert result['plan_checkpoint']['state'] == 'completed'
    checkpoint = json.loads(Path(result['plan_checkpoint']['path']).read_text())
    used = checkpoint['used']; limits = checkpoint['specification']['limits']
    assert used['starts'] == 9 and used['energy'] == 50
    assert used['actions'] == runtime.metrics['native_actions']
    assert used['treatments'] > 0 and used['recovery'] > 0
    assert all(used[k] <= limits[k] for k in used)
    ledgers = {**runtime.path_attempts.read()['stages'], **runtime.path_battles.read()['stages']}
    assert len(runtime.path_battles.read()['stages']) == 8
    assert all(len(rows) == 1 for rows in ledgers.values())
    assert all(rows[-1]['status'] in ('returned', 'verified') for rows in ledgers.values())
    for rows in ledgers.values():
        current = rows[-1]
        if current['key'] == 'historical-simulated-receipt':
            continue
        assert current['identity'] == request.identity.as_dict()
        assert all(event['proof'].get('observation_id') and event['proof'].get('window') == WINDOW
                   for event in current['events'])
    consumer_kinds = [e['proof']['target'].get('kind') for rows in ledgers.values()
                      for e in rows[-1].get('events', []) if e['phase'] == Status.RESERVED]
    assert {'equipment_confirm_change', 'equipment_enhance', 'abyss_start',
            'prequel_story_start', 'prequel_start', 'mission_claim', 'group_claim'} <= set(consumer_kinds)
    assert len(route_level(3)['tasks']) > 0
    runtime.report(result)
