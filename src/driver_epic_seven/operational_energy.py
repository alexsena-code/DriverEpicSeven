"""Read the energy purchase dialog without authorizing a purchase."""
import re

from .observed_ui import fact, derived
from .reading import ReadContext


def energy_nodes(observation, parent, add):
    reader = ReadContext(observation, parent, add)
    title = reader.one(r'Purchase Energy', (360, 110, 500, 85))
    description = reader.one(r'You can purchase Energy with the following currencies\.?',
                             (300, 195, 620, 65))
    cancel = reader.one(r'Cancel', (300, 485, 300, 75))
    buy = reader.one(r'Buy', (500, 485, 310, 75))
    pack = reader.one(r'Pack', (700, 485, 310, 75))
    if observation.get('state') != 'unknown' or not all((title, description, cancel, buy, pack)):
        return None
    if not cancel[1]['box'][0] < buy[1]['box'][0] < pack[1]['box'][0]:
        return None
    panel = reader.panel('energy_purchase', [title, description, cancel, buy, pack],
                         'wnd/battle_ready_buy.csb')
    left_owned = reader.one(r'[O0]wned\s*:\s*\d[\d,]*', (360, 380, 220, 50))
    right_owned = reader.one(r'[O0]wned\s*:\s*\d[\d,]*', (620, 380, 220, 50))
    left_amount = reader.one(r'\d+', (485, 350, 90, 42))
    right_amount = reader.one(r'\d+', (750, 350, 90, 42))
    leaf_selected = reader.match('energy_leaf_selected')

    def owned(row):
        return reader.value(row, lambda text: int(re.sub(r'\D', '', text.split(':', 1)[1])))

    selected_source = reader.match_source('energy_leaf_selected')
    reader.detail(panel, left_owned=owned(left_owned), right_owned=owned(right_owned),
                  left_result=reader.value(left_amount, int),
                  right_result=reader.value(right_amount, int),
                  selected_currency=fact('leif', selected_source) if leaf_selected else fact(),
                  selected_cost=fact(1, selected_source) if leaf_selected else fact(),
                  selection_note=fact('leaf_card_template' if leaf_selected else 'unverified',
                                      derived('/matches/energy_leaf_selected', 'current_selected_card')))
    reader.control(panel, 'cancel', cancel, consuming=False,
                   layout='wnd/battle_ready_buy.csb', path='btn_cancel')
    reader.control(panel, 'buy', buy, consuming=True,
                   layout='wnd/battle_ready_buy.csb', path='btn_yes')
    return 'energy_purchase'
