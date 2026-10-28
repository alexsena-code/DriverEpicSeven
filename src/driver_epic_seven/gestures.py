"""Bounded native gestures, not a second action scheduler."""

SKILL_POINTS = ((968, 627), (1062, 627), (1156, 627))
MANUAL_BATTLE_STATES = ("battle_running", "battle_nightmare_keeper", "battle_mercenary_lydia")


def skill_double_tap_graph(point, state, size):
    """Two taps are one native gesture; never applicable to a Start/claim control."""
    if list(size) != [1212, 682] or tuple(point or ()) not in SKILL_POINTS:
        raise ValueError("Toque duplo limitado aos três centros de habilidade calibrados em 1212 × 682.")
    if state not in MANUAL_BATTLE_STATES:
        raise ValueError("Toque duplo de habilidade exige contexto de combate reconhecido.")
    return {
        "SkillDoubleTap.Entry": {
            "recognition": "DirectHit", "action": "DoNothing", "pre_delay": 0,
            "post_delay": 0, "timeout": 1500, "next": ["SkillDoubleTap.Tap"],
        },
        "SkillDoubleTap.Tap": {
            "recognition": "Custom", "custom_recognition": "ScreenTarget",
            "custom_recognition_param": {"state": state},
            "action": "Click", "target": [*point, 1, 1],
            "repeat": 2, "repeat_delay": 80, "max_hit": 1,
            "pre_delay": 0, "post_delay": 0, "rate_limit": 50,
            "timeout": 1500, "next": ["SkillDoubleTap.Done"],
        },
        "SkillDoubleTap.Done": {
            "recognition": "DirectHit", "action": "DoNothing", "pre_delay": 0, "post_delay": 0,
        },
    }
