"""Read-only STOVE compositions from the same observation used by the UI tree.

This module never captures, carries state across frames, or authorizes an action.
It consumes current native matches/OCR and keeps unsupported facts unknown.
"""
from .reading import ReadContext
from .profile import supports_reading


def stove_nodes(observation, parent, add):
    if not supports_reading(observation):
        return None
    # Combat has its own scoped adapters. Text on a combat HUD must never be
    # reinterpreted as a menu or a notice by the exploratory OCR compositions.
    if observation.get('state') in ('battle_running', 'battle_nightmare_keeper',
                                     'battle_mercenary_lydia', 'stage_clear'):
        return None
    context = ReadContext(observation, parent, add)
    from .operational_stove_notices import notice_nodes
    from .operational_stove_heroes import hero_nodes
    from .operational_stove_pages import page_nodes
    from .operational_stove_quests import quest_nodes
    from .operational_altar import altar_nodes
    # Overlays must precede their underlying pages. A partial recognized overlay
    # returns a blocker, never permission to reinterpret the page beneath it.
    for adapter in (notice_nodes, quest_nodes, hero_nodes, altar_nodes, page_nodes):
        view = adapter(context)
        if view:
            return view
    return None
