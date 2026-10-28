"""Read-only catalog and conservative interpretation of the observed Orbis panel.

No game state is inferred from catalog rows. Coordinates below describe the
measured 1212x682 profile, never the local coordinates in a CSB file.
"""

import json
import re
from pathlib import Path

from .stages import normalize


MIN_SCORE = .90
PROFILE_SIZE = [1212, 682]


def mission_label_key(text):
    """Exact title with two observed equipment-word glyph variants only."""
    aliases={'eguip':'equip','eguipment':'equipment'}
    text=re.sub(r'\b(?:eguip|eguipment)\b',lambda m:aliases[m[0].lower()],text,flags=re.I)
    return normalize(text)


def has_text(rows, expected):
    """Exact normalized text, optionally wrapped in up to three aligned lines."""
    target = normalize(expected)
    valid = [r for r in rows if r["score"] >= MIN_SCORE]
    for first in valid:
        text = first["text"]
        if normalize(text) == target:
            return True
        previous = first
        for _ in range(2):
            x, y, w, h = previous["box"]
            following = [r for r in valid if abs(r["box"][0]-first["box"][0]) <= 25
                         and y+h-3 <= r["box"][1] <= y+h+22]
            if len(following) != 1:
                break
            previous = following[0]
            text += " " + previous["text"]
            if normalize(text) == target:
                return True
    return False


def navigation_context(observation):
    """Navigation depth is separate from a verified battle instance."""
    state = observation.get("state")
    rows = observation.get("text", [])
    kind = {"orbis_guide": "quest_panel", "episode_map": "stage_list", "battle_categories": "battle_categories",
            "quick_menu": "navigation_menu", "options_screen": "settings_menu", "hero_screen": "hero_menu",
            "supporter_selection": "supporter_selection", "battle_ready": "battle_preparation",
            "battle_running": "combat", "battle_rewards": "battle_result"}.get(state, "unknown")
    title = None
    difficulties = []
    if state == "unknown" and has_text(rows, "Battle") and has_text(rows, "Difficulty"):
        difficulties = [word for word in ("Normal", "Hard", "Hell") if has_text(rows, word)]
        if len(difficulties) >= 2 and has_text(rows, "Remnant of Supremacy"):
            kind, title = "mode_menu", "Remnant of Supremacy"
    elif state == "unknown" and has_text(rows, "Battle") and has_text(rows, "Seasonal") and has_text(rows, "Normal"):
        kind = "battle_categories"
    stage = observation.get("stage", {})
    stage_verified = bool(stage.get("identity_verified")) and kind in ("stage_list", "supporter_selection", "battle_preparation")
    return {"kind": kind, "title": title, "difficulty_options": difficulties,
            "stage_id": stage.get("requested_id") if stage_verified else None,
            "battle_identity_verified": stage_verified,
            "cost_verified": bool(stage_verified and stage.get("energy")
                                  and stage["energy"]["cost"] == stage.get("expected_energy")),
            "note": "Modo/categoria e dificuldade são níveis de navegação; não identificam uma batalha específica."}


def inside(row, roi):
    x, y, w, h = row["box"]
    left, top, width, height = roi
    return left <= x and top <= y and x+w <= left+width and y+h <= top+height


def counter(rows):
    values = []
    for row in rows:
        match = re.fullmatch(r"\s*(\d+)\s*/\s*(\d+)\s*", row["text"])
        if row["score"] >= MIN_SCORE and match:
            current, total = map(int, match.groups())
            if total > 0 and current <= total:
                values.append({"current": current, "total": total})
    return values[0] if len(values) == 1 else None


class QuestCatalog:
    def __init__(self, path, operation_map):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.tasks = {t["id"]: t for t in data["tasks"]}
        self.groups = {g["id"]: g for g in data["groups"]}
        mapping = json.loads(Path(operation_map).read_text(encoding="utf-8"))
        self.families = {c["condition"]: c["family"] for c in mapping["conditions"]}

    def get(self, task_id):
        if task_id not in self.tasks:
            raise ValueError("Missão ausente do catálogo: " + task_id)
        task = self.tasks[task_id]
        return {key: task[key] for key in ("id", "path", "group", "label", "condition", "parameters", "reward", "demo_excluded")} | {
            "family": self.families[task["condition"]],
            "group_name": self.groups[task["group"]]["name"],
            "account_progress": "not_in_static_catalog",
        }

    def list(self, path=None, group=None, family=None):
        return [self.get(t["id"]) for t in self.tasks.values()
                if (path is None or t["path"] == path)
                and (group is None or t["group"] == group)
                and (family is None or self.families[t["condition"]] == family)]

    def inspect(self, observation, claimed_matcher=None):
        report = {"profile": "steam-demo-en-1212x682", "group_id": None, "group_name": None,
                  "group_title_box": None,
                  "group_counter": None, "group_claim_ready": False, "group_receive_box": None,
                  "group_claimed": False,
                  "visible_tasks": [], "complete_group_inventory": False,
                  "reason": "panel_not_identified"}
        if observation.get("state") != "orbis_guide" or observation["window"]["client_size"] != PROFILE_SIZE:
            return report
        rows = [r for r in observation.get("text", []) if r["score"] >= MIN_SCORE]
        titles = [r for r in rows if inside(r, [400, 45, 640, 62])]
        groups = [g for g in self.groups.values()
                  if any(normalize(r["text"]) == normalize(g["name"]) for r in titles)]
        if len(groups) != 1:
            return report
        group = groups[0]
        tasks = [t for t in self.tasks.values() if t["group"] == group["id"]]
        report.update(group_id=group["id"], group_name=group["name"], path=group["path"], reason=None)
        report["group_title_box"] = next(row["box"] for row in titles if normalize(row["text"]) == normalize(group["name"]))
        # Group completion counts claimed missions; it is separate from each
        # task's condition counter. Never substitute one for the other.
        group_count = counter([r for r in rows if inside(r, [390, 155, 150, 60])])
        group_receive = [r for r in rows if inside(r, [975, 190, 165, 65])
                         and normalize(r["text"]) == "receive"]
        report["group_counter"] = group_count
        if len(group_receive) == 1:
            report["group_receive_box"] = group_receive[0]["box"]
        report["group_claim_ready"] = bool(group_count and group_count["current"] == group_count["total"] == len(tasks)
                                            and len(group_receive) == 1)
        report["group_claimed"] = bool(group_count and group_count["current"] == group_count["total"] == len(tasks)
                                        and not group_receive and claimed_matcher and claimed_matcher([1010, 195, 90, 62]))

        # Title and control must belong to the same fully visible row. Support
        # exact single-line titles first; clipped/wrapped/ambiguous text stays
        # unbound rather than guessed from sort order or a substring.
        labels = [r for r in rows if inside(r, [295, 285, 455, 335])]
        matched_titles = []
        for label in labels:
            candidates = [t for t in tasks if mission_label_key(t["label"]) == mission_label_key(label["text"])]
            if len(candidates) == 1:
                matched_titles.append((label, candidates[0]))
        for label, task in matched_titles:
            if sum(t["id"] == task["id"] for _, t in matched_titles) != 1:
                continue
            top = label["box"][1] - 12
            bottom = min(top+122, 622)
            band = [295, top, 845, bottom-top]
            counts = [r for r in rows if inside(r, band) and inside(r, [300, top+50, 435, 65])]
            value = counter(counts)
            raw_total = str(task.get("parameters", {}).get("count", ""))
            expected_total = int(raw_total) if raw_total.isdigit() else None
            if value and expected_total is not None and value["total"] != expected_total:
                value = None
            controls = [r for r in rows if inside(r, band) and inside(r, [975, top, 165, 100])
                        and normalize(r["text"]) in ("go", "receive", "received", "completed")]
            control = controls[0] if len(controls) == 1 else None
            word = normalize(control["text"]) if control else None
            tick = claimed_matcher([1010, int(top)+28, 90, min(65, int(bottom-top)-28)]) if claimed_matcher else None
            satisfied = value["current"] == value["total"] if value else None
            status = "unknown"
            if tick and control is None:
                status = "claimed"
            elif word in ("received", "completed"):
                status = "claimed"
            elif word == "receive" and satisfied is True:
                status = "claim_ready"
            elif word == "go" and satisfied is False:
                status = "incomplete"
            report["visible_tasks"].append({"task_id": task["id"], "label": task["label"],
                "title_match_rule": ('exact_mission_title_with_declared_equip_equipment_glyph_alias'
                    if normalize(task['label'])!=normalize(label['text']) else 'unique_exact_title_within_identified_group'),
                "family": self.families[task["condition"]], "counter": value,
                "expected_counter_total": expected_total,
                "condition_satisfied": satisfied, "status": status,
                "control": word, "control_box": control["box"] if control else None,
                "label_box": label["box"], "row_fully_visible": top+122 <= 622,
                "claimed_tick_box": tick,
                "demo_excluded": task["demo_excluded"]})
        report["complete_group_inventory"] = len(report["visible_tasks"]) == len(tasks)
        return report


def action_target(catalog, report, operation, identity, tree=None):
    def resolved(box, task_id, control):
        if tree is not None:
            from .observed_ui import query_control
            target = query_control(tree, report["group_id"], task_id, control)["node"]
            observed_box = target["fields"]["box"]["value"]
            if observed_box != box:
                raise ValueError("Árvore e leitura da missão divergem; entrada não autorizada.")
            return observed_box
        return box
    if report.get("path") != "heir":
        raise ValueError("Ações de missão calibradas inicialmente apenas no Path of Heir.")
    if not report.get("group_counter"):
        raise ValueError("Progresso do grupo não identificado; disponibilidade não confirmada.")
    if operation == "claim-group":
        if report["group_id"] != identity or not report["group_claim_ready"]:
            raise ValueError("Grupo solicitado não está identificado e pronto para resgate.")
        return resolved(report["group_receive_box"], None, "claim_group")
    task = catalog.get(identity)
    if task["demo_excluded"]:
        raise ValueError("Missão marcada como excluída da demo.")
    if task["group"] != report["group_id"]:
        raise ValueError("A missão pertence a outro grupo.")
    found = [r for r in report["visible_tasks"] if r["task_id"] == identity]
    if len(found) != 1 or not found[0]["row_fully_visible"]:
        raise ValueError("Missão precisa estar identificada em uma linha totalmente visível.")
    row = found[0]
    expected = "incomplete" if operation == "go" else "claim_ready"
    if operation not in ("go", "claim") or row["status"] != expected or not row["control_box"]:
        raise ValueError("A ação não corresponde ao estado observado da missão.")
    return resolved(row["control_box"], identity, operation)


def progress_signature(report):
    """Ignore OCR box jitter while waiting for a server-side state change."""
    return {"group": report.get("group_id"), "counter": report.get("group_counter"),
            "claimed": report.get("group_claimed"),
            "tasks": sorted((t["task_id"], t["status"], str(t["counter"])) for t in report["visible_tasks"])}


def compare_snapshots(before, after, task_id):
    from .runtime import check_observation
    # No age limit for historical comparison, but require the same window and
    # process session. Account switches are outside this check's evidence.
    check_observation(before, after["window"], before["epoch_seconds"])
    if after["epoch_seconds"] < before["epoch_seconds"]:
        raise ValueError("A observação final é anterior à inicial.")
    from .observed_ui import quest_view
    b, a = quest_view(before), quest_view(after)
    if not b["group_id"] or b["group_id"] != a["group_id"]:
        raise ValueError("Comparação exige o mesmo grupo identificado.")
    def find(report):
        found = [t for t in report["visible_tasks"] if t["task_id"] == task_id]
        if len(found) != 1:
            raise ValueError("Missão não identificada nas duas observações.")
        return found[0]
    old, new = find(b), find(a)
    delta = None
    if old["counter"] and new["counter"] and old["counter"]["total"] == new["counter"]["total"]:
        delta = new["counter"]["current"] - old["counter"]["current"]
    return {"task_id": task_id, "before_status": old["status"], "after_status": new["status"],
            "counter_delta": delta, "progress_verified": delta is not None and delta > 0,
            "condition_satisfied": new["condition_satisfied"],
            "claim_verified": old["status"] == "claim_ready" and new["status"] == "claimed",
            "note": "Ausência da linha ou abertura de banner não comprova resgate."}
