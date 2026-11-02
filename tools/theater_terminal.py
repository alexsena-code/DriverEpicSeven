"""Read-only terminal reporting over the existing driver observer/events."""
import json
from pathlib import Path
import re
from threading import Event, Thread
import time
from uuid import uuid4

from driver_epic_seven.observed_ui import operation_view,screen_state,auto_state


def clock_text(seconds):
    seconds=max(0,int(seconds))
    return f'{seconds//60:02d}:{seconds%60:02d}'


def prepare_session(config):
    """Isolate report ownership; preserve the effective game profile exactly."""
    root=Path(config['runs_dir'])/('terminal_'+uuid4().hex[:12])
    root.mkdir(parents=True,exist_ok=False)
    snapshot=dict(config);snapshot['runs_dir']=str(root)
    path=root/'config.json'
    path.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    return root,path


def read_json(path):
    try:
        if path.stat().st_size>2_000_000:return None
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError):return None


class Progress:
    """Presentation only: never calls a controller, recognizer or executor."""
    def __init__(self,acts,timeout,*,started=None,heartbeat=5):
        self.acts=acts;self.timeout=timeout
        self.started=time.monotonic() if started is None else started
        self.heartbeat=heartbeat;self.last_output=None;self.last_phase=None
        self.cursor=0;self.unit=1;self.first_act=None;self.taps=0;self.done=set()
        self.action=None;self.action_time=None;self.partial=False;self.history_notice=False

    def update(self,snapshot=None,plan=None,*,now=None,wall_now=None):
        now=time.monotonic() if now is None else now
        wall_now=time.time() if wall_now is None else wall_now
        notes=[]
        if plan:
            self.first_act=plan.get('first_act',self.first_act)
        if snapshot:
            events=snapshot.get('events',[])
            if events and self.cursor<events[0]['sequence']-1:
                self.partial=True
                if not self.history_notice:
                    notes.append('Historico parcial: os totais serao conferidos no resultado final.')
                    self.history_notice=True
            for event in events:
                seq=event.get('sequence',0)
                if seq<=self.cursor:continue
                self.cursor=seq
                if event.get('kind')!='operation_dispatch':continue
                match=re.fullmatch(r'Theater\.(\d+)\.(\w+)',event.get('proof',{}).get('node',''))
                if not match:continue
                unit=int(match[1]);self.unit=unit;self.action=match[2]
                self.action_time=event.get('available_at_epoch_seconds')
                if self.action=='Tap':self.taps+=1
                if self.action=='Done':self.done.add(unit)
        latest=(snapshot or {}).get('snapshot')
        phase='Conectando o driver; aguardando primeira leitura'
        age=None
        if latest:
            available=latest.get('available_at_epoch_seconds')
            if available is not None:age=max(0,wall_now-available)
            try:
                observation={'ui_tree':latest['ui_tree']}
                current=operation_view(observation);view=current.get('view')
                state=screen_state(observation)
                if view=='theater_story':phase='Historia: avancando dialogos'
                elif view=='theater_intro':phase='Abertura do ato: avancando'
                elif view=='theater_ticket':phase='Ingresso: aguardando confirmacao'
                elif view=='theater_main':phase='Painel do Theater: conferindo ato e saldo'
                elif view=='battle_clear_banner':phase='CLEAR observado: avancando resultado'
                elif state in ('battle_running','battle_nightmare_keeper','battle_mercenary_lydia'):
                    auto=auto_state(observation)
                    phase=('Combate: Auto reconhecido ligado' if auto is True else
                           'Combate: Auto reconhecido desligado' if auto is False else
                           'Combate: Auto sem leitura confiavel; aguardando')
                elif state=='battle_failed':phase='Derrota observada; aguardando encerramento'
                elif view=='theater_blocked':phase='Confirmacao incompleta; aguardando leitura segura'
                elif view:phase='Outro painel observado; aguardando a tela esperada'
                else:phase='Tela nao reconhecida; aguardando reconhecimento'
                recent_action=self.action_time is not None and 0<=wall_now-self.action_time<=2
                if recent_action:
                    if self.action=='Watch' and view=='theater_main':phase='Solicitando Watch'
                    elif self.action=='Confirm' and view=='theater_ticket':phase='Solicitando confirmacao de um ingresso'
                    elif self.action=='Clear' and view=='battle_clear_banner':phase='Avancando resultado CLEAR'
                    elif self.action=='Auto' and state=='battle_running':phase='Solicitando ativacao do Auto'
            except (KeyError,ValueError,TypeError):phase='Leitura indisponivel; aguardando reconhecimento'
        if age is not None and age>=10:
            phase='Sem leitura recente; ultima etapa: '+phase
        target=(self.first_act+self.unit-1) if type(self.first_act) is int else '?'
        key=(phase,target,len(self.done),self.partial)
        if self.last_output is None or key!=self.last_phase or now-self.last_output>=self.heartbeat:
            self.last_output=now;self.last_phase=key
            prefix='pelo menos ' if self.partial else ''
            age_text=f'{int(age)}s' if age is not None else 'indisponivel'
            notes.append(f'[{clock_text(now-self.started)}] Ato alvo: {target} | Atos confirmados: {len(self.done)}/{self.acts} | '
                         f'{phase} | Avancos: {prefix}{self.taps} tentativas | Ultima leitura: {age_text}')
        return notes


class TerminalMonitor:
    def __init__(self,root,acts,timeout,*,emit=None):
        self.root=Path(root);self.progress=Progress(acts,timeout)
        self.emit=emit or (lambda text:print(text,flush=True))
        self.stop_event=Event();self.thread=None;self.run=None

    def write(self,message):
        # Report failures must not change game decisions or interrupt the driver.
        try:self.emit(message)
        except (OSError,ValueError):pass
        try:
            with (self.root/'progresso.log').open('a',encoding='utf-8') as stream:stream.write(message+'\n')
        except OSError:pass

    def poll(self):
        if self.run is None:
            children=[p for p in self.root.iterdir() if p.is_dir()]
            if children:self.run=sorted(children)[0]
        snapshot=read_json(self.run/'observer.json') if self.run else None
        plan=read_json(self.run/'theater_plan.json') if self.run else None
        for line in self.progress.update(snapshot,plan):self.write(line)

    def safe_poll(self):
        try:self.poll()
        except (OSError,ValueError,KeyError,TypeError):pass

    def _loop(self):
        while not self.stop_event.wait(.5):self.safe_poll()

    def __enter__(self):
        self.write('Acompanhamento ativo | Limite da tarefa: '+clock_text(self.progress.timeout))
        self.safe_poll()
        self.thread=Thread(target=self._loop,name='theater-terminal-report',daemon=True)
        self.thread.start()
        return self

    def __exit__(self,kind,error,traceback):
        self.stop_event.set()
        if self.thread:self.thread.join(timeout=3)
        self.safe_poll()
        if kind is not None:
            message='cancelada pelo operador' if issubclass(kind,KeyboardInterrupt) else str(error) or kind.__name__
            self.write('Execucao interrompida: '+message)
        return False

    def complete(self,result):
        # Final totals come from the verified task result, not estimates in events.
        self.stop_event.set()
        if self.thread:self.thread.join(timeout=3)
        self.safe_poll()
        count=result.get('completed_acts',0)
        label='CONCLUIDO' if result.get('completed') else 'PARADO PARA CONFERENCIA'
        self.write(f'{label} | Atos confirmados no resultado: {count}/{self.progress.acts}')
