"""Equipment evidence uses current attributes, materials and active native regions."""
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree,operation_view
from test_operational_ui_equipment import saved,EQUIPMENT


@pytest.mark.fixtures
def test_preview_attributes_survive_missing_cp_and_partial_hero_attributes_stay_readable():
    d=saved(EQUIPMENT,48)
    d['text']=[r for r in d['text'] if not (255<=r['box'][1]<=280 and 475<=r['box'][0]<=860)]
    view=operation_view({'ui_tree':build_tree(d)});c=view['items'][0]
    assert view['view']=='equip_all_preview' and c['current_cp'] is None and c['candidate_cp'] is None
    assert c['current_attributes']=={'attack':1244,'defense':553,'health':5798}
    assert c['candidate_attributes']=={'attack':3770,'defense':769,'health':11906}
    c=operation_view({'ui_tree':build_tree(saved(EQUIPMENT,55))})['items'][0]
    assert c['attributes']=={'attack':3770,'defense':None,'health':11906}


@pytest.mark.fixtures
def test_fee_is_unknown_without_native_confirmation_and_never_inferred_from_cp():
    d=saved(EQUIPMENT,51);assert operation_view({'ui_tree':build_tree(d)})['items'][0]['gold_cost'] is None
    d['matches']['equipment_free_change']={'hit':True,'box':[614,472,227,59]}
    assert operation_view({'ui_tree':build_tree(d)})['items'][0]['gold_cost']==0


@pytest.mark.fixtures
def test_current_reserved_materials_need_slot_count_and_unambiguous_quantity():
    p=ROOT/'var/wave2/replay-agent_000008.json'
    if not p.exists():pytest.skip('Private material replay unavailable.')
    d=json.loads(p.read_text(encoding='utf-8'));d.pop('ui_tree',None)
    c=operation_view({'ui_tree':build_tree(d)})['items'][0]
    assert c['item_name']=='Hellish Essence Orb' and c['gold_cost']==22400 and c['gold_balance']==1383934
    assert c['selected_materials']==[{'name':'Equipment Enhancement Powder','remaining':31,'available':36,'quantity':5},
                                    {'name':'Lesser Equipment Charm','remaining':1,'available':2,'quantity':1}]
    assert c['material_selection_complete'] is True
    for variant in ('empty','quantity','name','duplicate'):
        changed=deepcopy(d)
        if variant=='empty':changed['matches']['equipment_material_empty_3']['hit']=False
        if variant=='quantity':changed['text']=[r for r in changed['text'] if r['text']!='31(-5)']
        if variant=='name':changed['text']=[r for r in changed['text'] if r['text']!='Enhancement Powder']
        if variant=='duplicate':changed['text'].append({'text':'30(-6)','box':[1114,166,61,24],'score':.99})
        c=operation_view({'ui_tree':build_tree(changed)})['items'][0]
        assert c['selected_materials'] is None and c['material_selection_complete'] is False


@pytest.mark.fixtures
def test_native_material_and_fee_controls_with_opposite_screens_and_dimmed_negatives(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.library import Library
    from maa.pipeline import JCustomRecognition
    from maa.define import LoggingLevelEnum
    from driver_epic_seven.vision import Vision
    from driver_epic_seven.stages import StageInspector
    from driver_epic_seven.operational_equipment import augment_text
    run=ROOT/'var/runs/20261028T112001Z_b231004c'
    cases=[(run/'agent_000004.png',5,False),(run/'agent_000008.png',3,False),
           (ROOT/'var/runs'/EQUIPMENT/'agent_000051.png',0,True),
           (ROOT/'var/runs'/EQUIPMENT/'agent_000055.png',0,False),
           (ROOT/'var/runs/20261028T220210Z_addb9574/path_after.png',3,False),
           (ROOT/'var/runs/20261028T220210Z_addb9574/observation.png',3,False)]
    if not all(p.exists() for p,_,_ in cases):pytest.skip('Private native equipment fixtures unavailable.')
    bundle=ROOT/'resources/epic-seven';vision=Vision(bundle/'vision.json',bundle);out=[]
    class Offline(CustomRecognition):
        def analyze(self,ctx,argv):
            a=vision.inspect(argv.image,lambda n:ctx.run_recognition(n,argv.image))
            a['text']=StageInspector._ocr(lambda k,p:ctx.run_recognition_direct(k,p,argv.image),(0,0,1212,682))
            augment_text(a,lambda k,p:ctx.run_recognition_direct(k,p,argv.image))
            a['window']={'process_name':'EpicSeven.exe','client_size':[1212,682]};out.append(a)
            return self.AnalyzeResult(box=[0,0,1,1],detail=a)
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('EquipmentOperationFixture',Offline())
    assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    diagnostics=[]
    for path,count,fee in cases:
        frame=np.asarray(Image.open(path).convert('RGB'))[:,:,::-1].copy()
        for dimmed in (False,True):
            pixels=(frame*.4).astype(np.uint8) if dimmed else frame
            assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='EquipmentOperationFixture'),pixels).wait().succeeded
            a=out[-1];m=a['matches'];empty=sum(m['equipment_material_empty_'+str(i)]['hit'] for i in range(1,6))
            assert empty==(0 if dimmed else count),(str(path),m)
            assert m['equipment_free_change']['hit'] is (fee and not dimmed)
            view=operation_view({'ui_tree':build_tree(a,vision.spec)})
            if not dimmed and path.name=='agent_000008.png':assert view['items'][0]['material_selection_complete'] is True
            if not dimmed and path.name=='agent_000004.png':assert view['view']=='equipment_auto_select' and len(view['controls'])==5
            diagnostics.append({'source':str(path),'dimmed':dimmed,'view':view})
    (tmp_path/'equipment-native.json').write_text(json.dumps(diagnostics,indent=2),encoding='utf-8')
