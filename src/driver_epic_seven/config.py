import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: str | None = None) -> dict:
    base = json.loads((ROOT / "config/epic-seven.json").read_text(encoding="utf-8"))
    chosen = path or os.environ.get("DRIVER_EPIC_SEVEN_CONFIG")
    if chosen:
        local = Path(chosen)
        if not local.is_absolute():
            local = ROOT / local
        base = merge(base, json.loads(local.read_text(encoding="utf-8")))
    if base["reference_size"] not in base.get("supported_client_sizes", [base["reference_size"]]):
        raise ValueError("Tamanho sem perfil calibrado; escolha uma resolução suportada.")
    base.setdefault("quest_file", "data/catalogs/quests.json")
    base.setdefault("operation_map_file", "data/missions/operation-map.json")
    for name in ("resource_dir", "vision_file", "registry_file", "stage_file", "runs_dir", "path_ledger", "stop_file", "session_lock", "quest_file", "operation_map_file"):
        value = Path(os.path.expandvars(base[name]))
        base[name] = value if value.is_absolute() else ROOT / value
    base["sentry_root"] = Path(os.path.expandvars(base["sentry_root"]))
    if base.get("campaign_ledger"):
        value=Path(base["campaign_ledger"])
        base["campaign_ledger"]=value if value.is_absolute() else ROOT/value
    if base["screencap_method"] not in (2, 32):
        raise ValueError("Método de captura sem suporte neste perfil; use FramePool (2) ou ScreenDC (32).")
    if base["mouse_method"] not in (1, 4, 64) or base["keyboard_method"] not in (1, 4):
        raise ValueError("Entrada sem suporte; mouse aceita Seize (1), PostMessage (4) ou PostMessageWithCursorPos (64); teclado aceita 1 ou 4.")
    return base
