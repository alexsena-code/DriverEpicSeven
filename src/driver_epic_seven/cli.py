import argparse
import json
import sys

from .config import load_config
from .pipelines import executable_routine, registry, validate


def parser():
    root = argparse.ArgumentParser(description="Driver Epic Seven: primitivas e pipelines Maa")
    root.add_argument("--config", help="Override JSON local; caminhos relativos ao repositório")
    root.add_argument('--retry-policy',help='JSON de nova tentativa limitada e explicitamente autorizada; não faz retry automático')
    root.add_argument('--plan-budget', help='JSON de tetos finitos autorizados desde a primeira execução do plano')
    root.add_argument('--execution-identity', help='JSON com objective_id, plan_id, operation_id e attempt_id explícitos')
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Verificar dependências e descobrir a janela, sem enviar entrada")
    commands.add_parser("validate", help="Validar recursos e contratos sem interagir com o jogo")
    commands.add_parser("capabilities", help="Consultar capacidades e escopo nas fontes existentes; sem conectar")
    commands.add_parser("list", help="Listar primitivas e rotinas disponíveis")
    commands.add_parser("observe", help="Capturar e reconhecer a janela, sem enviar entrada")
    repeat = commands.add_parser('repeat-stage', help='Experimental: repetir a fase escolhida pelo Try again atual')
    repeat.add_argument('--count', type=int, required=True, help='Novos inícios; não inclui a batalha manual inicial')
    repeat.add_argument('--max-resource', type=int, required=True, help='Teto do recurso exibido no botão; sem recarga')
    repeat.add_argument('--timeout', type=int, default=1800)
    theater = commands.add_parser('theater', help='Watch e avanço limitado do Moonlight Theater')
    theater.add_argument('--acts', type=int, required=True)
    theater.add_argument('--max-tickets', type=int, required=True)
    theater.add_argument('--timeout', type=int, default=1800)
    theater.add_argument('--taps-per-act', type=int, default=600)
    theater.add_argument('--finish-current', action='store_true', help='Concluir um ato pendente, com zero Watch/Confirm/ingressos novos')
    auto = commands.add_parser('battle-auto', help='Ativar Auto somente se o HUD comprovar desligado; nunca inicia batalha')
    auto.add_argument('desired', choices=['on'])
    ui_query = commands.add_parser('ui-query', help='Consultar controle de painel operacional em árvore salva; somente leitura')
    ui_query.add_argument('--observation', required=True)
    ui_query.add_argument('--view', required=True)
    ui_query.add_argument('--control', required=True)
    commands.add_parser("agent", help="Manter uma conexão e receber comandos JSONL; árvore e eventos primeiro")
    status = commands.add_parser('status', help='Consultar execução da sessão; --file lê evidência sem conectar')
    status.add_argument('--file')
    events = commands.add_parser('events', help='Consultar eventos existentes; nunca captura')
    events.add_argument('--file')
    events.add_argument('--after-sequence', type=int, default=0)
    events.add_argument('--max-age-ms', type=int, default=500)
    commands.add_parser('cancel', help='Solicitar cancelamento da execução na conexão agent')
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
    altar_path.add_argument('--scope',help='Objetivo persistente explícito; dispensa alias de missão')
    altar_path.add_argument('--max-energy',type=int,default=0)
    altar_path.add_argument('--timeout',type=int,default=240)
    altar_mode=altar_path.add_mutually_exclusive_group()
    altar_mode.add_argument('--prepare',action='store_true')
    altar_mode.add_argument('--finish-current',action='store_true')
    abyss_path=paths.add_parser('abyss',help='Uma entrada parametrizada de Abyss normal; nunca repete Start')
    abyss_path.add_argument('--floor',type=int,default=1)
    abyss_path.add_argument('--mode',choices=['normal'],default='normal')
    abyss_path.add_argument('--expected-energy',type=int,default=10)
    abyss_path.add_argument('--task-id',default='guide_02_005_001')
    abyss_path.add_argument('--scope',help='Objetivo persistente explícito; dispensa alias de missão')
    abyss_path.add_argument('--max-energy',type=int,default=0)
    abyss_path.add_argument('--timeout',type=int,default=300)
    abyss_path.add_argument('--next-floor',action='store_true',help='Navegar do resultado para o andar alvo; exige --prepare, sem Start')
    abyss_mode=abyss_path.add_mutually_exclusive_group()
    abyss_mode.add_argument('--prepare',action='store_true')
    abyss_mode.add_argument('--finish-current',action='store_true')
    equipment_path=paths.add_parser('equipment',help='Uma operação de equipamento com alvo atual, orçamento e envio único')
    equipment_path.add_argument('task_id',nargs='?')
    equipment_path.add_argument('--operation',dest='equipment_action',choices=['equip_all','enhance_weapon'])
    equipment_path.add_argument('--scope')
    equipment_path.add_argument('--hero-name',required=True)
    equipment_path.add_argument('--max-gold',type=int,default=0)
    equipment_path.add_argument('--auto-level',type=int,choices=[3,6,9,12,15],default=3)
    equipment_path.add_argument('--material-limits',help='Objeto JSON com tetos de quantidade por nome observado de material')
    equipment_mode=equipment_path.add_mutually_exclusive_group()
    equipment_mode.add_argument('--preview',action='store_true')
    equipment_mode.add_argument('--apply-preview',action='store_true')
    equipment_mode.add_argument('--finish-current',action='store_true')
    formation_path=paths.add_parser('formation',help='Seleção e mudança finita de formação com prova do integrante e destino')
    formation_path.add_argument('formation_action',choices=['select','reposition','remove','assign','substitute'])
    formation_path.add_argument('--scope',required=True)
    formation_path.add_argument('--source',choices=['upper','left','right','lower'])
    formation_path.add_argument('--destination',choices=['upper','left','right','lower'])
    formation_path.add_argument('--member-name')
    formation_path.add_argument('--finish-current',action='store_true',help='Comprovar destino de mudança registrada, sem nova mutação')
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
    if args.command in ('status', 'events'):
        if not args.file:
            raise ValueError('Fora da sessão agent, '+args.command+' exige --file.')
        if args.command == 'status':
            from pathlib import Path
            return json.loads(Path(args.file).read_text(encoding='utf-8'))
        from .observer import read_snapshot_file
        if args.after_sequence < 0:
            raise ValueError('after-sequence não pode ser negativo.')
        return read_snapshot_file(args.file, args.max_age_ms, args.after_sequence)
    if args.command == 'cancel':
        raise ValueError('cancel exige a conexão agent existente; não abre outra conexão.')
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
    encoded_identity = values.pop('execution_identity', None)
    if encoded_identity is not None:
        try:
            decoded_identity = json.loads(encoded_identity)
            if not isinstance(decoded_identity, dict) or set(decoded_identity) != {
                    'objective_id', 'plan_id', 'operation_id', 'attempt_id'}:
                raise ValueError('incomplete identity')
            cli_identity = Identity(**decoded_identity)
        except (ValueError, TypeError) as exc:
            raise ValueError('--execution-identity exige JSON com quatro IDs não vazios.') from exc
        if identity is not None and identity != cli_identity:
            raise ValueError('identity JSONL conflita com --execution-identity; informe uma identidade única.')
        identity = cli_identity
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
        if args.command in ('repeat-stage','theater') and result.get('completed') is not True:
            return 1
        return 0 if result.get("valid", True) else 1
    except (RuntimeError, ValueError, OSError, ImportError) as exc:
        from .contracts import ApplicationError
        details={'execution_error':exc.as_dict()} if isinstance(exc,ApplicationError) else {}
        print(json.dumps({"ok": False, "error": str(exc),**details}, ensure_ascii=False))
        return 1
