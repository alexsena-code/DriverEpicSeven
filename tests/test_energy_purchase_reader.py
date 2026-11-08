from driver_epic_seven.observed_ui import build_tree, operation_view


def row(text, box):
    return {'text': text, 'box': box, 'score': 0.99}


def dialog():
    return {'state': 'unknown', 'text': [
        row('Purchase Energy', [493, 134, 220, 40]),
        row('You can purchase Energy with the following currencies', [376, 220, 457, 23]),
        row('80', [517, 364, 27, 22]), row('60', [789, 364, 25, 20]),
        row('0wned:14', [427, 392, 83, 17]), row('Owned:2928', [689, 388, 102, 23]),
        row('Cancel', [369, 508, 62, 26]), row('Buy', [587, 511, 34, 23]),
        row('Pack', [801, 510, 47, 22]),
    ]}


def test_energy_dialog_is_read_only_and_does_not_infer_currency():
    view = operation_view({'ui_tree': build_tree(dialog())})
    assert view['view'] == 'energy_purchase'
    info = view['items'][0]
    assert (info['left_owned'], info['right_owned']) == (14, 2928)
    assert (info['left_result'], info['right_result']) == (80, 60)
    assert info['selected_currency'] is None and info['selected_cost'] is None
    buy = next(c for c in view['controls'] if c['semantic_id'] == 'buy')
    assert buy['consuming'] is True and buy['enabled'] is None


def test_similar_or_ambiguous_panels_are_not_energy_dialogs():
    for changed in ('missing', 'duplicate', 'other_state'):
        obs = dialog()
        if changed == 'missing':
            obs['text'] = [r for r in obs['text'] if r['text'] != 'Pack']
        elif changed == 'duplicate':
            obs['text'].append(row('Buy', [590, 511, 34, 23]))
        else:
            obs['state'] = 'battle_ready'
        assert operation_view({'ui_tree': build_tree(obs)}).get('view') != 'energy_purchase'


def test_shifted_footer_keeps_currency_unknown():
    obs = dialog()
    for r in obs['text']:
        if r['text'] in ('Cancel', 'Buy', 'Pack'):
            r['box'][0] += 103
    info = operation_view({'ui_tree': build_tree(obs)})['items'][0]
    assert info['selected_currency'] is None and info['selected_cost'] is None


def test_selected_leaf_requires_a_positive_native_card_match():
    obs = dialog()
    obs['matches'] = {'energy_leaf_selected': {'hit': True, 'box': [357, 289, 226, 100]}}
    info = operation_view({'ui_tree': build_tree(obs)})['items'][0]
    assert (info['selected_currency'], info['selected_cost']) == ('leif', 1)
    obs['matches']['energy_leaf_selected']['hit'] = False
    info = operation_view({'ui_tree': build_tree(obs)})['items'][0]
    assert info['selected_currency'] is None and info['selected_cost'] is None
