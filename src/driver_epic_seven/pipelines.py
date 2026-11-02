import json
from pathlib import Path


def registry(config: dict) -> dict:
    return json.loads(config["registry_file"].read_text(encoding="utf-8"))["routines"]


def executable_routine(config: dict, name: str) -> dict:
    routines = registry(config)
    if name not in routines:
        raise ValueError(f"Rotina desconhecida: {name}")
    routine = routines[name]
    if routine.get("parameterized"):
        if routine.get("compiler")=="theater":
            raise ValueError("Use theater com atos, limite de ingressos e prazo.")
        if routine.get("compiler")=="chapter":
            raise ValueError("Use o comando chapter com fase inicial e orçamento do trecho.")
        raise ValueError("Use o comando stage com o identificador da fase e seus parâmetros.")
    if routine["status"] != "validated":
        raise ValueError(f"Rotina {name} ainda está em calibração: {routine.get('pending', [])}")
    return routine


def validate(config: dict) -> dict:
    nodes, errors = {}, []
    for file in sorted((config["resource_dir"] / "pipeline").glob("*.json")):
        for key, value in json.loads(file.read_text(encoding="utf-8")).items():
            if key.startswith("$"):
                continue
            if key in nodes:
                errors.append(f"Nó duplicado: {key}")
            nodes[key] = value
    spec = json.loads(config["vision_file"].read_text(encoding="utf-8"))
    for name, template in spec["templates"].items():
        for appearance in [template, *template.get('alternatives', [])]:
            variants=appearance["template"] if isinstance(appearance["template"],list) else [appearance["template"]]
            for file in variants:
                if not (config["resource_dir"] / "image" / file).is_file():
                    errors.append(f"Template ausente: {name}/{file}")
            if appearance["node"] not in nodes:
                errors.append(f"Nó de template ausente: {name}/{appearance['node']}")
    routines = registry(config)
    compiled_info={}
    for name,spec_ocr in spec.get("ocr",{}).items():
        if spec_ocr["node"] not in nodes:
            errors.append(f"Nó OCR ausente: {name}")
    for name, routine in routines.items():
        available=nodes
        if routine.get("compiler")=="chapter":
            from .chapters import compile_chapter
            from .stages import load_stages
            try:
                stages=load_stages(config["stage_file"])
                first=min(stages.values(),key=lambda stage:(stage["episode"],stage["chapter"],stage["ordinal"]))
                plan,graph=compile_chapter(config,first["id"],sum(stage["energy"] for stage in stages.values() if isinstance(stage["energy"],int)))
                available={**nodes,**graph}
                compiled_info[name]={"nodes":len(graph),"max_starts":plan["max_starts"],"energy_limit":plan["energy_limit"]}
            except (ValueError,OSError,KeyError) as exc:
                errors.append(f"Não foi possível compilar {name}: {exc}")
                continue
        if routine.get("compiler")=="theater":
            from .theater import compile_theater
            try:
                graph,_,_=compile_theater(config['resource_dir'],acts=1,max_tickets=1,timeout=300,
                    act=1,series='static-validation-only',scope='theater:validation')
                available={**nodes,**graph}
                compiled_info[name]={'nodes':len(graph),'max_ticket_consumptions':1}
            except (ValueError,OSError,KeyError) as exc:
                errors.append('Não foi possível compilar theater: '+str(exc))
                continue
        if routine["entry"] not in available:
            errors.append(f"Entrada ausente: {name}")
        if routine["status"] != "validated":
            continue
        visited, pending = set(), [routine["entry"]]
        while pending:
            key = pending.pop()
            if key in visited:
                continue
            visited.add(key)
            node = available.get(key)
            if node is None:
                errors.append(f"Nó ausente: {key}")
                continue
            if node.get("enabled") is False:
                errors.append(f"Rotina validada alcança nó desabilitado: {key}")
            if node.get("timeout", 6000) < 0:
                errors.append(f"Timeout ilimitado: {key}")
            if node.get("action", "DoNothing") != "DoNothing" and node.get("recognition") == "DirectHit":
                errors.append(f"Entrada sem reconhecimento: {key}")
            if node.get("action", "DoNothing") != "DoNothing" and not node.get("max_hit"):
                errors.append(f"Ação sem limite de passagens: {key}")
            pending.extend(node.get("next", []))
            pending.extend(node.get("on_error", []))
    return {"valid": not errors, "errors": errors, "nodes": len(nodes),"compiled_routines":compiled_info,
            "routines": {name: value["status"] for name, value in routines.items()}}
