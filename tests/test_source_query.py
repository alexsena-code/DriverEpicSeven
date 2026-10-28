"""Offline source lookup: routing, partial evidence, provenance and read-only access."""

import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('source_query', ROOT / 'tools/query_sources.py')
query = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(query)


def test_spirit_altar_routes_its_own_layout_instead_of_shadow_module(tmp_path):
    index=query.SourceIndex(tmp_path/'absent')
    result=query.search(ROOT,index,'altar espiritual',None,1)
    assert result['routes'][0]['id']=='spirit_altar'
    sources={s['source'] for s in result['routes'][0]['sources']}
    assert {'wnd/dungeon.csb','wnd/formation.csb','wnd/result_base.csb','db/level_battlemenu_genie.db'} <= sources
    assert 'wnd/dungeon_home.csb' not in sources


@pytest.fixture
def extracted(tmp_path):
    (tmp_path / 'interpreted').mkdir()
    db = sqlite3.connect(tmp_path / 'audit.sqlite')
    db.execute('CREATE TABLE files (source TEXT PRIMARY KEY,size INTEGER,sha256 TEXT,'
               'extraction_status TEXT,interpretation_status TEXT,details TEXT)')
    sources = {
        'wnd/formation.csb': {
            'source_sha256': 'formation-hash',
            'scope': 'Static declarations only.',
            'limitations': ['Runtime bindings are unknown.'],
            'nodes': [
                {'path': '/Layer/selected_btn/btn_remove', 'class': 'Button',
                 'class_options_supported': True, 'declared_visible': True,
                 'declared_alpha': 0, 'declared_callback': {'name': '', 'type': ''}},
                {'path': '/Layer/custom', 'class': 'UnknownWidget', 'class_options_supported': False},
            ],
        },
        'db/example.db': {
            'source': 'db/example.db', 'scope': 'Decoded cells, not full semantic interpretation.',
            'columns': ['id', 'name'],
            'rows': [{'id': 'logical-a', 'name': 'Candidate A'}, {'id': 'logical-b', 'name': 'Candidate B'}],
            'row_keys': ['physical-7', 'physical-9'], 'opaque_rows': [{'offset': 40}],
            'opaque_control_members': [{'offset': 10}], 'complete_string_cells': False,
        },
    }
    for number, (name, data) in enumerate(sources.items()):
        filename = f'{number}.json'
        (tmp_path / 'interpreted' / filename).write_text(json.dumps(data), encoding='utf-8')
        db.execute('INSERT INTO files VALUES (?,?,?,?,?,?)',
                   (name, 30, data.get('source_sha256', 'db-hash'), 'verified', 'partial',
                    json.dumps({'normalized_file': filename, 'depth': 'partial'})))
    db.execute('CREATE TABLE asset_refs (source TEXT,kind TEXT,owner TEXT,reference TEXT,target TEXT,resolution TEXT)')
    db.execute('INSERT INTO asset_refs VALUES (?,?,?,?,?,?)',
               ('wnd/formation.csb', 'csb_resource', '7/normal/path', 'img/change.png', 'img/change.png', 'literal_pack_path'))
    db.execute('CREATE TABLE text_refs (source TEXT,row_index INTEGER,column_name TEXT,text_id TEXT)')
    db.execute('INSERT INTO text_refs VALUES (?,?,?,?)', ('db/example.db', 0, 'name', 'name_a'))
    db.commit()
    db.close()
    return tmp_path


def test_operation_alias_finds_full_composition_and_allows_missing_private_data(tmp_path):
    index = query.SourceIndex(tmp_path / 'not-extracted')
    result = query.search(ROOT, index, 'trocar personagem', None, 1)
    assert result['ok'] and result['routes'][0]['id'] == 'formation'
    paths = {source['source'] for source in result['routes'][0]['sources']}
    assert {'wnd/formation.csb', 'wnd/unit_list.csb', 'wnd/battle_ready.csb'} <= paths
    assert all(source['inventory_known'] is None for source in result['routes'][0]['sources'])
    assert not result['private_index_available']
    assert not (tmp_path / 'not-extracted').exists()


def test_family_routing_covers_existing_catalog_and_keeps_specialized_sources(extracted):
    index = query.SourceIndex(extracted)
    try:
        families = [entry for entry in query.routes(ROOT) if entry['kind'] == 'family']
        assert len(families) == 33 and len({entry['id'] for entry in families}) == 33
        result = query.search(ROOT, index, None, 'enhancement', 1)
        paths = {source['source'] for source in result['routes'][0]['sources']}
        assert {'wnd/unit_item_upgrade.csb', 'wnd/item_detail.csb', 'db/equip_item.db',
                'db/item_material.db', 'wnd/item_select_slidebar_popup.csb'} <= paths
        assert any('reforja' in gap for gap in result['routes'][0]['gaps'])
        assert result['routes'][0]['runtime_enabled'] is False
    finally:
        index.close()


def test_player_variants_and_reforging_are_routed_without_inventing_costs(tmp_path):
    index = query.SourceIndex(tmp_path / 'missing')
    try:
        for topic in ['formation', 'hero_growth', 'hero_skills', 'three_stars']:
            result = query.search(ROOT, index, topic, None, 20)
            route = next(r for r in result['routes'] if r['kind'] == 'topic' and r['id'] == topic)
            paths = {s['source'] for s in route['sources']}
            assert {'db/character.db', 'db/character_player_grade2.db',
                    'db/character_player_grade3.db'} <= paths
        result = query.search(ROOT, index, 'upar equipamento', None, 1)
        paths = {s['source'] for s in result['routes'][0]['sources']}
        assert 'db/item_equip_upgrade.db' not in paths
        result = query.search(ROOT, index, 'reforjar', None, 1)
        assert result['routes'][0]['id'] == 'reforging'
        assert 'db/item_equip_upgrade.db' in {s['source'] for s in result['routes'][0]['sources']}
        skills = query.search(ROOT, index, None, 'hero_skills', 1)['routes'][0]
        assert 'db/skill_player_grade3.db' in {s['source'] for s in skills['sources']}
        assert any('custos iguais' in gap for gap in skills['gaps'])
    finally:
        index.close()


def test_csb_keeps_declared_fields_unknown_classes_and_no_runtime_assertion(extracted):
    index = query.SourceIndex(extracted)
    try:
        result = index.inspect('wnd/formation.csb', 'btn_remove', 5)
        assert result['file']['interpretation_status'] == 'partial'
        assert result['content']['unsupported_class_nodes'] == 1
        assert result['content']['limitations'] == ['Runtime bindings are unknown.']
        candidate = result['candidates'][0]
        assert candidate['declared_visible'] and candidate['declared_alpha'] == 0
        assert candidate['declared_callback']['name'] == ''
        assert 'enabled' not in candidate and 'selected' not in candidate
    finally:
        index.close()


def test_db_keeps_physical_key_partial_rows_and_truncated_candidates(extracted):
    index = query.SourceIndex(extracted)
    try:
        result = index.inspect('db/example.db', 'Candidate', 1)
        assert result['total_candidates'] == 2 and result['truncated']
        assert result['content']['opaque_rows'] == 1
        assert result['content']['complete_string_cells'] is False
        assert result['candidates'][0]['container_key'] == 'physical-7'
        assert result['candidates'][0]['row']['id'] == 'logical-a'
        assert not index.inspect('db/example.db', None, 5)['candidates']
    finally:
        index.close()


def test_derived_path_escape_is_rejected(extracted):
    db = sqlite3.connect(extracted / 'audit.sqlite')
    db.execute('UPDATE files SET details=? WHERE source=?',
               (json.dumps({'normalized_file': '../../outside.json'}), 'wnd/formation.csb'))
    db.commit()
    db.close()
    index = query.SourceIndex(extracted)
    try:
        with pytest.raises(ValueError, match='escapes'):
            index.inspect('wnd/formation.csb', 'remove', 5)
    finally:
        index.close()


@pytest.mark.parametrize('key,value', [('source', 'db/different.db'), ('source_sha256', 'wrong-hash')])
def test_derived_identity_mismatch_is_rejected(extracted, key, value):
    path = extracted / 'interpreted/0.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    data[key] = value
    path.write_text(json.dumps(data), encoding='utf-8')
    index = query.SourceIndex(extracted)
    try:
        with pytest.raises(ValueError, match='differs from inventory'):
            index.inspect('wnd/formation.csb', 'remove', 5)
    finally:
        index.close()


def test_references_are_bounded_provenance_and_database_is_readonly(extracted):
    path = extracted / 'audit.sqlite'
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    index = query.SourceIndex(extracted)
    try:
        assets = index.references('asset', 'img/change.png', 1)
        assert assets['candidates'][0]['owner'] == '7/normal/path'
        assert index.references('text', 'name_a', 1)['candidates'][0]['row_index'] == 0
        with pytest.raises(sqlite3.OperationalError, match='readonly'):
            index.db.execute('DELETE FROM files')
    finally:
        index.close()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_missing_reference_index_is_reported_without_building_it(extracted):
    db = sqlite3.connect(extracted / 'audit.sqlite')
    db.execute('DROP TABLE asset_refs')
    db.commit()
    db.close()
    index = query.SourceIndex(extracted)
    try:
        assert index.references('asset', 'img/change.png', 1)['reason'] == 'reference_index_missing'
        assert not index.inspect('wnd/not-present.csb', 'remove', 5)['ok']
    finally:
        index.close()


def test_cli_reports_malformed_derived_json_as_error(extracted, capsys):
    (extracted / 'interpreted/0.json').write_text('{broken', encoding='utf-8')
    assert query.main(['--root', str(extracted), '--source', 'wnd/formation.csb', '--find', 'remove']) == 1
    result = json.loads(capsys.readouterr().out)
    assert result['ok'] is False and result['error']
