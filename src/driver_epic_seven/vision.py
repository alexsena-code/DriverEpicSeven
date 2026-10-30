"""Classificação de telas. TemplateMatch continua sendo executado pelo Maa."""

import json
import re
from pathlib import Path

import numpy as np
from PIL import Image


def classify(matches: dict, states: dict) -> str:
    def composition(spec):
        def hit(key):
            match = matches.get(key, {"hit": False})
            source = spec.get("source_nodes", {}).get(key)
            if source is None:
                return match["hit"]
            if source in match.get("source_matches", {}):
                return match["source_matches"][source]["hit"]
            return match.get("source_node") == source and match["hit"]
        return (all(hit(key) for key in spec["all"])
                and (not spec.get("any") or any(hit(key) for key in spec["any"]))
                and not any(hit(key) for key in spec.get("none", [])))

    found = [name for name, spec in states.items()
             if any(composition(variant) for variant in spec.get("variants", [spec]))]
    superseded = {name for current in found for name in states[current].get('supersedes', [])}
    found = [name for name in found if name not in superseded]
    return found[0] if len(found) == 1 else "unknown"


def pixel_error(frame, template, box, glyph_min=None, green_mask=False, green_glyph=False) -> float:
    x, y, width, height = box
    if x < 0 or y < 0 or width < 1 or height < 1 or x+width > frame.shape[1] or y+height > frame.shape[0]:
        return float("inf")
    patch = frame[y:y+height, x:x+width, :3]
    if patch.shape != template.shape:
        return float("inf")
    difference=np.abs(patch.astype(np.float32)-template.astype(np.float32))
    if green_glyph:
        # Compare the existing result check glyph, excluding its animated
        # background. Native TemplateMatch thresholds/candidates stay intact.
        mask=(template[:,:,1]>130)&(template[:,:,1]>template[:,:,0]*1.4)&(template[:,:,1]>template[:,:,2]*1.4)
        return float(difference[mask].mean()) if mask.sum()>=50 else float('inf')
    if green_mask:
        mask = ~((template[:, :, 1] >= 250) & (template[:, :, 0] <= 5) & (template[:, :, 2] <= 5))
        return float(difference[mask].mean()) if mask.any() else float('inf')
    if glyph_min is not None:
        # Story controls have translucent backgrounds. Compare their fixed
        # bright glyphs, while still rejecting dimmed controls and overlays.
        mask=(np.min(template,axis=2)>=glyph_min)&(np.max(template,axis=2)-np.min(template,axis=2)<30)
        return float(difference[mask].mean()) if mask.any() else float("inf")
    return float(difference.mean())


def validated_template_match(frame, templates, result, max_pixel_mae, glyph_min=None, green_mask=False, green_glyph=False):
    """Check Maa-filtered variants before choosing the highest valid correlation.

    The highest-correlation candidate can have wrong colors/lighting, while
    another variant at a different position passes both correlation and pixels.
    Never rescue an unfiltered result or run another recognition here.
    """
    candidates = []
    if result and result.hit:
        filtered = getattr(result, "filtered_results", None)
        if filtered is None:  # Compatibility with the single-result adapter.
            boxes = [(result.box, getattr(result.best_result, "score", None))] if result.box else []
        else:
            boxes = [(row.box, getattr(row, "score", None)) for row in filtered if row.box]
        for raw_box, score in boxes:
            box = list(raw_box)
            error = min(pixel_error(frame, template, box, glyph_min, green_mask, green_glyph) for template in templates)
            candidates.append({"box": box, "score": score, "error": error})
    valid = [row for row in candidates if row["error"] <= max_pixel_mae]
    best = max(valid or candidates, key=lambda row: row["score"] if row["score"] is not None else -float("inf"), default=None)
    return {"hit": bool(valid), "box": best["box"] if best else None,
            "score": best["score"] if best else None,
            "pixel_mae": round(best["error"], 3) if best and np.isfinite(best["error"]) else None}


class Vision:
    def __init__(self, file: Path, bundle: Path):
        self.spec = json.loads(file.read_text(encoding="utf-8"))
        self.templates = {}
        self._alternative_templates = {}
        def load(spec):
            files=spec["template"] if isinstance(spec["template"],list) else [spec["template"]]
            return [np.asarray(Image.open(bundle/"image"/name).convert("RGB"))[:,:,::-1].copy()
                    for name in files]
        for name,spec in self.spec["templates"].items():
            self.templates[name]=load(spec)
            self._alternative_templates[name]=[load(variant) for variant in spec.get("alternatives", [])]

    def match_template(self, name, frame, matcher):
        """Use the same native filtered candidates and pixel checks for one anchor."""
        spec = self.spec['templates'][name]
        specs = [spec, *spec.get('alternatives', [])]
        images = [self.templates[name], *getattr(self, '_alternative_templates', {}).get(name, [])]
        results = [dict(validated_template_match(frame, templates, matcher(variant['node']),
            variant['max_pixel_mae'], variant.get('glyph_min'), variant.get('green_mask', False),
            variant.get('green_glyph', False)), source_node=variant['node'])
            for variant, templates in zip(specs, images)]
        valid = [result for result in results if result['hit']]
        match = dict(max(valid or results,
            key=lambda result: result['score'] if result['score'] is not None else -float('inf')))
        if spec.get('alternatives'):
            match['source_matches'] = {result['source_node']: result for result in results}
        return match

    def match_ocr(self, name, frame, matcher):
        spec = self.spec['ocr'][name]
        match = {'hit':False,'box':None,'score':None,'text':None,'pixel_mae':None}
        result = matcher(spec['node'])
        rows = result.filtered_results if result else []
        def visible(row):
            if not spec.get('min_bright_pixels'):
                return True
            x,y,w,h = row.box
            if min(x,y)<0 or min(w,h)<1 or x+w>frame.shape[1] or y+h>frame.shape[0]:
                return False
            return int(np.count_nonzero(np.min(frame[y:y+h,x:x+w,:3],axis=2)
                       >=spec['bright_glyph_min'])) >= spec['min_bright_pixels']
        valid = [row for row in rows if row.score >= spec['min_score']
                 and re.fullmatch(spec['expected'],row.text.strip(),re.IGNORECASE) and visible(row)]
        if spec.get('require_unique'):
            match['filtered_candidates'] = [{'box':list(row.box),'score':row.score,'text':row.text} for row in rows]
            match['ambiguous'] = len(valid)>1
            found = valid[0] if len(valid)==1 else None
        else:
            found = next(iter(valid),None)
        if found:
            match.update(hit=True,box=list(found.box),score=found.score,text=found.text)
        return match

    def inspect(self, frame, matcher) -> dict:
        matches = {}
        recognized = {}
        def recognize(node):
            if node not in recognized:
                recognized[node] = matcher(node)
            return recognized[node]
        for name in self.spec['templates']:
            matches[name] = self.match_template(name, frame, recognize)
        for name in self.spec.get("ocr",{}):
            matches[name]={"hit":False,"box":None,"score":None,"text":None,"pixel_mae":None}
        state=classify(matches,self.spec["states"])
        # Specific screens and decision dialogs take priority over a generic
        # informational notice. Only use its explicit close label as fallback.
        if state=="unknown" or any(all(matches.get(key, {}).get('hit', False) for key in anchors)
                                  for anchors in self.spec.get('ocr_triggers', [])):
            for name in self.spec.get('ocr', {}):
                matches[name] = self.match_ocr(name, frame, recognize)
            state=classify(matches,self.spec["states"])
        return {"state":state,"matches":matches}

    def target(self, analysis: dict, params: dict):
        from .observed_ui import tree_for, screen_state, target_box
        tree = tree_for(analysis, self.spec)
        if screen_state({"ui_tree": tree}) != params["state"]:
            return None
        if 'auto_state' in params:
            from .observed_ui import auto_state
            if auto_state({'ui_tree': tree}) is not params['auto_state']:
                return None
        if params.get('require_three_stars'):
            from .observed_ui import operation_view
            from .battle_operations import context
            if context(operation_view({'ui_tree':tree})).get('earned_stars')!=3:return None
        if params.get('three_star_checkpoint'):
            from .observed_ui import operation_view
            from .battle_operations import context
            if context(operation_view({'ui_tree':tree})).get('earned_stars')==3:return None
        name = params.get("target")
        if name:
            return target_box(tree, name)
        return [0, 0, 1, 1]
