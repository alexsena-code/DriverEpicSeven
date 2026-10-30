import pytest

from driver_epic_seven.attempts import AttemptLedger
from driver_epic_seven.stages import StageInspector


def test_attempt_limit_survives_new_ledger_and_duplicate_recognition(tmp_path):
    path=tmp_path/"attempts.json"
    ledger=AttemptLedger(path,3)
    ledger.reserve("a","run1",8)
    ledger.reserve("a","run1",8)
    ledger.mark("a","run1","entered")
    ledger=AttemptLedger(path,3)
    ledger.reserve("a","run2",8)
    ledger.reserve("a","run3",8)
    with pytest.raises(ValueError,match="Limite persistente"):
        ledger.reserve("a","run4",8)
    assert len(ledger.read()["stages"]["a"])==3
    assert ledger.read()["stages"]["a"][0]["status"]=="entered"


def test_multiline_chapter_title_requires_full_exact_text():
    rows=[{"text":"Chapter 6. The Depths of","score":.98},{"text":"Despair","score":.96}]
    assert StageInspector._exact_block(rows,"Chapter 6. The Depths of Despair")
    assert not StageInspector._exact_block(rows,"Chapter 6. The Depths of")


def test_roman_suffix_keeps_the_title_and_number_of_glyphs():
    rows=[{"text":"Forsaken Land,Forsaken","score":.96,"box":[884,104,193,17]},
          {"text":"Peoplel","score":.96,"box":[882,120,64,21]}]
    assert StageInspector._story_title(rows,"Forsaken Land, Forsaken People I")=="roman_suffix_glyph"
    assert StageInspector._story_title(rows,"Forsaken Land, Forsaken People II") is None
    assert StageInspector._story_title(rows,"Forsaken Land, Different People I") is None


def test_resume_attributes_pending_victory_across_chapter_boundary(tmp_path):
    ledger=AttemptLedger(tmp_path/"attempts.json")
    catalog={"old":{"id":"old","episode":2,"chapter":9,"ordinal":10},
             "next":{"id":"next","episode":2,"chapter":10,"ordinal":1}}
    ledger.reserve("old","old-task",12)
    ledger.mark("old","old-task","entered")
    assert ledger.pending_before(catalog,"next")==("old","old-task")
    ledger.mark("old","old-task","victory")
    assert ledger.pending_before(catalog,"next")==("old","old-task")
    ledger.mark("old","old-task","returned")
    assert ledger.pending_before(catalog,"next") is None


def test_transient_windows_lock_retries_only_replace(tmp_path,monkeypatch):
    from pathlib import Path
    from driver_epic_seven import attempts
    ledger=AttemptLedger(tmp_path/'attempts.json');calls=[];sleeps=[]
    replace=Path.replace
    def locked(path,destination):
        calls.append(path.read_bytes())
        if len(calls)<3:raise PermissionError('sharing lock')
        return replace(path,destination)
    monkeypatch.setattr(Path,'replace',locked)
    monkeypatch.setattr(attempts.time,'sleep',sleeps.append)
    ledger.reserve('stage','one-input',8)
    assert len(calls)==3 and len(set(calls))==1 and sleeps==[.1,.2]
    assert len(ledger.read()['stages']['stage'])==1


def test_persistent_write_lock_fails_finitely_preserving_previous_ledger(tmp_path,monkeypatch):
    from pathlib import Path
    from driver_epic_seven import attempts
    ledger=AttemptLedger(tmp_path/'attempts.json');ledger.reserve('stage','one-input',8)
    original=ledger.path.read_bytes();calls=[];sleeps=[]
    def locked(path,destination):
        calls.append(destination)
        raise PermissionError('persistent lock')
    monkeypatch.setattr(Path,'replace',locked)
    monkeypatch.setattr(attempts.time,'sleep',sleeps.append)
    with pytest.raises(PermissionError,match='persistent lock'):
        ledger.mark('stage','one-input','sent')
    assert len(calls)==4 and len(sleeps)==3
    assert ledger.path.read_bytes()==original
    assert ledger.path.with_suffix('.tmp').exists()
