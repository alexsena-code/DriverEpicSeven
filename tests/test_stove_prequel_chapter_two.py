"""Chapter 2's current wrapped title remains text, not stage selection or access."""
from copy import deepcopy
import json
import pytest
from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree,operation_view

RUN=ROOT/'var/runs/20261027T024311Z_f1c0e142'


@pytest.mark.fixtures
def test_wrapped_chapter_two_header_and_rows_are_read_without_selection():
    p=RUN/'agent_000053.json'
    if not p.exists():pytest.skip('Private chapter2 evidence unavailable.')
    d=json.loads(p.read_text(encoding='utf-8'))['result'];original=deepcopy(d)
    tree=build_tree(d);v=operation_view({'ui_tree':tree});c=v['items'][0]
    assert v['view']=='prequel_story_map' and c['chapter_number']==2
    assert c['chapter_label']=='Chapter 2. The Belief That We > Can Protect'
    assert c['chapter_star_counter_label']=='0/15'
    for key in ('selected_stage_id','selected_row_ordinal','earned_stars','current_entry_cost','completed'):
        assert c[key] is None
    rows=[i for i in v['items'] if i['semantic_id']=='stage_row']
    assert [r['ordinal'] for r in rows]==[1,2,3,4]
    assert rows[0]['title']=='Finding the Covenant'
    assert all(r['stage_id'] is None and r['selected'] is None and r['locked'] is None for r in rows)
    field=tree['nodes']['operation:prequel_story_map/context']['fields']['chapter_label']
    assert len([s for s in field['sources'] if s['kind']=='ocr'])==2
    assert d==original
    d['text'].append(deepcopy(next(r for r in d['text'] if r['text'].startswith('Chapter 2.'))))
    assert operation_view({'ui_tree':build_tree(d)})=={}


@pytest.mark.fixtures
def test_chapter_label_behind_overlays_does_not_expose_map():
    for n in (48,51,63):
        p=RUN/f'agent_{n:06}.json'
        if not p.exists():pytest.skip('Private overlay evidence unavailable.')
        d=json.loads(p.read_text(encoding='utf-8'))['result']
        assert operation_view({'ui_tree':build_tree(d)}).get('view') not in ('prequel_story_map','prequel_ready_map')
