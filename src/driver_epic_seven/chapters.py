"""Compila um plano finito em um único grafo Maa, sem laço de cliques Python."""

from copy import deepcopy
import json

from .stages import compile_pipeline, load_stages
from .composition import append_fragment, validate_graph


def compile_chapter(config, from_stage, max_energy, finish_current=False):
    catalog=load_stages(config["stage_file"])
    if from_stage not in catalog:
        raise ValueError("Fase inicial ausente do catálogo.")
    first=catalog[from_stage]
    plan=sorted((stage for stage in catalog.values()
                 if (stage["episode"],stage["chapter"])==(first["episode"],first["chapter"])
                 and stage["ordinal"]>=first["ordinal"]),key=lambda stage:stage["ordinal"])
    if [stage["ordinal"] for stage in plan]!=list(range(first["ordinal"],plan[-1]["ordinal"]+1)):
        raise ValueError("O catálogo do trecho contém lacunas.")
    if any(not isinstance(stage["energy"],int) or stage["energy"]<1 for stage in plan):
        raise ValueError("O trecho inclui custo desconhecido ou entrada gratuita ainda não calibrada.")
    required=sum(stage["energy"] for stage in plan)
    if max_energy is None or max_energy<required:
        raise ValueError(f"O trecho requer até {required} de energia; orçamento insuficiente.")
    resources=config["resource_dir"]/"pipeline"
    stage_nodes=json.loads((resources/"stage_selection.json").read_text(encoding="utf-8"))
    finish_nodes=json.loads((resources/"battle_finish.json").read_text(encoding="utf-8"))
    graph={}
    for index,stage in enumerate(plan):
        prefix=f"Chapter.{stage['id']}."
        nodes={name:deepcopy(node) for source in (stage_nodes,finish_nodes)
               for name,node in source.items() if not name.startswith("$")}
        for name,override in compile_pipeline(stage["id"],"start",stage["energy"]).items():
            nodes[name].update(override)
        for name in ("Stage.EnteredStory","Stage.EnteredIntro","Stage.EnteredBattle"):
            nodes[name]["next"]=["Finish.Entry"]
        append_fragment(graph,nodes,prefix)
        next_entry=f"Chapter.{plan[index+1]['id']}.Stage.Entry" if index+1<len(plan) else "Chapter.Done"
        graph[prefix+"Finish.VerifyDone"]["next"]=[next_entry]
    graph["Chapter.Entry"]={"recognition":"DirectHit","action":"DoNothing",
                            "next":[f"Chapter.{plan[0]['id']}.Stage.Entry"]}
    if finish_current:
        prefix="Chapter.Current."
        append_fragment(graph,finish_nodes,prefix)
        graph[prefix+"Finish.VerifyDone"]["next"]=graph["Chapter.Entry"]["next"]
        graph["Chapter.Entry"]["next"]=[prefix+"Finish.Entry"]
    graph["Chapter.Done"]={"recognition":"Custom","custom_recognition":"ScreenTarget",
        "custom_recognition_param":{"state":"episode_map"},"action":"DoNothing","max_hit":1}
    validate_graph(graph,"Chapter.Entry",["Chapter.Done"])
    return {"stage_ids":[stage["id"] for stage in plan],"episode":first["episode"],
            "chapter":first["chapter"],"energy_limit":required,"max_starts":len(plan),
            "finish_current":finish_current},graph
