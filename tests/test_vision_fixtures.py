"""Usa o reconhecedor Maa em capturas salvas; não conecta ao jogo."""

import json
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from driver_epic_seven.config import ROOT, load_config
from driver_epic_seven.vision import Vision


@pytest.mark.fixtures
def test_saved_positive_and_negative_frames(tmp_path):
    fixture_dir=ROOT/"tests/fixtures/local"
    if not (fixture_dir/"manifest.json").exists():
        pytest.skip("Capturas locais não versionadas; importe a sessão para executar esta verificação.")
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.define import LoggingLevelEnum
    from maa.library import Library
    Tasker.set_stdout_level(LoggingLevelEnum.Off)
    Tasker.set_log_dir(tmp_path/"maa")
    config=load_config()
    vision=Vision(config["vision_file"],config["resource_dir"])
    found=[]

    class FixtureRecognition(CustomRecognition):
        def analyze(self,context,argv):
            analysis=vision.inspect(argv.image,lambda name:context.run_recognition(name,argv.image))
            found.append(analysis)
            return self.AnalyzeResult(box=[0,0,1,1],detail=analysis)

    resource=Resource()
    resource.set_cpu()
    resource.register_custom_recognition("Fixture",FixtureRecognition())
    assert resource.post_bundle(config["resource_dir"]).wait().succeeded
    tasker=Tasker()
    # The public C API supports recognition with only a resource. Python's bind
    # requires a controller; using the C binder keeps this test wholly offline.
    assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    for case in json.loads((fixture_dir/"manifest.json").read_text()):
        frame=np.asarray(Image.open(fixture_dir/case["file"]).convert("RGB"))[:,:,::-1].copy()
        job=tasker.post_recognition("Custom",JCustomRecognition(custom_recognition="Fixture"),frame).wait()
        assert job.succeeded
        assert found[-1]["state"]==case["expected_state"], (case,found[-1])


@pytest.mark.fixtures
def test_idle_lighting_rejects_other_screens_and_dimmed_overlays(tmp_path):
    """Exercise the paired day/night anchors through the real Maa matcher."""
    fixture_dir = ROOT / "tests/fixtures/local"
    if not (fixture_dir / "56_lobby_idle_day.png").exists():
        pytest.skip("Amostras privadas da taberna diurna não estão instaladas.")
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.define import LoggingLevelEnum
    from maa.library import Library

    config = load_config()
    vision = Vision(config["vision_file"], config["resource_dir"])
    vision.spec["states"] = {k: v for k, v in vision.spec["states"].items()
                             if k in ("lobby", "lobby_idle", "orbis_guide")}
    names = {name for composition in vision.spec["states"].values() for state in composition.get("variants",[composition])
             for clause in ("all", "any", "none") for name in state.get(clause, [])}
    vision.spec["templates"] = {k: v for k, v in vision.spec["templates"].items() if k in names}
    vision.spec["ocr"] = {}
    found = []

    class IdleRecognition(CustomRecognition):
        def analyze(self, context, argv):
            analysis = vision.inspect(argv.image, lambda name: context.run_recognition(name, argv.image))
            found.append(analysis)
            return self.AnalyzeResult(box=[0, 0, 1, 1], detail=analysis)

    Tasker.set_stdout_level(LoggingLevelEnum.Off)
    Tasker.set_log_dir(tmp_path / "maa")
    resource = Resource()
    resource.set_cpu()
    resource.register_custom_recognition("IdleFixture", IdleRecognition())
    assert resource.post_bundle(config["resource_dir"]).wait().succeeded
    tasker = Tasker()
    assert Library.framework().MaaTaskerBindResource(tasker._handle, resource._handle)
    cases = [(case["file"], case["expected_state"] == "lobby_idle")
             for case in json.loads((fixture_dir / "manifest.json").read_text())]
    cases.extend((name, False) for name in ("q_reward_overlay.png", "q_diary.png", "q_mode.png"))
    samples = [(name, np.asarray(Image.open(fixture_dir / name).convert("RGB"))[:, :, ::-1].copy(), idle)
               for name, idle in cases]
    for name in ("02_lobby_idle.png", "56_lobby_idle_day.png"):
        frame = np.asarray(Image.open(fixture_dir / name).convert("RGB"))[:, :, ::-1].copy()
        for factor in (.7, .45):
            samples.append((f"{name}/dimmed-{factor}", (frame * factor).astype(np.uint8), False))
        covered = frame.copy()
        covered[60:250, 850:1060] = 0
        samples.append((f"{name}/wall-covered", covered, False))
    for name, frame, expected_idle in samples:
        job = tasker.post_recognition("Custom", JCustomRecognition(custom_recognition="IdleFixture"), frame).wait()
        assert job.succeeded
        assert (found[-1]["state"] == "lobby_idle") == expected_idle, (name, found[-1])


@pytest.mark.fixtures
def test_navigation_markers_reject_dimmed_and_unrelated_screens(tmp_path):
    fixture_dir = ROOT / "tests/fixtures/local"
    new_cases = [("63_quick_menu.png", "quick_menu"), ("64_options_screen.png", "options_screen"),
                 ("65_hero_screen.png", "hero_screen"),
                 ("66_battle_categories_seasonal.png", "battle_categories"),
                 ("67_battle_categories_normal.png", "battle_categories")]
    if not all((fixture_dir / name).exists() for name, _ in new_cases):
        pytest.skip("Capturas privadas da calibração de navegação não estão instaladas.")
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.define import LoggingLevelEnum
    from maa.library import Library

    config = load_config()
    vision = Vision(config["vision_file"], config["resource_dir"])
    selected = {"quick_menu", "options_screen", "hero_screen", "battle_categories", "lobby", "orbis_guide"}
    vision.spec["states"] = {k: v for k, v in vision.spec["states"].items() if k in selected}
    names = {name for composition in vision.spec["states"].values() for state in composition.get("variants",[composition])
             for clause in ("all", "any", "none") for name in state.get(clause, [])}
    vision.spec["templates"] = {k: v for k, v in vision.spec["templates"].items() if k in names}
    vision.spec["ocr"] = {}
    found = []

    class NavigationRecognition(CustomRecognition):
        def analyze(self, context, argv):
            analysis = vision.inspect(argv.image, lambda name: context.run_recognition(name, argv.image))
            found.append(analysis)
            return self.AnalyzeResult(box=[0, 0, 1, 1], detail=analysis)

    Tasker.set_stdout_level(LoggingLevelEnum.Off)
    Tasker.set_log_dir(tmp_path / "maa")
    resource = Resource()
    resource.set_cpu()
    resource.register_custom_recognition("NavigationFixture", NavigationRecognition())
    assert resource.post_bundle(config["resource_dir"]).wait().succeeded
    tasker = Tasker()
    assert Library.framework().MaaTaskerBindResource(tasker._handle, resource._handle)
    manifest = json.loads((fixture_dir / "manifest.json").read_text())
    cases = [(c["file"], c["expected_state"] if c["expected_state"] in selected else "unknown") for c in manifest]
    cases += [("q_mode.png", "unknown"), ("q_categories.png", "battle_categories")]
    samples = [(name, np.asarray(Image.open(fixture_dir / name).convert("RGB"))[:, :, ::-1].copy(), expected)
               for name, expected in cases]
    for name, _ in new_cases:
        frame = np.asarray(Image.open(fixture_dir / name).convert("RGB"))[:, :, ::-1].copy()
        samples.append((name + "/dimmed", (frame * .55).astype(np.uint8), "unknown"))
    for name, frame, expected in samples:
        assert tasker.post_recognition("Custom", JCustomRecognition(
            custom_recognition="NavigationFixture"), frame).wait().succeeded
        assert found[-1]["state"] == expected, (name, found[-1])
