"""Finite STOVE coreloop readings; current evidence only, no executable controls."""
import re
from .observed_ui import fact, derived, node
from .profile import supports_reading


def coreloop_nodes(observation, parent, add):
    if observation.get('state') != 'unknown' or not supports_reading(observation):
        return None
    matches = observation.get('matches', {})
    from .reading import ReadContext
    reader = ReadContext(observation, parent, add)
    rows, find, one, src = reader.rows, reader.find, reader.one, reader.source

    def recog(key):
        return {'kind': 'recognition', 'pointer': '/matches/'+key}

    def marked(key):
        match = matches.get(key, {})
        box = match.get('box')
        return bool(match.get('hit') and box and len(box) == 4)

    def text(row):
        return fact(row[1]['text'], src(row), confidence=row[1]['score']) if row else fact()

    def number(key):
        match = matches.get(key, {})
        candidates = match.get('filtered_candidates', [])
        if (not marked(key) or match.get('ambiguous') or len(candidates) != 1
                or match.get('score', 0) < .98
                or not re.fullmatch(r'\+?\s*\d+', str(match.get('text', '')).strip())):
            return fact()
        return fact(int(re.sub(r'[+\s]', '', match['text'])), recog(key),
                    derived('/matches/'+key, 'unique_current_numeric_ocr_in_calibrated_region'),
                    confidence=match['score'])

    def panel(view, sources, layout, **fields):
        p = 'operation:'+view
        add(node(p, 'panel', parent, semantic_id=fact(view, *sources), adapter=fact('operations', *sources),
            view=fact(view, *sources), visible=fact(True, *sources),
            layout_reference={'source': layout, 'scope': 'static_hint'}))
        add(node(p+'/context', 'item', p, semantic_id=fact('context', *sources),
            adapter=fact('operations', *sources), **fields))
        return p

    # The current named decision takes precedence over anything behind the modal.
    decision_keys = ('coreloop_selector_confirmation', 'coreloop_selector_tenebria_question')
    if any(marked(k) for k in decision_keys):
        title = one('Use Selector', (490, 155, 230, 65))
        question = one(r'Would you like to summon Tenebria\??', (430, 245, 360, 40))
        irreversible = one(r'This decision cannot be reversed[.]?', (440, 275, 340, 35))
        if not (all(marked(k) for k in decision_keys) and title and question and irreversible):
            return None
        evidence = [*(recog(k) for k in decision_keys), src(title), src(question), src(irreversible)]
        panel('coreloop_selector_confirmation', evidence, 'wnd/msgbox.csb',
            title=text(title), question=text(question), irreversible_notice=text(irreversible),
            proposed_hero_name=fact('Tenebria', src(question), recog(decision_keys[1])),
            decision_irreversible=fact(True, src(irreversible)), confirmation_sent=fact(),
            received_hero_name=fact(), owned_instance_id=fact())
        return 'coreloop_selector_confirmation'
    if find('Confirm|Cancel', (300, 150, 650, 400)):
        return None

    tracks=[row for row in find(r'.+', (500, 430, 500, 90))
            if any(char.isalpha() for char in row[1]['text'])]
    track=tracks[0] if len(tracks)==1 else None
    header = one('Milestone of Radiance', (45, 5, 290, 55))
    # The currency strip crop includes the account balance. Its old digits
    # cannot gate this panel; current header and Receive prove composition.
    main_keys = ('milestone_read_header',)
    receive_key = next((k for k in ('milestone_read_receive', 'milestone_read_receive_limited') if marked(k)), None)
    if all(marked(k) for k in main_keys) and receive_key and header:
        evidence = [*(recog(k) for k in main_keys), recog(receive_key), src(header)]
        currency_sources = [recog('milestone_read_currencies')] if marked('milestone_read_currencies') else []
        evidence.extend(currency_sources)
        if track:evidence.append(src(track))
        price = number('milestone_read_cost')
        essence = number('milestone_read_essence')
        current_cost = (fact({'currency': 'to_essence', 'cost': price['value'], 'available': essence['value']},
            recog('milestone_read_cost'), recog('milestone_read_essence'), *currency_sources,
            recog(receive_key)) if price['value'] is not None and essence['value'] is not None else fact())
        panel('milestone_main', evidence, 'wnd/coreloop_main.csb', title=text(header), track_label=text(track),
            essence_balance=essence, origin_coin_balance=number('milestone_read_origin'),
            claim_cost=price, cost=current_cost,
            displayed_upgrade_probability=text(one(r'Chest Upgrade Probability \d+%', (600, 510, 310, 45))),
            progress_step=fact(), progress_total=fact(), claimed_steps=fact(), claim_completed=fact(),
            reward_identity=fact(), claim_enabled=fact())
        return 'milestone_main'

    names = [one(name, (x, 420, 180, 55)) for name, x in (('Kise', 25), ('Charles', 415), ('Tenebria', 795))]
    if marked('coreloop_selector_prompt') and all(names):
        evidence = [recog('coreloop_selector_prompt'), *(src(r) for r in names)]
        selected = marked('coreloop_selector_tenebria_bright') and marked('coreloop_selector_receive_normal')
        selected_sources = [recog('coreloop_selector_tenebria_bright'), recog('coreloop_selector_receive_normal'), src(names[2])]
        p = panel('coreloop_hero_selector', evidence, 'wnd/gacha_select_group.csb',
            candidate_names=fact([r[1]['text'] for r in names], *(src(r) for r in names)),
            selected_hero_name=fact('Tenebria', *selected_sources) if selected else fact(),
            selected_column=fact(3, *selected_sources) if selected else fact(),
            receive_appearance=fact('normal', recog('coreloop_selector_receive_normal')) if marked('coreloop_selector_receive_normal') else fact(),
            receive_enabled=fact(), received_hero_name=fact(), owned_instances=fact())
        for column, row in enumerate(names, 1):
            add(node(p+f'/candidate:{column}', 'item', p,
                semantic_id=fact('hero_candidate', src(row)), adapter=fact('operations', *evidence),
                name=text(row), display_column=fact(column, src(row), derived('/text', 'current_selector_column')),
                selected=fact(True, *selected_sources) if selected and column == 3 else fact(),
                owned=fact(), owned_instance_id=fact()))
        return 'coreloop_hero_selector'

    hero = one('Tenebria', (20, 50, 310, 70))
    obtained = one('Obtained', (85, 600, 150, 55))
    if marked('coreloop_obtained') and hero and obtained:
        evidence = [recog('coreloop_obtained'), src(hero), src(obtained)]
        panel('coreloop_hero_receipt', evidence, 'wnd/gacha_result_unit.csb',
            hero_name=text(hero), receipt_label=text(obtained), received_hero_name=text(hero),
            acquisition_announced=fact(True, *evidence), acquisition_origin=fact(),
            owned_instance_id=fact(), complete_roster=fact(), acknowledgement_completed=fact())
        return 'coreloop_hero_receipt'

    reward_keys = ('coreloop_catalyst_receipt', 'coreloop_catalyst_icon')
    if all(marked(k) for k in reward_keys):
        evidence = [recog(k) for k in reward_keys]
        panel('coreloop_item_receipt', evidence, 'wnd/coreloop_main_box_reward.csb',
            reward_name=fact('Rare Catalyst Selection Chest', *evidence),
            reward_quantity=number('coreloop_read_reward_quantity'), reward_announced=fact(True, *evidence),
            raw_headline=text(one(r'.*Rare Catalyst Selection Chest.*', (180, 140, 850, 70))),
            inventory_total=fact(), owned_item_instance_id=fact(), chest_opened=fact(), acknowledgement_completed=fact())
        return 'coreloop_item_receipt'
    return None
