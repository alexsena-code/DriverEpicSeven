"""Prequel stage identity and finite graphs over current canonical panels."""
import json
import math
import re
import time
from .config import ROOT
from .stages import normalize
from .path_execution import recognition
from .composition import append_fragment, validate_graph
from .interruptions import treatment
from .battle_operations import energy_verified, fresh_ticket, team_verified


def title_match(actual, expected):
    """Compare a current title with scoped O/zero and Roman-suffix glyphs.

    Callers must independently verify the current location. This does not
    rewrite OCR evidence or accept arbitrary approximate names.
    """
    if not isinstance(actual, str) or not actual.strip():
        return None
    if normalize(actual) == normalize(expected):
        return 'normalized_exact'
    if (re.search(r'\bO\b', expected)
            and normalize(re.sub(r'\b0\b', 'O', actual)) == normalize(expected)):
        return 'standalone_o_glyph'
    roman = re.fullmatch(r'(.+?)\s+(I{1,3})', expected)
    if roman:
        prefix = normalize(roman[1])
        observed = normalize(actual)
        if (observed.startswith(prefix)
                and observed[len(prefix):].translate(str.maketrans({'l':'i','1':'i'})) == roman[2].casefold()):
            return 'roman_suffix_glyph'
    return None


def augment_title(observation, params, recognize):
    """Retry the current single-line title on the same Maa frame, not its text.

    The detector can omit a thin Roman suffix. Recognition-only OCR retains
    it in the native title strip. Keep the original and all candidates as
    diagnostic evidence; never replace a title with the requested name.
    """
    identity = params.get('stage_id')
    if params.get('kind') in ('prequel_row', 'prequel_ready') and identity:
        augment_map_row(observation, params, recognize)
        return
    if params.get('kind') not in ('prequel_supporter', 'prequel_start', 'prequel_prepared') or not identity:
        return
    from .reading import ReadContext, is_preparation_time_record
    from .stages import StageInspector
    reader = ReadContext(observation, 'screen', lambda n: None)
    if not observation.get('matches', {}).get('prequel_ready_header', {}).get('hit'):
        return
    expected = stage(identity)
    # A wrapped title can have a strong first line and a weak continuation.
    # Re-read only the continuation on the same frame; its detector result
    # locates the pixels but never supplies the missing identity itself.
    first_rows = reader.preparation_title_rows()
    locations = reader.find(r'.+', (870, 65, 340, 45))
    raw_continuations = [(i, r) for i, r in enumerate(observation.get('text', []))
        if isinstance((b := r.get('box')), (list, tuple)) and len(b) == 4
        and all(type(v) in (int, float) and math.isfinite(v) for v in b)
        and min(b[2:]) > 0 and type(r.get('score')) in (int, float) and math.isfinite(r['score'])
        and 0 <= r['score'] < .90 and isinstance(r.get('text'), str)
        and 875 <= b[0] < b[0]+b[2] <= 1195 and 118 <= b[1] < b[1]+b[3] <= 155]
    if (len(first_rows) == 1 and len(locations) == 1 and len(raw_continuations) == 1
            and normalize(locations[0][1]['text']) == normalize(expected['location'])):
        index, raw = raw_continuations[0]
        first_box = first_rows[0][1]['box']; box = raw['box']
        if abs(box[0]-first_box[0]) <= 12 and -3 <= box[1]-(first_box[1]+first_box[3]) <= 22:
            left = max(875, math.floor((box[0]-2)/5)*5)
            top = max(100, math.floor(box[1]-1))
            roi = [left, top, min(1195-left, box[2]+13), min(155-top, box[3]+3)]
            second_roi = [max(875, math.floor(box[0]-1)), max(100, math.floor(box[1]-2)),
                          min(1195-max(875, math.floor(box[0]-1)), box[2]+7),
                          min(155-max(100, math.floor(box[1]-2)), box[3]+5)]
            third_roi = [max(875, math.floor((box[0]-2)/5)*5), max(100, math.floor(box[1]-3)),
                         min(1195-max(875, math.floor((box[0]-2)/5)*5), box[2]+8),
                         min(155-max(100, math.floor(box[1]-3)), box[3]+8)]
            attempts = []
            accepted = False
            for current_roi in (roi, second_roi, third_roi):
                candidates = StageInspector._ocr(recognize, current_roi, only_rec=True)
                accepted = bool(len(candidates) == 1 and candidates[0]['score'] >= .90
                                and title_match(first_rows[0][1]['text']+' '+candidates[0]['text'], expected['title']))
                attempts.append({'roi': current_roi, 'candidates': candidates, 'accepted': accepted})
                if accepted:
                    break
            observation['campaign_wrapped_title_reread'] = {'roi': current_roi, 'original': raw.copy(),
                'candidates': candidates, 'attempts': attempts, 'accepted': accepted, 'method': 'Maa/en_us/only_rec'}
            if accepted:
                observation['text'][index] = {**candidates[0], 'box': box,
                                              'source': 'campaign_wrapped_title_reread'}
                reader = ReadContext(observation, 'screen', lambda n: None)
    # A wrapped final number can be omitted by the detector. Read only its
    # current continuation pixels after the exact prefix and location agree.
    numeric_title=re.fullmatch(r'(.+)\s+(\d{1,3})',expected['title'])
    title_lines=reader.preparation_title_rows()
    location_lines=reader.find(r'.+',(870,65,340,45))
    if (numeric_title and len(title_lines)==1 and len(location_lines)==1
            and normalize(location_lines[0][1]['text'])==normalize(expected['location'])
            and normalize(title_lines[0][1]['text'])==normalize(numeric_title[1])):
        box=title_lines[0][1]['box'];top=math.ceil(box[1]+box[3])-1
        roi=[max(875,math.floor(box[0]-4)),top,50,min(28,155-top)]
        if roi[3]>=12:
            candidates=StageInspector._ocr(recognize,roi,only_rec=True)
            accepted=(len(candidates)==1 and candidates[0]['score']>=.90
                      and candidates[0]['text'].strip()==numeric_title[2])
            observation['campaign_numeric_title_reread']={'roi':roi,
                'original_rows':[r for _,r in title_lines],'candidates':candidates,
                'accepted':accepted,'method':'Maa/en_us/only_rec'}
            if accepted:
                observation['text'].append({**candidates[0],'source':'campaign_numeric_title_reread'})
    for field, area, roi in (
            ('location', (870,65,340,45), [875,70,320,30]),
            ('title', (870,100,340,55), [875,110,320,30])):
        rows = reader.find(r'.+', area)
        if field == 'title':
            rows = [(i, r) for i, r in rows if not is_preparation_time_record(r)]
        if not rows:
            # Low-confidence detector output may locate the line, but cannot
            # prove its content. A new native OCR score must still reach .90.
            x,y,w,h=area
            rows=[(i,r) for i,r in enumerate(observation.get('text',[]))
                  if isinstance(r.get('text'),str) and r['text'].strip()
                  and (field != 'title' or not is_preparation_time_record(r))
                  and isinstance(r.get('box'),(list,tuple)) and len(r['box'])==4
                  and all(type(v) in (int,float) and math.isfinite(v) for v in r['box'])
                  and min(r['box'][2:])>0 and x<=r['box'][0] and y<=r['box'][1]
                  and r['box'][0]+r['box'][2]<=x+w and r['box'][1]+r['box'][3]<=y+h]
        compare = title_match if field == 'title' else lambda a,b: normalize(a)==normalize(b)
        if len(rows) != 1 or (rows[0][1].get('score',0)>=.90 and compare(rows[0][1]['text'], expected[field])):
            continue
        # Keep the detected line inside the canonical field. A title can
        # extend a pixel below the first OCR strip; its tight reread must
        # contain the whole current line, never a clipped Roman suffix.
        box = rows[0][1]['box']
        # The detected location may extend below the first OCR strip while
        # remaining inside the independently calibrated location field.
        field_bottom = area[1]+area[3]
        if box[1] < roi[1] or box[1]+box[3] > field_bottom:
            continue
        # The timed-stage badge can be merged into the same detected line.
        # Re-read its adjacent title pixels, never remove words from OCR text.
        timing_badge = field == 'title' and any(
            isinstance(r.get('text'), str) and re.search(r'No\s*Record\s*$', r['text'], re.I)
            and isinstance(r.get('box'), (list, tuple)) and len(r['box']) == 4
            and 100 <= r['box'][1] and r['box'][1]+r['box'][3] <= 155
            and 1150 <= r['box'][0]+r['box'][2] <= 1210
            for r in observation.get('text', []))
        current_roi = [875,110,225,30] if timing_badge else roi
        candidates = StageInspector._ocr(recognize, current_roi, only_rec=True)
        accepted = (len(candidates) == 1 and candidates[0]['score'] >= .90
                    and compare(candidates[0]['text'], expected[field]))
        selected = candidates[0] if accepted else None
        tight = None
        if not accepted:
            # Short titles lose detail when the OCR strip contains mostly
            # empty pixels. One bounded retry uses the current detected line.
            left=max(area[0] if field == 'title' else 875, math.floor((box[0]-2)/5)*5)
            top=max(area[1] if field == 'title' else roi[1], math.floor((box[1]-4)/2)*2)
            tight_roi = [left, top, min(box[2]+8,1195-left),
                         min(math.ceil((box[3]+9)/2)*2,field_bottom-top)]
            tight_candidates = StageInspector._ocr(recognize, tight_roi, only_rec=True)
            tight = {'roi':tight_roi, 'candidates':tight_candidates}
            accepted = (len(tight_candidates)==1 and tight_candidates[0]['score']>=.90
                        and compare(tight_candidates[0]['text'],expected[field]))
            if accepted:selected=tight_candidates[0]
        evidence_key = 'campaign_'+field+'_reread'
        observation[evidence_key] = {'roi': current_roi, 'original_rows': [r for _,r in rows],
            'candidates': candidates, 'tight':tight, 'accepted': bool(accepted), 'method': 'Maa/en_us/only_rec'}
        if accepted:
            observation['text'][rows[0][0]] = {**selected, 'source': evidence_key}


def augment_map_row(observation, params, recognize):
    """Recover a split current row with bounded native OCR on the same frame."""
    from .observed_ui import build_tree, operation_view
    from .stages import StageInspector
    current = operation_view({'ui_tree': build_tree(observation)})
    expected = stage(params['stage_id'])
    contexts = [i for i in current.get('items', []) if i.get('semantic_id') == 'context']
    available = observation.get('matches', {}).get('path_prequel_available', {})
    box = available.get('box')
    if (current.get('view') != 'prequel_ready_map' or len(contexts) != 1
            or contexts[0].get('episode_label') != episode_label(expected)
            or not chapter_matches(contexts[0], expected)
            or not available.get('hit') or not box
            or target(current, params, observation)):
        return
    center = box[1] + box[3] / 2
    # Detector fragments locate the line only; their low score never proves it.
    rows = [(i, r) for i, r in enumerate(observation.get('text', []))
            if (b := r.get('box')) and len(b) == 4 and 85 <= b[0] < b[0]+b[2] <= 420
            and abs(b[1]+b[3]/2-center) <= 25]
    if not rows or not 191 <= center <= 544:
        return
    top = math.ceil(center)-16
    widths = list(dict.fromkeys((330, max(200, min(330, math.ceil(max(r['box'][0]+r['box'][2] for _,r in rows)-85+8))))))
    attempts = []
    for width in widths:
        roi = [85, top, width, 32]
        candidates = StageInspector._ocr(recognize, roi, only_rec=True)
        accepted = False
        if len(candidates) == 1 and candidates[0]['score'] >= .90:
            label = re.fullmatch(r'(\d+)\s*[.]\s*(.+)', candidates[0]['text'].strip())
            accepted = bool(label and int(label[1]) == expected['ordinal']
                            and title_match(label[2], expected['map_title']))
        attempts.append({'roi': roi, 'candidates': candidates, 'accepted': accepted})
        if accepted:
            indices = {i for i,_ in rows}
            observation['text'] = [r for i,r in enumerate(observation['text']) if i not in indices]
            observation['text'].append({**candidates[0], 'source': 'campaign_row_reread'})
            break
    observation['campaign_row_reread'] = {'original_rows': [r for _,r in rows],
        'attempts': attempts, 'accepted': accepted, 'method': 'Maa/en_us/only_rec'}


def campaign_catalog():
    """Read static candidates; catalog membership never proves account access."""
    stages = {}
    for filename in ('adventurer-prequel.json', 'episode1-chapter6-candidates.json'):
        entries = json.loads((ROOT/'data/stages'/filename).read_text(encoding='utf-8'))['stages']
        if stages.keys() & entries.keys():
            raise ValueError('Identidade duplicada entre catálogos de campanha.')
        stages.update(entries)
    campaign = json.loads((ROOT/'data/stages/campaign.json').read_text(encoding='utf-8'))['stages']
    for identity, entry in campaign.items():
        if identity in stages:
            raise ValueError('Identidade duplicada entre catálogos de campanha.')
        stages[identity] = {**entry, 'map_title':entry['title'], 'map_description':entry['description']}
    return stages


def stage(identity):
    stages=campaign_catalog()
    if identity not in stages or not stages[identity].get('title'):
        raise ValueError('Fase do prólogo sem identidade estática resolvida.')
    return stages[identity]


def episode_label(stage_record):
    if stage_record['episode'] == 0:
        return '6th World Episode'
    return 'Episode ' + str(stage_record['episode'])


def chapter_matches(context, stage_record):
    """Keep the visible chapter code separate from the catalog grouping index."""
    actual = context.get('chapter_code')
    if actual is None:
        # Existing numeric observations remain compatible; a suffixed chapter
        # always requires its explicit current code.
        actual = str(context.get('chapter_number'))
    return actual == str(stage_record.get('map_chapter', stage_record['chapter']))


def corrected_team_retry(entries):
    """One explicitly reconciled blocked entry, never an automatic retry rule."""
    if len(entries)!=1 or entries[0].get('status')!='blocked_team':return False
    proof=entries[0].get('team_correction',{})
    return bool(proof.get('user_confirmed') is True and proof.get('owned_hero')
                and isinstance(proof.get('expected_cp'),int) and proof['expected_cp']>0
                and proof.get('window') and proof.get('evidence'))


def reserve_entry(ledger, identity, key, energy, observation=None):
    """A new request cannot repeat an uncertain or already finished entry."""
    scope='prequel:'+identity
    entries=ledger.read()['stages'].get(scope,[])
    if any(item['key']!=key for item in entries):
        if not corrected_team_retry(entries):
            raise ValueError('Já existe entrada desta fase. Confira o resultado; finish-stage conclui sem iniciar novamente. Replay exige outro plano explícito.')
        from .observed_ui import operation_view
        proof=entries[0]['team_correction'];current=operation_view(observation or {})
        contexts=[i for i in current.get('items',[]) if i.get('semantic_id')=='context']
        info=contexts[0] if len(contexts)==1 else {}
        if (current.get('view')!='prequel_preparation' or info.get('team_cp')!=proof['expected_cp']
                or (info.get('cost') or {}).get('available')!=proof.get('energy_balance')
                or any(proof['window'].get(k)!=(observation or {}).get('window',{}).get(k)
                       for k in ('hwnd','pid','process_name','window_class','client_size'))):
            raise ValueError('A correção de equipe desta entrada não confere com a preparação atual.')
    ledger.reserve(scope,key,energy)


def target(current, params, observation=None, prepared=None):
    expected=stage(params['stage_id'])
    if params['kind']=='prequel_supporter':
        from .observed_ui import screen_state
        from .reading import ReadContext
        if screen_state(observation or {}) != 'supporter_selection':
            return None
        rows = (observation or {}).get('text', [])
        def matches(text, area):
            x, y, w, h = area
            return [r for r in rows if r.get('score', 0) >= .90
                    and normalize(r.get('text', '')) == normalize(text)
                    and (box := r.get('box')) and len(box) == 4
                    and x <= box[0] and y <= box[1]
                    and box[0]+box[2] <= x+w and box[1]+box[3] <= y+h]
        title_rows=[r for _,r in ReadContext(observation or {},'screen',lambda n:None).preparation_title_rows()]
        # The preparation reader already joins up to three non-overlapping
        # title lines. Apply that same field boundary before Select Team.
        title_valid=(1<=len(title_rows)<=3 and not any(
            a['box'][1]+a['box'][3]>b['box'][1]+3 for a,b in zip(title_rows,title_rows[1:])))
        current_title=' '.join(r['text'].strip() for r in title_rows) if title_valid else None
        if (len(matches(expected['location'], (870, 65, 340, 45))) != 1
                or not title_match(current_title, expected['title'])
                or any('loading' in normalize(r.get('text', '')) for r in rows)):
            return None
        buttons = matches('Select Team', (925, 598, 235, 65))
        return buttons[0]['box'] if len(buttons) == 1 else None
    if params['kind']=='prequel_defeat':
        from .observed_ui import screen_state
        return [0,0,1,1] if screen_state(observation or {})=='battle_failed' else None
    if params['kind']=='prequel_story_receipt':
        contexts=[i for i in current.get('items',[]) if i.get('semantic_id')=='context']
        info=contexts[0] if len(contexts)==1 else {}
        controls=[c for c in current.get('controls',[]) if c.get('semantic_id')=='close' and c.get('consuming') is False]
        labels={normalize(s) for s in info.get('story_lines',[])}
        if (expected['energy']!=0 or current.get('view')!='story_reward' or info.get('receipt_announced') is not True
                or normalize(expected['title']) not in labels or normalize(expected['location']) not in labels
                or normalize(info.get('chapter_text') or '')!=normalize('Chapter '+str(expected.get('map_chapter',expected['chapter']))+'.')
                or len(controls)!=1):return None
        return controls[0].get('box')
    if params['kind']=='prequel_story_start':
        contexts=[i for i in current.get('items',[]) if i.get('semantic_id')=='context']
        info=contexts[0] if len(contexts)==1 else {}
        labels=[i for i in current.get('items',[]) if i.get('semantic_id')=='view_story_label']
        if (expected['energy']!=0 or current.get('view')!='prequel_story_map'
                or not chapter_matches(info, expected) or info.get('episode_label')!=episode_label(expected)
                or info.get('selected_kind_label')!='Story'
                or normalize(info.get('selected_description') or '')!=normalize(expected['map_description'])
                or len(labels)!=1 or labels[0].get('text')!='View Story'):
            return None
        return labels[0].get('box')
    if params['kind']=='prequel_story_done':
        ticket=(prepared or {}).get('story_seen:'+expected['id'])
        return [0,0,1,1] if (expected['energy']==0 and ticket
            and ticket['window']==(observation or {}).get('window')
            and current.get('view') in ('prequel_ready_map','prequel_story_map')) else None
    if params['kind']=='prequel_story_row':
        contexts=[i for i in current.get('items',[]) if i.get('semantic_id')=='context']
        info=contexts[0] if len(contexts)==1 else {}
        if (current.get('view') not in ('prequel_ready_map','prequel_story_map')
                or not chapter_matches(info, expected)
                or info.get('episode_label')!=episode_label(expected)):
            return None
        rows=[i for i in current.get('items',[]) if i.get('semantic_id')=='stage_row'
              and i.get('ordinal')==expected['ordinal'] and normalize(i.get('title') or '')==normalize(expected['map_title'])]
        return rows[0].get('box') if len(rows)==1 else None
    if params['kind'] in ('prequel_story_hold','prequel_story_skip'):
        from .interruptions import story_target
        return story_target(observation,params)
    if params['kind']=='prequel_map_return':
        from .battle_operations import same_window
        ticket=(prepared or {}).get('prequel_victory:'+expected['id'])
        if not ticket or not same_window(ticket.get('window'),(observation or {}).get('window')):
            return None
        if current.get('view') in ('prequel_ready_map','prequel_story_map'):
            return [0,0,1,1]
        # The last stage of episode 1 advances directly to episode 2. This is
        # a scoped observed destination, not proof for any other stage.
        if expected['id'] == 'tae010':
            from .observed_ui import screen_state
            import re
            rows = (observation or {}).get('text', [])
            def one(pattern, area):
                x,y,w,h=area
                return [r for r in rows if r.get('score',0)>=.90 and re.fullmatch(pattern,r.get('text','').strip(),re.I)
                        and (box:=r.get('box')) and len(box)==4 and x<=box[0] and y<=box[1]
                        and box[0]+box[2]<=x+w and box[1]+box[3]<=y+h]
            if (screen_state(observation or {})=='episode_map' and len(one(r'Episode\s+2',(45,0,230,65)))==1
                    and len(one(r'Chapter\s*1\s*[.].+',(45,75,235,55)))==1):
                return [0,0,1,1]
        return None
    if params['kind']=='prequel_clear':
        from .observed_ui import target_box
        contexts=[i for i in current.get('items',[]) if i.get('semantic_id')=='context']
        # The current CLEAR composition proves victory independently of its
        # optional objectives. Missing stars stay unknown, never a replay gate.
        if current.get('view')!='campaign_result' or current.get('mode')!='current_clear' or len(contexts)!=1:
            return None
        return target_box(observation['ui_tree'],'clear_continue')
    contexts=[i for i in current.get('items',[]) if i.get('semantic_id')=='context']
    if len(contexts)!=1:
        return None
    info=contexts[0]
    if params['kind']=='prequel_row':
        if (current.get('view') not in ('prequel_ready_map','prequel_story_map')
                or not chapter_matches(info, expected)
                or info.get('episode_label')!=episode_label(expected)):
            return None
        description_matches=normalize(info.get('selected_description') or '')==normalize(expected['map_description'])
        rows=[i for i in current['items'] if i.get('semantic_id')=='stage_row'
              and i.get('ordinal')==expected['ordinal']
              and (normalize(i.get('title') or '')==normalize(expected['map_title']) or description_matches)
              and i.get('available') is True]
        return rows[0].get('box') if len(rows)==1 else None
    if params['kind']=='prequel_ready':
        if (current.get('view')!='prequel_ready_map' or not chapter_matches(info, expected)
                or info.get('episode_label')!=episode_label(expected)):
            return None
        description_matches=normalize(info.get('selected_description') or '')==normalize(expected['map_description'])
        row=[i for i in current['items'] if i.get('semantic_id')=='stage_row'
             and i.get('ordinal')==expected['ordinal'] and i.get('available') is True
             and (normalize(i.get('title') or '')==normalize(expected['map_title']) or description_matches)]
        if len(row)!=1:
            return None
        rows=[i for i in current['items'] if i.get('semantic_id')=='ready_label' and i.get('text')=='Ready']
        return rows[0].get('box') if len(rows)==1 else None
    if current.get('view')!='prequel_preparation':
        return None
    cost=info.get('cost')
    if (normalize(info.get('location') or '')!=normalize(expected['location'])
            or not title_match(info.get('story_title'), expected['title'])
            or not energy_verified(cost,expected['energy'])):
        return None
    if params['kind']=='prequel_prepared':
        return [0,0,1,1]
    if params['kind']=='prequel_start':
        ticket=(prepared or {}).get(expected['id'])
        if (not energy_verified(cost,expected['energy'],params.get('max_energy',0))
                or not team_verified(info) or not fresh_ticket(ticket,observation or {})):
            return None
        controls=[c for c in current.get('controls',[]) if c.get('semantic_id')=='start_quest'
                  and c.get('consuming') is True]
        return controls[0].get('box') if len(controls)==1 else None
    return None


def prepare_graph(identity):
    stage(identity)
    return {
        'Prequel.Prepare.Entry':{'recognition':'DirectHit','action':'DoNothing','timeout':25000,
                               'next':['Prequel.Prepare.Supporter','Prequel.Prepare.Done','Prequel.Prepare.Row']},
        'Prequel.Prepare.Row':recognition({'kind':'prequel_row','stage_id':identity},'Click',
            next_nodes=['Prequel.Prepare.Ready'],hits=1,post_delay=500),
        'Prequel.Prepare.Ready':recognition({'kind':'prequel_ready','stage_id':identity},'Click',
            next_nodes=['Prequel.Prepare.Done','Prequel.Prepare.Supporter'],hits=1,post_delay=500,timeout=12000),
        'Prequel.Prepare.Supporter':recognition({'kind':'prequel_supporter','stage_id':identity},'Click',
            next_nodes=['Prequel.Prepare.Done'],hits=1,post_delay=500,timeout=12000,
            pre_wait_freezes={'time':600,'target':[870,590,330,75],'threshold':0.995,'method':10001,'rate_limit':100,'timeout':4000}),
        'Prequel.Prepare.Done':recognition({'kind':'prequel_prepared','stage_id':identity}),
    }


def campaign_graph(first, last, max_energy, *, resume=False, victory_observed=False):
    start,stop=stage(first),stage(last)
    catalog=campaign_catalog()
    if start['episode']!=stop['episode'] or start['chapter']!=stop['chapter'] or stop['ordinal']<start['ordinal']:
        raise ValueError('O trecho deve permanecer no mesmo capítulo e em ordem.')
    plan=sorted((s for s in catalog.values() if s['episode']==start['episode'] and s['chapter']==start['chapter']
                 and start['ordinal']<=s['ordinal']<=stop['ordinal']),key=lambda s:s['ordinal'])
    if len(plan)!=stop['ordinal']-start['ordinal']+1 or any(not s.get('title') or not isinstance(s['energy'],int) or s['energy']<0 for s in plan):
        raise ValueError('O trecho contém identidade/custo desconhecido.')
    cost=sum(s['energy'] for s in plan)
    if max_energy<cost:
        raise ValueError('O orçamento não cobre o trecho: '+str(cost))
    if resume:
        if len(plan)!=1:raise ValueError('Retomada exige uma única tentativa identificada.')
        prefix='Path.Campaign.'+first+'.'
        choices=([prefix+'Map',prefix+'Receipt',prefix+'Before.Hold',prefix+'Before.Skip',prefix+'Before.Confirm',prefix+'Before.Notice']
                 if start['energy']==0 else
                 [prefix+'Map',prefix+'After.Rank',prefix+'After.Rewards',prefix+'After.StoryReward',prefix+'After.Hold',prefix+'After.Skip',prefix+'After.Confirm',prefix+'Clear']
                 if victory_observed else
                 [prefix+'Before.Rank',prefix+'Before.Auto',prefix+'Before.Hold',prefix+'Before.Skip',prefix+'Before.Confirm',prefix+'Clear'])
        graph={'Path.Campaign.Entry':{'recognition':'DirectHit','action':'DoNothing','timeout':600000,'next':choices}}
    else:
        graph={'Path.Campaign.Entry':{'recognition':'DirectHit','action':'DoNothing','timeout':25000,
                                     'next':['Path.Campaign.Tutorial','Path.Campaign.'+plan[0]['id']+'.Back','Path.Campaign.'+plan[0]['id']+'.Row']},
               'Path.Campaign.Tutorial':recognition({'kind':'informational_ack','view':'tutorial'},'LongPress',duration=100,
                   hits=4,next_nodes=['Path.Campaign.Tutorial','Path.Campaign.'+plan[0]['id']+'.Back','Path.Campaign.'+plan[0]['id']+'.Row'],post_delay=700,timeout=12000)}
    for index,s in enumerate(plan):
        prefix='Path.Campaign.'+s['id']+'.'
        params={'stage_id':s['id']}
        following='Path.Campaign.'+plan[index+1]['id']+'.Row' if index+1<len(plan) else 'Path.Campaign.Done'
        if s['energy']==0:
            if not resume:
                graph[prefix+'Back']=recognition({'kind':'navigation','view':'prequel_preparation','key':'escape'},
                    'LongPressKey',next_nodes=[prefix+'Row'],key=[27],duration=100,hits=1,post_delay=500)
                graph[prefix+'Row']=recognition({'kind':'prequel_story_row',**params},'Click',
                    next_nodes=[prefix+'Start'],post_delay=400)
            recovery_entry=prefix+'Recovery.Path.Recover.Entry'
            choices=[prefix+'Map',prefix+'Receipt',prefix+'Before.Hold',prefix+'Before.Skip',prefix+'Before.Confirm',prefix+'Before.Notice',recovery_entry]
            # A free-story exit can return to Lobby with its receipt pending.
            # Reopen the same campaign mission using the shared navigation graph.
            from .path_execution import recovery_graph
            from .path_planning import catalog as quest_catalog
            chapter_end=max((x for x in catalog.values() if x['episode']==s['episode']
                            and x['chapter']==s['chapter']),key=lambda x:x['ordinal'])['id']
            missions=[t for t in quest_catalog().tasks.values() if t['path']=='heir'
                      and t.get('parameters',{}).get('enter')==chapter_end]
            if len(missions)==1:
                mission=missions[0]
                recovery=recovery_graph(mission['group'],mission['id'],'campaign')
                recovery['Path.Recover.Entry']=recognition({'kind':'view','views':['lobby','orbis_guide']},
                    next_nodes=['Path.Recover.Done','Path.Open.Entry'])
                names=append_fragment(graph,recovery,prefix+'Recovery.')
                graph[names['Path.Recover.Done']]['next']=[prefix+'Map']
            else:
                choices.remove(recovery_entry)
            if not resume:
                graph[prefix+'Start']=recognition({'kind':'prequel_story_start',**params,'energy':0,'consuming':True},
                    'LongPress',duration=100,next_nodes=choices,post_delay=500,timeout=60000)
            for suffix,kind,hits in [('Hold','story_hold',6),('Skip','story_skip',6),('Confirm','confirm_skip',6)]:
                graph[prefix+'Before.'+suffix]=treatment(kind,choices,hits=hits,timeout=60000,post_delay=500,stage_id=s['id'])
            graph[prefix+'Receipt']=recognition({'kind':'prequel_story_receipt',**params},'LongPress',duration=100,
                next_nodes=[prefix+'Map'],post_delay=700,timeout=60000)
            graph[prefix+'Before.Notice']=treatment('notice',choices,hits=4,timeout=60000,post_delay=700)
            graph[prefix+'Map']=recognition({'kind':'prequel_story_done',**params},next_nodes=[following],timeout=60000)
            continue
        if not resume:
            graph[prefix+'Back']=recognition({'kind':'navigation','view':'prequel_preparation','key':'escape'},
                'LongPressKey',next_nodes=[prefix+'Row'],key=[27],duration=100,hits=1,post_delay=500)
            graph[prefix+'Row']=recognition({'kind':'prequel_row',**params},'Click',next_nodes=[prefix+'Ready'],post_delay=400)
            graph[prefix+'Ready']=recognition({'kind':'prequel_ready',**params},'Click',next_nodes=[prefix+'Supporter',prefix+'Start'],post_delay=500,timeout=12000)
            # A dispatched navigation click can be ignored by the game. Re-read
            # the current supporter panel before one bounded retry; Start stays
            # first and single-use, so arrival cannot repeat battle entry.
            graph[prefix+'Supporter']=recognition({'kind':'prequel_supporter',**params},'Click',hits=2,
                next_nodes=[prefix+'Start',prefix+'Supporter'],post_delay=500,timeout=12000,
                pre_wait_freezes={'time':600,'target':[870,590,330,75],'threshold':0.995,'method':10001,'rate_limit':100,'timeout':4000})
            graph[prefix+'Start']=recognition({'kind':'prequel_start',**params,'max_energy':s['energy'],
                                              'energy':s['energy'],'consuming':True},'Click',
                next_nodes=[prefix+'Before.Rank',prefix+'Before.Auto',prefix+'Before.Hold',prefix+'Before.Skip',prefix+'Before.Confirm',prefix+'Clear'],post_delay=500,timeout=600000)
        graph[prefix+'Clear']=recognition({'kind':'prequel_clear',**params},'Click',
            next_nodes=[prefix+'After.Rank',prefix+'After.Rewards',prefix+'After.StoryReward',prefix+'After.Hold',prefix+'After.Skip',prefix+'After.Confirm',prefix+'Map',prefix+'Clear'],
            hits=3,post_delay=500,timeout=600000)
        for phase in ('Before','After'):
            choices=([prefix+'Before.Rank',prefix+'Before.Auto',prefix+'Before.Hold',prefix+'Before.Skip',prefix+'Before.Confirm',prefix+'Clear'] if phase=='Before' else
                     [prefix+'After.Rank',prefix+'After.Rewards',prefix+'After.StoryReward',prefix+'After.Hold',prefix+'After.Skip',prefix+'After.Confirm',prefix+'Map',prefix+'Clear'])
            graph[prefix+phase+'.Rank']=treatment('notice',choices,hits=8,timeout=600000,post_delay=500)
            for suffix,kind,hits in [('Hold','story_hold',6),('Skip','story_skip',12),('Confirm','confirm_skip',12)]:
                graph[prefix+phase+'.'+suffix]=treatment(kind,choices,hits=hits,timeout=600000,post_delay=500,stage_id=s['id'])
        graph[prefix+'Before.Auto']=treatment('auto',
            [prefix+'Before.Rank',prefix+'Before.Hold',prefix+'Before.Skip',prefix+'Before.Confirm',prefix+'Clear'],
            hits=1,timeout=600000,post_delay=200)
        for suffix,kind in [('Rewards','rewards'),('StoryReward','story_reward')]:
            graph[prefix+'After.'+suffix]=treatment(kind,
                [prefix+'After.Rank',prefix+'After.Rewards',prefix+'After.StoryReward',prefix+'After.Hold',prefix+'After.Skip',prefix+'After.Confirm',prefix+'Map'],
                hits=2,timeout=600000,post_delay=500)
        following='Path.Campaign.'+plan[index+1]['id']+'.Row' if index+1<len(plan) else 'Path.Campaign.Done'
        graph[prefix+'Map']=recognition({'kind':'prequel_map_return',**params},
            next_nodes=[prefix+'After.Rank',prefix+'After.StoryReward',following],hits=3,post_delay=800)
    graph['Path.Campaign.Done']=recognition({'kind':'prequel_story_done' if stop['energy']==0 else 'prequel_map_return','stage_id':stop['id']})
    for s in plan:
        if s['energy']==0:continue
        name='Path.Campaign.'+s['id']+'.Defeat'
        for key,node in list(graph.items()):
            if key.startswith('Path.Campaign.'+s['id']+'.') and node.get('next'):
                node['next'].insert(0,name)
        graph[name]=recognition({'kind':'prequel_defeat','stage_id':s['id']})
        if resume:graph['Path.Campaign.Entry']['next'].insert(0,name)
    # Reuse calibrated non-consuming interruptions, including victory resumes.
    # Closing a side-story notice never launches that story or accepts a friend.
    for s in plan:
        prefix='Path.Campaign.'+s['id']+'.'
        destinations=[prefix+'Map',prefix+'Receipt',prefix+'Before.Hold',prefix+'Before.Skip',
                      prefix+'Before.Confirm',prefix+'Before.Notice'] if s['energy']==0 else [
                      prefix+'Defeat',prefix+'Before.Auto',prefix+'After.Rank',prefix+'After.Rewards',prefix+'After.StoryReward',
                      prefix+'After.Hold',prefix+'After.Skip',prefix+'After.Confirm',prefix+'Map',prefix+'Clear']
        destinations=[n for n in destinations if n in graph]
        treatments={prefix+'After.'+suffix:kind for suffix,kind in
                    [('SideAlert','side_alert'),('CancelFriend','cancel_friend')]}
        for key,node in list(graph.items()):
            if (key.startswith(prefix) or (key=='Path.Campaign.Entry' and len(plan)==1)) and node.get('next'):
                node['next'][:0]=list(treatments)
        for name,kind in treatments.items():
            graph[name]=treatment(kind,destinations+list(treatments),hits=3,timeout=600000,post_delay=500)
    # Test story controls before the broad notice reader, retaining defeat
    # precedence. Every hit still builds the complete tree before any input.
    def priority(name):
        params = graph[name].get('custom_recognition_param', {})
        kind = params.get('path', {}).get('kind')
        if kind == 'prequel_defeat': return 0
        if params.get('state') in ('side_story_alert','friend_request'): return 1
        if kind in ('story_hold','story_skip') or params.get('state') == 'story_confirmation': return 1
        return 2
    for node in graph.values():
        if node.get('next'):
            node['next'].sort(key=priority)
    validate_graph(graph,'Path.Campaign.Entry',['Path.Campaign.Done'],resume=resume)
    from .plans import contract, sequential_units
    finite=contract('path.campaign',sequential_units([s['id'] for s in plan],prefix='prequel:'),graph,energy=0 if resume else cost)
    return {'finite_plan':finite,'stage_ids':[s['id'] for s in plan],'energy_limit':0 if resume else cost,'max_starts':0 if resume else len(plan),'requires_three_stars':False},graph


def finish_graph(identity, victory_observed=False):
    # Compile only the authorized continuation. No consumer/preparation node is
    # generated, so error/interrupt edges cannot accidentally re-enter Start.
    return campaign_graph(identity,identity,stage(identity)['energy'],
                          resume=True,victory_observed=victory_observed)[1]
