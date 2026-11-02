"""Finite Try again graph. Maa owns every wait, transition and action."""
from copy import deepcopy
import json

from .battle_operations import context, control
from .observed_ui import operation_view, screen_state


def target(observation, params):
    current = operation_view(observation)
    if params['kind'] == 'repeat_entered':
        # Retained combat HUD on a result footer is not an entry proof.
        from .reading import ReadContext
        c = ReadContext(observation, '', lambda _: None)
        if (current.get('view') not in (None, 'battle_skill_selection') or c.match('path_battle_exit_lobby')
                or c.find(r'Leave|Lobby|Try\s*again|Confirm|Cancel|FAILED|FAIVLED')):
            return None
        return [0, 0, 1, 1] if screen_state(observation) == 'battle_running' else None
    if current.get('view') != 'battle_exit':
        return None
    if params['kind'] == 'repeat_footer':
        return [0, 0, 1, 1]
    cost = context(current).get('repeat_cost') or {}
    if (type(cost.get('cost')) is not int or cost['cost'] != params['energy']
            or type(cost.get('available')) is not int or cost['available'] < cost['cost']):
        return None
    return control(current, 'try_again', True)


def graph(count, cost, budget, timeout, scope, resource_dir):
    from .path_execution import recognition
    from .composition import validate_graph
    if type(count) is not int or not 1 <= count <= 100:
        raise ValueError('Repetições devem estar entre 1 e 100.')
    if type(cost) is not int or cost <= 0 or type(budget) is not int or budget < count * cost:
        raise ValueError('Orçamento insuficiente ou custo inválido.')
    if type(timeout) is not int or not 1 <= timeout <= 1800:
        raise ValueError('Prazo deve estar entre 1 e 1800 segundos.')
    templates = json.loads((resource_dir / 'pipeline/battle_finish.json').read_text(encoding='utf-8'))
    # No map return, next difficulty, reward claims, refill or generic confirm.
    treatments = ['EnableAuto', 'Skip', 'ConfirmSkip', 'Clear', 'RankUp',
                  'ReceivedReward', 'CancelFriend', 'StoryReward', 'TapToClose']
    nodes = {'Repeat.Entry': {'recognition': 'DirectHit', 'action': 'DoNothing',
                              'next': ['Repeat.1.Start'], 'timeout': 10000}}
    for index in range(1, count + 1):
        prefix = f'Repeat.{index}.'
        unit = scope + ':' + str(index)
        start, entered, done = [prefix + s for s in ('Start', 'Entered', 'Done')]
        branches = [done] + [prefix + s for s in treatments]
        nodes[start] = recognition({'kind': 'repeat_start', 'task_id': unit,
            'consuming': True, 'energy': cost}, 'LongPress', duration=100,
            next_nodes=[entered], post_delay=700, timeout=15000)
        nodes[entered] = recognition({'kind': 'repeat_entered'}, next_nodes=branches, timeout=timeout * 1000)
        nodes[entered]['custom_recognition_param']['execution'] = {
            'ledger': 'path', 'scope': unit, 'phase': 'entry_verified', 'status': 'entered'}
        nodes[done] = recognition({'kind': 'repeat_footer'}, timeout=10000)
        nodes[done]['custom_recognition_param']['execution'] = {
            'ledger': 'path', 'scope': unit, 'phase': 'return_verified', 'status': 'verified'}
        if index < count:
            nodes[done]['next'] = [f'Repeat.{index + 1}.Start']
        for name in treatments:
            node = deepcopy(templates['Finish.' + name])
            node['next'] = branches
            node['timeout'] = timeout * 1000
            # The native auto recognizer receives text so it can reject footers.
            node['custom_recognition_param']['read_text'] = True
            nodes[prefix + name] = node
    success = f'Repeat.{count}.Done'
    validate_graph(nodes, 'Repeat.Entry', [success])
    return nodes, 'Repeat.Entry', success


def run(runtime, count, budget, timeout):
    from .path_execution import run_graph
    # A new request cannot hide an unresolved repeat after a disconnect.
    for scope, rows in runtime.path_attempts.read()['stages'].items():
        if scope.startswith('repeat:') and rows and rows[-1]['status'] != 'verified':
            raise ValueError('Repetição anterior pendente; conferir o resultado antes de outro lote.')
    before = runtime.observe('repeat_before', read_text=True)
    current = operation_view(before)
    if current.get('view') != 'battle_exit':
        raise ValueError('Termine a fase escolhida e deixe Leave, Lobby e Try again visíveis.')
    cost = (context(current).get('repeat_cost') or {}).get('cost')
    scope = 'repeat:' + runtime.execution_identity.operation_id
    nodes, entry, success = graph(count, cost, budget, timeout, scope, runtime.config['resource_dir'])
    runtime.evidence.write('repeat_plan', {'count': count, 'cost_per_start': cost,
        'max_resource': budget, 'timeout': timeout, 'scope': scope,
        'currency': None, 'stage_identity': None, 'selection': 'current_result_try_again',
        'validation': 'draft_live_pending'})
    result = run_graph(runtime, nodes, entry, success, timeout)
    completed = sum(n['completed'] for n in result['nodes'] if n['name'].startswith('Repeat.') and n['name'].endswith('.Done'))
    return {**result, 'operation': 'repeat-stage', 'requested_repeats': count,
            'completed_repeats': completed, 'max_resource': budget,
            'validation': 'draft_live_pending'}
