import json
from types import SimpleNamespace

import numpy as np
import pytest

from driver_epic_seven.agent_session import parse_request
from driver_epic_seven.gestures import skill_double_tap_graph
from driver_epic_seven.runtime import Runtime


def test_double_tap_is_one_bounded_native_gesture_in_known_skill_area():
    graph = skill_double_tap_graph((1062, 627), 'battle_running', [1212, 682])
    actions = [n for n in graph.values() if n['action'] != 'DoNothing']
    assert len(actions) == 1
    assert actions[0]['repeat'] == 2 and actions[0]['repeat_delay'] == 80
    assert actions[0]['max_hit'] == 1
    assert actions[0]['recognition'] == 'Custom'
    assert actions[0]['custom_recognition_param'] == {'state': 'battle_running'}
    assert actions[0]['target'] == [1062, 627, 1, 1]
    assert not any(n.get('on_error') for n in graph.values())
    _, args = parse_request(json.dumps({'args': ['skill-double-tap', '2', '--observation', 'seen.json', '--from-state', 'battle_running']}))
    assert args.slot == 2


@pytest.mark.parametrize('point,state,size', [
    ((1062,627),'battle_ready',[1212,682]),
    ((1062,627),'unknown',[1212,682]),
    ((1084,622),'battle_running',[1212,682]),
    ((1062,627),'battle_running',[1280,720]),
])
def test_non_skill_or_non_battle_context_is_rejected(point, state, size):
    with pytest.raises(ValueError):
        skill_double_tap_graph(point, state, size)


def test_double_tap_requires_explicit_observation_and_state_before_input():
    runtime = object.__new__(Runtime)
    runtime.observe = lambda name: {'state': 'battle_running', 'window': {'client_size': [1212,682]}}
    runtime.vision = SimpleNamespace(spec={'states': {}})
    with pytest.raises(ValueError, match='observação'):
        runtime.primitive('skill_double_tap', point=(1062,627), from_state='battle_running')


@pytest.mark.parametrize('recognized', [True, False])
def test_native_gesture_sends_exactly_two_taps_or_none_offline(tmp_path, recognized):
    from maa.controller import CustomController
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.define import LoggingLevelEnum

    class ContextProof(CustomRecognition):
        def analyze(self, context, argv):
            return self.AnalyzeResult(box=[0,0,1,1] if recognized else None, detail={})

    class Offline(CustomController):
        def __init__(self):
            self.clicks = []
            super().__init__()
        def connect(self): return True
        def request_uuid(self): return 'offline-double-tap-only'
        def get_features(self): return 0
        def screencap(self): return np.zeros((682,1212,3), dtype=np.uint8)
        def click(self, x, y):
            self.clicks.append((x,y))
            return True
        def unexpected(self, *args): raise AssertionError('Unexpected input')
        start_app=stop_app=swipe=touch_down=touch_move=touch_up=click_key=input_text=key_down=key_up=unexpected

    Tasker.set_stdout_level(LoggingLevelEnum.Off)
    Tasker.set_log_dir(tmp_path/'maa')
    resource = Resource()
    resource.register_custom_recognition('ScreenTarget', ContextProof())
    bundle = tmp_path/'resource'
    (bundle/'pipeline').mkdir(parents=True)
    (bundle/'pipeline/base.json').write_text('{}')
    assert resource.post_bundle(bundle).wait().succeeded
    ctrl = Offline()
    ctrl.set_screenshot_use_raw_size(True)
    assert ctrl.post_connection().wait().succeeded
    tasker = Tasker()
    assert tasker.bind(resource, ctrl)
    graph = skill_double_tap_graph((1062,627), 'battle_running', [1212,682])
    graph['SkillDoubleTap.Entry']['timeout'] = 200
    job = tasker.post_task('SkillDoubleTap.Entry', graph).wait()
    assert ctrl.clicks == ([(1062,627)]*2 if recognized else [])
    assert job.succeeded is recognized
