"""Quick Battle state is observation, never an implicit alternate Start."""
from copy import deepcopy
import json

import numpy as np
from PIL import Image
import pytest

from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree, operation_view, target_box
from driver_epic_seven.altar import target
from test_altar_ui import prep


def test_quick_button_states_are_partial_and_scoped_to_the_current_preparation():
    data=prep()
    for state in (True,False,None):
        current=deepcopy(data)
        current['matches'].update({f'altar_quick_{name}':{'hit':state is value,'box':[1146,606,48,48]}
                                  for name,value in [('on',True),('off',False)]})
        tree=build_tree(current);view=operation_view({'ui_tree':tree})
        assert view['items'][0]['quick_battle_active'] is state
        assert bool(view['controls']) is (state is not True)
        assert target_box(tree,'altar_quick_on') is None
        assert target_box(tree,'altar_quick_off') is None
    current=deepcopy(data)
    current['matches']={f'altar_quick_{name}':{'hit':True,'box':[1146,606,48,48]} for name in ('on','off')}
    assert operation_view({'ui_tree':build_tree(current)})['items'][0]['quick_battle_active'] is None
    current['matches']={'altar_quick_on':{'hit':True,'box':[0,0,48,48]}}
    assert operation_view({'ui_tree':build_tree(current)})['items'][0]['quick_battle_active'] is None


@pytest.mark.fixtures
def test_saved_quick_composition_never_exposes_normal_start_even_if_cost_matches():
    path=ROOT/'var/runs/20261028T200703Z_4e4a3ba2/path_failure_after.json'
    if not path.exists():pytest.skip('Private Quick Battle observation unavailable.')
    data=json.loads(path.read_text(encoding='utf-8'));data.pop('ui_tree',None)
    data['matches']['altar_quick_on']={'hit':True,'box':[1146,606,48,48]}
    view=operation_view({'ui_tree':build_tree(data)})
    assert view['view']=='spirit_altar_quick_preparation'
    assert view['items'][0]['quick_battle_active'] is True
    assert view['items'][0]['quick_battle_count']=={'selected':10,'maximum':10}
    assert view['items'][0]['cost']['cost']==90
    assert not view['controls']
    view['items'][0]['cost']['cost']=9
    assert target(view,{'kind':'altar_start','stage_id':'cmon001','max_energy':999},data,{}) is None


@pytest.mark.fixtures
def test_native_quick_state_templates_have_opposite_and_unrelated_negatives(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.define import LoggingLevelEnum
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.resource import Resource
    from maa.tasker import Tasker
    from driver_epic_seven.vision import Vision
    run=ROOT/'var/runs/20261028T200703Z_4e4a3ba2'
    sources=[(run/'agent_000009.png','on'),(run/'observation.png','off'),
             (ROOT/'var/runs/20261028T200037Z_2c75c487/agent_000006.png',None)]
    if not all(p.exists() for p,_ in sources):pytest.skip('Private quick-state native fixtures unavailable.')
    bundle=ROOT/'resources/epic-seven';vision=Vision(bundle/'vision.json',bundle);out=[]
    class Offline(CustomRecognition):
        def analyze(self,ctx,argv):
            out.append(vision.inspect(argv.image,lambda name:ctx.run_recognition(name,argv.image)))
            return self.AnalyzeResult(box=[0,0,1,1],detail=out[-1])
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('QuickStateFixture',Offline())
    assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    diagnostics=[]
    for path,state in sources:
        frame=np.asarray(Image.open(path).convert('RGB'))[:,:,::-1].copy()
        for altered in (False,True):
            pixels=(frame.astype(np.float32)*.4).astype(np.uint8) if altered else frame
            assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='QuickStateFixture'),pixels).wait().succeeded
            matches=out[-1]['matches']
            assert matches['altar_quick_on']['hit'] is (state=='on' and not altered)
            assert matches['altar_quick_off']['hit'] is (state=='off' and not altered)
            diagnostics.append({'source':str(path),'dimmed':altered,
                'matches':{k:v for k,v in matches.items() if k.startswith('altar_quick_')}})
    (tmp_path/'quick-states.json').write_text(json.dumps(diagnostics,indent=2),encoding='utf-8')
