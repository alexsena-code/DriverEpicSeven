from copy import deepcopy
import json
from types import SimpleNamespace

import numpy as np
import pytest

from driver_epic_seven.cli import execute, parser
from driver_epic_seven.config import load_config
from driver_epic_seven.evidence import Evidence
from driver_epic_seven.observed_ui import build_tree, fact, query_control, validate_tree
from driver_epic_seven.quests import QuestCatalog, action_target
from driver_epic_seven.runtime import Runtime


@pytest.fixture
def snapshot():
    config = load_config()
    observation = {"state": "orbis_guide", "epoch_seconds": 1000.0,
        "frame": "saved-frame.png", "window": {"client_size": [1212, 682], "hwnd": 1, "pid": 2},
        "navigation": {"kind": "quest_panel", "battle_identity_verified": False},
        "text": [{"text": title, "box": box, "score": .98} for title, box in [
            ("Path of Heir 16", [635, 65, 166, 25]), ("4/5", [427, 169, 54, 34]),
            ("Receive", [1021, 214, 63, 21]),
            ("Clear Otherworld Breach 1 time", [305, 304, 225, 16]),
            ("Go", [1039, 333, 21, 18]), ("0/1", [503, 378, 27, 14]),
        ]]}
    catalog = QuestCatalog(config["quest_file"], config["operation_map_file"])
    observation["quest"] = catalog.inspect(observation)
    return observation


def test_exact_scoped_lookup_preserves_field_evidence_and_unknown_enabled(snapshot):
    tree = build_tree(snapshot)
    result = query_control(tree, "group_guide_16", "guide_16_004_001", "go")
    fields = result["node"]["fields"]
    assert fields["box"]["value"] == [1039, 333, 21, 18]
    assert fields["box_role"]["value"] == "text_anchor"
    assert fields["text"]["confidence"] == .98
    assert fields["text"]["sources"][0]["pointer"] == "/text/4"
    assert fields["status"]["value"] == "incomplete"
    assert fields["status"]["confidence"] is None
    assert fields["enabled"] == fact()
    assert result["read_only"] and result["requires_current_action_guards"]
    assert result["observation_id"] == build_tree(snapshot)["observation_id"]
    assert result["node"]["layout_reference"]["scope"] == "static_hint"
    assert tree["nodes"]["group:group_guide_16"]["fields"]["box"]["value"] is None
    assert tree["nodes"]["group:group_guide_16"]["fields"]["value"]["confidence"] is None


def test_only_observed_nodes_exist_and_catalog_presence_is_not_visibility(snapshot):
    tree = build_tree(snapshot)
    missions = [n for n in tree["nodes"].values() if n["kind"] == "mission"]
    assert len(missions) == 1
    assert not any(n["fields"]["enabled"]["value"] is not None for n in tree["nodes"].values())
    with pytest.raises(ValueError, match="não identificado"):
        query_control(tree, "group_guide_16", "guide_16_002_001", "claim")
    with pytest.raises(ValueError, match="não identificado"):
        query_control(tree, "group_guide_15", "guide_16_004_001", "go")
    group_claim = query_control(tree, "group_guide_16", None, "claim_group")
    assert group_claim["node"]["fields"]["status"]["value"] == "incomplete"
    assert group_claim["node"]["fields"]["enabled"]["value"] is None


def test_overlay_discards_underlying_quest_nodes_and_unknown_panel_is_partial(snapshot):
    snapshot["state"] = "tap_to_close_notice"
    overlay = build_tree(snapshot)
    assert not any(n["kind"] in ("group", "mission") for n in overlay["nodes"].values())
    assert overlay["nodes"]["panel:tap_to_close_notice"]["fields"]["semantic_id"]["value"] == "tap_to_close_notice"
    snapshot["state"] = "orbis_guide"
    snapshot["quest"]["group_id"] = None
    tree = build_tree(snapshot)
    assert not any(n["kind"] in ("group", "mission") for n in tree["nodes"].values())


def test_lookup_of_clipped_control_does_not_authorize_action(snapshot):
    report = snapshot["quest"]
    report["visible_tasks"][0]["row_fully_visible"] = False
    tree = build_tree(snapshot)
    assert query_control(tree, "group_guide_16", "guide_16_004_001", "go")["read_only"]
    config = load_config()
    catalog = QuestCatalog(config["quest_file"], config["operation_map_file"])
    with pytest.raises(ValueError, match="totalmente visível"):
        action_target(catalog, report, "go", "guide_16_004_001", tree=tree)


def test_current_action_resolves_tree_and_rejects_mismatched_box(snapshot):
    config = load_config()
    catalog = QuestCatalog(config["quest_file"], config["operation_map_file"])
    tree = build_tree(snapshot)
    assert action_target(catalog, snapshot["quest"], "go", "guide_16_004_001", tree=tree) == [1039, 333, 21, 18]
    result = query_control(tree, "group_guide_16", "guide_16_004_001", "go")
    tree["nodes"][result["node"]["id"]]["fields"]["box"]["value"][0] += 1
    with pytest.raises(ValueError, match="divergem"):
        action_target(catalog, snapshot["quest"], "go", "guide_16_004_001", tree=tree)


@pytest.mark.parametrize("damage", ["wrong_version", "bad_box", "parent", "cycle", "confidence", "unproven_fact"])
def test_contract_rejects_invalid_snapshots(snapshot, damage):
    tree = build_tree(snapshot)
    root = tree["nodes"]["screen"]
    if damage == "wrong_version":
        tree["schema_version"] = 999
    elif damage == "bad_box":
        root["fields"]["box"]["value"] = [-1, 0, 1212, 682]
    elif damage == "parent":
        tree["nodes"]["panel:orbis"]["parent_id"] = None
    elif damage == "cycle":
        tree["nodes"]["panel:orbis"]["children"].append("panel:orbis")
    elif damage == "confidence":
        root["fields"]["status"]["confidence"] = float("nan")
    else:
        root["fields"]["enabled"] = {"value": True, "confidence": 1, "sources": []}
    with pytest.raises(ValueError):
        validate_tree(tree)


def test_trees_and_query_results_do_not_mutate_their_sources(snapshot):
    original = deepcopy(snapshot)
    tree = build_tree(snapshot)
    result = query_control(tree, "group_guide_16", "guide_16_004_001", "go")
    result["node"]["fields"]["box"]["value"][0] = 0
    assert query_control(tree, "group_guide_16", "guide_16_004_001", "go")["node"]["fields"]["box"]["value"][0] == 1039
    tree["nodes"]["group:group_guide_16"]["fields"]["value"]["value"]["current"] = 0
    assert snapshot == original


def test_offline_query_never_initializes_the_live_runtime(snapshot, tmp_path, monkeypatch):
    file = tmp_path / "observation.json"
    file.write_text(json.dumps(snapshot), encoding="utf-8")
    def forbidden(*args, **kwargs):
        pytest.fail("Offline query attempted to initialize the live Runtime")
    monkeypatch.setattr(Runtime, "__init__", forbidden)
    args = parser().parse_args(["quest", "query", "--observation", str(file), "--group", "group_guide_16",
                               "--task", "guide_16_004_001", "--control", "go"])
    assert execute(args)["node"]["fields"]["semantic_id"]["value"] == "go"


def test_live_reader_persists_the_same_tree_it_returns_without_input(snapshot, tmp_path):
    # Exercise Runtime.observe's serialization with a fake capture/tasker;
    # no Win32 controller or window discovery is instantiated.
    runtime = object.__new__(Runtime)
    runtime.config = load_config()
    runtime.capture = lambda: np.zeros((682, 1212, 3), dtype=np.uint8)
    runtime.guard = lambda: snapshot["window"]
    runtime.bridge = SimpleNamespace(latest=deepcopy(snapshot))
    runtime.tasker = SimpleNamespace(post_recognition=lambda *args: object())
    runtime.wait = lambda job: job
    runtime.evidence = Evidence(tmp_path)
    result = runtime.observe("quest_test")
    saved = json.loads((runtime.evidence.path / "quest_test.json").read_text(encoding="utf-8"))
    assert result["ui_tree"] == saved["ui_tree"]
    assert saved["observation_id"] == saved["ui_tree"]["observation_id"]
    assert saved["ui_tree"]["context"]["observation_file"] == saved["observation_file"]


def test_generic_actions_use_tree_authority_instead_of_mutated_legacy_matches():
    from driver_epic_seven.vision import Vision
    config = load_config()
    vision = Vision(config["vision_file"], config["resource_dir"])
    observation = {"state": "lobby", "matches": {"orbis_button": {"hit": True, "box": [827, 593, 49, 66], "score": .99}}}
    observation["ui_tree"] = build_tree(observation, vision.spec)
    observation["matches"]["orbis_button"]["hit"] = False
    assert vision.target(observation, {"state": "lobby", "target": "orbis_button"}) == [827, 593, 49, 66]
    observation["ui_tree"]["nodes"]["screen"]["fields"]["status"] = fact()
    assert vision.target(observation, {"state": "lobby", "target": "orbis_button"}) is None


def test_stage_adapter_retains_identity_cost_and_start_guards():
    from driver_epic_seven.config import ROOT
    from driver_epic_seven.stages import StageInspector
    from driver_epic_seven.observed_ui import stage_view
    inspector = StageInspector(ROOT / "data/stages/campaign-initial.json")
    observation = {"state": "battle_ready", "stage": {"requested_id": "pen002", "requested_title": "Permeating Darkness",
        "identity_verified": True, "context_verified": True, "expected_energy": 8, "row_box": None,
        "row_locked": None, "energy": {"cost": 8, "available": 900}, "already_cleared": False},
        "matches": {"start_quest_label": {"hit": True, "box": [1040, 615, 100, 30]}}}
    observation["ui_tree"] = build_tree(observation)
    observation["stage"]["energy"]["cost"] = 1
    assert stage_view(observation)["energy"]["cost"] == 8
    with pytest.raises(ValueError, match="limite de energia"):
        inspector.target(observation, {"state": "battle_ready", "target": "stage_start", "max_energy": 7})
    assert inspector.target(observation, {"state": "battle_ready", "target": "stage_start", "max_energy": 8}) == [1040, 615, 100, 30]


def test_calibrated_point_is_not_a_claim_of_visibility():
    config = load_config()
    spec = json.loads(config["vision_file"].read_text(encoding="utf-8"))
    tree = build_tree({"state": "lobby_idle", "matches": {}}, spec)
    fields = tree["nodes"]["visual:wake_lobby"]["fields"]
    assert fields["box_role"]["value"] == "calibrated_point"
    assert fields["visible"]["value"] is None and fields["enabled"]["value"] is None
    assert tree["context"]["scope"] == "recognition_only"
    assert tree["observed_at_epoch_seconds"] is None


def test_saved_pipeline_evidence_binds_tree_to_actual_frame(snapshot, tmp_path):
    evidence = Evidence(tmp_path)
    snapshot["ui_tree"] = build_tree(snapshot)
    original = deepcopy(snapshot)
    evidence.recognized("Pipeline.Test", np.zeros((682, 1212, 3), dtype=np.uint8), snapshot)
    file = next(p for p in evidence.path.glob("*.json"))
    saved = json.loads(file.read_text(encoding="utf-8"))
    assert saved["ui_tree"]["context"]["frame"] == saved["frame"]
    assert saved["ui_tree"]["context"]["observation_file"] == str(file)
    assert snapshot == original
