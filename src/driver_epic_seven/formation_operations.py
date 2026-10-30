"""Bounded formation operations over the canonical tree, scheduled only by Maa."""
from .observed_ui import formation_view,operation_view
from .battle_operations import context,control,fresh_ticket
from .path_execution import recognition
from .composition import validate_graph
from .operational_formation import POSITIONS


def target(observation,params,prepared):
    kind=params['kind'];f=formation_view(observation);info=context(f)
    source=params.get('source');dest=params.get('destination');name=params.get('member_name')
    ticket=(prepared or {}).get('formation:'+params['task_id'])
    valid=bool(ticket and fresh_ticket(ticket,observation,180) and ticket.get('member_name')==name)
    position=dest if params.get('after') else source
    if kind=='formation_select':return control(f,'select:'+position,False)
    if kind=='formation_selected':return [0,0,1,1] if f.get('selected_position')==position else None
    if kind=='formation_details':return control(f,'member_details',False) if f.get('selected_position')==position else None
    if kind in ('formation_identity','formation_applied'):
        c=operation_view(observation)
        return [0,0,1,1] if c.get('view') in ('hero_detail','hero_equipment') and context(c).get('hero_name')==name else None
    if kind=='formation_back':
        c=operation_view(observation)
        return [0,0,1,1] if c.get('view') in ('hero_detail','hero_equipment') and context(c).get('hero_name')==name else None
    if kind=='formation_candidate':return control(f,'candidate:'+name,False)
    if kind=='formation_add':return control(f,'candidate_add',False) if info.get('candidate_name')==name else None
    if kind=='formation_reposition':
        return control(f,'swap:'+dest,True) if valid and ticket.get('identity_verified') and f.get('selected_position')==source else None
    if kind=='formation_remove':
        return control(f,'remove_member',True) if valid and ticket.get('identity_verified') and f.get('selected_position')==source else None
    if kind=='formation_assign':
        if not valid or info.get('candidate_name')!=name:return None
        return control(f,'assign:'+dest,True) or control(f,'swap:'+dest,True)
    if kind=='formation_removed':
        return [0,0,1,1] if valid and info.get('empty_position')==source else None
    if kind=='formation_returned':return [0,0,1,1] if valid and ticket.get('applied') and f else None
    return None


def graph(scope,operation,*,source=None,destination=None,member_name=None,finish=False):
    if not isinstance(scope,str) or not scope.strip():raise ValueError('Escopo persistente de formação ausente.')
    if operation not in ('select','reposition','remove','assign','substitute'):raise ValueError('Operação de formação não mapeada.')
    if operation in ('select','reposition','remove') and source not in POSITIONS:raise ValueError('Posição visual de origem ausente.')
    if operation in ('reposition','assign','substitute') and destination not in POSITIONS:raise ValueError('Posição visual de destino ausente.')
    if operation=='reposition' and source==destination:raise ValueError('Origem e destino são iguais.')
    if operation=='remove' and source!='left':raise ValueError('Prova de slot vazio calibrada somente para posição esquerda.')
    if operation!='select' and (not isinstance(member_name,str) or not member_name.strip()):raise ValueError('Nome atual necessário para comprovar integrante/candidato.')
    common={'task_id':scope,'source':source,'destination':destination,'member_name':member_name}
    prefix='Formation.'
    def n(kind,action='DoNothing',following=(),**extra):
        return recognition({'kind':'formation_'+kind,**common,**extra},action,duration=100,post_delay=700,next_nodes=following,timeout=15000)
    nodes={prefix+'Entry':{'recognition':'DirectHit','action':'DoNothing','next':[prefix+'SourceSelected',prefix+'Source']},
           prefix+'Source':n('select','LongPress',[prefix+'SourceSelected']),
           prefix+'SourceSelected':n('selected')}
    if operation=='select':success=prefix+'SourceSelected'
    else:
        if operation in ('assign','substitute'):
            nodes={prefix+'Entry':{'recognition':'DirectHit','action':'DoNothing','next':[prefix+'Candidate']},
                   prefix+'Candidate':n('candidate','LongPress',[prefix+'Add']),
                   prefix+'Add':n('add','LongPress',[prefix+'Mutate']),
                   prefix+'Mutate':n('assign','LongPress',[prefix+'DestSelect'],consuming=True)}
        else:
            nodes[prefix+'SourceSelected']['next']=[prefix+'DetailsBefore']
            nodes.update({prefix+'DetailsBefore':n('details','LongPress',[prefix+'IdentityBefore']),
                prefix+'IdentityBefore':n('identity',following=[prefix+'BackBefore']),
                prefix+'BackBefore':recognition({'kind':'formation_back',**common},'LongPressKey',key=[27],duration=100,
                    post_delay=700,next_nodes=[prefix+'ReadyMutation',prefix+'Reselect'],timeout=15000),
                prefix+'Reselect':n('select','LongPress',[prefix+'ReadyMutation']),
                prefix+'ReadyMutation':n('selected',following=[prefix+'Mutate']),
                prefix+'Mutate':n('remove' if operation=='remove' else 'reposition','LongPress',
                    [prefix+'Removed'] if operation=='remove' else [prefix+'DestSelect'],consuming=True)})
        if operation=='remove':
            nodes[prefix+'Removed']=n('removed');success=prefix+'Removed'
        else:
            nodes.update({prefix+'DestSelect':n('select','LongPress',[prefix+'DestSelected'],after=True),
                prefix+'DestSelected':n('selected',following=[prefix+'DetailsAfter'],after=True),
                prefix+'DetailsAfter':n('details','LongPress',[prefix+'IdentityAfter'],after=True),
                prefix+'IdentityAfter':n('applied',following=[prefix+'BackAfter'],after=True),
                prefix+'BackAfter':recognition({'kind':'formation_back',**common},'LongPressKey',key=[27],duration=100,
                    post_delay=700,next_nodes=[prefix+'Returned'],timeout=15000),
                prefix+'Returned':n('returned')})
            success=prefix+'Returned'
    if finish:
        if operation in ('select','remove'):raise ValueError('Reconciliação automatizada exige destino e identidade final; remoção legada requer leitura explícita do vazio.')
        keep={'Formation.Entry','Formation.DestSelect','Formation.DestSelected','Formation.DetailsAfter',
              'Formation.IdentityAfter','Formation.BackAfter','Formation.Returned'}
        nodes={k:v for k,v in nodes.items() if k in keep}
        nodes[prefix+'Entry']['next']=[prefix+'Returned',prefix+'DestSelected',prefix+'DestSelect',prefix+'IdentityAfter']
        assert not any(v.get('custom_recognition_param',{}).get('path',{}).get('consuming') for v in nodes.values())
    validate_graph(nodes,prefix+'Entry',[success])
    return nodes,prefix+'Entry',success
