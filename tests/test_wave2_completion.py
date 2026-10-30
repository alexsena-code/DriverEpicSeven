from types import SimpleNamespace
import pytest
from driver_epic_seven.runtime import Runtime
from driver_epic_seven.config import load_config
from driver_epic_seven.chapters import compile_chapter
from driver_epic_seven.execution import annotate_campaign_result
from driver_epic_seven.vision import Vision
from driver_epic_seven.observed_ui import build_tree


@pytest.mark.parametrize('terminal,result,complete',[('Finish.VerifyDone','victory',True),('Finish.Defeat','defeat',False),('Finish.CriteriaUnverified','victory',False)])
def test_terminal_proof_survives_later_capture_failure_and_never_restarts(terminal,result,complete):
    calls=[]
    def fail(*args):calls.append(args);raise OSError('capture disconnected after proof')
    r=SimpleNamespace(observe=fail,evidence=SimpleNamespace(path='evidence'))
    d=Runtime.campaign_terminal(r,[{'name':terminal,'completed':True,'action_success':True}],
        'Finish.VerifyDone','after')
    assert d['battle_result']==result and d['completed'] is complete and d['observation_error']
    assert len(calls)==1 and d['needs_review']
    if terminal.endswith('CriteriaUnverified'):assert d['diagnostic']=='three_star_proof_missing'


def test_unproven_timeout_cannot_become_defeat_or_completed():
    r=SimpleNamespace(observe=lambda *_:{'state':'unknown'},evidence=SimpleNamespace(path='evidence'))
    with pytest.raises(RuntimeError):Runtime.campaign_terminal(r,[],'Finish.VerifyDone','after')


def test_three_star_checkpoint_records_victory_and_stops_before_next_stage():
    plan,g=compile_chapter(load_config(),'pes005',20)
    checkpoints=[(k,v) for k,v in g.items() if k.endswith('Finish.CriteriaUnverified')]
    assert checkpoints and all('next' not in v and v['action']=='DoNothing' for _,v in checkpoints)
    assert all(v['custom_recognition_param']['execution']['status']=='victory' for _,v in checkpoints)
    assert all(v['custom_recognition_param']['require_three_stars'] is True for k,v in g.items() if k.endswith('Finish.Clear'))


def test_apply_preview_enters_guarded_non_action_entry(tmp_path,monkeypatch):
    from driver_epic_seven.application import Application
    from driver_epic_seven.cli import parser,request_from_args
    from driver_epic_seven.attempts import AttemptLedger
    from driver_epic_seven.composition import validate_graph
    import driver_epic_seven.path_execution as execution
    def inspect(runtime,nodes,entry,success,timeout):
        assert nodes[entry]['action']=='DoNothing'
        assert nodes[entry]['next']==['Path.Equipment.Enhance.Apply']
        validate_graph(nodes,entry,[success]);return {'completed':False}
    monkeypatch.setattr(execution,'run_graph',inspect)
    args=parser().parse_args(['path','equipment','--operation','enhance_weapon','--scope','unit',
        '--hero-name','Observed Hero','--apply-preview','--max-gold','100',
        '--material-limits','{"Lesser Equipment Charm":1}'])
    runtime=SimpleNamespace(config=load_config(),path_attempts=AttemptLedger(tmp_path/'ledger.json'))
    result=Application(runtime.config).execute(request_from_args(args),runtime)
    assert result['equipment_effect']=='uncertain'


def test_explicit_battle_scopes_do_not_require_a_mission_selector(tmp_path,monkeypatch):
    from driver_epic_seven.application import Application
    from driver_epic_seven.cli import parser,request_from_args
    import driver_epic_seven.battle_operations as operations
    calls=[]
    def unit(runtime,family,stage,scope,compilation,**kwargs):
        calls.append((family,stage,scope));assert compilation[0]['task_id']==scope
        return {'completed':True}
    monkeypatch.setattr(operations,'run_unit',unit)
    runtime=SimpleNamespace(config=load_config())
    for argv in (['path','altar','cmon002','--scope','independent altar','--prepare'],
                 ['path','abyss','--floor','32','--scope','independent abyss','--prepare']):
        Application(runtime.config).execute(request_from_args(parser().parse_args(argv)),runtime)
    assert calls==[('altar','cmon002','independent altar'),('abyss','abyss032','independent abyss')]
