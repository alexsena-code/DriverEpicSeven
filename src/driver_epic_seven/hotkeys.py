"""Static game key map and a deliberately small navigation-only input surface."""

import json
from pathlib import Path


KEY_CODES = {"escape": 0x1B, "tab": 0x09, "g": 0x47, "c": 0x43, "o": 0x4F, "1": 0x31, "3": 0x33}
# A bounded native Maa press lets the game's menu read both key edges.
KEY_PRESS_MS = 100
NAVIGATION_STATES = {"lobby", "quick_menu", "orbis_guide", "episode_map", "options_screen", "hero_screen", "battle_categories"}


def catalog(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {"source": data["source"], "scope": data["scope"], "records": data["rows"],
            "explicit_bindings": data["with_explicit_binding"], "bindings": data["bindings"],
            "live_validations": data.get("live_validations", {})}
