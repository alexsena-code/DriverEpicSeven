"""Mapped notices/results; no identity or balance carried from earlier frames."""
import re
from .observed_ui import fact, derived


def notice_nodes(c):
    tutorial = c.one('Skip Tutorial', (1000, 5, 210, 55))
    artifact_instruction=c.one(r'You have acquired Artifact[.]?',(430,40,390,65))
    if tutorial and (not c.state.startswith('prequel_') or artifact_instruction):
        p = c.panel('tutorial', [tutorial,artifact_instruction], 'db/tutorial_guide.db', c.state)
        fragments = c.find(r'.+', (250, 100, 920, 560))
        c.detail(p, instruction_fragments=fact([r['text'] for _, r in fragments], *(c.source(r) for r in fragments)) if fragments else fact(),
                 underlying_page=fact(), current_hero=fact(), input_required=fact())
        c.control(p, 'skip', tutorial, consuming=False,match_key='tutorial_skip')
        return 'tutorial'
    close = c.one(r'(?:[Xx×]\s*)?Tap to close[.]?', (350, 420, 530, 262))
    awakening = c.one('Awakening Reward', (370, 130, 330, 60))
    level = c.one('Level Up Success', (370, 130, 330, 60))
    if awakening or level:
        description = c.one('Hero [Ss]tats? ha(?:s|ve) been increased due to (?:Awakening|leveling up)[.]?', (375, 200, 480, 55))
        if not (description and close):
            return 'stove_overlay_unresolved'
        view = 'hero_awakening_result' if awakening else 'hero_level_result'
        layout = 'wnd/dlg_zodiac_reward_stat.csb' if awakening else 'wnd/dlg_promote_levelup.csb'
        p = c.panel(view, [awakening or level, description, close], layout, 'result')
        c.detail(p, title=c.value(awakening or level), description=c.value(description),
                 hero_name=fact(), hero_instance_id=fact(), remaining_materials=fact(),
                 result_announced=fact(True, c.source(description)))
        bands = [(265,50),(340,35),(375,30)] if awakening else [(265,50),(340,38),(370,35),(398,32),(425,30)]
        occurrences = {}
        for y, h in bands:
            name = c.label((380, y, 180, h))
            change = c.one(r'(?:Lv[.]\s*)?\d[\d,.]*%?\s*[>→]\s*(?:Lv[.]\s*)?\d[\d,.]*%?', (600, y, 155, h))
            delta = c.one(r'\d[\d,.]*%?', (780, y, 80, h))
            if name:
                label_key = re.sub(r'\W+', '_', name[1]['text'].strip().lower()).strip('_')
                occurrence = occurrences.get(label_key, 0)
                occurrences[label_key] = occurrence + 1
                key = label_key + (f':{occurrence}' if occurrence else '')
                raw = change[1]['text'] if change else ''
                parts = re.split(r'\s*[>→]\s*', raw) if change else []
                c.item(p, 'stat:'+key, name, label=c.value(name), change_text=c.value(change),
                       before=c.value(change, lambda _: parts[0]) if len(parts)==2 else fact(),
                       after=c.value(change, lambda _: parts[1]) if len(parts)==2 else fact(), increase_text=c.value(delta))
        c.control(p, 'close', close, layout, '/Layer/btn_ok', False)
        return view

    # Reuse the mapped artifact result before the generic modal blocker. This
    # composition used to be below that blocker in the other client reader.
    artifact = c.one('Artifact Skill Enhance', (350, 115, 520, 80))
    if artifact:
        before = c.one(r'Lv[.]\s*\d+', (280, 205, 170, 65))
        after = c.one(r'Lv[.]\s*\d+', (610, 205, 170, 65))
        dismiss = c.one('Tap to close', (450, 480, 320, 80))
        if not (before and after and dismiss):return 'stove_overlay_unresolved'
        p = c.panel('artifact_skill_result', [artifact, before, after], 'wnd/unit_item_upgrade.csb')
        c.detail(p, before_level=c.value(before, lambda s:int(re.search(r'\d+',s)[0])),
                 after_level=c.value(after, lambda s:int(re.search(r'\d+',s)[0])), item_instance_id=fact())
        c.control(p, 'close_result', dismiss, consuming=False)
        return 'artifact_skill_result'

    date = c.one('Date Changed', (390, 165, 440, 70))
    if date:
        body = c.one(r'The date has changed,\s*proceeding to Lobby[.]?', (350, 300, 520, 75))
        if not (body and close):return 'stove_overlay_unresolved'
        p = c.panel('date_changed_notice', [date, body, close], 'wnd/msgbox.csb')
        c.detail(p, title=c.value(date), message=c.value(body), destination_label=fact('Lobby', c.source(body)), dismissed=fact())
        c.control(p, 'close', close, 'wnd/msgbox.csb', '/Layer/btn_default', False)
        return 'date_changed_notice'

    calendar = c.one(r'Collaboration Check.in Reward!?', (90, 25, 730, 80))
    newcomer = c.one('New Player Check-In Event', (70, 25, 600, 70))
    if calendar or newcomer:
        confirm = c.one('Confirm', (920, 560, 250, 100))
        receipt = c.one(r'Rewards Received:\s*\d+\s*/\s*\d+', (870, 535, 290, 55))
        insufficient = c.one('Insufficient Rank', (150, 240, 190, 60))
        success = c.one('Success!', (870, 470, 280, 70))
        mail_notice = c.one(r'All rewards will be sent to your mailbox[.]\s*Once you receive all the', (70, 545, 550, 60))
        newcomer_status = insufficient or (success if mail_notice else None)
        if not (confirm and (receipt if calendar else newcomer_status)):
            return 'stove_overlay_unresolved'
        p = c.panel('checkin_notice', [calendar or newcomer, confirm, receipt or newcomer_status], 'wnd/calendar.csb' if calendar else 'wnd/calendar_14days.csb', 'collaboration' if calendar else 'new_player')
        c.detail(p, title=c.value(calendar or newcomer), rewards_received_text=c.value(receipt),
                 consecutive_login_text=c.value(c.one(r'Consecutive Login:\s*\d+d', (880, 500, 300, 55))),
                 rank_requirement_notice=c.value(insufficient), current_rank=fact(), selected_day=fact(), reward_claimed=fact())
        c.control(p, 'confirm', confirm, 'wnd/calendar.csb' if calendar else 'wnd/calendar_14days.csb',
                  '/Layer/btn_close' if calendar else '/Layer/bg_frame/btn_close', False)
        return 'checkin_notice'

    buff = c.one('Buff Effect', (140, 80, 260, 65))
    if buff and close:
        if len(c.find(r'.*(?:Blessing|Exploration).*', (250, 160, 760, 450))) < 2:
            return 'stove_overlay_unresolved'
        p = c.panel('buff_effects', [buff, close], 'wnd/booster_tooltip.csb')
        c.detail(p, title=c.value(buff), effect_lines=c.lines((260, 165, 780, 450)), actual_remaining_seconds=fact())
        c.control(p, 'close', close, consuming=False)
        return 'buff_effects'

    rank_limit = c.one(r'Rank up!', (450, 175, 330, 70))
    if rank_limit:
        body = c.one(r'Maximum Energy has been increased[.]?', (400, 245, 430, 60))
        dismiss = c.one(r'Tap to close[.]?', (450, 420, 320, 70))
        if not (body and dismiss):return 'stove_overlay_unresolved'
        change = c.one(r'\d+\s*[>→]\s*\d+', (480, 315, 260, 65))
        p = c.panel('rank_up_result', [rank_limit, body, dismiss], 'wnd/dlg_rankup_up.csb', 'maximum_energy')
        c.detail(p, title=c.value(rank_limit), message=c.value(body), rank=fact(), recovered_energy=fact(),
                 maximum_energy_before=c.value(change, lambda s:int(re.split(r'[>→]', s)[0])),
                 maximum_energy_after=c.value(change, lambda s:int(re.split(r'[>→]', s)[1])),
                 energy_balance=fact())
        c.control(p, 'close', dismiss, 'wnd/dlg_rankup_up.csb', '/base/btn_ok', False)
        return 'rank_up_result'

    rank = c.one(r'RANK\s*UP', (450, 175, 330, 70))
    if rank:
        body = c.one(r"You.ve recovered \d+ Energy for Ranking up[.].*", (200, 550, 850, 75))
        number = c.one(r'\d+', (520, 220, 190, 110))
        if not (body and number):return 'stove_overlay_unresolved'
        p = c.panel('rank_up_result', [rank, body, number], 'wnd/rankup.csb')
        c.detail(p, rank=c.value(number, int), recovery_text=c.value(body),
                 recovered_energy=c.value(body, lambda s: int(re.search(r'recovered (\d+)', s)[1])), energy_balance=fact())
        c.control(p,'close',body,'wnd/rankup.csb',consuming=False)
        return 'rank_up_result'

    friendship = c.one('Hero Friendship Level Increase', (400, 120, 560, 70))
    if friendship:
        stranger = c.one('Stranger', (430, 275, 190, 60))
        met = c.one('Just Met', (770, 275, 180, 60))
        if not (stranger and met and close):return 'stove_overlay_unresolved'
        p = c.panel('hero_friendship_result', [friendship, stranger, met, close], 'wnd/result_intimacy.csb')
        c.detail(p, title=c.value(friendship), before_label=c.value(stranger), after_label=c.value(met),
                 before_level=fact(1, c.match_source('friendship_level_one')) if c.match('friendship_level_one') else fact(),
                 after_level=fact(2, c.match_source('friendship_level_two')) if c.match('friendship_level_two') else fact(),
                 hero_name=fact(), hero_instance_id=fact())
        c.control(p, 'close', close, 'wnd/result_intimacy.csb', '/Layer/btn_close', False)
        return 'hero_friendship_result'

    reward = c.one('Received Reward', (380, 120, 470, 80))
    if reward:
        close = c.one(r'(?:[Xx×]\s*)?Tap to close[.]?', (450, 460, 310, 100))
        body = c.one(r'(?:You have (?:successfully received the rewards|received Star Reward)[!.]?|All mail received)', (330, 195, 570, 80))
        if not (body and close):return 'stove_overlay_unresolved'
        p = c.panel('received_reward', [reward, body, close], 'wnd/msgbox_rewards.csb', 'receipt')
        c.detail(p, title=c.value(reward), receipt_announced=fact(True, c.source(body)),
                 displayed_reward_text=c.lines((300, 270, 650, 205)), reward_ids=fact(), quantities=fact(),
                 mission_ids=fact(), inventory_totals=fact())
        c.control(p, 'close', close, 'wnd/msgbox_rewards.csb', '/Layer/btn_ok', False)
        return 'received_reward'

    equipment = c.one('Equipment Acquired', (400, 40, 420, 70))
    if equipment:
        kind = c.one(r'(?:Epic|Heroic|Rare|Good|Normal)\s+(?:Weapon|Helmet|Armor|Necklace|Ring|Boots)', (550, 205, 195, 55))
        set_label = c.one(r'.+ Set\s*\(\d+/\d+\)', (480, 500, 265, 50))
        main_stat = c.label((450, 305, 180, 50))
        if not (kind and set_label and main_stat):
            return 'stove_overlay_unresolved'
        p = c.panel('equipment_receipt', [equipment, kind, set_label, main_stat], None)
        c.detail(p, title=c.value(equipment), type_label=c.value(kind), name_lines=c.lines((560, 245, 180, 60)),
                 enhancement=c.value(c.one(r'\+\d+', (515, 195, 75, 45)), lambda s:int(s[1:])),
                 main_stat_label=c.value(main_stat), main_stat_value=c.value(c.one(r'\d[\d,]*', (650, 305, 90, 50)), lambda s:int(s.replace(',',''))),
                 set_label=c.value(set_label), stat_lines=c.lines((470, 350, 270, 150)),
                 acquisition_announced=fact(True, c.source(equipment)), item_id=fact(), owned_instance_id=fact(),
                 equipped=fact(), current_lock=fact(), acknowledgement_completed=fact())
        c.control(p, 'lock', c.one('Lock', (830, 495, 100, 55)))
        c.control(p, 'sell', c.one('Sell', (830, 550, 100, 55)), consuming=True)
        return 'equipment_receipt'

    mail_question = c.one('Would you like to receive all mail in your inbox[?]', (380, 210, 470, 60))
    mail_heading = c.one('Mailbox', (40, 5, 260, 65))
    if mail_heading and mail_question:
        confirm = c.one('Confirm', (620, 415, 180, 65))
        cancel = c.one('Cancel', (420, 415, 180, 65))
        if not (confirm and cancel):
            return 'stove_overlay_unresolved'
        p = c.panel('mail_receive_confirmation', [mail_heading, mail_question, confirm, cancel], 'wnd/msgbox.csb')
        c.detail(p, question=c.value(mail_question), warning_lines=c.lines((300, 265, 600, 100)),
                 proposed_scope=fact('receive_all', c.source(mail_question)), completed=fact(), actual_rewards=fact())
        c.control(p, 'confirm', confirm, 'wnd/msgbox.csb', '/Layer/CENTER/n_show_eff/n_content/n_buttons/btn_yes', True)
        c.control(p, 'cancel', cancel, 'wnd/msgbox.csb', '/Layer/CENTER/n_show_eff/n_content/n_buttons/btn_cancel', False)
        return 'mail_receive_confirmation'

    mail_receive = c.one('Receive', (500, 490, 230, 65))
    mail_sender = c.label((270, 145, 230, 65))
    if mail_heading and mail_receive and mail_sender:
        p = c.panel('mail_detail', [mail_heading, mail_receive, mail_sender], 'wnd/mail_event_popup.csb')
        c.detail(p, sender=c.value(mail_sender), body_lines=c.lines((185, 200, 840, 285)),
                 mail_instance_id=fact(), reward_identity=fact(), quantity=fact(), received=fact())
        c.control(p, 'receive', mail_receive, 'wnd/mail_event_popup.csb', '/Layer/n_normal/btn_receive', True)
        c.control(p, 'close', c.one(r'(?:[Xx×]\s*)?Tap to close', (500, 630, 230, 50)),
                  'wnd/mail_event_popup.csb', '/Layer/btn_cancel', False)
        return 'mail_detail'

    story = c.one('Story Clear', (420, 125, 400, 80))
    if story:
        close = c.one(r'(?:[Xx×]\s*)?Tap to close[.]?', (450, 430, 310, 100))
        body = c.one('You have received Story Clear Reward[.]?', (350, 210, 520, 70))
        if not (body and close):return 'stove_overlay_unresolved'
        p = c.panel('story_reward', [story, body, close], None, 'receipt')
        c.detail(p, receipt_announced=fact(True, c.source(body)), chapter_text=c.value(c.one(r'Chapter\s+\d+[.]?', (540, 280, 400, 50))),
                 story_lines=c.lines((540, 320, 520, 85)), rewards=fact(), stage_id=fact())
        c.control(p, 'close', close, consuming=False)
        return 'story_reward'

    auto_assign = c.one('Auto Assign', (420, 160, 370, 90))
    if auto_assign:
        body = c.lines((300, 290, 620, 85))
        confirm = c.one('Confirm', (610, 430, 230, 85))
        cancel = c.one('Cancel', (390, 430, 230, 85))
        if not (body['value'] and confirm and cancel):
            return 'stove_overlay_unresolved'
        p = c.panel('formation_auto_assign', [auto_assign, confirm, cancel], 'wnd/msgbox.csb', 'proposal')
        c.detail(p, title=c.value(auto_assign), description_lines=body, assigned_heroes=fact(), applied=fact())
        c.control(p, 'confirm', confirm, 'wnd/msgbox.csb', '/Layer/CENTER/n_show_eff/n_content/n_buttons/btn_yes')
        c.control(p, 'cancel', cancel, 'wnd/msgbox.csb', '/Layer/CENTER/n_show_eff/n_content/n_buttons/btn_cancel', False)
        return 'formation_auto_assign'

    altar = c.one('Spirit Altar', (430, 145, 400, 70))
    altar_body = c.one(r'You can now enter Spirit Altar[.]\s*Receive various Runes to Awaken', (320, 350, 570, 60))
    abyss = c.one('Abyss', (430, 145, 400, 70))
    abyss_body = c.one(r'You can enter Abyss[.]\s*Test your strength in the depths of the Abyss!', (320, 350, 570, 60))
    if (altar and altar_body) or (abyss and abyss_body):
        heading, body = (altar, altar_body) if altar and altar_body else (abyss, abyss_body)
        close = c.one(r'Tap\s*to\s*close', (450, 455, 310, 80))
        if not close:
            return 'stove_overlay_unresolved'
        p = c.panel('system_unlock_notice', [heading, body, close], 'wnd/unlock_system_open.csb')
        c.detail(p, title=c.value(heading), message_lines=c.lines((320, 350, 570, 80)),
                 unlock_announced=fact(True, c.source(body)), accessible_now=fact(), dismissed=fact())
        c.control(p, 'close', close, 'wnd/unlock_system_open.csb', '/Layer/btn_close', False)
        return 'system_unlock_notice'

    connection = c.one('Connection Unlocked', (410, 145, 430, 80))
    connection_pattern = r'A Connection with (.+?) has been unlocked[.]\s*You can'
    body = c.one(connection_pattern, (320, 350, 570, 60))
    if connection and body:
        ok = c.one('OK', (500, 450, 220, 75))
        if not ok:
            return 'stove_overlay_unresolved'
        p = c.panel('connection_unlock_notice', [connection, body, ok], 'wnd/msgbox.csb')
        c.detail(p, title=c.value(connection), hero_name=c.value(body, lambda s:re.fullmatch(connection_pattern,s,re.I)[1]),
                 message_lines=c.lines((320, 350, 570, 80)),
                 unlock_announced=fact(True, c.source(body)), acquired=fact(), hero_instance_id=fact())
        c.control(p, 'acknowledge', ok, 'wnd/msgbox.csb', '/Layer/CENTER/n_show_eff/n_content/n_buttons/btn_ok', False)
        return 'connection_unlock_notice'
    # A central dismiss label is enough to know that a modal covers the page,
    # even when its title/body failed OCR. The bottom Orbis/Recruit footer is
    # outside this region and remains owned by its respective adapter.
    if c.find(r'(?:[Xx×]\s*)?Tap to close[.]?', (350, 420, 530, 200)):
        return 'stove_overlay_unresolved'
    return None
