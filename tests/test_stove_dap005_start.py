"""One explicit preparation identity permits the current OCR Start box only."""
import json,re
import numpy as np
from PIL import Image
import pytest
from driver_epic_seven.config import ROOT
from driver_epic_seven.vision import Vision
from driver_epic_seven.observed_ui import build_tree,target_box


def test_dap005_target_is_bound_to_identity_ready_and_payable_cost():
    spec=json.loads((ROOT/'resources/epic-seven/vision.json').read_text(encoding='utf-8'))
    assert spec['target_states']['dap005_start_quest']==['prequel_preparation_dap005']
    required={'prequel_ready_header','dap005_preparation_identity','dap005_location','dap005_stage_title','dap005_energy_cost','dap005_start_quest'}
    assert set(spec['states']['prequel_preparation_dap005']['all'])==required
    expected=spec['ocr']['dap005_energy_cost']['expected']
    assert all(re.fullmatch(expected,s) for s in ('8/8','8/9','8/163','8 / 164'))
    assert not any(re.fullmatch(expected,s) for s in ('8/7','8/0','9/163','0/163','163/150','8/','8/163 9'))
    for state in ('unknown','prequel_preparation','prequel_ready_map','story'):
        tree=build_tree({'state':state,'matches':{'dap005_start_quest':{'hit':True,'box':[1032,614,102,24],'text':'Start Quest'}},
                         'window':{'process_name':'EpicSeven.exe','client_size':[1212,682]}},spec)
        assert target_box(tree,'dap005_start_quest') is None


@pytest.mark.fixtures
def test_native_dap005_start_current_text_and_required_context(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    run=ROOT/'var/runs/20261027T032805Z_f1bed6a4'
    paths=[(run/f'agent_{n:06}.png',True) for n in (25,28,33)]
    paths += [(run/'primitive_rejected.png',True),(run/'agent_000022.png',False),(run/'agent_000020.png',False),
              (ROOT/'var/runs/20261027T031057Z_dcdc3935/agent_000019.png',False)]
    paths += [(ROOT/'var/runs/20261027T024311Z_f1c0e142'/f'agent_{n:06}.png',False) for n in (63,66,69)]
    if not all(p.exists() for p,_ in paths):pytest.skip('Private scoped dap005 start evidence unavailable.')
    bundle=ROOT/'resources/epic-seven';vision=Vision(bundle/'vision.json',bundle);out=[]
    class Offline(CustomRecognition):
        def analyze(self,ctx,argv):
            filtered={}
            def recognize(name):
                raw=ctx.run_recognition(name,argv.image)
                if '.Dap005' in name:
                    filtered[name]=[{'box':list(r.box),'score':getattr(r,'score',None),'text':getattr(r,'text',None)}
                                    for r in raw.filtered_results] if raw else []
                return raw
            a=vision.inspect(argv.image,recognize)
            tree=build_tree({**a,'window':{'process_name':'EpicSeven.exe','client_size':[1212,682]}},vision.spec)
            out.append({'analysis':a,'target':target_box(tree,'dap005_start_quest'),'filtered':filtered})
            return self.AnalyzeResult(box=[0,0,1,1],detail=out[-1])
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('Dap005StartFixture',Offline())
    assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    cases=[]
    for p,want in paths:
        frame=np.asarray(Image.open(p).convert('RGB'))[:,:,::-1].copy();cases.append((str(p),frame,want))
        if p==run/'agent_000025.png':
            cases.append((str(p)+'/dimmed',(frame*.45).astype(np.uint8),False))
            for label,(x,y,w,h) in [('location',(870,70,190,36)),('title',(870,108,220,38)),
                    ('cost',(920,605,90,40)),('start',(1028,610,111,31)),('ready',(45,5,110,55))]:
                altered=frame.copy();altered[y:y+h,x:x+w]=0;cases.append((str(p)+'/missing_'+label,altered,False))
    for name,frame,want in cases:
        before=len(out)
        assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='Dap005StartFixture'),frame).wait().succeeded
        assert len(out)==before+1
        a=out[-1]
        assert bool(a['target']) is want,(name,a)
        if want:
            assert a['analysis']['state']=='prequel_preparation_dap005'
            assert a['target']==a['analysis']['matches']['dap005_start_quest']['box']
            assert a['analysis']['matches']['dap005_energy_cost']['text']=='8/163'
            assert all(len(rows)==1 for rows in a['filtered'].values())
    (tmp_path/'dap005-start-replay.json').write_text(json.dumps([
        {'case':c[0],'expected':c[2],**a} for c,a in zip(cases,out)],indent=2),encoding='utf-8')
