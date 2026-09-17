"""Read-only fingerprints and consistent local backups for the material transition."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from datetime import datetime, timezone

root = Path(__file__).resolve().parents[2]
destination = Path(sys.argv[1]).resolve()
destination.mkdir(parents=True, exist_ok=True)
prior = json.loads((root / 'system2/outputs/runs/requirement-acceptance-20260911/stage-v2/normal-load-current08/before.json').read_text())
result = {'at': datetime.now(timezone.utc).isoformat(), 'stores': {}, 'originals': {}, 'canonical': {}}
for name, entry in prior['stores'].items():
    path = Path(entry['source'])
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as source:
        backup = destination / (name + '.sqlite')
        if backup.exists():
            raise ValueError('Backup destination already exists')
        with sqlite3.connect(backup) as target:
            source.backup(target)
        tables = {}
        for (table,) in source.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            quoted = '"' + table.replace('"', '""') + '"'
            rows = sorted(json.dumps(row, ensure_ascii=False, default=str) for row in source.execute('SELECT * FROM ' + quoted))
            tables[table] = {'rows': len(rows), 'sha256': hashlib.sha256('\n'.join(rows).encode()).hexdigest()}
        result['stores'][name] = {'source': str(path.relative_to(root)), 'tables': tables}
for path in sorted((root / 'system1/Data').rglob('*')):
    if path.is_file():
        result['originals'][str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
with sqlite3.connect((root / 'system2/runtime/workflow/workflow.sqlite').as_uri() + '?mode=ro', uri=True) as db:
    for (payload,) in db.execute('SELECT data FROM documents'):
        for ref in json.loads(payload).get('canonical', []):
            path = Path(ref['path'])
            result['canonical'][str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
(destination / 'fingerprints.json').write_text(json.dumps(result, indent=2))
print(json.dumps({'stores':len(result['stores']), 'originals':len(result['originals']), 'canonical':len(result['canonical']), 'evidence':str(destination/'fingerprints.json')}))
