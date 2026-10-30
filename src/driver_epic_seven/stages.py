"""Identidade de fase por catálogo, OCR Maa e contexto visual observado."""

import json
import re
from pathlib import Path

from maa.pipeline import JOCR, JTemplateMatch


def normalize(text):
    return "".join(char for char in text.casefold() if char.isalnum())


def parse_energy(results):
    for result in results:
        match = re.fullmatch(r"\s*(\d+)\s*/\s*(\d+)\s*", result["text"])
        if result["score"] >= .90 and match:
            return {"cost": int(match[1]), "available": int(match[2]), "score": result["score"]}
    return None


def check_start(stage, observed, max_energy, allow_replay=False):
    from .battle_operations import team_verified
    if not observed.get("identity_verified"):
        raise ValueError("A identidade da fase na preparação não foi confirmada.")
    if observed.get("already_cleared") and not allow_replay:
        raise ValueError("A fase já foi concluída; repetição não autorizada neste comando.")
    energy = observed.get("energy")
    if energy is None or energy["cost"] != stage["energy"]:
        raise ValueError("O custo observado está ausente ou diverge do catálogo.")
    if max_energy is None or max_energy < energy["cost"]:
        raise ValueError("O custo excede o limite de energia informado para esta entrada.")
    if energy["available"] < energy["cost"]:
        raise ValueError("Energia insuficiente; o driver não fará recarga.")
    if not team_verified(observed):
        raise ValueError('A composição/equipe atual não foi comprovada; CP não autoriza Start.')


def load_stages(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))["stages"]


class StageInspector:
    def __init__(self, path):
        self.catalog = load_stages(path)

    def get(self, stage_id):
        if stage_id not in self.catalog:
            raise ValueError("Fase ausente do catálogo: "+stage_id)
        return self.catalog[stage_id]

    @staticmethod
    def _ocr(recognize, roi, only_rec=False):
        result = recognize("OCR", JOCR(roi=roi, model="en_us",only_rec=only_rec))
        if result is None:
            return []
        return sorted([{"text": item.text, "score": item.score, "box": list(item.box)}
                       for item in result.filtered_results], key=lambda item: (item["box"][1], item["box"][0]))

    @staticmethod
    def _exact(rows, text):
        return next((row for row in rows if row["score"] >= .90
                     and normalize(row["text"]) == normalize(text)), None)

    @classmethod
    def _exact_block(cls,rows,text):
        return bool(rows) and all(row["score"]>=.90 for row in rows) and normalize(" ".join(row["text"] for row in rows))==normalize(text)

    @classmethod
    def _story_title(cls,rows,expected):
        if cls._exact(rows,expected):return "exact"
        lines=sorted((row for row in rows if row["box"][1]>=99 and row["score"]>=.90
            and normalize(row["text"])!="norecord"
            and not re.fullmatch(r"\d{1,2}:\d{2}(?:[.]\d+)?",row["text"].strip())),key=lambda row:row["box"][1])
        if cls._exact_block(lines,expected):return "exact_lines"
        # The UI renders a terminal Roman I like lowercase l or digit 1.
        # Restrict this normalization to an explicitly numbered story suffix;
        # preserve every preceding letter and the number of suffix glyphs.
        roman=re.fullmatch(r"(.+?)\s+(I{1,3})",expected)
        if roman and lines:
            actual=normalize(" ".join(row["text"] for row in lines))
            prefix=normalize(roman.group(1))
            if actual.startswith(prefix) and actual[len(prefix):].translate(str.maketrans({"l":"i","1":"i"}))==roman.group(2).casefold():
                return "roman_suffix_glyph"
        return None

    def inspect(self, stage_id, analysis, recognize):
        stage = self.get(stage_id)
        state = analysis["state"]
        report = {"requested_id": stage_id, "requested_title": stage["title"],
                  "expected_energy": stage["energy"],
                  "identity_verified": False, "context_verified": False, "row_locked": None,
                  "row_box": None, "energy": None, "ocr": {}}
        if state == "episode_map":
            episode = self._ocr(recognize, (55,8,150,48))
            chapter = self._ocr(recognize, (63,81,200,39))
            chapter_expected=f"Chapter {stage['chapter']}. {stage['chapter_title']}"
            chapter_detector=list(chapter)
            if not self._exact_block(chapter,chapter_expected):
                refined=[]
                for row in chapter:
                    x,y,w,h=row["box"]
                    refined.extend(self._ocr(recognize,(max(55,x-4),max(80,y-4),w+8,h+8),only_rec=True))
                if self._exact_block(refined,chapter_expected):chapter=refined
            rows = self._ocr(recognize, (80,112,370,437))
            description = self._ocr(recognize, (850,125,350,80))
            context = bool(self._exact(episode, f"Episode {stage['episode']}") and
                           self._exact_block(chapter,chapter_expected))
            row = self._exact(rows, f"{stage['ordinal']}. {stage['title']}")
            report.update(context_verified=context, row_box=row["box"] if row else None)
            report["ocr"] = {"episode":episode,"chapter":chapter,"chapter_detector":chapter_detector,"rows":rows,"description":description}
            report["visible_ordinals"] = [int(match.group(1)) for item in rows
                if item["score"]>=.90 and (match:=re.match(r"\s*(\d{1,2})\s*[.]",item["text"]))]
            if row:
                middle = row["box"][1]+row["box"][3]//2
                lock = recognize("TemplateMatch", JTemplateMatch(template=["map_padlock.png"],
                    roi=(48,max(112,middle-2),45,48),threshold=[.92]))
                report["row_locked"] = bool(lock and lock.hit)
            actual = normalize(" ".join(item["text"] for item in description if item["score"] >= .90))
            description_detector=list(description)
            if context and not actual.startswith(normalize(stage["description"])[:32]):
                refined=[]
                for row in description:
                    x,y,w,h=row["box"]
                    left,top=max(850,x-4),max(125,y-4)
                    refined.extend(self._ocr(recognize,(left,top,min(1208-left,w+8),h+8),only_rec=True))
                alternative=normalize(" ".join(item["text"] for item in refined if item["score"]>=.90))
                if alternative.startswith(normalize(stage["description"])[:32]):
                    actual=alternative;description=refined
            report["ocr"]["description_detector"]=description_detector
            report["ocr"]["description"]=description
            report["identity_verified"] = context and actual.startswith(normalize(stage["description"])[:32])
        elif state in ("supporter_selection", "battle_ready"):
            title = self._ocr(recognize, (875,68,325,85))
            # Reading the two-line region can yield a poor detection crop for
            # the gold location name. Retry that known line directly; still
            # require an exact normalized match and the same confidence floor.
            if not self._exact(title,stage["location"]):
                title.extend(self._ocr(recognize,(878,75,320,29),only_rec=True))
            if not self._exact(title,stage["location"]):
                # Long location labels need their detected line bounds: a wide
                # fixed crop can include the trial icon after the final letter.
                for row in list(title):
                    if row["box"][1]>=99 or row["score"]<.80:continue
                    x,y,w,h=row["box"]
                    left,top=max(875,x-4),max(68,y-4)
                    title.extend(self._ocr(recognize,(left,top,min(1200-left,w+8),h+8),only_rec=True))
                    if self._exact(title,stage["location"]):break
            title_method=self._story_title(title,stage["title"])
            if not title_method:
                # Use the detector's actual line bounds. A fixed wide crop can
                # erase the final Roman numeral when the OCR resizes the line.
                detected=list(title)
                for dx,dy,dw,dh in ((4,4,8,8),(2,3,16,6),(2,3,36,6)):
                    refined=[]
                    for row in detected:
                        if row["box"][1]<99 or row["score"]<.80:continue
                        x,y,w,h=row["box"]
                        left,top=max(875,x-dx),max(99,y-dy)
                        refined.extend(self._ocr(recognize,(left,top,min(1200-left,w+dw),h+dh),only_rec=True))
                    title_method=self._story_title(refined,stage["title"])
                    title.extend(refined)
                    if title_method:break
            if not title_method:
                title.extend(self._ocr(recognize,(878,112,320,34),only_rec=True))
                title_method=self._story_title(title,stage["title"])
            report["ocr"]["title"] = title
            report["title_match_method"]=title_method
            report["identity_verified"] = bool(self._exact(title, stage["location"]) and title_method)
            # Both names together identify this catalog entry; this view does not
            # display episode/chapter, so we do not claim to have OCR-read them.
            report["context_verified"] = report["identity_verified"]
            report["already_cleared"] = analysis["matches"].get("ready_completed_flag",{}).get("hit",False)
            if state == "battle_ready":
                energy = self._ocr(recognize, (912,602,110,50))
                report["ocr"]["energy"] = energy
                report["energy"] = parse_energy(energy)
                members=self._ocr(recognize,(180,110,430,260))
                levels=[int(row['text'].strip()) for row in members
                        if row['score']>=.90 and re.fullmatch(r'[1-9]|[1-5]\d|60',row['text'].strip())]
                stories=[row for row in members if row['score']>=.90 and row['text'].strip()=='Story']
                report.update(preparation_composition_verified=bool(report['identity_verified']
                              and any(analysis.get('matches',{}).get(k,{}).get('hit')
                                      for k in ('start_quest_label','start_regular_label'))),
                              visible_hero_levels=levels or None,visible_story_member_markers=len(stories) or None)
                report['ocr']['members']=members
            else:
                team = self._ocr(recognize, (925,598,235,65))
                report["ocr"]["select_team"] = team
                loading=self._ocr(recognize,(360,420,390,55))
                report["ocr"]["loading"] = loading
                report["supporter_loading"]=any("loading" in normalize(item["text"]) for item in loading)
                found = self._exact(team,"Select Team")
                report["select_team_box"] = found["box"] if found else None
        return report

    def target(self, analysis, params):
        from .observed_ui import tree_for, screen_state, stage_view, target_box, preparation_blocked
        tree = tree_for(analysis)
        if preparation_blocked({'ui_tree':tree}):return None
        info = stage_view({"ui_tree": tree})
        stage = self.get(info["requested_id"])
        target = params.get("target")
        state = screen_state({"ui_tree": tree})
        if state != params["state"]:
            return None
        if target == "stage_row":
            return target_box(tree, target, "stage") if info["context_verified"] and info["row_locked"] is False else None
        if target in ("scroll_top","scroll_down"):
            visible=info.get("visible_ordinals",[])
            if not info["context_verified"] or info["row_box"] or not visible:
                return None
            if target=="scroll_top" and stage["ordinal"]<=min(visible):return target_box(tree,target,"stage")
            if target=="scroll_down" and stage["ordinal"]>=max(visible):return target_box(tree,target,"stage")
            return None
        if not info["identity_verified"]:
            return None
        if target == "stage_ready":
            return target_box(tree, target, "stage")
        if target == "stage_select_team":
            return None if info.get("supporter_loading") else target_box(tree,target,"stage")
        if state == "battle_ready":
            if info["energy"] is None or info["energy"]["cost"] != stage["energy"]:
                return None
            if target == "stage_start":
                check_start(stage,info,params.get("max_energy"),params.get("allow_replay",False))
                return target_box(tree,target,"stage")
            return [0,0,1,1]
        return None


def compile_pipeline(stage_id, operation, max_energy=None, allow_replay=False):
    if operation not in ("prepare","start"):
        raise ValueError("Operação de fase desconhecida.")
    if operation == "start" and (max_energy is None or max_energy < 1):
        raise ValueError("Início de fase requer limite positivo de energia.")
    definitions = {
        "Stage.Row": ("episode_map","stage_row"),
        "Stage.ScrollTop": ("episode_map","scroll_top"),
        "Stage.ScrollDown": ("episode_map","scroll_down"),
        "Stage.OpenReady": ("episode_map","stage_ready"),
        "Stage.Supporter": ("supporter_selection","stage_select_team"),
        "Stage.CheckReady": ("battle_ready","stage_start" if operation=="start" else None),
    }
    override={}
    for name,(state,target) in definitions.items():
        params={"state":state,"stage_id":stage_id,"target":target}
        if operation=="start":params["max_energy"]=max_energy
        if operation=="start":params["allow_replay"]=allow_replay
        override[name]={"custom_recognition_param":params}
    if operation=="start":
        override["Stage.CheckReady"].update(action="Click",target=True,max_hit=1,
                                           next=["Stage.EnteredStory","Stage.EnteredIntro","Stage.EnteredBattle"],timeout=90000)
        for name,state in (('Stage.EnteredStory','story'),('Stage.EnteredIntro','story_intro'),('Stage.EnteredBattle','battle_running')):
            override[name] = {'custom_recognition_param':{'state':state,'execution':{
                'ledger':'campaign','scope':stage_id,'phase':'effect_verified','status':'entered'}}}
    return override
