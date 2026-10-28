"""Observed session preparation: notification switches and known demo notices."""

from .stages import normalize


class CheckboxReader:
    """Recognize checked/unchecked box styles; uncertainty never authorizes a click."""

    def __init__(self, resource_dir):
        import numpy as np
        from PIL import Image
        self.names = {"on": ["checkbox_on.png"],
                      "off": ["checkbox_off.png", "checkbox_off_item.png"]}
        self.templates = {
            state: [np.asarray(Image.open(resource_dir / "image" / name).convert("RGB"))[:, :, ::-1].copy()
                    for name in names] for state, names in self.names.items()}

    def read(self, frame, roi, recognize):
        from .vision import validated_template_match
        found = []
        for state, names in self.names.items():
            result = recognize(names, roi)
            matched = validated_template_match(frame, self.templates[state], result, 6)
            if matched["hit"]:
                found.append({"checked": state == "on", "box": matched["box"]})
        return found[0] if len(found) == 1 else {"checked": None, "box": None}


NOTICE_PREFIXES = (
    "Thank you for playing the Epic Seven demo",
    "We look forward to seeing Players again at the official launch on",
    "The Epic Seven demo will end on",
)


def inspect_session(analysis, checkbox_matcher):
    state = analysis["state"]
    rows = [r for r in analysis.get("text", []) if r["score"] >= .90]
    report = {"category": None, "checkboxes": [], "all_off_verified": False,
              "notice_box": None, "notice_text": None, "controls": {}}
    def control(name, box, role="calibrated_point"):
        report["controls"][name] = {"box": box, "box_role": role}
    if state == "lobby":
        control("chat_open", [1120, 28, 7, 7])
    if state == "chat_panel":
        control("chat_settings_open", [1165, 26, 7, 7])
    if state == "chat_notifications":
        control("notifications_public", [919, 141, 7, 7])
        control("notifications_guild", [988, 141, 7, 7])
        names = [normalize(r["text"]) for r in rows if r["box"][0] >= 920]
        if "guildadvertisementalert" in names:
            report["category"] = "public"
        elif "sharedreplaynotice" in names:
            report["category"] = "guild"
        if report["category"]:
            for y in (195, 258, 309, 358, 409):
                report["checkboxes"].append(checkbox_matcher([884, y-18, 39, 38]))
            states = [c["checked"] for c in report["checkboxes"]]
            report["all_off_verified"] = states == [False]*5
            if states[0] is True:
                control("notifications_all_on", report["checkboxes"][0]["box"], "template_extent")
            elif all(value is not None for value in states):
                for item in report["checkboxes"][1:]:
                    if item["checked"]:
                        control("notification_item_on", item["box"], "template_extent")
                        break
    if state in ("lobby", "episode_map", "orbis_guide", "chat_panel", "chat_notifications"):
        notices = [r for r in rows if 350 <= r["box"][0] <= 880 and 108 <= r["box"][1] <= 155
                   and any(normalize(r["text"]).startswith(normalize(prefix)) for prefix in NOTICE_PREFIXES)]
        if len(notices) == 1:
            report.update(notice_box=notices[0]["box"], notice_text=notices[0]["text"])
            control("demo_notice", notices[0]["box"], "text_anchor")
    if state == "notice_disable_confirmation":
        found = analysis["matches"].get("notice_disable_confirm", {})
        if found.get("hit"):
            control("notice_disable_confirm", found["box"], "text_anchor")
    return report


def session_target(tree, params):
    from .observed_ui import field_value, target_box, screen_state
    if screen_state({"ui_tree": tree}) != params["state"]:
        return None
    reports = [n for n in tree["nodes"].values() if field_value(n, "adapter") == "session" and n["kind"] == "item"]
    if len(reports) != 1:
        return None
    item = reports[0]
    name = params.get("target")
    category = field_value(item, "category")
    if params.get("category") is not None and category != params["category"]:
        return None
    if name == "notifications_public" and category not in ("public", "guild"):
        return None
    if name == "notifications_guild" and category != "public":
        return None
    if name in ("public_off_verified", "guild_off_verified"):
        category = "public" if name.startswith("public") else "guild"
        return [0, 0, 1, 1] if field_value(item, "category") == category and field_value(item, "all_off_verified") is True else None
    if name == "no_known_notice":
        return [0, 0, 1, 1] if field_value(item, "notice_detected") is False else None
    return target_box(tree, name, "session") if name else [0, 0, 1, 1]


def session_nodes(observation, parent, add):
    from .observed_ui import fact, derived, node
    report = observation.get("session")
    if report is None:
        return
    source = derived("/session", "observed_session_preparation")
    detected = report.get("notice_box") is not None if observation["state"] in ("lobby", "episode_map", "orbis_guide") else None
    item = add(node("session:preparation", "item", parent,
        semantic_id=fact("session_preparation", source), adapter=fact("session", source),
        category=fact(report.get("category"), source), all_off_verified=fact(report["all_off_verified"], source),
        notice_detected=fact(detected, source), checkboxes=fact(report["checkboxes"], source)))
    for name, control in report["controls"].items():
        source = derived(f"/session/controls/{name}", "calibrated_session_control")
        add(node(f"session:{name}", "control", item,
            semantic_id=fact(name, source), adapter=fact("session", source),
            box=fact(control["box"], source), box_role=fact(control["box_role"], source)))
