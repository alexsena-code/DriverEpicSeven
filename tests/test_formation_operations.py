from copy import deepcopy
from pathlib import Path
import time
import pytest

from driver_epic_seven.observed_ui import build_tree,formation_view,operation_view
from driver_epic_seven.formation_operations import graph,target
from driver_epic_seven.config import ROOT


def observation():
    d={'state':'battle_ready','window':{'pid':1,'client_size':[1212,682]},'epoch_seconds':time.time(),
       'text':[{'text':t,'box':b,'score':.99} for t,b in [('Ready',[60,17,70,31]),('Episode Team',[10,90,110,20]),
        ('50',[363,125,20,20]),('60',[239,195,20,20]),('42',[500,167,20,20]),('19',[393,269,20,20])]],
       'matches':{'formation_remove':{'hit':True,'box':[342,248,42,19]},'formation_details':{'hit':True,'box':[429,240,38,39]},
                  'formation_swap_right':{'hit':True,'box':[507,308,47,48]}}}
    d['ui_tree']=build_tree(d);return d


def test_formation_blocks_preparation_only_with_current_overlay_and_preserves_unknowns():
    d=observation();f=formation_view(d)
    assert f['selected_position']=='upper' and operation_view(d)=={}
    info=f['items'][0]
    assert info['member_instance_id'] is None and info['candidate_name'] is None and info['selection_applied'] is None
    normal=deepcopy(d);normal.pop('ui_tree');normal['matches']={};normal['ui_tree']=build_tree(normal)
    assert formation_view(normal)['view']=='formation'
    assert next(n for n in normal['ui_tree']['nodes'].values() if n['id']=='formation:selection')['fields']['blocks_preparation']['value'] is False
    for state in ('hero_screen','stage_clear','battle_running'):
        changed=deepcopy(d);changed.pop('ui_tree');changed['state']=state;changed['ui_tree']=build_tree(changed)
        assert formation_view(changed)=={}


def test_mutation_requires_current_selected_source_verified_identity_and_native_destination():
    d=observation();p={'kind':'formation_reposition','task_id':'scope','source':'upper','destination':'right','member_name':'Any Observed Hero'}
    ticket={'formation:scope':{'epoch_seconds':time.time(),'window':d['window'],'member_name':p['member_name'],'identity_verified':True}}
    assert target(d,p,ticket)==[507,308,47,48]
    assert target(d,p,{}) is None
    for key,value in [('identity_verified',False),('member_name','Other'),('epoch_seconds',time.time()-181),('window',{'pid':2})]:
        changed=deepcopy(ticket);changed['formation:scope'][key]=value;assert target(d,p,changed) is None
    assert target(d,{**p,'source':'left'},ticket) is None
    changed=deepcopy(d);changed.pop('ui_tree');changed['matches'].pop('formation_swap_right');changed['ui_tree']=build_tree(changed)
    assert target(changed,p,ticket) is None


def test_graphs_are_finite_separate_selection_and_application_and_never_start_battle():
    for op in ('select','reposition','remove','assign','substitute'):
        nodes,entry,success=graph('arbitrary objective',op,source='left',destination='right',member_name='A New Hero')
        assert nodes[entry]['action']=='DoNothing' and success in nodes
        consumers=[n for n in nodes.values() if n.get('custom_recognition_param',{}).get('path',{}).get('consuming')]
        assert len(consumers)==(0 if op=='select' else 1)
        assert all(n.get('max_hit',1)==1 for n in consumers)
        assert not any('start' in str(n.get('custom_recognition_param',{})).lower() for n in nodes.values())
    with pytest.raises(ValueError):graph('scope','remove',source='upper',member_name='Hero')
    with pytest.raises(ValueError):graph('scope','reposition',source='left',destination='left',member_name='Hero')
    with pytest.raises(ValueError):graph('scope','assign',destination='right')


@pytest.mark.native
@pytest.mark.fixtures
def test_native_formation_controls_and_opposite_panels(tmp_path):
    import numpy as np
    from PIL import Image
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.library import Library
    from maa.custom_recognition import CustomRecognition
    from maa.pipeline import JCustomRecognition
    from maa.define import LoggingLevelEnum
    from driver_epic_seven.vision import Vision
    from driver_epic_seven.stages import StageInspector
    from driver_epic_seven.operational_formation import augment_text
    bundle=ROOT/'resources/epic-seven';v=Vision(bundle/'vision.json',bundle);out=[]
    class Read(CustomRecognition):
        def analyze(self,ctx,argv):
            a=v.inspect(argv.image,lambda n:ctx.run_recognition(n,argv.image))
            a['text']=StageInspector._ocr(lambda k,p:ctx.run_recognition_direct(k,p,argv.image),(0,0,1212,682))
            augment_text(a,lambda k,p:ctx.run_recognition_direct(k,p,argv.image))
            from driver_epic_seven.operational_altar import augment_text as augment_altar
            augment_altar(a,lambda k,p:ctx.run_recognition_direct(k,p,argv.image))
            a['window']={'process_name':'EpicSeven.exe','client_size':[1212,682]};out.append(a)
            return self.AnalyzeResult(box=[0,0,1,1],detail=a)
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa');r=Resource();r.set_cpu();r.register_custom_recognition('FormationFixture',Read())
    assert r.post_bundle(bundle).wait().succeeded;t=Tasker();assert Library.framework().MaaTaskerBindResource(t._handle,r._handle)
    cases=[('20261026T201921Z_d656a3d9','agent_000033.png','left',None),
           ('20261026T201921Z_d656a3d9','agent_000036.png',None,'Muwi'),
           ('20261026T201921Z_d656a3d9','agent_000039.png',None,'Muwi'),
           ('20261026T192147Z_72af049c','agent_000048.png','upper','Brieg'),
           ('20261028T220210Z_addb9574','agent_000002.png',None,None),
           ('20261028T222221Z_82265018','agent_000020.png',None,None),
           ('20261028T223039Z_22d10fc2','013_Formation.Mutate.png','right','Arbiter Vildred')]
    for run,file,selected,name in cases:
        path=ROOT/'var/runs'/run/file
        if not path.exists():pytest.skip('Private calibration frame unavailable: '+str(path))
        frame=np.array(Image.open(path).convert('RGB'))[:,:,::-1].copy()
        for dimmed in (False,True):
            pixels=(frame*.4).astype(np.uint8) if dimmed else frame
            assert t.post_recognition('Custom',JCustomRecognition(custom_recognition='FormationFixture'),pixels).wait().succeeded
            a=out[-1];f=formation_view({'ui_tree':build_tree(a,v.spec)})
            if dimmed or run in ('20261028T220210Z_addb9574','20261028T222221Z_82265018'):assert not f,(run,file,dimmed,a['state'])
            if not dimmed and run=='20261028T222221Z_82265018':
                hub=operation_view({'ui_tree':build_tree(a)});assert any(c['semantic_id']=='open_difficulty:normal' for c in hub['controls'])
            if dimmed or run in ('20261028T220210Z_addb9574','20261028T222221Z_82265018'):continue
            else:
                assert f['selected_position']==selected
                assert f['items'][0]['candidate_name']==name
                assert operation_view({'ui_tree':build_tree(a,v.spec)})=={}
                if file=='agent_000036.png':assert f['items'][0]['empty_position']=='left'
                if file=='agent_000039.png':assert {'assign:left','swap:upper','swap:right','swap:lower'}<={c['semantic_id'] for c in f['controls']}


def test_finish_formation_never_repeats_mutation_or_candidate_application():
    nodes,entry,success=graph('scope','reposition',source='right',destination='upper',member_name='Hero',finish=True)
    assert not any(n.get('custom_recognition_param',{}).get('path',{}).get('consuming') for n in nodes.values())
    assert 'Formation.Mutate' not in nodes and 'Formation.Source' not in nodes
    assert success=='Formation.Returned'
