"""Shared calibrated Maa treatments. Consumers choose branches and limits."""
from copy import deepcopy
import json

from .config import ROOT


def treatment(kind, destinations, *, hits, timeout, post_delay=None, stage_id=None):
    if not isinstance(hits,int) or isinstance(hits,bool) or not 1<=hits<=12 or not 1<=timeout<=600000:
        raise ValueError('Tratamento precisa de limites finitos.')
    templates={'confirm_skip':'Finish.ConfirmSkip','cancel_friend':'Finish.CancelFriend','side_alert':'Finish.SideAlert',
               'auto':'Finish.EnableAuto','rewards':'Finish.Rewards','story_reward':'Finish.StoryReward'}
    if kind in templates:
        # Preserve calibrated stability, target and guard in one existing source.
        source=json.loads((ROOT/'resources/epic-seven/pipeline/battle_finish.json').read_text(encoding='utf-8'))
        node=deepcopy(source[templates[kind]])
        node['custom_recognition_param']['read_text']=True
    elif kind in ('story_skip','story_hold','notice'):
        from .path_execution import recognition
        params={'kind':'informational_ack'} if kind=='notice' else {'kind':kind,'stage_id':stage_id}
        node=recognition(params,'LongPress',duration=1500 if kind=='story_hold' else 100)
    else:
        raise ValueError('Tratamento sem composição calibrada: '+kind)
    if kind=='auto' and hits!=1:
        raise ValueError('Auto admite no máximo uma ativação comprovada.')
    node.update(next=list(destinations),max_hit=hits,timeout=timeout)
    if post_delay is not None:node['post_delay']=post_delay
    return node


def story_target(observation, params):
    from .observed_ui import operation_view, target_box
    current=operation_view(observation)
    info=[i for i in current.get('items',[]) if i.get('semantic_id')=='context']
    gesture='hold' if params['kind'] in ('story_hold','prequel_story_hold') else 'click'
    if current.get('view')!='story_dialogue' or len(info)!=1 or info[0].get('skip_gesture')!=gesture:
        return None
    return target_box(observation['ui_tree'],'story_skip')
