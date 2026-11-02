"""Shared read-only primitives over one canonical observation, with no I/O."""
import re
import math
from .observed_ui import fact, derived, node


def is_preparation_time_record(row):
    """Exclude the current right-hand timing badge, not arbitrary title text."""
    box = row.get('box')
    return bool(isinstance(box, (list, tuple)) and len(box) == 4
                and 1080 <= box[0] and 100 <= box[1]
                and box[0] + box[2] <= 1210 and box[1] + box[3] <= 155
                and re.fullmatch(r'(?:[e©]\s*)?No\s+Record', row.get('text', '').strip(), re.I))


class ReadContext:
    def __init__(self, observation, parent, add):
        self.observation, self.parent, self.add = observation, parent, add
        self.state = observation.get('state', 'unknown')
        self.rows = []
        for index, row in enumerate(observation.get('text', [])):
            box = row.get('box')
            score = row.get('score')
            if (not isinstance(box, (list, tuple)) or len(box) != 4
                    or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in box)
                    or isinstance(score, bool) or not isinstance(score, (int, float))
                    or not math.isfinite(score) or not .90 <= score <= 1
                    or not isinstance(row.get('text'), str)
                    or min(box[:2]) < 0 or min(box[2:]) <= 0
                    or box[0]+box[2] > 1212 or box[1]+box[3] > 682):
                continue
            self.rows.append((index, row))

    def find(self, pattern, area=(0, 0, 1212, 682)):
        x, y, w, h = area
        return [(i, r) for i, r in self.rows if re.fullmatch(pattern, r['text'].strip(), re.I)
                and x <= r['box'][0] and y <= r['box'][1]
                and r['box'][0]+r['box'][2] <= x+w and r['box'][1]+r['box'][3] <= y+h]

    def one(self, pattern, area=(0, 0, 1212, 682)):
        rows = self.find(pattern, area)
        return rows[0] if len(rows) == 1 else None

    def preparation_title_rows(self):
        """Current title lines, including an aligned number-only continuation."""
        candidates=sorted((row for row in self.find(r'.+', (870,100,330,55))
                           if not is_preparation_time_record(row[1])),
                          key=lambda row:(row[1]['box'][1],row[1]['box'][0]))
        lines=[]
        for row in candidates:
            text=row[1]['text'].strip();box=row[1]['box']
            if any(char.isalpha() for char in text):
                lines.append(row)
            elif (re.fullmatch(r'\d{1,3}',text) and lines
                  and abs(box[0]-lines[0][1]['box'][0])<=12
                  and -3<=box[1]-lines[-1][1]['box'][1]-lines[-1][1]['box'][3]<=22):
                lines.append(row)
        return lines

    def label(self, area):
        """Read an unambiguous text field without a content/name allowlist."""
        rows = [row for row in self.find(r'.+', area)
                if any(char.isalpha() for char in row[1]['text'])]
        return rows[0] if len(rows) == 1 else None

    @staticmethod
    def source(row):
        return {'kind': 'ocr', 'pointer': f'/text/{row[0]}', 'engine': 'Maa/en_us'}

    def value(self, row, transform=None):
        if row is None:
            return fact()
        text = row[1]['text'].strip()
        return fact(transform(text) if transform else text, self.source(row),
                    confidence=row[1]['score'] if transform is None else None)

    def lines(self, area, pattern=r'.+'):
        rows = sorted(self.find(pattern, area), key=lambda pair: (pair[1]['box'][1], pair[1]['box'][0]))
        return (fact([r['text'].strip() for _, r in rows], *(self.source(row) for row in rows))
                if rows else fact())

    def match(self, key):
        m = self.observation.get('matches', {}).get(key, {})
        return m if m.get('hit') else None

    @staticmethod
    def match_source(key):
        return {'kind': 'recognition', 'pointer': '/matches/'+key}

    def panel(self, view, anchors, layout, mode=None, match_keys=(), back_destinations=None):
        evidence = [self.source(row) for row in anchors if row]
        evidence += [self.match_source(key) for key in match_keys if self.match(key)]
        if not evidence and self.state != 'unknown':
            evidence = [derived('/state', 'existing_visual_classifier')]
        identity = 'operation:'+view
        self.add(node(identity, 'panel', self.parent,
                      layout_reference={'source': layout, 'scope': 'static_hint'} if layout else None,
                      semantic_id=fact(view, *evidence), adapter=fact('operations', *evidence),
                      view=fact(view, *evidence), mode=fact(mode, *evidence),
                      back_destinations=fact(back_destinations, *evidence, derived('/text','mapped_non_consuming_back_navigation')),
                      visible=fact(True, *evidence)))
        return identity

    def detail(self, owner, **fields):
        self.add(node(owner+'/context', 'item', owner,
                      semantic_id=fact('context', derived('/text', 'current_stove_composition')),
                      adapter=fact('operations', derived('/text', 'current_stove_composition')), **fields))

    def item(self, owner, suffix, row=None, **fields):
        sources = [self.source(row)] if row else [derived('/text', 'current_stove_composition')]
        self.add(node(owner+'/'+suffix, 'item', owner,
                      semantic_id=fact(suffix, *sources), adapter=fact('operations', *sources),
                      visible=fact(True, *sources), **fields))

    def control(self, owner, name, row, layout=None, path=None, consuming=None, navigation=None, shortcut=None, match_key=None):
        if row is None:
            return
        source = self.source(row)
        match=self.match(match_key) if match_key else None
        hitbox=match.get('box') if match else None
        hit_source=self.match_source(match_key) if hitbox else source
        # A text label may be outside a button. A current native marker can
        # supply a calibrated inner hit region without treating CSB coordinates
        # as screen coordinates or tying the reader to a character identity.
        self.add(node(owner+'/'+name, 'control', owner,
                      semantic_id=fact(name, source), adapter=fact('operations', source),
                      text=self.value(row), box=fact(hitbox or row[1]['box'], hit_source),
                      box_role=fact('template_extent' if hitbox else 'text_anchor', hit_source),
                      navigation_template_verified=fact(bool(hitbox) if navigation else None,hit_source),
                      label_box=fact(row[1]['box'],source),visible=fact(True, source),
                      consuming=fact(consuming, source, derived('/text', 'mapped_control_role')),
                      navigation_destinations=fact(navigation, source, derived('/text','mapped_navigation_destinations')),
                      navigation_shortcut=fact(shortcut, source, derived('/text','mapped_navigation_shortcut')),
                      layout_reference={'source': layout, 'path': path, 'scope': 'static_hint'} if layout else None))

    def ratio(self, row, first='current', second='total'):
        if row is None:
            return fact()
        match = re.fullmatch(r'\s*(\d[\d,]*)\s*/\s*(\d[\d,]*)\s*', row[1]['text'])
        if not match:
            return fact()
        return fact(dict(zip((first, second), (int(s.replace(',', '')) for s in match.groups()))),
                    self.source(row), derived(f'/text/{row[0]}', 'displayed_ratio_order'))

