import argparse
import json
import sys

from .config import load_config
from .pipelines import executable_routine, registry, validate


def parser():
    root = argparse.ArgumentParser(description="Driver Epic Seven: primitivas e pipelines Maa")
    root.add_argument("--config", help="Override JSON local; caminhos relativos ao repositório")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Verificar dependências e descobrir a janela, sem enviar entrada")
    commands.add_parser("validate", help="Validar recursos e contratos sem interagir com o jogo")
    commands.add_parser("capabilities", help="Consultar capacidades e escopo nas fontes existentes; sem conectar")
    commands.add_parser("list", help="Listar primitivas e rotinas disponíveis")
    commands.add_parser("observe", help="Capturar e reconhecer a janela, sem enviar entrada")
    auto = commands.add_parser('battle-auto', help='Ativar Auto somente se o HUD comprovar desligado; nunca inicia batalha')
    auto.add_argument('desired', choices=['on'])
    ui_query = commands.add_parser('ui-query', help='Consultar controle de painel operacional em árvore salva; somente leitura')
    ui_query.add_argument('--observation', required=True)
    ui_query.add_argument('--view', required=True)
    ui_query.add_argument('--control', required=True)
    commands.add_parser("agent", help="Manter uma conexão e receber comandos JSONL; árvore e eventos primeiro")
    path = commands.add_parser('path', help='Roteiro por nível e checkpoint do Caminho do Herdeiro')
    paths = path.add_subparsers(dest='path_operation', required=True)
    road = paths.add_parser('roadmap', help='Roteiro estático; não contém progresso da conta')
    road.add_argument('--level', type=int)
    plan = paths.add_parser('plan', help='Planejar um nível a partir de uma árvore salva; somente leitura')
    plan.add_argument('--observation', required=True)
    plan.add_argument('--level', type=int)
    inspect_path = paths.add_parser('inspect', help='Ler o nível atual e preparar o checkpoint; sem entrada')
    inspect_path.add_argument('--level', type=int)
    paths.add_parser('open', help='Abrir Orbis e selecionar Path of Heir por alvos atuais')
    go_path = paths.add_parser('go', help='Abrir o destino de uma missão atualmente observada; não executar')
    go_path.add_argument('task_id')
    recover_path = paths.add_parser('recover', help='Retomar o destino de uma missão por navegação calibrada; zero Start/Receive')
    recover_path.add_argument('task_id')
    group_path=paths.add_parser('run-group',help='Executar um grupo observado em um único grafo Maa finito; revisar ao terminar')
    group_path.add_argument('--level',type=int,required=True)
    group_path.add_argument('--plan',required=True)
    group_path.add_argument('--timeout',type=int,default=1200)
    nav_path = paths.add_parser('navigate', help='Navegação não consumidora por controle mapeado da árvore')
    nav_path.add_argument('--view',required=True)
    nav_path.add_argument('--control',required=True)
    nav_path.add_argument('--expect-view',required=True)
    nav_path.add_argument('--expect-mode')
    ack_path = paths.add_parser('acknowledge', help='Fechar um aviso informativo mapeado e conferir o destino; envio único')
    ack_path.add_argument('--view',required=True)
    ack_path.add_argument('--expect-view',required=True)
    execute_path = paths.add_parser('execute', help='Executar uma unidade calibrada da missão, com entrada única')
    execute_path.add_argument('task_id')
    prepare_path = paths.add_parser('prepare', help='Selecionar e conferir uma fase do prólogo; não iniciar')
    prepare_path.add_argument('stage_id')
    campaign_path=paths.add_parser('campaign',help='Trecho do prólogo com identidade, orçamento e um início por fase')
    campaign_path.add_argument('--from-stage',required=True)
    campaign_path.add_argument('--to-stage',required=True)
    campaign_path.add_argument('--max-energy',type=int,required=True)
    campaign_path.add_argument('--timeout',type=int,default=600)
    finish_path=paths.add_parser('finish-stage',help='Concluir uma fase já iniciada; nunca inicia outra batalha')
    finish_path.add_argument('stage_id')
    finish_path.add_argument('--timeout',type=int,default=300)
    altar_path=paths.add_parser('altar',help='Uma unidade identificada do Spirit Altar; nunca repetir Start')
    altar_path.add_argument('stage_id')
    altar_path.add_argument('--task-id',default='guide_01_004_001')
    altar_path.add_argument('--max-energy',type=int,default=0)
    altar_path.add_argument('--timeout',type=int,default=240)
    altar_mode=altar_path.add_mutually_exclusive_group()
    altar_mode.add_argument('--prepare',action='store_true')
    altar_mode.add_argument('--finish-current',action='store_true')
    abyss_path=paths.add_parser('abyss',help='Uma unidade Abyss 1 do grupo 2; nunca repete Start')
    abyss_path.add_argument('--task-id',default='guide_02_005_001')
    abyss_path.add_argument('--max-energy',type=int,default=0)
    abyss_path.add_argument('--timeout',type=int,default=300)
    abyss_mode=abyss_path.add_mutually_exclusive_group()
    abyss_mode.add_argument('--prepare',action='store_true')
    abyss_mode.add_argument('--finish-current',action='store_true')
    equipment_path=paths.add_parser('equipment',help='Uma operação de equipamento do grupo 2, com alvo atual e envio único')
    equipment_path.add_argument('task_id',choices=['guide_02_004_001','guide_02_003_001'])
    equipment_path.add_argument('--hero-name',required=True)
    equipment_path.add_argument('--max-gold',type=int,default=0)
    equipment_mode=equipment_path.add_mutually_exclusive_group()
    equipment_mode.add_argument('--preview',action='store_true')
    equipment_mode.add_argument('--apply-preview',action='store_true')
    for claim_command in ('collect','collect-group'):
        collect_path=paths.add_parser(claim_command,help='Coletar uma recompensa atual e conferir o resultado; sem repetir')
        collect_path.add_argument('--level',type=int,required=True)
        collect_path.add_argument('--task-id')
        collect_path.add_argument('--allow-ready-group',action='store_true')
    snapshot = commands.add_parser("snapshot", help="Consultar a árvore compartilhada salva, sem capturar ou conectar")
    snapshot.add_argument("--file", help="Obrigatório fora da sessão agent")
    snapshot.add_argument("--max-age-ms", type=int, default=500)
    snapshot.add_argument("--after-sequence", type=int, default=0)
    read = commands.add_parser("read-screen", help="Ler texto da captura via OCR Maa, sem enviar entrada")
    read.add_argument("--roi", type=int, nargs=4, metavar=("X", "Y", "W", "H"))
    session = commands.add_parser("session", help="Preparação observada: notificações e avisos, sem gasto ou chat enviado")
    session.add_argument("session_operation", choices=["inspect", "prepare", "notifications-off", "dismiss-notices"])
    hotkeys = commands.add_parser("hotkeys", help="Consultar defaults e restrições do DB; não envia teclas")
    hotkeys.add_argument("binding_id", nargs="?")
    quest = commands.add_parser("quest", help="Primitivas do catálogo e do painel de missões")
    quests = quest.add_subparsers(dest="quest_operation", required=True)
    listing = quests.add_parser("list", help="Listar requisitos estáticos; não contém progresso da conta")
    listing.add_argument("--path", choices=["heir", "succession", "arena", "connections"])
    listing.add_argument("--group")
    listing.add_argument("--family")
    inspect = quests.add_parser("inspect")
    inspect.add_argument("task_id")
    quests.add_parser("read", help="Ler grupo e missões visíveis; nenhuma entrada")
    quests.add_parser("open", help="Abrir Orbis a partir do lobby, sem resgatar")
    query = quests.add_parser("query", help="Consultar um controle na árvore de uma leitura salva; nenhuma entrada")
    query.add_argument("--observation", required=True)
    query.add_argument("--group", required=True)
    query.add_argument("--task")
    query.add_argument("--control", required=True, choices=["go", "claim", "claim_group", "receipt"])
    comparison = quests.add_parser("compare", help="Comparar duas leituras da mesma missão")
    comparison.add_argument("task_id")
    comparison.add_argument("--before", required=True)
    comparison.add_argument("--after", required=True)
    for operation in ("tab", "group", "go", "claim", "claim-group"):
        sub = quests.add_parser(operation)
        sub.add_argument("identity", help="heir, group_id ou task_id conforme a operação")
        sub.add_argument("--observation", required=True)
        if operation == "go":
            expectation = sub.add_mutually_exclusive_group(required=True)
            expectation.add_argument("--expect")
            expectation.add_argument("--expect-text", help="Texto exato distintivo da tela de destino; não autoriza executar a missão")
            sub.add_argument("--destination-kind", required=True,
                             choices=["mode_menu", "battle_categories", "stage_list", "supporter_selection", "battle_preparation"])
        if operation == "claim":
            sub.add_argument("--allow-ready-group", action="store_true", help="Autorizar resgate de todas as missões prontas do grupo selecionado")
    swipe = commands.add_parser("swipe", help="Uma rolagem por arraste vinculada à captura recente")
    swipe.add_argument("--begin", type=int, nargs=2, required=True)
    swipe.add_argument("--end", type=int, nargs=2, required=True)
    swipe.add_argument("--observation", required=True)
    swipe.add_argument("--duration-ms", type=int, default=400)
    swipe.add_argument("--from-state")
    finish=commands.add_parser("finish-battle",help="Experimental: acompanhar uma batalha já iniciada e retornar ao mapa")
    finish.add_argument("--timeout",type=float,default=240)
    chapter=commands.add_parser("chapter",help="Executar um trecho do capítulo em um único pipeline Maa")
    chapter.add_argument("--from-stage",required=True)
    chapter.add_argument("--max-energy",type=int,required=True)
    chapter.add_argument("--timeout",type=float,default=600)
    chapter.add_argument("--finish-current",action="store_true",help="Concluir o combate/resultado atual antes de iniciar o trecho, sem repetir essa batalha")
    run = commands.add_parser("run", help="Executar um pipeline Maa validado")
    run.add_argument("routine")
    click = commands.add_parser("click", help="Clicar em alvo reconhecido ou ponto de uma observação recente")
    target = click.add_mutually_exclusive_group(required=True)
    target.add_argument("--target")
    target.add_argument("--point", type=int, nargs=2, metavar=("X", "Y"))
    for cmd in (click,):
        cmd.add_argument("--observation")
        cmd.add_argument("--from-state")
        cmd.add_argument("--expect")
    hold=commands.add_parser("hold",help="Manter clique em ponto de uma observação recente, por exemplo numa cutscene")
    hold.add_argument("--point",type=int,nargs=2,required=True)
    hold.add_argument("--observation",required=True)
    hold.add_argument("--duration-ms",type=int,default=1500)
    hold.add_argument("--from-state")
    hold.add_argument("--expect")
    double = commands.add_parser("skill-double-tap", help="Experimental: dois toques nativos numa habilidade observada; nunca inicia batalha")
    double.add_argument("slot", type=int, choices=[1, 2, 3])
    double.add_argument("--observation", required=True)
    double.add_argument("--from-state", required=True)
    key = commands.add_parser("key", help="Enviar tecla com contexto observado")
    from .hotkeys import KEY_CODES
    key.add_argument("key", choices=list(KEY_CODES))
    key.add_argument("--observation")
    key.add_argument("--from-state")
    key.add_argument("--expect")
    key.add_argument("--duration-ms", type=int, default=100, help="100 ms por padrão; Escape longo somente para calibração observada")
    wait = commands.add_parser("wait-state", help="Esperar estado sem enviar entrada")
    wait.add_argument("state")
    wait.add_argument("--timeout", type=float, default=6)
    stage=commands.add_parser("stage",help="Inspecionar, selecionar e preparar/iniciar uma fase por identidade")
    stages=stage.add_subparsers(dest="stage_operation",required=True)
    stages.add_parser("list")
    for operation in ("inspect","prepare","start"):
        sub=stages.add_parser(operation)
        sub.add_argument("stage_id")
        if operation=="start":
            sub.add_argument("--max-energy",type=int,required=True)
            sub.add_argument("--allow-replay",action="store_true",help="Permitir fase já concluída, quando essa repetição é o objetivo")
    return root


def execute(args):
    config = load_config(args.config)
    if args.command == "capabilities":
        from .application import Application
        return Application(config).execute(request_from_args(args))
    if args.command == 'path' and args.path_operation in ('roadmap','plan'):
        from .path_planning import roadmap, route_level, plan_level
        if args.path_operation == 'roadmap':
            return route_level(args.level, config) if args.level else roadmap(config)
        from pathlib import Path
        return plan_level(json.loads(Path(args.observation).read_text(encoding='utf-8')), args.level, config)
    if args.command == "validate":
        return validate(config)
    if args.command == "snapshot":
        if not args.file:
            raise ValueError("Fora da sessão agent, snapshot exige --file.")
        from .observer import read_snapshot_file
        from .windows import Windows
        current = Windows().discover(config["target"])
        return read_snapshot_file(args.file, args.max_age_ms, args.after_sequence, current)
    if args.command == "list":
        return {"primitives": ["observe", "read-screen", "click --target", "click --point --observation", "hold", "swipe", "key", "wait-state", "quest"],
                "routines": registry(config)}
    if args.command == 'ui-query':
        from pathlib import Path
        from .observed_ui import tree_for, query_operation_control
        saved = json.loads(Path(args.observation).read_text(encoding='utf-8'))
        return query_operation_control(tree_for(saved), args.view, args.control)
    if args.command == "hotkeys":
        from .hotkeys import catalog
        from .config import ROOT
        data = catalog(ROOT / "data/input/hotkeys.json")
        if args.binding_id:
            found = [row for row in data["bindings"] if row["id"] == args.binding_id]
            if len(found) != 1:
                raise ValueError("Atalho ausente do catálogo: " + args.binding_id)
            return {"binding": found[0], "source": data["source"], "scope": data["scope"],
                    "live_validation": data["live_validations"].get(args.binding_id)}
        return data
    if args.command == "quest" and args.quest_operation in ("list", "inspect", "compare", "query"):
        from .quests import QuestCatalog, compare_snapshots
        from pathlib import Path
        if args.quest_operation == "query":
            from .observed_ui import build_tree, query_control
            observation = json.loads(Path(args.observation).read_text(encoding="utf-8"))
            tree = observation.get("ui_tree")
            if tree is None:
                tree = build_tree(observation)
            return query_control(tree, args.group, args.task, args.control)
        catalog = QuestCatalog(config["quest_file"], config["operation_map_file"])
        if args.quest_operation == "list":
            return {"tasks": catalog.list(args.path, args.group, args.family), "source": "static_catalog"}
        if args.quest_operation == "inspect":
            return catalog.get(args.task_id)
        return compare_snapshots(json.loads(Path(args.before).read_text(encoding="utf-8")),
                                 json.loads(Path(args.after).read_text(encoding="utf-8")), args.task_id)
    if args.command == "doctor":
        from maa.library import Library
        from .windows import Windows
        return {"maa_version": Library.version(), "window": Windows().discover(config["target"]),
                "resources": validate(config), "methods": {key: config[key] for key in
                    ("screencap_method", "mouse_method", "keyboard_method")}}
    if args.command=="stage" and args.stage_operation=="list":
        from .stages import load_stages
        return {"stages":load_stages(config["stage_file"])}
    if args.command == "run":
        executable_routine(config, args.routine)
    if args.command == "agent":
        from .agent_session import serve
        return serve(config)
    from .runtime import Runtime
    with Runtime(config) as runtime:
        return execute_live(args, runtime)


def request_from_args(args, identity=None):
    """Legacy command aliases terminate here; contracts never import argparse."""
    from .contracts import Request, Identity
    values = vars(args).copy()
    family = values.pop('command')
    values.pop('config', None)
    operation = values.pop(family+'_operation', None)
    return Request(family+('.'+operation if operation else ''), values, identity or Identity())


def execute_live(args, runtime):
    """Compatibility adapter shared with older callers."""
    from .application import Application
    return Application(runtime.config).execute(request_from_args(args), runtime)


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    try:
        result = execute(args)
        if args.command != "agent":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("valid", True) else 1
    except (RuntimeError, ValueError, OSError, ImportError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
