from copy import deepcopy
from types import SimpleNamespace
import json

import numpy as np
import pytest

from fixture_cache import FixtureCache,bundle_signature,transition_overrides
from native_tiers import native_reasons


def test_exact_pixels_configuration_and_effective_node_are_distinct():
    cache=FixtureCache();frame=np.zeros((4,4,3),np.uint8);env={'model':'one','pipeline':'one'}
    base=cache.key(frame,env,{'threshold':.9})
    assert cache.key(frame.copy(),env,{'threshold':.9})==base
    frame[0,0,0]=1
    assert cache.key(frame,env,{'threshold':.9})!=base
    frame[0,0,0]=0
    for changed in ({'model':'two','pipeline':'one'},{'model':'one','pipeline':'two'}):
        assert cache.key(frame,changed,{'threshold':.9})!=base
    assert cache.key(frame,env,{'threshold':.8})!=base
    cache.local.vision='changed configuration'
    assert cache.key(frame,env,{'threshold':.9})!=base
    ctx=SimpleNamespace(tasker=SimpleNamespace(resource=SimpleNamespace(_handle=1)))
    cache.resources[1]={'inference':'CPU','bundles':['immutable']};cache.local.environments={}
    assert cache.environment(ctx)['inference']=='CPU'
    cache.resources[1]['inference']='unverified'
    assert cache.environment(ctx) is None  # a failed configuration cannot reuse the previous binding.


@pytest.mark.parametrize('relative',['pipeline/node.json','image/template.png','model/ocr/model.onnx','vision.json'])
def test_bundle_invalidation_uses_bytes_even_with_same_length(tmp_path,relative):
    path=tmp_path/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'old')
    before=bundle_signature(tmp_path);path.write_bytes(b'new')
    assert bundle_signature(tmp_path)!=before


def test_cache_returns_independent_values_and_never_reuses_failed_native_call():
    cache=FixtureCache();calls=[]
    def native():calls.append(True);return SimpleNamespace(hit=True,filtered_results=[{'score':.99}])
    first=cache.read('key',native);first.filtered_results[0]['score']=0
    second=cache.read('key',native);second.filtered_results.append('mutated')
    assert cache.read('key',native).filtered_results==[{'score':.99}]
    assert len(calls)==1
    assert cache.read('failed',lambda:None) is None
    assert cache.read('failed',native).hit and len(calls)==2


def test_bounded_cache_evicts_without_reusing_a_different_frame():
    cache=FixtureCache(max_bytes=500)
    for i in range(8):cache.read(str(i),lambda:SimpleNamespace(hit=False,payload='x'*250))
    assert cache.bytes<=500 and cache.stats['evictions']>0
    assert cache.read('0',lambda:SimpleNamespace(hit=True)).hit


def test_simulation_overrides_preserve_actions_geometry_and_real_gesture_contract():
    graph={'Entry':{'action':'DoNothing','next':['Hold']},'Hold':{'action':'LongPress',
        'target':[10,20,1,1],'duration':1500,'max_hit':1,'repeat':2,'repeat_delay':80,
        'pre_wait_freezes':{'time':350},'post_delay':700}}
    original=deepcopy(graph);simulation=transition_overrides(graph)
    for name in graph:
        for key in ('action','target','duration','max_hit','repeat','repeat_delay','next'):
            assert simulation[name].get(key)==graph[name].get(key)
    assert simulation['Hold']['post_delay']==0 and graph==original


def test_fixture_dependency_audit_finds_stage_engine_and_named_helper():
    from test_stage_selection import stage_engine
    assert 'Resource' in native_reasons(stage_engine)


@pytest.mark.native
def test_native_cache_replays_identical_results_but_not_override_or_dark_pixels(tmp_path,request):
    from maa.context import Context
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.library import Library
    from maa.pipeline import JCustomRecognition
    from maa.define import LoggingLevelEnum
    from PIL import Image
    template=np.zeros((20,20,3),np.uint8);template[2:18,2:18]=255;template[5:10,5:10]=30
    bundle=tmp_path/'bundle';(bundle/'pipeline').mkdir(parents=True);(bundle/'image').mkdir()
    Image.fromarray(template).save(bundle/'image/marker.png')
    definitions={'Marker':{'recognition':'TemplateMatch','template':'marker.png','roi':[0,0,40,40],'threshold':.9}}
    (bundle/'pipeline/base.json').write_text(json.dumps(definitions))
    image=np.zeros((40,40,3),np.uint8);image[10:30,10:30]=template
    out=[]
    cache=getattr(request.config,'_fixture_cache',None)
    before=deepcopy(cache.stats) if cache else None
    class Offline(CustomRecognition):
        def __init__(self,tag):super().__init__();self.tag=tag
        def analyze(self,ctx,argv):
            if argv.custom_recognition_param=='"override"':ctx.override_pipeline({'Marker':{'threshold':1.01}})
            value=ctx.run_recognition('Marker',argv.image)
            out.append({'tag':self.tag,'hit':value.hit,'box':value.box,'raw':value.raw_detail})
            return self.AnalyzeResult(box=[0,0,1,1],detail={})
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('Offline',Offline('A'))
    assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    for frame,param in ((image,None),(image.copy(),None),((image*.45).astype(np.uint8),None),(image,'override')):
        assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='Offline',custom_recognition_param=param),frame).wait().succeeded
    assert out[0]==out[1] and out[0]['hit'] and not out[-1]['hit']
    other=Resource();other.set_cpu();other.register_custom_recognition('Offline',Offline('B'))
    assert other.post_bundle(bundle).wait().succeeded
    second_tasker=Tasker();assert Library.framework().MaaTaskerBindResource(second_tasker._handle,other._handle)
    assert second_tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='Offline'),image).wait().succeeded
    assert out[-1]['tag']=='B' and out[-1]['hit']  # callback ran; A's override did not leak.
    if cache:
        assert cache.stats['hits']-before['hits']==2
        assert cache.stats['misses']-before['misses']==3
