import json
from copy import deepcopy
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree, operation_view
from driver_epic_seven.prequel import augment_title, title_match


@pytest.mark.fixtures
@pytest.mark.parametrize('name', ['sac005-preparation-20261104', 'sac005-preparation2-20261104'])
def test_wrapped_title_reread_needs_location_and_exact_continuation(tmp_path, name):
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    source = ROOT/'var'/f'{name}.json'
    if not source.exists():
        pytest.skip('Private wrapped title fixture unavailable')
    original = json.loads(source.read_text(encoding='utf-8'))
    image = np.asarray(Image.open(source.with_suffix('.png')).convert('RGB'))[:, :, ::-1].copy()
    Tasker.set_stdout_level(LoggingLevelEnum.Off); Tasker.set_log_dir(tmp_path/'maa')
    resource = Resource(); resource.set_cpu()
    assert resource.post_bundle(ROOT/'resources/epic-seven').wait().succeeded
    tasker = Tasker(); assert Library.framework().MaaTaskerBindResource(tasker._handle, resource._handle)
    def recognize(kind, args):
        return tasker.post_recognition(kind, args, image).wait().get().nodes[-1].recognition
    params = {'kind': 'prequel_start', 'stage_id': 'sac005'}
    good = deepcopy(original); augment_title(good, params, recognize)
    assert good['campaign_wrapped_title_reread']['accepted'] is True
    info = operation_view({'ui_tree': build_tree(good)})['items'][0]
    assert title_match(info['story_title'], 'What’s Left Behind in the Past I')
    assert not title_match(info['story_title'], 'What’s Left Behind in the Past II')
    wrong = deepcopy(original)
    next(r for r in wrong['text'] if r['text'] == 'Business District Ruins')['text'] = 'Other District'
    augment_title(wrong, params, recognize)
    assert 'campaign_wrapped_title_reread' not in wrong
    if name == 'sac005-preparation2-20261104':
        shifted = deepcopy(original)
        continuation = next(r for r in shifted['text'] if r['text'] == 'PastI')
        continuation['box'] = [878, 125, 47, 17]
        continuation['score'] = .871261
        augment_title(shifted, params, recognize)
        assert shifted['campaign_wrapped_title_reread']['accepted'] is True
        assert shifted['campaign_wrapped_title_reread']['attempts'][-1]['roi'] == [875, 122, 55, 25]
        wrong_location = deepcopy(original)
        row = next(r for r in wrong_location['text'] if r['text'] == 'Business District Ruins')
        row.update(text='Business vistrict Ruins', score=.910977, box=[879, 77, 190, 28])
        augment_title(wrong_location, params, recognize)
        assert wrong_location['campaign_location_reread']['accepted'] is True
