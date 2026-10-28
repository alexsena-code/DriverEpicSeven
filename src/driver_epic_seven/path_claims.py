"""One guarded reward collection, separated from satisfying a mission."""
from .observed_ui import quest_view,operation_view,field_value,tree_for
from .path_execution import recognition


def target(observation, params, prepared=None):
    current=quest_view(observation)
    kind=params['kind']
    if kind=='mission_receipt':
        view=operation_view(observation)
        ticket=(prepared or {}).get('mission_claim:'+params['group_id'])
        if view.get('view')!='received_reward' or not ticket:return None
        if ticket.get('mission_id')!=params.get('mission_id'):return None
        controls=[c for c in view.get('controls',[]) if c.get('semantic_id')=='close' and c.get('consuming') is False]
        return controls[0].get('box') if len(controls)==1 else None
    if kind=='group_receipt':
        view=operation_view(observation)
        if view.get('view')!='received_reward' or not (prepared or {}).get('group_claim:'+params['group_id']):return None
        controls=[c for c in view.get('controls',[]) if c.get('semantic_id')=='close' and c.get('consuming') is False]
        return controls[0].get('box') if len(controls)==1 else None
    if kind=='group_claim_done':
        return [0,0,1,1] if current.get('group_id')==params.get('next_group_id') else None
    if current.get('group_id')!=params['group_id']:return None
    count=current.get('group_counter')
    if not count or count['total']!=params['total']:return None
    tasks=[t for t in current['visible_tasks'] if t['task_id']==params.get('mission_id')]
    task=tasks[0] if len(tasks)==1 else {}
    if kind=='claim_done':
        receipt=(prepared or {}).get('mission_receipt:'+params['group_id'],{})
        receipt_verified=(receipt.get('mission_id')==params.get('mission_id')
            and receipt.get('before_count')==params['before_count']
            and receipt.get('window')==observation.get('window') and receipt.get('window') is not None)
        verified=(count['current']>params['before_count'] and
                  (count['current']==count['total'] or receipt_verified
                   or (task.get('status')=='claimed' and task.get('claimed_tick_box'))))
        return [0,0,1,1] if verified else None
    if kind=='group_next':
        if count['current']!=count['total'] or not (prepared or {}).get('group_receipt:'+params['group_id']):return None
        nodes=[n for n in tree_for(observation)['nodes'].values() if n['kind']=='control'
               and field_value(n,'semantic_id')=='orbis_next_group' and field_value(n,'consuming') is False
               and field_value(n,'box_role')=='template_extent']
        return field_value(nodes[0],'box') if len(nodes)==1 else None
    if count['current']!=params['before_count']:return None
    if kind=='mission_claim':
        if (task.get('claim_ready') is not True or task.get('row_fully_visible') is not True
                or task.get('control')!='receive'):return None
        return task.get('claim_control_box')
    if kind=='group_claim':
        if (count['current']!=count['total'] or current.get('group_claim_control_ready') is not True):return None
        return current.get('group_receive_box')
    return None


def graph(group_id, mission_id, before_count, total, *, next_group_id=None):
    group=next_group_id is not None
    scope=('group_reward:'+group_id if group else 'claim:'+group_id+':'+mission_id)
    args={'group_id':group_id,'mission_id':mission_id,'before_count':before_count,'total':total}
    if group:args['next_group_id']=next_group_id
    nodes={
        'Path.Claim.Entry':{'recognition':'DirectHit','action':'DoNothing','next':['Path.Claim.Dispatch']},
        'Path.Claim.Dispatch':recognition({'kind':'group_claim' if group else 'mission_claim',**args,
            'task_id':scope,'consuming':True},'LongPress',duration=100,hits=1,post_delay=700,
            next_nodes=['Path.Claim.Done','Path.Claim.Receipt'],timeout=45000),
        'Path.Claim.Receipt':recognition({'kind':'group_receipt','group_id':group_id} if group else {'kind':'mission_receipt',**args},'LongPress',
            duration=100,hits=4,post_delay=700,next_nodes=['Path.Claim.Done','Path.Claim.Receipt'],timeout=45000),
        'Path.Claim.Done':recognition({'kind':'group_claim_done' if group else 'claim_done',**args}),
    }
    if group:
        follow=['Path.Claim.Done','Path.Claim.Receipt','Path.Claim.Notice','Path.Claim.Next']
        nodes['Path.Claim.Dispatch']['next']=follow
        nodes['Path.Claim.Receipt']['next']=follow
        nodes['Path.Claim.Notice']=recognition({'kind':'informational_ack'},'LongPress',duration=100,hits=4,
            post_delay=700,next_nodes=follow,timeout=45000)
        nodes['Path.Claim.Next']=recognition({'kind':'group_next',**args},'LongPress',duration=100,hits=1,
            next_nodes=['Path.Claim.Done'],post_delay=700,timeout=20000)
    return scope,nodes
