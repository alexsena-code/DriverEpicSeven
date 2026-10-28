"""Limite persistente de entradas; uma reserva não é declaração de derrota."""

import json
from pathlib import Path
import time


class AttemptLedger:
    def __init__(self,path,limit=3):
        self.path=Path(path)
        self.limit=limit

    def read(self):
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {"stages":{}}

    def save(self,data):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temporary=self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        temporary.replace(self.path)

    def reserve(self,stage_id,key,cost):
        data=self.read()
        attempts=data["stages"].setdefault(stage_id,[])
        if any(item["key"]==key for item in attempts):return
        if len(attempts)>=self.limit:
            raise ValueError(f"Limite persistente de {self.limit} entradas atingido em {stage_id}; confira os resultados registrados.")
        attempts.append({"key":key,"cost":cost,"status":"reserved","epoch_seconds":time.time()})
        self.save(data)

    def mark(self,stage_id,key,status):
        data=self.read()
        for item in data["stages"].get(stage_id,[]):
            if item["key"]==key:
                item["status"]=status
                item[status+"_at"]=time.time()
        self.save(data)

    def pending_before(self,catalog,stage_id):
        first=catalog[stage_id]
        if first["ordinal"]>1:
            previous=next((s for s in catalog.values() if (s["episode"],s["chapter"],s["ordinal"])==
                (first["episode"],first["chapter"],first["ordinal"]-1)),None)
        else:
            candidates=[s for s in catalog.values() if (s["episode"],s["chapter"])==
                        (first["episode"],first["chapter"]-1)]
            previous=max(candidates,key=lambda s:s["ordinal"]) if candidates else None
        entries=self.read()["stages"].get(previous["id"],[]) if previous else []
        if entries and entries[-1]["status"] in ("reserved","sent","entered"):
            return previous["id"],entries[-1]["key"]
        return None
