"""Bounded exact-input memoization for offline tests, never for Runtime.

Native Resource/Tasker instances and callbacks remain owned by each test. Only
pure TemplateMatch/OCR result values can cross tests, through serialized copies.
"""
from collections import OrderedDict
from dataclasses import asdict, is_dataclass
from functools import wraps
import hashlib
import json
from pathlib import Path
import pickle
import threading


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,default=str,separators=(',',':')).encode()).hexdigest()


def bundle_signature(path):
    """Content, not mtimes: called at each independent bundle load/binding."""
    root=Path(path)
    files=[*root.glob('pipeline/*.json'),*root.glob('image/**/*'),*root.glob('model/**/*'),
           root/'vision.json',root/'default_pipeline.json']
    rows=[]
    for file in sorted(set(files)):
        if file.is_file():rows.append((str(file.relative_to(root)),hashlib.sha256(file.read_bytes()).hexdigest()))
    return digest(rows)


def frame_signature(frame):
    return (frame.shape,str(frame.dtype),hashlib.sha256(frame.tobytes()).hexdigest())


class FixtureCache:
    def __init__(self,max_bytes=256*1024*1024):
        self.max_bytes=max_bytes;self.bytes=0;self.entries=OrderedDict();self.lock=threading.RLock()
        self.stats={'hits':0,'misses':0,'bypassed':0,'evictions':0,'native_positive':0,'native_negative':0}
        self.resources={};self.originals=[];self.local=threading.local()

    def read(self,key,compute):
        with self.lock:
            if key in self.entries:
                self.stats['hits']+=1;value=self.entries.pop(key);self.entries[key]=value
                return pickle.loads(value)
        result=compute()
        with self.lock:
            self.stats['misses']+=1
            # None can mean an engine/setup error; do not persist that failure.
            if result is None:return result
            self.stats['native_positive' if result.hit else 'native_negative']+=1
            value=pickle.dumps(result,protocol=pickle.HIGHEST_PROTOCOL)
            if len(value)<=self.max_bytes:
                if key in self.entries:self.bytes-=len(self.entries.pop(key))
                self.entries[key]=value;self.bytes+=len(value)
                while self.bytes>self.max_bytes:
                    _,removed=self.entries.popitem(last=False);self.bytes-=len(removed);self.stats['evictions']+=1
        return result

    def key(self,frame,environment,node,configuration=None):
        current=getattr(self.local,'frame',None)
        pixels=current[1] if current and current[0] is frame else frame_signature(frame)
        return digest([pixels,environment,node,configuration,getattr(self.local,'vision',None)])

    def replace(self,owner,name,wrapper):
        original=getattr(owner,name);self.originals.append((owner,name,original))
        setattr(owner,name,wrapper(original))

    def environment(self,ctx):
        scope=getattr(self.local,'environments',None)
        if scope is not None and id(ctx) in scope and scope[id(ctx)][0] is ctx:
            environment=scope[id(ctx)][1]
            return None if environment and environment['inference']=='unverified' else environment
        resource=ctx.tasker.resource
        environment=self.resources.get(int(resource._handle))
        if environment and environment['inference']=='unverified':environment=None
        if scope is not None:scope[id(ctx)]=(ctx,environment)
        return environment

    def install(self):
        from maa.context import Context
        from maa.resource import Resource
        from maa.controller import Win32Controller
        from maa.library import Library
        from driver_epic_seven.vision import Vision
        version=Library.version()

        def resource_created(original):
            @wraps(original)
            def created(resource,*args,**kwargs):
                result=original(resource,*args,**kwargs)
                if resource._own:self.resources[int(resource._handle)]={'sdk':version,'bundles':[],'inference':'default'}
                return result
            return created

        def loaded(original):
            @wraps(original)
            def load(resource,path,*args,**kwargs):
                signature=bundle_signature(path)
                job=original(resource,path,*args,**kwargs)
                env=self.resources.get(int(resource._handle))
                if env is not None:env['bundles'].append(signature)
                return job
            return load

        def inference(original):
            @wraps(original)
            def configure(resource,*args,**kwargs):
                result=original(resource,*args,**kwargs)
                env=self.resources.get(int(resource._handle))
                if env is not None:env['inference']=[args,kwargs] if result else 'unverified'
                return result
            return configure

        def inspect(original):
            @wraps(original)
            def read(vision,frame,matcher):
                if frame is None:return original(vision,frame,matcher)
                previous=(getattr(self.local,'frame',None),getattr(self.local,'vision',None),getattr(self.local,'environments',None))
                arrays=[frame_signature(image) for images in vision.templates.values() for image in images]
                arrays.extend(frame_signature(image) for variants in getattr(vision,'_alternative_templates',{}).values()
                              for images in variants for image in images)
                self.local.frame=(frame,frame_signature(frame));self.local.vision=digest([vision.spec,arrays])
                self.local.environments={}
                try:return original(vision,frame,matcher)
                finally:self.local.frame,self.local.vision,self.local.environments=previous
            return read

        def recognition(original):
            @wraps(original)
            def read(ctx,name,image,pipeline_override=None):
                environment=self.environment(ctx)
                node=ctx.get_node_data(name)
                spec=(node or {}).get('recognition',{})
                kind=spec.get('type') if isinstance(spec,dict) else spec
                # Named geometry, anchors and arbitrary custom recognizers are
                # context dependent. Only the current fixed-region pure nodes
                # are eligible; per-call overrides bypass this cache entirely.
                parameters=spec.get('param',{}) if isinstance(spec,dict) else node or {}
                if not environment or pipeline_override or kind not in ('TemplateMatch','OCR') or isinstance(parameters.get('roi'),str):
                    self.stats['bypassed']+=1
                    return original(ctx,name,image,pipeline_override)
                return self.read(self.key(image,environment,node),lambda:original(ctx,name,image,pipeline_override))
            return read

        def direct(original):
            @wraps(original)
            def read(ctx,kind,params,image):
                environment=self.environment(ctx)
                values=asdict(params) if is_dataclass(params) else params
                if not environment or str(kind) not in ('OCR','TemplateMatch') or isinstance(values.get('roi'),str):
                    self.stats['bypassed']+=1;return original(ctx,kind,params,image)
                key=self.key(image,environment,{'direct':str(kind),'parameters':values})
                return self.read(key,lambda:original(ctx,kind,params,image))
            return read

        def forbid_live(original):
            @wraps(original)
            def rejected(*args,**kwargs):
                raise AssertionError('Offline fixture caching must never connect a Win32 game controller.')
            return rejected

        self.replace(Resource,'__init__',resource_created)
        self.replace(Resource,'post_bundle',loaded)
        self.replace(Resource,'set_inference',inference)
        self.replace(Vision,'inspect',inspect)
        self.replace(Context,'run_recognition',recognition)
        self.replace(Context,'run_recognition_direct',direct)
        self.replace(Win32Controller,'__init__',forbid_live)

    def close(self):
        for owner,name,original in reversed(self.originals):setattr(owner,name,original)
        self.originals=[]


def transition_overrides(definitions,overrides=None):
    """Remove waiting only in fixture simulations; preserve every gesture."""
    from copy import deepcopy
    result={}
    for name,definition in definitions.items():
        if name.startswith('$'):continue
        node=deepcopy(definition);node.update(deepcopy((overrides or {}).get(name,{})))
        node.update(timeout=1500,pre_delay=0,post_delay=0,rate_limit=1,
                    pre_wait_freezes={'time':0},post_wait_freezes={'time':0},repeat_wait_freezes={'time':0})
        result[name]=node
    return result
