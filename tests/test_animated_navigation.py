"""Animation may change the background, never the current navigation target."""
from copy import deepcopy
import json
from types import SimpleNamespace
import time

import numpy as np
from PIL import Image
import pytest

from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree, operation_view
from driver_epic_seven.input_guards import navigation_proof, navigation_arrived
from driver_epic_seven.runtime import Runtime


WINDOW={'hwnd':1,'pid':2,'process_name':'EpicSeven.exe','window_title':'Epic Seven',
        'window_class':'GLFW30','client_size':[1212,682]}


def lobby():
    rows=[('Rank.8',[100,43,65,22]),('Hero',[914,635,40,20])]
    rows += [(t,[1045,y,130,30]) for t,y in (
        ('Episode',160),('Side Story',230),('Battle',295),('Arena',360),('Summon',420),('Shop',475))]
    return {'state':'unknown','window':deepcopy(WINDOW),'matches':{},'epoch_seconds':time.time(),
            'text':[{'text':t,'box':b,'score':.99} for t,b in rows]}


def frames(data):
    previous=np.zeros((682,1212,3),dtype=np.uint8)+20
    current=np.zeros_like(previous)+90
    for row in data['text']:
        x,y,w,h=row['box']
        previous[y:y+h,x:x+w]=20;current[y:y+h,x:x+w]=20
        previous[y+3:y+7,x+3:x+w-3]=255;current[y+3:y+7,x+3:x+w-3]=255
    return previous,current


def proof(data,current_data,previous,current,action='click',point=(934,645),key=None):
    return navigation_proof(build_tree(data),build_tree(current_data),previous,current,
                            action=action,point=point,key=key)


def test_background_changes_are_accepted_only_for_explicit_navigation():
    data=lobby();previous,current=frames(data)
    assert np.abs(previous.astype(float)-current).mean()>12
    accepted=proof(data,data,previous,current)
    assert accepted['status']=='accepted' and accepted['control']=='hero'
    assert len(accepted['anchors'])>=3
    assert proof(data,data,previous,current,action='key',point=None,key='c')['status']=='accepted'
    # A generic false-consuming flag alone does not authorize the bypass.
    assert proof(data,data,previous,current,point=(1100,435))['status']=='not_applicable'
    assert proof(data,data,previous,current,action='hold')['status']=='not_applicable'
    assert proof(data,data,previous,current,action='key',point=None,key='g')['status']=='not_applicable'
    # A nearby icon is not the observed label's hit region.
    assert proof(data,data,previous,current,point=(932,619))['status']=='not_applicable'


@pytest.mark.parametrize('mutation', ['dimmed','covered_target','missing_control','duplicate_control',
                                    'changed_panel','changed_window','moved_control','consuming'])
def test_overlays_changes_and_ambiguous_controls_do_not_allow_navigation(mutation):
    data=lobby();now=deepcopy(data);previous,current=frames(data)
    if mutation=='dimmed':current=(current*.45).astype(np.uint8)
    elif mutation=='covered_target':current[630:670,910:960]=0
    elif mutation=='missing_control':now['text']=[r for r in now['text'] if r['text']!='Hero']
    elif mutation=='duplicate_control':now['text'].append(deepcopy(now['text'][1]))
    elif mutation=='changed_panel':now['text'] += [
        {'text':'Received Reward','box':[490,150,230,30],'score':.99},
        {'text':'You have successfully received the rewards!','box':[350,220,500,25],'score':.99},
        {'text':'Tap to close','box':[550,490,110,25],'score':.99}]
    elif mutation=='changed_window':now['window']['pid']=999
    elif mutation=='moved_control':now['text'][1]['box'][0]+=30
    tree=build_tree(now)
    if mutation=='consuming':tree['nodes']['operation:lobby/hero']['fields']['consuming']['value']=True
    result=navigation_proof(build_tree(data),tree,previous,current,action='click',point=(934,645))
    assert result['status']=='rejected',result


@pytest.mark.fixtures
def test_real_animated_lobby_pairs_preserve_bright_foreground_and_reject_dimmed_overlay():
    run=ROOT/'var/runs/20261027T121820Z_dd807e2e'
    files=[run/f'agent_{n:06}.png' for n in (1,4,7)]
    if not all(p.exists() for p in files):pytest.skip('Private animated lobby captures unavailable.')
    observations=[]
    for p in files:
        data=json.loads(p.with_suffix('.json').read_text(encoding='utf-8'))['result']
        observations.append((data,np.asarray(Image.open(p).convert('RGB'))[:,:,::-1].copy()))
    for data,current in observations[1:]:
        old,previous=observations[0]
        accepted=proof(old,data,previous,current,action='key',point=None,key='c')
        assert accepted['status']=='accepted',accepted
        rejected=proof(old,data,previous,(current*.5).astype(np.uint8),action='key',point=None,key='c')
        assert rejected['status']=='rejected'


@pytest.mark.fixtures
def test_real_hero_button_uses_native_glyph_region_instead_of_outside_caption():
    p=ROOT/'var/runs/20261027T125626Z_2e4a9cff/agent_000007.json'
    if not p.exists():pytest.skip('Private Arbiter screen unavailable.')
    data=json.loads(p.read_text(encoding='utf-8'))['result'];tree=build_tree(data)
    control=tree['nodes']['operation:hero_detail/awaken']
    assert control['fields']['box']['value']==[772,577,48,47]
    assert control['fields']['box_role']['value']=='template_extent'
    assert control['fields']['label_box']['value'][1]>624
    pixels=np.asarray(Image.open(p.with_suffix('.png')).convert('RGB'))[:,:,::-1].copy()
    assert navigation_proof(tree,tree,pixels,pixels,action='click',point=(796,600))['status']=='accepted'
    assert navigation_proof(tree,tree,pixels,pixels,action='click',point=(795,646))['status']=='not_applicable'
    covered=pixels.copy();covered[577:624,772:820]=0
    assert navigation_proof(tree,tree,pixels,covered,action='click',point=(796,600))['status']=='rejected'


@pytest.mark.fixtures
def test_awakening_badge_follows_zodiac_layout_without_hero_name_gate():
    p=ROOT/'var/runs/20261027T130439Z_84857abb/agent_000003.json'
    if not p.exists():pytest.skip('Private Leo awakening screen unavailable.')
    data=json.loads(p.read_text(encoding='utf-8'))['result']
    current=operation_view({'ui_tree':build_tree(data)})
    assert current['view']=='hero_awakening' and current['mode']=='overview'
    assert current['items'][0]['hero_name']=='Arbiter Vildred'
    for row in data['text']:
        row['text']=row['text'].replace('Arbiter Vildred','Other Hero')
    assert operation_view({'ui_tree':build_tree(data)})['items'][0]['hero_name']=='Other Hero'


def runtime_case(tmp_path,after=None):
    data=lobby();previous,current=frames(data)
    old=tmp_path/'old.png';fresh=tmp_path/'fresh.png'
    Image.fromarray(previous[:,:,::-1]).save(old);Image.fromarray(current[:,:,::-1]).save(fresh)
    data.update(frame=str(old),ui_tree=build_tree(data))
    path=tmp_path/'seen.json';path.write_text(json.dumps(data),encoding='utf-8')
    now=deepcopy(data);now['frame']=str(fresh);now['ui_tree']=build_tree(now)
    hero={'state':'unknown','window':deepcopy(WINDOW),'text':[
        {'text':t,'box':b,'score':.99} for t,b in (
            ('Ravi',[63,18,150,25]),('Ravi',[103,111,200,34]),('Lv.12/50',[101,179,120,34]),
            ('Search',[886,80,70,20]),('Awaken',[770,625,70,25]))],
          'matches':{'victorika_hero_tab':{'hit':True}}}
    hero['ui_tree']=build_tree(hero)
    calls=[];writes=[]
    runtime=object.__new__(Runtime)
    runtime.vision=SimpleNamespace(spec={'states':{}})
    runtime.observe=lambda name,**kwargs: (calls.append(('observe',name,kwargs)) or (after or hero if name=='after' else now))
    runtime.guard=lambda **kwargs: calls.append(('guard',kwargs)) or WINDOW
    runtime.capture=lambda: pytest.fail('UI and pixel proof must share the same observe frame.')
    runtime.wait=lambda job:None
    runtime.ctrl=SimpleNamespace(post_click=lambda *p:calls.append(('click',p)))
    runtime.tasker=SimpleNamespace(post_action=lambda *args:calls.append(('key',args)))
    runtime.evidence=SimpleNamespace(write=lambda *args:writes.append(args),frame=lambda *args:str(tmp_path/'rejected.png'),path=tmp_path)
    runtime.observer=SimpleNamespace(invalidate=lambda reason:calls.append(('invalidate',reason)))
    return runtime,path,data,now,calls,writes


@pytest.mark.parametrize('action', ['click','key'])
def test_runtime_sends_one_navigation_and_verifies_ui_destination(tmp_path,action):
    runtime,path,data,now,calls,writes=runtime_case(tmp_path)
    result=runtime.primitive(action,point=(934,645) if action=='click' else None,key='c' if action=='key' else None,
                             observation=path,from_state='unknown')
    assert result['selection']=='semantic_navigation'
    assert result['postcondition_verified'] is True and result['navigation_destination_verified'] is True
    assert sum(c[0] in ('click','key') for c in calls)==1
    assert ('observe','before',{'read_text':True}) in calls and ('observe','after',{'read_text':True}) in calls
    assert any(name=='navigation_guard' for name,_ in writes)


def test_dispatch_without_destination_proof_is_review_not_retry(tmp_path):
    runtime,path,data,now,calls,writes=runtime_case(tmp_path,after=lobby())
    result=runtime.primitive('click',point=(934,645),observation=path,from_state='unknown')
    assert result['dispatch_succeeded'] and not result['postcondition_verified'] and result['needs_review']
    assert sum(c[0]=='click' for c in calls)==1


def test_consuming_or_unmapped_point_keeps_global_guard(tmp_path):
    runtime,path,data,now,calls,writes=runtime_case(tmp_path)
    with pytest.raises(ValueError,match='tela mudou'):
        runtime.primitive('click',point=(1100,435),observation=path,from_state='unknown')
    assert not any(c[0]=='click' for c in calls)


def test_reference_is_loaded_before_fresh_observe_overwrites_same_filename(tmp_path):
    runtime,path,data,now,calls,writes=runtime_case(tmp_path)
    def changed(name,**kwargs):
        current=deepcopy(now);current['window']['pid']=100
        path.write_text(json.dumps(current),encoding='utf-8')
        return current
    runtime.observe=changed
    with pytest.raises(ValueError,match='outra janela'):
        runtime.primitive('click',point=(934,645),observation=path,from_state='unknown')
    assert not any(c[0]=='click' for c in calls)


def test_episode_navigation_accepts_stable_labels_and_requires_current_destination():
    data=lobby();previous,current=frames(data)
    accepted=proof(data,data,previous,current,point=(1110,175))
    assert accepted['status']=='accepted' and accepted['control']=='episode'
    assert accepted['destinations']==[{'view':'prequel_ready_map'}]
    assert not navigation_arrived({'ui_tree':build_tree(data)},accepted)
    for label in ('Side Story','Battle','Arena','Summon','Shop'):
        row=next(r for r in data['text'] if r['text']==label)
        x,y,w,h=row['box']
        assert proof(data,data,previous,current,point=(x+w//2,y+h//2))['status']=='not_applicable'
    for mutation in ('dim','covered','missing','moved','window','overlay'):
        now=deepcopy(data);pixels=current.copy()
        row=next(r for r in now['text'] if r['text']=='Episode')
        if mutation=='dim':pixels=(pixels*.5).astype(np.uint8)
        elif mutation=='covered':pixels[160:190,1045:1175]=0
        elif mutation=='missing':now['text'].remove(row)
        elif mutation=='moved':row['box'][0]+=30
        elif mutation=='window':now['window']['pid']=99
        elif mutation=='overlay':now['text'].append({'text':'Confirm','box':[630,400,120,35],'score':.99})
        assert proof(data,now,previous,pixels,point=(1110,175))['status']=='rejected',mutation


@pytest.mark.fixtures
def test_episode_current_lobby_glyphs_and_observed_map_arrival():
    lobby_file=ROOT/'var/admin-campaign-20261030w/lobby-navigation.json'
    map_file=ROOT/'var/runs/20261030T090525Z_45b0562b/agent_000004.json'
    if not all(p.exists() for p in (lobby_file,lobby_file.with_suffix('.png'),map_file)):
        pytest.skip('Private daily-reset lobby and Episode arrival unavailable.')
    data=json.loads(lobby_file.read_text(encoding='utf-8'))
    pixels=np.asarray(Image.open(lobby_file.with_suffix('.png')).convert('RGB'))[:,:,::-1].copy()
    changed=pixels.copy()
    changed[250:550,300:700]=0
    result=proof(data,data,pixels,changed,point=(1118,175))
    assert result['status']=='accepted',result
    arrived=json.loads(map_file.read_text(encoding='utf-8'))['result']
    assert navigation_arrived({'ui_tree':build_tree(arrived)},result)
    assert proof(data,data,pixels,(pixels*.5).astype(np.uint8),point=(1118,175))['status']=='rejected'
