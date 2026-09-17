"""Stopped-service code rollback plus SQLite snapshots; not a full asset backup."""
from pathlib import Path
from contextlib import closing
import json, shutil, sqlite3, sys

area = Path(__file__).resolve().parent
root = area.parents[1]
sys.path.insert(0, str(area/'candidate/workbench/src'))
from local_workbench import recovery

destination = area/'activation-checkpoint'
if destination.exists():
    raise SystemExit('Preserve existing checkpoint; inspect before retrying.')
info = recovery.layout(root)
with recovery.quiescent(root, info):
    code = set(recovery.source_inventory(root))
    for section in ('workbench/tests', 'system1/Code/tests'):
        code.update(p for p in (root/section).rglob('*') if p.is_file() and p.suffix in {'.py', '.mjs'} and '__pycache__' not in p.parts)
    required = sum(p.stat().st_size for p in code | set(info['stores']))
    if shutil.disk_usage(area).free < required*2 + 128*1024*1024:
        raise SystemExit('Insufficient checkpoint space.')
    destination.mkdir()
    manifest = {'status': 'incomplete', 'scope': 'Same-workstation code rollback and SQLite snapshots; excludes historical assets. Not a portable full recovery package.', 'code_files': {}, 'stores': {}}
    for source in sorted(code):
        rel = source.relative_to(root).as_posix()
        before = recovery.digest(source)
        target = destination/'code'/rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if recovery.digest(target) != before or recovery.digest(source) != before:
            raise ValueError('Code checkpoint mismatch: '+rel)
        manifest['code_files'][rel] = {'sha256': before, 'bytes': target.stat().st_size}
    for source in info['stores']:
        rel = source.relative_to(root).as_posix()
        target = destination/'stores'/rel
        target.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(source.as_uri()+'?mode=ro', uri=True)) as reader, closing(sqlite3.connect(target)) as writer:
            reader.backup(writer)
            if writer.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Store checkpoint integrity failed: '+rel)
        manifest['stores'][rel] = {'sha256': recovery.digest(target), 'bytes': target.stat().st_size}
    manifest['status'] = 'complete'
    (destination/'manifest.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps({'status': 'complete', 'code_files': len(manifest['code_files']), 'stores': len(manifest['stores']), 'scope': manifest['scope']}), flush=True)
