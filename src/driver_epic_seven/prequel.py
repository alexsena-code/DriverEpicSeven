"""Prequel stage identity and finite graphs over current canonical panels."""
import json
import time
from .config import ROOT
from .stages import normalize
from .path_execution import recognition
from .composition import append_fragment, validate_graph


def stage(identity):
    stages=json.loads((ROOT/'data/stages/adventurer-prequel.json').read_text(encoding='utf-8'))['stages']
    if identity not in stages or not stages[identity].get('title'):
        raise ValueError('Fase do prólogo sem identidade estática resolvida.')
    return stages[identity]


def corrected_team_retry(entries):
    """One explicitly reconciled blocked entry, never an automatic retry rule."""
    if len(entries)!=1 or entries[0].get('status')!='blocked_team':return False
    proof=entries[0].get('team_correction',{})
    return bool(proof.get('user_confirmed') is True and proof.get('owned_hero')
                and isinstance(proof.get('expected_cp'),int) and proof['expected_cp']>0
                and proof.get('window') and proof.get('evidence'))


def reserve_entry(ledger, identity, key, energy, observation=None):
    """A new request cannot repeat an uncertain or already finished entry."""
    scope='prequel:'+identity
    entries=ledger.read()['stages'].get(scope,[])
    if any(item['key']!=key for item in entries):
        if not corrected_team_retry(entries):
            raise ValueError('Já existe entrada desta fase. Confira o resultado; finish-stage conclui sem iniciar novamente. Replay exige outro plano explícito.')
        from .observed_ui import operation_view
        proof=entries[0]['team_correction'];current=operation_view(observation or {})
        contexts=[i for i in current.get('items',[]) if i.get('semantic_id')=='context']
        info=contexts[0] if len(contexts)==1 else {}
        if (current.get('view')!='prequel_preparation' or info.get('team_cp')!=proof['expected_cp']
                or (info.get('cost') or {}).get('available')!=proof.get('energy_balance')
                or any(proof['window'].get(k)!=(observation or {}).get('window',{}).get(k)
                       for k in ('hwnd','pid','process_name','window_class','client_size'))):
            raise ValueError('A correção de equipe desta entrada não confere com a preparação atual.')
    ledger.reserve(scope,key,energy)


def target(current, params, observation=None, prepared=None):
    expected=stage(params['stage_id'])
    if params['kind']=='prequel_story_receipt':
        contexts=[i for i in current.get('items',[]) if i.get('semantic_id')=='context']
        info=contexts[0] if len(contexts)==1 else {}
        controls=[c for c in current.get('controls',[]) if c.get('semantic_id')=='close' and c.get('consuming') is False]
        labels={normalize(s) for s in info.get('story_lines',[])}
        if (expected['energy']!=0 or current.get('view')!='story_reward' or info.get('receipt_announced') is not True
                or normalize(expected['title']) not in labels or normalize(expected['location']) not in labels
                or normalize(info.get('chapter_text') or '')!=normalize('Chapter '+str(expected['chapter'])+'.')
                or len(controls)!=1):return None
        return controls[0].get('box')
    if params['kind']=='prequel_story_start':
        contexts=[i for i in current.get('items',[]) if i.get('semantic_id')=='context']
        info=contexts[0] if len(contexts)==1 else {}
        labels=[i for i in current.get('items',[]) if i.get('semantic_id')=='view_story_label']
        if (expected['energy']!=0 or current.get('view')!='prequel_story_map'
                or info.get('chapter_number')!=expected['chapter'] or info.get('episode_label')!='6th World Episode'
                or info.get('selected_kind_label')!='Story'
                or normalize(info.get('selected_description') or '')!=normalize(expected['map_description'])
                or len(labels)!=1 or labels[0].get('text')!='View Story'):
            return None
        return labels[0].get('box')
    if params['kind']=='prequel_story_done':
        ticket=(prepared or {}).get('story_seen:'+expected['id'])
        return [0,0,1,1] if (expected['energy']==0 and ticket
            and ticket['window']==(observation or {}).get('window')
            and current.get('view') in ('prequel_ready_map','prequel_story_map')) else None
    if params['kind']=='prequel_story_row':
        contexts=[i for i in current.get('items',[]) if i.get('semantic_id')=='context']
        info=contexts[0] if len(contexts)==1 else {}
        if current.get('view') not in ('prequel_ready_map','prequel_story_map') or info.get('chapter_number')!=expected['chapter']:
            return None
        rows=[i for i in current.get('items',[]) if i.get('semantic_id')=='stage_row'
              and i.get('ordinal')==expected['ordinal'] and normalize(i.get('title') or '')==normalize(expected['map_title'])]
        return rows[0].get('box') if len(rows)==1 else None
    if params['kind'] in ('prequel_story_hold','prequel_story_skip'):
        from .observed_ui import target_box
        contexts=[i for i in current.get('items',[]) if i.get('semantic_id')=='context']
        gesture='hold' if params['kind']=='prequel_story_hold' else 'click'
        if current.get('view')!='story_dialogue' or len(contexts)!=1 or contexts[0].get('skip_gesture')!=gesture:
            return None
        return target_box(observation['ui_tree'],'story_skip')
    if params['kind']=='prequel_map_return':
        return [0,0,1,1] if current.get('view') in ('prequel_ready_map','prequel_story_map') else None
    if params['kind']=='prequel_clear':
        from .observed_ui import target_box
        contexts=[i for i in current.get('items',[]) if i.get('semantic_id')=='context']
        if current.get('view')!='campaign_result' or len(contexts)!=1 or contexts[0].get('earned_stars')!=3:
            return None
        return target_box(observation['ui_tree'],'clear_continue')
    contexts=[i for i in current.get('items',[]) if i.get('semantic_id')=='context']
    if len(contexts)!=1:
        return None
    info=contexts[0]
    if params['kind']=='prequel_row':
        if (current.get('view') not in ('prequel_ready_map','prequel_story_map')
                or info.get('chapter_number')!=expected['chapter']
                or info.get('episode_label')!='6th World Episode'):
            return None
        description_matches=normalize(info.get('selected_description') or '')==normalize(expected['map_description'])
        rows=[i for i in current['items'] if i.get('semantic_id')=='stage_row'
              and i.get('ordinal')==expected['ordinal']
              and (normalize(i.get('title') or '')==normalize(expected['map_title']) or description_matches)
              and i.get('available') is True]
        return rows[0].get('box') if len(rows)==1 else None
    if params['kind']=='prequel_ready':
        if current.get('view')!='prequel_ready_map' or info.get('chapter_number')!=expected['chapter']:
            return None
        description_matches=normalize(info.get('selected_description') or '')==normalize(expected['map_description'])
        row=[i for i in current['items'] if i.get('semantic_id')=='stage_row'
             and i.get('ordinal')==expected['ordinal'] and i.get('available') is True
             and (normalize(i.get('title') or '')==normalize(expected['map_title']) or description_matches)]
        if len(row)!=1:
            return None
        rows=[i for i in current['items'] if i.get('semantic_id')=='ready_label' and i.get('text')=='Ready']
        return rows[0].get('box') if len(rows)==1 else None
    if current.get('view')!='prequel_preparation':
        return None
    cost=info.get('cost')
    if (normalize(info.get('location') or '')!=normalize(expected['location'])
            or normalize(info.get('story_title') or '')!=normalize(expected['title'])
            or not cost or cost.get('cost')!=expected['energy'] or cost.get('available',-1)<cost['cost']):
        return None
    if params['kind']=='prequel_prepared':
        return [0,0,1,1]
    if params['kind']=='prequel_start':
        ticket=(prepared or {}).get(expected['id'])
        if (params.get('max_energy',0)<cost['cost']
                or not isinstance(info.get('team_cp'),int) or info['team_cp']<=0
                or not ticket or not 0<=time.time()-ticket['epoch_seconds']<=30
                or any(ticket['window'].get(k)!=(observation or {}).get('window',{}).get(k)
                       for k in ('hwnd','pid','process_name','window_class','client_size'))):
            return None
        controls=[c for c in current.get('controls',[]) if c.get('semantic_id')=='start_quest'
                  and c.get('consuming') is True]
        return controls[0].get('box') if len(controls)==1 else None
    return None


def prepare_graph(identity):
    stage(identity)
    return {
        'Prequel.Prepare.Entry':{'recognition':'DirectHit','action':'DoNothing',
                               'next':['Prequel.Prepare.Done','Prequel.Prepare.Row']},
        'Prequel.Prepare.Row':recognition({'kind':'prequel_row','stage_id':identity},'Click',
            next_nodes=['Prequel.Prepare.Ready'],hits=1,post_delay=500),
        'Prequel.Prepare.Ready':recognition({'kind':'prequel_ready','stage_id':identity},'Click',
            next_nodes=['Prequel.Prepare.Done'],hits=1,post_delay=500,timeout=12000),
        'Prequel.Prepare.Done':recognition({'kind':'prequel_prepared','stage_id':identity}),
    }


def campaign_graph(first, last, max_energy):
    start,stop=stage(first),stage(last)
    catalog=json.loads((ROOT/'data/stages/adventurer-prequel.json').read_text(encoding='utf-8'))['stages']
    if start['chapter']!=stop['chapter'] or stop['ordinal']<start['ordinal']:
        raise ValueError('O trecho deve permanecer no mesmo capítulo e em ordem.')
    plan=sorted((s for s in catalog.values() if s['chapter']==start['chapter']
                 and start['ordinal']<=s['ordinal']<=stop['ordinal']),key=lambda s:s['ordinal'])
    if len(plan)!=stop['ordinal']-start['ordinal']+1 or any(not s.get('title') or not isinstance(s['energy'],int) or s['energy']<0 for s in plan):
        raise ValueError('O trecho contém identidade/custo desconhecido.')
    cost=sum(s['energy'] for s in plan)
    if max_energy<cost:
        raise ValueError('O orçamento não cobre o trecho: '+str(cost))
    graph={'Path.Campaign.Entry':{'recognition':'DirectHit','action':'DoNothing',
                                 'next':['Path.Campaign.Tutorial','Path.Campaign.'+plan[0]['id']+'.Back','Path.Campaign.'+plan[0]['id']+'.Row']},
           'Path.Campaign.Tutorial':recognition({'kind':'informational_ack','view':'tutorial'},'LongPress',duration=100,
               hits=4,next_nodes=['Path.Campaign.Tutorial','Path.Campaign.'+plan[0]['id']+'.Back','Path.Campaign.'+plan[0]['id']+'.Row'],post_delay=700,timeout=12000)}
    for index,s in enumerate(plan):
        prefix='Path.Campaign.'+s['id']+'.'
        params={'stage_id':s['id']}
        following='Path.Campaign.'+plan[index+1]['id']+'.Row' if index+1<len(plan) else 'Path.Campaign.Done'
        if s['energy']==0:
            graph[prefix+'Back']=recognition({'kind':'navigation','view':'prequel_preparation','key':'escape'},
                'LongPressKey',next_nodes=[prefix+'Row'],key=[27],duration=100,hits=1,post_delay=500)
            graph[prefix+'Row']=recognition({'kind':'prequel_story_row',**params},'Click',
                next_nodes=[prefix+'Start'],post_delay=400)
            recovery_entry=prefix+'Recovery.Path.Recover.Entry'
            choices=[prefix+'Map',prefix+'Receipt',prefix+'Before.Hold',prefix+'Before.Skip',prefix+'Before.Confirm',prefix+'Before.Notice',recovery_entry]
            # A free-story exit can return to Lobby with its receipt pending.
            # Reopen the same campaign mission using the shared navigation graph.
            from .path_execution import recovery_graph
            from .path_planning import catalog as quest_catalog
            chapter_end=max((x for x in catalog.values() if x['chapter']==s['chapter']),key=lambda x:x['ordinal'])['id']
            missions=[t for t in quest_catalog().tasks.values() if t['path']=='heir'
                      and t.get('parameters',{}).get('enter')==chapter_end]
            if len(missions)==1:
                mission=missions[0]
                recovery=recovery_graph(mission['group'],mission['id'],'campaign')
                recovery['Path.Recover.Entry']=recognition({'kind':'view','views':['lobby','orbis_guide']},
                    next_nodes=['Path.Recover.Done','Path.Open.Entry'])
                names=append_fragment(graph,recovery,prefix+'Recovery.')
                graph[names['Path.Recover.Done']]['next']=[prefix+'Map']
            else:
                choices.remove(recovery_entry)
            graph[prefix+'Start']=recognition({'kind':'prequel_story_start',**params,'energy':0,'consuming':True},
                'LongPress',duration=100,next_nodes=choices,post_delay=500,timeout=60000)
            for kind,duration in [('Hold',1500),('Skip',100)]:
                graph[prefix+'Before.'+kind]=recognition({'kind':'prequel_story_'+kind.lower(),**params},
                    'LongPress',duration=duration,hits=6,post_delay=500,timeout=60000,next_nodes=choices)
            graph[prefix+'Before.Confirm']={'recognition':'Custom','custom_recognition':'ScreenTarget',
                'custom_recognition_param':{'state':'story_confirmation','target':'story_confirm_button','read_text':True},
                'action':'Click','max_hit':6,'post_delay':500,'timeout':60000,'next':choices}
            graph[prefix+'Receipt']=recognition({'kind':'prequel_story_receipt',**params},'LongPress',duration=100,
                next_nodes=[prefix+'Map'],post_delay=700,timeout=60000)
            graph[prefix+'Before.Notice']=recognition({'kind':'informational_ack'},'LongPress',duration=100,
                hits=4,next_nodes=choices,post_delay=700,timeout=60000)
            graph[prefix+'Map']=recognition({'kind':'prequel_story_done',**params},next_nodes=[following],timeout=60000)
            continue
        graph[prefix+'Back']=recognition({'kind':'navigation','view':'prequel_preparation','key':'escape'},
            'LongPressKey',next_nodes=[prefix+'Row'],key=[27],duration=100,hits=1,post_delay=500)
        graph[prefix+'Row']=recognition({'kind':'prequel_row',**params},'Click',next_nodes=[prefix+'Ready'],post_delay=400)
        graph[prefix+'Ready']=recognition({'kind':'prequel_ready',**params},'Click',next_nodes=[prefix+'Start'],post_delay=500,timeout=12000)
        graph[prefix+'Start']=recognition({'kind':'prequel_start',**params,'max_energy':s['energy'],
                                          'energy':s['energy'],'consuming':True},'Click',
            next_nodes=[prefix+'Before.Rank',prefix+'Before.Auto',prefix+'Before.Hold',prefix+'Before.Skip',prefix+'Before.Confirm',prefix+'Clear'],post_delay=500,timeout=600000)
        graph[prefix+'Clear']=recognition({'kind':'prequel_clear',**params},'Click',
            next_nodes=[prefix+'After.Rank',prefix+'After.Rewards',prefix+'After.StoryReward',prefix+'After.Hold',prefix+'After.Skip',prefix+'After.Confirm',prefix+'Map'],
            hits=1,post_delay=500,timeout=600000)
        for phase in ('Before','After'):
            choices=([prefix+'Before.Rank',prefix+'Before.Auto',prefix+'Before.Hold',prefix+'Before.Skip',prefix+'Before.Confirm',prefix+'Clear'] if phase=='Before' else
                     [prefix+'After.Rank',prefix+'After.Rewards',prefix+'After.StoryReward',prefix+'After.Hold',prefix+'After.Skip',prefix+'After.Confirm',prefix+'Map'])
            graph[prefix+phase+'.Rank']=recognition({'kind':'informational_ack'},'Click',
                next_nodes=choices,hits=8,post_delay=500,timeout=600000)
            for suffix,state,target_name,hits in [('Skip','story','story_skip',12),('Confirm','story_confirmation','story_confirm_button',12)]:
                graph[prefix+phase+'.'+suffix]={'recognition':'Custom','custom_recognition':'ScreenTarget',
                    'custom_recognition_param':{'state':state,'target':target_name,'read_text':True},'action':'Click',
                    'max_hit':hits,'post_delay':500,'timeout':600000,'next':choices}
                if suffix=='Skip':
                    graph[prefix+phase+'.'+suffix]=recognition({'kind':'prequel_story_skip',**params},'Click',
                        next_nodes=choices,hits=12,post_delay=500,timeout=600000)
            graph[prefix+phase+'.Hold']=recognition({'kind':'prequel_story_hold',**params},'LongPress',
                next_nodes=choices,hits=6,duration=1500,post_delay=500,timeout=600000)
        graph[prefix+'Before.Auto']={'recognition':'Custom','custom_recognition':'ScreenTarget',
            'custom_recognition_param':{'state':'battle_running','auto_state':False,'target':'battle_auto'},
            'action':'Click','max_hit':1,'post_delay':200,'timeout':600000,
            'next':[prefix+'Before.Rank',prefix+'Before.Hold',prefix+'Before.Skip',prefix+'Before.Confirm',prefix+'Clear']}
        for suffix,state,target_name in [('Rewards','battle_rewards','result_confirm'),('StoryReward','story_reward','story_reward_close')]:
            graph[prefix+'After.'+suffix]={'recognition':'Custom','custom_recognition':'ScreenTarget',
                'custom_recognition_param':{'state':state,'target':target_name,'read_text':True},'action':'Click',
                'max_hit':2,'post_delay':500,'timeout':600000,
                'next':[prefix+'After.Rank',prefix+'After.Rewards',prefix+'After.StoryReward',prefix+'After.Hold',prefix+'After.Skip',prefix+'After.Confirm',prefix+'Map']}
        following='Path.Campaign.'+plan[index+1]['id']+'.Row' if index+1<len(plan) else 'Path.Campaign.Done'
        graph[prefix+'Map']=recognition({'kind':'prequel_map_return',**params},
            next_nodes=[prefix+'After.Rank',prefix+'After.StoryReward',following],hits=3,post_delay=800)
    graph['Path.Campaign.Done']=recognition({'kind':'prequel_story_done' if stop['energy']==0 else 'prequel_map_return','stage_id':stop['id']})
    return {'stage_ids':[s['id'] for s in plan],'energy_limit':cost,'max_starts':len(plan),'requires_three_stars':True},graph


def finish_graph(identity, victory_observed=False):
    _,graph=campaign_graph(identity,identity,stage(identity)['energy'])
    # An already running battle with Auto on needs no input. Keep watching
    # for the result/story within the caller's bounded runtime deadline.
    graph['Path.Campaign.Entry']['timeout']=600000
    prefix='Path.Campaign.'+identity+'.'
    # This entry belongs to a new campaign, not a resume. Its Back/Row edges
    # would reference nodes removed below and cause Maa to reject the graph.
    graph.pop('Path.Campaign.Tutorial',None)
    if stage(identity)['energy']==0:
        graph['Path.Campaign.Entry']['next']=[prefix+'Map',prefix+'Receipt',prefix+'Before.Hold',prefix+'Before.Skip',prefix+'Before.Confirm',prefix+'Before.Notice']
        for suffix in ('Back','Row','Start'):
            graph.pop(prefix+suffix)
        return graph
    graph['Path.Campaign.Entry']['next']=([prefix+'Map',prefix+'After.Rank',prefix+'After.Rewards',prefix+'After.StoryReward',prefix+'After.Hold',prefix+'After.Skip',prefix+'After.Confirm']
        if victory_observed else [prefix+'Before.Rank',prefix+'Before.Auto',prefix+'Before.Hold',prefix+'Before.Skip',prefix+'Before.Confirm',prefix+'Clear'])
    # Resume only result/story/combat of an existing reservation. Unreachable
    # start/preparation nodes are removed, so this graph cannot enter a battle.
    for suffix in ('Back','Row','Ready','Start'):
        graph.pop(prefix+suffix)
    return graph
