"""STOVE Orbis readings in the existing group/mission/control tree contract.

Catalog IDs are bound only by a unique current group and an exact current title.
This does not change the native screen state or authorize any input.
"""
from functools import lru_cache
import math
import re

from .config import ROOT
from .observed_ui import fact, derived, node, catalog_ref
from .quests import QuestCatalog,mission_label_key
from .stages import normalize


@lru_cache(maxsize=1)
def _catalog():
    return QuestCatalog(ROOT / 'data/catalogs/quests.json',
                        ROOT / 'data/missions/operation-map.json')


def quest_nodes(c):
    if c.state not in ('unknown', 'orbis_guide'):
        return None
    if c.state == 'orbis_guide' and c.observation.get('quest', {}).get('group_id'):
        return None  # Existing canonical quest adapter owns a populated report.
    heading = c.one('Orbis Guide', (45, 45, 250, 65))
    footer = c.one(r'(?:[Xx×]\s*)?Tap to close[.]?', (500, 630, 260, 52))
    heir_tab = c.one('Path of Heir', (95, 180, 160, 55))
    if not (heading and footer and heir_tab):
        return None
    # A central confirmation is an overlay, not a mission control on the right.
    if c.find('Confirm|Cancel|Received Reward|Story Clear', (360, 110, 520, 420)):
        return 'stove_overlay_unresolved'
    title = c.one(r'Path of Heir\s+\d+', (400, 45, 640, 65))
    if title:
        reward_heading = c.one('Group Clear Reward', (625, 135, 345, 55))
        if not reward_heading:
            return 'stove_orbis_unresolved'
        return _heir_nodes(c, heading, heir_tab, title, reward_heading, footer)
    diary = c.one(r"Three Sisters[’']?", (95, 100, 165, 45))
    diary_label = c.one('Diary', (95, 125, 165, 40))
    tasks = c.find(r'\[Daily\].+', (290, 180, 550, 430))
    if diary and diary_label and tasks:
        return _diary_nodes(c, heading, heir_tab, diary, diary_label, tasks, footer)
    return 'stove_orbis_unresolved'


def _panel(c, heading, tab, mode, anchors):
    sources = [c.source(r) for r in [heading, tab, *anchors] if r]
    p = 'panel:orbis'
    # Native orbis_guide already creates this exact canonical parent.
    if c.parent != p:
        c.add(node(p, 'panel', c.parent, semantic_id=fact('orbis_guide', *sources),
                   visible=fact(True, *sources), mode=fact(mode, *sources),
                   back_destinations=fact([{'view':'lobby'}], *sources),
                   layout_reference={'source': 'wnd/growth_masterbook.csb', 'scope': 'static_hint'}))
    native=c.match('path_heir_tab_inactive')
    c.add(node(p+'/heir_tab', 'control', p, semantic_id=fact('orbis_heir_tab', c.source(tab)),
               text=c.value(tab), box=fact(tab[1]['box'], c.source(tab)),
               box_role=fact('text_anchor', c.source(tab)), visible=fact(True, c.source(tab)),
               consuming=fact(False,c.source(tab)),
               navigation_template_verified=fact(bool(native),c.match_source('path_heir_tab_inactive')),
               navigation_destinations=fact([{'view':'orbis_guide','mode':'heir'}],c.source(tab))))
    return p


def _heir_nodes(c, heading, tab, title, reward_heading, footer):
    catalog = _catalog()
    groups = [g for g in catalog.groups.values() if normalize(g['name']) == normalize(title[1]['text'])]
    if len(groups) != 1:
        return 'stove_orbis_unresolved'
    group = groups[0]
    tasks = [t for t in catalog.tasks.values() if t['group'] == group['id']]
    p = _panel(c, heading, tab, 'heir', [title, reward_heading, footer])
    _next_group(c,p,group,catalog)
    counter_row = c.one(r'\d+\s*/\s*\d+', (390, 150, 165, 75))
    count = c.ratio(counter_row)
    if count['value'] and (count['value']['total'] != len(tasks) or count['value']['current'] > len(tasks)):
        count = fact()
    receive = c.one('Receive', (975, 190, 165, 70))
    current = count['value']
    status = ('claim_ready' if current['current'] == current['total'] and receive else
              'incomplete' if current['current'] < current['total'] else None) if current else None
    native_receive = _receive_marker(c, receive, 190, 265, ('path_receive_group',))
    claim_ready = (fact(False, c.source(counter_row), derived('/text', 'group_claimed_counter_incomplete'))
                   if current and current['current'] < current['total'] else
                   fact(True, c.source(receive), native_receive[1],
                        derived('/matches', 'current_group_full_counter_and_active_receive'))
                   if current and current['current'] == current['total'] and native_receive else fact())
    gid = 'group:'+group['id']
    c.add(node(gid, 'group', p, semantic_id=fact(group['id'], c.source(title), catalog_ref('groups', group['id'])),
               text=c.value(title), visible=fact(True, c.source(title)), value=count,
               status=fact(status, c.source(counter_row) if counter_row else c.source(title)),
               group_name=c.value(title), path=fact('heir', catalog_ref('groups', group['id'])),
               claim_ready=claim_ready,
               complete_group_inventory=fact(), anchor_box=fact(title[1]['box'], c.source(title))))
    if receive:
        _control(c, gid, 'claim_group', receive, status, '/Layer/n_content/n_growth_guide/n_top/n_reward/btn_group_reward',
                 claim_ready=claim_ready, native=native_receive if claim_ready['value'] is True else None)
    matched = []
    for label in c.find(r'.+', (295, 285, 650, 335)):
        candidates = [t for t in tasks if mission_label_key(t['label']) == mission_label_key(label[1]['text'])]
        if len(candidates) == 1:
            matched.append((label, candidates[0]))
    for label, task in matched:
        if sum(t['id'] == task['id'] for _, t in matched) != 1:
            continue
        top = label[1]['box'][1]-12
        bottom = min(top+122, 622)
        counter_row = c.one(r'\d+\s*/\s*\d+', (300, top+50, 435, max(1, min(65, bottom-top-50))))
        count = c.ratio(counter_row)
        expected = str(task.get('parameters', {}).get('count', ''))
        if count['value'] and (count['value']['current'] > count['value']['total'] or
                              (expected.isdigit() and count['value']['total'] != int(expected))):
            count = fact()
        controls = c.find('Go|Receive|Received|Completed', (975, top, 165, min(100, bottom-top)))
        control = controls[0] if len(controls) == 1 else None
        word = control[1]['text'].strip().lower() if control else None
        satisfied = count['value']['current'] == count['value']['total'] if count['value'] else None
        fully_visible = top >= 285 and top+122 <= 622
        claimed_native = (_claimed_marker(c, top, bottom)
                          if control is None and fully_visible and satisfied is True else None)
        native_receive = _receive_marker(c, control, max(285, top), bottom,
            ('path_receive_row_1','path_receive_row_2','path_receive_row_3')) if word == 'receive' else None
        claim_ready = (fact(False, claimed_native[1], derived('/matches', 'current_claimed_row_check'))
                       if claimed_native else
                       fact(False, c.source(control), derived('/text', 'current_explicit_claimed_or_incomplete'))
                       if word in ('received','completed') or (word == 'go' and satisfied is False) else
                       fact(True, c.source(control), native_receive[1],
                            derived('/matches', 'current_active_receive_on_fully_visible_mission'))
                       if fully_visible and native_receive and satisfied is not False else fact())
        state = ('claim_ready' if word == 'receive' and satisfied is True else
                 'incomplete' if word == 'go' and satisfied is False else
                 'claimed' if word in ('received', 'completed') or claimed_native else None)
        mid = gid+'/mission:'+task['id']
        source = c.source(label)
        title_rule=(derived('/text','exact_mission_title_with_declared_equip_equipment_glyph_alias')
                    if normalize(task['label'])!=normalize(label[1]['text']) else
                    derived('/text','unique_exact_mission_title_within_current_group'))
        count_source = c.source(counter_row) if counter_row else source
        c.add(node(mid, 'mission', gid,
                   semantic_id=fact(task['id'], source, title_rule, catalog_ref('tasks', task['id'])),
                   text=c.value(label), anchor_box=fact(label[1]['box'], source), visible=fact(True, source),
                   value=count, condition_satisfied=fact(satisfied, count_source),
                   status=fact(state, count_source, c.source(control) if control else claimed_native[1] if claimed_native else source),
                   claim_ready=claim_ready,
                   fully_visible=fact(fully_visible, source, derived('/text', 'observed_row_extent')),
                   family=fact(catalog.families[task['condition']], catalog_ref('tasks', task['id'])),
                   catalog_label=fact(task['label'], catalog_ref('tasks', task['id'])),
                   demo_excluded=fact(),
                   expected_counter_total=fact(int(expected) if expected.isdigit() else None, catalog_ref('tasks', task['id'])),
                   layout_reference={'source': 'wnd/growth_masterbook_quest_item.csb', 'scope': 'static_hint'}))
        if control:
            key = {'go':'go', 'receive':'claim', 'received':'receipt', 'completed':'receipt'}[word]
            _control(c, mid, key, control, state, '/Layer/btn_go' if word=='go' else '/Layer/btn_reward',
                     claim_ready=claim_ready,
                     native=native_receive if claim_ready['value'] is True else None)
        elif claimed_native:
            box, marker_source=claimed_native
            c.add(node(mid+'/receipt','control',mid,
                       semantic_id=fact('receipt',marker_source),box=fact(box,marker_source),
                       box_role=fact('template_extent',marker_source),visible=fact(True,marker_source),
                       status=fact('claimed',marker_source,count_source),claim_ready=claim_ready,
                       layout_reference={'source':'wnd/growth_masterbook_quest_item.csb',
                                         'path':'/Layer/n_complete/bg/icon','scope':'static_hint'}))
    return 'stove_orbis_heir'


def _next_group(c,parent,group,catalog):
    key='path_group_next';match=c.match(key);box=match.get('box') if match else None
    if (not isinstance(box,(list,tuple)) or len(box)!=4
            or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in box)):
        return
    x,y,w,h=box
    if not (w>0 and h>0 and 1045<=x and x+w<=1125 and 45<=y and y+h<=115):
        return
    number=int(group['id'].rsplit('_',1)[-1]);candidate=f'group_guide_{number+1:02d}'
    next_group=candidate if candidate in catalog.groups and catalog.groups[candidate]['path']=='heir' else None
    source=c.match_source(key)
    c.add(node(parent+'/next_group','control',parent,semantic_id=fact('orbis_next_group',source),
               box=fact(list(box),source),box_role=fact('template_extent',source),visible=fact(True,source),
               consuming=fact(False,source,derived('/matches','mapped_group_navigation')),
               navigation_template_verified=fact(True,source),
               navigation_destinations=fact([{'view':'orbis_guide','mode':'heir'}],source),
               destination_group_id_hint=fact(next_group,catalog_ref('groups',next_group)) if next_group else fact(),
               destination_group_unlocked=fact(),
               layout_reference={'source':'wnd/growth_masterbook.csb','path':'/Layer/n_content/n_growth_guide/n_top/btn_next',
                                 'scope':'static_hint_with_current_native_arrow'}))


def _receive_marker(c, row, top, bottom, keys):
    """Associate a current native active-render match with this exact label.

    The marker proves rendered readiness, never Windows enabled state or the
    unread objective counter. ROI bands are recognizer scopes, not task IDs.
    """
    if row is None:
        return None
    label=row[1]['box']; found={}
    for key in keys:
        match=c.match(key)
        box=match.get('box') if match else None
        if (not isinstance(box,(list,tuple)) or len(box)!=4
                or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in box)):
            continue
        x,y,w,h=box
        if (w<=0 or h<=0 or x<975 or x+w>1145 or y<top or y+h>bottom
                or x>label[0]+3 or y>label[1]+3
                or x+w<label[0]+label[2]-3 or y+h<label[1]+label[3]-3):
            continue
        found[tuple(box)]=(list(box),c.match_source(key))
    return next(iter(found.values())) if len(found)==1 else None


def _claimed_marker(c, top, bottom):
    found={}
    for key in ('path_claimed_row_1','path_claimed_row_2','path_claimed_row_3'):
        match=c.match(key);box=match.get('box') if match else None
        if (not isinstance(box,(list,tuple)) or len(box)!=4
                or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in box)):
            continue
        x,y,w,h=box
        if 20<=w<=50 and 12<=h<=40 and 975<=x and x+w<=1145 and top+10<=y and y+h<=min(bottom,top+95):
            found[tuple(box)]=(list(box),c.match_source(key))
    return next(iter(found.values())) if len(found)==1 else None


def _control(c, parent, key, row, status, path, *, claim_ready=None, native=None):
    source = c.source(row)
    native_box, native_source = native if native else (None, None)
    c.add(node(parent+'/'+key, 'control', parent, semantic_id=fact(key, source), text=c.value(row),
               box=fact(native_box, native_source) if native_box else fact(row[1]['box'], source),
               box_role=fact('template_extent', native_source) if native_box else fact('text_anchor', source),
               label_box=fact(row[1]['box'], source),
               claim_ready=claim_ready or fact(),
               consuming=fact(key in ('claim','claim_group'),source,derived('/text','mapped_quest_control_role')),
               visible=fact(True, source), status=fact(status, source),
               layout_reference={'source':'wnd/growth_masterbook.csb' if key=='claim_group' else 'wnd/growth_masterbook_quest_item.csb',
                                 'path':path, 'scope':'static_hint'}))


def _diary_nodes(c, heading, tab, diary, label, tasks, footer):
    p = _panel(c, heading, tab, 'diary', [diary, label, footer])
    gid = p+'/observed_diary'
    c.add(node(gid, 'group', p, semantic_id=fact('observed_diary', c.source(diary)),
               text=fact("Three Sisters' Diary", c.source(diary), c.source(label)),
               group_name=fact("Three Sisters' Diary", c.source(diary), c.source(label)),
               path=fact('diary', c.source(diary)), group_id=fact(), visible=fact(True, c.source(diary)),
               value=fact(), header_number=c.value(c.one(r'\d+', (320, 105, 80, 65)), int),
               complete_group_inventory=fact()))
    for index, title in enumerate(tasks):
        top = title[1]['box'][1]-12
        source = c.source(title)
        mid = gid+'/row:'+str(index)
        counter = c.ratio(c.one(r'\d+/\d+', (300,top+55,435,55)))
        c.add(node(mid,'mission',gid,semantic_id=fact('observed_row:'+str(index),source),
                   text=c.value(title),visible=fact(True,source),value=counter,task_id=fact(),
                   condition_lines=c.lines((300,top+25,550,55)),condition_satisfied=fact(),status=fact()))
        control = c.one('Go|Receive', (975,top,165,100))
        if control:
            _control(c,mid,'go' if control[1]['text'].strip()=='Go' else 'claim',control,None,'/Layer/btn_go')
    return 'stove_orbis_diary'
