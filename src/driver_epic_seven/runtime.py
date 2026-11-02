import json
import time
from pathlib import Path
from threading import Event

import numpy as np
from PIL import Image

from .evidence import Evidence, sentry_context
from .pipelines import executable_routine
from .vision import Vision, pixel_error
from .windows import Windows, verify_window, WindowProfileLease
from .observed_ui import build_tree, screen_state, stage_view, quest_view, navigation_view, text_rows, target_box, query_control, operation_view


def check_observation(saved: dict, original: dict, now: float, max_age=30):
    age = now - saved["epoch_seconds"]
    if age < 0 or age > max_age:
        raise ValueError("Observação expirada; capture a janela novamente.")
    for key in ("hwnd", "pid", "process_name", "window_title", "window_class", "client_size"):
        if saved["window"][key] != original[key]:
            raise ValueError("A observação pertence a outra janela ou resolução.")


class SessionLock:
    def __init__(self, path):
        self.path, self.file = path, None

    def acquire(self):
        import msvcrt
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = self.path.open("a+b")
        if self.path.stat().st_size == 0:
            self.file.write(b"0")
            self.file.flush()
        self.file.seek(0)
        try:
            msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            self.file.close()
            self.file = None
            raise RuntimeError("Outro comando do driver está usando a sessão.") from None

    def close(self):
        if self.file:
            self.file.close()
            self.file = None


class Runtime:
    def __init__(self, config):
        self.config = config
        self.lock = SessionLock(config["session_lock"])
        self.lock.acquire()
        self.ctrl = None
        self.tasker = None
        self.fatal = None
        self._execution_cancel = Event()
        self.execution_dispatched = False
        self.window_profile = None
        from .attempts import AttemptLedger
        self.attempts=AttemptLedger(config["campaign_ledger"],config.get("attempt_limit",3)) if config.get("campaign_ledger") else None
        self.start_reservations={}
        # Normal Path actions remain single-use in OperationCycle. Only a new
        # explicit, proven-defeat permit can reach another battle reservation.
        self.path_attempts=AttemptLedger(config['path_ledger'],3)
        self.path_reservations={}
        self.path_prepared={}
        self.path_completion_scopes={}
        self.path_group_actions=set()
        self.path_group_action_count=0
        self.path_group_action_limit=None
        self.path_battles=AttemptLedger(config['path_ledger'],3)
        try:
            self.windows = Windows()
            self.original = self.windows.discover(config["target"])
            initial = self.original
            self.window_profile = WindowProfileLease(self.windows, initial, config)
            self.original = self.windows.inspect(initial["hwnd"])
            self.guard()
            self.evidence = Evidence(config["runs_dir"])
            from .observer import SharedObserver
            self.observer = SharedObserver(self.evidence.write)
            self.evidence.write("window_profile", {"before": initial, "after": self.original,
                "policy": config.get("window_policy", {}), "style_before": self.window_profile.saved_style,
                "style_while_connected": self.windows.style(self.original["hwnd"])})
            self.vision = Vision(config["vision_file"], config["resource_dir"])
            from .stages import StageInspector
            self.stage_inspector = StageInspector(config["stage_file"])
            self._initialize_maa()
        except Exception:
            self.close()
            raise

    def _initialize_maa(self):
        from maa.controller import Win32Controller
        from maa.resource import Resource
        from maa.tasker import Tasker
        from maa.define import LoggingLevelEnum
        from maa.custom_recognition import CustomRecognition
        runtime = self

        class ScreenTarget(CustomRecognition):
            def __init__(self):
                super().__init__()
                self.latest = None

            def analyze(self, context, argv):
                try:
                    analysis_started, cpu_started = time.perf_counter(), time.process_time()
                    params = json.loads(argv.custom_recognition_param)
                    runtime.guard(input_active=not params.get("observe", False))
                    from .story_performance import candidate_matcher
                    matcher = candidate_matcher(runtime.vision, argv.image,
                        lambda name: context.run_recognition(name, argv.image), params)
                    if matcher is None:
                        runtime.observer.count('candidate_rejections')
                        runtime.observer.count('candidate_rejection_wall_ms',
                            (time.perf_counter() - analysis_started) * 1000)
                        return None
                    from .operational_theater import fast_analysis
                    def theater_ocr(roi):
                        from .stages import StageInspector
                        return StageInspector._ocr(lambda kind,args:context.run_recognition_direct(kind,args,argv.image),roi)
                    analysis = fast_analysis(runtime.vision, argv.image, matcher, params, theater_ocr)
                    if analysis is None:
                        analysis = runtime.vision.inspect(argv.image, matcher)
                    if params.get("stage_id"):
                        analysis["stage"] = runtime.stage_inspector.inspect(params["stage_id"], analysis,
                            lambda kind, args: context.run_recognition_direct(kind,args,argv.image))
                    from .story_performance import needs_story_text
                    wants_text = params.get("read_text") or params.get("session")
                    read_text = wants_text and (params.get('session') or needs_story_text(params, analysis['state']))
                    read_text = read_text and analysis.get('text_scope') not in ('theater_dialogue_anchors_only','theater_dialogue_roi','theater_intro_roi')
                    if read_text:
                        from .stages import StageInspector
                        analysis["text"] = StageInspector._ocr(
                            lambda kind, args: context.run_recognition_direct(kind,args,argv.image),
                            params.get("text_roi", [0, 0, *runtime.config["reference_size"]]))
                        from .operational_equipment import augment_text
                        from .operational_formation import augment_text as augment_formation
                        augment_text(analysis,lambda kind,args:context.run_recognition_direct(kind,args,argv.image))
                        augment_formation(analysis,lambda kind,args:context.run_recognition_direct(kind,args,argv.image))
                        from .operational_altar import augment_text as augment_altar
                        augment_altar(analysis,lambda kind,args:context.run_recognition_direct(kind,args,argv.image))
                    elif wants_text:
                        analysis.setdefault('text', [])
                        analysis.setdefault('text_scope', 'skipped_incompatible_story_candidate')
                    if params.get("session"):
                        from .session import CheckboxReader, inspect_session
                        from maa.pipeline import JTemplateMatch
                        if not hasattr(runtime, "checkbox_reader"):
                            runtime.checkbox_reader = CheckboxReader(runtime.config["resource_dir"])
                        def checkbox_match(roi):
                            return runtime.checkbox_reader.read(argv.image, roi,
                                lambda names, area: context.run_recognition_direct("TemplateMatch",
                                    JTemplateMatch(template=names, roi=area, threshold=[.85] * len(names)), argv.image))
                        analysis["session"] = inspect_session(analysis, checkbox_match)
                    if params.get("quest"):
                        from .quests import QuestCatalog
                        from maa.pipeline import JTemplateMatch
                        if not hasattr(runtime, "quest_catalog"):
                            runtime.quest_catalog = QuestCatalog(runtime.config["quest_file"], runtime.config["operation_map_file"])
                            runtime.quest_tick = np.asarray(Image.open(runtime.config["resource_dir"] / "image/quest_claimed_tick.png").convert("RGB"))[:, :, ::-1].copy()
                        def claimed_match(roi):
                            result = context.run_recognition_direct("TemplateMatch",
                                JTemplateMatch(template=["quest_claimed_tick.png"], roi=roi, threshold=[.94]), argv.image)
                            box = list(result.box) if result and result.hit and result.box else None
                            return box if box and pixel_error(argv.image, runtime.quest_tick, box) <= 12 else None
                        analysis["quest"] = runtime.quest_catalog.inspect(
                            {**analysis, "window": {"client_size": runtime.config["reference_size"]}}, claimed_match)
                    from .quests import navigation_context
                    analysis.update(window=runtime.guard(),epoch_seconds=time.time())
                    analysis["navigation"] = navigation_context(analysis)
                    if read_text:
                        from .prequel import augment_title
                        augment_title(analysis, params.get('path', {}),
                            lambda kind,args:context.run_recognition_direct(kind,args,argv.image))
                    analysis["ui_tree"] = build_tree(analysis, runtime.vision.spec)
                    runtime.observer.count("recognitions")
                    runtime.observer.count("analysis_wall_ms", (time.perf_counter() - analysis_started) * 1000)
                    runtime.observer.count("analysis_cpu_ms", (time.process_time() - cpu_started) * 1000)
                    if not params.get("observe"):
                        # Maa provides the frame, but not its capture timestamp.
                        # Publish its meaning without claiming capture freshness.
                        runtime.observer.publish(analysis, "maa_pipeline")
                    self.latest = analysis
                    runtime.evidence.live(argv.image,analysis)
                    if params.get("observe"):
                        box = [0, 0, 1, 1]
                    elif params.get("session"):
                        from .session import session_target
                        box = session_target(analysis["ui_tree"], params)
                    elif params.get("stage_id"):
                        box = runtime.stage_inspector.target(analysis,params)
                    elif params.get('path'):
                        from .path_execution import path_target
                        box = path_target(analysis, params['path'], argv.image,runtime.path_prepared)
                    elif params.get('auto_state') is not None and operation_view(analysis).get('view') in ('battle_exit','battle_clear_banner','battle_rewards'):
                        box = None
                    else:
                        box = runtime.vision.target(analysis, params)
                    if box is not None:
                        runtime.evidence.recognized(argv.node_name, argv.image, analysis)
                    return self.AnalyzeResult(box=box, detail=analysis)
                except Exception as exc:
                    # Exceptions must not escape a ctypes callback.
                    if not runtime.execution_cancelled:
                        runtime.fatal = str(exc)
                    try:runtime.observer.invalidate('recognition_failed')
                    except Exception:pass  # Never escape a native callback.
                    return None

        Tasker.set_log_dir(self.evidence.path / "maa")
        Tasker.set_stdout_level(LoggingLevelEnum.Off)
        self.ctrl = Win32Controller(self.original["hwnd"], self.config["screencap_method"],
                                    self.config["mouse_method"], self.config["keyboard_method"])
        self.ctrl.set_screenshot_use_raw_size(True)
        self.wait(self.ctrl.post_connection())
        from .execution import OperationCycle, boundary_action
        runtime.operation_cycle = OperationCycle(runtime)
        self.action_boundary = boundary_action(runtime)
        self.resource = Resource()
        self.resource.set_cpu()
        if not self.resource.register_custom_action('OperationBoundary',self.action_boundary):
            raise RuntimeError('Não foi possível registrar a fronteira de ação Maa.')
        self.bridge = ScreenTarget()
        if not self.resource.register_custom_recognition("ScreenTarget", self.bridge):
            raise RuntimeError("Não foi possível registrar o reconhecimento ScreenTarget.")
        self.wait(self.resource.post_bundle(self.config["resource_dir"]))
        self.tasker = Tasker()
        if not self.tasker.bind(self.resource, self.ctrl):
            raise RuntimeError("Não foi possível conectar recurso e controlador Maa.")
        from maa.context import ContextEventSink
        from maa.event_sink import NotificationType
        class ObserverEvents(ContextEventSink):
            def on_node_action(self, context, noti_type, detail):
                try:
                    if noti_type == NotificationType.Starting:
                        runtime.observer.invalidate("pipeline_action_started", node=detail.name)
                except Exception as exc:
                    runtime.fatal = str(exc)
        self.observer_events = ObserverEvents()
        if self.tasker.add_context_sink(self.observer_events) is None:
            raise RuntimeError("Não foi possível registrar o observador do Maa.")
        from maa.tasker import TaskerEventSink
        class ObserverTasks(TaskerEventSink):
            def on_tasker_task(self, tasker, noti_type, detail):
                try:
                    if noti_type in (NotificationType.Succeeded, NotificationType.Failed):
                        if not detail.entry.startswith("recognition/"):
                            runtime.observer.event("pipeline_finished", entry=detail.entry,
                                                   succeeded=noti_type == NotificationType.Succeeded)
                except Exception as exc:
                    runtime.fatal = str(exc)
        self.observer_tasks = ObserverTasks()
        if self.tasker.add_sink(self.observer_tasks) is None:
            raise RuntimeError("Não foi possível registrar a conclusão observada do Maa.")
    def post_task(self, entry, override=None):
        """Materialize overrides before wrapping; one Tasker/controller remains."""
        if self.execution_cancelled:
            raise RuntimeError('Execução cancelada antes de iniciar o Maa.')
        from copy import deepcopy
        from .execution import wrap_graph
        if not hasattr(self,'pipeline_nodes'):
            self.pipeline_nodes = {}
            for path in sorted((self.config['resource_dir']/'pipeline').glob('*.json')):
                self.pipeline_nodes.update({k:v for k,v in json.loads(path.read_text(encoding='utf-8')).items()
                                            if not k.startswith('$')})
        graph = deepcopy(self.pipeline_nodes)
        for name,node in (override or {}).items():
            graph[name] = {**graph.get(name,{}),**deepcopy(node)}
        if entry == 'Finish.Entry' and getattr(self,'current_campaign_reservation',None):
            from .execution import annotate_campaign_result
            annotate_campaign_result(graph,*self.current_campaign_reservation,require_three_stars=True)
        return self.tasker.post_task(entry,wrap_graph(graph))

    @property
    def execution_cancelled(self):
        event = getattr(self, '_execution_cancel', None)
        return bool(event and event.is_set())

    def prepare_execution(self, identity):
        """Only the session's single worker may prepare another request."""
        if self.tasker and self.tasker.running:
            raise RuntimeError('Há uma execução Maa ativa; não iniciar outra entrada.')
        if not hasattr(self, '_execution_cancel'):
            self._execution_cancel = Event()
        self._execution_cancel.clear()
        self.execution_identity = identity
        self.execution_dispatched = False

    def cancel_execution(self):
        """Signal only. The owning worker stops Maa and preserves its ledger."""
        if not hasattr(self, '_execution_cancel'):
            self._execution_cancel = Event()
        self._execution_cancel.set()

    def stop_task(self, timeout=10):
        """Do not release the emitter until Maa confirms it has stopped."""
        if not self.tasker or not self.tasker.running:
            return
        stop=self.tasker.post_stop()
        deadline=time.monotonic()+timeout
        while (not stop.done or self.tasker.running) and time.monotonic()<deadline:
            time.sleep(.01)
        if not stop.done or self.tasker.running:
            self.fatal='Parada Maa não comprovada; conexão e perfil permanecem reservados.'
            raise RuntimeError(self.fatal)

    def guard(self, input_active=False):
        try:
            if input_active and self.execution_cancelled:
                raise RuntimeError('Execução cancelada; conferir o diário antes de continuar.')
            if self.fatal:
                raise RuntimeError(self.fatal)
            if input_active and self.config["stop_file"].exists():
                raise RuntimeError("Execução interrompida por var/STOP.")
            current = self.windows.inspect(self.original["hwnd"])
            verify_window(current, self.original, self.config, input_active)
            return current
        except Exception:
            if hasattr(self, 'observer'):
                self.observer.invalidate('runtime_guard_failed')
            raise

    def wait(self, job, timeout=None, task=False):
        if job.job_id <= 0:
            raise RuntimeError(f"Maa recusou a operação (job_id inválido); consulte a evidência em {self.evidence.path}.")
        end = time.monotonic() + (timeout or self.config["job_timeout_seconds"])
        while not job.done:
            if self.execution_cancelled or self.fatal or (task and self.config["stop_file"].exists()) or time.monotonic() > end:
                if task and self.tasker:
                    self.stop_task()
                if hasattr(self, 'observer'):
                    self.observer.invalidate('execution_cancelled' if self.execution_cancelled else 'execution_interrupted')
                raise RuntimeError(self.fatal or ('Execução cancelada.' if self.execution_cancelled else "Execução interrompida ou tempo limite excedido."))
            time.sleep(.01)
        if not job.succeeded:
            if hasattr(self, 'observer'):
                self.observer.invalidate('maa_operation_failed')
            raise RuntimeError(f"Operação Maa não concluiu; consulte a evidência em {self.evidence.path}.")
        return job

    def capture(self):
        try:
            self.guard()
            frame = self.wait(self.ctrl.post_screencap()).get()
            if hasattr(self, "observer"):
                self.observer.count("driver_captures")
            if list(frame.shape[:2][::-1]) != self.config["reference_size"]:
                raise RuntimeError("A captura tem dimensão diferente do perfil.")
            self.guard()
            return frame
        except Exception:
            if hasattr(self, 'observer'):
                self.observer.invalidate('capture_failed')
            raise

    def observe(self, name="observation", stage_id=None, read_text=False, text_roi=None, quest=False, session=False):
        try:
            return self._observe(name, stage_id, read_text, text_roi, quest, session)
        except Exception:
            if hasattr(self, 'observer'):
                self.observer.invalidate('observation_failed')
            raise

    def _observe(self, name="observation", stage_id=None, read_text=False, text_roi=None, quest=False, session=False):
        from maa.pipeline import JCustomRecognition
        frame = self.capture()
        captured_at = time.time()
        params={"observe":True}
        if session:
            params["session"] = True
        if quest:
            params["quest"] = True
        if read_text:
            roi = text_roi or [0, 0, *self.config["reference_size"]]
            x, y, w, h = roi
            width, height = self.config["reference_size"]
            if x < 0 or y < 0 or w < 1 or h < 1 or x+w > width or y+h > height:
                raise ValueError("Região de leitura fora da área cliente.")
            model = self.config["resource_dir"] / "model/ocr/en_us"
            if not all((model/file).is_file() for file in ("det.onnx", "rec.onnx", "keys.txt")):
                raise ValueError("OCR não instalado; execute tools/install_ocr.py.")
            params.update(read_text=True, text_roi=list(roi))
        if stage_id:
            self.stage_inspector.get(stage_id)
            params["stage_id"]=stage_id
        args = JCustomRecognition(custom_recognition="ScreenTarget", custom_recognition_param=params)
        self.wait(self.tasker.post_recognition("Custom", args, frame))
        if self.bridge.latest is None:
            raise RuntimeError("O reconhecimento não retornou uma observação.")
        data = {**self.bridge.latest, "epoch_seconds": time.time(), "window": self.guard(),
                "captured_at_epoch_seconds": captured_at,
                "methods": {key: self.config[key] for key in ("screencap_method", "mouse_method", "keyboard_method")},
                "frame": self.evidence.frame(name, frame),
                "log": sentry_context(self.config["sentry_root"], self.config["sentry_fresh_seconds"]),
                "evidence_dir": str(self.evidence.path)}
        if read_text or stage_id:
            from .quests import navigation_context
            data["navigation"] = navigation_context(data)
        data["observation_file"] = str(self.evidence.path / f"{name}.json")
        data["ui_tree"] = build_tree(data, self.vision.spec if hasattr(self, "vision") else None)
        data["observation_id"] = data["ui_tree"]["observation_id"]
        self.evidence.write(name, data)
        if hasattr(self, "observer"):
            self.observer.publish(data, "driver_observe")
        return data

    def read_snapshot(self, max_age_ms=500, *, refresh=True, after_sequence=0):
        """Read the common tree; fresh reads reuse it, actions still re-observe."""
        current = self.guard()
        snapshot = self.observer.snapshot(max_age_ms, after_sequence, current)
        if snapshot["validity"]["valid"]:
            self.observer.count("cache_hits")
        elif refresh:
            if self.tasker.running:
                raise RuntimeError("Pipeline ativo; consulte o snapshot sem refresh, sem iniciar captura concorrente.")
            self.observer.count("refreshes")
            self.observe("observer_refresh")
        return self.observer.snapshot(max_age_ms, after_sequence, self.guard())

    def stage_operation(self, operation, stage_id, max_energy=None, allow_replay=False):
        from .stages import compile_pipeline, check_start
        stage=self.stage_inspector.get(stage_id)
        model=self.config["resource_dir"] / "model/ocr/en_us"
        if not all((model/name).is_file() for name in ("det.onnx","rec.onnx","keys.txt")):
            raise ValueError("OCR não instalado; execute tools/install_ocr.py.")
        before=self.observe("stage_before",stage_id)
        info=stage_view(before)
        if operation=="inspect":
            return before
        override=compile_pipeline(stage_id,operation,max_energy,allow_replay)
        if screen_state(before) not in ("episode_map","supporter_selection","battle_ready"):
            raise ValueError("A seleção de fase começa no mapa ou na preparação.")
        if not info["context_verified"]:
            raise ValueError("Episódio/capítulo ou fase da preparação divergente; entrada não enviada.")
        if info["row_locked"] is True:
            raise ValueError("A fase solicitada está bloqueada.")
        if operation=="start" and max_energy < stage["energy"]:
            raise ValueError("Limite de energia inferior ao custo catalogado.")
        if operation=="start" and screen_state(before)=="battle_ready":
            check_start(stage,info,max_energy,allow_replay)
        self.guard(input_active=True)
        began=time.perf_counter()
        job=self.post_task("Stage.Entry",override)
        try:
            self.wait(job,120 if operation=="start" else 45,task=True)
            nodes=[{"name":node.name,"completed":node.completed,
                    "action_success":node.action.success if node.action else None} for node in job.get().nodes]
            success_nodes=["Stage.CheckReady"] if operation=="prepare" else ["Stage.EnteredStory","Stage.EnteredIntro","Stage.EnteredBattle"]
            if not any(node["completed"] and node["name"] in success_nodes for node in nodes):
                raise RuntimeError("O pipeline de fase não atingiu sua condição de conclusão.")
            after=self.observe("stage_after",stage_id)
            if operation=="prepare":
                # A UI can change scale during its entrance animation. Require
                # two consistent identity/cost observations, with bounded reads.
                deadline=time.monotonic()+4
                consistent=0
                while time.monotonic()<deadline:
                    info_after=stage_view(after)
                    energy=info_after.get("energy")
                    valid=(screen_state(after)=="battle_ready" and info_after.get("identity_verified")
                           and energy is not None and energy["cost"]==stage["energy"])
                    consistent=consistent+1 if valid else 0
                    if consistent>=2:break
                    time.sleep(.15)
                    after=self.observe("stage_after",stage_id)
                if consistent<2:
                    raise RuntimeError("A preparação não estabilizou com a identidade e custo esperados.")
            if operation=="prepare" and (screen_state(after)!="battle_ready" or not stage_view(after)["identity_verified"]):
                raise RuntimeError("A preparação final diverge da fase solicitada.")
            if operation=="start" and screen_state(after) not in ("story","story_intro","battle_running"):
                raise RuntimeError("Entrada de fase não confirmada visualmente.")
            result={"operation":operation,"stage_id":stage_id,"title":stage["title"],
                    "completed":True,"nodes":nodes,"max_starts":1 if operation=="start" else 0,
                    "max_energy":max_energy,"before":before,"after":after,
                    "elapsed_ms":round((time.perf_counter()-began)*1000,2),
                    "evidence_dir":str(self.evidence.path)}
            self.evidence.write("stage_result",result)
            return result
        except Exception as exc:
            self.evidence.write("stage_failure",{"operation":operation,"stage_id":stage_id,"error":str(exc)})
            raise

    def wait_state(self, state, timeout=6):
        if state not in self.vision.spec["states"]:
            raise ValueError("Estado não calibrado: "+state)
        deadline = time.monotonic()+timeout
        while True:
            found = self.observe("after")
            if screen_state(found) == state:
                return found
            if time.monotonic() > deadline:
                raise RuntimeError("Estado de destino não confirmado: "+state)
            time.sleep(.1)

    def ensure_auto(self):
        """One conditional Maa click; no toggle from unknown and no battle start."""
        from .observed_ui import auto_state
        before = self.observe('auto_before')
        if screen_state(before) != 'battle_running' or auto_state(before) is None:
            raise ValueError('Auto exige combate e HUD ligado/desligado reconhecidos; entrada não enviada.')
        if auto_state(before) is True:
            return {'completed': True, 'changed': False, 'before_state': 'battle_running',
                    'after_state': 'battle_running', 'max_clicks': 0}
        self.guard(input_active=True)
        job = self.post_task('Auto.Entry')
        self.wait(job, 12, task=True)
        after = self.observe('auto_after')
        nodes = [{'name': n.name, 'completed': n.completed} for n in job.get().nodes]
        completed = auto_state(after) is True and any(n['name'] == 'Auto.Done' and n['completed'] for n in nodes)
        changed = any(n['name'] == 'Auto.Enable' and n['completed'] for n in nodes)
        result = {'completed': completed, 'changed': changed if completed else None,
                  'max_clicks': 1, 'before_state': screen_state(before), 'after_state': screen_state(after),
                  'nodes': nodes, 'needs_review': not completed, 'evidence_dir': str(self.evidence.path)}
        self.evidence.write('auto_result', result)
        return result

    def campaign_terminal(self,nodes,success,observation_name,stage_id=None):
        completed=[n['name'] for n in nodes if n['completed'] and n['action_success'] is not False]
        defeat=any(n.endswith('Finish.Defeat') for n in completed)
        criteria=any(n.endswith('Finish.CriteriaUnverified') for n in completed)
        reached=success in completed
        error=None
        try:after=self.observe(observation_name,stage_id) if stage_id else self.observe(observation_name)
        except (RuntimeError,OSError,ValueError) as exc:after=None;error=str(exc)
        if not (defeat or criteria or reached):raise RuntimeError('Conclusão não comprovada; não repetir Start.')
        return {'completed':reached,'postcondition_verified':reached,'battle_result':'defeat' if defeat else 'victory' if criteria or reached else None,
                'criteria_verified':False if criteria else True if reached else None,
                'diagnostic':'three_star_proof_missing' if criteria else 'defeat_requires_agent_decision' if defeat else None,
                'needs_review':defeat or criteria or error is not None,'observation_error':error,'after':after,
                'nodes':nodes,'evidence_dir':str(self.evidence.path)}

    def finish_battle(self, timeout=240):
        if not 1 <= timeout <= 600:
            raise ValueError("Limite de batalha deve estar entre 1 e 600 segundos.")
        before=self.observe("battle_finish_before")
        if screen_state(before) not in ("story","story_intro","story_confirmation","battle_running","stage_clear","battle_rewards","story_reward","side_story_alert","friend_request","received_reward","tap_to_close_notice","rank_up","connection_unlocked","battle_failed"):
            raise ValueError("Conclusão de batalha exige história, combate ou resultado reconhecido.")
        self.guard(input_active=True)
        job=self.post_task("Finish.Entry")
        try:
            self.wait(job,timeout,task=True)
            nodes=[{"name":node.name,"completed":node.completed,
                    "action_success":node.action.success if node.action else None} for node in job.get().nodes]
            result=self.campaign_terminal(nodes,'Finish.VerifyDone','battle_finish_after')
            result.update(before_state=screen_state(before),after_state=screen_state(result['after']) if result['after'] else None,
                          frame=result['after'].get('frame') if result['after'] else None)
            self.evidence.write("battle_finish_result",result)
            return result
        except Exception as exc:
            self.evidence.write("battle_finish_failure",{"error":str(exc),"evidence_dir":str(self.evidence.path)})
            raise

    def run_chapter(self, from_stage, max_energy, timeout=600, finish_current=False):
        from .chapters import compile_chapter
        if not 1<=timeout<=3600:
            raise ValueError("Limite do trecho deve estar entre 1 e 3600 segundos.")
        plan,graph=compile_chapter(self.config,from_stage,max_energy,finish_current)
        from .plans import begin_runtime_plan, existing_runtime_plan, resume_chapter
        original_specification=plan['finite_plan']
        previous=existing_runtime_plan(self)
        entry,terminal='Chapter.Entry','Chapter.Done'
        if previous:
            plan,graph,entry,terminal=resume_chapter(self.config,from_stage,max_energy,self.attempts.read()['stages'],
                allow_defeat_retry=bool(getattr(self,'execution_retry',None)))
        before=self.observe("chapter_before",from_stage)
        finishing_states=("lobby","lobby_idle","story","story_intro","story_confirmation","battle_running","stage_clear","battle_rewards","story_reward","side_story_alert","friend_request","received_reward","tap_to_close_notice","rank_up","connection_unlocked")
        resume_allowed=(finish_current or previous is not None) and screen_state(before) in (
            *finishing_states,'episode_map','supporter_selection','battle_ready')
        if not resume_allowed and (screen_state(before) not in ("episode_map","supporter_selection","battle_ready") or not stage_view(before)["context_verified"]):
            raise ValueError("O trecho começa no capítulo correto ou na preparação da fase inicial.")
        if finish_current and self.attempts and previous is None:
            pending=self.attempts.pending_before(self.stage_inspector.catalog,from_stage)
            if pending:
                from .execution import annotate_campaign_result
                current={name.removeprefix('Chapter.Current.'):node for name,node in graph.items()
                         if name.startswith('Chapter.Current.')}
                annotate_campaign_result(current,*pending,require_three_stars=True)
                graph['Chapter.Current.Finish.CriteriaUnverified']=current['Finish.CriteriaUnverified']
                for node in graph.values():
                    following=node.get('next',[])
                    clear='Chapter.Current.Finish.Clear'
                    checkpoint='Chapter.Current.Finish.CriteriaUnverified'
                    if clear in following and checkpoint not in following:
                        following.insert(following.index(clear),checkpoint)
            else:raise ValueError("Não há tentativa anterior vinculada para concluir antes do trecho.")
        self.guard(input_active=True)
        self.evidence.write("chapter_plan",{**plan,"graph":graph})
        checkpoint=begin_runtime_plan(self,original_specification,timeout,resume=previous is not None)
        try:
            remaining=min(timeout,checkpoint.read()['deadline_epoch_seconds']-time.time())
            if remaining<=0:
                raise RuntimeError('Prazo original do plano expirou.')
            job=self.post_task(entry,graph)
            self.wait(job,remaining,task=True)
            nodes=[{"name":node.name,"completed":node.completed,
                    "action_success":node.action.success if node.action else None} for node in job.get().nodes]
            result={**plan,**self.campaign_terminal(nodes,terminal,'chapter_after',plan['stage_ids'][-1]),'before':before,
                    'finite_plan':original_specification}
            result['plan_checkpoint']=checkpoint.finish(result)
            self.evidence.write("chapter_result",result)
            return result
        except Exception as exc:
            try:checkpoint.finish(error=exc)
            except Exception as failure:exc.add_note('Falha ao preservar checkpoint: '+str(failure))
            try:self.evidence.write("chapter_failure",{"error":str(exc),"plan":plan})
            except Exception as failure:exc.add_note('Falha ao preservar evidência: '+str(failure))
            raise
        finally:
            self.active_plan_checkpoint=None

    def primitive(self, action, *, target=None, point=None, observation=None,
                  from_state=None, expect=None, key=None, duration_ms=1500, end_point=None, key_duration_ms=100):
        if action == 'key' and key_duration_ms != 100:
            if (key != 'escape' or observation is None or not isinstance(key_duration_ms,int)
                    or isinstance(key_duration_ms,bool) or not 100 <= key_duration_ms <= 5000):
                raise ValueError('Tecla longa exige Escape, observação explícita e duração entre 100 e 5000 ms.')
        # Read the supplied evidence before creating a fresh "before" artifact:
        # callers may refer to an earlier file with that same name.
        semantic_read = bool(observation and action in ('click','key') and not target)
        saved = previous = None
        navigation_guard = None
        if semantic_read:
            saved = json.loads(Path(observation).read_text(encoding="utf-8"))
            previous = np.asarray(Image.open(saved["frame"]).convert("RGB"))[:, :, ::-1].copy()
        before = self.observe("before", read_text=True) if semantic_read else self.observe("before")
        if expect is not None and expect not in self.vision.spec["states"]:
            raise ValueError("Estado de destino não calibrado: "+expect)
        if from_state is not None and screen_state(before) != from_state:
            raise ValueError("O estado mudou; entrada não enviada.")
        if action == "skill_double_tap":
            from .gestures import skill_double_tap_graph
            if observation is None or from_state is None or target is not None:
                raise ValueError("Toque duplo exige habilidade por ponto, observação e estado explícitos.")
            gesture_graph = skill_double_tap_graph(point, from_state, before["window"]["client_size"])
        method = "recognized_target" if target else "recognized_state"
        if target:
            if screen_state(before) == "unknown":
                raise ValueError("Tela desconhecida; use uma observação para calibrar a ação.")
            allowed = self.vision.spec["target_states"].get(target, [])
            if screen_state(before) not in allowed:
                raise ValueError("O alvo não pertence ao estado atual.")
            box = self.vision.target(before, {"state": screen_state(before), "target": target})
            if not box:
                raise ValueError("Alvo não reconhecido: "+target)
            point = [box[0]+box[2]//2, box[1]+box[3]//2]
        elif point is not None or (key and (from_state is None or screen_state(before) == "unknown")):
            if observation is None:
                raise ValueError("A primitiva por coordenada/tecla sem estado requer --observation.")
            if saved is None:
                saved = json.loads(Path(observation).read_text(encoding="utf-8"))
            check_observation(saved, before["window"], time.time())
            if previous is None:
                previous = np.asarray(Image.open(saved["frame"]).convert("RGB"))[:, :, ::-1]
            # The UI proof and pixels must describe the exact same Maa frame.
            current = (np.asarray(Image.open(before["frame"]).convert("RGB"))[:,:,::-1]
                       if semantic_read else self.capture())
            height, width = current.shape[:2]
            global_mae = pixel_error(current, previous, [0, 0, width, height])
            if semantic_read:
                from .input_guards import navigation_proof
                from .observed_ui import tree_for
                navigation_guard = navigation_proof(tree_for(saved), before['ui_tree'], previous, current,
                                                     action=action, point=point, key=key)
                navigation_guard.update(global_pixel_mae=global_mae, observation=observation,
                                        current_observation=before.get('observation_file'))
                self.evidence.write('navigation_guard',navigation_guard)
                if navigation_guard['status']=='rejected':
                    self.evidence.write('primitive_guard_failure',{**navigation_guard,'input_sent':False})
                    raise ValueError('Navegação não comprovada na tela atual: '+navigation_guard['reason'])
            semantic_ok = navigation_guard and navigation_guard['status']=='accepted'
            if global_mae > 12 and not semantic_ok:
                rejected_frame = self.evidence.frame("primitive_rejected", current)
                self.evidence.write("primitive_guard_failure", {
                    "reason": "global_frame_changed", "global_pixel_mae": global_mae,
                    "limit": 12, "point": point, "observation": observation,
                    "current_frame": rejected_frame, "input_sent": False})
                raise ValueError("A tela mudou desde a observação; capture novamente.")
            if point is not None and not semantic_ok:
                px, py = point
                if not 0 <= px < width or not 0 <= py < height:
                    raise ValueError("Ponto fora da área cliente.")
                left, top = max(0, px-16), max(0, py-16)
                patch = [left, top, min(32, width-left), min(32, height-top)]
                template = previous[top:top+patch[3], left:left+patch[2]]
                local_mae = pixel_error(current, template, patch)
                if local_mae > 18:
                    rejected_frame = self.evidence.frame("primitive_rejected", current)
                    self.evidence.write("primitive_guard_failure", {
                        "reason": "target_region_changed", "global_pixel_mae": global_mae,
                        "local_pixel_mae": local_mae, "limit": 18, "point": point,
                        "observation": observation, "current_frame": rejected_frame,
                        "input_sent": False})
                    raise ValueError("A região do clique mudou; capture novamente.")
            method = 'semantic_navigation' if semantic_ok else "observed_coordinate" if point else "observed_key"
        elif key and screen_state(before) == "unknown":
            raise ValueError("Uma tecla em tela desconhecida requer --observation.")
        if action in ("click","hold","skill_double_tap") and point is None:
            raise ValueError("Clique requer um alvo ou ponto observado.")
        if action == "swipe":
            width, height = self.config["reference_size"]
            if point is None or observation is None or end_point is None:
                raise ValueError("Swipe requer início, fim e observação recente.")
            if not 0 <= end_point[0] < width or not 0 <= end_point[1] < height:
                raise ValueError("Fim do gesto fora da área cliente.")
            if not 200 <= duration_ms <= 2000:
                raise ValueError("Swipe deve durar entre 200 e 2000 ms.")
        if action == "key":
            from .hotkeys import KEY_CODES, KEY_PRESS_MS, NAVIGATION_STATES
            if key not in KEY_CODES:
                raise ValueError("Tecla não habilitada como primitiva de navegação.")
            if (key != "escape" and screen_state(before) not in NAVIGATION_STATES
                    and not (navigation_guard and navigation_guard['status']=='accepted')):
                raise ValueError("Atalho de navegação exige uma tela calibrada fora de combate e de confirmações.")
        self.guard(input_active=True)
        started = time.perf_counter()
        self.execution_dispatched = True
        if hasattr(self, "observer"):
            self.observer.invalidate("primitive_action_started")
        if action == "click":
            self.wait(self.ctrl.post_click(*point))
        elif action == "skill_double_tap":
            # Maa's native repeat is a two-tap gesture at one already-checked
            # skill point. It is not a retry of a consuming game operation.
            self.evidence.write("skill_double_tap_request", {
                "point": list(point), "from_state": from_state, "requested_clicks": 2,
                "observation": observation, "graph": gesture_graph,
                "dispatch_succeeded": None, "postcondition_verified": False})
            job = self.post_task("SkillDoubleTap.Entry", gesture_graph)
            try:
                self.wait(job, 5, task=True)
                if not any(n.name == "SkillDoubleTap.Done" and n.completed for n in job.get().nodes):
                    raise RuntimeError("O gesto não atingiu sua condição final; não repetir sem observar.")
            except Exception as exc:
                self.evidence.write("skill_double_tap_failure", {
                    "error": str(exc), "requested_clicks": 2, "clicks_sent": None,
                    "point": list(point), "observation": observation, "needs_review": True})
                raise
        elif action == "swipe":
            self.wait(self.ctrl.post_swipe(*point, *end_point, duration_ms))
        elif action == "hold":
            if not 300<=duration_ms<=5000:
                raise ValueError("Clique mantido deve durar entre 300 e 5000 ms.")
            from maa.pipeline import JLongPress
            self.wait(self.tasker.post_action("LongPress",JLongPress(target=(*point,1,1),duration=duration_ms)))
        elif action == "key":
            from maa.pipeline import JLongPressKey
            self.wait(self.tasker.post_action("LongPressKey",
                JLongPressKey(key=[KEY_CODES[key]], duration=key_duration_ms)))
        else:
            raise ValueError("Primitiva sem suporte.")
        result = {"action": action, "selection": method, "point": point, "target": target,
                  "methods": before.get("methods"),
                  "key": key, "dispatch_succeeded": True, "postcondition_verified": False,
                  "duration_ms": key_duration_ms if action == "key" else duration_ms if action in ("hold", "swipe") else None,
                  "end_point": end_point,
                  "expected_state": expect, "before_state": screen_state(before),
                  "evidence_dir": str(self.evidence.path)}
        if action == "skill_double_tap":
            result.update(requested_clicks=2, repeat_delay_ms=80, gesture_engine="Maa native repeat")
        if navigation_guard and navigation_guard['status']=='accepted':
            result['navigation_guard'] = navigation_guard
        self.evidence.write("primitive", result)
        try:
            after = (self.wait_state(expect) if expect else
                     self.observe("after",read_text=True) if navigation_guard and navigation_guard['status']=='accepted'
                     else self.observe("after"))
        except Exception as exc:
            result["error"] = str(exc)
            result["elapsed_ms"] = round((time.perf_counter()-started)*1000, 2)
            self.evidence.write("primitive", result)
            raise
        result.update(postcondition_verified=expect is not None, after_state=screen_state(after),
                      elapsed_ms=round((time.perf_counter()-started)*1000,2))
        if navigation_guard and navigation_guard['status']=='accepted':
            from .input_guards import navigation_arrived
            arrived=navigation_arrived(after,navigation_guard)
            result.update(postcondition_verified=arrived if expect is None else bool(arrived and result['postcondition_verified']),
                          navigation_destination_verified=arrived, needs_review=not arrived)
        self.evidence.write("primitive", result)
        return result

    def read_quest(self, name="quest_observation"):
        return self.observe(name, read_text=True, quest=True)

    def session_operation(self, operation):
        before = self.observe("session_before", read_text=True, session=True)
        if operation == "inspect":
            return before
        if operation not in ("prepare", "notifications-off", "dismiss-notices"):
            raise ValueError("Operação de preparação desconhecida.")
        if operation == "dismiss-notices" and screen_state(before) not in ("lobby", "lobby_idle", "notice_disable_confirmation"):
            raise ValueError("Fechamento de avisos calibrado na taberna ou em sua confirmação específica.")
        if operation != "dismiss-notices" and screen_state(before) not in ("lobby", "lobby_idle", "chat_panel", "chat_notifications"):
            raise ValueError("Preparação começa na taberna, chat ou configurações de notificação.")
        entry = "Notice.Entry" if operation == "dismiss-notices" else "Session.Entry"
        override = {"Session.ReturnToLobby": {"next": ["Session.OffDone"]}} if operation == "notifications-off" else {}
        self.guard(input_active=True)
        job = self.post_task(entry, override)
        try:
            self.wait(job, 90, task=True)
            nodes = [{"name": n.name, "completed": n.completed} for n in job.get().nodes]
            expected = "Session.OffDone" if operation == "notifications-off" else "Notice.Done"
            if not any(n["name"] == expected and n["completed"] for n in nodes):
                raise RuntimeError("Preparação não confirmou sua condição final.")
            after = self.observe("session_after", read_text=True, session=True)
            if screen_state(after) != "lobby":
                raise RuntimeError("Preparação não terminou na taberna.")
            result = {"operation": operation, "completed": True, "nodes": nodes,
                      "before_observation": before["observation_file"], "after_observation": after["observation_file"],
                      "methods": after["methods"], "notifications_enabled_by_driver": False,
                      "keyword_tab_touched": False, "evidence_dir": str(self.evidence.path)}
            self.evidence.write("session_result", result)
            return result
        except Exception as exc:
            self.evidence.write("session_failure", {"operation": operation, "error": str(exc), "before_observation": before["observation_file"]})
            raise

    def quest_action(self, operation, identity=None, observation=None, expect=None, allow_ready_group=False, expect_text=None, destination_kind=None):
        """One guarded UI action. No automatic retry or reward-dialog loop."""
        started = time.perf_counter()
        from .quests import QuestCatalog, action_target
        if operation == "open":
            return self.primitive("click", target="orbis_button", from_state="lobby", expect="orbis_guide")
        if observation is None:
            raise ValueError("A ação de missão requer --observation da leitura atual.")
        saved = json.loads(Path(observation).read_text(encoding="utf-8"))
        before = self.read_quest("quest_before")
        check_observation(saved, before["window"], time.time())
        if screen_state(before) != "orbis_guide":
            raise ValueError("Ação exige o painel Orbis Guide reconhecido.")
        # Preserve the selected identity across the fresh read. The actual
        # point comes only from current OCR or calibrated navigation anchors.
        if "ui_tree" not in saved and "quest" not in saved:
            raise ValueError("Use uma observação retornada por quest read.")
        current = quest_view(before)
        if quest_view(saved).get("group_id") != current.get("group_id"):
            raise ValueError("Grupo mudou desde a leitura; entrada não enviada.")
        catalog = QuestCatalog(self.config["quest_file"], self.config["operation_map_file"])
        if operation == "tab":
            if identity != "heir":
                raise ValueError("A aba inicial calibrada é heir.")
            box = target_box(before["ui_tree"], "orbis_heir_tab")
            if box is None:
                raise ValueError("Aba Path of Heir não identificada sem ambiguidade.")
        elif operation == "group":
            group = catalog.groups.get(identity)
            original = catalog.groups.get(current.get("group_id"))
            if not group or not original or group["path"] != "heir" or original["path"] != "heir":
                raise ValueError("Navegação requer dois grupos Path of Heir identificados.")
            distance = int(group["source_fields"]["sort"]) - int(original["source_fields"]["sort"])
            if abs(distance) != 1:
                raise ValueError("Esta primitiva navega um grupo adjacente por vez.")
            control = "next_group" if distance > 0 else "previous_group"
            box = query_control(before["ui_tree"], current["group_id"], None, control)["node"]["fields"]["box"]["value"]
        else:
            if operation == "go" and not expect_text and (not expect or expect not in self.vision.spec["states"] or expect == "unknown"):
                raise ValueError("Go requer --expect calibrado ou --expect-text exato do destino; não inicia batalhas.")
            if operation == "go" and destination_kind not in ("mode_menu", "battle_categories", "stage_list", "supporter_selection", "battle_preparation"):
                raise ValueError("Go requer --destination-kind para distinguir categoria, modo, lista e preparação.")
            if operation == "go" and expect_text:
                from .quests import has_text
                if has_text(text_rows(before), expect_text):
                    raise ValueError("Texto de destino já aparece na origem; escolha uma prova que distinga a transição.")
            box = action_target(catalog, current, operation, identity, tree=before["ui_tree"])
            if operation == "claim" and not allow_ready_group:
                raise ValueError("Receive pode resgatar todas as prontas do grupo; use --allow-ready-group quando autorizado.")
            if quest_view(saved).get("group_id") is None:
                raise ValueError("Grupo não estava identificado na leitura fornecida.")
        point = [box[0]+box[2]//2, box[1]+box[3]//2]
        # The coordinate primitive rechecks window age and pixel consistency
        # against the OCR frame immediately before dispatch.
        result = self.primitive("click", point=point, observation=before["observation_file"],
                                from_state="orbis_guide", expect=expect if operation == "go" else None)
        result.update(operation=operation, identity=identity, max_dispatches=1,
                      reward_claim_verified=False, needs_review=False,
                      claim_scope="all_ready_in_selected_group" if operation == "claim" else operation,
                      selected_group=current.get("group_id"))
        self.evidence.write("quest_action", result)
        after = self.read_quest("quest_after")
        # Read-only bounded settling: the server may answer after the click
        # animation. Never retry the reward action while waiting for evidence.
        deadline = time.monotonic()+5
        while time.monotonic() < deadline:
            if operation in ("claim", "claim-group"):
                from .quests import progress_signature
                changed = (screen_state(after) != "orbis_guide" or progress_signature(quest_view(after)) != progress_signature(current))
            elif operation == "group":
                changed = quest_view(after)["group_id"] == identity
            elif operation == "tab":
                changed = quest_view(after).get("path") == identity
            elif operation == "go" and expect_text:
                from .quests import has_text
                changed = has_text(text_rows(after), expect_text) and navigation_view(after)["kind"] == destination_kind
            else:
                changed = True
            if changed:
                break
            time.sleep(.15)
            after = self.read_quest("quest_after")
        if operation == "group":
            result["postcondition_verified"] = quest_view(after)["group_id"] == identity
        elif operation == "tab":
            result["postcondition_verified"] = quest_view(after).get("path") == identity
        elif operation == "go" and expect_text:
            result["expected_text"] = expect_text
            result["postcondition_verified"] = changed
        if operation == "go":
            result["destination"] = navigation_view(after)
            result["expected_destination_kind"] = destination_kind
            result["postcondition_verified"] = result["postcondition_verified"] and navigation_view(after)["kind"] == destination_kind
            result["verification_scope"] = "navigation_only"
            result["battle_start_dispatched"] = False
        elif operation in ("claim", "claim-group"):
            # A reward banner or a disappeared row is not a receipt. Read again
            # after dismissing only an understood informational banner.
            if operation == "claim":
                result["reward_claim_verified"] = any(t["task_id"] == identity and t["status"] == "claimed"
                    for t in quest_view(after)["visible_tasks"])
            else:
                result["reward_claim_verified"] = quest_view(after)["group_id"] == identity and quest_view(after)["group_claimed"]
            result["postcondition_verified"] = result["reward_claim_verified"]
            result["needs_review"] = not result["reward_claim_verified"]
        result["before_observation"] = before["observation_file"]
        result["after_observation"] = after["observation_file"]
        result["after_state"] = screen_state(after)
        result["note"] = "Uma entrada; sem retries ou escolhas automáticas. Releia antes da próxima ação."
        result["dispatch_elapsed_ms"] = result["elapsed_ms"]
        result["elapsed_ms"] = round((time.perf_counter()-started)*1000, 2)
        if not result["postcondition_verified"]:
            result["needs_review"] = True
        self.evidence.write("quest_action", result)
        return result

    def run(self, name):
        routine = executable_routine(self.config, name)
        before = self.observe("before")
        if screen_state(before) not in routine["initial_states"]:
            raise ValueError("Estado inicial incompatível: "+screen_state(before))
        self.guard(input_active=True)
        started = time.perf_counter()
        job = self.post_task(routine["entry"])
        try:
            self.wait(job, routine["max_seconds"], task=True)
            detail = job.get()
            nodes = [{"name": node.name, "completed": node.completed,
                      "action_success": node.action.success if node.action else None}
                     for node in detail.nodes]
            if not any(node["name"] == routine["success_node"] and node["completed"] for node in nodes):
                raise RuntimeError("O pipeline terminou sem atingir o nó de conclusão.")
            after = self.observe("after")
            if screen_state(after) != routine["final_state"]:
                raise RuntimeError("A tela final não confirmou a conclusão.")
            result = {"routine": name, "completed": True, "nodes": nodes,
                      "before_state": screen_state(before), "after_state": screen_state(after),
                      "elapsed_ms": round((time.perf_counter()-started)*1000,2),
                      "evidence_dir": str(self.evidence.path)}
            self.evidence.write("result", result)
            if hasattr(self, "observer"):
                self.observer.event("routine_completed", routine=name, state=screen_state(after))
            return result
        except Exception as exc:
            self.evidence.write("failure", {"routine": name, "completed": False, "error": str(exc)})
            raise

    def close(self):
        # A failed stop must not restore the profile or unlock another emitter
        # while a native gesture still owns the controller.
        if self.tasker and self.tasker.running:
            self.stop_task()
        try:
            if hasattr(self, "observer"):
                self.observer.invalidate("disconnected")
            if self.ctrl:
                job = self.ctrl.post_inactive()
                deadline = time.monotonic()+3
                while not job.done and time.monotonic()<deadline:
                    time.sleep(.02)
        finally:
            try:
                if self.window_profile:
                    self.window_profile.close()
            finally:
                self.lock.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
