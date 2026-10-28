"""Offline invariants: path confinement, bounded decompression and table keys."""
import importlib.util
import hashlib
from pathlib import Path
import struct
import sys
import zlib
from types import SimpleNamespace

import pytest

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
try:
    spec = importlib.util.spec_from_file_location('pack_auditor', TOOLS / 'audit_pack.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    from inspect_db_table import inspect_table
finally:
    sys.path.pop(0)


def wrapper(raw, encoded):
    return struct.pack('<II', len(raw), len(encoded)) + encoded


def table(columns, row_key, row_value):
    def member(key, value):
        return struct.pack('<IBBI', 15 + len(key) + len(value), 2, len(key), len(value)) + b'\0' * 5 + key + value
    head = bytearray(43)
    head[:10] = b'PLPcK\x01\x26\0\0\0'
    records = [member(b'\tcols', struct.pack('<I', len(columns))),
               member(b'\trows', struct.pack('<I', 1))]
    records += [member(b'\t' + str(i).encode(), c.encode()) for i,c in enumerate(columns)]
    records += [member(row_key.encode(), row_value)]
    return bytes(head) + b''.join(records) + b'PLPcK\x01' + b'\0' * 32


@pytest.mark.parametrize('name', ['../escape', '/absolute', 'C:/outside', 'CON.txt', 'nested/../escape'])
def test_invalid_platform_paths_are_mapped_inside_destination(tmp_path, name):
    path, rel = module.safe_destination(name, tmp_path, set())
    assert path.is_relative_to(tmp_path.resolve())
    assert rel.startswith('__mapped__/')


def test_case_collisions_keep_distinct_outputs(tmp_path):
    used = set()
    first, _ = module.safe_destination('img/Asset.png', tmp_path, used)
    second, rel = module.safe_destination('img/asset.png', tmp_path, used)
    assert str(first).casefold() != str(second).casefold()
    assert rel.startswith('__mapped__/')


def test_zlib_wrapper_checks_size_and_stream_end():
    raw = b'{"example":1}'
    encoded = zlib.compress(raw)
    assert module.unpack_blob(wrapper(raw, encoded), 'zlib') == raw
    with pytest.raises(ValueError):
        module.unpack_blob(wrapper(raw[:-1], encoded), 'zlib')
    with pytest.raises(ValueError):
        module.unpack_blob(wrapper(raw, encoded + b'junk'), 'zlib')


def test_compression_does_not_accept_unbounded_allocations():
    with pytest.raises(ValueError):
        module.unpack_blob(struct.pack('<II', 0xffffffff, 1) + b'x', 'lz4')


def test_lz4_wrapper_matches_declared_output():
    lz4 = pytest.importorskip('lz4.block')
    raw = b'bounded-data' * 20
    encoded = lz4.compress(raw, store_size=False)
    assert module.unpack_blob(wrapper(raw, encoded), 'lz4') == raw


def test_table_row_key_can_differ_from_semantic_id():
    result = inspect_table(table(['set_id', 'id'], '24', b'24\0skill_id\0'), 'synthetic')
    assert result['rows'] == [{'set_id': '24', 'id': 'skill_id'}]
    assert result['row_keys'] == ['24']
    assert result['complete_string_cells']
    assert result['validation']['row_keys_match_id'] is False


def test_table_without_id_column_is_valid():
    result = inspect_table(table(['season_id', 'heroes'], 'season1', b'season1\0a;b\0'), 'synthetic')
    assert result['complete_string_cells']
    assert result['validation']['row_keys_match_id'] is None


def test_binary_row_remains_explicit_and_addressable():
    raw = table(['id'], 'item', b'\xff\0')
    result = inspect_table(raw, 'synthetic')
    assert not result['complete_string_cells'] and not result['rows']
    opaque = result['opaque_rows'][0]
    assert raw[opaque['offset']:opaque['offset'] + opaque['bytes']] == b'\xff\0'


def test_truncated_table_does_not_claim_complete_cells():
    raw = table(['id'], 'item', b'item\0')
    with pytest.raises(ValueError):
        inspect_table(raw[:-1], 'synthetic')


def test_alternate_index_header_and_keyless_blocks_are_preserved():
    raw = bytearray(table(['id'], 'item', b'item\0'))
    struct.pack_into('<I', raw, 21, 1)  # The valid count remains at header offset 17.
    block = struct.pack('<IBBI', 20, 1, 0, 0) + b'\0' * 10
    raw = bytes(raw[:-38]) + block + bytes(raw[-38:])
    result = inspect_table(raw, 'alternate-header')
    assert result['rows'] == [{'id': 'item'}]
    assert result['index_count_header_offsets'] == [17]
    assert result['non_entry_blocks'][0]['bytes'] == 20


def test_opaque_real_table_is_not_promoted_to_an_empty_known_table():
    source = 'db/pvp_npcbattle.db'
    name = hashlib.sha256(source.encode()).hexdigest() + '.table.decoded.bin'
    path = TOOLS.parent / 'assets/local/extraction-audit/db' / name
    if not path.exists():
        pytest.skip('Private partially decoded table fixture is not installed.')
    result = inspect_table(path.read_bytes(), source)
    assert result['row_count'] == 10 and result['rows'] == []
    assert len(result['opaque_rows']) == 10
    assert not result['complete_string_cells']
    assert result['opaque_control_members']


def test_sct2_compression_and_metadata_remain_separate_from_pixel_semantics(tmp_path):
    pytest.importorskip('lz4.block')
    source = 'effect/skeff_meilin_sk3_hookup.sct'
    path = TOOLS.parent / 'assets/local/full-pack/files' / source
    if not path.exists():
        pytest.skip('Private full extraction fixture is not installed.')
    result = module.interpret(source, path, path.read_bytes(), None, tmp_path)
    assert result['status'] == 'partial'
    assert result['candidate_dimensions'] == (176, 176)
    assert result['decoded_bytes'] == 30976
    assert next(m for m in result['metadata'] if m['key'] == 'proc')['uint32_candidate'] == 34
    assert (tmp_path / result['decoded_file']).stat().st_size == 30976


def test_sct2_header_cannot_point_outside_the_file(tmp_path):
    raw = bytearray(48)
    raw[:4] = b'SCT2'
    struct.pack_into('<I', raw, 4, len(raw))
    struct.pack_into('<I', raw, 12, 0xffffffff)
    result = module.interpret('synthetic.sct', tmp_path, bytes(raw), None, tmp_path)
    assert result['status'] == 'error'
    assert 'bounds' in result['error']
    assert not list(tmp_path.iterdir())


def test_lenient_json_only_changes_trailing_commas_outside_strings():
    result, normalization = module.parse_json('{"s":",]", "url":"http://example", "a":[1,],}')
    assert result == {'s': ',]', 'url': 'http://example', 'a': [1]}
    assert normalization == 'trailing_commas_removed_outside_strings'
    with pytest.raises(ValueError):
        module.parse_json('{"a": undefined}')


def test_model_metadata_reads_tensor_indices_without_inference():
    path = TOOLS.parent / 'assets/local/full-pack/files/tflite/equip_cleanup/enh0.tflite'
    if not path.exists():
        pytest.skip('Private full extraction fixture is not installed.')
    result = module.model_metadata(path.read_bytes())
    assert result['model_version'] == 3 and len(result['subgraphs']) == 1
    graph = result['subgraphs'][0]
    names = {graph['tensors'][i]['name'] for i in graph['inputs']}
    assert 'serving_default_equipment_grade:0' in names
    assert len(graph['outputs']) == 2


def test_sca_header_is_useful_without_claiming_region_geometry(tmp_path):
    source = 'bg/e7wc2026_group.sca'
    path = TOOLS.parent / 'assets/local/full-pack/files' / source
    if not path.exists():
        pytest.skip('Private full extraction fixture is not installed.')
    result = module.interpret(source, path, path.read_bytes(), None, tmp_path)
    assert result['status'] == 'partial'
    assert result['texture_page'] == 'e7wc2026_group.sct'
    assert result['declared_dimensions'] == [2002, 1014]
    assert result['declared_regions'] == 71
    assert result['region_payload_bytes'] > 0


def fake_reader(tmp_path, monkeypatch):
    path = tmp_path / 'source.pack'
    payload = b'hello'
    path.write_bytes(bytes(v ^ 107 for v in payload))
    reader = SimpleNamespace(PACK=path, OUTER_KEY=b'k',
                             INDEX={'sample.txt': {'path': 'sample.txt', 'data_offset': 0, 'size': 5}})
    monkeypatch.setattr(module.importlib, 'import_module', lambda _: reader)
    return path


def test_resume_does_not_accept_modified_outputs(tmp_path, monkeypatch):
    path = fake_reader(tmp_path, monkeypatch)
    before = path.read_bytes()
    destination = tmp_path / 'out'
    module.run(tmp_path, destination)
    (destination / 'files/sample.txt').write_bytes(b'other')
    with pytest.raises(ValueError, match='Resume evidence changed'):
        module.run(tmp_path, destination)
    assert path.read_bytes() == before


def test_existing_extraction_cannot_be_reused_for_a_different_pack(tmp_path, monkeypatch):
    path = fake_reader(tmp_path, monkeypatch)
    destination = tmp_path / 'out'
    module.run(tmp_path, destination)
    path.write_bytes(b'other')
    with pytest.raises(ValueError, match='different source pack'):
        module.run(tmp_path, destination)
