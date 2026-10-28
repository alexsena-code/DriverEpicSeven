"""Generic battle exit footer; a retained HUD does not prove combat is active."""
import math

from .observed_ui import fact, derived, node
from .operational_stove import ReadContext
from .profile import supports_reading


def battle_end_nodes(observation,parent,add):
    if (not supports_reading(observation)
            or observation.get('state') not in ('unknown','battle_running','battle_nightmare_keeper','battle_mercenary_lydia')):
        return None
    c=ReadContext(observation,parent,add)
    marker=c.match('path_battle_exit_lobby');box=marker.get('box') if marker else None
    if (not isinstance(box,(list,tuple)) or len(box)!=4
            or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in box)):
        return None
    x,y,w,h=box
    if not (w>0 and h>0 and 175<=x and x+w<=335 and 585<=y and y+h<=667):
        return None
    if (c.find('Confirm|Cancel|Received Reward|Story Clear|Auto Assign',(300,120,650,450))
            or c.find(r'(?:[Xx×]\s*)?Tap\s*to\s*close[.]?',(350,400,600,282))):
        return None
    leave=c.one('Leave',(70,590,100,70))
    lobby=c.one('Lobby',(205,590,100,70))
    next_label=c.one(r'Next\s*Difficulty',(1050,530,155,70))
    again=c.one(r'Try\s*again',(1050,595,155,65))
    next_ratio=c.one(r'\d[\d,]*\s*/\s*\d[\d,]*',(935,530,115,55))
    repeat_ratio=c.one(r'\d[\d,]*\s*/\s*\d[\d,]*',(935,600,115,55))
    if not all((leave,lobby,next_label,again,next_ratio,repeat_ratio)):
        return None
    def cost(row):
        ratio=c.ratio(row,'cost','available')
        return fact({'currency':None,**ratio['value']},*ratio['sources'],
                    derived('/text','current_footer_numeric_cost_currency_unidentified'))
    next_cost,repeat_cost=cost(next_ratio),cost(repeat_ratio)
    anchors=[leave,lobby,next_label,again,next_ratio,repeat_ratio]
    p=c.panel('battle_exit',anchors,'wnd/result_base.csb',match_keys=('path_battle_exit_lobby',))
    c.detail(p,outcome=fact(),mode_identity=fact(),stage_id=fact(),battle_id=fact(),
             next_difficulty_cost=next_cost,repeat_cost=repeat_cost,
             exit_footer_visible=fact(True,*(c.source(r) for r in anchors),c.match_source('path_battle_exit_lobby')),
             victory_announced=fact(),mission_credit=fact())
    c.control(p,'lobby',lobby,'wnd/result_base.csb','/Layer/n_buttons/CENTER/n_left_btns/btn_lobby',False,
              navigation=[{'view':'lobby'}],match_key='path_battle_exit_lobby')
    c.control(p,'leave',leave,'wnd/result_base.csb','/Layer/n_buttons/CENTER/n_left_btns/btn_back',False)
    for key,row,current_cost,path in (
            ('next_difficulty',next_label,next_cost,'/Layer/n_buttons/CENTER/n_right_btns/btn_next'),
            ('try_again',again,repeat_cost,'/Layer/n_buttons/CENTER/n_right_btns/btn_again')):
        source=c.source(row)
        c.add(node(p+'/'+key,'control',p,semantic_id=fact(key,source),adapter=fact('operations',source),
                   text=c.value(row),box=fact(row[1]['box'],source),box_role=fact('text_anchor',source),
                   visible=fact(True,source),consuming=fact(True,source,derived('/text','mapped_consuming_result_control')),
                   cost=current_cost,layout_reference={'source':'wnd/result_base.csb','path':path,'scope':'static_hint'}))
    return 'battle_exit'
