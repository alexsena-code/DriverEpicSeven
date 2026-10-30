"""Current and older friend invitations share the existing Cancel treatment."""
import numpy as np
from PIL import Image
import pytest
from driver_epic_seven.config import ROOT
from driver_epic_seven.vision import Vision


@pytest.mark.fixtures
def test_native_current_friend_prompt_and_missing_controls(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.library import Library
    from maa.pipeline import JCustomRecognition
    from maa.define import LoggingLevelEnum
    paths=[ROOT/p for p in (
        'var/runs/20261030T035220Z_b37e5050/agent_000008.png',
        'var/runs/20261030T041811Z_874f006c/agent_000015.png',
        'var/runs/20261030T043311Z_c1b210d0/observation.png',
        'var/runs/20261026T012003Z_c0ed817e/friend_request.png')]
    if not all(p.exists() for p in paths):pytest.skip('Private friend invitation frames unavailable.')
    vision=Vision(ROOT/'resources/epic-seven/vision.json',ROOT/'resources/epic-seven')
    vision.spec['templates']={k:v for k,v in vision.spec['templates'].items()
                               if k in ('friend_header','friend_prompt','friend_cancel')}
    vision.spec['states']={'friend_request':vision.spec['states']['friend_request']}
    vision.spec['ocr']={}
    found=[]
    class Replay(CustomRecognition):
        def analyze(self,context,argv):
            found.append(vision.inspect(argv.image,lambda n:context.run_recognition(n,argv.image)))
            return self.AnalyzeResult(box=[0,0,1,1],detail=found[-1])
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('FriendPromptReplay',Replay())
    assert resource.post_bundle(ROOT/'resources/epic-seven').wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    for path in paths:
        frame=np.asarray(Image.open(path).convert('RGB'))[:,:,::-1].copy()
        cases=[('positive',frame,True),('dimmed',(frame*.5).astype(np.uint8),False)]
        for label,box in [('heading',(550,140,660,190)),('prompt',(390,210,820,285)),('cancel',(410,470,600,530))]:
            image=frame.copy();x,y,x2,y2=box;image[y:y2,x:x2]=0
            cases.append((label,image,False))
        for label,image,positive in cases:
            assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='FriendPromptReplay'),image).wait().succeeded
            assert (found[-1]['state']=='friend_request') is positive,(path,label,found[-1])
