"""Inventory, private extraction and bounded structural interpretation of a pack.

Uses the existing local read-only decoder; never copies its keys into the repo.
All outputs are private. Parsing data never executes it or connects to the game.
"""
import argparse
from collections import Counter
import hashlib
import importlib
import json
import os
from pathlib import Path, PurePosixPath
import sqlite3
import struct
import sys
import time
import xml.etree.ElementTree as ET
import zlib

import numpy as np
from PIL import Image, ImageFont

from inspect_csb_layout import CSB
from inspect_db_table import inspect_table


def digest_file(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def safe_destination(name, root, used):
    parts = PurePosixPath(name).parts
    reserved = {'CON', 'PRN', 'AUX', 'NUL'} | {f'{s}{i}' for s in ('COM', 'LPT') for i in range(1, 10)}
    safe = bool(parts) and not name.startswith('/') and all(
        p not in ('.', '..') and not any(c in p for c in ':\\<>"|?*')
        and not p.endswith((' ', '.')) and p.split('.')[0].upper() not in reserved
        for p in parts)
    rel = name if safe and name.casefold() not in used else '__mapped__/' + hashlib.sha256(name.encode()).hexdigest()
    used.add(rel.casefold())
    path = (root / rel).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Destination outside extraction root')
    return path, rel


def long_path(path):
    return Path('\\\\?\\' + str(path.resolve())) if os.name == 'nt' else path


def xml_node(node):
    return {'tag': node.tag, 'attributes': node.attrib,
            'text': node.text.strip() if node.text and node.text.strip() else None,
            'children': [xml_node(c) for c in node]}


def atlas_data(text):
    if not text.strip():
        return {'pages': []}
    pages, page, region = [], None, None
    blank = True
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            blank = True
            continue
        if ':' in line:
            key, value = line.split(':', 1)
            target = region if region is not None else page
            if target is None:
                raise ValueError('Atlas property without owner')
            target['properties'][key] = value.strip()
        elif page is None or blank:
            page = {'name': line, 'properties': {}, 'regions': []}
            pages.append(page)
            region = None
        else:
            region = {'name': line, 'properties': {}}
            page['regions'].append(region)
        blank = False
    if not pages:
        raise ValueError('Atlas without pages')
    return {'pages': pages}


def parse_json(text):
    try:
        return json.loads(text), None
    except json.JSONDecodeError:
        cleaned, quoted, escaped = [], False, False
        for index, char in enumerate(text):
            if quoted:
                cleaned.append(char)
                if escaped:
                    escaped = False
                elif char == '\\':
                    escaped = True
                elif char == '"':
                    quoted = False
            else:
                if char == '"':
                    quoted = True
                if char == ',' and text[index + 1:].lstrip().startswith((']', '}')):
                    continue
                cleaned.append(char)
        return json.loads(''.join(cleaned)), 'trailing_commas_removed_outside_strings'


def unpack_blob(raw, codec):
    if len(raw) < 8:
        raise ValueError('Missing compressed wrapper')
    size, compressed = struct.unpack_from('<II', raw)
    if not 0 < size <= 64 * 1024 * 1024 or compressed != len(raw) - 8:
        raise ValueError('Compressed wrapper size mismatch')
    if codec == 'lz4':
        import lz4.block
        out = lz4.block.decompress(raw[8:], uncompressed_size=size)
    else:
        dec = zlib.decompressobj()
        out = dec.decompress(raw[8:], size + 1)
        if not dec.eof or dec.unused_data or dec.unconsumed_tail:
            raise ValueError('Incomplete or oversized zlib stream')
    if len(out) != size:
        raise ValueError('Decoded size differs from declared size')
    return out


def model_metadata(raw):
    if raw[4:8] != b'TFL3':
        raise ValueError('Unknown model identifier')
    fb = CSB(raw)
    root = fb.read('<I', 0)
    def ints(table, slot):
        pos = fb.pointer(table, slot)
        if pos is None:
            return []
        count = fb.read('<I', pos)
        if count > 10000 or pos + 4 + count * 4 > len(raw):
            raise ValueError('Model integer vector exceeds bounds')
        return [fb.read('<i', pos + 4 + i * 4) for i in range(count)]
    graphs = []
    for graph in fb.vector(root, 8):
        tensors = [{'name': fb.string(t, 10), 'shape': ints(t, 4),
                    'type_code': fb.value(t, 6, '<b', 0), 'buffer_index': fb.value(t, 8, '<I', 0)}
                   for t in fb.vector(graph, 4)]
        inputs, outputs = ints(graph, 6), ints(graph, 8)
        if any(i < 0 or i >= len(tensors) for i in inputs + outputs):
            raise ValueError('Model input/output tensor outside table')
        graphs.append({'name': fb.string(graph, 12), 'tensors': tensors, 'inputs': inputs,
                       'outputs': outputs, 'operator_count': len(fb.vector(graph, 10))})
    return {'model_version': fb.value(root, 4, '<I', 0), 'description': fb.string(root, 10),
            'buffer_count': len(fb.vector(root, 12)), 'subgraphs': graphs,
            'schema_reference': 'https://github.com/tensorflow/tensorflow/blob/v2.18.0/tensorflow/compiler/mlir/lite/schema/schema.fbs'}


def interpret(source, path, raw, reader, outputs):
    ext = PurePosixPath(source).suffix.lower()
    result = {'format': ext or '(none)', 'status': 'uninterpreted', 'depth': 'signature_only',
              'signature_hex': raw[:16].hex(), 'limitations': []}
    normalized = None
    try:
        if len(raw) == 4 and source.startswith(('@ver', '#partion.')):
            result.update(status='partial', depth='declared_revision_uint32', value=struct.unpack('<I', raw)[0])
            result['limitations'] = ['Static revision scalar; not current account/server state.']
        elif ext == '.ttf':
            family, style = ImageFont.truetype(str(path), size=12).getname()
            result.update(status='partial', depth='font_identity', family=family, style=style)
            result['limitations'] = ['Font identity read; outlines and character coverage not exhaustively interpreted.']
        elif ext == '.tflite':
            normalized = model_metadata(raw)
            result.update(status='partial', depth='model_tensor_metadata',
                          model_version=normalized['model_version'], subgraphs=len(normalized['subgraphs']))
            result['limitations'] = ['Tensor metadata read; weights/operators not evaluated; no inference executed.']
        elif ext == '.sca':
            if raw[:4] != b'SCA\x00' or len(raw) < 16:
                raise ValueError('Unknown SCA header')
            header = struct.unpack_from('<H', raw, 4)[0]
            if not 16 <= header <= len(raw):
                raise ValueError('Invalid SCA header length')
            end = raw.index(b'\0', 6, header)
            page = raw[6:end].decode('utf-8')
            start, end = end + 1, raw.index(b'\0', end + 1, header)
            pixel_format = raw[start:end].decode('ascii')
            if end + 11 != header:
                raise ValueError('Unexpected SCA header fields')
            width, height, regions = struct.unpack_from('<IIH', raw, end + 1)
            result.update(status='partial', depth='sca_header', texture_page=page, pixel_format=pixel_format,
                          declared_dimensions=[width, height], declared_regions=regions,
                          region_payload_bytes=len(raw) - header)
            result['limitations'] = ['Header corroborated by samples; region geometry/animation payload unparsed.']
        elif ext in ('.scsb', '.scsp'):
            codec = 'zlib' if ext == '.scsb' else 'lz4'
            decoded = unpack_blob(raw, codec)
            decoded_name = hashlib.sha256(source.encode()).hexdigest() + ('.decoded.json' if ext == '.scsb' else '.decoded.bin')
            long_path(outputs / decoded_name).write_bytes(decoded)
            result.update(status='partial', depth='decompressed_binary', codec=codec,
                          decoded_bytes=len(decoded), decoded_sha256=hashlib.sha256(decoded).hexdigest(),
                          decoded_file=decoded_name, decoded_signature_hex=decoded[:16].hex())
            result['limitations'] = ['Compression decoded; internal binary semantics remain unparsed.']
            if ext == '.scsb':
                data = json.loads(decoded.decode('utf-8-sig'))
                result.update(status='structured', depth='decompressed_json_values',
                              root_type=type(data).__name__, top_level_keys=list(data)[:40] if isinstance(data, dict) else None)
                result['limitations'] = ['JSON values parsed; scenario execution and runtime state not inferred.']
        elif ext == '.sct':
            if raw.startswith((b'SCT\x00', b'SCT\x01')):
                width, height = struct.unpack_from('<HH', raw, 5)
                decoded = unpack_blob(raw[9:], 'lz4')
                result.update(status='partial', depth='sct_decompressed_texture_v' + str(raw[3]), width=width, height=height,
                              format_code=raw[4], decoded_bytes=len(decoded),
                              decoded_sha256=hashlib.sha256(decoded).hexdigest())
                name = hashlib.sha256(source.encode()).hexdigest() + '.texture.bin'
                long_path(outputs / name).write_bytes(decoded)
                result['decoded_file'] = name
                result['limitations'] = ['Pixel format/alpha mapping needs independent confirmation.']
            elif raw.startswith(b'SCT2') and len(raw) >= 28:
                header = struct.unpack_from('<I', raw, 12)[0]
                if not 36 <= header <= len(raw) - 8 or struct.unpack_from('<I', raw, 4)[0] != len(raw):
                    raise ValueError('Invalid SCT2 container bounds')
                metadata = []
                cursor = 36
                while cursor < header:
                    if cursor + 2 > header:
                        raise ValueError('Truncated SCT2 metadata key')
                    length = struct.unpack_from('<H', raw, cursor)[0]
                    cursor += 2
                    if cursor + length + 2 > header:
                        raise ValueError('SCT2 metadata key outside header')
                    key = raw[cursor:cursor + length].decode('ascii')
                    cursor += length
                    length = struct.unpack_from('<H', raw, cursor)[0]
                    cursor += 2
                    if cursor + length > header:
                        raise ValueError('SCT2 metadata value outside header')
                    value = raw[cursor:cursor + length]
                    cursor += length
                    metadata.append({'key': key, 'value_hex': value.hex(),
                                     'uint32_candidate': struct.unpack('<I', value)[0] if length == 4 else None})
                storage_flags = struct.unpack_from('<I', raw, 32)[0]
                decoded = unpack_blob(raw[header:], 'lz4') if storage_flags & 0x80000000 else raw[header:]
                name = hashlib.sha256(source.encode()).hexdigest() + '.texture.bin'
                long_path(outputs / name).write_bytes(decoded)
                result.update(status='partial', depth='sct2_header',
                              declared_container_bytes=struct.unpack_from('<I', raw, 4)[0],
                              header_bytes=header, metadata=metadata,
                              storage_flags=storage_flags,
                              payload_codec='lz4' if storage_flags & 0x80000000 else 'none',
                              candidate_dimensions=struct.unpack_from('<HH', raw, 24),
                              decoded_bytes=len(decoded), decoded_sha256=hashlib.sha256(decoded).hexdigest(), decoded_file=name)
                result['limitations'] = ['Container and LZ4 decoded; texture processor/pixel format mapping still needs confirmation.']
            else:
                result['limitations'] = ['Unrecognized SCT version.']
        elif ext in ('.png', '.jpg', '.jpeg', '.webp'):
            with Image.open(path) as im:
                result.update(format=im.format, width=im.width, height=im.height, mode=im.mode)
                im.verify()
            result.update(status='structured', depth='image_container_verified')
            result['limitations'] = ['No visual recognition or semantic identity inferred.']
        elif ext == '.db':
            if raw.startswith(b'YUNADBSET\t'):
                data = {'source': source, 'lines': raw.decode('utf-8-sig').splitlines()}
                result.update(status='partial', depth='filter_definition_text')
                result['limitations'] = ['Filter declarations decoded; not executed or expanded into virtual rows.']
            else:
                decoded, _ = reader.decode_inner(raw)
                data = inspect_table(decoded, source)
                result.update(status='structured' if data['complete_string_cells'] and not data['non_entry_blocks'] else 'partial',
                              depth='validated_table_cells', rows=data['row_count'], columns=data['columns'],
                              opaque_rows=len(data['opaque_rows']), validation=data['validation'])
                result['limitations'] = ['Column values decoded; application semantics not exhaustively resolved.']
                if data['opaque_rows'] or data['non_entry_blocks']:
                    blob_name = hashlib.sha256(source.encode()).hexdigest() + '.table.decoded.bin'
                    long_path(outputs / blob_name).write_bytes(decoded)
                    result['decoded_file'] = blob_name
                    result['limitations'].append('Opaque rows/keyless blocks retained by byte offset/hash in the decoded blob.')
            normalized = data
        elif ext == '.csb':
            data = CSB(raw).nodes()
            unsupported = dict(Counter(n['class'] for n in data['nodes'] if not n['class_options_supported']))
            result.update(status='partial', depth='declared_layout_fields', nodes=len(data['nodes']),
                          classes=dict(Counter(n['class'] for n in data['nodes'])),
                          unsupported_classes=unsupported, timelines=len(data['action']['timelines']),
                          animations=data['animations'])
            result['limitations'] = data['limitations']
            normalized = data
        elif ext == '.atlas':
            data = atlas_data(raw.decode('utf-8-sig'))
            result.update(status='structured', depth='atlas_pages_regions_and_properties',
                          pages=len(data['pages']), regions=sum(len(p['regions']) for p in data['pages']))
            result['limitations'] = ['Texture composition, transforms and visibility not evaluated.']
            normalized = data
        else:
            stripped = raw.lstrip(b'\xef\xbb\xbf \r\n\t')
            if stripped.startswith((b'{', b'[')):
                data, normalization = parse_json(raw.decode('utf-8-sig'))
                result.update(status='structured', depth='json_values',
                              root_type=type(data).__name__, root_count=len(data) if isinstance(data, (dict, list)) else None,
                              top_level_keys=list(data)[:40] if isinstance(data, dict) else None)
                result['limitations'] = ['Syntax and values parsed; event semantics not exhaustively resolved.']
                if normalization:
                    result['normalization'] = normalization
                    normalized = data
                # Original bytes already preserve all JSON values without another copy.
            elif stripped.startswith((b'<?xml', b'<plist', b'<root')):
                data = ET.fromstring(raw)
                normalized = xml_node(data)
                result.update(status='structured', depth='xml_elements_attributes_and_text',
                              root_tag=data.tag, elements=sum(1 for _ in data.iter()))
                result['limitations'] = ['No external DTD loaded; effect/event semantics not evaluated.']
            else:
                try:
                    text = raw.decode('utf-8-sig')
                except UnicodeDecodeError:
                    text = None
                if text is not None and '\x00' not in text and all(ord(c) >= 32 or c in '\r\n\t' for c in text):
                    result.update(status='partial', depth='utf8_text_lines', lines=len(text.splitlines()))
                    result['limitations'] = ['Text decoded; format-specific grammar not fully interpreted.']
                else:
                    result['limitations'] = ['Binary format requires a compatible decoder.']
        if normalized is not None:
            target = long_path(outputs / (hashlib.sha256(source.encode()).hexdigest() + '.json'))
            target.write_text(json.dumps(normalized, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
            result['normalized_file'] = target.name
    except Exception as exc:
        result.update(status='error', error=type(exc).__name__ + ': ' + str(exc), depth='failed')
    return result


def run(reader_dir, destination):
    sys.path.insert(0, str(reader_dir.resolve()))
    reader = importlib.import_module('e7_db_reader')
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    files, outputs = destination / 'files', destination / 'interpreted'
    files.mkdir(exist_ok=True)
    outputs.mkdir(exist_ok=True)
    db = sqlite3.connect(destination / 'audit.sqlite')
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS files (source TEXT PRIMARY KEY, extension TEXT, offset INTEGER, size INTEGER, destination TEXT, sha256 TEXT, extraction_status TEXT, interpretation_status TEXT, details TEXT)')
    entries = sorted(reader.INDEX.items(), key=lambda pair: pair[1]['data_offset'])
    (destination / 'inventory.json').write_text(json.dumps(list(reader.INDEX.values()), ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    pack_size = reader.PACK.stat().st_size
    for name, entry in entries:
        if entry['path'] != name or not 0 <= entry['size'] <= 64 * 1024 * 1024 or not 0 <= entry['data_offset'] <= pack_size - entry['size']:
            raise ValueError('Invalid inventory bounds: ' + name)
    print(json.dumps({'phase': 'hashing_original', 'entries': len(entries), 'bytes': pack_size}), flush=True)
    before_hash = digest_file(reader.PACK)
    identity_file = destination / 'identity.json'
    identity = {'pack_sha256': before_hash, 'pack_size': pack_size}
    if identity_file.exists() and json.loads(identity_file.read_text(encoding='utf-8')) != identity:
        db.close()
        raise ValueError('Destination belongs to a different source pack')
    identity_file.write_text(json.dumps(identity, indent=2) + '\n', encoding='utf-8')
    started = time.time()
    progress = destination / 'progress.json'
    used = set()
    extraction, parsing = Counter(), Counter()
    key = np.frombuffer(reader.OUTER_KEY, dtype=np.uint8)
    with reader.PACK.open('rb') as stream:
        for number, (source, entry) in enumerate(entries, 1):
            target, relative = safe_destination(source, files, used)
            old = db.execute('SELECT extraction_status,sha256,size,offset,destination FROM files WHERE source=?', (source,)).fetchone()
            if old and old[0] == 'verified':
                existing = long_path(files / old[4])
                if (old[2] != entry['size'] or old[3] != entry['data_offset'] or old[4] != relative
                        or not existing.is_file() or digest_file(existing) != old[1]):
                    db.close()
                    raise ValueError('Resume evidence changed: ' + source)
                continue
            sha = None
            details = {}
            status = 'error'
            try:
                stream.seek(entry['data_offset'])
                raw = stream.read(entry['size'])
                if len(raw) != entry['size']:
                    raise ValueError('Truncated source record')
                payload = np.frombuffer(raw, dtype=np.uint8).copy()
                payload ^= np.resize(np.roll(key, -(entry['data_offset'] % len(key))), entry['size'])
                payload = payload.tobytes()
                sha = hashlib.sha256(payload).hexdigest()
                target = long_path(target)
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    if digest_file(target) != sha:
                        raise ValueError('Existing output differs; refusing overwrite')
                else:
                    with target.open('xb') as out:
                        out.write(payload)
                if target.stat().st_size != entry['size'] or digest_file(target) != sha:
                    raise ValueError('Extraction readback integrity failed')
                status = 'verified'
                details = interpret(source, target, payload, reader, outputs)
            except Exception as exc:
                details = {'status': 'not_attempted', 'error': type(exc).__name__ + ': ' + str(exc)}
            extraction[status] += 1
            parsing[details['status']] += 1
            db.execute('INSERT OR REPLACE INTO files VALUES (?,?,?,?,?,?,?,?,?)',
                       (source, PurePosixPath(source).suffix.lower(), entry['data_offset'], entry['size'],
                        relative, sha, status, details['status'], json.dumps(details, ensure_ascii=False)))
            if number % 500 == 0 or number == len(entries):
                db.commit()
                report = {'phase': 'extracting_and_interpreting', 'processed': number, 'total': len(entries),
                          'extraction': dict(extraction), 'interpretation': dict(parsing),
                          'elapsed_seconds': round(time.time() - started, 2)}
                progress.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
                print(json.dumps(report), flush=True)
    db.commit()
    print(json.dumps({'phase': 'verifying_original_again'}), flush=True)
    after_hash = digest_file(reader.PACK)
    counts = db.execute('SELECT extraction_status, interpretation_status, COUNT(*), SUM(size) FROM files GROUP BY 1,2').fetchall()
    extraction_errors = sum(c for a,b,c,d in counts if a != 'verified')
    summary = {'status': ('original_changed' if before_hash != after_hash else 'completed_with_extraction_errors' if extraction_errors else 'completed'),
               'inventory_count': len(entries), 'pack_size': pack_size,
               'pack_sha256_before': before_hash, 'pack_sha256_after': after_hash,
               'original_unchanged': before_hash == after_hash,
               'payload_bytes': sum(e['size'] for _, e in entries),
               'results': [{'extraction': a, 'interpretation': b, 'files': c, 'bytes': d} for a,b,c,d in counts],
               'elapsed_seconds': round(time.time() - started, 2),
               'interpretation_scope': 'Structural parsing and declared fields only; no claim of complete application semantics.',
               'private_index': 'audit.sqlite'}
    (destination / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    progress.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary), flush=True)
    db.close()


def reinterpret(reader_dir, destination, repair_only=False, extensions=None):
    """Revisit improved decoders without changing extracted source bytes."""
    sys.path.insert(0, str(reader_dir.resolve()))
    reader = importlib.import_module('e7_db_reader')
    destination = destination.resolve()
    db = sqlite3.connect(destination / 'audit.sqlite')
    db.execute('CREATE TABLE IF NOT EXISTS interpretation_attempts (source TEXT, phase TEXT, status TEXT, details TEXT)')
    if not db.execute('SELECT 1 FROM interpretation_attempts LIMIT 1').fetchone():
        db.execute("INSERT INTO interpretation_attempts SELECT source,'before_final_expansion',interpretation_status,details FROM files")
        db.commit()
    condition = "interpretation_status IN ('error','uninterpreted')" if repair_only else "extension IN ('.db','.scsp','.scsb','.sct')"
    parameters = []
    if extensions:
        condition = 'extension IN (' + ','.join('?' for _ in extensions) + ')'
        parameters = extensions
    rows = db.execute("SELECT source,destination,sha256 FROM files WHERE extraction_status='verified' AND " + condition + ' ORDER BY source', parameters).fetchall()
    fingerprint = hashlib.sha256(b''.join((Path(__file__).parent / n).read_bytes() for n in
                                         ['audit_pack.py','inspect_csb_layout.py','inspect_db_table.py'])).hexdigest()
    counts = Counter()
    for number, (source, relative, sha) in enumerate(rows, 1):
        path = long_path(destination / 'files' / relative)
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != sha:
            raise ValueError('Extracted file integrity changed: ' + source)
        details = interpret(source, path, raw, reader, destination / 'interpreted')
        db.execute('INSERT INTO interpretation_attempts VALUES (?,?,?,?)',
                   (source, 'expanded:' + fingerprint, details['status'], json.dumps(details, ensure_ascii=False)))
        db.execute('UPDATE files SET interpretation_status=?,details=? WHERE source=?',
                   (details['status'], json.dumps(details, ensure_ascii=False), source))
        counts[details['status']] += 1
        if number % 500 == 0 or number == len(rows):
            db.commit()
            print(json.dumps({'phase':'reinterpretation','processed':number,'total':len(rows),'results':dict(counts)}), flush=True)
    summary = json.loads((destination / 'summary.json').read_text(encoding='utf-8'))
    counts = db.execute('SELECT extraction_status,interpretation_status,COUNT(*),SUM(size) FROM files GROUP BY 1,2').fetchall()
    summary['results'] = [{'extraction':a,'interpretation':b,'files':c,'bytes':d} for a,b,c,d in counts]
    summary['reinterpretation_completed'] = True
    (destination / 'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    db.close()


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reader-dir',required=True,type=Path)
    parser.add_argument('--destination',required=True,type=Path)
    parser.add_argument('--reinterpret',action='store_true')
    parser.add_argument('--repair',action='store_true')
    parser.add_argument('--extensions',nargs='+')
    args=parser.parse_args()
    if args.reinterpret or args.repair:
        reinterpret(args.reader_dir,args.destination,repair_only=args.repair,extensions=args.extensions)
    else:
        run(args.reader_dir,args.destination)
