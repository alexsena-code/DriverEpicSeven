"""Index literal static references in an extracted pack; never resolve live state."""
import argparse
import json
from pathlib import Path, PurePosixPath
import posixpath
import sqlite3
import time


def build(root):
    root = root.resolve()
    db = sqlite3.connect(root / 'audit.sqlite')
    rows = db.execute('SELECT source,destination,details FROM files WHERE extraction_status=\'verified\'').fetchall()
    names = {source for source, _, _ in rows}
    details = {source: (rel, json.loads(data)) for source,rel,data in rows}
    db.execute('CREATE TABLE IF NOT EXISTS asset_refs (source TEXT, kind TEXT, owner TEXT, reference TEXT, target TEXT, resolution TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS text_refs (source TEXT, row_index INTEGER, column_name TEXT, text_id TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS atlas_regions (source TEXT, page TEXT, region TEXT, properties TEXT)')
    for table in ('asset_refs', 'text_refs', 'atlas_regions'):
        db.execute('DELETE FROM ' + table)
    counts = {'asset_refs': 0, 'resolved_asset_refs': 0, 'text_refs': 0, 'atlas_regions': 0}
    def output(name):
        path = (root / 'interpreted' / name).resolve()
        if not path.is_relative_to((root / 'interpreted').resolve()):
            raise ValueError('Normalized path outside private extraction')
        return path
    def reference(source, kind, owner, value):
        if not isinstance(value, str) or not value:
            return
        relative = posixpath.normpath(str(PurePosixPath(source).parent / value))
        target = value if value in names else relative if relative in names else None
        resolution = 'literal_pack_path' if value in names else 'relative_pack_path' if target else 'unresolved_literal'
        db.execute('INSERT INTO asset_refs VALUES (?,?,?,?,?,?)', (source,kind,owner,value,target,resolution))
        counts['asset_refs'] += 1
        counts['resolved_asset_refs'] += target is not None
    english = details.get('text/en/text.db')
    texts = set()
    if english and english[1].get('normalized_file'):
        data = json.loads(output(english[1]['normalized_file']).read_text(encoding='utf-8'))
        texts = {r['id'] for r in data.get('rows', [])}
    known_exts = {'.png','.sct','.atlas','.sca','.scsp','.csb','.cfx','.particle','.ttf','.fnt','.webp','.jpg'}
    def json_literals(source, value, owner=''):
        if isinstance(value, dict):
            for key, item in value.items():
                json_literals(source, item, owner + '/' + str(key))
        elif isinstance(value, list):
            for index,item in enumerate(value):
                json_literals(source, item, owner + '/' + str(index))
        elif isinstance(value, str) and PurePosixPath(value).suffix.lower() in known_exts and '\n' not in value:
            reference(source, 'literal_asset_candidate', owner, value)
    started = time.time()
    for index, (source, _, _) in enumerate(rows, 1):
        rel, data = details[source]
        ext = PurePosixPath(source).suffix.lower()
        normalized = data.get('normalized_file')
        if ext == '.atlas' and normalized:
            parsed = json.loads(output(normalized).read_text(encoding='utf-8'))
            for page in parsed['pages']:
                reference(source,'atlas_page','pages',page['name'])
                for region in page['regions']:
                    db.execute('INSERT INTO atlas_regions VALUES (?,?,?,?)',
                               (source,page['name'],region['name'],json.dumps(region['properties'])))
                    counts['atlas_regions'] += 1
        elif ext == '.sca' and data.get('texture_page'):
            reference(source,'sca_page','header',data['texture_page'])
        elif ext == '.csb' and normalized:
            parsed = json.loads(output(normalized).read_text(encoding='utf-8'))
            for node in parsed['nodes']:
                for role,res in (node['declared_options'] or {}).get('resources',{}).items():
                    if res:
                        for field in ('path','plist'):
                            reference(source,'csb_resource',str(node['node_index']) + '/' + role + '/' + field,res[field])
        elif ext == '.db' and normalized:
            parsed = json.loads(output(normalized).read_text(encoding='utf-8'))
            if source != 'text/en/text.db':
                for row_index,row in enumerate(parsed.get('rows', [])):
                    for column,value in row.items():
                        if value in texts and len(value) > 3:
                            db.execute('INSERT INTO text_refs VALUES (?,?,?,?)',(source,row_index,column,value))
                            counts['text_refs'] += 1
            if data.get('depth') == 'filter_definition_text':
                for line_index,line in enumerate(parsed.get('lines', [])[1:],1):
                    fields = line.split('\t')
                    if fields and fields[0]:
                        reference(source,'virtual_table_component',str(line_index),'db/' + fields[0] + '.db')
        elif data.get('depth') in ('json_values','decompressed_json_values','xml_elements_attributes_and_text'):
            filename = normalized or data.get('decoded_file')
            if filename:
                parsed = json.loads(output(filename).read_text(encoding='utf-8'))
            else:
                path = (root / 'files' / rel).resolve()
                if not path.is_relative_to((root / 'files').resolve()):
                    raise ValueError('Source path outside extraction')
                parsed = json.loads(path.read_text(encoding='utf-8-sig'))
            json_literals(source, parsed)
        if index % 10000 == 0:
            db.commit()
            print(json.dumps({'files':index,**counts}),flush=True)
    db.execute('CREATE INDEX IF NOT EXISTS asset_refs_source ON asset_refs(source)')
    db.execute('CREATE INDEX IF NOT EXISTS text_refs_id ON text_refs(text_id)')
    db.execute('CREATE INDEX IF NOT EXISTS atlas_regions_name ON atlas_regions(region)')
    db.commit()
    assert db.execute('SELECT COUNT(*) FROM asset_refs WHERE target IS NOT NULL AND target NOT IN (SELECT source FROM files)').fetchone()[0] == 0
    summary = {**counts,'files_considered':len(rows),'elapsed_seconds':round(time.time()-started,2),
               'scope':'Literal static candidates only; not a complete semantic graph or a live selector.'}
    (root/'reference-summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary),flush=True)
    db.close()


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True,type=Path)
    build(parser.parse_args().root)
