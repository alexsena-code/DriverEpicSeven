"""Exercise installed Maa 5.14.3 with an in-memory test controller, no game."""
from types import SimpleNamespace
import time

import numpy as np
import pytest

from driver_epic_seven import execution
from driver_epic_seven.observed_ui import build_tree
from test_operation_cycle import context


@pytest.mark.parametrize('advance_on',[2,None])
def test_maa_clear_retry_requires_a_new_recognition_and_stops_at_three(tmp_path,advance_on):
    from maa.controller import CustomController
    from maa.custom_recognition import CustomRecognition
    from maa.define import LoggingLevelEnum
    from maa.resource import Resource
    from maa.tasker import Tasker
    from driver_epic_seven.prequel import finish_graph
    from driver_epic_seven.execution import wrap_graph
    r,cycle,analysis,_=context(tmp_path)
    r.operation_cycle=cycle;r.fatal=None
    events=[];clicks=[]
    class MemoryController(CustomController):
        def connect(self):return True
        def request_uuid(self):return 'closure-retry-only'
        def screencap(self):return np.zeros((682,1212,3),np.uint8)
        def click(self,*args):clicks.append(True);events.append('click');return True
        def touch_down(self,*args):return self.click()
        def touch_up(self,*args):return True
    class Recognizer(CustomRecognition):
        def analyze(self,ctx,argv):
            done=advance_on is not None and len(clicks)>=advance_on
            if argv.node_name.endswith('Clear') and not done:
                events.append('recognize_clear')
                analysis['epoch_seconds']=time.time();analysis['ui_tree']=build_tree(analysis)
                return self.AnalyzeResult(box=[1140,605,68,70],detail=analysis)
            if argv.node_name=='Done' and done:
                return self.AnalyzeResult(box=[0,0,1,1],detail={})
            return None
    # The real compiled closure node, with synthetic destinations and short
    # waits only for this transition simulation. No Start exists in this task.
    original=finish_graph('jer001',True)
    name='Path.Campaign.jer001.Clear'
    clear=dict(original[name],next=['Done',name],timeout=100,pre_delay=0,post_delay=0)
    graph={'Entry':{'next':[name],'timeout':100,'rate_limit':1},name:clear,
           'Done':{'recognition':'Custom','custom_recognition':'ScreenTarget','action':'DoNothing'}}
    graph[name]['rate_limit']=1
    bundle=tmp_path/'bundle';bundle.mkdir();(bundle/'pipeline').mkdir()
    import json
    (bundle/'pipeline/test.json').write_text(json.dumps({'Entry':{}}))
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    ctrl=MemoryController();assert ctrl.post_connection().wait().succeeded
    resource=Resource();resource.register_custom_recognition('ScreenTarget',Recognizer())
    resource.register_custom_action('OperationBoundary',execution.boundary_action(r))
    assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker();assert tasker.bind(resource,ctrl)
    job=tasker.post_task('Entry',wrap_graph(graph)).wait()
    assert r.fatal is None
    assert job.succeeded is (advance_on is not None)
    assert len(clicks)==(advance_on or 3)
    assert events==['recognize_clear','click']*len(clicks)
    assert not r.path_battles.read()['stages']


@pytest.mark.parametrize('disk_failure',[False,True])
def test_maa_custom_boundary_can_refuse_before_native_action(tmp_path,monkeypatch,disk_failure):
    from maa.controller import CustomController
    from maa.custom_recognition import CustomRecognition
    from maa.define import LoggingLevelEnum
    from maa.resource import Resource
    from maa.tasker import Tasker
    r,cycle,analysis,params=context(tmp_path)
    r.operation_cycle=cycle;r.fatal=None
    calls=[];original=execution.native_action
    def native(*args):calls.append(True);return original(*args)
    monkeypatch.setattr(execution,'native_action',native)
    if disk_failure:
        def fail(_):raise OSError('simulated persistence failure')
        monkeypatch.setattr(r.path_attempts,'save',fail)
    class Recognition(CustomRecognition):
        def analyze(self,ctx,argv):
            analysis['epoch_seconds']=time.time()
            analysis['ui_tree']=build_tree(analysis)
            return self.AnalyzeResult(box=[10,10,30,30],detail=analysis)
    inputs=[]
    class MemoryController(CustomController):
        def connect(self):return True
        def request_uuid(self):return 'wave1-test-only'
        def start_app(self,intent):return False
        def stop_app(self,intent):return False
        def screencap(self):return np.zeros((682,1212,3),np.uint8)
        def click(self,x,y):inputs.append('click');return True
        def swipe(self,*args):return False
        def touch_down(self,*args):inputs.append('down');return True
        def touch_move(self,*args):return False
        def touch_up(self,*args):inputs.append('up');return True
        def click_key(self,*args):return False
        def input_text(self,*args):return False
        def key_down(self,*args):return False
        def key_up(self,*args):return False
    bundle=tmp_path/'bundle';bundle.mkdir();(bundle/'pipeline').mkdir()
    (bundle/'pipeline/test.json').write_text('{"Entry":{"action":"DoNothing"}}')
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    ctrl=MemoryController();assert ctrl.post_connection().wait().succeeded
    resource=Resource();resource.register_custom_recognition('ScreenTarget',Recognition())
    resource.register_custom_action('OperationBoundary',execution.boundary_action(r))
    assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker();assert tasker.bind(resource,ctrl)
    graph={'Entry':{'recognition':'DirectHit','action':'DoNothing','next':['Send'],'timeout':1000},
           'Send':{'recognition':'Custom','custom_recognition':'ScreenTarget',
                   'custom_recognition_param':params,'action':'LongPress','duration':100,'max_hit':1,
                   'pre_delay':0,'post_delay':0}}
    job=tasker.post_task('Entry',execution.wrap_graph(graph)).wait()
    assert job.succeeded is not disk_failure
    assert len(calls)==(0 if disk_failure else 1)
    assert inputs==([] if disk_failure else ['down','up'])
    assert bool(r.fatal) is disk_failure
    if not disk_failure:assert r.path_attempts.read()['stages']['task'][0]['status']=='sent'
