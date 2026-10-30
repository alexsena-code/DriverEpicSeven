"""Finite equipment operations with current item/material proof and no mission policy."""
from .path_execution import recognition
from .battle_operations import context, control, fresh_ticket
from .composition import validate_graph


def primary_attributes(value):
    return isinstance(value,dict) and all(type(value.get(k)) is int and value[k]>0 for k in ('attack','health'))


def target(current,params,observation,prepared):
    kind=params['kind'];hero=params['hero_name'];info=context(current)
    ticket=(prepared or {}).get('equipment:'+params['task_id'])
    valid=bool(ticket and ticket.get('hero_name')==hero and fresh_ticket(ticket,observation,120))
    if kind in ('equipment_equip_all','equipment_weapon'):
        return control(current,'equip_all' if kind=='equipment_equip_all' else 'weapon_slot',False) if (
            current.get('view')=='hero_equipment' and info.get('hero_name')==hero) else None
    if not valid:return None
    if kind=='equipment_no_better':
        return [0,0,1,1] if (current.get('view')=='hero_equipment' and info.get('hero_name')==hero
            and info.get('recommendation_status')=='no_better_equipment') else None
    if kind=='equipment_review_change':
        before,candidate=info.get('current_attributes'),info.get('candidate_attributes')
        return control(current,'review_change',False) if (current.get('view')=='equip_all_preview'
            and primary_attributes(before) and primary_attributes(candidate)
            and any(before[k]!=candidate[k] for k in ('attack','health'))) else None
    if kind=='equipment_confirm_change':
        if not (current.get('view')=='equipment_change_confirmation' and ticket.get('reviewed')
                and primary_attributes(ticket.get('candidate_attributes')) and info.get('gold_cost')==0):return None
        for key in ('current_cp','candidate_cp'):
            if info.get(key) is not None and ticket.get(key) is not None and info[key]!=ticket[key]:return None
        return control(current,'confirm_change',True)
    if kind=='equipment_equipped':
        wanted=ticket.get('candidate_attributes');actual=info.get('attributes')
        return [0,0,1,1] if (current.get('view')=='hero_equipment' and info.get('hero_name')==hero
            and primary_attributes(actual) and primary_attributes(wanted)
            and all(actual[k]==wanted[k] for k in ('attack','health'))) else None
    if kind=='equipment_open_enhancement':
        return control(current,'open_enhancement',False) if (current.get('view')=='equipment_detail'
            and info.get('item_kind')=='weapon' and info.get('item_name')) else None
    same_item=info.get('item_name')==ticket.get('item_name') and bool(ticket.get('item_name'))
    if kind=='equipment_snapshot':
        return [0,0,1,1] if (current.get('view')=='item_enhancement' and same_item
            and info.get('item_slot')=='weapon' and isinstance(info.get('exp_value'),dict)) else None
    if kind=='equipment_auto_materials':
        return control(current,'auto_select',False) if current.get('view')=='item_enhancement' and same_item else None
    if kind=='equipment_choose_level':
        return control(current,'level:'+str(params['auto_level']),False) if current.get('view')=='equipment_auto_select' and same_item else None
    if kind=='equipment_preview':
        return [0,0,1,1] if current.get('view')=='item_enhancement' and same_item else None
    if kind=='equipment_enhance':
        gold,balance=info.get('gold_cost'),info.get('gold_balance');materials=info.get('selected_materials')
        exp=info.get('exp_value');before=ticket.get('before_exp_value')
        if not (current.get('view')=='item_enhancement' and same_item and info.get('item_slot')=='weapon'
                and type(gold) is int and 0<gold<=params.get('max_gold',0) and type(balance) is int and balance>=gold
                and isinstance(exp,dict) and isinstance(before,dict) and exp['current']>before['current']
                and info.get('material_selection_complete') is True and isinstance(materials,list) and materials):return None
        limits=params.get('material_limits',{})
        if any(type(m.get('quantity')) is not int or m['quantity']<=0 or type(m.get('available')) is not int
               or m['available']<m['quantity'] or m['quantity']>limits.get(m.get('name'),0) for m in materials):return None
        return control(current,'enhance',True)
    if kind=='equipment_enhanced':
        exp=info.get('exp_value')
        paid=(type(ticket.get('gold_balance')) is int and type(ticket.get('gold_cost')) is int
              and info.get('gold_balance')==ticket['gold_balance']-ticket['gold_cost'])
        changed=isinstance(exp,dict) and exp!=ticket.get('before_exp_value')
        cleared=info.get('material_selection_complete') is True and info.get('selected_materials')==[]
        return [0,0,1,1] if (current.get('view')=='item_enhancement' and same_item and paid and changed and cleared) else None
    if kind=='equipment_back':
        return [0,0,1,1] if ticket.get('applied') and current.get('view') in ('item_enhancement','equipment_detail') and same_item else None
    if kind=='equipment_returned':
        return [0,0,1,1] if ticket.get('applied') and current.get('view')=='hero_equipment' and info.get('hero_name')==hero else None
    return None


def graph(task_id,settings,*,operation,preview=False,finish=False):
    if not isinstance(task_id,str) or not task_id.strip():raise ValueError('Escopo persistente ausente.')
    hero=settings.get('hero_name')
    if not isinstance(hero,str) or not hero.strip():raise ValueError('Escolha um herói cuja identidade atual possa ser comprovada.')
    if preview and finish:raise ValueError('Prévia e reconciliação são operações distintas.')
    common={'task_id':task_id,'hero_name':hero};p='Path.Equipment.'+('Equip.' if operation=='equip_all' else 'Enhance.')
    def node(kind,action='DoNothing',following=(),**extra):
        return recognition({'kind':kind,**common,**extra},action,duration=100,post_delay=500,next_nodes=following,timeout=20000)
    if operation=='equip_all':
        nodes={p+'Entry':{'recognition':'DirectHit','action':'DoNothing','next':[p+'Returned',p+'Done'] if finish else [p+'Preview']},
          p+'Done':node('equipment_equipped',following=[p+'Returned']),p+'Returned':node('equipment_returned'),
          p+'NoBetter':node('equipment_no_better')}
        if not finish:
            nodes.update({p+'Preview':node('equipment_equip_all','LongPress',[p+'NoBetter',p+'Review']),
                p+'Review':node('equipment_review_change','LongPress',[p+'Apply']),
                p+'Apply':node('equipment_confirm_change','DoNothing' if preview else 'LongPress',
                               () if preview else [p+'Done'],**({} if preview else {'consuming':True}))})
        success=(p+'Apply' if preview else p+'Returned',p+'NoBetter')
    elif operation=='enhance_weapon':
        gold=settings.get('max_gold',0);level=settings.get('auto_level',3);limits=settings.get('material_limits',{})
        if type(gold) is not int or gold<0 or (not preview and not finish and gold==0):raise ValueError('Informe orçamento positivo de ouro.')
        if level not in (3,6,9,12,15):raise ValueError('Opção Auto Select fora do menu mapeado.')
        if not isinstance(limits,dict) or any(not isinstance(k,str) or type(v) is not int or v<0 for k,v in limits.items()):raise ValueError('Limites de materiais inválidos.')
        if not preview and not finish and not limits:raise ValueError('A aplicação exige limites explícitos de materiais.')
        nodes={p+'Entry':{'recognition':'DirectHit','action':'DoNothing','next':[p+'Returned',p+'Back',p+'Done'] if finish else [p+'Weapon']},
          p+'Done':node('equipment_enhanced',following=[p+'Back']),
          p+'Back':recognition({'kind':'equipment_back',**common},'LongPressKey',key=[27],duration=100,hits=2,
                 next_nodes=[p+'Returned',p+'Back'],post_delay=500,timeout=20000),
          p+'Returned':node('equipment_returned')}
        if not finish:
            nodes.update({p+'Weapon':recognition({'kind':'equipment_weapon',**common},'LongPress',duration=100,hits=2,
                    next_nodes=[p+'Open',p+'Weapon'],post_delay=500,timeout=20000),
                p+'Open':node('equipment_open_enhancement','LongPress',[p+'Snapshot']),
                p+'Snapshot':node('equipment_snapshot',following=[p+'Materials']),
                p+'Materials':node('equipment_auto_materials','LongPress',[p+'Choose']),
                p+'Choose':node('equipment_choose_level','LongPress',[p+'Preview'],auto_level=level),
                p+'Preview':node('equipment_preview',following=[] if preview else [p+'Apply']),
                p+'Apply':node('equipment_enhance','LongPress',[p+'Done'],consuming=True,max_gold=gold,material_limits=limits)})
            if preview:nodes.pop(p+'Apply')
        success=p+'Preview' if preview else p+'Returned'
    else:raise ValueError('Operação de equipamento fora do escopo mapeado.')
    validate_graph(nodes,p+'Entry',resume=finish or preview)
    return {'task_id':task_id,'equipment_operation':operation,'hero_name':hero,'max_starts':0,'energy_limit':0,
            'gold_limit':settings.get('max_gold',0) if operation=='enhance_weapon' else 0,
            'preview_only':preview,'finish_current':finish,'mission_credit_requires_path_read':True},nodes,p+'Entry',success
