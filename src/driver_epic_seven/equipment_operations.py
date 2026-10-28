"""Group-2 equipment units over current composed panels; no item-ID inference."""
import re
import time

from .path_execution import recognition


def target(current,params,observation,prepared):
    kind=params['kind'];hero=params['hero_name']
    contexts=[i for i in current.get('items',[]) if i.get('semantic_id')=='context']
    info=contexts[0] if len(contexts)==1 else {}
    def control(name):
        found=[c for c in current.get('controls',[]) if c.get('semantic_id')==name]
        return found[0].get('box') if len(found)==1 else None
    if kind in ('equipment_equip_all','equipment_weapon'):
        if current.get('view')!='hero_equipment' or info.get('hero_name')!=hero:return None
        return control('equip_all' if kind=='equipment_equip_all' else 'weapon_slot')
    if kind=='equipment_review_change':
        a,b=info.get('current_cp'),info.get('candidate_cp')
        origin=(prepared or {}).get('equipment:'+params['task_id'],{})
        return control('review_change') if (current.get('view')=='equip_all_preview'
            and origin.get('hero_name')==hero and origin.get('window')==observation.get('window')
            and isinstance(a,int) and isinstance(b,int) and 0<a<b) else None
    ticket=(prepared or {}).get('equipment:'+params['task_id'])
    if not ticket or ticket.get('hero_name')!=hero or ticket.get('window')!=observation.get('window'):
        return None
    if not 0<=time.time()-ticket['epoch_seconds']<=120:return None
    if kind=='equipment_confirm_change':
        return control('confirm_change') if (current.get('view')=='equipment_change_confirmation'
            and info.get('current_cp')==ticket.get('current_cp')
            and info.get('candidate_cp')==ticket.get('candidate_cp')) else None
    if kind=='equipment_equipped':
        return [0,0,1,1] if (current.get('view')=='hero_equipment' and info.get('hero_name')==hero
            and isinstance(ticket.get('candidate_cp'),int) and info.get('cp')==ticket['candidate_cp']) else None
    if kind=='equipment_open_enhancement':
        return control('open_enhancement') if (current.get('view')=='equipment_detail'
            and info.get('item_kind')=='weapon' and info.get('item_name')) else None
    if kind=='equipment_auto_materials':
        return control('auto_select') if (current.get('view')=='item_enhancement' and info.get('item_kind')=='equipment') else None
    if kind=='equipment_enhance':
        gold=info.get('gold_cost');xp=info.get('proposed_exp');balance=info.get('gold_balance')
        if (current.get('view')!='item_enhancement' or info.get('item_kind')!='equipment'
                or not ticket.get('item_name')
                or not isinstance(gold,int) or isinstance(gold,bool)
                or not isinstance(balance,int) or balance<gold
                or not 0<gold<=params.get('max_gold',0) or not isinstance(xp,int) or xp<=0
                or (not isinstance(ticket.get('before_level'),int) and not info.get('exp'))):return None
        return control('enhance')
    if kind=='equipment_enhanced':
        # The changed native enhancement value is proof of an application,
        # not an internal inventory-instance identity or mission credit.
        level_changed=(isinstance(info.get('enhancement_level'),int) and isinstance(ticket.get('before_level'),int)
                       and info['enhancement_level']>ticket['before_level'])
        expense_verified=(isinstance(ticket.get('gold_balance'),int) and isinstance(ticket.get('gold_cost'),int)
            and info.get('gold_balance')==ticket['gold_balance']-ticket['gold_cost']
            and ticket.get('before_exp') and info.get('exp') and info['exp']!=ticket['before_exp']
            and not info.get('proposed_exp'))
        return [0,0,1,1] if current.get('view')=='item_enhancement' and (level_changed or expense_verified) else None
    return None


def graph(task_id,settings,*,preview=False):
    hero=settings.get('hero_name')
    if not isinstance(hero,str) or not hero.strip():raise ValueError('Escolha um herói cuja identidade atual possa ser comprovada.')
    common={'task_id':task_id,'hero_name':hero}
    if task_id=='guide_02_004_001':
        p='Path.Equipment.Equip.'
        nodes={p+'Entry':{'recognition':'DirectHit','action':'DoNothing','next':[p+'Preview']},
            p+'Preview':recognition({'kind':'equipment_equip_all',**common},'LongPress',duration=100,
                next_nodes=[p+'Review'],post_delay=700,timeout=15000),
            p+'Review':recognition({'kind':'equipment_review_change',**common},'LongPress',duration=100,
                next_nodes=[p+'Apply'],post_delay=700,timeout=15000),
            p+'Apply':recognition({'kind':'equipment_confirm_change',**common,'consuming':True},'LongPress',duration=100,
                next_nodes=[p+'Done'],post_delay=1000,timeout=20000),
            p+'Done':recognition({'kind':'equipment_equipped',**common})}
    elif task_id=='guide_02_003_001':
        max_gold=settings.get('max_gold',0)
        if not isinstance(max_gold,int) or isinstance(max_gold,bool) or max_gold<=0:raise ValueError('Informe um orçamento de ouro positivo.')
        p='Path.Equipment.Enhance.'
        nodes={p+'Entry':{'recognition':'DirectHit','action':'DoNothing','next':[p+'Weapon']},
            p+'Weapon':recognition({'kind':'equipment_weapon',**common},'LongPress',duration=100,
                next_nodes=[p+'Open'],post_delay=700,timeout=15000),
            p+'Open':recognition({'kind':'equipment_open_enhancement',**common},'LongPress',duration=100,
                next_nodes=[p+'Materials'],post_delay=700,timeout=15000),
            p+'Materials':recognition({'kind':'equipment_auto_materials',**common},'LongPress',duration=100,
                next_nodes=[p+'Apply'],post_delay=700,timeout=15000),
            p+'Apply':recognition({'kind':'equipment_enhance',**common,'consuming':True,'max_gold':max_gold},'LongPress',duration=100,
                next_nodes=[p+'Done'],post_delay=1200,timeout=25000),
            p+'Done':recognition({'kind':'equipment_enhanced',**common})}
    else:raise ValueError('Unidade de equipamento limitada às missões mapeadas do grupo 2.')
    success=p+'Done'
    if preview:
        nodes[p+'Apply']['action']='DoNothing'
        nodes[p+'Apply']['custom_recognition_param']['path'].pop('consuming',None)
        nodes[p+'Apply'].pop('next',None)
        success=p+'Apply'
    return {'task_id':task_id,'hero_name':hero,'max_starts':0,'energy_limit':0,
            'gold_limit':settings.get('max_gold',0) if task_id=='guide_02_003_001' else 0,
            'preview_only':preview,'mission_credit_requires_path_read':True},nodes,p+'Entry',success
