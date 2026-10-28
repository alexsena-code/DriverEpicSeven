"""Preserve each native calibration while sharing semantic matches/states."""
import json
from types import SimpleNamespace

import numpy as np
from PIL import Image

from driver_epic_seven.vision import Vision, classify


def test_only_a_complete_specific_composition_supersedes_its_generic_shell():
    states={'ready':{'all':['shell']},'own_team':{'all':['shell','team'],'supersedes':['ready']}}
    assert classify({'shell':{'hit':True},'team':{'hit':True}},states)=='own_team'
    assert classify({'shell':{'hit':True},'team':{'hit':False}},states)=='ready'
    assert classify({'shell':{'hit':True},'team':{'hit':True}},
        {**states,'unrelated':{'all':['shell']}})=='unknown'


def test_bright_caption_guard_rejects_legible_but_dimmed_ocr(tmp_path):
    v=vision(tmp_path,{}, {}, {'notice':{'all':['close']}})
    v.spec['ocr']={'close':{'node':'Caption','expected':'Tap to close','min_score':.9,
                          'bright_glyph_min':180,'min_bright_pixels':8}}
    row=SimpleNamespace(box=[0,0,4,4],score=.99,text='Tap to close')
    recognize=lambda _:SimpleNamespace(filtered_results=[row])
    assert v.inspect(np.full((4,4,3),230,np.uint8),recognize)['state']=='notice'
    assert v.inspect(np.full((4,4,3),104,np.uint8),recognize)['state']=='unknown'


def test_mapped_ocr_trigger_reads_specific_identity_despite_recognized_shell(tmp_path):
    pixels=np.full((4,4,3),200,np.uint8)
    v=vision(tmp_path,{'shell':{'node':'Shell','template':'shell.png','max_pixel_mae':0}},
        {'shell.png':pixels},{'ready':{'all':['shell']},
        'identified':{'all':['shell','cost'],'supersedes':['ready']}})
    v.spec['ocr']={'cost':{'node':'Cost','expected':'8','min_score':.98}}
    v.spec['ocr_triggers']=[['shell']]
    def recognize(name):
        if name=='Shell':return native([0,0,4,4])
        return SimpleNamespace(filtered_results=[SimpleNamespace(box=[0,0,2,2],score=.99,text='8')])
    assert v.inspect(pixels,recognize)['state']=='identified'
    v.spec['ocr_triggers']=[['not_loaded_in_this_subset']]
    assert v.inspect(pixels,recognize)['state']=='ready'


def native(box,score=.99,*,filtered=True):
    row=SimpleNamespace(box=box,score=score)
    return SimpleNamespace(hit=True,box=box,best_result=row,
                           filtered_results=[row] if filtered else [],all_results=[row])


def vision(tmp_path,templates,images,states=None):
    (tmp_path/'image').mkdir()
    for name,pixels in images.items():
        Image.fromarray(pixels).save(tmp_path/'image'/name)
    path=tmp_path/'vision.json'
    path.write_text(json.dumps({'templates':templates,'states':states or {}}),encoding='utf-8')
    return Vision(path,tmp_path)


def alternatives():
    return {'skip':{'node':'Old.Skip','template':'old.png','max_pixel_mae':5,
                    'alternatives':[{'node':'Current.Skip','template':'current.png','max_pixel_mae':8}]}}


def test_alternative_keeps_its_own_pixels_and_mae_and_rejects_higher_invalid_score(tmp_path):
    old=np.full((4,4,3),200,np.uint8);current=np.full((4,4,3),100,np.uint8)
    v=vision(tmp_path,alternatives(),{'old.png':old,'current.png':current})
    frame=np.concatenate([old-20,current+7],axis=1)
    calls=[]
    def recognize(name):
        calls.append(name)
        return native([0,0,4,4],.999) if name=='Old.Skip' else native([4,0,4,4],.95)
    matched=v.inspect(frame,recognize)['matches']['skip']
    assert matched['hit'] and matched['box']==[4,0,4,4] and matched['pixel_mae']==7
    assert matched['source_node']=='Current.Skip'
    assert not matched['source_matches']['Old.Skip']['hit']
    assert calls==['Old.Skip','Current.Skip']
    assert np.array_equal(v.templates['skip'][0],old)


def test_alternative_mask_does_not_inherit_the_primary_settings(tmp_path):
    old=np.full((4,4,3),200,np.uint8)
    masked=np.full((4,4,3),[0,255,0],np.uint8);masked[0,0]=200
    specs=alternatives();specs['skip']['alternatives'][0].update(max_pixel_mae=0,green_mask=True)
    v=vision(tmp_path,specs,{'old.png':old,'current.png':masked})
    frame=np.zeros((4,8,3),np.uint8);frame[0,4]=200
    result=v.inspect(frame,lambda name:native([0,0,4,4]) if name=='Old.Skip' else native([4,0,4,4]))
    assert result['matches']['skip']['hit']
    assert result['matches']['skip']['pixel_mae']==0


def test_alternative_cannot_rescue_an_unfiltered_native_candidate(tmp_path):
    pixels=np.full((4,4,3),200,np.uint8)
    v=vision(tmp_path,alternatives(),{'old.png':pixels,'current.png':pixels})
    result=v.inspect(pixels,lambda _:native([0,0,4,4],filtered=False))
    assert not result['matches']['skip']['hit']
    assert all(not record['hit'] for record in result['matches']['skip']['source_matches'].values())


def test_state_source_guard_can_use_valid_primary_even_if_alternative_wins(tmp_path):
    pixels=np.full((4,4,3),200,np.uint8)
    states={'story':{'variants':[{'all':['skip'],'source_nodes':{'skip':'Old.Skip'}}]}}
    v=vision(tmp_path,alternatives(),{'old.png':pixels,'current.png':pixels},states)
    result=v.inspect(pixels,lambda name:native([0,0,4,4],.95 if name=='Old.Skip' else .99))
    assert result['matches']['skip']['source_node']=='Current.Skip'
    assert result['state']=='story'


def test_same_native_node_is_recognized_once_per_inspection(tmp_path):
    pixels=np.full((4,4,3),200,np.uint8)
    spec={'node':'Shared.Native','template':'old.png','max_pixel_mae':5}
    v=vision(tmp_path,{'first':spec,'second':spec},{'old.png':pixels})
    calls=[]
    def recognize(node):
        calls.append(node);return native([0,0,4,4])
    assert all(m['hit'] for m in v.inspect(pixels,recognize)['matches'].values())
    assert calls==['Shared.Native']


def story_matches(*,old=False,current=True,history=False,confirm=False):
    return {'skip':{'hit':old or current,'source_node':'Current.Skip',
                    'source_matches':{'Old.Skip':{'hit':old},'Current.Skip':{'hit':current}}},
            'history':{'hit':history},'confirm':{'hit':confirm}}


def story_states():
    return {'story':{'variants':[
        {'all':['skip'],'none':['confirm'],'source_nodes':{'skip':'Old.Skip'}},
        {'all':['skip','history'],'none':['confirm'],'source_nodes':{'skip':'Current.Skip'}}]}}


def test_current_skip_alone_never_borrows_legacy_story_rule():
    states=story_states()
    assert classify(story_matches(),states)=='unknown'
    assert classify(story_matches(history=True),states)=='story'
    assert classify(story_matches(old=True,current=False),states)=='story'
    assert classify(story_matches(old=True,history=True,confirm=True),states)=='unknown'


def test_variants_are_complete_compositions_and_never_union_partial_positives():
    states={'panel':{'variants':[{'all':['a','b']},{'all':['c','d']}]}}
    matches={key:{'hit':key in ('a','c')} for key in 'abcd'}
    assert classify(matches,states)=='unknown'
    matches['b']['hit']=True
    assert classify(matches,states)=='panel'
    matches['d']['hit']=True
    assert classify(matches,states)=='panel'  # Multiple variants are still one state.


def test_source_guards_apply_to_any_and_none_and_keep_state_ambiguity():
    matches={'anchor':{'hit':True},'option':{'hit':True,'source_node':'Current.Option'},
             'overlay':{'hit':True,'source_node':'Other.Overlay'}}
    rule={'all':['anchor'],'any':['option'],'none':['overlay'],
          'source_nodes':{'option':'Current.Option','overlay':'Current.Overlay'}}
    assert classify(matches,{'one':{'variants':[rule]}})=='one'
    assert classify(matches,{'one':{'variants':[rule]},'two':{'all':['anchor']}})=='unknown'
    matches['overlay']['source_node']='Current.Overlay'
    assert classify(matches,{'one':{'variants':[rule]}})=='unknown'
