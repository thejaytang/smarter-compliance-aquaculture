"""Capture the explicitly requested Windows branch's business state unchanged.

This is an evidence archive, not a validated Collaboration package or seed.
Runtime settings, credentials, sessions, environments and caches are excluded.
"""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import sqlite3
import zipfile

from backend.shared.filesystem import FilePath as Path, temporary_directory
from backend.shared.platform_support import exclusive_lock
from backend.shared.workspace import Workspace, DATABASES


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    root = Path(__file__).resolve().parents[2]
    w = Workspace(root / 'workbench')
    output = root / 'workbench/initial-data/windows-20261009'
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / 'manifest.json'
    if manifest_path.exists():
        raise ValueError('An archive manifest already exists; preserve the immutable capture.')
    archive = w.runtime / 'staging/windows-workspace-20261009.zip'
    archive.parent.mkdir(parents=True, exist_ok=True)
    if archive.exists():
        raise ValueError('Archive staging path already exists.')
    entries = {}
    tables = {}
    with exclusive_lock(w.runtime / 'state/service.lock'), temporary_directory(prefix='win-archive-') as stage:
        with w.freeze():
            inputs = []
            for name in DATABASES:
                target = stage / (name + '.sqlite')
                with closing(sqlite3.connect(w.database(name))) as source, closing(sqlite3.connect(target)) as dest:
                    source.backup(dest)
                    if dest.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                        raise ValueError('SQLite integrity failed: ' + name)
                    tables[name] = {table: dest.execute('SELECT count(*) FROM "' + table.replace('"', '""') + '"').fetchone()[0]
                                    for (table,) in dest.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
                inputs.append(('workbench/workspace/databases/' + name + '.sqlite', target))
            for path in sorted((w.workspace / 'sources').rglob('*')):
                if not path.is_file() or path.name.endswith(('.lock', '-wal', '-shm', '.tmp', '.log')):
                    continue
                if path.suffix in {'.sqlite', '.sqlite3'}:
                    raise ValueError('Unexpected database in source evidence: ' + str(path))
                inputs.append((path.relative_to(root).as_posix(), path))
            with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
                for name, path in inputs:
                    before = sha(path)
                    size = path.stat().st_size
                    with path.open('rb') as source, z.open(name, 'w', force_zip64=True) as target:
                        copied = hashlib.sha256()
                        while chunk := source.read(1024 * 1024):
                            target.write(chunk)
                            copied.update(chunk)
                    if copied.hexdigest() != before or path.stat().st_size != size:
                        raise ValueError('Source changed during capture: ' + name)
                    entries[name] = {'bytes': size, 'sha256': before}
        with zipfile.ZipFile(archive) as z:
            if set(z.namelist()) != set(entries):
                raise ValueError('Archive inventory mismatch')
            for name, record in entries.items():
                with z.open(name) as stream:
                    if hashlib.file_digest(stream, 'sha256').hexdigest() != record['sha256']:
                        raise ValueError('Archive readback mismatch: ' + name)
        parts = []
        with archive.open('rb') as source:
            index = 1
            while chunk := source.read(80 * 1024 * 1024):
                name = 'windows-workspace-20261009.zip.' + str(index).zfill(3)
                with (output / name).open('xb') as target:
                    target.write(chunk)
                parts.append({'name': name, 'bytes': len(chunk), 'sha256': hashlib.sha256(chunk).hexdigest()})
                index += 1
        manifest = {'schema': 'workbench-windows-evidence-archive/1',
                    'captured_at': datetime.now(timezone.utc).isoformat(),
                    'archive': archive.name, 'bytes': archive.stat().st_size, 'sha256': sha(archive),
                    'parts': parts, 'files': entries, 'database_tables': tables,
                    'sqlite_integrity': 'ok', 'archive_readback': 'all file SHA-256 values match',
                    'collaboration_validation': 'failed',
                    'known_error': 'Requirement has no matching saved material revision: 8f2d46c7-29f6-57e4-b600-e98781e875dd/1',
                    'purpose': 'Preserve the requested local state without repairing or replacing business history. Not a Collaboration import or initial seed.'}
        manifest_path.write_bytes((json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
        print(json.dumps({k: manifest[k] for k in ('captured_at', 'bytes', 'sha256', 'parts', 'sqlite_integrity')}, indent=2))


if __name__ == '__main__':
    main()
