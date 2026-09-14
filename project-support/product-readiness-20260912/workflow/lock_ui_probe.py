"""Bounded lock-only fault for the owned TS003 engineering draft; no DB writes."""
from pathlib import Path
from hashlib import sha256
import json
import select
import sqlite3
import sys
from datetime import datetime, timezone

root = Path(__file__).resolve().parents[3]
database = root / 'workbench/runtime/product-readiness-20260912/fixture/workbench/runtime/collaboration/personal/1436f495-a248-4240-a129-8f76dd65aa6d/workflow.sqlite'
assert database.is_file()
out = Path(__file__).parent / 'lock-ui-02'
out.mkdir(exist_ok=False)
with sqlite3.connect(database.resolve().as_uri()+'?mode=ro', uri=True) as source:
    data = json.loads(source.execute("SELECT data FROM material_documents WHERE source_id='TS003'").fetchone()[0])
    assert data['id']=='608f102a55d299a37f44f6873a427407' and data['revision']==5
    with sqlite3.connect(out/'before.sqlite') as backup:
        source.backup(backup)
        assert backup.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
manifest = {'scope':'isolated TS003 draft only; lock transaction writes no rows',
    'database':str(database),'material_id':data['id'],'before_revision':data['revision'],
    'backup_sha256':sha256((out/'before.sqlite').read_bytes()).hexdigest(),
    'acquired_at':None,'released_at':None}
with sqlite3.connect(database, timeout=2) as locked:
    locked.execute('BEGIN IMMEDIATE')
    manifest['acquired_at']=datetime.now(timezone.utc).isoformat()
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print('LOCK ACQUIRED: TS003 engineering personal draft only',flush=True)
    try:
        if select.select([sys.stdin],[],[],120)[0]:
            sys.stdin.readline()
    finally:
        locked.rollback()
        manifest['released_at']=datetime.now(timezone.utc).isoformat()
        (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
        print('LOCK RELEASED; transaction rolled back without writes',flush=True)
