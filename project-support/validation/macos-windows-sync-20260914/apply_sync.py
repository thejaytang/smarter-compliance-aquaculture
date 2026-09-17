from pathlib import Path
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone

BASE = Path('/tmp/sc-macos-windows-sync-20260914')
ROOT = Path('/Users/tang/Desktop/smarter-compliance-aquaculture/05_Working area of requirements side')
EVIDENCE = ROOT / 'project-support/macos-windows-sync-20260914'
PLAN = json.loads((BASE / 'merge-plan.json').read_text())

def read(path):
    size = path.stat().st_size
    with path.open('rb') as handle:
        data = handle.read(size)
    assert len(data) == size, str(path)
    return data

def digest(data):
    return hashlib.sha256(data).hexdigest()

def atomic(path, data, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.windows-sync-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

assert not PLAN['conflicts'] and len(PLAN['files']) == 62
prepared = []
for item in PLAN['files']:
    name = item['path']
    assert '..' not in Path(name).parts and not Path(name).is_absolute()
    assert not any(part in {'runtime', 'Data', 'data', 'outputs', '.venv'} for part in Path(name).parts), name
    assert not name.endswith(('.sqlite', '.sqlite3', '.db', '.xlsx', '.pdf')), name
    local = ROOT / name
    before = read(local) if local.exists() else None
    assert (digest(before) if before is not None else None) == item['before_sha256'], 'Local changed: ' + name
    after = read(BASE / 'merged' / name)
    assert digest(after) == item['after_sha256'], 'Candidate changed: ' + name
    prepared.append((item, before, after))

# Back up every existing target before changing any source file.
backup = EVIDENCE / 'source-before'
assert not backup.exists(), 'Backup already exists; inspect previous application before continuing'
for item, before, _ in prepared:
    if before is not None:
        target = backup / item['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(before)
        os.chmod(target, item['before_mode'])
        assert digest(read(target)) == item['before_sha256']

# Make new component helpers available before replacing their callers.
prepared.sort(key=lambda entry: (entry[0]['action'] != 'add', entry[0]['path']))
applied = []
for item, before, after in prepared:
    target = ROOT / item['path']
    current = read(target) if target.exists() else None
    assert (digest(current) if current is not None else None) == item['before_sha256'], 'Concurrent change: ' + item['path']
    atomic(target, after, item['before_mode'] or 0o644)
    assert digest(read(target)) == item['after_sha256']
    applied.append(item)
    print('applied', item['path'], flush=True)

for item in applied:
    assert digest(read(ROOT / item['path'])) == item['after_sha256']
result = {**PLAN, 'applied_at_utc': datetime.now(timezone.utc).isoformat(),
          'verified_files': len(applied), 'business_data_targets': 0,
          'normal_service_restarted': False, 'github_push': False}
(EVIDENCE / 'sync-manifest.json').write_text(json.dumps(result, indent=2) + '\n')
shutil.copyfile(BASE / 'merge-plan.json', EVIDENCE / 'merge-plan.json')
print('VERIFIED', len(applied), 'files; no business data paths targeted', flush=True)
