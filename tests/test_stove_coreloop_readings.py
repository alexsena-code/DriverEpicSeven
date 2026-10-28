"""Current coreloop fields distinguish previews, selection, confirmation and receipts."""
from copy import deepcopy
import json
import numpy as np
from PIL import Image
import pytest
from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree,operation_view,target_box
from driver_epic_seven.vision import Vision


@pytest.mark.fixtures
def test_native_coreloop_readonly_phases_and_preview_negatives(tmp_path):
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.pipeline import JCustomRecognition
    from maa.library import Library
    from maa.define import LoggingLevelEnum
    run=ROOT/'var/runs/20261027T060242Z_390d2724'
    expected={'main':'milestone_main','selector':'coreloop_hero_selector','selected':'coreloop_hero_selector',
       'confirmation':'coreloop_selector_confirmation','obtained':'coreloop_hero_receipt','reward':'coreloop_item_receipt'}
    paths=[(run/f'agent_{n:06}.png',kind) for n,kind in ((6,'main'),(65,'main'),(74,'main'),(49,'selector'),(52,'selected'),(55,'confirmation'),(62,'obtained'),(71,'reward'))]
    paths += [(run/f'agent_{n:06}.png',None) for n in (3,10,16,19,22,26,33,40,46)]
    paths += [(ROOT/'var/runs'/r/f'agent_{n:06}.png',None) for r,n in (('20261027T055624Z_d8a1e216',10),('20261027T034529Z_6b3c4cd0',156),('20261027T012018Z_f4ee88cc',11))]
    if not all(p.exists() for p,_ in paths):pytest.skip('Private coreloop phase evidence unavailable.')
    bundle=ROOT/'resources/epic-seven';vision=Vision(bundle/'vision.json',bundle);out=[]
    class Offline(CustomRecognition):
        def analyze(self,ctx,argv):
            filtered={}
            def recognize(name):
                raw=ctx.run_recognition(name,argv.image)
                if 'Coreloop' in name or 'MilestoneRead' in name:
                    filtered[name]=[{'box':list(r.box),'score':r.score,'text':getattr(r,'text',None)} for r in raw.filtered_results] if raw else []
                return raw
            out.append({'analysis':vision.inspect(argv.image,recognize),'filtered':filtered})
            return self.AnalyzeResult(box=[0,0,1,1],detail=out[-1])
    Tasker.set_stdout_level(LoggingLevelEnum.Off);Tasker.set_log_dir(tmp_path/'maa')
    resource=Resource();resource.set_cpu();resource.register_custom_recognition('CoreloopReadingFixture',Offline())
    assert resource.post_bundle(bundle).wait().succeeded
    tasker=Tasker();assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
    cases=[]
    for path,kind in paths:
        f=np.asarray(Image.open(path).convert('RGB'))[:,:,::-1].copy();cases.append((str(path),path,f,kind))
        if kind:cases.append((str(path)+'/dimmed',path,(f*.45).astype(np.uint8),None))
    for name,path,f,kind in cases:
        before=len(out);assert tasker.post_recognition('Custom',JCustomRecognition(custom_recognition='CoreloopReadingFixture'),f).wait().succeeded
        assert len(out)==before+1
        saved=json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))['result']
        data={**saved,**out[-1]['analysis']};copy=deepcopy(data)
        tree=build_tree(data,vision.spec);v=operation_view({'ui_tree':tree});want=expected.get(kind)
        assert v.get('view')==want if want else v.get('view') not in expected.values(),(name,v)
        if want:
            assert not v['controls'];c=v['items'][0]
            if kind=='main':
                price,balance={6:(0,64),65:(40,64),74:(60,24)}[int(path.stem.split('_')[-1])]
                assert c['claim_cost']==price and c['essence_balance']==balance
                assert c['cost']=={'currency':'to_essence','cost':price,'available':balance}
                for key in ('origin_coin_balance','progress_step','progress_total','claimed_steps','claim_completed','claim_enabled'):
                    assert c[key] is None
                assert tree['nodes']['operation:milestone_main/context']['fields']['claim_cost']['sources'][0]['pointer']=='/matches/milestone_read_cost'
            elif kind in ('selector','selected'):
                assert c['candidate_names']==['Kise','Charles','Tenebria']
                assert c['selected_hero_name']==('Tenebria' if kind=='selected' else None)
                assert c['received_hero_name'] is None and c['receive_enabled'] is None
            elif kind=='confirmation':
                assert c['proposed_hero_name']=='Tenebria' and c['decision_irreversible'] is True
                assert c['confirmation_sent'] is None and c['received_hero_name'] is None
            elif kind=='obtained':
                assert c['received_hero_name']=='Tenebria' and c['acquisition_announced'] is True
                assert c['owned_instance_id'] is None and c['complete_roster'] is None
            elif kind=='reward':
                assert c['reward_name']=='Rare Catalyst Selection Chest' and c['reward_quantity']==16
                assert c['inventory_total'] is None and c['chest_opened'] is None
            for key in data['matches']:
                if key.startswith(('milestone_read','coreloop_')):assert target_box(tree,key) is None
        assert data==copy
        if kind=='main' and path.name=='agent_000006.png':
            for mutation in ('duplicate','low_score','not_hit','wrong_window','wrong_title'):
                changed=deepcopy(data);m=changed['matches']['milestone_read_cost']
                if mutation=='duplicate':m['filtered_candidates']*=2
                elif mutation=='low_score':m['score']=.97
                elif mutation=='not_hit':m['hit']=False
                elif mutation=='wrong_window':changed['window']['process_name']='Other.exe'
                else:next(r for r in changed['text'] if r['text']=='Dawning Trajectory')['text']='Other track'
                v2=operation_view({'ui_tree':build_tree(changed,vision.spec)})
                if mutation=='wrong_window':assert v2.get('view')!='milestone_main'
                elif mutation=='wrong_title':
                    assert v2['view']=='milestone_main' and v2['items'][0]['track_label']=='Other track'
                else:
                    assert v2['items'][0]['claim_cost'] is None and v2['items'][0]['cost'] is None
                    assert v2['items'][0]['essence_balance']==64
    (tmp_path/'coreloop-reading-replay.json').write_text(json.dumps([
        {'case':c[0],'expected':c[3],**a} for c,a in zip(cases,out)],indent=2),encoding='utf-8')
