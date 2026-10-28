"""Notification switch evidence and guards, without changing live settings."""

import numpy as np
from PIL import Image
import pytest

from driver_epic_seven.config import ROOT, load_config
from driver_epic_seven.session import CheckboxReader, inspect_session, session_target
from driver_epic_seven.observed_ui import build_tree
from driver_epic_seven.vision import Vision
from types import SimpleNamespace
import json


@pytest.mark.fixtures
def test_notification_switch_styles_and_unknowns_use_real_maa(tmp_path):
    source = ROOT / "tests/fixtures/local/notifications_public_off.png"
    if not source.exists():
        pytest.skip("Captura privada de notificações não está instalada.")
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition, JTemplateMatch
    from maa.define import LoggingLevelEnum
    from maa.library import Library

    config = load_config()
    reader = CheckboxReader(config["resource_dir"])
    reports = []

    class NotificationRecognition(CustomRecognition):
        def analyze(self, context, argv):
            report = inspect_session({"state": "chat_notifications", "text": [
                {"text": "Guild Advertisement Alert", "box": [930, 345, 200, 25], "score": .99}]},
                lambda roi: reader.read(argv.image, roi,
                    lambda names, area: context.run_recognition_direct("TemplateMatch",
                        JTemplateMatch(template=names, roi=area, threshold=[.85] * len(names)), argv.image)))
            reports.append(report)
            return self.AnalyzeResult(box=[0, 0, 1, 1], detail=report)

    Tasker.set_stdout_level(LoggingLevelEnum.Off)
    Tasker.set_log_dir(tmp_path / "maa")
    resource = Resource()
    resource.set_cpu()
    resource.register_custom_recognition("NotificationFixture", NotificationRecognition())
    assert resource.post_bundle(config["resource_dir"]).wait().succeeded
    tasker = Tasker()
    assert Library.framework().MaaTaskerBindResource(tasker._handle, resource._handle)
    frame = np.asarray(Image.open(source).convert("RGB"))[:, :, ::-1].copy()

    def read(image):
        assert tasker.post_recognition("Custom", JCustomRecognition(
            custom_recognition="NotificationFixture"), image).wait().succeeded
        return reports[-1]

    off = read(frame)
    assert [item["checked"] for item in off["checkboxes"]] == [False] * 5
    assert off["all_off_verified"]
    assert "notifications_all_on" not in off["controls"]
    assert "notification_item_on" not in off["controls"]
    on = reader.templates["on"][0]
    height, width = on.shape[:2]
    for index, y in enumerate((181, 244, 294, 344, 395)):
        checked = frame.copy()
        checked[y:y+height, 888:888+width] = on
        report = read(checked)
        assert report["checkboxes"][index]["checked"] is True
        assert not report["all_off_verified"]
        assert ("notifications_all_on" if index == 0 else "notification_item_on") in report["controls"]
    obscured = frame.copy()
    obscured[239:279, 883:923] = 0
    unknown = read(obscured)
    assert unknown["checkboxes"][1]["checked"] is None
    assert not unknown["all_off_verified"]
    assert "notification_item_on" not in unknown["controls"]
    dimmed = read((frame * .45).astype(np.uint8))
    assert all(item["checked"] is None for item in dimmed["checkboxes"])
    assert not dimmed["all_off_verified"]


def test_category_and_five_off_boxes_are_required_for_completion():
    report = {"category": "public", "all_off_verified": False,
              "notice_box": None, "checkboxes": [{"checked": False}] * 4 + [{"checked": None}], "controls": {}}
    observation = {"state": "chat_notifications", "epoch_seconds": 1000,
                   "window": {"client_size": [1212, 682]}, "session": report}
    tree = build_tree(observation)
    assert session_target(tree, {"state": "chat_notifications", "target": "public_off_verified"}) is None
    report["all_off_verified"] = True
    tree = build_tree(observation)
    assert session_target(tree, {"state": "chat_notifications", "target": "public_off_verified"}) == [0, 0, 1, 1]
    assert session_target(tree, {"state": "chat_notifications", "target": "guild_off_verified"}) is None
    assert session_target(tree, {"state": "chat_notifications", "target": "notification_item_on", "category": "guild"}) is None
    report["controls"]["notifications_guild"] = {"box": [988, 141, 7, 7], "box_role": "calibrated_point"}
    tree = build_tree(observation)
    assert session_target(tree, {"state": "chat_notifications", "target": "notifications_guild", "category": "public"}) == [988, 141, 7, 7]
    report["category"] = "guild"
    tree = build_tree(observation)
    assert session_target(tree, {"state": "chat_notifications", "target": "notifications_guild", "category": "public"}) is None


@pytest.mark.parametrize("question,button,score,expected", [
    ("These notices will no longer be displayed.", "Confirm", .99, "notice_disable_confirmation"),
    ("Spend 1000 gold?", "Confirm", .99, "unknown"),
    ("These notices will no longer be displayed.", "Cancel", .99, "unknown"),
    ("These notices will no longer be displayed.", "Confirm", .7, "unknown"),
])
def test_notice_confirmation_requires_specific_question_and_button(tmp_path, question, button, score, expected):
    config = load_config()
    full = json.loads(config["vision_file"].read_text(encoding="utf-8"))
    spec = {"templates": {}, "ocr": {key: full["ocr"][key]
            for key in ("notice_disable_question", "notice_disable_confirm")},
            "states": {"notice_disable_confirmation": full["states"]["notice_disable_confirmation"]}}
    file = tmp_path / "vision.json"
    file.write_text(json.dumps(spec), encoding="utf-8")
    vision = Vision(file, tmp_path)
    def recognize(name):
        text, box = (question, [305, 280, 570, 45]) if name.endswith("Question") else (button, [670, 420, 130, 30])
        return SimpleNamespace(filtered_results=[SimpleNamespace(text=text, box=box, score=score)])
    analysis = vision.inspect(None, recognize)
    assert analysis["state"] == expected
    report = inspect_session(analysis, lambda roi: pytest.fail("No checkbox read in a notice dialog"))
    observation = {**analysis, "session": report, "epoch_seconds": 1000,
                   "window": {"client_size": [1212, 682]}}
    target = session_target(build_tree(observation), {"state": "notice_disable_confirmation", "target": "notice_disable_confirm"})
    assert (target is not None) == (expected == "notice_disable_confirmation")


def test_unknown_banner_never_becomes_a_dismiss_target():
    text = {"text": "Unrecognized offer. Confirm?", "box": [400, 120, 300, 30], "score": .99}
    report = inspect_session({"state": "lobby", "text": [text]}, lambda roi: pytest.fail("No checkbox read in lobby"))
    assert report["notice_box"] is None and "demo_notice" not in report["controls"]
    text["text"] = "We look forward to seeing Players again at the official launch on October 29!"
    report = inspect_session({"state": "lobby", "text": [text]}, lambda roi: None)
    assert report["notice_box"] == text["box"]
