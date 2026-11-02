"""Terminal reporting is a read-only consumer, isolated from game execution."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from driver_epic_seven.config import ROOT,load_config
from driver_epic_seven.observed_ui import build_tree

spec=importlib.util.spec_from_file_location('terminal_under_test',ROOT/'tools/theater_terminal.py')
terminal=importlib.util.module_from_spec(spec);spec.loader.exec_module(terminal)


def snapshot(*,view=None,state='unknown',auto=None,events=(),available=100):
    if view:
        from driver_epic_seven.observed_ui import node,fact
        tree=build_tree({'state':state,'matches':{},'window':{'process_name':'EpicSeven.exe','client_size':[1212,682]}})
        p=node('operation:test','panel','screen',adapter=fact('operations'),view=fact(view))
        tree['nodes'][p['id']]=p;tree['nodes']['screen']['children'].append(p['id'])
    else:
        matches={'auto_hud_on':{'hit':True}} if auto is True else {'auto_hud_off':{'hit':True}} if auto is False else {}
        tree=build_tree({'state':state,'matches':matches,'window':{'process_name':'EpicSeven.exe','client_size':[1212,682]}})
    return {'events':list(events),'snapshot':{'ui_tree':tree,'available_at_epoch_seconds':available}}


def event(seq,node,at=100):
    return {'sequence':seq,'kind':'operation_dispatch','proof':{'node':node},'available_at_epoch_seconds':at}


def test_startup_and_heartbeat_do_not_pretend_to_have_an_observation():
    p=terminal.Progress(2,600,started=0)
    assert 'aguardando primeira leitura' in p.update(now=0,wall_now=100)[-1]
    assert p.update(now=1,wall_now=101)==[]
    assert '00:05' in p.update(now=5,wall_now=105)[-1]


@pytest.mark.parametrize('view,text',[('theater_story','Historia'),('theater_intro','Abertura'),
    ('theater_ticket','Ingresso'),('battle_clear_banner','CLEAR'),('hero_detail','Outro painel')])
def test_observed_stage_is_displayed_without_actions(view,text):
    p=terminal.Progress(1,600,started=0)
    line=p.update(snapshot(view=view),{'first_act':9},now=1,wall_now=101)[-1]
    assert text in line and 'Ato alvo: 9' in line


@pytest.mark.parametrize('auto,text',[(True,'ligado'),(False,'desligado'),(None,'sem leitura confiavel')])
def test_battle_auto_reporting_preserves_unknown(auto,text):
    p=terminal.Progress(1,600,started=0)
    assert text in p.update(snapshot(state='battle_running',auto=auto),now=1,wall_now=100)[-1]


def test_events_are_deduplicated_and_taps_are_aggregated_instead_of_printed_per_click():
    p=terminal.Progress(2,600,started=0)
    first=snapshot(view='theater_story',events=[event(1,'Theater.1.Tap')])
    p.update(first,{'first_act':7},now=0,wall_now=100)
    second=snapshot(view='theater_story',events=[event(1,'Theater.1.Tap'),event(2,'Theater.1.Tap')])
    assert p.update(second,now=1,wall_now=101)==[]
    assert p.taps==2
    assert p.update(second,now=2,wall_now=102)==[] and p.taps==2
    line=p.update(second,now=5,wall_now=105)[-1]
    assert 'Avancos: 2 tentativas' in line


def test_done_requires_explicit_verified_node_and_unit_number_updates_target():
    p=terminal.Progress(3,600,started=0)
    line=p.update(snapshot(view='theater_main',events=[event(1,'Theater.1.Done'),event(2,'Theater.2.Watch')]),
        {'first_act':7},now=0,wall_now=100)[-1]
    assert 'Atos confirmados: 1/3' in line and 'Ato alvo: 8' in line
    assert 'Solicitando Watch' in line
    # An old action is not described as a new repeated input.
    line=p.update(snapshot(view='theater_main',events=[event(1,'Theater.1.Done'),event(2,'Theater.2.Watch')]),now=6,wall_now=106)[-1]
    assert 'Solicitando Watch' not in line


def test_stale_observation_and_missing_history_are_visible_not_invented():
    p=terminal.Progress(3,600,started=0)
    lines=p.update(snapshot(view='theater_story',available=70,events=[event(30,'Theater.2.Tap')]),now=0,wall_now=100)
    assert any('Historico parcial' in line for line in lines)
    assert 'Sem leitura recente' in lines[-1] and 'pelo menos 1' in lines[-1]


def test_session_owns_only_its_run_and_preserves_effective_profile(tmp_path):
    config=load_config();config['runs_dir']=tmp_path/'logs com espacos'
    root,path=terminal.prepare_session(config)
    loaded=load_config(str(path))
    assert loaded['runs_dir']==root
    assert all(loaded[key]==value for key,value in config.items() if key!='runs_dir')
    root2,_=terminal.prepare_session(config)
    assert root2!=root
    other=config['runs_dir']/'unrelated';other.mkdir()
    (other/'observer.json').write_text(json.dumps(snapshot(view='theater_story')))
    output=[];m=terminal.TerminalMonitor(root,1,60,emit=output.append)
    m.poll()
    assert m.run is None
    child=root/'own-run';child.mkdir();(child/'observer.json').write_text(json.dumps(snapshot(view='theater_intro',available=__import__('time').time())))
    m.poll()
    assert m.run==child and any('Abertura' in line for line in output)


def test_monitor_tolerates_partial_files_and_uses_final_verified_result(tmp_path):
    child=tmp_path/'run';child.mkdir();(child/'observer.json').write_text('{')
    output=[]
    with terminal.TerminalMonitor(tmp_path,2,60,emit=output.append) as monitor:
        monitor.complete({'completed':True,'completed_acts':2})
    assert any('Atos confirmados no resultado: 2/2' in line for line in output)
    assert monitor.stop_event.is_set() and not monitor.thread.is_alive()
    assert (tmp_path/'progresso.log').exists()


def test_reporting_error_never_hides_driver_failure(tmp_path,monkeypatch):
    output=[];m=terminal.TerminalMonitor(tmp_path,1,60,emit=output.append)
    monkeypatch.setattr(m,'poll',lambda:(_ for _ in ()).throw(ValueError('broken report')))
    with pytest.raises(RuntimeError,match='driver failed'):
        with m:raise RuntimeError('driver failed')
    assert any('driver failed' in line for line in output)
