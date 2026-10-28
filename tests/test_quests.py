from copy import deepcopy
import json

import pytest

from driver_epic_seven.config import ROOT, load_config
from driver_epic_seven.quests import (
    QuestCatalog, action_target, compare_snapshots, has_text, navigation_context,
)


@pytest.fixture
def catalog():
    c = load_config()
    return QuestCatalog(c["quest_file"], c["operation_map_file"])


def text(value, box, score=.99):
    return {"text": value, "box": box, "score": score}


def panel():
    return {"state": "orbis_guide", "window": {"client_size": [1212, 682]}, "text": [
        text("Path of Heir 16", [635, 65, 166, 25]),
        text("0/5", [427, 169, 54, 34]),
        text("Receive", [1021, 214, 63, 21]),
        text("Own two Level 60 Heroes", [303, 303, 185, 19]),
        text("Receive", [1021, 330, 62, 22]), text("2/2", [503, 378, 27, 14]),
        text("Enhance Equipment 5 times", [303, 426, 200, 19]),
        text("Receive", [1021, 453, 62, 23]), text("5/5", [502, 501, 29, 15]),
        text("Enhance Equipment 3 times", [303, 549, 200, 20]),
        text("Receive", [1022, 579, 61, 19]),
    ]}


def test_individual_ready_does_not_unlock_group_or_clipped_row(catalog):
    report = catalog.inspect(panel())
    assert action_target(catalog, report, "claim", "guide_16_002_001") == [1021, 453, 62, 23]
    assert not report["group_claim_ready"]
    with pytest.raises(ValueError, match="pronto"):
        action_target(catalog, report, "claim-group", "group_guide_16")
    with pytest.raises(ValueError, match="totalmente visível"):
        action_target(catalog, report, "claim", "guide_16_003_001")


def test_group_identity_and_counter_are_required_before_input(catalog):
    report = catalog.inspect(panel())
    with pytest.raises(ValueError, match="outro grupo"):
        action_target(catalog, report, "claim", "guide_15_001_001")
    observation = panel()
    observation["text"][1]["score"] = .60
    with pytest.raises(ValueError, match="Progresso do grupo"):
        action_target(catalog, catalog.inspect(observation), "claim", "guide_16_002_001")


@pytest.mark.parametrize("change", ["wrong_total", "low_score", "wrong_label", "overlay"])
def test_ambiguous_or_inconsistent_evidence_never_authorizes_claim(catalog, change):
    observation = panel()
    if change == "wrong_total":
        observation["text"][8]["text"] = "5/6"
    elif change == "low_score":
        observation["text"][6]["score"] = .65
    elif change == "wrong_label":
        observation["text"][6]["text"] = "Enhance Equipment 15 times"
    else:
        observation["state"] = "tap_to_close_notice"
    with pytest.raises(ValueError):
        action_target(catalog, catalog.inspect(observation), "claim", "guide_16_002_001")


def test_duplicate_catalog_label_is_not_bound_by_sort_order(catalog):
    copy = deepcopy(catalog.tasks["guide_16_002_001"])
    copy["id"] = "test_duplicate"
    catalog.tasks[copy["id"]] = copy
    assert not any(t["task_id"] == "guide_16_002_001" for t in catalog.inspect(panel())["visible_tasks"])


def test_claimed_checkmark_is_distinct_from_counter_completion(catalog):
    observation = panel()
    observation["text"] = [r for r in observation["text"] if r["box"] != [1021, 453, 62, 23]]
    report = catalog.inspect(observation, lambda roi: [1038, 454, 30, 23] if roi[1] == 442 else None)
    row = next(t for t in report["visible_tasks"] if t["task_id"] == "guide_16_002_001")
    assert row["status"] == "claimed"
    with pytest.raises(ValueError, match="estado observado"):
        action_target(catalog, report, "claim", row["task_id"])


def test_wrapped_mode_title_does_not_establish_battle_or_cost():
    rows = [text("Battle", [60, 20, 70, 26]), text("Remnant of", [36, 111, 171, 30]),
            text("Supremacy", [35, 145, 165, 39]), text("Difficulty", [876, 175, 80, 25]),
            text("Normal", [1004, 265, 71, 22]), text("Hard", [997, 401, 48, 22])]
    assert has_text(rows, "Remnant of Supremacy")
    assert not has_text(rows, "Remnant of Supremacy II")
    result = navigation_context({"state": "unknown", "text": rows})
    assert result["kind"] == "mode_menu"
    assert result["battle_identity_verified"] is False and result["cost_verified"] is False
    assert result["stage_id"] is None
    assert navigation_context({"state": "battle_ready"})["battle_identity_verified"] is False


def test_preparation_cost_needs_catalog_identity_and_matching_cost():
    observation = {"state": "battle_ready", "stage": {"identity_verified": True,
        "requested_id": "pen002", "expected_energy": 8, "energy": {"cost": 18, "available": 900}}}
    assert navigation_context(observation)["battle_identity_verified"]
    assert not navigation_context(observation)["cost_verified"]
    observation["stage"]["energy"]["cost"] = 8
    assert navigation_context(observation)["cost_verified"]


def test_compare_requires_same_group_and_does_not_call_claim_progress(catalog):
    window = {"hwnd": 1, "pid": 2, "process_name": "EpicSeven_Steam.exe", "window_title": "Epic Seven",
              "window_class": "GLFW30", "client_size": [1212, 682]}
    before = {**panel(), "window": window, "epoch_seconds": 100, "quest": catalog.inspect(panel())}
    after = deepcopy(before)
    after["epoch_seconds"] = 120
    after["quest"]["visible_tasks"][1]["status"] = "claimed"
    result = compare_snapshots(before, after, "guide_16_002_001")
    assert result["claim_verified"] and not result["progress_verified"]
    after["quest"]["group_id"] = "group_guide_15"
    with pytest.raises(ValueError, match="mesmo grupo"):
        compare_snapshots(before, after, "guide_16_002_001")


@pytest.mark.fixtures
def test_quest_ocr_and_receipts_on_saved_frames(tmp_path):
    """Replay real frames entirely offline, including dimmed/negative panels."""
    fixture_dir = ROOT / "tests/fixtures/local"
    manifest = fixture_dir / "quest_manifest.json"
    if not manifest.exists():
        pytest.skip("Capturas locais da base de missões ausentes.")
    import numpy as np
    from PIL import Image
    from maa.custom_recognition import CustomRecognition
    from maa.define import LoggingLevelEnum
    from maa.library import Library
    from maa.pipeline import JCustomRecognition, JTemplateMatch
    from maa.resource import Resource
    from maa.tasker import Tasker
    from driver_epic_seven.stages import StageInspector
    from driver_epic_seven.vision import Vision, pixel_error
    from driver_epic_seven.observed_ui import build_tree, query_control
    config = load_config()
    catalog = QuestCatalog(config["quest_file"], config["operation_map_file"])
    vision = Vision(config["vision_file"], config["resource_dir"])
    tick = np.asarray(Image.open(config["resource_dir"] / "image/quest_claimed_tick.png").convert("RGB"))[:, :, ::-1].copy()
    Tasker.set_stdout_level(LoggingLevelEnum.Off)
    Tasker.set_log_dir(tmp_path / "maa")
    found = []

    class Recognition(CustomRecognition):
        def analyze(self, context, argv):
            analysis = vision.inspect(argv.image, lambda name: context.run_recognition(name, argv.image))
            analysis["text"] = StageInspector._ocr(lambda kind, args: context.run_recognition_direct(kind, args, argv.image), [0, 0, 1212, 682])
            analysis["window"] = {"client_size": [1212, 682]}
            def match(roi):
                result = context.run_recognition_direct("TemplateMatch", JTemplateMatch(template=["quest_claimed_tick.png"], roi=roi, threshold=[.94]), argv.image)
                box = list(result.box) if result and result.hit and result.box else None
                return box if box and pixel_error(argv.image, tick, box) <= 12 else None
            analysis["quest"] = catalog.inspect(analysis, match)
            analysis["navigation"] = navigation_context(analysis)
            found.append(analysis)
            return self.AnalyzeResult(box=[0, 0, 1, 1], detail=analysis)

    resource = Resource()
    resource.set_cpu()
    resource.register_custom_recognition("QuestFixture", Recognition())
    assert resource.post_bundle(config["resource_dir"]).wait().succeeded
    tasker = Tasker()
    assert Library.framework().MaaTaskerBindResource(tasker._handle, resource._handle)
    for case in json.loads(manifest.read_text(encoding="utf-8")):
        frame = np.asarray(Image.open(fixture_dir / case["file"]).convert("RGB"))[:, :, ::-1].copy()
        job = tasker.post_recognition("Custom", JCustomRecognition(custom_recognition="QuestFixture"), frame).wait()
        assert job.succeeded
        observation = found[-1]
        assert observation["quest"]["group_id"] == case["group_id"], case
        assert observation["navigation"]["kind"] == case["navigation_kind"], case
        actual = {t["task_id"]: t["status"] for t in observation["quest"]["visible_tasks"]}
        for task, status in case.get("tasks", {}).items():
            assert actual.get(task) == status, (case, actual)
        if case["group_id"] is None:
            assert not observation["quest"]["group_claim_ready"]
        if case["navigation_kind"] == "mode_menu":
            assert not observation["navigation"]["battle_identity_verified"]
        observation.update(epoch_seconds=1000, frame=str(fixture_dir / case["file"]))
        tree = build_tree(observation)
        assert tree["coverage"] == "partial_observation"
        if case["group_id"] is None:
            assert not any(n["kind"] == "mission" for n in tree["nodes"].values())
        for task in observation["quest"]["visible_tasks"]:
            control = {"go": "go", "receive": "claim"}.get(task.get("control"))
            if control:
                resolved = query_control(tree, case["group_id"], task["task_id"], control)
                assert resolved["node"]["fields"]["box"]["value"] == task["control_box"]
                if task["row_fully_visible"] and task["status"] in ("incomplete", "claim_ready"):
                    assert action_target(catalog, observation["quest"], "go" if control == "go" else "claim", task["task_id"], tree=tree) == task["control_box"]
