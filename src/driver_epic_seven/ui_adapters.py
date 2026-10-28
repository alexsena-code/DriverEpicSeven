"""Adapters for existing visual and stage recognition; no new recognizers."""

import re

from .observed_ui import fact, derived, node


def campaign_objective_nodes(observation, parent, add):
    """Read the calibrated adventure requirement labels, never infer earned stars.

    Uses only the existing read-screen OCR. A gold star beside a requirement is
    decoration on an unplayed stage too; completion needs independent evidence.
    """
    if (observation.get('state') not in ('battle_ready', 'supporter_selection')
            or observation.get('window', {}).get('client_size') != [1212, 682]):
        return
    rows = []
    for index, row in enumerate(observation.get('text', [])):
        box = row.get('box')
        if (isinstance(box, (list, tuple)) and len(box) == 4
                and all(isinstance(v, (int, float)) for v in box)
                and row.get('score', 0) >= .90 and isinstance(row.get('text'), str)
                and min(box[:2]) >= 0 and min(box[2:]) > 0
                and box[0] + box[2] <= 1212 and box[1] + box[3] <= 682):
            rows.append((index, row))

    def one(pattern, area):
        x, y, w, h = area
        candidates = [(i, r) for i, r in rows
            if re.fullmatch(pattern, r['text'].strip(), re.I)
            and x <= r['box'][0] and y <= r['box'][1]
            and r['box'][0] + r['box'][2] <= x+w
            and r['box'][1] + r['box'][3] <= y+h]
        return candidates[0] if len(candidates) == 1 else None

    def src(row):
        return {'kind': 'ocr', 'pointer': f'/text/{row[0]}', 'engine': 'Maa/en_us'}

    def observed(row):
        return fact(row[1]['text'], src(row), confidence=row[1]['score']) if row else fact()

    start = one('Start Quest', (1010, 590, 190, 75))
    location = one(r'[A-Za-z][A-Za-z\s\u0027-]+', (870, 65, 340, 40))
    title = one(r'[A-Za-z][A-Za-z\s\u0027-]+', (870, 105, 220, 45))
    # Unknown closeable overlays must not expose objectives from behind them.
    central_cancel = one('Cancel', (250, 140, 700, 450))
    central_decision = one('Confirm|Change|Expand|Arrange', (250, 140, 700, 450))
    if (not (start and location and title)
            or one(r'.*Tap to close[.]?', (350, 480, 600, 202))
            or (central_cancel and central_decision)):
        return
    labels = [one(r'.+', (905, y, 305, 31)) for y in (155, 185, 215)]
    if sum(label is not None for label in labels) < 2:
        return
    anchors = [src(start), src(location), src(title)]
    p = add(node('operation:campaign_preparation', 'panel', parent,
        semantic_id=fact('campaign_preparation', *anchors),
        adapter=fact('operations', *anchors), view=fact('campaign_preparation', *anchors),
        mode=fact('adventure', *anchors), visible=fact(True, *anchors),
        layout_reference={'source': 'wnd/battle_ready.csb', 'scope': 'static_hint'}))
    stage = observation.get('stage', {})
    verified = stage.get('identity_verified') is True
    add(node(p+'/context', 'item', p,
        semantic_id=fact('context', *anchors), adapter=fact('operations', *anchors),
        location=observed(location), story_title=observed(title),
        stage_id=fact(stage.get('requested_id'), derived('/stage', 'current_stage_identity_verified'))
            if verified else fact(),
        record_label=observed(one('No Record', (1090, 100, 120, 55))),
        earned_stars=fact(), objectives_complete=fact(),
        coverage=fact('requirement_labels_only', *anchors)))
    for slot, label in enumerate(labels, 1):
        condition, parameters = None, None
        if label:
            text = label[1]['text'].strip()
            if text.casefold() == 'initial clear':
                condition = 'clear_enter_count'
                parameters = {'count': 1}
            elif text.casefold() == 'clear with no continues':
                condition = 'clearnocontinue_enter_count'
                parameters = {'count': 1}
            else:
                element = re.fullmatch(r'Have (\d+) (Fire|Ice|Earth|Light|Dark) Hero(?:es)? in the Team', text, re.I)
                if element:
                    condition = 'party_enter_attribute_count'
                    parameters = {'count': int(element[1]), 'attribute': element[2].casefold()}
        provenance = ([src(label), derived(f'/text/{label[0]}', 'calibrated_adventure_requirement_label')]
            if label else [derived('/text', 'unread_calibrated_objective_slot')])
        add(node(p+f'/objective:{slot}', 'item', p,
            semantic_id=fact('stage_objective', *provenance), adapter=fact('operations', *provenance),
            slot=fact(slot, derived('/text', 'calibrated_adventure_requirement_row')),
            text=observed(label), condition=fact(condition, *provenance),
            parameters=fact(parameters, *provenance), completed=fact(), status=fact(),
            box=fact(label[1]['box'], src(label)) if label else fact(),
            box_role=fact('text_anchor', src(label)) if label else fact(),
            visible=fact(True, src(label)) if label else fact()))


def visual_nodes(observation, spec, parent, add):
    state = observation.get("state")
    for index, row in enumerate(observation.get("text", [])):
        source = {"kind": "ocr", "pointer": f"/text/{index}", "engine": "Maa/en_us"}
        add(node(f"ocr:{index}", "item", parent,
            semantic_id=fact(f"text:{index}", source), adapter=fact("ocr", source),
            box=fact(row["box"], source), box_role=fact("text_anchor", source),
            text=fact(row["text"], source, confidence=row["score"]), visible=fact(True, source)))
    for name, match in observation.get("matches", {}).items():
        if not match.get("hit") or not match.get("box"):
            continue
        source = {"kind": "recognition", "pointer": f"/matches/{name}"}
        allowed = state in spec.get("target_states", {}).get(name, [])
        role = "text_anchor" if match.get("text") is not None else "template_extent"
        add(node(f"visual:{name}", "control" if allowed else "item", parent,
            semantic_id=fact(name, source), adapter=fact("vision", source),
            box=fact(match["box"], source), box_role=fact(role, source),
            text=fact(match.get("text"), source, confidence=match.get("score") if role == "text_anchor" else None),
            match_score=fact(match.get("score"), source),
            visible=fact(True, source)))
    for name, point in spec.get("points", {}).items():
        if point["state"] != state:
            continue
        source = {"kind": "profile", "source": "vision.json", "pointer": f"/points/{name}",
                  "rule": "calibrated_point_in_recognized_state"}
        add(node(f"visual:{name}", "control", parent,
            semantic_id=fact(name, source), adapter=fact("vision", source),
            box=fact([*point["xy"], 1, 1], source), box_role=fact("calibrated_point", source)))


def stage_nodes(observation, parent, add):
    info = observation.get("stage")
    if not info:
        return
    state = observation.get("state")
    requested = info["requested_id"]
    actual = requested if info.get("identity_verified") or (info.get("context_verified") and info.get("row_box")) else None
    fields = {key: fact(value, derived(f"/stage/{key}", "existing_stage_inspector"))
              for key, value in info.items() if key != "ocr"}
    item = add(node(f"stage:{requested}", "item", parent,
        semantic_id=fact(actual, derived("/stage", "identity_or_exact_row_in_verified_chapter")),
        adapter=fact("stage", derived("/stage", "existing_stage_inspector")),
        anchor_box=fact(info.get("row_box"), derived("/stage/row_box", "observed_stage_label")),
        **fields))
    def control(name, box, pointer, role="text_anchor", kind="derived"):
        if box is None:
            return
        source = {"kind": kind, "pointer": pointer, "rule": "existing_calibrated_stage_target"}
        add(node(f"{item}/{name}", "control", item,
            semantic_id=fact(name, source), adapter=fact("stage", source),
            box=fact(box, source), box_role=fact(role, source)))
    control("stage_row", info.get("row_box"), "/stage/row_box")
    control("stage_select_team", info.get("select_team_box"), "/stage/select_team_box")
    ready = observation.get("matches", {}).get("map_ready_label", {})
    if state == "episode_map" and ready.get("hit"):
        control("stage_ready", ready.get("box"), "/matches/map_ready_label", "template_extent")
    if state == "battle_ready":
        for name in ("start_quest_label", "start_regular_label"):
            match = observation.get("matches", {}).get(name, {})
            if match.get("hit"):
                control("stage_start", match.get("box"), f"/matches/{name}", "template_extent")
                break
    if state == "episode_map" and info.get("context_verified") and not info.get("row_box") and info.get("visible_ordinals"):
        control("scroll_top", [250, 180, 1, 1], "/stage/visible_ordinals", "calibrated_point", "profile")
        control("scroll_down", [250, 500, 1, 1], "/stage/visible_ordinals", "calibrated_point", "profile")
