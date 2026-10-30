"""Limite persistente de entradas; uma reserva não é declaração de derrota."""

import json
import os
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
        with temporary.open('w',encoding='utf-8') as stream:
            stream.write(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
            stream.flush()
            os.fsync(stream.fileno())
        # Windows readers/scanners can briefly hold the destination without
        # FILE_SHARE_DELETE. Retry only this durable write, never game input.
        for attempt in range(4):
            try:
                temporary.replace(self.path)
                break
            except PermissionError:
                if attempt==3:
                    raise
                time.sleep(0.1*(attempt+1))

    def record(self, stage_id, key, phase, *, identity, proof, status=None):
        """Add evidence without replacing history or conflating dispatch/result."""
        data = self.read()
        found = [row for row in data['stages'].get(stage_id,[]) if row['key']==key]
        if len(found)!=1:
            raise ValueError('Reserva ausente ou ambígua no diário.')
        row = found[0]
        if status in ('victory','defeat') and row.get('result_status') not in (None,status):
            raise ValueError('Resultado contraditório para a mesma tentativa; reconciliar a prova.')
        events = row.setdefault('events',[])
        if any(e['phase']==phase and e.get('proof')==proof for e in events):
            return
        if row.get('identity') and row['identity'] != identity:
            raise ValueError('Identidade incompatível com a reserva existente.')
        row['identity'] = identity
        row['ledger_scope'] = str(self.path.resolve())
        events.append({'phase':phase,'epoch_seconds':time.time(),'proof':proof})
        if status in ('victory','defeat'):
            row['result_status']=status
        if status:
            terminal = row['status'] in ('victory','returned','verified','applied','defeat','cancelled')
            return_without_result=(status=='returned' and row['status'] not in ('victory','defeat','applied','returned')
                                   and row.get('result_status') not in ('victory','defeat'))
            if not return_without_result and (not terminal or status in ('returned','verified','applied')):
                row['status'] = status
                row[status+'_at'] = time.time()
        if phase in ('result_verified','defeat') and proof.get('window'):
            row['verification_window'] = proof['window']
        self.save(data)

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
        if entries and entries[-1]["status"] in ("reserved","sent","entered","victory"):
            return previous["id"],entries[-1]["key"]
        return None
