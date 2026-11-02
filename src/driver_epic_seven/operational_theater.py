"""Moonlight Theater compositions on the canonical observation; read-only."""
import re
import numpy as np
from .reading import ReadContext
from .observed_ui import fact, derived, node
from .profile import supports_reading

ANCHORS = {variant: tuple('theater_story_'+role+'_'+variant for role in ('speed','history','pause'))
           for variant in ('normal','black')}
# Color variants with masked foregrounds remain candidate assets. They no
# longer establish dialogue alone: the generic route requires shape + OCR.


def dialogue_keys(matches):
    return next((keys for keys in ANCHORS.values() if all(matches.get(k,{}).get('hit') for k in keys)), ())


SHAPES={
    'play':('theater_story_play_plain','Theater.Template.PlayShape',[1047,17,43,40]),
    'history':('theater_story_history_plain','Theater.Template.HistoryShape',[1108,17,37,38]),
    'pause':('theater_story_pause_plain','Theater.Template.PauseShape',[1163,18,27,35]),
}
BODY_ROI=[80,545,1052,90]


def shape_match(vision,frame,matcher,role):
    """Native filtered geometry plus visibility, independent of backdrop color.

    This is a separate composition recognizer, not a rescue of failed MAE
    candidates. It authorizes no action without current OCR/ink proof below.
    """
    base,name,expected=SHAPES[role]
    raw=matcher(name)
    candidates=[]
    if raw and raw.hit:
        for row in getattr(raw,'filtered_results',[]) or []:
            box=list(row.box) if row.box else None
            score=getattr(row,'score',None)
            if box!=expected or score is None or score<.94:continue
            x,y,w,h=box
            reference=vision.templates[base][0]
            mask=~((reference[:,:,1]>=250)&(reference[:,:,0]<=5)&(reference[:,:,2]<=5))
            patch=frame[y:y+h,x:x+w,:3].astype(float)
            pixels=patch[mask]
            if not len(pixels):continue
            luma=float(np.median(pixels.mean(axis=1)))
            neutral=float(((pixels.max(axis=1)-pixels.min(axis=1))<40).mean())
            background=patch[~mask]
            contrast=abs(luma-float(np.median(background.mean(axis=1)))) if len(background) else 0.0
            candidates.append({'box':box,'score':float(score),'median_luma':luma,
                'neutral_fraction':neutral,'contrast':contrast,'valid':85<=luma<=235 and neutral>=.8 and contrast>=10})
    valid=[r for r in candidates if r['valid']]
    best=max(valid,key=lambda r:r['score'],default=None)
    return {'hit':bool(best),'box':best['box'] if best else None,
        'score':best['score'] if best else None,'source_node':name,
        'validation':'native_filtered_shape_and_visible_neutral_glyphs_requires_ocr',
        'candidates':candidates}


def bright_ink(frame,row):
    x,y,w,h=map(int,row[1]['box'])
    patch=frame[y:y+h,x:x+w,:3]
    if patch.size==0:return 0.0
    # Dialogue is white even when the gray toolbar changes with its backdrop.
    return float(((patch.min(axis=2)>=235)&(patch.max(axis=2)-patch.min(axis=2)<25)).mean())


def generic_analysis(vision,frame,matcher,ocr,matches):
    geometry={role:shape_match(vision,frame,matcher,role) for role in SHAPES}
    matches.update({'theater_story_'+role+'_shape':value for role,value in geometry.items()})
    if not (geometry['play']['hit'] and geometry['history']['hit']):return None
    if geometry['pause']['hit']:
        rows=ocr(BODY_ROI)
        c=ReadContext({'text':rows},'',lambda _:None)
        valid=[row for row in c.find(r'.+',BODY_ROI)
               if sum(ch.isalpha() for ch in row[1]['text'])>=2 and bright_ink(frame,row)>=.02]
        if valid:
            row=max(valid,key=lambda row:len(row[1]['text']))
            matches['theater_dialogue_ink']={'hit':True,'box':row[1]['box'],
                'ocr_pointer':c.source(row)['pointer'],'bright_fraction':bright_ink(frame,row),
                'validation':'current_dialogue_ocr_and_white_ink'}
            return {'state':'unknown','matches':matches,'text':rows,'text_scope':'theater_dialogue_roi'}
    # Intro screens intentionally omit Pause. Their current title and explicit
    # tap prompt distinguish them from dialogue, combat, menus and ticket UI.
    rows=ocr([420,220,380,100])+ocr([420,590,410,75])
    c=ReadContext({'text':rows},'',lambda _:None)
    title=c.one(r'Act\s+\d+',[420,220,380,100])
    prompt=c.one(r'Tap\s+the\s+screen\s+again\s+to\s+skip[.]?',[420,590,410,75])
    if title and prompt and bright_ink(frame,title)>=.02:
        matches['theater_intro_text']={'hit':True,'box':title[1]['box'],
            'title_ocr_pointer':c.source(title)['pointer'],'prompt_ocr_pointer':c.source(prompt)['pointer'],
            'validation':'current_act_title_and_explicit_tap_instruction'}
        return {'state':'unknown','matches':matches,'text':rows,'text_scope':'theater_intro_roi'}
    return None


def fast_analysis(vision, frame, matcher, params, ocr=None):
    if not str(params.get('path',{}).get('kind','')).startswith('theater_'):
        return None
    matches = {}
    for keys in ANCHORS.values():
        if not all(k in vision.spec['templates'] for k in keys):
            return None
        for key in keys:
            matches[key] = vision.match_template(key,frame,matcher)
        if dialogue_keys(matches):
            return {'state':'unknown','matches':matches,'text':[],
                    'text_scope':'theater_dialogue_anchors_only'}
    if ocr is not None:
        return generic_analysis(vision,frame,matcher,ocr,matches)
    return None


def theater_nodes(observation, parent, add):
    if not supports_reading(observation) or observation.get('state','unknown')!='unknown':
        return None
    c=ReadContext(observation,parent,add)
    keys=dialogue_keys(observation.get('matches',{}))
    if keys:
        p=c.panel('theater_story',[],None,match_keys=keys)
        sources=[c.match_source(k) for k in keys]
        c.detail(p,stage_id=fact(),selection=fact(),dialogue_visible=fact(True,*sources))
        c.add(node(p+'/advance','control',p,semantic_id=fact('advance',*sources),adapter=fact('operations',*sources),
            box=fact([1100,610,1,1],*sources,derived('/matches','calibrated_theater_dialogue_tap_point')),
            box_role=fact('calibrated_point',*sources),visible=fact(True,*sources),consuming=fact(False,*sources)))
        return 'theater_story'
    generic_keys=tuple('theater_story_'+r+'_shape' for r in ('play','history','pause'))+('theater_dialogue_ink',)
    intro_keys=('theater_story_play_shape','theater_story_history_shape','theater_intro_text')
    for view,required in (('theater_story',generic_keys),('theater_intro',intro_keys)):
        if all(c.match(key) for key in required):
            anchors=c.find(r'.+',BODY_ROI) if view=='theater_story' else c.find(r'.+',[420,220,380,445])
            p=c.panel(view,anchors,None,match_keys=required)
            sources=[c.match_source(key) for key in required]+[c.source(r) for r in anchors]
            act_row=c.one(r'Act\s+\d+',[420,220,380,100]) if view=='theater_intro' else None
            c.detail(p,stage_id=fact(),selection=fact(),act=c.value(act_row,lambda text:int(re.search(r'\d+',text).group())),dialogue_visible=fact(view=='theater_story',*sources),
                     intro_visible=fact(view=='theater_intro',*sources),text_scope=fact(observation.get('text_scope'),*sources))
            c.add(node(p+'/advance','control',p,semantic_id=fact('advance',*sources),adapter=fact('operations',*sources),
                box=fact([1100,610,1,1],*sources,derived('/matches','calibrated_theater_nonconsuming_tap_point')),
                box_role=fact('calibrated_point',*sources),visible=fact(True,*sources),consuming=fact(False,*sources)))
            return view
    popup=c.one('Use Theater Ticket',(350,105,520,90))
    if popup:
        entry=c.one('Entry Ticket',(580,265,280,60))
        ticket=c.one('Theater Ticket',(580,300,280,60))
        owned=c.one(r'[O0]wned\s*:\s*\d[\d,]*',(440,350,230,65))
        confirm=c.one('Confirm',(620,465,170,70));cancel=c.one('Cancel',(440,465,140,70))
        p=c.panel('theater_ticket' if all((entry,ticket,owned,confirm,cancel)) else 'theater_blocked',
                  [r for r in (popup,entry,ticket,owned,confirm,cancel) if r], None)
        if all((entry,ticket,owned,confirm,cancel)):
            c.detail(p,owned=c.value(owned,lambda text:int(re.sub(r'[^0-9]','',text))),currency=fact('theater_ticket',c.source(ticket)))
            c.control(p,'confirm',confirm,consuming=True)
            c.control(p,'cancel',cancel,consuming=False)
            return 'theater_ticket'
        return 'theater_blocked'
    if c.find('Confirm|Cancel|Use Theater Ticket|Received Reward'):
        return None
    header=c.one('Moonlight Theater',(30,5,340,55))
    board=c.one('Cast Board',(95,600,190,70))
    watch=c.one('Watch',(735,600,110,65))
    ratio=c.one(r'\d[\d,]*\s*/\s*\d[\d,]*',(635,600,100,65))
    title=c.one(r'Act\s*\d+\s*[.:].+',(30,450,600,40))
    series=c.label((30,395,700,55))
    if not all((header,board,watch,ratio,title,series)):
        return None
    anchors=[header,board,watch,ratio,title,series]
    p=c.panel('theater_main',anchors,'wnd/story_theater_main.csb')
    cost=c.ratio(ratio,'cost','available')
    completed=[];completion_sources=[]
    for row in c.find(r'Act\s*\d+',(885,110,175,560)):
        index=int(re.search(r'\d+',row[1]['text']).group())
        x,y,w,h=row[1]['box']
        status=c.one('Rewards Available|Complete',(890,y+h,170,45))
        if status:
            completed.append(index);completion_sources += [c.source(row),c.source(status)]
    c.detail(p,act=c.value(title,lambda text:int(re.search(r'\d+',text).group())),
        act_title=c.value(title),series=c.value(series),ticket_cost=cost,
        completed_acts=fact(completed,*completion_sources,derived('/text','current_visible_act_completion_rows')),
        season=fact(),stage_id=fact())
    c.control(p,'watch',watch,'wnd/story_theater_main.csb','/Layer/RIGHT/btn_watch_pay',False)
    return 'theater_main'
