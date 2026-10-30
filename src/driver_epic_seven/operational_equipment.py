"""Current equipment fields and Auto Select composition, without I/O or input."""
import re
from .observed_ui import fact, derived


def augment_text(analysis, recognize):
    """Bounded Maa rereads only for missing fields of this proven composition."""
    from .reading import ReadContext
    from .stages import StageInspector
    c=ReadContext(analysis,'screen',lambda _:None)
    if not (c.one('Enhance Equipment',(0,0,400,65))
            and c.one('Enhancement Ingredients',(810,60,400,75))):return
    requests=[((680,5,150,50),r'\d{1,3}(?:[,.]\d{3})+', (728,14,101,36))]
    requests += [((1105,y+25,100,65),r'\d+(?:\s*\(-\d+\))?',(1108,y+35,86,35)) for y in (125,215,305,400)]
    for area,pattern,roi in requests:
        if c.find(pattern,area):continue
        extra=StageInspector._ocr(recognize,roi,only_rec=True)
        analysis['text'].extend(extra)


def attributes(c, *, preview=False, candidate=False):
    result={};sources=[]
    for name in ('Attack','Defense','Health'):
        label=c.one(name,(300,300,190,90) if preview else (90,380,150,80))
        if not label:
            result[name.lower()]=None;continue
        y=label[1]['box'][1]
        left,width=(665,78) if candidate else (480,100) if preview else (240,130)
        value=c.one(r'\d[\d,.]*(?:\s*[-+]\s*\d[\d,.]*)?',(left,y-7,width,37))
        if not value:
            result[name.lower()]=None;continue
        number=re.fullmatch(r'(\d[\d,.]*)(?:\s*[-+]\s*\d[\d,.]*)?',value[1]['text'].strip())[1]
        result[name.lower()]=int(re.sub(r'[,.]','',number));sources.extend((c.source(label),c.source(value)))
    return fact(result,*sources,derived('/text','current_scoped_primary_attributes_not_cp'))


def enhancement_nodes(c):
    heading=c.one('Enhance Equipment',(0,0,400,65))
    ingredients=c.one('Enhancement Ingredients',(810,60,400,75))
    kind=c.one(r'(?:Epic|Heroic|Rare|Good|Normal) (?:Weapon|Helmet|Armor|Necklace|Ring|Boots)',(120,85,250,45))
    name=c.label((125,123,240,55))
    if not all((heading,ingredients,kind,name)):return None
    if c.find('Confirm|Cancel',(300,200,500,350)):return 'stove_overlay_unresolved'
    options=c.find(r'\+(?:3|6|9|12|15) Level',(900,305,225,280))
    powder=c.one('Use Enhancement',(940,235,170,35))
    powder_only=c.one('Powder only',(940,258,170,35))
    if options or powder or powder_only:
        if len(options)!=5 or not powder or not powder_only:return 'stove_overlay_unresolved'
        p=c.panel('equipment_auto_select',[heading,ingredients,kind,name,powder,powder_only], 'wnd/unit_item_upgrade.csb','level_menu')
        c.detail(p,item_name=c.value(name),item_slot=c.value(kind,lambda s:s.split()[-1].lower()),
                 powder_only=fact(),item_instance_id=fact())
        for row in options:
            level=int(re.search(r'\d+',row[1]['text'])[0])
            c.control(p,'level:'+str(level),row,consuming=False)
        return 'equipment_auto_select'
    p=c.panel('item_enhancement',[heading,ingredients,kind,name], 'wnd/unit_item_upgrade.csb','equipment')
    xp=c.one(r'exp\s*\d[\d,]*\s*/\s*\d[\d,]*',(390,350,420,115))
    exp=(dict(zip(('current','maximum'),map(lambda s:int(s.replace(',','')),re.findall(r'\d[\d,]*',xp[1]['text'])))) if xp else None)
    costs=c.find(r'\d{1,3}(?:[,.]\d{3})+|0',(450,590,220,80))
    gold=costs[0] if len(costs)==1 else None
    balance=c.one(r'\d{1,3}(?:[,.]\d{3})+',(680,5,150,50))
    selected=[];material_sources=[];inventory_complete=True
    material_names=('Equipment Enhancement Powder','Lesser Equipment Charm','Greater Equipment Charm','Epic Equipment Charm')
    for y,expected_name in zip((125,215,305,400),material_names):
        rows=c.find(r'[A-Za-z][A-Za-z ]*',(925,y,180,43))
        rows=sorted(rows,key=lambda r:r[1]['box'][1])
        title=' '.join(r['text'].strip() for _,r in rows)
        quantity=c.one(r'\d+(?:\s*\(-\d+\))?',(1105,y+25,100,65))
        if title!=expected_name or not quantity:
            inventory_complete=False;continue
        parsed=re.fullmatch(r'(\d+)(?:\s*\(-(\d+)\))?',quantity[1]['text'].strip())
        material_sources.extend([*(c.source(r) for r in rows),c.source(quantity)])
        if parsed[2]:selected.append({'name':title,'remaining':int(parsed[1]),
                                     'available':int(parsed[1])+int(parsed[2]),'quantity':int(parsed[2])})
    empty=[]
    for slot in range(1,6):
        key='equipment_material_empty_'+str(slot);match=c.match(key);box=match.get('box') if match else None
        if (box and len(box)==4 and 410+74*(slot-1)<=box[0] and box[0]+box[2]<=484+74*(slot-1)
                and 410<=box[1] and box[1]+box[3]<=505):empty.append(key)
    selection_complete=(len(selected)==5-len(empty) and len(empty)>0)
    selection_sources=material_sources+[c.match_source(k) for k in empty]
    sources=[c.source(xp)] if xp else []
    c.detail(p,item_kind=fact('equipment',c.source(kind)),item_slot=c.value(kind,lambda s:s.split()[-1].lower()),
             item_name=c.value(name),item_instance_id=fact(),exp=c.value(xp),
             exp_value=fact(exp,*sources) if xp else fact(),
             enhancement_level=c.value(c.one(r'\+\d+',(600,170,80,55)),lambda s:int(s[1:])),
             preview_level_badge=c.value(c.one(r'\+\d+',(700,355,65,55)),lambda s:int(s[1:])),
             proposed_exp=fact(),
             gold_cost=c.value(gold,lambda s:int(re.sub(r'[,.]','',s))),
             gold_balance=c.value(balance,lambda s:int(re.sub(r'[,.]','',s))),
             selected_materials=fact(selected,*selection_sources) if selection_complete else fact(),
             empty_material_slots=fact(len(empty),*(c.match_source(k) for k in empty)) if empty else fact(),
             material_selection_complete=fact(selection_complete,*(selection_sources or [c.source(ingredients)])))
    c.control(p,'enhance',c.one('Enhance',(665,590,110,65)),consuming=True)
    c.control(p,'auto_select',c.one('Auto Select',(900,590,240,70)),consuming=False)
    c.control(p,'clear_materials',c.one('Empty',(395,590,140,75)),consuming=False)
    return 'item_enhancement'
