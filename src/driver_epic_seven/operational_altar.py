"""Spirit Altar panels from one current observation; no capture or input."""
import re
import math

from .observed_ui import fact, derived, node


_STAGE = r'(?P<altar>[A-Za-z][A-Za-z ’\x27]+ Spirit Altar)\s*[-–]\s*(?P<difficulty>[A-Za-z]+)'
_DIFFICULTIES = {'easy','normal','hard','hell'}


def _stage(row):
    if row is None:
        return None
    match=re.fullmatch(_STAGE,row[1]['text'].strip(),re.I)
    return (match['altar'].strip(),match['difficulty'].lower()) if match else None


def altar_nodes(c):
    if c.state not in ('unknown','battle_ready'):
        return None
    clear=_clear_banner(c)
    if clear:
        return clear
    ready=c.one('Ready',(40,5,200,60))
    altar_team=c.one(r'Spirit Altar\s*-?',(5,65,135,65))
    enemies=c.one(r'(?:[Xx]\s*)?Enemies',(875,245,300,65))
    rewards=c.one('Obtainable Rewards',(870,410,330,70))
    if ready and altar_team and enemies and rewards:
        if (c.find('Confirm|Cancel',(300,200,600,350))
                or c.find(r'(?:[Xx×]\s*)?Tap\s*to\s*close[.]?',(350,400,600,282))):
            return 'stove_overlay_unresolved'
        return _preparation(c,ready,altar_team,enemies,rewards)
    battle=c.one('Battle',(40,5,220,60))
    title=c.one('Spirit Altar',(15,120,290,75))
    available=c.one('Available Altars',(970,75,235,65))
    rows=c.find(_STAGE,(720,135,245,420))
    if battle and title and available and rows:
        if (c.find('Confirm|Cancel',(300,200,600,350))
                or c.find(r'(?:[Xx×]\s*)?Tap\s*to\s*close[.]?',(350,400,600,282))):
            return 'stove_overlay_unresolved'
        return _hub(c,battle,title,available,rows)
    return None


def _bounded_marker(c,key,area):
    marker=c.match(key);box=marker.get('box') if marker else None
    if (not isinstance(box,(list,tuple)) or len(box)!=4
            or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in box)):
        return None
    x,y,w,h=box;ax,ay,aw,ah=area
    return list(box) if w>0 and h>0 and ax<=x and ay<=y and x+w<=ax+aw and y+h<=ay+ah else None


def _clear_banner(c):
    # The persistent Abyss result also contains CLEAR and a dim HUD. Its
    # explicit footer belongs to the specific result reader, not tap-to-advance.
    if all((c.one('Abyss',(400,345,410,75)), c.one(r'Floor\s+\d+',(400,395,410,75)),
            c.one('Conquer Reward',(400,435,410,80)), c.one('Back',(0,590,1212,92)),
            c.one('Next Floor',(0,590,1212,92)))):
        return None
    heading=_bounded_marker(c,'path_battle_clear_heading',(450,220,310,110))
    hud=_bounded_marker(c,'path_battle_clear_dim_hud',(925,5,65,60))
    if not (heading and hud):
        return None
    if (c.find('Confirm|Cancel',(300,200,600,350))
            or c.find(r'(?:[Xx×]\s*)?Tap\s*to\s*close[.]?',(350,400,600,282))):
        return 'stove_overlay_unresolved'
    keys=('path_battle_clear_heading','path_battle_clear_dim_hud')
    sources=[c.match_source(key) for key in keys]
    p=c.panel('battle_clear_banner',[],'wnd/result_base.csb',match_keys=keys)
    c.detail(p,result=fact('victory',*sources,derived('/matches','current_clear_caption_and_battle_hud')),
             victory_announced=fact(True,*sources),earned_stars=fact(),mode_identity=fact(),stage_id=fact(),
             battle_id=fact(),reward_claimed=fact(),mission_credit=fact())
    c.add(node(p+'/advance','control',p,
               semantic_id=fact('advance',*sources),adapter=fact('operations',*sources),
               text=fact('CLEAR',sources[0]),box=fact(heading,sources[0]),
               box_role=fact('template_extent',sources[0]),label_box=fact(heading,sources[0]),
               visible=fact(True,*sources),consuming=fact(False,*sources,derived('/matches','calibrated_result_navigation')),
               gesture=fact('tap',*sources),navigation_template_verified=fact(True,*sources),
               navigation_destinations=fact([{'view':'battle_rewards'}],*sources),
               layout_reference={'source':'wnd/result_base.csb','path':'/Layer/n_buttons/CENTER/btn_move_next',
                                 'scope':'declared_full_screen_button_with_live_transition'}))
    return 'battle_clear_banner'


def _hub(c,battle,title,available,rows):
    rows=sorted(rows,key=lambda row:row[1]['box'][1])
    p=c.panel('spirit_altar_hub',[battle,title,available], 'wnd/dungeon.csb','spirit_altar')
    names={_stage(row)[0] for row in rows}
    options=c.find(r'[A-Za-z][A-Za-z ’\x27]+ Spirit Altar',(975,130,235,500))
    c.detail(p,mode_label=c.value(title),listed_altar_name=(fact(next(iter(names)),*(c.source(r) for r in rows))
             if len(names)==1 else fact()),selected_altar_name=fact(),selected_difficulty=fact(),
             altar_names=fact([r['text'].strip() for _,r in options],*(c.source(r) for r in options)) if options else fact(),
             current_stage_id=fact(),entry_cost=fact(),owned_team=fact())
    for index,row in enumerate(rows):
        name,difficulty=_stage(row);y=row[1]['box'][1]
        status=c.one(r'Available|(?:B\s*)?Locked',(720,y+18,245,55))
        availability=(True if status and status[1]['text'].strip().lower()=='available' else
                      False if status else None)
        known=difficulty in _DIFFICULTIES
        unique=sum(_stage(other)[1]==difficulty for other in rows)==1
        key='difficulty:'+difficulty if known and unique else 'difficulty_row:'+str(index)
        c.item(p,key,row,altar_name=fact(name,c.source(row)),difficulty=fact(difficulty,c.source(row)) if known else fact(),
               difficulty_label=fact(re.split(r'\s*[-–]\s*',row[1]['text'].strip())[-1],c.source(row)),
               availability_label=c.value(status),available=fact(availability,c.source(status)) if status else fact(),
               stage_id=fact(),selected=fact(),box=fact(row[1]['box'],c.source(row)),box_role=fact('text_anchor',c.source(row)),
               layout_reference={'source':'wnd/dungeon.csb','path':'/Layer/RIGHT/n_sub/sub_Weekly/n_floors/weekly_stage_scrollview',
                                 'scope':'static_container_hint_dynamic_row_binding_unknown'})
        if known and unique and len(names)==1 and availability is True:
            c.control(p,'open_difficulty:'+difficulty,row,'wnd/dungeon.csb',consuming=False,
                      navigation=[{'view':'spirit_altar_preparation'}])
    return 'spirit_altar_hub'


def _preparation(c,ready,altar_team,enemies,rewards):
    short=c.one(r'[A-Za-z][A-Za-z ’\x27]+ Spirit Altar',(870,65,330,45))
    stage=c.one(_STAGE,(870,105,330,45))
    parts=_stage(stage)
    conflict=bool(short and parts and short[1]['text'].strip().casefold()!=parts[0].casefold())
    name=(fact(parts[0],c.source(stage)) if parts and not conflict else fact())
    difficulty=(fact(parts[1],c.source(stage)) if parts and parts[1] in _DIFFICULTIES and not conflict else fact())
    start=c.one('Start',(1020,595,170,65))
    ratio=c.ratio(c.one(r'\d[\d,]*\s*/\s*\d[\d,]*',(900,590,120,75)),'cost','available')
    cost=fact({'currency':'energy',**ratio['value']},*ratio['sources']) if ratio['value'] else fact()
    cp=c.one(r'\d[\d,.]*',(210,610,190,65))
    teams=c.find(r'Team\s*\d+',(5,85,130,285))
    levels=c.find(r'\d{1,3}',(180,140,420,220))
    p=c.panel('spirit_altar_preparation',[ready,altar_team,enemies,rewards], 'wnd/battle_ready.csb','spirit_altar')
    c.detail(p,altar_name=name,altar_label=c.value(short),stage_label=c.value(stage),difficulty=difficulty,
             identity_conflict=fact(conflict,c.source(short),c.source(stage)) if short and stage else fact(),
             cost=cost,team_cp=c.value(cp,lambda s:int(re.sub(r'[,.]','',s))),
             team_label=fact(),selected_team_id=fact(),hero_instances=fact(),stage_id=fact(),
             visible_team_labels=fact([r['text'].strip() for _,r in teams],*(c.source(r) for r in teams)) if teams else fact(),
             visible_hero_levels=fact([int(r['text'].strip()) for _,r in levels],*(c.source(r) for r in levels)) if levels else fact(),
             preparation_composition_verified=fact(True,c.source(ready),c.source(altar_team),c.source(enemies),c.source(rewards)),
             entered=fact(),victory=fact())
    c.control(p,'start',start,'wnd/battle_ready.csb',consuming=True)
    return 'spirit_altar_preparation'
