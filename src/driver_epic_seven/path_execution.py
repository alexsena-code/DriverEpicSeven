"""Finite Maa graphs and current-tree targets for the Path operations."""
from .observed_ui import field_value, operation_view, quest_view, query_control, query_operation_control
from .input_guards import navigation_proof


def current_view(observation):
    current = operation_view(observation)
    quest = quest_view(observation)
    if not current and quest.get('group_id'):
        current = {'view': 'orbis_guide', 'mode': quest.get('path')}
    return current


def path_target(observation, params, frame, prepared=None):
    """A box is returned only for a mapped current target in this Maa frame."""
    tree = observation['ui_tree']
    current = current_view(observation)
    if str(params.get('kind','')).startswith('formation_'):
        from .formation_operations import target
        return target(observation,params,prepared)
    if params.get('kind') in ('story_skip','story_hold'):
        from .interruptions import story_target
        return story_target(observation,params)
    if params.get('kind')=='mapped_back':
        if current.get('view') not in ('hero_detail','hero_equipment','equipment_detail','item_enhancement',
                                      'prequel_preparation','prequel_ready_map','prequel_story_map','abyss_floors','abyss_hub'):
            return None
        return path_target(observation,{'kind':'navigation','view':current['view'],'key':'escape'},frame,prepared)
    if str(params.get('kind','')).startswith('equipment_'):
        from .equipment_operations import target
        return target(current,params,observation,prepared)
    if params.get('kind') in ('group_guard','group_task_ready','group_scroll'):
        from .path_group import target
        return target(observation,params)
    if params.get('kind') in ('mission_claim','mission_receipt','claim_done','group_claim','group_claim_done','group_receipt','group_next'):
        from .path_claims import target
        return target(observation,params,prepared)
    if str(params.get('kind','')).startswith('altar_'):
        from .altar import target
        return target(current,params,observation,prepared)
    if str(params.get('kind','')).startswith('abyss_'):
        from .abyss import target
        return target(current,params,observation,prepared)
    if str(params.get('kind','')).startswith('prequel_'):
        from .prequel import target
        return target(current,params,observation,prepared)
    if params.get('kind') == 'view':
        if params.get('views'):
            return [0,0,1,1] if current.get('view') in params['views'] else None
        if params.get('states'):
            from .observed_ui import screen_state
            return [0,0,1,1] if screen_state(observation) in params['states'] else None
        if params.get('state'):
            from .observed_ui import screen_state
            return [0,0,1,1] if screen_state(observation) == params['state'] else None
        return [0,0,1,1] if params.get('view') and all(current.get(k) == v for k,v in params.items()
                                if k in ('view','mode')) else None
    if params.get('kind') == 'navigation':
        if current.get('view') != params.get('view'):
            return None
        key = params.get('key')
        point = None
        if key is None:
            try:
                control = query_operation_control(tree, current['view'], params.get('control'))['node']
            except ValueError:
                return None
            box = field_value(control,'box')
            if not box:
                return None
            if (field_value(control,'navigation_template_verified') is True
                    and field_value(control,'consuming') is False
                    and field_value(control,'navigation_destinations')):
                return box
            point = [box[0]+box[2]//2,box[1]+box[3]//2]
        proof = navigation_proof(tree,tree,frame,frame,
                                 action='key' if key else 'click',key=key,point=point)
        return [0,0,1,1] if key and proof['status']=='accepted' else (
            box if not key and proof['status']=='accepted' else None)
    if params.get('kind') == 'mission_go':
        quest = quest_view(observation)
        if quest.get('group_id') != params.get('group_id'):
            return None
        tasks = [t for t in quest['visible_tasks'] if t['task_id'] == params.get('task_id')]
        if (len(tasks) != 1 or tasks[0]['status'] not in ('incomplete','unknown')
                or tasks[0]['row_fully_visible'] is not True or tasks[0]['control'] != 'go'):
            return None
        # Go only navigates in the individually calibrated recipes. This
        # selector does not turn all catalog deep links into battle entries.
        try:
            found = query_control(tree,params['group_id'],params['task_id'],'go')['node']
        except ValueError:
            return None
        return field_value(found,'box')
    if params.get('kind') == 'free_covenant':
        if current.get('view')!='summon_page' or current.get('mode')!='covenant':
            return None
        items=current.get('items',[])
        if len(items)!=1 or items[0].get('actual_cost')!={'currency':'covenant_bookmark','amount':0,'quantity':1}:
            return None
        controls=[c for c in current.get('controls',[]) if c.get('semantic_id')=='free_summon'
                  and c.get('consuming') is True and c.get('box_role')=='template_extent']
        return controls[0]['box'] if len(controls)==1 else None
    if params.get('kind') == 'summon_result':
        return [0,0,1,1] if current.get('view') in ('hero_presentation','equipment_receipt','artifact_receipt') else None
    if params.get('kind') == 'informational_ack':
        if (params.get('view') and current.get('view')!=params['view']) or current.get('view') not in (
                'rank_up_result','received_reward','system_unlock_notice','connection_unlock_notice','hero_friendship_result',
                'hero_level_result','hero_awakening_result','checkin_notice','story_reward','tutorial'):
            return None
        roles={'checkin_notice':('confirm',),'tutorial':('skip',)}.get(current.get('view'),('close','acknowledge'))
        controls=[c for c in current.get('controls',[]) if c.get('semantic_id') in roles
                  and c.get('consuming') is False and c.get('visible') is True]
        if current.get('view')=='tutorial' and (len(controls)!=1 or controls[0].get('box_role')!='template_extent'):
            return None
        return controls[0].get('box') if len(controls)==1 else None
    return None


def recognition(params, action='DoNothing', *, next_nodes=(), hits=1, timeout=6000, **extra):
    if action=='Click' and params.get('kind') in ('navigation','mission_go','prequel_row','prequel_ready'):
        action='LongPress'
        extra.setdefault('duration',100)
    result = {'recognition':'Custom','custom_recognition':'ScreenTarget',
              'custom_recognition_param':{'read_text':True,'path':params},
              'action':action,'max_hit':hits,'timeout':timeout,**extra}
    if next_nodes:
        result['next'] = list(next_nodes)
    return result


def open_path_graph():
    branches = ['Path.Open.Done','Path.Open.Heir','Path.Open.ResultBack','Path.Open.SummonBack','Path.Open.Back','Path.Open.Lobby']
    return {
        'Path.Open.Entry': {'recognition':'DirectHit','action':'DoNothing','next':branches},
        'Path.Open.Done': recognition({'kind':'view','view':'orbis_guide','mode':'heir'}),
        'Path.Open.Heir': recognition({'kind':'navigation','view':'orbis_guide','control':'orbis_heir_tab'},
            'Click',next_nodes=['Path.Open.Done'],hits=2,post_delay=500),
        'Path.Open.ResultBack': recognition({'kind':'navigation','view':'hero_presentation','control':'back'},
            'Click',next_nodes=['Path.Open.SummonBack'],hits=1,post_delay=500),
        'Path.Open.SummonBack': recognition({'kind':'navigation','view':'summon_page','key':'escape'},
            'LongPressKey',next_nodes=['Path.Open.Lobby'],key=[27],duration=100,hits=1,post_delay=500),
        'Path.Open.Lobby': recognition({'kind':'navigation','view':'lobby','key':'g'},
            'LongPressKey',next_nodes=['Path.Open.Done','Path.Open.Heir'],key=[71],duration=100,hits=2,post_delay=500),
        'Path.Open.Back': recognition({'kind':'mapped_back'},'LongPressKey',
            next_nodes=branches,key=[27],duration=100,hits=4,post_delay=500),
    }


GO_DESTINATIONS = {
    'summon': {'kind':'view','view':'summon_page'},
    'campaign': {'kind':'view','states':['prequel_ready_map','prequel_story_map']},
    'spirit_altar': {'kind':'view','view':'spirit_altar_hub'},
    'abyss': {'kind':'view','views':['abyss_hub','abyss_floors','abyss_preparation']},
    'equip': {'kind':'view','views':['hero_equipment','hero_detail']},
    'equipment_enhance': {'kind':'view','views':['hero_equipment','hero_detail']},
}


def go_graph(group_id, task_id, executor):
    if executor not in GO_DESTINATIONS:
        raise ValueError('Navegação desta família ainda não calibrada: '+executor)
    return {
        'Path.Go.Entry': {'recognition':'DirectHit','action':'DoNothing','next':['Path.Go.Click']},
        'Path.Go.Click': recognition({'kind':'mission_go','group_id':group_id,'task_id':task_id},
            'Click',next_nodes=['Path.Go.Done'],hits=1,post_delay=500,timeout=12000),
        'Path.Go.Done': recognition(GO_DESTINATIONS[executor]),
    }


def recovery_graph(group_id, task_id, executor):
    """Return to one mission destination through existing finite navigation.

    This composes Maa graphs, never dispatches the mission or repeats an
    uncertain consuming action. A destination already reached needs no input.
    """
    from .path_planning import catalog, executor_for
    task=catalog().tasks.get(task_id)
    if not task or task['group']!=group_id or executor_for(task)!=executor:
        raise ValueError('Missão/grupo incompatível com a recuperação solicitada.')
    if executor not in GO_DESTINATIONS:
        raise ValueError('Destino de recuperação ainda não calibrado: '+executor)
    graph={**open_path_graph(),**go_graph(group_id,task_id,executor)}
    notice='Path.Recover.StoryReward'
    graph['Path.Recover.Entry']={'recognition':'DirectHit','action':'DoNothing',
        'next':['Path.Recover.Done',notice,'Path.Open.Entry'],'max_hit':1}
    graph['Path.Open.Done']['next']=['Path.Go.Entry']
    graph['Path.Go.Done']['next']=['Path.Recover.Done']
    graph['Path.Go.Click']['next']=['Path.Go.Done',notice]
    graph[notice]=recognition({'kind':'informational_ack','view':'story_reward'},'LongPress',duration=100,
        hits=1,post_delay=700,timeout=12000,next_nodes=['Path.Recover.Done','Path.Open.Entry'])
    graph['Path.Recover.Done']=recognition(GO_DESTINATIONS[executor])
    return graph


def navigation_graph(view, control, destination, mode=None):
    goal = {'kind':'view','view':destination}
    if mode is not None:
        goal['mode'] = mode
    return {
        'Path.Navigate.Entry': {'recognition':'DirectHit','action':'DoNothing','next':['Path.Navigate.Click']},
        'Path.Navigate.Click': recognition({'kind':'navigation','view':view,'control':control},
            'Click',next_nodes=['Path.Navigate.Done'],hits=1,post_delay=500,timeout=12000),
        'Path.Navigate.Done': recognition(goal),
    }


def acknowledge_graph(view, destination):
    # Reuse the composed notice reader and its non-consuming control. A label
    # such as Confirm alone never authorizes dismissing an arbitrary modal.
    if view not in ('checkin_notice','rank_up_result','received_reward','system_unlock_notice',
                    'connection_unlock_notice','hero_friendship_result','hero_level_result','hero_awakening_result','story_reward','tutorial'):
        raise ValueError('Aviso sem confirmação informativa mapeada.')
    return {
        'Path.Acknowledge.Entry': {'recognition':'DirectHit','action':'DoNothing','next':['Path.Acknowledge.Click']},
        'Path.Acknowledge.Click': recognition({'kind':'informational_ack','view':view},'LongPress',duration=100,
            hits=1,post_delay=700,timeout=12000,next_nodes=['Path.Acknowledge.Done']),
        'Path.Acknowledge.Done': recognition({'kind':'view','view':destination}),
    }


def free_summon_graph(task_id):
    if task_id!='guide_01_006_001':
        raise ValueError('O executor gratuito foi limitado à missão calibrada do nível 1.')
    return {
        'Path.Summon.Entry':{'recognition':'DirectHit','action':'DoNothing','next':['Path.Summon.Free']},
        'Path.Summon.Free':recognition({'kind':'free_covenant','task_id':task_id,'consuming':True},
            'Click',next_nodes=['Path.Summon.Result'],hits=1,post_delay=1500,timeout=45000),
        'Path.Summon.Result':recognition({'kind':'summon_result'}),
    }


def run_graph(runtime, graph, entry, success, timeout=25):
    if not 1 <= timeout <= 1800:
        raise ValueError('Tempo da operação fora do limite.')
    runtime.guard(input_active=True)
    runtime.evidence.write('path_graph',{'entry':entry,'success':success,'graph':graph})
    from .composition import validate_graph
    terminals=list(success) if isinstance(success,(tuple,list)) else [success]
    validate_graph(graph,entry,terminals)
    post = getattr(runtime,'post_task',runtime.tasker.post_task)
    job = post(entry, graph)
    try:
        runtime.wait(job, timeout, task=True)
        nodes = [{'name':n.name,'completed':n.completed,
                  'action_success':n.action.success if n.action else None} for n in job.get().nodes]
        completed=[n['name'] for n in nodes if n['name'] in terminals and n['completed']]
        reached=bool(completed)
        defeats=[n['name'] for n in nodes if n['completed'] and (
            graph.get(n['name'],{}).get('custom_recognition_param',{}).get('execution',{}).get('phase')=='defeat'
            or graph.get(n['name'],{}).get('custom_recognition_param',{}).get('path',{}).get('kind') in ('prequel_defeat','abyss_defeat','altar_defeat'))]
        # The terminal Maa recognition is the action's proof. A later capture
        # may fail independently and must not turn that proof into a retry.
        observation_error = None
        try:
            after = runtime.observe('path_after',read_text=True)
        except (RuntimeError, OSError, ValueError) as exc:
            after = None
            observation_error = str(exc)
        result = {'operation':'path','completed':reached,'postcondition_verified':reached,
                  'completion_node':completed[-1] if completed else None,
                  'battle_result':'defeat' if defeats else None,
                  'needs_review':not reached or observation_error is not None,
                  'observation_error':observation_error,'nodes':nodes,'after':after,
                  'agent_checkpoint':True,'evidence_dir':str(runtime.evidence.path)}
        runtime.evidence.write('path_result',result)
        return result
    except Exception as exc:
        try:runtime.evidence.write('path_failure',{'entry':entry,'error':str(exc),'no_automatic_retry':True})
        except Exception as failure:exc.add_note('Falha ao preservar evidência: '+str(failure))
        try:
            runtime.observe('path_failure_after',read_text=True)
        except (RuntimeError, OSError, ValueError):
            pass
        raise
