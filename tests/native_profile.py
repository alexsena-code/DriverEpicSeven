"""Opt-in pytest measurements; never imported by the production driver."""
from collections import defaultdict
from contextlib import contextmanager
from functools import wraps
import ctypes
import hashlib
import json
import os
from pathlib import Path
import platform
import threading
import time


def process_metrics():
    result={'cpu_seconds':time.process_time(),'python_threads':threading.active_count()}
    if os.name=='nt':
        from ctypes import wintypes as w
        class Memory(ctypes.Structure):
            _fields_=[('cb',w.DWORD),('faults',w.DWORD)]+[(n,ctypes.c_size_t) for n in
                ('peak_working_set','working_set','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile')]
        kernel=ctypes.WinDLL('kernel32');psapi=ctypes.WinDLL('psapi')
        kernel.GetCurrentProcess.restype=w.HANDLE
        psapi.GetProcessMemoryInfo.argtypes=[w.HANDLE,ctypes.POINTER(Memory),w.DWORD]
        memory=Memory();memory.cb=ctypes.sizeof(memory)
        if psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(memory),memory.cb):
            result.update(working_set_bytes=memory.working_set,peak_working_set_bytes=memory.peak_working_set)
        class Entry(ctypes.Structure):
            _fields_=[('size',w.DWORD),('usage',w.DWORD),('id',w.DWORD),('owner',w.DWORD),
                      ('priority',w.LONG),('delta',w.LONG),('flags',w.DWORD)]
        kernel.CreateToolhelp32Snapshot.argtypes=[w.DWORD,w.DWORD];kernel.CreateToolhelp32Snapshot.restype=w.HANDLE
        kernel.Thread32First.argtypes=kernel.Thread32Next.argtypes=[w.HANDLE,ctypes.POINTER(Entry)]
        kernel.CloseHandle.argtypes=[w.HANDLE]
        handle=kernel.CreateToolhelp32Snapshot(4,0)
        if handle!=ctypes.c_void_p(-1).value:
            entry=Entry();entry.size=ctypes.sizeof(entry);count=0
            found=kernel.Thread32First(handle,ctypes.byref(entry))
            while found:
                count+=entry.owner==os.getpid()
                found=kernel.Thread32Next(handle,ctypes.byref(entry))
            kernel.CloseHandle(handle);result['native_threads']=count
    return result


def file_manifest(paths):
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths)) if p.is_file()}


class NativeProfile:
    def __init__(self,output):
        self.output=Path(output);self.current='session';self.phase='collection'
        self.stats=defaultdict(lambda:defaultdict(lambda:{'calls':0,'seconds':0.0}))
        self.reports=defaultdict(dict);self.frames=defaultdict(lambda:{'visits':0,'native_calls':0,'native_seconds':0.0})
        self.originals=[];self.lock=threading.RLock();self.local=threading.local();self.spans=defaultdict(list)
        self.start=time.perf_counter();self.started_epoch=time.time();self.before=process_metrics()

    @contextmanager
    def measure(self,label):
        started=time.perf_counter();key=self.current+'/'+self.phase
        try:yield
        finally:
            with self.lock:
                elapsed=time.perf_counter()-started
                row=self.stats[key][label];row['calls']+=1;row['seconds']+=elapsed
                self.spans[key].append((started,started+elapsed))
                frame=getattr(self.local,'frame',None)
                if frame and label.startswith('recognition.'):
                    self.frames[self.current+'/'+frame]['native_calls']+=1
                    self.frames[self.current+'/'+frame]['native_seconds']+=elapsed

    def wrap(self,owner,name,label,tag_job=None):
        original=getattr(owner,name);self.originals.append((owner,name,original))
        @wraps(original)
        def measured(*args,**kwargs):
            chosen=label(*args,**kwargs) if callable(label) else label
            with self.measure(chosen):result=original(*args,**kwargs)
            if tag_job:result._test_profile_kind=tag_job
            return result
        setattr(owner,name,measured)

    def install(self):
        from maa.context import Context
        from maa.job import Job
        from maa.resource import Resource
        from maa.tasker import Tasker
        from driver_epic_seven.vision import Vision
        from driver_epic_seven import observed_ui
        for owner in (Resource,Tasker):
            self.wrap(owner,'__init__',lambda obj,*a,owner=owner,**k:
                      owner.__name__+('.wrap_borrowed_handle' if (a and a[0]) or k.get('handle') else '.create'))
        self.wrap(Vision,'__init__','Vision.create')
        self.wrap(Resource,'post_bundle','resource.post_bundle',tag_job='bundle')
        self.wrap(Tasker,'post_recognition','tasker.post_recognition',tag_job='recognition')
        self.wrap(Tasker,'post_task','tasker.post_task',tag_job='task')
        self.wrap(Job,'wait',lambda job,*a,**k:'job.wait.'+getattr(job,'_test_profile_kind','other'))
        self.wrap(Context,'run_recognition',lambda ctx,name,*a,**k:'recognition.node:'+name)
        self.wrap(Context,'run_recognition_direct',lambda ctx,kind,*a,**k:'recognition.direct:'+str(kind))
        self.wrap(observed_ui,'build_tree','ui_tree.build')
        original=Vision.inspect;self.originals.append((Vision,'inspect',original))
        @wraps(original)
        def inspect(vision,frame,matcher):
            if frame is None:
                with self.measure('vision.inspect'):return original(vision,frame,matcher)
            before=getattr(self.local,'frame',None)
            identity=hashlib.sha256(frame.tobytes()).hexdigest()
            self.local.frame=identity;self.frames[self.current+'/'+identity]['visits']+=1
            try:
                with self.measure('vision.inspect'):return original(vision,frame,matcher)
            finally:self.local.frame=before
        Vision.inspect=inspect

    def close(self,config,exitstatus):
        for owner,name,original in reversed(self.originals):setattr(owner,name,original)
        from driver_epic_seven.config import ROOT
        from maa.library import Library
        files=[*ROOT.glob('tests/*.py'),*ROOT.glob('src/driver_epic_seven/*.py'),ROOT/'pyproject.toml']
        corpus=[*ROOT.glob('tests/fixtures/local/*'),*ROOT.glob('var/runs/**/agent_*.png')]
        resource=ROOT/'resources/epic-seven'
        result={'schema_version':1,'selection':list(config.args),'command':list(config.invocation_params.args),
                'started_epoch_seconds':self.started_epoch,'exitstatus':int(exitstatus),
                'elapsed_seconds':time.perf_counter()-self.start,'before':self.before,'after':process_metrics(),
                'environment':{'python':platform.python_version(),'pytest':__import__('pytest').__version__,
                               'maa':Library.version(),'logical_cpus':os.cpu_count()},
                'source_sha256':file_manifest(files),
                'corpus_sha256':file_manifest(corpus),
                'resource_sha256':file_manifest([*resource.glob('pipeline/*.json'),*resource.glob('image/*'),
                    *resource.glob('model/ocr/en_us/*'),resource/'vision.json',resource/'default_pipeline.json']),
                'reports':dict(self.reports),'measurements':{k:dict(v) for k,v in self.stats.items()},
                'frames':dict(self.frames),'python_asserts_and_uninstrumented_seconds':{},
                'cache':getattr(self,'cache_report',{'mode':'not_installed'}),
                'timing_note':'Instrumented durations are inclusive/nested; do not sum them as disjoint costs.'}
        for key,spans in self.spans.items():
            test,phase=key.rsplit('/',1);duration=self.reports.get(test,{}).get(phase,{}).get('seconds')
            if duration is None:continue
            union=0;end=0
            for a,b in sorted(spans):
                union+=max(0,b-max(a,end));end=max(end,b)
            result['python_asserts_and_uninstrumented_seconds'][key]=max(0,duration-union)
        self.output.parent.mkdir(parents=True,exist_ok=True)
        self.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
