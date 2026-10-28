"""Current STOVE finish states reuse anchors; map counters are not earned stars."""
import json
import numpy as np
from PIL import Image
import pytest
from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree, operation_view, target_box
from driver_epic_seven.vision import Vision


@pytest.mark.fixtures
def test_stove_completed_unit_and_map_variants_with_no_roster_inference(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    run=ROOT/'var/runs/20261027T012018Z_f4ee88cc'
    expected={7:'story',11:'stage_clear',14:'battle_rewards',17:'story_reward',20:'prequel_story_map',22:'received_reward',24:'prequel_story_map',40:'story'}
    if not all((run/f'agent_{n:06}.png').exists() for n in expected):pytest.skip('Private completed STOVE unit unavailable.')
    bundle=ROOT/'resources/epic-seven';v=Vision(bundle/'vision.json',bundle);results=[]
    class Offline(CustomRecognition):
        def analyze(self,ctx,argv):
            results.append(v.inspect(argv.image,lambda n:ctx.run_recognition(n,argv.image)))
            return self.AnalyzeResult(box=[0,0,1,1],detail=results[-1])
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('StoveFinishFixture',Offline())
    assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    cases=[]
    for n,state in expected.items():
        frame=np.asarray(Image.open(run/f'agent_{n:06}.png').convert('RGB'))[:,:,::-1].copy();cases.append((str(n),n,frame,state))
        if n in (11,14,17,22):cases.append((f'{n}/dimmed',n,(frame*.45).astype(np.uint8),'unknown'))
    for name,n,frame,state in cases:
        before=len(results)
        assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='StoveFinishFixture'),frame).wait().succeeded
        assert len(results)==before+1
        a=results[-1]
        if a['state']!=state:pytest.fail(name+'\n'+json.dumps(a,indent=2))
        saved=json.loads((run/f'agent_{n:06}.json').read_text(encoding='utf-8'))['result'] or {}
        tree=build_tree({**saved,**a},v.spec)
        targets={'stage_clear':'clear_continue','battle_rewards':'result_confirm','story_reward':'story_reward_close','received_reward':'received_reward_close'}
        for candidate,target in targets.items():
            assert bool(target_box(tree,target))==(state==candidate)
        if state=='prequel_story_map':
            view=operation_view({'ui_tree':tree})
            assert view['view']=='prequel_story_map'
            assert view['items'][0]['chapter_star_counter_label']=='3/9'
            assert view['items'][0]['earned_stars'] is None
            assert [r['ordinal'] for r in view['items'] if r['semantic_id']=='stage_row']==[3,4,5,6]
            assert 'Arbiter' not in json.dumps(view) and 'summoned' not in json.dumps(view)
    (tmp_path/'stove-finish-replay.json').write_text(json.dumps([
        {'case':c[0],'expected':c[3],'observed':a} for c,a in zip(cases,results)],indent=2),encoding='utf-8')
