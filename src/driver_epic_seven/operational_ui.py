"""Scoped adapters over the current Maa OCR/matches, never a second observer.

Screen regions use calibrated 1212x682 compositions, including the explicitly
guarded STOVE prequel map. Other operations retain their original scoped checks.
Static paths are hints; unknown selection, owned-instance IDs and enabled stay null.
"""
import re

from .observed_ui import fact, derived, node
from .operational_coreloop import coreloop_nodes
from .profile import supports_reading


def operational_nodes(observation, parent, add):
    if observation.get('window', {}).get('client_size', [1212, 682]) != [1212, 682]:
        return None
    from .operational_energy import energy_nodes
    energy_view = energy_nodes(observation, parent, add)
    if energy_view:
        return energy_view
    from .operational_battle_end import battle_end_nodes
    result_view=battle_end_nodes(observation,parent,add)
    if result_view:
        return result_view
    from .operational_theater import theater_nodes
    theater_view=theater_nodes(observation,parent,add)
    if theater_view:return theater_view
    from .operational_stove import stove_nodes
    stove_view = stove_nodes(observation, parent, add)
    if stove_view:
        return stove_view
    state = observation.get('state', 'unknown')
    # Never reinterpret text behind a known unrelated overlay.
    if state not in ('unknown', 'battle_ready', 'battle_running', 'hero_screen', 'tap_to_close_notice',
                     'prequel_story_map', 'prequel_ready_map', 'prequel_preparation', 'episode_map',
                     'battle_nightmare_keeper', 'battle_mercenary_lydia', 'stage_clear', 'hero_joined_notice',
                     'victorika_acquisition_dialogue', 'victorika_acquisition_result'):
        return None
    coreloop_view = coreloop_nodes(observation, parent, add)
    if coreloop_view:
        return coreloop_view
    from .reading import ReadContext
    reader = ReadContext(observation, parent, add)
    rows, find, one, source = reader.rows, reader.find, reader.one, reader.source
    from .operational_equipment import enhancement_nodes, attributes
    equipment_view=enhancement_nodes(reader)
    if equipment_view:return equipment_view

    def value(row, transform=lambda s: s, rule='calibrated_operation_composition'):
        if row is None:
            return fact()
        return fact(transform(row[1]['text'].strip()), source(row),
                    derived(f'/text/{row[0]}', rule))

    panel, detail = reader.panel, reader.detail

    def control(owner, name, row, consuming=False, path=None):
        reader.control(owner, name, row, consuming=consuming,
                       layout=path[0] if path else None, path=path[1] if path else None)

    def cost(area, currency):
        r = one(r'\d[\d,]*\s*/\s*\d[\d,]*', area)
        return (fact({'currency': currency, **dict(zip(('cost', 'available'),
                 map(int, re.sub(r'[,\s]', '', r[1]['text']).split('/'))))}, source(r),
                 derived(f'/text/{r[0]}', 'calibrated_cost_region_not_header_stock')) if r else fact())

    def integer(text):
        return int(re.sub(r'[,.\s]', '', text))

    def joined(found, rule):
        if not found:
            return fact()
        return fact(' '.join(r['text'].strip() for _, r in sorted(found, key=lambda row: row[1]['box'][1])),
                    *(source(r) for r in found), derived('/text', rule))

    heading = (0, 0, 400, 65)
    footer = (0, 580, 1212, 102)
    tag_prompt=one('Change Heroes using Tag',(220,585,320,55))
    tag_label=one('TAG',(75,620,105,50))
    tag_boss=one('Nilgal',(275,0,220,40))
    if (state=='unknown' and all((tag_prompt,tag_label,tag_boss))
            and supports_reading(observation)):
        p=panel('battle_tag_tutorial',[tag_prompt,tag_label,tag_boss],'db/tutorial_guide.db','prequel_tag_02')
        detail(p,prompt_text=value(tag_prompt),opponent_label=value(tag_boss),
               static_binding_hint=fact('btn_tag',{'kind':'catalog','source':'db/tutorial_guide.db','identity':'prequel_tag_02'}),
               hud_control_path=fact(),actor_before=fact(),actor_after=fact(),swap_completed=fact(),hero_instance_id=fact())
        # Only a descriptive current text control. No runtime target or copied menu ancestry.
        control(p,'tag_label',tag_label)
        return 'battle_tag_tutorial'
    if state in ('victorika_acquisition_dialogue','victorika_acquisition_result'):
        matches=observation.get('matches', {})
        names=('victorika_acquisition_name','victorika_acquisition_traits','victorika_acquisition_new','victorika_acquisition_four_stars')
        if (not supports_reading(observation)
                or not all(matches.get(k,{}).get('hit') for k in names)):
            return None
        sources={k:{'kind':'recognition','pointer':f'/matches/{k}'} for k in names}
        evidence=list(sources.values());p='operation:hero_acquisition'
        add(node(p,'panel',parent,semantic_id=fact('hero_acquisition',*evidence),adapter=fact('operations',*evidence),
                 view=fact('hero_acquisition',*evidence),mode=fact('victorika',*evidence),visible=fact(True,*evidence),
                 layout_reference={'source':'wnd/gacha_result_unit.csb','path':'/Layer/n_result','scope':'static_hint'}))
        dialogue=matches.get('victorika_acquisition_speech_name',{}).get('hit')
        normal=matches.get('victorika_acquisition_confirm_normal',{}).get('hit')
        name_source=sources['victorika_acquisition_name'];traits_source=sources['victorika_acquisition_traits']
        detail(p,hero_name=fact('Victorika',name_source),
               hero_catalog_id=fact('c1166',name_source,traits_source,
                   {'kind':'catalog','source':'db/character_player.db','identity':'c1166'},
                   {'kind':'catalog','source':'text/en/text.db','identity':'chrn_c1166'}),
               displayed_rarity=fact(4,sources['victorika_acquisition_four_stars']),
               element_label=fact('Fire',traits_source),role_label=fact('Knight',traits_source),zodiac_label=fact('Leo',traits_source),
               new_badge_visible=fact(True,sources['victorika_acquisition_new']),
               acquisition_announced=fact(True,*evidence,derived('/matches','calibrated_current_new_hero_result_composition')),
               presentation_phase=fact('dialogue' if state=='victorika_acquisition_dialogue' else 'normal_confirm',
                   derived('/state','calibrated_acquisition_dialogue_or_normal_confirm_variant')),
               speech_visible=(fact(True,{'kind':'recognition','pointer':'/matches/victorika_acquisition_speech_name'}) if dialogue else fact()),
               description_text=joined(find(r'.+',(20,110,235,70)),'current_acquisition_description_lines'),
               speech_text=joined(find(r'.+',(100,545,1020,78)),'current_acquisition_dialogue_lines') if dialogue else fact(),
               confirm_normal_visible=(fact(True,{'kind':'recognition','pointer':'/matches/victorika_acquisition_confirm_normal'}) if normal else fact()),
               owned_instance_id=fact(),complete_roster=fact(),acquisition_origin=fact(),summon_performed=fact(),acknowledgement_completed=fact())
        confirm=matches.get('victorika_acquisition_confirm',{})
        if state=='victorika_acquisition_result' and normal and not dialogue and confirm.get('hit') and confirm.get('box'):
            src={'kind':'recognition','pointer':'/matches/victorika_acquisition_confirm'}
            add(node(p+'/confirm','control',p,semantic_id=fact('confirm_acquisition',src),adapter=fact('operations',src),
                     text=fact(confirm.get('text'),src,confidence=confirm.get('score')),
                     box=fact(confirm['box'],src),box_role=fact('text_anchor',src),visible=fact(True,src),
                     consuming=fact(False,src,derived('/state','acknowledgement_of_current_acquisition_result')),
                     layout_reference={'source':'wnd/gacha_result_unit.csb','path':'/Layer/n_result/n_buttons_ext/btn_close','scope':'static_hint'}))
        return 'hero_acquisition'
    if state == 'hero_joined_notice':
        anchors = ('hero_joined_title','hero_joined_description','hero_joined_ok')
        if (not supports_reading(observation)
                or not all(observation.get('matches', {}).get(name, {}).get('hit') for name in anchors)):
            return None
        title = one('Inexperienced Victorika has Joined', (350,150,510,65))
        available = one(r'Inexperienced Victorika is now available[.]?', (345,355,525,40))
        assign = one(r'You can now assign her to your team and use her in battle[.]?', (345,393,525,37))
        ok = one('OK', (495,445,220,85))
        if not all((title,available,assign,ok)):
            return None
        p = panel('hero_joined_notice', [title,available,assign,ok], 'wnd/hero_get.csb', 'availability_announcement')
        evidence = [source(row) for row in (title,available,assign)]
        evidence += [{'kind':'recognition','pointer':f'/matches/{name}'} for name in anchors]
        detail(p, hero_name=value(title, lambda s: re.sub(r' has Joined$', '', s)),
               title=value(title), availability_text=value(available), assignment_text=value(assign),
               hero_catalog_id=fact('c0166', *evidence,
                   {'kind':'catalog','source':'text/en/text.db','identity':'c0166_get_title'},
                   {'kind':'catalog','source':'db/character_player.db','identity':'c0166'},
                   derived('/text','exact_current_notice_label_to_static_character_id')),
               availability_announced=fact(True, *evidence,
                   derived('/text','current_hero_joined_notice_explicit_availability')),
               team_assignment_announced=fact(True, *evidence,
                   derived('/text','current_notice_explicit_team_assignment_statement')),
               owned_instance_id=fact(), owned_roster=fact(), selected=fact(), team_slot=fact(),
               acknowledgement_completed=fact())
        control(p, 'acknowledge', ok, path=('wnd/hero_get.csb','/Layer/window_frame/btn_ok'))
        return 'hero_joined_notice'
    if state == 'stage_clear':
        matches = observation.get('matches', {})
        clear_anchors = ('clear_initial', 'clear_continue', 'clear_heading')
        if (not supports_reading(observation)
                or not all(matches.get(name, {}).get('hit') for name in clear_anchors)):
            return None
        context_sources = [{'kind':'recognition', 'pointer':f'/matches/{name}'} for name in clear_anchors]

        def result_marker(name, area):
            match = matches.get(name, {})
            box = match.get('box')
            x,y,w,h = area
            if (match.get('hit') and box and len(box)==4 and min(box[2:])>0
                    and x<=box[0] and y<=box[1] and box[0]+box[2]<=x+w and box[1]+box[3]<=y+h):
                return {'kind':'recognition', 'pointer':f'/matches/{name}'}
            return None

        checks = {slot: result_marker(f'clear_objective_check_{slot}', (x,525,45,40))
                  for slot,x in enumerate((200,518,836),1)}
        stars = result_marker('clear_three_stars', (480,235,250,155))
        stars_sources = context_sources + ([stars] if stars else []) + [s for s in checks.values() if s]
        three_stars = bool(stars and all(checks.values()))
        p = 'operation:campaign_result'
        add(node(p, 'panel', parent,
                 semantic_id=fact('campaign_result', *context_sources), adapter=fact('operations', *context_sources),
                 view=fact('campaign_result', *context_sources), mode=fact('current_clear', *context_sources),
                 visible=fact(True, *context_sources)))
        objectives = []
        objective_nodes = []
        # These are the three labels calibrated in the two current prequel results.
        # Different, partial or overlapping text remains readable but not a completed objective.
        labels = ('Initial Clear', 'Story Clear', 'Have 1 or more Heroes survive')
        for slot,(x,expected) in enumerate(zip((235,552,870),labels),1):
            header = one('Stage Mission', (x,530,150,27))
            lines = sorted(find(r'.+', (x,557,285,43)), key=lambda row:row[1]['box'][1])
            ambiguous = len(lines)>2 or any(a[1]['box'][1]+a[1]['box'][3]>b[1]['box'][1]+3
                                           for a,b in zip(lines,lines[1:]))
            label = joined(lines, 'aligned_current_clear_objective_lines') if not ambiguous else fact()
            completed = bool(header and checks[slot] and label['value'] == expected)
            evidence = context_sources + ([checks[slot]] if checks[slot] else [])
            if header:evidence.append(source(header))
            evidence += [source(r) for r in lines]
            completion = (fact(True, *evidence, derived('/matches', 'current_clear_check_header_and_exact_objective_label'))
                          if completed else fact())
            objectives.append(completion)
            objective_nodes.append(node(p+f'/objective:{slot}', 'item', p,
                     semantic_id=fact('stage_objective', *context_sources), adapter=fact('operations', *context_sources),
                     slot=fact(slot, *context_sources, derived('/matches','calibrated_clear_objective_slot')),
                     header=value(header), text=label, completed=completion,
                     check_visible=fact(True, checks[slot]) if checks[slot] else fact(),
                     condition=fact(), parameters=fact(),
                     status=fact('completed', *evidence) if completed else fact(),
                     layout_reference={'source':'wnd/result_mission_item.csb','path':'/Layer/icon_check','scope':'static_hint'}))
        add(node(p+'/context', 'item', p,
                 semantic_id=fact('context', *context_sources), adapter=fact('operations', *context_sources),
                 stage_id=fact(),
                 earned_stars=(fact(3, *stars_sources, derived('/matches','three_star_display_and_three_current_result_checks'))
                               if three_stars else fact()),
                 earned_stars_basis=(fact('three_star_display_and_three_result_checks', *stars_sources) if three_stars else fact()),
                 objectives_complete=(fact(True, *(s for objective in objectives for s in objective['sources']),
                     derived('/text','all_three_current_result_objectives_completed'))
                     if all(o['value'] is True for o in objectives) else fact()),
                 next_stage_id=fact(), reward_claimed=fact()))
        for item in objective_nodes:
            add(item)
        return 'campaign_result'
    if state in ('prequel_story_map', 'prequel_ready_map', 'episode_map'):
        # Current visual composition, separate from the legacy stage executor.
        matches = observation.get('matches', {})
        heading_hit = (matches.get('map_episode_header', {}).get('hit') if state == 'episode_map' else
                       matches.get('prequel_episode_header', {}).get('hit') or matches.get('episode1_heading', {}).get('hit')
                       or matches.get('map_episode_header', {}).get('hit'))
        if (not supports_reading(observation) or not heading_hit
                or not matches.get('prequel_view_story' if state == 'prequel_story_map' else 'map_ready_label', {}).get('hit')):
            return None
        episode = one(r'6th World Episode|Episode\s+\d+', heading)
        view_story = one('View Story' if state == 'prequel_story_map' else 'Ready', (980, 590, 160, 75))
        story_kind = one('Story', (835, 75, 150, 55))
        map_content = one('Obtainable Rewards|Enemies', (835, 230, 320, 60))
        # The current chapter label can include its left navigation arrow in
        # one OCR box (x41). Preserve the text; the arrow is not a stage ID.
        chapter_area = (35, 75, 245, 55)
        chapter = one(r'<?\s*Chapter\s*\d+S?\s*[.].+', chapter_area)
        chapter_rows = find(r'.+', chapter_area)
        if not all((episode, view_story, story_kind, map_content, chapter)):
            return None
        # Decision overlays and partial reads do not expose the underlying map.
        if (find('Cancel|Confirm', (300, 200, 600, 350))
                or find(r'.*Tap to close[.]?', (350, 480, 600, 202))):
            return None
        view_name = 'prequel_ready_map' if state == 'episode_map' else state
        p = panel(view_name, [episode, view_story, story_kind, map_content],
                  'wnd/battle_prequel.csb', 'adventure_prequel')
        detail(p, episode_label=value(episode),
               chapter_label=joined(chapter_rows, 'aligned_chapter_header_lines'),
               chapter_number=value(chapter, lambda s: int(re.search(r'Chapter\s*(\d+)', s, re.I)[1])),
               chapter_code=value(chapter, lambda s: re.search(r'Chapter\s*(\d+S?)\s*[.]', s, re.I)[1].upper()),
               selected_kind_label=value(story_kind),
               selected_description=joined(find(r'.+', (835, 125, 360, 85)),
                                           'aligned_story_description_lines'),
               chapter_star_counter_label=value(one(r'\d+\s*/\s*\d+', (20, 565, 100, 50))),
               selected_stage_id=fact(), selected_row_ordinal=fact(), earned_stars=fact(),
               current_entry_cost=fact(), completed=fact())
        groups = []
        for row in sorted(find(r'.+', (75, 175, 345, 385)), key=lambda r: (r[1]['box'][1], r[1]['box'][0])):
            start = re.fullmatch(r'(\d+)\s*[.]\s*(.+)', row[1]['text'].strip())
            if start:
                groups.append((int(start[1]), [row]))
            elif groups:
                previous = groups[-1][1][-1][1]['box']
                if 0 <= row[1]['box'][1] - previous[1] <= 32:
                    groups[-1][1].append(row)
        ordinals = [ordinal for ordinal, _ in groups]
        for ordinal, lines in groups:
            if ordinals.count(ordinal) != 1:
                continue
            label = joined(lines, 'aligned_visible_prequel_row_lines')
            title = dict(label, value=re.sub(r'^\d+\s*[.]\s*', '', label['value']))
            evidence = [source(row) for row in lines]
            available_match=observation.get('matches',{}).get('path_prequel_available',{})
            available_box=available_match.get('box')
            available=bool(available_match.get('hit') and available_box and
                           abs(available_box[1]+available_box[3]/2-lines[0][1]['box'][1]-lines[0][1]['box'][3]/2)<=25)
            add(node(p+f'/row:{ordinal}', 'item', p,
                     semantic_id=fact('stage_row', *evidence), adapter=fact('operations', *evidence),
                     ordinal=fact(ordinal, *evidence, derived('/text', 'explicit_prequel_row_number')),
                     title=title, stage_id=fact(), selected=fact(), locked=fact(), completed=fact(),
                     earned_stars=fact(), visible=fact(True, *evidence),
                     available=fact(True,{'kind':'recognition','pointer':'/matches/path_prequel_available'},*evidence) if available else fact(),
                     box=fact([min(r[1]['box'][0] for r in lines),min(r[1]['box'][1] for r in lines),
                               max(r[1]['box'][0]+r[1]['box'][2] for r in lines)-min(r[1]['box'][0] for r in lines),
                               max(r[1]['box'][1]+r[1]['box'][3] for r in lines)-min(r[1]['box'][1] for r in lines)],*evidence),
                     box_role=fact('text_anchor',*evidence),
                     layout_reference={'source':'wnd/battle_prequel.csb',
                                       'path':'/Layer/left/scrollview_stage','scope':'static_hint'}))
        # Reading the label does not grant a target or a generic free-story action.
        action_label = 'view_story_label' if state == 'prequel_story_map' else 'ready_label'
        add(node(p+'/'+action_label, 'item', p,
                 semantic_id=fact(action_label, source(view_story)),
                 adapter=fact('operations', source(view_story)), text=value(view_story),
                 box=fact(view_story[1]['box'], source(view_story)), box_role=fact('text_anchor', source(view_story)),
                 consuming=fact(), visible=fact(True, source(view_story)),
                 layout_reference={'source':'wnd/story_ready.csb','path':'/Layer/btn_go','scope':'static_hint'}))
        return view_name
    episode_team = one(r'Episode\s*-\s*Team',(0,55,145,60))
    story_team = one('Story Team',(150,65,150,55))
    own_preparation = state in ('unknown','battle_ready') and (episode_team or story_team) and one('Ready',heading)
    if state == 'prequel_preparation' or own_preparation:
        if (not supports_reading(observation)
                or not observation.get('matches', {}).get('prequel_ready_header',{}).get('hit')
                or not (episode_team or story_team or observation.get('matches',{}).get('prequel_story_team',{}).get('hit'))):
            return None
        ready = one('Ready', heading)
        team = episode_team or story_team
        start = one(r'Start Quest\s*[-+*]?', (1020, 590, 160, 75))
        search = one('Search', (1070,60,140,60))
        candidate = reader.label((940,220,270,85))
        candidate_add = one(r'\+', (875,230,65,80))
        if all((ready,team,search,candidate,candidate_add)):
            p = panel('prequel_formation', [ready,team,search,candidate], 'wnd/formation.csb', 'candidate_list')
            matches = observation.get('matches', {})
            destinations = []
            for position,area in (('right',(488,287,98,99)),('lower',(371,360,99,99))):
                name = f'formation_destination_{position}'
                match = matches.get(name, {});box = match.get('box');x,y,w,h = area
                if (match.get('hit') and box and len(box)==4 and min(box[2:])>0 and x<=box[0] and y<=box[1]
                        and box[0]+box[2]<=x+w and box[1]+box[3]<=y+h):
                    destinations.append((position,box,{'kind':'recognition','pointer':f'/matches/{name}'}))
            detail(p, team_kind_label=value(team),
                   team_label=joined(find(r'[A-Za-z][A-Za-z\s\u0027-]+', (150,105,180,60)), 'current_story_team_label_lines'),
                   team_cp=value(one(r'\d[\d,.]*', (210,620,190,50)), integer),
                   stage_id=fact(), team_instance_id=fact(), owned_roster=fact(),
                   selected_candidate_id=fact(), selected_slot=fact(), assignment_completed=fact(),
                   destination_positions_visible=(fact([pos for pos,_,_ in destinations], *(s for _,_,s in destinations))
                                                  if destinations else fact()),
                   cost=cost((900,590,120,75), 'energy'))
            add(node(p+'/candidate:visible_row', 'item', p,
                     semantic_id=fact('hero_candidate', source(candidate)), adapter=fact('operations', source(candidate)),
                     hero_name=value(candidate), level=value(one(r'\d+', (940,268,150,40)), int),
                     box=fact(candidate[1]['box'], source(candidate)), box_role=fact('text_anchor', source(candidate)),
                     visible=fact(True, source(candidate)), hero_instance_id=fact(), selected=fact(), assigned=fact()))
            control(p, 'candidate_add', candidate_add)  # Dynamic row control ancestry remains unresolved.
            control(p, 'search', search, path=('wnd/unit_list.csb','/Layer/RIGHT/n_equip_menu/btn_search_on'))
            for position,box,src in destinations:
                add(node(p+'/destination:'+position, 'item', p,
                         semantic_id=fact('formation_destination_marker', src), adapter=fact('operations',src),
                         visual_position=fact(position,src,derived('/matches','calibrated_visual_position_not_static_slot_id')),
                         box=fact(box,src),box_role=fact('template_extent',src),visible=fact(True,src),
                         slot_id=fact(),selected=fact(),hero_instance_id=fact(),
                         layout_reference={'source':'wnd/formation.csb','scope':'static_hint'}))
            appearance = matches.get('formation_victorika_right', {});box=appearance.get('box')
            if (appearance.get('hit') and box and len(box)==4 and min(box[2:])>0 and 486<=box[0] and 222<=box[1]
                    and box[0]+box[2]<=587 and box[1]+box[3]<=342):
                src={'kind':'recognition','pointer':'/matches/formation_victorika_right'}
                add(node(p+'/member:right_visual', 'item', p,
                         semantic_id=fact('formation_member_appearance',src),adapter=fact('operations',src),
                         appearance_label=fact('Inexperienced Victorika',src,source(candidate),
                             derived('/matches/formation_victorika_right','calibrated_current_member_sprite_not_cp_delta')),
                         visual_position=fact('right',src),box=fact(box,src),box_role=fact('template_extent',src),
                         visible=fact(True,src),hero_instance_id=fact(),slot_id=fact(),selected=fact()))
            for ordinal,area in enumerate(((215,180,85,65),(345,110,85,50)),1):
                story = one('Story',area)
                if story:
                    add(node(p+f'/story_marker:{ordinal}', 'item', p,
                             semantic_id=fact('story_member_marker',source(story)),adapter=fact('operations',source(story)),
                             text=value(story),box=fact(story[1]['box'],source(story)),box_role=fact('text_anchor',source(story)),
                             hero_name=fact(),hero_instance_id=fact(),slot_id=fact(),visible=fact(True,source(story))))
            return 'prequel_formation'
        # An unreadable/ambiguous roster row must not turn the formation
        # editor into the battle preparation behind its shared Ready shell.
        if search:
            return None
        location = reader.label((870, 65, 330, 45))
        title_rows = reader.preparation_title_rows()
        title_rows.sort(key=lambda row: row[1]['box'][1])
        title_ambiguous = (len(title_rows) > 3 or any(
            a[1]['box'][1]+a[1]['box'][3] > b[1]['box'][1]+3
            for a,b in zip(title_rows,title_rows[1:])))
        current_cost = cost((900, 590, 120, 75), 'energy')
        enemies=one(r'(?:[Xx]\s*)?Enemies',(875,245,300,65))
        if (not all((ready, team)) or not (start or enemies)
                or find('Cancel|Confirm', (300, 200, 600, 350))
                or find(r'.*Tap to close[.]?', (350, 480, 600, 202))):
            return None
        p = panel('prequel_preparation', [ready, team, start, enemies], 'wnd/battle_ready.csb', 'adventure_own_team' if episode_team else 'adventure_prequel',
                  back_destinations=[{'view':'prequel_ready_map'},{'view':'prequel_story_map'}])
        hero_levels=find(r'\d{1,2}',(180,140,420,220))
        story_members=find('Story',(180,140,420,220))
        detail(p, location=value(location),
               story_title=joined(title_rows, 'aligned_current_prequel_preparation_title') if not title_ambiguous else fact(),
               identity_basis=(fact('current_location_and_title_labels', source(location), *(source(r) for r in title_rows))
                               if location and title_rows and not title_ambiguous else fact()),
               stage_id=fact(), team_kind_label=value(team),
               team_label=joined(find(r'[A-Za-z][A-Za-z\s\u0027-]+', (130, 105, 210, 60)), 'aligned_story_team_label'),
               team_cp=value(one(r'\d[\d,.]*', (210, 610, 180, 65)), integer),
               cost=current_cost, hero_instances=fact(), earned_stars=fact(), objectives_complete=fact(),
               preparation_composition_verified=fact(True,source(ready),source(team)),
               visible_story_member_markers=(fact(len(story_members),*(source(r) for r in story_members))
                                             if story_members else fact()),
               visible_hero_levels=(fact([int(r['text'].strip()) for _,r in hero_levels],
                   *(source(r) for r in hero_levels)) if hero_levels else fact()))
        for slot, y in enumerate((155, 185, 215), 1):
            label = one(r'.+', (905, y, 305, 40))
            add(node(p+f'/objective:{slot}', 'item', p,
                     semantic_id=fact('stage_objective', source(label)) if label else fact('stage_objective', derived('/text','unread_prequel_objective_slot')),
                     adapter=fact('operations', derived('/text','current_prequel_preparation')),
                     slot=fact(slot, derived('/text','calibrated_prequel_objective_row')),
                     text=value(label), completed=fact(), condition=fact(), parameters=fact()))
        # The two static btn_go branches are not resolved to a live branch here.
        control(p, 'start_quest', start, True)
        return 'prequel_preparation'
    if state in ('battle_running', 'battle_nightmare_keeper', 'battle_mercenary_lydia'):
        matches = observation.get('matches', {})
        battle_context = (supports_reading(observation)
                          and all(matches.get(name, {}).get('hit') for name in ('battle_help','battle_pause')))
        highlighted = []
        for slot in (1,2,3):
            match = matches.get(f'skill_highlight_{slot}', {})
            box = match.get('box')
            if (battle_context and match.get('hit') and box and len(box) == 4
                    and 910+(slot-1)*96 <= box[0] and box[0]+box[2] <= 1020+(slot-1)*96
                    and 565 <= box[1] and box[1]+box[3] <= 682):
                highlighted.append((slot, match))
        cooldown_rows = {slot: (find(r'\d+\s*turn(?:\(s\)|s?)',
                            (924+(slot-1)*96, 610, 96, 45)) if battle_context else [])
                         for slot in (1,2,3)}
        cooldowns = {slot: found[0] if len(found)==1 else None
                     for slot,found in cooldown_rows.items()}
        actor_row=one(r'[A-Za-z][A-Za-z\s\u0027-]+', (185,585,350,50))
        rinak_context=bool(battle_context and actor_row and actor_row[1]['text'].strip()=='Rinak')
        resource_rows=find(r'[0-5]\s*/\s*5',(325,650,60,25)) if rinak_context else []
        resource_row=resource_rows[0] if len(resource_rows)==1 else None
        if highlighted or any(cooldown_rows.values()) or resource_rows:
            highlight_evidence = [{'kind':'recognition','pointer':f'/matches/skill_highlight_{slot}'}
                                  for slot,_ in highlighted]
            evidence = highlight_evidence + [source(row) for found in cooldown_rows.values() for row in found]
            evidence += [source(row) for row in resource_rows]
            p = 'operation:battle_skill_selection'
            add(node(p, 'panel', parent,
                     semantic_id=fact('battle_skill_selection', *evidence), adapter=fact('operations', *evidence),
                     view=fact('battle_skill_selection', *evidence), mode=fact('battle', *evidence),
                     visible=fact(True, *evidence),
                     layout_reference={'source':'wnd/hud_skill.csb','path':'/Layer/selected','scope':'static_hint'}))
            add(node(p+'/context', 'item', p,
                semantic_id=fact('context', *evidence), adapter=fact('operations', *evidence),
                highlighted_slot=(fact(highlighted[0][0], *evidence,
                derived('/matches','one_calibrated_selected_skill_border')) if len(highlighted)==1 else fact()),
                highlighted_candidates=fact([slot for slot,_ in highlighted],
                    derived('/matches','positive_highlight_candidates_only')),
                actor_label=value(actor_row),
                actor_hp_text=value(one(r'\d+\s*/\s*\d+', (275,630,110,25)) if rinak_context else None),
                resource_counter_text=value(resource_row),
                resource_counter=(fact(dict(zip(('current','maximum'),map(int,re.sub(r'\s','',resource_row[1]['text']).split('/')))),
                    source(resource_row),derived('/text','current_calibrated_resource_row_not_hp_or_team_cp')) if resource_row else fact()),
                resource_kind=fact(),runtime_variant_id=fact(),
                hero_instance_id=fact(), skill_id=fact(), selected_slot=fact(), turn_accepts_input=fact(),
                auto_enabled=fact(), auto_available=fact(), action_completed=fact()))
            for (slot,match),src in zip(highlighted,highlight_evidence):
                add(node(p+f'/highlight:{slot}', 'item', p,
                         semantic_id=fact('skill_highlight',src), adapter=fact('operations',src),
                         slot=fact(slot,src), box=fact(match['box'],src), box_role=fact('template_extent',src),
                         highlighted=fact(True,src), selected=fact(), visible=fact(True,src)))
            for slot in (1,2,3):
                row = cooldowns[slot]
                add(node(p+f'/slot:{slot}', 'item', p,
                    semantic_id=fact('skill_slot', derived('/matches','calibrated_skill_slot_region')),
                    adapter=fact('operations', *evidence),
                    slot=fact(slot, derived('/matches','calibrated_skill_slot_region')),
                    cooldown_text=(fact(row[1]['text'], source(row), confidence=row[1]['score']) if row else fact()),
                    cooldown_turns=value(row, lambda s: int(re.match(r'\d+',s)[0]), 'explicit_cooldown_turn_label'),
                    skill_id=fact(), selected=fact(), action_completed=fact(),
                    visible=fact(True, source(row)) if row else fact(),
                    layout_reference={'source':'wnd/hud_skill.csb','path':'/Layer/cooltime','scope':'static_hint'}))
            return 'battle_skill_selection'
    # Dialogs take precedence over every text in the underlying preparation.
    if state == 'tap_to_close_notice':
        return None

    skill_confirm = one('Skill Enhancement', (350, 95, 520, 80))
    question = one(r'Are you sure you want to enhance .+\?', (280, 175, 660, 75))
    if skill_confirm or question:
        if not (skill_confirm and question and one('Consumed Resources', (430, 330, 360, 70))):
            return None
        p = panel('hero_skill_confirmation', [skill_confirm, question], 'wnd/skill_up_confirm.csb')
        detail(p, selected_skill_name=value(question, lambda s: s[len('Are you sure you want to enhance '):-1]),
               gold_cost=value(one(r'\d[\d,.]*', (600, 435, 100, 55)), integer),
               material_count=value(one(r'\d+', (520, 435, 80, 55)), int),
               hero_instance_id=fact(), selected_skill_id=fact(), material_currency=fact())
        control(p, 'confirm_enhancement', one('Confirm', (610, 500, 220, 90)), True,
                ('wnd/skill_up_confirm.csb', '/Layer/CENTER/window_frame/btn_ok'))
        control(p, 'cancel', one('Cancel', (400, 500, 210, 90)), path=
                ('wnd/skill_up_confirm.csb', '/Layer/CENTER/window_frame/btn_cancel'))
        return 'hero_skill_confirmation'

    equipment_change = one('Change', (450, 135, 320, 85))
    change_message = one(r'E[qg]uipment will change as follows:', (350, 245, 520, 75))
    if equipment_change or change_message:
        if not (equipment_change and change_message):
            return None
        p = panel('equipment_change_confirmation', [equipment_change, change_message], 'wnd/equip_change_popup.csb')
        detail(p, current_cp=value(one(r'\d[\d,.]*', (380, 375, 170, 65)), integer),
               candidate_cp=value(one(r'\d[\d,.]*', (650, 375, 200, 65)), integer),
               current_instance_id=fact(), candidate_instance_id=fact(),
               gold_cost=(fact(0,{'kind':'recognition','pointer':'/matches/equipment_free_change'},
                              derived('/matches','calibrated_fee_free_second_confirmation'))
                          if (reader.match('equipment_free_change') or {}).get('box')==[614,472,227,59] else fact()))
        control(p, 'confirm_change', one('Change', (630, 460, 220, 85)), True,
                ('wnd/equip_change_popup.csb', '/Layer/n_show_eff/btn_buy'))
        control(p, 'cancel', one('Cancel', (380, 460, 220, 85)), path=
                ('wnd/equip_change_popup.csb', '/Layer/n_show_eff/btn_cancel'))
        return 'equipment_change_confirmation'
    equip_all = one('Equip All', (450, 20, 310, 80))
    change_preview = one('Change', (470, 555, 270, 75))
    if equip_all:
        if not (change_preview and len(find('Attack|Defense|Health|Speed', (300, 300, 190, 110))) >= 3):
            return None
        p = panel('equip_all_preview', [equip_all, change_preview], 'wnd/equip_change_popup.csb')
        candidate_cp = (one(r'[XxÃ—]?\s*\d{1,3}(?:[,.]\d{3})+(?:\s+\d[\d,.]*)?', (630,255,135,65))
                        or one(r'[XxÃ—]\s*\d{1,3}(?:[,.]\d{3})+(?:\s+\d[\d,.]*)?', (630,255,290,65)))
        detail(p, current_cp=value(one(r'\d[\d,.]*', (475, 255, 120, 65)), integer),
               candidate_cp=value(candidate_cp, lambda s: integer(re.search(r'\d{1,3}(?:[,.]\d{3})+', s)[0])),
               hero_instance_id=fact(), current_items=fact(), candidate_items=fact(), selection_applied=fact(),
               current_attributes=attributes(reader,preview=True),candidate_attributes=attributes(reader,preview=True,candidate=True))
        control(p, 'review_change', change_preview)
        return 'equip_all_preview'

    popup_unequip = one('Unequip', (435, 515, 115, 70))
    popup_change = one('Change', (540, 515, 100, 70))
    artifact_type = one(r'(?:Rare|Heroic|Epic|Normal) Artifact', (625, 85, 160, 70))
    artifact_skill = one('Artifact Skill', (430, 375, 180, 55))
    if popup_unequip and popup_change and artifact_type and artifact_skill:
        name = one(r'[A-Za-z][A-Za-z\s\u0027-]+', (625, 125, 160, 55))
        p = panel('artifact_detail', [artifact_type, artifact_skill, popup_unequip], 'wnd/item_detail.csb')
        detail(p, item_name=value(name), item_instance_id=fact(),
               skill_level=value(one(r'Lv[.]\s*\d+/\d+', (630, 170, 130, 50))),
               attack=value(one(r'\d+', (640, 235, 100, 30)), int),
               health=value(one(r'\d+', (640, 280, 100, 35)), int))
        control(p, 'unequip', popup_unequip, True, ('wnd/item_detail.csb', '/Layer/n_btn/btn_putoff'))
        control(p, 'change', popup_change)
        control(p, 'open_enhancement', one('Enhance', (640, 515, 140, 70)), path=
                ('wnd/item_detail.csb', '/Layer/n_btn/btn_upgrade'))
        return 'artifact_detail'
    equipment_score = one('Equipment Score', (420, 340, 230, 65))
    weapon_type = one('Weapon|Helmet|Armor|Necklace|Ring|Boots', (510, 75, 180, 65))
    if popup_unequip and popup_change and equipment_score and weapon_type:
        p = panel('equipment_detail', [equipment_score, weapon_type, popup_unequip], 'wnd/item_detail.csb')
        name_rows = find(r'[A-Za-z][A-Za-z\s\u0027-]+', (510, 108, 245, 50))
        detail(p, item_kind=value(weapon_type, str.casefold), item_name=joined(name_rows, 'aligned_item_name_lines'),
               enhancement_level=value(one(r'\+\d+', (480,60,65,40)),lambda s:int(s[1:])),
               equipment_score=value(one(r'\d+', (700, 340, 80, 60)), int), item_instance_id=fact())
        control(p, 'unequip', popup_unequip, True, ('wnd/item_detail.csb', '/Layer/n_btn/btn_putoff'))
        control(p, 'change', popup_change)
        control(p, 'open_enhancement', one('Enhance', (640,515,140,70)), path=
                ('wnd/item_detail.csb','/Layer/n_btn/btn_upgrade'))
        return 'equipment_detail'
    warning = one('Low Level Hero', (300, 130, 620, 100))
    if warning and one(r'There is a low.level Hero on your team[.]?', (250, 260, 710, 100)):
        p = panel('arena_entry_warning', [warning], 'wnd/pvp_unequipped_hero.csb', 'arena')
        control(p, 'cancel', one('Cancel', (250, 450, 700, 100)))
        control(p, 'confirm_entry', one('Confirm', (250, 450, 700, 100)), True)
        control(p, 'suppress_and_enter', one('Do Not Display', (250, 450, 700, 100)), True)
        return 'arena_entry_warning'
    quantity = one('Select Ingredients', (350, 140, 520, 90))
    if quantity and one('Choose ingredient amount', (300, 210, 620, 90)):
        p = panel('ingredient_quantity', [quantity], 'wnd/item_select_slidebar_popup.csb')
        detail(p, quantity=value(one(r'\d[\d,]*/\d[\d,]*', (400, 280, 420, 80))))
        control(p, 'select_quantity', one('Select', (430, 430, 360, 85)))
        return 'ingredient_quantity'
    # An unknown dialog's close affordance forbids promoting underlying controls.
    if find(r'.*Tap to close[.]?', (350, 630, 600, 52)):
        return None

    abyss = one('Abyss', (400, 345, 410, 75))
    floor_result = one(r'Floor\s+\d+', (400, 395, 410, 75))
    clear = one(r'C\s*L\s*E\s*A\s*R', (300, 170, 620, 160))
    if abyss and floor_result and clear and one(r'Con[qg]uer Reward', (400, 435, 410, 80)):
        p = panel('abyss_result', [abyss, floor_result, clear], 'wnd/result_base.csb', 'abyss')
        detail(p, floor=value(floor_result, lambda s: int(re.search(r'\d+', s)[0])),
               result=value(clear, lambda s: 'victory'))
        control(p, 'back', one('Back', footer))
        control(p, 'next_floor', one('Next Floor', footer), False, path=
                ('wnd/result_base.csb', '/Layer/n_hell/n_btns_normal/btn_hell_next'))
        return 'abyss_result'
    victory = one(r'V\s*I\s*C\s*T\s*O\s*R\s*Y', (280, 160, 680, 160))
    quick_victory = one('Victory', (350, 90, 520, 140))
    quick_confirm = one('Confirm', (610, 570, 220, 75))
    quick_results = one('Battle Results', (380, 570, 240, 75))
    if quick_victory and quick_confirm and quick_results:
        p = panel('arena_quick_result', [quick_victory, quick_confirm, quick_results], 'wnd/result_base.csb', 'arena')
        detail(p, result=value(quick_victory, lambda s: 'victory'),
               opponent_label=value(one(r'[A-Za-z][A-Za-z\s\u0027-]+', (625, 300, 290, 60))),
               opponent_instance_id=fact(), arena_type=fact())
        control(p, 'confirm_result', quick_confirm)
        control(p, 'battle_results', quick_results)
        return 'arena_quick_result'
    npc_result = one('NPC Challenge', (450, 395, 320, 75))
    npc_points_note = one('does not affect your Victory Points', (400, 430, 440, 65))
    if victory and npc_result and npc_points_note:
        p = panel('arena_result', [victory, npc_result, npc_points_note], 'wnd/result_base.csb', 'arena')
        detail(p, result=value(victory, lambda s: 'victory'), arena_type=value(npc_result, lambda s: 'npc'),
               victory_points=fact())
        control(p, 'confirm_result', one('Confirm', footer))
        control(p, 'battle_results', one('Battle Results', footer))
        return 'arena_result'
    if victory and one('Victory Points', (400, 340, 430, 90)):
        p = panel('arena_result', [victory], 'wnd/result_base.csb', 'arena')
        detail(p, result=value(victory, lambda s: 'victory'),
               victory_points=value(one(r'\d[\d,]*', (480, 405, 250, 50)), lambda s: int(s.replace(',', ''))))
        control(p, 'confirm_result', one('Confirm', footer))
        control(p, 'battle_results', one('Battle Results', footer))
        return 'arena_result'

    clear_reward = one('Clear Reward', (400, 175, 420, 100))
    if clear_reward and one('Next Difficulty', (1000, 515, 210, 85)) and one('Try again', (1000, 590, 210, 85)):
        p = panel('otherworld_result', [clear_reward], 'wnd/result_base.csb', 'otherworld')
        detail(p, result=value(clear_reward, lambda s: 'victory'), stage_id=fact())
        control(p, 'lobby', one('Lobby', (180, 590, 180, 85)))
        control(p, 'next_difficulty', one('Next Difficulty', (1000, 515, 210, 85)), True)
        control(p, 'try_again', one('Try again', (1000, 590, 210, 85)), True)
        return 'otherworld_result'

    arena = one('Rookie Arena', heading)
    if arena:
        start = one('Start|Quick Match', (720, 595, 150, 70))
        cp = one(r'\d{1,3}(?:,\d{3})+', (420, 510, 230, 60))
        if start and one('Add Team', (0, 600, 145, 82)):
            p = panel('arena_preparation', [arena, start, cp], 'wnd/pvp_ready.csb', 'arena')
            npc = one('NPC Challenge', (650, 500, 290, 65))
            detail(p, arena_type=value(npc, lambda s: 'npc') if npc else fact('normal',
                       source(start), derived('/text', 'arena_preparation_without_npc_requires_ranked_points'))
                       if one(r'\d+\s*pts[.]?', (700, 530, 250, 45)) else fact(),
                   cost=cost((645, 590, 85, 75), 'arena_flag'),
                   team_cp=value(cp, lambda s: int(s.replace(',', ''))),
                   quick=value(start, lambda s: s.casefold() == 'quick match'),
                   quick_remaining=value(one(r'\d+/\d+', (420, 630, 220, 40))),
                   team_instance_id=fact(), opponent_instance_id=fact())
            control(p, 'quick_match' if start[1]['text'].casefold() == 'quick match' else 'start', start, True)
            return 'arena_preparation'
        opponents = one('Opponents', (260, 70, 450, 80))
        npc_list = one('NPC Challenge', (260, 70, 450, 80))
        streak = one(r'(?:[+*]\s*)*\d+\s+Consecutive Victories!', (260, 70, 450, 80))
        ranked_streak = streak if one('Opponents', (950, 65, 260, 95)) else None
        if (opponents or npc_list or ranked_streak) and one('Challenge', (450, 580, 300, 90)):
            view = 'arena_npc_list' if npc_list else 'arena_opponents'
            p = panel(view, [arena, opponents or npc_list or ranked_streak], 'wnd/pvp_base.csb', 'arena')
            detail(p, selected_opponent=fact(), flags=value(one(r'\d+/\d+', (535, 5, 75, 48))),
                   consecutive_victories=value(ranked_streak, lambda s: int(re.search(r'\d+', s)[0])))
            control(p, 'challenge', one('Challenge', (450, 580, 300, 90)))
            control(p, 'opponents_tab', one('Opponents', (950, 65, 260, 95)))
            control(p, 'npc_tab', one('NPC Challenge', (950, 160, 260, 100)))
            for j, (i, r) in enumerate(rows):
                if (370 <= r['box'][0] <= 490 and 180 <= r['box'][1] <= 480
                        and not re.fullmatch(r'[\d,OoIl.\s]+pts[.]?', r['text'].strip(), re.I)):
                    add(node(p+f'/candidate:{j}', 'item', p, semantic_id=fact('opponent_label_fragment', source((i,r))),
                             text=fact(r['text'], source((i,r)), confidence=r['score']),
                             box=fact(r['box'], source((i,r))), box_role=fact('text_anchor', source((i,r))),
                             selected=fact(), owned_instance_id=fact()))
            return view
    hub = one('Arena', heading)
    rookie = one('Rookie Arena', (280, 570, 320, 100))
    if hub and rookie and one('Draft Arena', (20, 590, 270, 80)):
        p = panel('arena_hub', [hub, rookie], 'wnd/pvp_sel_renew.csb', 'arena')
        control(p, 'rookie_arena', rookie)
        return 'arena_hub'

    otherworld_team = one('Otherworld', (0, 65, 140, 50))
    if otherworld_team and one('Breach Team', (0, 85, 140, 50)) and one('Start', (1020, 590, 180, 80)):
        p = panel('otherworld_preparation', [otherworld_team], 'wnd/battle_ready.csb', 'otherworld')
        title = one(r'Remnant of Supremacy\s*-\s*(Normal|Hard|Hell)', (865, 180, 345, 70))
        detail(p, stage_id=fact(), title=value(title), difficulty=value(title, lambda s: s.split('-')[-1].strip()),
               cost=cost((920, 590, 110, 80), 'spectral_core'),
               team_cp=value(one(r'\d{1,3}(?:[,.]\d{3})+', (200, 610, 240, 65)),
                             lambda s: int(re.sub(r'[,.]', '', s))), team_instance_id=fact())
        control(p, 'start', one('Start', (1020, 590, 180, 80)), True)
        return 'otherworld_preparation'
    remnant = one('Remnant of', (20, 90, 280, 75))
    if remnant and one('Supremacy', (20, 140, 280, 70)) and one('Difficulty', (850, 150, 350, 75)):
        p = panel('otherworld_hub', [remnant], 'wnd/dungeon_home.csb', 'otherworld')
        for name in ('Normal','Hard','Hell'):
            control(p, name.casefold(), one(name, (950, 240, 260, 350)))
        return 'otherworld_hub'

    floor_ready = one(r'Floor\s+\d+', (860, 85, 340, 85))
    if one('Abyss', (860, 65, 340, 60)) and floor_ready and one('Start', (1020, 590, 180, 80)):
        p = panel('abyss_preparation', [floor_ready], 'wnd/battle_ready.csb', 'abyss')
        hero_levels=find(r'\d{1,2}',(180,140,420,220))
        detail(p, floor=value(floor_ready, lambda s: int(re.search(r'\d+', s)[0])),
               cost=cost((900, 590, 130, 80), 'energy'),
               team_cp=value(one(r'\d{1,3}(?:[,.]\d{3})+|\d+', (200, 610, 240, 65)), integer),
               team_instance_id=fact(),
               preparation_composition_verified=fact(True,source(floor_ready)),
               visible_hero_levels=(fact([int(r['text'].strip()) for _,r in hero_levels],
                   *(source(r) for r in hero_levels)) if hero_levels else fact()))
        control(p, 'start', one('Start', (1020, 590, 180, 80)), True)
        return 'abyss_preparation'
    floor_selected = one(r'Floor\s+\d+', (960, 180, 240, 90))
    abyss_heading = one('Abyss', (20, 125, 220, 90))
    if abyss_heading and floor_selected and one('Conquer Reward', (940, 280, 270, 60)):
        p = panel('abyss_floors', [abyss_heading, floor_selected], 'wnd/dungeon_hell.csb', 'abyss')
        detail(p, floor=value(floor_selected, lambda s: int(re.search(r'\d+', s)[0])))
        for i, row in find(r'Floor\s+\d+', (700, 40, 230, 630)):
            f = int(re.search(r'\d+', row['text'])[0])
            statuses = [(j, r) for j, r in rows if 700 <= r['box'][0] <= 820
                        and row['box'][1]+15 <= r['box'][1] <= row['box'][1]+45
                        and re.fullmatch(r'(?:[Vvâœ“]\s*)?Conquered|Available|Cannot proceed[.]?', r['text'].strip(), re.I)]
            s = statuses[0] if len(statuses) == 1 else None
            add(node(p+f'/floor:{f}', 'item', p, semantic_id=fact('abyss_floor', source((i,row))),
                     value=value((i,row), lambda t: f), status=value(s, lambda t:
                         'available' if t.casefold() == 'available' else 'locked' if 'cannot' in t.casefold() else 'conquered'),
                     box=fact(row['box'], source((i,row))), box_role=fact('text_anchor', source((i,row))),
                     selected=fact()))
        control(p, 'select_team', one('Select Team', footer))
        control(p, 'move_to_floor', one(r'Move to Floor\s+\d+', (940, 510, 270, 165)))
        control(p, 'replay', one('Replay', footer), True)
        return 'abyss_floors'
    if abyss_heading and one('Progress', (940, 70, 270, 65)) and one('Challenge Mode', (940, 400, 270, 100)):
        p = panel('abyss_hub', [abyss_heading], 'wnd/dungeon_home.csb', 'abyss')
        control(p, 'normal', one(r'Floor\s+\d+', (960, 260, 240, 65)))
        return 'abyss_hub'

    enhance = one('Enhance Equipment', heading)
    if enhance and (one('Enhancement Ingredients', (810, 60, 400, 75)) or one('Max Enhance', (0, 240, 380, 80))):
        p = panel('item_enhancement', [enhance], 'wnd/unit_item_upgrade.csb')
        detail(p, item_kind=fact('equipment' if one('Enhancement Ingredients', (810, 60, 400, 75)) else 'artifact',
                               source(enhance), derived('/text', 'ingredients_or_artifact_limit_branch')),
               exp=value(one(r'exp\s*[\d,]+\s*/\s*[\d,]+', (390, 410, 420, 55))),
               gold_cost=value(one(r'[\d,]+', (470, 600, 110, 60)), lambda s: int(s.replace(',', ''))),
               gold_balance=value(one(r'\d{1,3}(?:[,.]\d{3})+', (680,5,150,50)),integer),
               proposed_exp=value(one(r'\+[\d,]+\s*EXP', (390,350,430,100)),lambda s:int(re.sub(r'\D','',s))),
               enhancement_level=value(one(r'\+\d+', (380,75,280,280)),lambda s:int(s[1:])),
               item_instance_id=fact(), selected_materials=fact())
        control(p, 'enhance', one('Enhance', (590, 590, 190, 80)), True)
        control(p, 'auto_select', one('Auto Select', footer))
        return 'item_enhancement'
    equip_heading = one('Equip', heading)
    selecting = one('Selecting', (420, 50, 180, 55))
    selection_score = one('Equipment Score', (420, 390, 230, 65))
    if equip_heading and selecting and selection_score and one('Equip', (500, 590, 260, 80)):
        p = panel('equipment_selection', [equip_heading, selecting, selection_score], 'wnd/item_detail.csb')
        detail(p, item_name=joined(find(r'[A-Za-z][A-Za-z\s\u0027-]+', (530, 130, 250, 55)),
                                  'aligned_selected_item_name_lines'),
               equipment_score=value(one(r'\d+', (770, 390, 75, 65)), int),
               current_instance_id=fact(), candidate_instance_id=fact(), selection_applied=fact())
        control(p, 'equip', one('Equip', (500, 590, 260, 80)), True,
                ('wnd/item_detail.csb', '/Layer/n_btn/btn_puton'))
        return 'equipment_selection'
    manage = one('Manage Equipment', heading)
    if manage and one('Change', (940, 590, 260, 80)) and one('Recommended Equipment', (420, 595, 250, 70)):
        p = panel('equipment_comparison', [manage], 'wnd/equip_base.csb')
        detail(p, current_instance_id=fact(), candidate_instance_id=fact(), selection_applied=fact())
        control(p, 'change', one('Change', (940, 590, 260, 80)), True)
        control(p, 'open_enhancement', one('Enhance', (700, 590, 240, 80)))
        return 'equipment_comparison'
    equip_all_control = one('Equip All', (580, 610, 115, 65))
    unequip_all_control = one('Unequip All', (690, 610, 130, 65))
    manage_label = one('Manage', (490, 610, 115, 40))
    equipment_label = one('Equipment', (480, 635, 150, 40))
    hero_header = one(r'[A-Za-z][A-Za-z\s\u0027-]+', heading)
    hero_label = one(r'[A-Za-z][A-Za-z\s\u0027-]+', (90, 100, 275, 60))
    if (state == 'hero_screen' and (equip_all_control or unequip_all_control)
            and equipment_label and hero_header and hero_label
            and hero_header[1]['text'].casefold() == hero_label[1]['text'].casefold()
            and len(find('Attack|Defense|Health', (90, 380, 150, 80))) >= 3):
        p = panel('hero_equipment', [hero_header, hero_label, equip_all_control, unequip_all_control], 'wnd/unit_detail.csb')
        cp = one(r'[XxÃ—]?\s*\d{1,3}(?:[,.]\d{3})+', (90, 340, 200, 50))
        sets = find(r'.+ Set', (90, 580, 310, 85))
        detail(p, hero_name=value(hero_label), hero_instance_id=fact(),
               attributes=attributes(reader),
               cp=value(cp, lambda s: integer(re.sub(r'^[XxÃ—]\s*', '', s))),
               set_labels=fact([row['text'] for _, row in sets], *(source(r) for r in sets)) if sets else fact(),
               equipped_items=fact(), equipment_slots=fact(),
               recommendation_status=value(one(r'There is no better E[qg]uipment[.]?', (450, 600, 370, 50)),
                                           lambda s: 'no_better_equipment'))
        control(p, 'equip_all', equip_all_control, False,
                ('wnd/unit_detail.csb', '/Layer/n_menu_equipment/center_equipment/btn_equip'))
        control(p, 'unequip_all', unequip_all_control, True,
                ('wnd/unit_detail.csb', '/Layer/n_menu_equipment/center_equipment/btn_unequip'))
        control(p, 'manage_equipment', manage_label, path=
                ('wnd/unit_detail.csb', '/Layer/n_menu_equipment/center_equipment/btn_equip_detail'))
        return 'hero_equipment'
    skill_button = one('Skill Enhancement', (830, 590, 380, 85))
    skill_name = one(r'[A-Za-z][A-Za-z\s\u0027-]+', (910, 75, 295, 55))
    ladder = find(r'.*(?:damage|effect|chance|cooldown).*', (875, 175, 325, 335))
    if skill_button and skill_name and len(ladder) >= 2:
        p = panel('hero_skill_enhancement', [skill_button, skill_name], 'wnd/unit_skill_renewal.csb')
        detail(p, hero_instance_id=fact(), selected_skill_id=fact(), selected_skill_name=value(skill_name),
               gold_cost=value(one(r'\d+(?:[,.]\d{3})*', (1020, 540, 90, 50)), integer),
               material_count=value(one(r'\d+', (950, 540, 65, 50)), int), material_currency=fact())
        control(p, 'enhance_skill', skill_button, True)
        return 'hero_skill_enhancement'
    return None


def auto_nodes(observation, parent, add):
    """HUD state requires positive native matches, never absence or arrow angle."""
    if (observation.get('state') != 'battle_running'
            or observation.get('window', {}).get('client_size', [1212,682]) != [1212,682]):
        return
    matches = observation.get('matches', {})
    on = matches.get('auto_hud_on', {}).get('hit', False)
    old_off = matches.get('auto_hud_off', {}).get('hit', False)
    manual = matches.get('auto_manual_skills', {}).get('hit', False)
    unlocked = matches.get('auto_unlocked_off', {}).get('hit', False)
    # One calibrated HUD proves off directly. The manual-skills variant needs
    # the current unlocked control as well: onboarding can still lock Auto.
    off = old_off or (manual and unlocked)
    state = (on if on != off else None) if not (on and (old_off or manual)) else None
    keys = (['auto_hud_on'] if on else []) + (['auto_hud_off'] if old_off else [])
    if manual:
        keys.append('auto_manual_skills')
        if unlocked:
            keys.append('auto_unlocked_off')
    evidence = [{'kind': 'recognition', 'pointer': '/matches/'+key} for key in keys]
    if not evidence:
        evidence = [derived('/matches', 'no_positive_unambiguous_auto_proof')]
    add(node('battle:auto', 'control', parent,
             semantic_id=fact('battle_auto', derived('/state', 'battle_hud_context')),
             adapter=fact('vision', derived('/state', 'battle_hud_context')),
             box=fact([1068, 31, 1, 1], {'kind': 'profile', 'rule': 'calibrated_topbar_auto_point_1212x682'}),
             box_role=fact('calibrated_point', derived('/state', 'battle_hud_context')),
             value=fact(state, *evidence), enabled=fact(),
             layout_reference={'source': 'wnd/inbattle_topbar.csb',
                               'path': '/base/top_right/n_miscs/n_top_auto/btn_top_auto', 'scope': 'static_hint'}))


def formation_nodes(observation, parent, add):
    from .operational_formation import formation_nodes as adapt
    return adapt(observation,parent,add)
