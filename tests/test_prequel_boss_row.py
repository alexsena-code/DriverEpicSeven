import json
from copy import deepcopy

import numpy as np
from PIL import Image
import pytest

from driver_epic_seven.config import ROOT
from driver_epic_seven.vision import Vision
from driver_epic_seven.observed_ui import build_tree,operation_view
from driver_epic_seven.prequel import target


@pytest.mark.fixtures
@pytest.mark.parametrize('source_name,stage_id,next_id',[
    ('var/runs/20261028T095702Z_2f558826/path_failure_after.json','ijp007','ijp008'),
    ('var/runs/20261030T202253Z_f3164114/path_failure_after.json','trd009','trd010'),
])
def test_boss_badge_alternative_preserves_native_candidates_and_row_identity(tmp_path,source_name,stage_id,next_id):
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.library import Library
    from maa.pipeline import JTemplateMatch
    from maa.define import LoggingLevelEnum
    source=ROOT/source_name
    image=source.with_suffix('.png')
    if not source.exists() or not image.exists():pytest.skip('Private independent boss row unavailable.')
    original=json.loads(source.read_text(encoding='utf-8'))
    pixels=np.asarray(Image.open(image).convert('RGB'))[:,:,::-1].copy()
    bundle=ROOT/'resources/epic-seven'
    vision=Vision(bundle/'vision.json',bundle)
    spec=vision.spec['templates']['path_prequel_available']
    vision.spec['templates']={'path_prequel_available':spec};vision.spec['states']={};vision.spec['ocr']={}
    native=json.loads((bundle/'pipeline/vision.json').read_text(encoding='utf-8'))
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    covered=pixels.copy();covered[185:255,15:90]=0
    for label,frame,wanted in [('boss',pixels,True),('dimmed',(pixels*.55).astype(np.uint8),False),('covered',covered,False)]:
        readings={}
        for item in [spec,*spec.get('alternatives',[])]:
            definition=native[item['node']]
            readings[item['node']]=tasker.post_recognition('TemplateMatch',JTemplateMatch(
                template=[definition['template']],roi=definition['roi'],threshold=[definition['threshold']]),frame).wait().get().nodes[0].recognition
        observed=vision.inspect(frame,lambda name:readings[name])['matches']['path_prequel_available']
        assert observed['hit'] is wanted,(label,observed)
        data=deepcopy(original);data['matches']['path_prequel_available']=observed;data['ui_tree']=build_tree(data)
        view=operation_view(data)
        if wanted:
            assert target(view,{'kind':'prequel_row','stage_id':stage_id},data,{}) is not None
            assert target(view,{'kind':'prequel_row','stage_id':next_id},data,{}) is None
        else:
            assert target(view,{'kind':'prequel_row','stage_id':stage_id},data,{}) is None
