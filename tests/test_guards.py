from copy import deepcopy
import json
from types import SimpleNamespace

import numpy as np
import pytest

from driver_epic_seven.config import load_config
from driver_epic_seven.evidence import Evidence
from driver_epic_seven.pipelines import executable_routine, validate
from driver_epic_seven.runtime import check_observation, Runtime
from driver_epic_seven.vision import classify, pixel_error, Vision
from driver_epic_seven.windows import verify_window


WINDOW = {"hwnd": 100, "pid": 200, "process_name": "EpicSeven_Steam.exe",
          "window_title": "Epic Seven", "window_class": "GLFW30",
          "client_size": [1212,682], "minimized": False, "foreground": False}


def test_pid_reuse_is_rejected():
    changed = deepcopy(WINDOW)
    changed["pid"] += 1
    with pytest.raises(RuntimeError,match="identidade"):
        verify_window(changed,WINDOW,load_config(),True)


def test_resolution_change_blocks_input():
    changed = deepcopy(WINDOW)
    changed["client_size"] = [1280,720]
    with pytest.raises(RuntimeError,match="Resolução"):
        verify_window(changed,WINDOW,load_config(),True)


def test_background_and_foreground_are_separate_conditions():
    config = load_config()
    verify_window(WINDOW,WINDOW,config,True)
    config["mouse_method"] = 1
    with pytest.raises(RuntimeError,match="primeiro plano"):
        verify_window(WINDOW,WINDOW,config,True)


def test_stale_observation_and_different_window_are_rejected():
    saved = {"epoch_seconds":1000,"window":WINDOW}
    check_observation(saved,WINDOW,1010)
    with pytest.raises(ValueError,match="expirada"):
        check_observation(saved,WINDOW,1031)
    changed = {**WINDOW,"hwnd":999}
    with pytest.raises(ValueError,match="outra janela"):
        check_observation(saved,changed,1010)


def test_ambiguous_screen_does_not_become_a_valid_state():
    matches = {"a":{"hit":True},"b":{"hit":True}}
    assert classify(matches,{"one":{"all":["a"]},"two":{"all":["b"]}})=="unknown"


def test_pixel_check_rejects_dimmed_overlay_even_with_same_pattern():
    template = np.full((20,20,3),180,dtype=np.uint8)
    dimmed = np.full_like(template,65)
    assert pixel_error(dimmed,template,[0,0,20,20]) > 18


def test_coordinate_target_is_bound_to_idle_lobby():
    config=load_config()
    vision=Vision(config["vision_file"],config["resource_dir"])
    assert vision.target({"state":"lobby","matches":{}},{"state":"lobby","target":"wake_lobby"}) is None
    assert vision.target({"state":"lobby_idle","matches":{}},{"state":"lobby_idle","target":"wake_lobby"}) == [1120,620,1,1]


def test_uncalibrated_battle_cannot_be_executed():
    with pytest.raises(ValueError,match="calibração"):
        executable_routine(load_config(),"start_battle")


def test_live_resource_contracts_are_complete():
    assert validate(load_config())["valid"]


def test_sdk_node_names_cannot_create_nested_evidence_paths(tmp_path):
    evidence=Evidence(tmp_path)
    evidence.recognized("recognition/Custom/node",np.zeros((2,2,3),dtype=np.uint8),{"state":"unknown"})
    files=list(evidence.path.iterdir())
    assert len(files)==2
    assert all(path.is_file() and path.parent==evidence.path for path in files)


def test_postcondition_timeout_preserves_dispatch_without_retry(tmp_path):
    runtime=object.__new__(Runtime)
    runtime.evidence=Evidence(tmp_path)
    runtime.observe=lambda name: {"state":"lobby","window":WINDOW}
    runtime.guard=lambda **kwargs: WINDOW
    runtime.wait=lambda job: job
    runtime.vision=SimpleNamespace(
        spec={"states":{"lobby":{},"orbis_guide":{}},"target_states":{"orbis_button":["lobby"]}},
        target=lambda analysis,params:[827,593,49,66])
    calls=[]
    runtime.ctrl=SimpleNamespace(post_click=lambda *point:calls.append(point))

    def no_transition(state):
        raise RuntimeError("Destino não confirmado")

    runtime.wait_state=no_transition
    with pytest.raises(RuntimeError,match="Destino"):
        runtime.primitive("click",target="orbis_button",expect="orbis_guide")
    record=json.loads((runtime.evidence.path/"primitive.json").read_text(encoding="utf-8"))
    assert record["dispatch_succeeded"] is True
    assert record["postcondition_verified"] is False
    assert "error" in record
    assert len(calls)==1
