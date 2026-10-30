"""Version 1 of a partial, read-only UI tree derived from one observation.

This module adapts existing recognition results. It does not recognize pixels,
schedule pipelines, retain nodes across frames, or dispatch input.
"""

from copy import deepcopy
import json
import math
from uuid import NAMESPACE_URL, uuid5


SCHEMA_VERSION = 1


def fact(value=None, *sources, confidence=None):
    """None is unknown, not false. Confidence is never invented for a rule."""
    if value is None:
        return {"value": None, "confidence": None, "sources": []}
    return {"value": deepcopy(value), "confidence": confidence, "sources": deepcopy(list(sources))}


def derived(pointer, rule):
    return {"kind": "derived", "pointer": pointer, "rule": rule}


def catalog_ref(kind, identity):
    return {"kind": "catalog", "source": "data/catalogs/quests.json",
            "collection": kind, "identity": identity}


def node(identity, kind, parent=None, layout_reference=None, **fields):
    defaults = {key: fact() for key in ("semantic_id", "box", "text", "value", "visible", "enabled", "status")}
    return {"id": identity, "kind": kind, "parent_id": parent, "children": [],
            "fields": {**defaults, **fields}, "layout_reference": layout_reference}


def _ocr(observation, box):
    candidates = [(i, row) for i, row in enumerate(observation.get("text", [])) if box and row["box"] == box]
    if len(candidates) != 1:
        return fact(), []
    index, row = candidates[0]
    source = {"kind": "ocr", "pointer": f"/text/{index}", "engine": "Maa/en_us"}
    return fact(row["text"], source, confidence=row["score"]), [source]


def _layout(file, path=None):
    return {"source": file, "path": path, "scope": "static_hint"}


def build_tree(observation, vision_spec=None):
    """Adapt the existing recognizers to the shared observation contract."""
    observation = dict(observation)
    observation.setdefault("state", "unknown")
    recognition_only = "epoch_seconds" not in observation
    observation.setdefault("epoch_seconds", None)
    observation.setdefault("window", {"client_size": (vision_spec or {}).get("reference_size", [1212, 682])})
    width, height = observation["window"]["client_size"]
    identity = json.dumps([observation["window"], observation["epoch_seconds"], observation.get("frame")], sort_keys=True)
    tree = {"schema_version": SCHEMA_VERSION,
            "observation_id": observation.get("observation_id") or str(uuid5(NAMESPACE_URL, identity)),
            "observed_at_epoch_seconds": observation.get("captured_at_epoch_seconds", observation["epoch_seconds"]),
            "context": {"window": deepcopy(observation["window"]), "frame": observation.get("frame"),
                        "observation_file": observation.get("observation_file"),
                        "coordinate_space": "client_pixels", "client_size": [width, height],
                        "scope": "recognition_only" if recognition_only else "captured_observation",
                        "methods": deepcopy(observation.get("methods"))},
            "coverage": "partial_observation", "root_id": "screen", "nodes": {}}

    def add(item):
        if item["id"] in tree["nodes"]:
            raise ValueError("Identidade duplicada na árvore observada: " + item["id"])
        tree["nodes"][item["id"]] = item
        if item["parent_id"] is not None:
            tree["nodes"][item["parent_id"]]["children"].append(item["id"])
        return item["id"]

    navigation = observation.get("navigation", {})
    add(node("screen", "screen",
        semantic_id=fact("epic_seven_window", {"kind": "window", "pointer": "/window"}),
        box=fact([0, 0, width, height], {"kind": "capture", "pointer": "/window/client_size"}),
        box_role=fact("client_frame", {"kind": "capture", "pointer": "/frame"}),
        visible=fact(True, {"kind": "capture", "pointer": "/frame"}),
        status=fact(observation["state"] if observation.get("state") != "unknown" else None,
                    derived("/state", "existing_visual_classifier")),
        navigation_kind=fact(navigation.get("kind") if navigation.get("kind") != "unknown" else None,
                            derived("/navigation/kind", "navigation_depth_not_battle_identity")),
        battle_identity_verified=fact(navigation.get("battle_identity_verified"),
                                      derived("/navigation/battle_identity_verified", "existing_stage_inspector")),
        **{f"navigation_{key}": fact(value, derived(f"/navigation/{key}", "existing_navigation_classifier"))
           for key, value in navigation.items() if key not in ("kind", "battle_identity_verified")}
    ))
    parent = "screen"
    state = observation.get("state", "unknown")
    if state != "unknown":
        parent = add(node("panel:orbis" if state == "orbis_guide" else f"panel:{state}", "panel", "screen",
            semantic_id=fact(state, derived("/state", "existing_visual_classifier")),
            visible=fact(True, derived("/state", "existing_visual_classifier")),
            layout_reference=_layout("wnd/growth_masterbook.csb") if state == "orbis_guide" else None))
    from .ui_adapters import visual_nodes, stage_nodes, campaign_objective_nodes
    from .session import session_nodes
    visual_nodes(observation, vision_spec or {}, parent, add)
    stage_nodes(observation, parent, add)
    session_nodes(observation, parent, add)
    from .operational_ui import operational_nodes, auto_nodes, formation_nodes
    operational_nodes(observation, parent, add)
    if not any(n['kind']=='panel' and field_value(n,'view')=='prequel_preparation'
               for n in tree['nodes'].values()):
        campaign_objective_nodes(observation, parent, add)
    auto_nodes(observation, parent, add)
    formation_nodes(observation, parent, add)
    report = observation.get("quest", {})
    if observation.get("state") != "orbis_guide":
        validate_tree(tree)
        return tree

    panel = parent
    tabs = [(i, r) for i, r in enumerate(observation.get("text", []))
            if r["score"] >= .90 and r["text"].strip() == "Path of Heir"
            and 100 <= r["box"][0] and 180 <= r["box"][1]
            and r["box"][0]+r["box"][2] <= 245 and r["box"][1]+r["box"][3] <= 240]
    if len(tabs) == 1 and not any(
            n['kind']=='control' and field_value(n,'semantic_id')=='orbis_heir_tab'
            for n in tree['nodes'].values()):
        index, row = tabs[0]
        source = {"kind": "ocr", "pointer": f"/text/{index}", "rule": "calibrated_orbis_heir_tab"}
        add(node("visual:orbis_heir_tab", "control", panel,
            semantic_id=fact("orbis_heir_tab", source), adapter=fact("vision", source),
            box=fact(row["box"], source), box_role=fact("text_anchor", source),
            text=fact(row["text"], source, confidence=row["score"]), visible=fact(True, source)))
    group_id = report.get("group_id")
    if group_id is None:
        validate_tree(tree)
        return tree

    title, title_sources = _ocr(observation, report.get("group_title_box"))
    identity_sources = [derived("/quest/group_id", "unique_exact_group_title"), catalog_ref("groups", group_id), *title_sources]
    group_status = "claimed" if report.get("group_claimed") else "claim_ready" if report.get("group_claim_ready") else None
    count = report.get("group_counter")
    if group_status is None and count and count["current"] < count["total"]:
        group_status = "incomplete"
    group_node = add(node(f"group:{group_id}", "group", panel,
        semantic_id=fact(group_id, *identity_sources), text=title,
        visible=fact(True, *identity_sources),
        value=fact(deepcopy(count), derived("/quest/group_counter", "parsed_group_counter")),
        status=fact(group_status, derived("/quest", "group_counter_and_reward_control")),
        group_name=fact(report.get("group_name"), *identity_sources),
        path=fact(report.get("path"), derived("/quest/path", "identified_group_catalog")),
        complete_group_inventory=fact(report.get("complete_group_inventory"), derived("/quest/complete_group_inventory", "observed_rows_vs_group_catalog")),
        anchor_box=fact(report.get("group_title_box"), *title_sources)))

    if report.get("path") == "heir":
        for name, box in (("previous_group", [337, 56, 42, 44]), ("next_group", [1063, 56, 43, 43])):
            source = {"kind": "profile", "pointer": "/quest/group_id", "rule": "calibrated_adjacent_heir_group_navigation"}
            add(node(f"{group_node}/{name}", "control", group_node,
                semantic_id=fact(name, source), box=fact(box, source), box_role=fact("calibrated_point", source)))

    # A visible Receive does not establish that the control is enabled.
    if report.get("group_receive_box"):
        text, sources = _ocr(observation, report["group_receive_box"])
        add(node(f"{group_node}/claim_group", "control", group_node,
            semantic_id=fact("claim_group", derived("/quest/group_receive_box", "group_reward_control")),
            box=fact(report["group_receive_box"], *sources,
                     derived("/quest/group_receive_box", "observed_label_box")),
            box_role=fact("text_anchor", *sources), text=text,
            visible=fact(True, derived("/quest/group_receive_box", "observed_label_box")),
            status=fact(group_status, derived("/quest", "group_counter_and_reward_control"))))

    for index, task in enumerate(report.get("visible_tasks", [])):
        pointer = f"/quest/visible_tasks/{index}"
        title, sources = _ocr(observation, task["label_box"])
        task_status = task["status"] if task["status"] != "unknown" else None
        mission = add(node(f"{group_node}/mission:{task['task_id']}", "mission", group_node,
            semantic_id=fact(task["task_id"], derived(pointer+"/task_id", task.get('title_match_rule','unique_exact_title_within_identified_group')),
                             catalog_ref("tasks", task["task_id"]), *sources),
            text=title, anchor_box=fact(task["label_box"], *sources),
            visible=fact(True, derived(pointer+"/label_box", "observed_mission_title")),
            fully_visible=fact(task["row_fully_visible"], derived(pointer+"/row_fully_visible", "measured_row_bounds")),
            value=fact(deepcopy(task["counter"]), derived(pointer+"/counter", "parsed_counter_checked_against_catalog")),
            condition_satisfied=fact(task["condition_satisfied"], derived(pointer+"/condition_satisfied", "parsed_counter_comparison")),
            status=fact(task_status, derived(pointer+"/status", "counter_control_or_claim_receipt")),
            catalog_label=fact(task["label"], catalog_ref("tasks", task["task_id"])),
            family=fact(task["family"], derived(pointer+"/family", "operation_map_catalog")),
            demo_excluded=fact(task["demo_excluded"], catalog_ref("tasks", task["task_id"])),
            expected_counter_total=fact(task.get("expected_counter_total"), catalog_ref("tasks", task["task_id"])),
            layout_reference=_layout("wnd/growth_masterbook_quest_item.csb")))
        control = {"go": "go", "receive": "claim", "received": "receipt", "completed": "receipt"}.get(task.get("control"))
        if control and task.get("control_box"):
            text, sources = _ocr(observation, task["control_box"])
            add(node(f"{mission}/{control}", "control", mission,
                semantic_id=fact(control, derived(pointer+"/control", "observed_mission_control")),
                box=fact(task["control_box"], *sources, derived(pointer+"/control_box", "observed_label_box")),
                box_role=fact("text_anchor", *sources), text=text,
                visible=fact(True, derived(pointer+"/control_box", "observed_label_box")),
                status=fact(task_status, derived(pointer+"/status", "mission_status_not_enabled_state")),
                layout_reference=_layout("wnd/growth_masterbook_quest_item.csb",
                    "/Layer/btn_go" if control == "go" else "/Layer/btn_reward" if control == "claim" else None)))
        if task.get("claimed_tick_box") and task_status == "claimed" and control != "receipt":
            add(node(f"{mission}/receipt", "control", mission,
                semantic_id=fact("receipt", derived(pointer+"/claimed_tick_box", "existing_claimed_tick_match")),
                box=fact(task["claimed_tick_box"], {"kind": "template", "pointer": pointer+"/claimed_tick_box",
                                                 "source": "quest_claimed_tick.png"}),
                box_role=fact("template_extent", derived(pointer+"/claimed_tick_box", "existing_claimed_tick_match")),
                visible=fact(True, derived(pointer+"/claimed_tick_box", "existing_claimed_tick_match")),
                status=fact("claimed", derived(pointer+"/status", "existing_claimed_tick_match"))))
    validate_tree(tree)
    return tree


def validate_tree(tree):
    """Validate snapshot relationships and coordinate/evidence conventions."""
    if tree.get("schema_version") != SCHEMA_VERSION or not tree.get("observation_id"):
        raise ValueError("Contrato de árvore observada inválido ou não suportado.")
    stamp = tree.get("observed_at_epoch_seconds")
    if stamp is None and tree["context"].get("scope") == "recognition_only":
        pass
    elif not isinstance(stamp, (int, float)) or not math.isfinite(stamp):
        raise ValueError("Árvore precisa do instante da observação.")
    if tree["context"].get("coordinate_space") != "client_pixels":
        raise ValueError("Coordenadas precisam estar na área cliente observada.")
    width, height = tree["context"]["client_size"]
    nodes = tree["nodes"]
    root = tree["root_id"]
    if root not in nodes or nodes[root]["parent_id"] is not None:
        raise ValueError("Raiz inválida na árvore observada.")
    visited = set()
    def visit(identity):
        if identity in visited:
            raise ValueError("Ciclo ou filho duplicado na árvore observada.")
        visited.add(identity)
        item = nodes[identity]
        if item["id"] != identity:
            raise ValueError("Identidade de nó inconsistente.")
        if item["kind"] not in ("screen", "panel", "group", "mission", "item", "control"):
            raise ValueError("Tipo de nó fora do contrato inicial.")
        if any(key not in item["fields"] for key in ("semantic_id", "box", "text", "value", "visible", "enabled", "status")):
            raise ValueError("Campos obrigatórios ausentes no nó observado.")
        for name, value in item["fields"].items():
            confidence = value["confidence"]
            if confidence is not None and (isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not math.isfinite(confidence) or not 0 <= confidence <= 1):
                raise ValueError("Confiança inválida no campo observado.")
            if value["value"] is not None and not value["sources"]:
                raise ValueError("Valor conhecido exige proveniência por campo.")
            if name in ("box", "anchor_box") and value["value"] is not None:
                x, y, w, h = value["value"]
                if not all(isinstance(n, (int, float)) and math.isfinite(n) for n in (x, y, w, h)) or min(x, y) < 0 or min(w, h) <= 0 or x+w > width or y+h > height:
                    raise ValueError("Caixa fora da captura observada.")
        for child in item["children"]:
            if child not in nodes or nodes[child]["parent_id"] != identity:
                raise ValueError("Relação pai/filho inconsistente.")
            visit(child)
    visit(root)
    if visited != set(nodes):
        raise ValueError("Nó desconectado da árvore observada.")


def query_control(tree, group_id, task_id, control):
    """Resolve one control by ancestry; never return an executable handle."""
    validate_tree(tree)
    def child(parent, kind, semantic):
        matches = [tree["nodes"][identity] for identity in parent["children"]
                   if tree["nodes"][identity]["kind"] == kind
                   and tree["nodes"][identity]["fields"]["semantic_id"]["value"] == semantic]
        if len(matches) != 1:
            raise ValueError("Elemento não identificado sem ambiguidade nesta observação: " + semantic)
        return matches[0]
    screen = tree["nodes"][tree["root_id"]]
    panel = child(screen, "panel", "orbis_guide")
    group = child(panel, "group", group_id)
    parent = child(group, "mission", task_id) if task_id is not None else group
    result = child(parent, "control", control)
    return {"schema_version": SCHEMA_VERSION, "read_only": True,
            "observation_id": tree["observation_id"], "observed_at_epoch_seconds": tree["observed_at_epoch_seconds"],
            "context": deepcopy(tree["context"]), "node": deepcopy(result),
            "group_id": group_id, "task_id": task_id,
            "requires_current_action_guards": True}


def tree_for(observation, vision_spec=None):
    """Legacy observations are adapted at the boundary, never in new consumers."""
    return observation.get("ui_tree") or build_tree(observation, vision_spec)


def field_value(item, name):
    return item["fields"].get(name, {}).get("value")


def preparation_blocked(observation):
    """The current formation surface takes precedence over its preparation."""
    tree = tree_for(observation)
    return any(n['kind'] == 'panel' and field_value(n, 'adapter') == 'formation'
           and field_value(n,'blocks_preparation') is not False
           for n in tree['nodes'].values())


def operation_view(observation):
    """Disposable projection of a uniquely identified operational panel."""
    tree = tree_for(observation)
    if preparation_blocked({'ui_tree':tree}):
        return {}
    panels = [n for n in tree['nodes'].values() if n['kind'] == 'panel'
              and field_value(n, 'adapter') == 'operations']
    if len(panels) != 1:
        return {}
    panel = panels[0]
    result = {k: v['value'] for k, v in panel['fields'].items()
              if k in ('view', 'mode')}
    result['items'] = [{k: v['value'] for k, v in tree['nodes'][i]['fields'].items()}
                       for i in panel['children'] if tree['nodes'][i]['kind'] == 'item']
    result['controls'] = [{k: v['value'] for k, v in tree['nodes'][i]['fields'].items()}
                          for i in panel['children'] if tree['nodes'][i]['kind'] == 'control']
    return result


def formation_view(observation):
    tree=tree_for(observation)
    panels=[n for n in tree['nodes'].values() if n['kind']=='panel' and field_value(n,'adapter')=='formation']
    if len(panels)!=1:return {}
    p=panels[0]
    result={k:v['value'] for k,v in p['fields'].items() if k in ('view','selected_position')}
    for kind,key in (('item','items'),('control','controls')):
        result[key]=[{k:v['value'] for k,v in tree['nodes'][i]['fields'].items()} for i in p['children'] if tree['nodes'][i]['kind']==kind]
    return result


def query_operation_control(tree, view, control, *, observation_id=None):
    validate_tree(tree)
    if observation_id is not None and observation_id != tree['observation_id']:
        raise ValueError('Controle pertence a outra observação; resolver na árvore atual.')
    panels = [n for n in tree['nodes'].values() if n['kind'] == 'panel'
              and ((field_value(n, 'adapter') in ('operations', 'formation') and field_value(n, 'view') == view)
                   or (n['id'] == 'panel:orbis' and view == 'orbis_guide'))]
    if len(panels) != 1:
        raise ValueError('Painel operacional não identificado sem ambiguidade.')
    found = [tree['nodes'][i] for i in panels[0]['children'] if tree['nodes'][i]['kind'] == 'control'
             and field_value(tree['nodes'][i], 'semantic_id') == control]
    if len(found) != 1:
        raise ValueError('Controle não identificado nesse painel: '+control)
    blockers = ['current_action_guards_required']
    if field_value(found[0], 'visible') is not True:
        blockers.append('visibility_unproven')
    if field_value(found[0], 'enabled') is not True:
        blockers.append('enabled_unknown' if field_value(found[0], 'enabled') is None else 'disabled')
    if not field_value(found[0], 'box'):
        blockers.append('active_region_unknown')
    if field_value(found[0], 'box_role') == 'text_anchor':
        blockers.append('text_anchor_requires_calibrated_operation')
    return {'read_only': True, 'requires_current_action_guards': True,
            'observed': True, 'actionability': {'eligible': None, 'blockers': blockers},
            'observation_id': tree['observation_id'], 'context': deepcopy(tree['context']),
            'observed_at_epoch_seconds': tree['observed_at_epoch_seconds'], 'node': deepcopy(found[0])}


def auto_state(observation):
    tree = tree_for(observation)
    item = tree['nodes'].get('battle:auto')
    return field_value(item, 'value') if item else None


def screen_state(observation):
    tree = tree_for(observation)
    return field_value(tree["nodes"][tree["root_id"]], "status") or "unknown"


def target_box(tree, name, adapter="vision", allow_anchor=False):
    matches = [item for item in tree["nodes"].values()
               if (item["kind"] == "control" or allow_anchor)
               and field_value(item, "semantic_id") == name and field_value(item, "adapter") == adapter]
    return field_value(matches[0], "box") if len(matches) == 1 else None


def stage_view(observation):
    """Guard-friendly projection of the stage node, not a second state store."""
    tree = tree_for(observation)
    matches = [n for n in tree["nodes"].values() if n["kind"] == "item" and field_value(n, "adapter") == "stage"]
    if len(matches) != 1:
        return {}
    return {key: value["value"] for key, value in matches[0]["fields"].items()
            if key not in ("semantic_id", "box", "text", "value", "visible", "enabled", "status", "adapter", "anchor_box")}


def navigation_view(observation):
    tree = tree_for(observation)
    root = tree["nodes"][tree["root_id"]]
    output = {key.removeprefix("navigation_"): value["value"] for key, value in root["fields"].items() if key.startswith("navigation_")}
    output["kind"] = output.get("kind") or "unknown"
    output["battle_identity_verified"] = field_value(root, "battle_identity_verified")
    return output


def text_rows(observation):
    tree = tree_for(observation)
    return [{"text": field_value(n, "text"), "box": field_value(n, "box"),
             "score": n["fields"]["text"]["confidence"]}
            for n in tree["nodes"].values() if field_value(n, "adapter") == "ocr"]


def quest_view(observation):
    tree = tree_for(observation)
    report = {"group_id": None, "group_name": None, "group_title_box": None, "group_counter": None,
              "group_claim_ready": False, "group_claimed": False, "group_receive_box": None,
              "group_claim_control_ready": None,
              "visible_tasks": [], "complete_group_inventory": False, "reason": "panel_not_identified"}
    groups = [n for n in tree["nodes"].values() if n["kind"] == "group"]
    if len(groups) != 1:
        return report
    group = groups[0]
    report.update(group_id=field_value(group, "semantic_id"), group_name=field_value(group, "group_name"),
                  group_title_box=field_value(group, "anchor_box"), group_counter=field_value(group, "value"),
                  group_claim_ready=field_value(group, "status") == "claim_ready",
                  group_claim_control_ready=field_value(group, "claim_ready"),
                  group_claimed=field_value(group, "status") == "claimed", path=field_value(group, "path"),
                  complete_group_inventory=field_value(group, "complete_group_inventory"), reason=None)
    for identity in group["children"]:
        item = tree["nodes"][identity]
        if item["kind"] == "control" and field_value(item, "semantic_id") == "claim_group":
            report["group_receive_box"] = field_value(item, "box")
        if item["kind"] != "mission":
            continue
        row = {"task_id": field_value(item, "semantic_id"), "label": field_value(item, "catalog_label"),
               "family": field_value(item, "family"), "counter": field_value(item, "value"),
               "expected_counter_total": field_value(item, "expected_counter_total"),
               "condition_satisfied": field_value(item, "condition_satisfied"),
               "claim_ready": field_value(item, "claim_ready"), "claim_control_box": None,
               "status": field_value(item, "status") or "unknown", "control": None, "control_box": None,
               "label_box": field_value(item, "anchor_box"), "row_fully_visible": field_value(item, "fully_visible"),
               "claimed_tick_box": None, "demo_excluded": field_value(item, "demo_excluded")}
        for child in item["children"]:
            control = tree["nodes"][child]
            role = field_value(control, "semantic_id")
            if role in ("go", "claim"):
                row.update(control="go" if role == "go" else "receive", control_box=field_value(control, "box"))
                if role == "claim":
                    row["claim_control_box"] = field_value(control, "box") if field_value(control, "claim_ready") is True else None
            elif role == "receipt":
                row["claimed_tick_box"] = field_value(control, "box")
        report["visible_tasks"].append(row)
    return report
