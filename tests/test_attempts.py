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
    assert ledger.pending_before(catalog,"next") is None
