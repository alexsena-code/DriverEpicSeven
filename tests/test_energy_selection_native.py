"""Native filtered candidates for the selected Leif purchase card."""
import numpy as np
from PIL import Image
import pytest

from driver_epic_seven.config import ROOT
from driver_epic_seven.vision import validated_template_match


@pytest.mark.fixtures
def test_leaf_selection_requires_current_undimmed_selected_card(tmp_path):
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.library import Library
    from maa.pipeline import JTemplateMatch
    from maa.define import LoggingLevelEnum
    paths = [ROOT/'var/runs/20261104T165020Z_093b2435/agent_000027.png',
             ROOT/'var/runs/20261104T181328Z_8933bce0/agent_000007.png',
             ROOT/'var/runs/20261104T181328Z_8933bce0/agent_000004.png']
    if not all(p.exists() for p in paths):
        pytest.skip('Private selected and unselected cards unavailable')
    frames = [np.asarray(Image.open(p).convert('RGB'))[:, :, ::-1].copy() for p in paths]
    template = np.asarray(Image.open(ROOT/'resources/epic-seven/image/energy_leaf_selected.png').convert('RGB'))[:, :, ::-1].copy()
    Tasker.set_stdout_level(LoggingLevelEnum.Off)
    Tasker.set_log_dir(tmp_path/'maa')
    resource = Resource(); resource.set_cpu()
    assert resource.post_bundle(ROOT/'resources/epic-seven').wait().succeeded
    tasker = Tasker()
    assert Library.framework().MaaTaskerBindResource(tasker._handle, resource._handle)
    covered = frames[0].copy(); covered[289:310, 357:583] = 0
    for label, frame, expected in [('original', frames[0], True), ('independent', frames[1], True),
                                   ('crystals_selected', frames[2], False),
                                   ('dimmed', (frames[0] * .55).astype(np.uint8), False),
                                   ('covered', covered, False)]:
        raw = tasker.post_recognition('TemplateMatch', JTemplateMatch(
            template=['energy_leaf_selected.png'], roi=[355, 287, 230, 105], threshold=[.99]),
            frame).wait().get().nodes[0].recognition
        found = validated_template_match(frame, [template], raw, 5)
        assert found['hit'] is expected, (label, found)
