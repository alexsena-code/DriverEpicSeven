"""Read-only routing and bounded queries over the existing extracted-pack index."""

import argparse
import json
from pathlib import Path
import sqlite3
import sys
import unicodedata


ROOT = Path(__file__).resolve().parents[1]
SCOPE = ('Static source evidence only. Not current visibility, selection, inventory, '
         'global client coordinates, runtime selectors or authorization to act.')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(text).casefold())
                   if not unicodedata.combining(c))


def routes(repo):
    index = read_json(repo / 'data/catalogs/source-index.json')
    result = [dict(topic, kind='topic') for topic in index['topics']]
    families = read_json(repo / index['family_catalog'])['families']
    evidence = read_json(repo / index['family_evidence'])
    for family in families:
        groups = [group for group in evidence['groups'] if family['id'] in group['family_ids']]
        topics = [topic for topic in index['topics'] if topic['id'] == family['id']
                  or family['id'] in topic.get('related_families', [])]
        sources = list(dict.fromkeys(source for group in groups for source in
                                    group['decoded_layouts'] + group['decoded_databases']))
        sources = list(dict.fromkeys(sources + [source for topic in topics for source in topic['sources']]))
        result.append({'id': family['id'], 'kind': 'family', 'title': family['title'],
                       'aliases': [family['id']], 'sources': sources,
                       'repository_refs': list(dict.fromkeys(
                           [index['family_catalog'], index['family_evidence']]
                           + [ref for topic in topics for ref in topic['repository_refs']])),
                       'gaps': list(dict.fromkeys(
                           [family['needs_calibration']] + [g['remaining_live_measurement'] for g in groups]
                           + [gap for topic in topics for gap in topic['gaps']])),
                       'source_scope': 'Shared group candidates; not an exhaustive mapping of this family.',
                       'runtime_enabled': family['runtime_enabled']})
    return result


class SourceIndex:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.path = self.root / 'audit.sqlite'
        self.db = None
        if self.path.is_file():
            self.db = sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True)
            self.db.row_factory = sqlite3.Row
            self.db.execute('PRAGMA query_only=ON')

    def close(self):
        if self.db:
            self.db.close()

    def metadata(self, source):
        if self.db is None:
            return {'source': source, 'inventory_known': None, 'reason': 'private_index_unavailable'}
        row = self.db.execute('SELECT source,size,sha256,extraction_status,interpretation_status,details '
                              'FROM files WHERE source=?', (source,)).fetchone()
        if row is None:
            return {'source': source, 'inventory_known': False, 'reason': 'source_not_in_inventory'}
        result = dict(row)
        details = json.loads(result.pop('details'))
        result['inventory_known'] = True
        result['interpretation_depth'] = details.get('depth')
        name = details.get('normalized_file') or details.get('decoded_file')
        if name:
            base = (self.root / 'interpreted').resolve()
            path = (base / name).resolve()
            if not path.is_relative_to(base):
                raise ValueError('Derived file escapes the interpreted directory.')
            result['interpreted_file'] = str(path)
            result['interpreted_file_available'] = path.is_file()
        return result

    def inspect(self, source, term, limit):
        meta = self.metadata(source)
        if not meta.get('inventory_known') or not meta.get('interpreted_file_available'):
            return {'ok': False, 'scope': SCOPE, 'file': meta, 'candidates': []}
        path = Path(meta['interpreted_file'])
        if path.stat().st_size > 128 * 1024 * 1024:
            raise ValueError('Derived file exceeds the 128 MiB inspection limit.')
        data = read_json(path)
        if not isinstance(data, dict):
            raise ValueError('Derived content has no supported object structure; interpretation remains unknown.')
        if data.get('source') not in (None, source):
            raise ValueError('Derived source identity differs from inventory.')
        if data.get('source_sha256') not in (None, meta['sha256']):
            raise ValueError('Derived source hash differs from inventory.')
        summary = {'limitations': data.get('limitations', []), 'scope': data.get('scope')}
        if 'nodes' in data:
            summary.update(kind='csb', nodes=len(data['nodes']),
                           unsupported_class_nodes=sum(not n.get('class_options_supported', False) for n in data['nodes']))
            candidates = data['nodes']
        elif 'rows' in data:
            summary.update(kind='db', columns=data.get('columns'), rows=len(data['rows']),
                           opaque_rows=len(data.get('opaque_rows', [])),
                           opaque_control_members=len(data.get('opaque_control_members', [])),
                           complete_string_cells=data.get('complete_string_cells'))
            keys = data.get('row_keys', [])
            candidates = ({'row_index': i, 'container_key': keys[i] if i < len(keys) else None, 'row': row}
                          for i, row in enumerate(data['rows']))
        else:
            summary.update(kind='other_json', keys=list(data))
            candidates = [{'key': key, 'value': value} for key, value in data.items()]
        matches, total = [], 0
        if term:
            needle = normalized(term)
            for candidate in candidates:
                if needle in normalized(json.dumps(candidate, ensure_ascii=False)):
                    total += 1
                    if len(matches) < limit:
                        matches.append(candidate)
        return {'ok': True, 'scope': SCOPE, 'file': meta, 'content': summary,
                'find': term, 'total_candidates': total, 'truncated': total > limit,
                'candidates': matches,
                'hint': None if term else 'Use --find to inspect only matching nodes/rows; metadata is not interpretation completeness.'}

    def references(self, kind, value, limit):
        if self.db is None:
            return {'ok': False, 'reason': 'private_index_unavailable', 'scope': SCOPE}
        if kind == 'asset':
            query = 'SELECT source,kind,owner,reference,target,resolution FROM asset_refs WHERE reference=? OR target=?'
            args = (value, value)
        else:
            query = 'SELECT source,row_index,column_name,text_id FROM text_refs WHERE text_id=?'
            args = (value,)
        try:
            total = self.db.execute('SELECT COUNT(*) FROM (' + query + ')', args).fetchone()[0]
            rows = [dict(row) for row in self.db.execute(query + ' ORDER BY source LIMIT ?', args + (limit,))]
        except sqlite3.OperationalError as error:
            if 'no such table' not in str(error):
                raise
            return {'ok': False, 'reason': 'reference_index_missing', 'scope': SCOPE,
                    'hint': 'The existing offline index_pack_references.py builds these tables; this query never rebuilds them.'}
        return {'ok': True, 'scope': SCOPE, 'kind': kind, 'value': value,
                'total_candidates': total, 'truncated': total > limit, 'candidates': rows}


def search(repo, index, query, family, limit):
    entries = routes(repo)
    if family:
        matches = [(1, entry) for entry in entries if entry['kind'] == 'family' and entry['id'] == family]
    else:
        needle = normalized(query or '').strip()
        matches = []
        for entry in entries:
            aliases = [normalized(value) for value in [entry['id'], entry['title']] + entry['aliases']]
            score = 100 if needle and needle in aliases else 0
            if needle and not score:
                score = 20 if any(needle in value for value in aliases) else 0
                score += sum(token in ' '.join(aliases) for token in needle.split() if len(token) > 2)
            if score or not needle:
                matches.append((score, entry))
    matches.sort(key=lambda value: (-value[0], value[1]['kind'], value[1]['id']))
    selected = []
    for score, entry in matches[:limit]:
        selected.append({**entry, 'score': score,
                         'sources': [index.metadata(source) for source in entry['sources']]})
    return {'ok': bool(matches), 'scope': SCOPE, 'private_index_available': index.db is not None,
            'query': query, 'family': family, 'total_candidates': len(matches),
            'truncated': len(matches) > limit, 'routes': selected}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('query', nargs='?', help='Operation or topic, e.g. "trocar personagem"')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--family', help='Exact family ID from the existing operation map')
    mode.add_argument('--source', help='Exact inventory path, e.g. wnd/formation.csb')
    mode.add_argument('--asset', help='Exact literal asset reference or resolved target')
    mode.add_argument('--text-id', help='Exact localized text key used by indexed sources')
    parser.add_argument('--find', help='Literal case/accent-insensitive filter within one derived file')
    parser.add_argument('--limit', type=int, choices=range(1, 21), default=5, metavar='1..20')
    parser.add_argument('--root', type=Path, default=ROOT / 'assets/local/full-pack')
    args = parser.parse_args(argv)
    if args.find and not args.source:
        parser.error('--find requires --source')
    if args.query and any((args.family, args.source, args.asset, args.text_id)):
        parser.error('Use a topic query or one explicit selector, not both.')
    index = None
    try:
        index = SourceIndex(args.root)
        if args.source:
            result = index.inspect(args.source, args.find, args.limit)
        elif args.asset or args.text_id:
            result = index.references('asset' if args.asset else 'text', args.asset or args.text_id, args.limit)
        else:
            result = search(ROOT, index, args.query, args.family, args.limit)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['ok'] else 1
    except (OSError, ValueError, sqlite3.Error) as error:
        print(json.dumps({'ok': False, 'error': str(error)}, ensure_ascii=False))
        return 1
    finally:
        if index:
            index.close()


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
