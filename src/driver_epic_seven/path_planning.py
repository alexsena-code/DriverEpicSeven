"""Catalog-backed group plans. No capture, Runtime, input or inferred progress."""
from collections import Counter
from copy import deepcopy
import json

from .config import ROOT
from .observed_ui import quest_view
from .quests import QuestCatalog


CONDITION_EXECUTORS = {
    'syncclear_content_enter_count': 'campaign', 'clearepisodechapter_count': 'campaign',
    'get_content_chrid_count': 'connection', 'chrup_count': 'hero_level',
    'chrl_level_count': 'hero_level', 'charawaken_grade_level_count': 'hero_awaken',
    'chrevo_grade_count': 'hero_promote', 'clearessence_count': 'hero_imprint',
    'gacha_gachaid_count': 'summon', 'equipup_equiptype_count': 'enhance',
    'equipup_equiptype_level_count': 'enhance', 'equiptype_chrid_level_count': 'equip',
    'clearmaxlevel_enter_count': 'abyss', 'clear_enter_count': 'mode_battle',
    'clear_entertype_count': 'mode_battle', 'pvpplay_pvptype_count': 'arena',
    'get_content_materialid_count': 'production', 'autosetspt_count': 'supporters',
    'chrskillenhance_count': 'hero_skill', 'gachapet_count': 'pet_summon',
    'petcare_count': 'pet_care', 'petsyn_grade_count': 'pet_synthesis',
    'petsell_count': 'pet_release', 'buy_shopid_count': 'shop',
    'buy_shopcategory_count': 'shop', 'equipcraft_count': 'craft',
    'equipalchemy_equiptype_count': 'conversion', 'equipupgrade_equiptype_count': 'reforge',
    'chrintimacy_level_count': 'friendship', 'euipsell_equiptype_count': 'equipment_sale',
    'euipextraction_equiptype_count': 'extraction', 'moonlighttheaterclear_storyid_count': 'theater',
    'clanattend_count': 'guild_attendance', 'clansupport_count': 'guild_support',
    'clear_worldboss_count': 'world_boss', 'chrclasschange_count': 'specialty',
    'use_tokentype_count': 'spending', 'eventlogin_eventid_count': 'time_gate',
}


def policy():
    return json.loads((ROOT/'data/missions/adventurer-policy.json').read_text(encoding='utf-8'))


def catalog(config=None):
    config = config or {}
    return QuestCatalog(config.get('quest_file', ROOT/'data/catalogs/quests.json'),
                        config.get('operation_map_file', ROOT/'data/missions/operation-map.json'))


def group_id(level):
    if isinstance(level, bool):
        raise ValueError('Nível do Caminho inválido.')
    if isinstance(level, str) and level.startswith('group_guide_'):
        level = level.removeprefix('group_guide_')
    try:
        number = int(level)
    except (TypeError, ValueError):
        raise ValueError('Informe o número do nível do Caminho.') from None
    if str(number) != str(level).lstrip('0') or not 1 <= number <= 65:
        raise ValueError('Nível do Caminho fora do catálogo (1 a 65).')
    return f'group_guide_{number:02d}'


def executor_for(task):
    operation = CONDITION_EXECUTORS.get(task['condition'], 'unmapped')
    if operation == 'mode_battle':
        entry = str(task.get('parameters', {}).get('enter', ''))
        if entry.startswith(('cmon','ctue','cwed','cthu','cfri')):
            operation = 'spirit_altar'
        elif entry.startswith('bmz'):
            operation = 'labyrinth'
        elif entry.startswith('hcs'):
            operation = 'otherworld'
    if operation == 'enhance':
        operation = 'artifact_enhance' if task.get('parameters', {}).get('equiptype') == 'artifact' else 'equipment_enhance'
    return operation


def equipment_operation(task):
    """Adapt a mission requirement to an existing capability, without input."""
    if not task.get('condition'):raise ValueError('Missão de equipamento ausente do catálogo.')
    executor=executor_for(task)
    if executor=='equip':return 'equip_all'
    if executor=='equipment_enhance' and 'weapon' in str(task.get('parameters',{}).get('equiptype','')).split(';'):
        return 'enhance_weapon'
    raise ValueError('Requisito sem operação de equipamento no escopo mapeado.')


def route_level(level, config=None):
    cat = catalog(config)
    identity = group_id(level)
    if identity not in cat.groups or cat.groups[identity]['path'] != 'heir':
        raise ValueError('Grupo ausente do Caminho do Herdeiro.')
    group = cat.groups[identity]
    tasks = sorted((t for t in cat.tasks.values() if t['group'] == identity),
                   key=lambda t: (int(t.get('sort') or 0), t['id']))
    return {'group_id': identity, 'name': group['name'], 'dependency': group['dependency'],
            'source': group['source'], 'group_reward_candidates': deepcopy(group['rewards']),
            'account_progress': None, 'completion_requires_current_tree': True,
            'tasks': [{'task_id': t['id'], 'label': t['label'], 'condition': t['condition'],
                       'parameters': deepcopy(t['parameters']), 'executor': executor_for(t),
                       'family': cat.families.get(t['condition']), 'source': t['source'],
                       'reward_candidates': deepcopy(t['reward']), 'repeat_group': t.get('repeat_group') or None,
                       'dependency': t.get('mission_dependency') or None,
                       'navigation_hint': t.get('btn_move_reference') or None,
                       'static_only': True} for t in tasks],
            'repeat_groups': sorted({t['repeat_group'] for t in tasks if t.get('repeat_group')}),
            'boundary': 'agent_checkpoint_after_this_group'}


def roadmap(config=None):
    cat = catalog(config)
    groups = [route_level(g['id'], config) for g in cat.groups.values() if g['path'] == 'heir']
    return {'schema_version': 1, 'path': 'heir', 'execution_unit': 'one_group',
            'progress_source': 'current_ui_tree_only', 'policy': policy(), 'groups': groups,
            'coverage': {'groups': len(groups), 'catalog_records': sum(len(g['tasks']) for g in groups),
                         'executors_required': dict(Counter(t['executor'] for g in groups for t in g['tasks'])),
                         'time_gated_records': sum(t['executor'] == 'time_gate' for g in groups for t in g['tasks'])}}


def next_progression(level, config=None):
    current = route_level(level, config)
    number = int(current['group_id'].split('_')[-1])
    following = route_level(number+1, config) if number < 65 else None
    goals = [{'task_id': t['task_id'], 'executor': t['executor'], 'parameters': t['parameters']}
             for t in (following or {}).get('tasks', []) if t['executor'] in
             ('hero_level','hero_awaken','hero_promote','equip','hero_skill','equipment_enhance','artifact_enhance')]
    return {'next_group': following['group_id'] if following else None,
            'requirements': goals, 'policy': policy()['checkpoint'],
            'note': 'Targets are requirements, not commands to spend; compare current heroes and materials first.'}


def plan_level(observation, level=None, config=None):
    current = quest_view(observation)
    seen_group = current.get('group_id')
    if not seen_group or not seen_group.startswith('group_guide_'):
        return {'status': 'needs_path_read', 'input_sent': False,
                'reason': 'Read the current Path of Heir group, not Diary or an old catalog checkpoint.'}
    identity = group_id(level if level is not None else seen_group)
    if seen_group != identity:
        raise ValueError('O grupo observado difere do nível solicitado.')
    route = route_level(identity, config)
    visible = {t['task_id']: t for t in current.get('visible_tasks', [])}
    tasks = []
    for task in route['tasks']:
        live = visible.get(task['task_id'])
        tasks.append({**task, 'observed': live is not None,
                      'status': live.get('status', 'unknown') if live else 'not_visible',
                      'counter': deepcopy(live.get('counter')) if live else None,
                      'claim_ready': live.get('claim_ready') if live else None,
                      'fully_visible': live.get('row_fully_visible') if live else None})
    count = current.get('group_counter')
    # The group counter is claimed progress. A hidden or missing row never
    # proves completion; repeated task records are not all visible rows.
    finished = bool(current.get('group_claimed') or (count and count['current'] == count['total']))
    return {'status': 'agent_checkpoint' if finished else 'level_in_progress',
            'group_id': identity, 'group_counter': count, 'group_claimed': current.get('group_claimed'),
            'tasks': tasks, 'not_visible_tasks': [t['task_id'] for t in tasks if not t['observed']],
            'progression_after_group': next_progression(identity, config),
            'milestone_after_group': policy()['milestone'], 'input_sent': False,
            'boundary': route['boundary']}
