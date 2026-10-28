"""Sequential JSONL transport over one Runtime, using the common UI tree."""

from contextlib import redirect_stderr
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import shutil
import sys

from .observed_ui import screen_state, operation_view, quest_view


LIVE_COMMANDS = {"observe", "read-screen", "session", "quest", "swipe", "hold", "skill-double-tap",
                 "key", "click", "wait-state", "stage", "run", "finish-battle", "chapter", "battle-auto", "path"}
ERRORS = (RuntimeError, ValueError, OSError, ImportError)


def parse_request(line):
    from .cli import parser

    request = json.loads(line)
    if not isinstance(request, dict):
        raise ValueError("Pedido deve ser um objeto JSON com args.")
    argv = request.get("args")
    if not isinstance(argv, list) or not argv or not all(isinstance(v, str) for v in argv):
        raise ValueError("args deve ser uma lista de argumentos, sem comando de shell.")
    if not isinstance(request.get("inspect_image", False), bool):
        raise ValueError("inspect_image deve ser booleano.")
    if argv == ["disconnect"]:
        return request, None
    diagnostic = StringIO()
    try:
        with redirect_stderr(diagnostic):
            args = parser().parse_args(argv)
    except SystemExit:
        raise ValueError("Argumentos inválidos. Consulte driver-epic-seven --help.") from None
    if args.config is not None:
        raise ValueError("A configuração é fixa durante a conexão; reinicie agent para mudá-la.")
    if args.command == "snapshot":
        if args.file:
            raise ValueError("Na sessão agent, snapshot consulta a conexão atual; omita --file.")
    elif args.command not in LIVE_COMMANDS or (
        args.command == 'path' and args.path_operation in ('roadmap','plan')
    ) or (
        args.command == "quest" and args.quest_operation in ("list", "inspect", "compare", "query")
    ) or (args.command == "stage" and args.stage_operation == "list"):
        raise ValueError("Use este comando no CLI independente, fora da conexão agent.")
    return request, args


def agent_view(snapshot, *, artifact, observer_file, result=None, error=None, inspect_image=False):
    """A disposable projection. The referenced artifact retains every field's evidence."""
    latest = snapshot["snapshot"]
    tree = latest["ui_tree"] if latest else None
    state = screen_state({"ui_tree": tree}) if tree else "unknown"
    reasons = []
    if tree is None:
        reasons.append("no_observation")
    elif (state == "unknown" and not operation_view({'ui_tree': tree})
          and not quest_view({'ui_tree': tree}).get('group_id')):
        reasons.append("unknown_screen")
    if error or (result and (result.get("needs_review") or result.get("completed") is False
                            or result.get("postcondition_verified") is False)):
        reasons.append("operation_needs_review")
    if inspect_image:
        reasons.append("requested_visual_inspection")
    # An old image cannot resolve an expired snapshot. Ask for observation first.
    context = tree["context"] if tree else {}
    image_path = context.get("frame")
    image_available = bool(image_path and Path(image_path).is_file())
    if reasons and image_available:
        saved_image = Path(artifact).with_suffix(".png")
        shutil.copyfile(image_path, saved_image)
        image_path = str(saved_image)
    nodes = []
    if tree:
        for item in tree["nodes"].values():
            # Geometry and template scores stay in the canonical tree. Unknown
            # semantic fields (including enabled) remain explicitly null here.
            values = {name: deepcopy(value["value"]) for name, value in item["fields"].items()
                      if name not in ("box", "anchor_box", "box_role", "match_score")}
            nodes.append({"id": item["id"], "kind": item["kind"],
                          "parent_id": item["parent_id"], "fields": values})
    operation = None
    if result is not None and "ui_tree" not in result:
        operation = {key: deepcopy(result[key]) for key in (
            "routine", "operation", "action", "target", "key", "completed", "dispatch_succeeded",
            "postcondition_verified", "execution", "needs_review", "observation_error", "before_state", "after_state", "elapsed_ms", "duration_ms",
            "notifications_enabled_by_driver", "keyword_tab_touched", "requested_clicks", "repeat_delay_ms", "error",
            "status", "group_id", "group_counter", "group_claimed", "boundary", "input_sent",
            "agent_checkpoint", "stage_ids", "max_starts", "energy_limit", "requires_three_stars",
            "progression_after_group", "milestone_after_group"
        ) if key in result}
        if 'tasks' in result:
            operation['visible_tasks']=[{key: deepcopy(task[key]) for key in
                ('task_id','executor','status','counter','fully_visible') if key in task}
                for task in result['tasks'] if task.get('observed')]
            operation['not_visible_task_count']=len(result.get('not_visible_tasks',[]))
    return {
        "ok": error is None, "readonly_snapshot": True, "requires_current_action_guards": True,
        "state": state, "validity": deepcopy(snapshot["validity"]),
        "snapshot_revision": snapshot["snapshot_revision"], "event_sequence": snapshot["event_sequence"],
        "events": deepcopy(snapshot["events"]), "history_lost": snapshot["history_lost"],
        "ui": {"schema_version": tree["schema_version"] if tree else None,
               "observation_id": tree["observation_id"] if tree else None,
               "coverage": tree["coverage"] if tree else "no_observation", "nodes": nodes,
               "operation_view": operation_view({'ui_tree': tree}) if tree else {},
               "quest_view": quest_view({'ui_tree': tree}) if tree else {}},
        "evidence": {"response_file": str(artifact), "tree_pointer": "/snapshot/snapshot/ui_tree",
                     "observer_file": str(observer_file), "observation_file": context.get("observation_file")},
        "image": {"required": bool(reasons), "reasons": reasons,
                  "available": image_available, "path": image_path if reasons else None,
                  "requires_fresh_observation": bool(reasons) and not snapshot["validity"]["valid"]},
        "operation": operation, "error": error, "metrics": deepcopy(snapshot["metrics"]),
    }


def serve(config, input_stream=None, output_stream=None, runtime_factory=None):
    """No background capture, implicit action, retries or second connection."""
    from .cli import request_from_args
    from .application import Application
    from .contracts import Identity
    from .runtime import Runtime

    input_stream = input_stream if input_stream is not None else sys.stdin
    output_stream = output_stream if output_stream is not None else sys.stdout
    runtime_factory = runtime_factory or Runtime

    def emit(data):
        output_stream.write(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n")
        output_stream.flush()

    application = Application(config)
    disconnect_requested, disconnect_id = False, None
    with runtime_factory(config) as runtime:
        observer_file = runtime.evidence.path / "observer.json"
        emit({"type": "ready", "protocol_version": 1, "observer_file": str(observer_file),
              "evidence_dir": str(runtime.evidence.path), "captures_started": False})
        cursor = 0
        for number, line in enumerate(input_stream, 1):
            request, args, result, error = {}, None, None, None
            max_age_ms = 500
            try:
                # Retain the caller's correlation ID when argument validation fails.
                # The rejected command must never look like an unrelated response.
                decoded = json.loads(line)
                if isinstance(decoded, dict):
                    request = decoded
                request, args = parse_request(line)
                if args is None:
                    disconnect_requested, disconnect_id = True, request.get("id")
                    break
                if args.command == "snapshot":
                    max_age_ms = args.max_age_ms
                    if args.after_sequence < 0:
                        raise ValueError("after-sequence não pode ser negativo.")
                    explicit_cursor = any(arg == "--after-sequence" or arg.startswith("--after-sequence=")
                                          for arg in request["args"])
                    cursor = args.after_sequence if explicit_cursor else cursor
                    runtime.read_snapshot(max_age_ms, refresh=False, after_sequence=cursor)
                else:
                    identity = Identity(**request["identity"]) if "identity" in request else Identity()
                    result = application.execute(request_from_args(args, identity), runtime)
            except (*ERRORS, TypeError) as exc:
                error = str(exc)
                # A rejected command cannot leave its previous snapshot marked current.
                runtime.observer.invalidate("agent_command_failed")
                max_age_ms = 500
            try:
                window = runtime.guard()
            except (*ERRORS, TypeError) as exc:
                runtime.observer.invalidate("window_unavailable")
                window = None
                error = error or str(exc)
            snapshot = runtime.observer.snapshot(max_age_ms, cursor, window)
            name = f"agent_{number:06d}"
            artifact = runtime.evidence.path / f"{name}.json"
            view = agent_view(snapshot, artifact=artifact, observer_file=observer_file,
                              result=result, error=error, inspect_image=request.get("inspect_image", False))
            runtime.evidence.write(name, {"request": request, "result": result,
                                         "snapshot": snapshot, "response": view})
            emit({"id": request.get("id"), "type": "response", **view})
            cursor = snapshot["event_sequence"]
    if disconnect_requested:
        emit({"id": disconnect_id, "type": "disconnected", "ok": True})
    return {"ok": True}
