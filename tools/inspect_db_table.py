"""Inspect already-decoded PLPcK table cells without assuming a column named id."""
import hashlib
import struct


def key_value(raw):
    if raw is None:
        return None
    try:
        value = raw.decode('utf-8')
        return value if value.isprintable() else {'raw_hex': raw.hex()}
    except UnicodeDecodeError:
        return {'raw_hex': raw.hex()}


def _inspect_table(data, source, bucket_offset):
    if not 76 <= len(data) <= 64 * 1024 * 1024 or data[:10] != b'PLPcK\x01\x26\0\0\0':
        raise ValueError('Unsupported table container')
    buckets = struct.unpack_from('<I', data, bucket_offset)[0] + 1
    cursor = 38 + buckets * 5
    if buckets > 1000000 or cursor > len(data) - 38:
        raise ValueError('Invalid bucket range')
    members = {}
    non_entries = []
    opaque = []
    while cursor + 15 <= len(data) - 38:
        total, kind, key_len, data_len = struct.unpack_from('<IBBI', data, cursor)
        if kind == 1 and key_len == 0 and data_len == 0 and 15 <= total <= len(data) - 38 - cursor:
            block = data[cursor:cursor + total]
            non_entries.append({'offset': cursor, 'bytes': total, 'kind': kind,
                                'sha256': hashlib.sha256(block).hexdigest(),
                                'semantics': 'keyless_kind1_block_not_a_row'})
            cursor += total
            continue
        if total != 15 + key_len + data_len or total < 15 or cursor + total > len(data) - 38:
            raise ValueError('Invalid member bounds')
        key = data[cursor + 15:cursor + 15 + key_len]
        value = data[cursor + 15 + key_len:cursor + total]
        if key in members:
            raise ValueError('Duplicate raw member key')
        members[key] = (value, cursor + 15 + key_len, kind)
        cursor += total
        if len(members) > 1000000:
            raise ValueError('Member limit')
    if len(data) - cursor != 38 or data[cursor:cursor + 6] != b'PLPcK\x01':
        raise ValueError('Unparsed or invalid footer')
    def count(key):
        value = members[key][0]
        if len(value) != 4:
            raise ValueError('Invalid declared table count')
        return struct.unpack('<I', value)[0]
    ncols, nrows = count(b'\tcols'), count(b'\trows')
    if not 0 < ncols <= 10000 or nrows > 1000000:
        raise ValueError('Declared table dimensions exceed limit')
    columns = [members[b'\t' + str(i).encode()][0].decode('utf-8') for i in range(ncols)]
    if len(set(columns)) != len(columns):
        raise ValueError('Duplicate column name')
    rows, keys, control = [], [], []
    for raw_key, (value, offset, kind) in members.items():
        if raw_key.startswith(b'\t'):
            continue
        if raw_key == b'\x1b\x01':
            control.append({'key_hex': raw_key.hex(), 'offset': offset, 'bytes': len(value),
                            'sha256': hashlib.sha256(value).hexdigest(), 'semantics': 'uninterpreted_control_member'})
            continue
        try:
            key = key_value(raw_key)
            if kind != 2 or not value.endswith(b'\0'):
                raise ValueError('Non-string row encoding')
            fields = value[:-1].decode('utf-8').split('\0')
            if len(fields) != ncols:
                raise ValueError('Row column count differs')
            rows.append(dict(zip(columns, fields)))
            keys.append(key)
        except (UnicodeDecodeError, ValueError) as exc:
            opaque.append({'key_hex': raw_key.hex(), 'offset': offset, 'bytes': len(value),
                           'sha256': hashlib.sha256(value).hexdigest(), 'reason': str(exc)})
    count_matches = len(rows) + len(opaque) == nrows
    if not count_matches:
        raise ValueError('Declared row count differs from members')
    declared_keys = [members.get(b'\t\t' + str(i).encode(), (None, None, None))[0] for i in range(nrows)]
    declared_keys = [key_value(v) for v in declared_keys]
    return {'source': source, 'columns': columns, 'row_count': nrows, 'rows': rows, 'row_keys': keys,
            'declared_row_keys': declared_keys, 'opaque_control_members': control,
            'non_entry_blocks': non_entries,
            'opaque_rows': opaque, 'complete_string_cells': not opaque,
            'validation': {'container_fully_walked': True, 'footer_bytes': 38,
                           'declared_row_count_matches': count_matches,
                           'decoded_rows_have_declared_columns': True,
                           'row_keys_match_id': all(r['id'] == k for r,k in zip(rows, keys)) if 'id' in columns else None},
            'scope': 'Static table cells; row keys are preserved separately from semantic columns.'}


def inspect_table(data, source):
    if len(data) < 76:
        raise ValueError('Truncated table container')
    candidates = {}
    errors = []
    for offset in (21, 17):
        count = struct.unpack_from('<I', data, offset)[0]
        if count in candidates:
            candidates[count][1].append(offset)
            continue
        try:
            result = _inspect_table(data, source, offset)
            candidates[count] = (result, [offset])
        except (ValueError, KeyError) as exc:
            errors.append(type(exc).__name__ + ': ' + str(exc))
    if len(candidates) != 1:
        raise ValueError('Ambiguous or unsupported table header: ' + '; '.join(errors))
    result, offsets = next(iter(candidates.values()))
    result['index_count_header_offsets'] = offsets
    return result
