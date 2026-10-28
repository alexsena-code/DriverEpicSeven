"""Mapped STOVE navigation, inventory and presentation readings."""
import re
from .observed_ui import fact


def page_nodes(c):
    question=c.one(r'Would you like to apply the Recommended List\??',(350,270,520,75))
    confirm_recommended=c.one('Confirm',(620,400,190,75))
    cancel_recommended=c.one('Cancel',(410,400,190,75))
    if question and confirm_recommended and cancel_recommended:
        p=c.panel('summon_wish_list_confirmation',[question,confirm_recommended,cancel_recommended],'wnd/msgbox.csb')
        c.detail(p,question=c.value(question),applied=fact())
        c.control(p,'confirm',confirm_recommended,consuming=False)
        c.control(p,'cancel',cancel_recommended,consuming=False)
        return 'summon_wish_list_confirmation'
    register=c.one('Register Wish List',(90,35,410,65))
    recommend=c.one('Apply Recommended List',(220,550,240,65))
    unacquired=c.one('Show unacquired only',(580,35,350,65))
    close_wish=c.one(r'(?:[Xx×]\s*)?Tap to close[.]?',(450,630,310,52))
    if register and recommend and unacquired and close_wish:
        p=c.panel('summon_wish_list',[register,recommend,unacquired,close_wish],'wnd/gacha_wish_choose.csb')
        c.detail(p,title=c.value(register),selection_count=fact(),selected_hero_instances=fact(),recommended_applied=fact())
        c.control(p,'apply_recommended',recommend,consuming=False)
        c.control(p,'close',close_wish,consuming=False,navigation=[{'view':'summon_page','mode':'covenant'}])
        return 'summon_wish_list'
    # Existing shared adapters own equipment/coreloop overlays. Do not expose
    # their underlying page, and let those adapters inspect the same frame.
    if c.find(r'(?:[Xx×]\s*)?Tap to close[.]?', (350, 630, 530, 52)):
        return None
    settings=c.one('Settings',(40,5,220,60))
    account=c.one('Account Info',(100,75,260,65))
    game=c.one(r'[+]\s*Game Settings',(100,75,300,65))
    if settings and (account or game):
        p=c.panel('settings',[settings,account or game],'wnd/option.csb','game' if game else 'account')
        # Only whitelisted option labels; never export account identifiers.
        c.detail(p,title=c.value(settings),section=c.value(account or game),option_values=fact())
        if game:
            for key,pattern,area in (
                ('profile_cards',r"Display Others'Profile Cards",(130,235,400,55)),
                ('lobby_viewing','Lobby Viewing Mode',(130,305,400,65)),
                ('entry_animation','Lobby Illustration Entry Animation Settings',(130,380,470,65))):
                row=c.one(pattern,area)
                if row:c.item(p,key,row,label=c.value(row),displayed_choices=c.lines((560,area[1],560,area[3]),r'On|Off|Always|Once a Day'),selected_value=fact())
        return 'settings'

    # Quick menu anchors are geometrically distinct from the ordinary lobby.
    guide=c.one('Orbis Guide',(840,145,135,55))
    journal=c.one('Journal',(975,145,110,55))
    recruit=c.one('Recruit',(1090,250,120,60))
    episode=c.one('Episode',(690,145,150,65))
    if all((guide,journal,recruit,episode)):
        p=c.panel('quick_menu',[guide,journal,recruit,episode],'wnd/quick_menu_renew.csb')
        c.detail(p,underlying_page=fact(),selected_entry=fact())
        for key,pattern,area,path in (
            ('episode','Episode',(690,145,150,65),'/Layer/n_quick_menu/notch_main_btn/main_btn/btn_map'),
            ('orbis','Orbis Guide',(840,145,135,55),'/Layer/n_quick_menu/notch_hide_btn/n_quick_btn/n_guidebook/btn_guidebook'),
            ('hero','Hero',(1090,145,120,55),'/Layer/n_quick_menu/notch_hide_btn/n_quick_btn/n_unit_detail/btn_unit_detail'),
            ('recruit','Recruit',(1090,250,120,60),'/Layer/n_quick_menu/notch_hide_btn/n_quick_btn/n_recruit/btn_recruit'),
            ('summon','Summon',(690,405,150,60),'/Layer/n_quick_menu/notch_main_btn/main_btn/btn_gacha')):
            c.control(p,key,c.one(pattern,area),'wnd/quick_menu_renew.csb',path,False)
        for j,row in enumerate(c.find('Journal|Friends|Guild|Pet House|Grace of Growth|Reputation|Battle|Arena|Shop',(690,145,520,390))):
            c.item(p,f'entry:{j}',row,label=c.value(row),locked=fact(),enabled=fact())
        return 'quick_menu'

    # Adventure preparation has one canonical adapter in operational_ui.
    # Do not publish a second set of title/cost/control names for this panel.

    inventory=c.one('Inventory',(40,5,260,65))
    if inventory:
        empty=c.one('You have no items[.]',(300,385,400,65))
        none=c.one('No items selected',(850,385,350,65))
        use=c.one('Use',(1030,600,170,70))
        owned=c.one(r'\d+\s*owned',(1030,265,180,55))
        if empty and none:
            p=c.panel('inventory',[inventory,empty,none],'wnd/inventory.csb','empty_current_list')
            c.detail(p,empty_message=c.value(empty),current_capacity=c.ratio(c.one(r'\d+/\d+',(960,70,130,60))),
                     selected_tab=fact(),all_inventory_empty=fact(),item_instance_id=fact())
            return 'inventory'
        if use and owned and c.one('You can choose a Rare Catalyst to',(810,295,390,60)):
            p=c.panel('inventory_item',[inventory,use,owned],'wnd/inventory_renewal.csb','selection_chest_detail')
            c.detail(p,name_lines=c.lines((910,175,290,70)),owned_quantity=c.value(owned,lambda s:int(re.match(r'\d+',s)[0])),
                     description_lines=c.lines((815,300,390,125)),item_instance_id=fact(),selected_reward=fact(),opened=fact())
            c.control(p,'use',use,consuming=True)
            return 'inventory_item'
        return 'stove_inventory_unresolved'

    mail=c.one('Mailbox',(40,5,260,65))
    receive_all=c.one('Receive All',(980,600,230,65))
    mail_count=c.one(r'Mail\s+\d+/\d+',(820,600,180,65))
    if mail and receive_all and mail_count:
        p=c.panel('mailbox',[mail,receive_all,mail_count],'wnd/mail_list.csb')
        c.detail(p,mail_count_text=c.value(mail_count),selected_tab=fact(),all_claimed=fact())
        for j,row in enumerate(c.find('Receive',(1000,100,200,480))):
            y=row[1]['box'][1]
            c.item(p,f'mail:{j}',row,subject_lines=c.lines((220,max(90,y-5),490,60)),
                   reward_text=c.lines((860,y+25,130,60)),mail_instance_id=fact(),claimed=fact())
            c.control(p,f'receive:{j}',row,consuming=True)
        c.control(p,'receive_all',receive_all,'wnd/mail_list.csb',consuming=True)
        return 'mailbox'

    shop=c.one('Shop',(40,3,230,65))
    dawning=c.one('Dawning',(475,65,160,40))
    trajectory=c.one('Trajectory',(475,98,170,40))
    shop_note=c.one(r'Once Dawning Trajectory is complete,\s*all products will be available for purchase',(280,610,900,55))
    if shop and dawning and trajectory and shop_note:
        p=c.panel('milestone_shop',[shop,dawning,trajectory,shop_note],'wnd/shop_base_renew.csb','dawning_trajectory')
        c.detail(p,shop_title_lines=c.lines((475,65,170,75)),availability_note=c.value(shop_note),currency_balance=fact(),selected_item=fact())
        for row_y in (145,377):
            for col,x in enumerate((300,488,676,864)):
                labels=c.find(r'.+',(x,row_y,182,35))
                if not labels:continue
                anchor=labels[0];suffix=f'offer:{row_y}:{col}'
                c.item(p,suffix,anchor,label_fragment=c.lines((x,row_y,182,35)),
                       stock_text=c.value(c.one(r'\d+/\d+',(x,row_y+29,182,45))),
                       price_text=c.value(c.one(r'\d[\d,]*',(x,row_y+168,182,45))),
                       item_id=fact(),currency_id=fact(),available=fact(),selected=fact())
        return 'milestone_shop'

    next_button=c.one('Next',(1000,590,175,70))
    preview_name=c.label((15,50,460,65))
    details=c.one('Details',(75,170,150,70))
    confirm=c.one('Confirm',(1000,590,180,75))
    traits_pattern=r'.*(?:Dark|Light|Fire|Earth|Ice).*(?:Thief|Warrior|Knight|Mage|Ranger|Soul Weaver).*|.*(?:Thief|Warrior|Knight|Mage|Ranger|Soul Weaver).*(?:Dark|Light|Fire|Earth|Ice).*'
    traits=c.one(traits_pattern,(15,5,480,55))
    back=c.one('Back',(75,590,180,70))
    voice_left=c.one(r'(?:CV|VA):\s*.+',(20,235,370,65))
    dialogue=c.one(r'.+',(200,545,820,75))
    if back and details and traits and voice_left and preview_name:
        p=c.panel('hero_presentation',[back,details,traits,voice_left,preview_name],
                  'wnd/gacha_result_unit.csb','dialogue' if dialogue else 'presentation')
        c.detail(p,hero_name=c.value(preview_name,lambda s:re.sub(r'\s*[*★☆]+\s*$','',s)),
                 traits_text=c.value(traits),voice_label=c.value(voice_left),
                 dialogue_lines=c.lines((200,545,820,75)),acquired=fact(),owned_instance_id=fact(),origin=fact())
        if dialogue:
            c.control(p,'advance_dialogue',dialogue,consuming=False,
                      navigation=[{'view':'hero_presentation','mode':'presentation'}])
        else:
            c.control(p,'back',back,consuming=False,navigation=[{'view':'summon_page','mode':'covenant'}])
        return 'hero_presentation'
    if details and (next_button or (confirm and traits)):
        p=c.panel('hero_presentation',[next_button,confirm,details,traits],'wnd/gacha_result_unit.csb','candidate_preview' if next_button else 'presentation')
        c.detail(p,hero_name=c.value(preview_name,lambda s:re.sub(r'\s*[*★☆]+\s*$','',s)),traits_text=c.value(traits),
                 description_lines=c.lines((20,110,330,75)),
                 dialogue_lines=c.lines((200,550,820,85)),acquired=fact(),owned_instance_id=fact(),next_enabled=fact(),origin=fact())
        c.control(p,'next',next_button,'wnd/gacha_result_unit.csb','/Layer/n_result/n_buttons/btn_next',False)
        c.control(p,'confirm',confirm,'wnd/gacha_result_unit.csb','/Layer/n_result/n_buttons_ext/btn_close',False)
        c.control(p,'details',details,consuming=False)
        return 'hero_presentation'

    alternate_traits=c.one(traits_pattern,(190,55,230,70))
    voice=c.one(r'(?:CV|VA):\s*.+',(200,230,300,60))
    new_label=c.one('NEW!?',(400,195,150,60))
    if confirm and alternate_traits and voice and new_label:
        p=c.panel('hero_presentation',[confirm,alternate_traits,voice,new_label],'wnd/gacha_result_unit.csb','presentation')
        c.detail(p,hero_name=c.value(c.label((220,120,250,90))),traits_text=c.value(alternate_traits),
                 voice_label=c.value(voice),new_label=c.value(new_label),description_lines=c.lines((120,270,420,90)),
                 acquired=fact(),owned_instance_id=fact(),origin=fact(),summon_performed=fact())
        c.control(p,'confirm',confirm,'wnd/gacha_result_unit.csb','/Layer/n_result/n_buttons_ext/btn_close',False)
        return 'hero_presentation'
    if c.state=='renoa_promotional_presentation':
        p=c.panel('hero_presentation',[],'wnd/gacha_result_unit.csb','promotion',('renoa_promo_name','renoa_promo_traits','renoa_promo_description'))
        c.detail(p,hero_name=fact(c.match('renoa_promo_name').get('text'),c.match_source('renoa_promo_name')) if c.match('renoa_promo_name') else fact(),
                 description_lines=c.lines((120,270,420,90)),acquired=fact(),summon_performed=fact(),owned_instance_id=fact())
        c.control(p,'confirm',c.one('Confirm',(1000,590,180,70)),'wnd/gacha_result_unit.csb','/Layer/n_result/n_buttons_ext/btn_close',False)
        return 'hero_presentation'

    chest=c.match('stove_coreloop_chest_presentation')
    tap=c.one(r'Tap the screen[.]?',(480,565,270,70))
    if chest and tap:
        p=c.panel('milestone_chest_presentation',[tap],None,match_keys=('stove_coreloop_chest_presentation',))
        c.detail(p,prompt=c.value(tap),contents=fact(),rarity=fact(),reward_obtained=fact())
        c.control(p,'advance',tap,consuming=False)
        return 'milestone_chest_presentation'

    summon=c.one('Summon',(40,5,220,60))
    wish=c.one(r'Wish List\s*\(\d+/14\)',(570,495,260,70))
    wish_text=c.one('Make a wish list of your own',(470,315,470,70))
    single=c.one('Summon',(820,590,135,55))
    free=c.one('D?Free',(730,595,100,55))
    free_tip=c.one('Free Summon',(760,530,180,45))
    available=c.one(r'Available!?\s*1/1',(760,555,180,45))
    if summon and wish and single:
        p=c.panel('summon_page',[summon,wish,wish_text,single],'wnd/gacha_renew.csb','covenant',
                  back_destinations=[{'view':'lobby'}])
        zero=bool(re.fullmatch(r'Wish List\s*\(14/14\)',wish[1]['text'])
                  and free_tip and available and c.match('path_free_summon'))
        c.detail(p,title=c.value(summon),selected_banner=fact('covenant',c.source(wish),c.source(summon)),
                 wish_list_text=c.value(wish),free_available=fact(zero,c.source(free_tip) if free_tip else c.source(wish)),
                 actual_cost=fact({'currency':'covenant_bookmark','amount':0,'quantity':1},c.match_source('path_free_summon'),c.source(available),c.source(wish)) if zero else fact(),
                 summon_performed=fact(),owned_instance_id=fact())
        c.control(p,'wish_list',wish,'wnd/gacha_renew_covenant.csb',consuming=False,
                  navigation=[{'view':'summon_wish_list'}])
        if zero:
            c.control(p,'free_summon',single,'wnd/gacha_renew.csb','/Layer/n_before/n_btn_summon_1/btn_summon_1',True,match_key='path_free_summon')
        return 'summon_page'
    count=c.one(r'T?otal Summon Count Reward\s*\(\d+/\d+\)?',(220,450,430,65))
    if summon and count and c.one('Covenant',(15,560,200,65)):
        p=c.panel('summon_page',[summon,count],'wnd/gacha_renew.csb')
        c.detail(p,title=c.value(summon),reward_counter_text=c.value(count),banner_name=c.value(c.label((210,350,390,90))),
                 free_labels=c.lines((5,545,210,50),r'\d+ time\(s\) for free!'),selected_banner=fact(),summon_performed=fact(),actual_cost=fact())
        c.control(p,'covenant_tab',c.one('Covenant',(15,560,200,65)),consuming=False,
                  navigation=[{'view':'summon_page','mode':'covenant'}],match_key='path_covenant_tab')
        return 'summon_page'

    if c.state in ('story','story_intro','tieria_connection_dialogue','story_confirmation'):
        view='story_confirmation' if c.state=='story_confirmation' else 'story_dialogue'
        p=c.panel(view,[],'wnd/story.csb',match_keys=('story_skip','story_history','story_confirm_question','tieria_dialogue_name','tieria_dialogue_line'))
        gray=bool(c.match('path_story_skip_gray') and c.match('path_story_history_gray'))
        c.detail(p,speaker=c.value(c.one(r'.+',(400,480,420,55))),dialogue_lines=c.lines((150,545,940,95)),
                 skip_visible=fact(True,c.match_source('story_skip')) if c.match('story_skip') else fact(),
                 history_visible=fact(True,c.match_source('story_history')) if c.match('story_history') else fact(),
                 skip_gesture=fact('hold' if gray else 'click',c.match_source('path_story_skip_gray') if gray else c.match_source('story_skip'))
                     if c.state=='story' else fact(),
                 acquired=fact(),story_completed=fact())
        c.control(p,'confirm',c.one('Confirm',(620,395,220,80)),consuming=False)
        c.control(p,'cancel',c.one('Cancel',(380,395,220,80)),consuming=False)
        return view

    lobby_labels=[c.one(name,(1000,135,210,390)) for name in ('Episode','Side Story','Battle','Arena','Summon','Shop')]
    lobby_rank=c.one(r'Rank[.]\d+',(90,30,150,45))
    if c.state in ('lobby','lobby_idle') or (c.state=='unknown' and all(lobby_labels) and lobby_rank):
        p=c.panel('lobby',lobby_labels+[lobby_rank],'wnd/lobby_ui_renew.csb','idle' if c.state=='lobby_idle' else 'visible_hud',match_keys=('lobby_stained_window','lobby_menu_grid','lobby_idle_upper_left'))
        c.detail(p,rank_text=c.value(c.one(r'Rank[.]\d+',(90,30,150,45))),unlocked_modes=fact())
        if c.state!='lobby_idle':
            for name in ('Episode','Side Story','Battle','Arena','Summon','Shop'):
                c.control(p,name.casefold().replace(' ','_'),c.one(name,(1000,135,210,390)),consuming=False)
            c.control(p,'hero',c.one('Hero',(890,620,140,55)),consuming=False,
                      navigation=[{'view':'hero_detail'},{'view':'hero_equipment'}],shortcut='c')
            orbis=c.one('Orbis',(800,615,100,40))
            guide=c.one('Guide',(800,640,100,40))
            if orbis and guide:
                c.control(p,'orbis',orbis,consuming=False,
                          navigation=[{'view':'orbis_guide'}],shortcut='g')
        return 'lobby'

    if c.state in ('tutorial_prompt','tutorial_lobby','tutorial_episode_prompt','equipment_tutorial_prompt'):
        prompt = c.lines((300,100,650,550))
        p=c.panel('tutorial',[],'db/tutorial_guide.db',c.state,('tutorial_skip','equipment_tutorial_instruction'))
        c.detail(p,prompt_lines=prompt,current_hero=fact(),input_required=fact())
        c.control(p,'skip',c.one('Skip Tutorial',(1000,5,210,55)),consuming=False)
        return 'tutorial'

    if c.state=='battle_rewards' and c.one('Acquired Items',(960,15,250,60)):
        confirm=c.one('Confirm',(1000,590,190,70))
        results=c.one('Battle Results',(850,590,180,70))
        if not(confirm and results):return None
        p=c.panel('battle_rewards',[confirm,results],'wnd/result_base.csb','reward_screen')
        c.detail(p,rank_text=c.value(c.one(r'Rank[.]\d+',(40,5,200,45))),items=fact(),reward_claimed=fact())
        for j,x in enumerate((70,285,495,705)):
            row=c.one(r'Lv[.]\d+/\d+',(x,590,190,45))
            if row:c.item(p,f'hero:{j}',row,name_lines=c.lines((x,550,190,45)),level_text=c.value(row),exp_text=c.value(c.one(r'exp\s*\+\s*[\d,]+',(x,625,190,45))),hero_instance_id=fact())
        c.control(p,'confirm',confirm,'wnd/result_base.csb',consuming=False)
        c.control(p,'battle_results',results,consuming=False)
        return 'battle_rewards'
    return None
