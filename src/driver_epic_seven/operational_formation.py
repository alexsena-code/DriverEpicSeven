"""Current formation controls; positions are visual labels, never game slot IDs."""
import re
from .observed_ui import fact,derived,node
from .reading import ReadContext

POSITIONS=('upper','left','right','lower')
LEVEL_AREAS={'upper':(350,100,105,85),'left':(230,175,95,95),'right':(490,135,100,90),'lower':(385,245,95,90)}
POINTS={'upper':[330,347,1,1],'left':[206,426,1,1],'right':[550,390,1,1],'lower':[410,490,1,1]}
REMOVE_CENTERS={'upper':(363,258),'left':(239,345),'right':(488,338),'lower':(374,408)}


def formation_nodes(observation,parent,add):
    if observation.get('state') not in ('battle_ready','unknown') or observation.get('window',{}).get('client_size',[1212,682])!=[1212,682]:return
    c=ReadContext(observation,parent,add)
    remove,details=(c.match(k) for k in ('formation_remove','formation_details'))
    selected=None
    if remove and details and remove.get('box') and details.get('box'):
        a,b=remove['box'],details['box'];x,y=a[0]+a[2]/2,a[1]+a[3]/2
        if 55<=(b[0]+b[2]/2)-x<=115 and abs(y-(b[1]+b[3]/2))<=25:
            positions=[k for k,(px,py) in REMOVE_CENTERS.items() if abs(x-px)<=26 and abs(y-py)<=26]
            if len(positions)==1:selected=positions[0]
    ready=c.one('Ready',(0,0,250,65));team=c.find(r'.*Team.*',(0,65,160,80))
    levels={k:c.one(r'(?:[1-9]|[1-5][0-9]|60)',area) for k,area in LEVEL_AREAS.items()}
    markers=[k for k in c.observation.get('matches',{}) if k.startswith(('formation_swap_','formation_assign_')) and c.match(k)]
    search=c.one('Search',(1080,60,130,55))
    if observation.get('state')=='unknown' and not (ready and team and (
            selected or markers or c.match('formation_empty_left') or c.match('start_quest_label'))):return
    # Preserve the old native overlay even when its text is unreadable.
    if not selected and not (ready and team and (sum(bool(v) for v in levels.values())>=3 or markers or c.match('formation_empty_left'))):return
    source=derived('/matches','current_formation_composition_and_native_controls')
    owner='formation:selection'
    add(node(owner,'panel',parent,semantic_id=fact('formation',source),adapter=fact('formation',source),
             view=fact('formation_selection' if selected else 'formation',source),visible=fact(True,source),
             blocks_preparation=fact(bool(selected or markers or search),source),
             selected_position=fact(selected,source),selected_member_id=fact(),selected_slot=fact(),team_members=fact()))
    def item(suffix,**fields):
        add(node(owner+'/'+suffix,'item',owner,semantic_id=fact(suffix,source),adapter=fact('formation',source),**fields))
    def control(name,box,src,consuming=False,role=None):
        add(node(owner+'/'+name,'control',owner,semantic_id=fact(name,src),adapter=fact('formation',src),
                 box=fact(box,src),box_role=fact(role or ('template_extent' if src.get('kind')=='recognition' else 'text_anchor'),src),
                 consuming=fact(consuming,src),visible=fact(True,src)))
    name=c.label((974,230,237,40)) if search else None
    # This is the highlighted candidate, not evidence that it is in the team.
    item('context',selected_position=fact(selected,source),candidate_name=c.value(name),
         member_instance_id=fact(),candidate_instance_id=fact(),selection_applied=fact(),
         empty_position=fact('left',c.match_source('formation_empty_left')) if c.match('formation_empty_left') else fact(),
         visible_levels=fact({k:int(row[1]['text']) for k,row in levels.items() if row},source,*(c.source(row) for row in levels.values() if row)))
    for k,row in levels.items():
        if row:control('select:'+k,POINTS[k],derived('/text','calibrated_visual_platform_'+k+'_1212x682_with_current_level_badge'),role='calibrated_point')
    if selected:
        control('remove_member',remove['box'],c.match_source('formation_remove'),True)
        control('member_details',details['box'],c.match_source('formation_details'))
    for key in markers:control(key.removeprefix('formation_').replace('_',':',1),c.match(key)['box'],c.match_source(key),True)
    if name and c.match('formation_candidate_add'):
        control('candidate_add',c.match('formation_candidate_add')['box'],c.match_source('formation_candidate_add'))
    if search:
        candidates={}
        for row in c.find(r"[A-Za-z][A-Za-z '\-]+",(970,110,240,470)):
            text=row[1]['text'].strip()
            if text in ('Max','Search'):continue
            candidates.setdefault(text,[]).append(row)
        for text,rows in candidates.items():
            if len(rows)==1:control('candidate:'+text,rows[0][1]['box'],c.source(rows[0]))


def augment_text(analysis,recognize):
    """Reread only the highlighted name, excluding the class icon; never lower OCR confidence."""
    c=ReadContext(analysis,'screen',lambda _:None)
    if (analysis.get('state')=='battle_ready' and c.one('Ready',(0,0,250,65))
            and c.one('Search',(1080,60,130,55))):
        from .stages import StageInspector
        analysis['text'].extend(StageInspector._ocr(recognize,(974,230,237,40),only_rec=True))
