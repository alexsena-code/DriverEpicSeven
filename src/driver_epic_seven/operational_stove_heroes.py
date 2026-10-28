"""Current hero/Connections/growth panels, separate from proposals and receipts."""
import re
from .observed_ui import fact, node, derived


def _hero_name(c, header, body):
    # Screen identity comes from controls/layout. Conflicting or missing OCR
    # names affect only this field, never select a known character implicitly.
    if body is None or (header and header[1]['text'].strip() != body[1]['text'].strip()):
        return fact()
    return c.value(body)


def hero_nodes(c):
    # Three-card Recruit hub is an overlay, even when Summon remains behind it.
    connections = c.one('Connections', (90, 85, 300, 70))
    moonlight = c.one("Moonlight's Blessing", (450, 85, 330, 70))
    change = c.one('Specialty Change', (820, 85, 360, 70))
    if connections and moonlight and change:
        p = c.panel('recruit_hub', [connections, moonlight, change], None)
        c.detail(p, current_acquired_counter=c.ratio(c.one(r'\d+/\d+', (160, 565, 160, 60))),
                 selected_category=fact(), acquisition_completed=fact())
        for key, row in (('connections', connections), ('moonlight_blessing', moonlight), ('specialty_change', change)):
            c.control(p, key, row, consuming=False)
        return 'recruit_hub'

    heading = c.one('Connections', (45, 8, 270, 50))
    hero = c.label((15, 110, 455, 65))
    if heading:
        progress = c.one(r'[CT]onnection Progress', (15, 510, 280, 55))
        complete = c.one('Connection Complete', (100, 590, 380, 65))
        if not (progress or complete):
            return 'stove_overlay_unresolved'
        p = c.panel('connections', [heading, hero, progress, complete], 'wnd/destiny.csb')
        c.detail(p, hero_name=c.value(hero), acquired_counter=c.ratio(c.one(r'\d+/\d+', (1080, 60, 130, 50))),
                 progress_text=c.value(c.one(r'\d+%', (90, 540, 150, 45))),
                 requirement_lines=c.lines((560, 65, 545, 140)), hero_instance_id=fact(), acquired=fact())
        c.control(p, 'complete_connection', complete, 'wnd/destiny.csb', '/base/n_content/LEFT/n_bottom/btn_complete', True)
        for j, row in enumerate(c.find('Go|Receive', (1000, 65, 160, 440))):
            c.control(p, f'mission_control:{j}', row, 'wnd/destiny_achieve_item.csb', '/Layer/n_right/btn_go')
        return 'connections'

    blessing = c.one("Moonlight's Blessing", (40, 5, 420, 60))
    reset = c.one("Reset Moonlight's Blessing", (900, 80, 310, 65))
    if blessing:
        if not (reset and c.one('Skill Enhancement', (850, 390, 350, 60))):
            return 'stove_overlay_unresolved'
        p = c.panel('moonlight_blessing', [blessing, reset], 'wnd/destiny_moonlight_hero.csb')
        name = c.label((15, 55, 380, 65))
        c.detail(p, displayed_hero_name=c.value(name),
                 restriction_text=c.lines((15, 105, 435, 100)), hero_instance_id=fact(), restrictions_fully_unlocked=fact(),
                 tutorial_visible=fact(True, c.match_source('tutorial_skip')) if c.match('tutorial_skip') else fact())
        for key, box in [('promotion',(40,395,350,110)), ('awakening',(40,545,350,110)),
                         ('skill',(880,395,330,120)), ('defense',(880,540,330,115))]:
            c.item(p, 'requirement:'+key, requirement_lines=c.lines(box), completed=fact())
        c.control(p, 'reset', reset, consuming=True)
        return 'moonlight_blessing'

    header = c.label((45, 5, 410, 55))
    awakening_name = c.label((90, 120, 380, 60))
    awaken = c.one('Awaken', (960,590,240,75))
    potential = c.one('Potential Stone', (900,155,310,60))
    resources = c.one('Consumed Resource', (900,450,310,60))
    reward = c.one('Hero Awakening Reward', (900,220,310,55))
    # The badge follows the selected node of each zodiac constellation. Its
    # position is content-dependent; the fixed footer is a separate control.
    overview = c.one('Awaken', (0,60,1212,520))
    preview = bool(potential and resources and reward)
    if awaken and (preview or (overview and not any((potential, resources, reward)))):
        tutorial = c.one('Skip Tutorial', (1000,5,210,55))
        p = c.panel('hero_awakening', [awaken,overview,potential,resources,reward,header,awakening_name],
                    'wnd/unit_zodiac2_renewal.csb', 'tutorial' if tutorial else 'preview' if preview else 'overview',
                    back_destinations=[{'view':'hero_awakening','mode':'overview'}] if preview else [{'view':'hero_detail'},{'view':'hero_equipment'}])
        c.detail(p, hero_name=_hero_name(c,header,awakening_name), description_lines=c.lines((10,260,370,85)), selected_stone=c.value(potential),
                 material_ratio=c.ratio(c.one(r'\d+\s*/\s*\d+', (980,535,210,70)), 'available','cost') if preview else fact(),
                 material_name=fact(), material_id=fact(), current_awakened_stars=fact(), hero_instance_id=fact(),
                 proposed_stat_lines=c.lines((905,270,305,160)) if preview else fact(),
                 application_completed=fact(), remaining_materials=fact(),
                 tutorial_prompt=c.lines((440,565,350,90)) if tutorial else fact())
        c.control(p, 'awaken', awaken, 'wnd/unit_zodiac2_renewal.csb', '/Layer/BOTTOM/btn_up' if preview else '/Layer/BOTTOM/btn_go_awake', preview,
                  navigation=None if preview else [{'view':'hero_awakening','mode':'preview'}])
        c.control(p, 'skip_tutorial', tutorial, consuming=False)
        return 'hero_awakening'
    if awaken and any((overview, potential, resources, reward)):
        return 'stove_overlay_unresolved'

    penguins = c.one(r'Penguins [O0]wned:\s*\d+', (850,55,350,60))
    level_up = c.one('Level Up', (690,590,150,70))
    growth_name = c.label((15,110,375,65))
    auto_select = c.one('Auto Select',(930,590,260,70))
    if penguins and level_up and auto_select:
        before = c.one(r'Lv[.]\s*\d+', (15,190,150,55))
        proposed = c.one(r'Lv[.]\s*\d+', (225,190,145,55))
        p = c.panel('hero_level_up', [penguins,level_up,auto_select], 'wnd/unit_level_up.csb', 'preview' if proposed else 'current',
                    back_destinations=[{'view':'hero_detail'},{'view':'hero_equipment'}])
        c.detail(p, hero_name=_hero_name(c,header,growth_name), current_level=c.value(before, lambda s:int(re.search(r'\d+',s)[0])),
                 proposed_level=c.value(proposed, lambda s:int(re.search(r'\d+',s)[0])),
                 penguins_owned_text=c.value(penguins), gold_cost=c.value(c.one(r'\d[\d,]*', (590,590,110,70)), lambda s:int(s.replace(',',''))),
                 stat_lines=c.lines((20,265,330,250)), hero_instance_id=fact(), application_completed=fact())
        for j,y in enumerate((135,250,365)):
            rows=c.find(r'.+', (950,y,260,90))
            if rows:c.item(p,f'penguin:{j}',rows[0],displayed_lines=c.lines((950,y,260,90)),selected_count=fact(),available_before=fact())
        c.control(p,'level_up',level_up,'wnd/unit_level_up.csb','/Layer/CENTER/n_buttons/btn_up',True)
        c.control(p,'auto_select',auto_select,'wnd/unit_level_up.csb','/Layer/RIGHT/btn_auto',False)
        return 'hero_level_up'

    body_name = c.label((90,100,380,65))
    level = c.one(r'Lv[.]\s*\d+\s*/\s*\d+', (90,165,250,65))
    search = c.one('Search', (840,60,140,55))
    if not (level and search):
        return None
    # Do not promote the hero behind a preview, menu or unknown modal.
    if c.one('Equip All',(440,15,310,80)) or c.find(r'.*Tap to close[.]?',(350,630,560,52)):
        return None
    equip = c.one('Equip All',(520,605,130,65))
    stats = c.find('Attack|Defense|Health',(85,375,150,85))
    hero_tab = c.match('victorika_hero_tab')
    entry = c.one('Awaken',(730,610,140,60))
    if not ((equip and len(stats)==3) or (hero_tab and entry)):
        return None
    view='hero_equipment' if equip else 'hero_detail'
    p=c.panel(view,[header,body_name,level,search,equip,entry],'wnd/unit_detail.csb',match_keys=('victorika_hero_tab',) if hero_tab else (),
              back_destinations=[{'view':'lobby'}])
    parsed=re.fullmatch(r'Lv[.]\s*(\d+)\s*/\s*(\d+)',level[1]['text'].strip(),re.I)
    c.detail(p,hero_name=_hero_name(c,header,body_name),level=c.value(level,lambda _:int(parsed[1])) if parsed else fact(),
             level_cap=c.value(level,lambda _:int(parsed[2])) if parsed else fact(),
             traits_text=c.value(c.one(r'.*(?:Dark|Light|Fire|Earth|Ice).*(?:Thief|Warrior|Knight|Mage|Ranger|Soul Weaver).*',(90,65,380,45))),
             hero_instance_id=fact(),owned_roster_complete=fact(),equipped_items=fact(),equipment_slots=fact(),
             awakened_stars=fact(),
             cp=c.value(c.one(r'[Xx×]?\s*\d[\d,.]*',(90,335,250,55)),lambda s:int(re.sub(r'\D','',s))) if equip else fact(),
             stat_lines=c.lines((90,380,285,210)) if equip else fact(),
             set_labels=c.lines((90,585,300,75),r'.*set effect|.* Set') if equip else fact())
    for j,row in enumerate(c.find(r'.+',(925,105,285,480))):
        if any(char.isalpha() for char in row[1]['text']):
            c.item(p,f'roster_label:{j}',row,label_text=c.value(row),hero_name=fact(),hero_instance_id=fact(),selected=fact())
    for name,pattern,area,path in (
        ('equip_all','Equip All',(520,605,130,65),'/Layer/n_menu_equipment/center_equipment/btn_equip'),
        ('unequip_all','Unequip All',(640,605,150,65),'/Layer/n_menu_equipment/center_equipment/btn_unequip'),
        ('awaken','Awaken',(730,610,140,60),'/Layer/n_menu_hero/center_hero/btn_zodiac'),
        ('level_up','Level Up',(535,610,120,60),'/Layer/n_menu_hero/center_hero/btn_lv_up')):
        destination={'awaken':[{'view':'hero_awakening','mode':'overview'}],
                     'level_up':[{'view':'hero_level_up'}]}.get(name)
        marker={'awaken':'tieria_hero_awaken_entry','level_up':'tieria_hero_level_up_entry','equip_all':'equip_all_control'}.get(name)
        c.control(p,name,c.one(pattern,area),'wnd/unit_detail.csb',path,
                  consuming=False if destination else None,navigation=destination,match_key=marker)
    if view=='hero_equipment' and c.match('equip_all_control'):
        src=derived('/text','calibrated_weapon_container_1212x682_with_current_equipment_panel')
        c.add(node(p+'/weapon_slot','control',p,semantic_id=fact('weapon_slot',src),adapter=fact('operations',src),
                   box=fact([423,304,1,1],src),box_role=fact('calibrated_point',src),consuming=fact(False,src),
                   layout_reference={'source':'wnd/unit_detail.csb','path':'/Layer/n_menu_equipment/center_equipment/n_item/item_left/n_item_left_base/btn_item1','scope':'static_hint'}))
    return view
