"""Native candidate filtering plus independent result backgrounds; no window."""
import numpy as np
from PIL import Image
import pytest

from driver_epic_seven.config import ROOT
from driver_epic_seven.vision import validated_template_match


@pytest.mark.fixtures
def test_existing_checks_keep_native_threshold_and_reject_dimmed_or_covered_results(tmp_path):
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.library import Library
    from maa.pipeline import JTemplateMatch
    from maa.define import LoggingLevelEnum
    path=ROOT/'var/group2-live/ijp003-clear-independent.png'
    if not path.exists():pytest.skip('Private independent result unavailable.')
    frame=np.asarray(Image.open(path).convert('RGB'))[:,:,::-1].copy()
    template=np.asarray(Image.open(ROOT/'resources/epic-seven/image/clear_objective_check.png').convert('RGB'))[:,:,::-1].copy()
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();assert resource.post_bundle(ROOT/'resources/epic-seven').wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    covered=frame.copy();covered[525:565,518:563]=0
    for label,pixels in [('positive',frame),('dimmed',(frame*.55).astype(np.uint8)),('covered',covered)]:
        for i,x in enumerate((200,518,836),1):
            details=tasker.post_recognition('TemplateMatch',JTemplateMatch(
                template=['clear_objective_check.png'],roi=[x,525,45,40],threshold=[.94]),pixels).wait().get().nodes[0].recognition
            result=validated_template_match(pixels,[template],details,14,green_glyph=True)
            assert result['hit'] is (label=='positive' or (label=='covered' and i!=2)),(label,i,result)
            if label=='positive':
                assert details.hit and result['score']>=.94 and result['pixel_mae']<=14
    # Only candidates already retained by Maa can pass the scoped pixel proof.
    assert not validated_template_match(frame,[template],None,14,green_glyph=True)['hit']
