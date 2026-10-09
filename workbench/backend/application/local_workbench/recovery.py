"""Explicit, stopped-service recovery packages. No business writes or schedules."""
from __future__ import annotations
import argparse
from contextlib import ExitStack, contextmanager, closing
from datetime import datetime, timezone
import hashlib
import json
import os
from backend.shared.filesystem import FilePath as Path
import shutil
import sqlite3
from backend.shared.sqlite_support import connect as connect_sqlite
import subprocess
from backend.shared.platform_support import process_alive, exclusive_lock, venv_python


def digest(path):
    # Bound reads to the descriptor size: avoid a blocking extra read at EOF.
    # Some local filesystem reads can transiently end early. Reopen at most
    # three times, and never accept a hash unless every advertised byte arrived.
    for _ in range(3):
        with path.open('rb') as stream:
            before = os.fstat(stream.fileno())
            content = stream.read(before.st_size)
            length = len(content)
            after = os.fstat(stream.fileno())
            if before.st_size != after.st_size:
                raise OSError('Recovery resource size changed while reading: ' + str(path))
            if length == before.st_size:
                return hashlib.sha256(content).hexdigest()
    raise OSError('Incomplete recovery resource: ' + str(path))

def digests(paths):
    # Serial reads avoid stressing local filesystem providers during a stopped
    # backup. Independent before/copy/after hashes still bind exact content.
    return {path: digest(path) for path in paths}

def below(path, root):
    path = path.resolve()
    if not path.is_relative_to(root): raise ValueError('A configured recovery resource is outside the project root.')
    return path

def quote(name): return '"' + name.replace('"', '""') + '"'

def layout(root):
    from backend.shared.workspace import Workspace, active, DATABASES
    if active(root/'workbench'):
        w=Workspace(root/'workbench')
        raw=json.loads(w.source_config.read_text())
        return dict(modern=True,config=w.source_config,
            stores=[w.journal,*[w.database(n) for n in DATABASES],*[p for p in (w.runtime/'state').rglob('*') if p.is_file() and p.suffix in {'.sqlite','.sqlite3'} and p!=w.journal]],
            source=w.workspace/'sources',logs=(w.source_config.parent/raw['log_root']).resolve(),
            companion=w.workspace/'sources/governance-template.xlsx',workbook=(w.source_config.parent/raw['workbook']).resolve())
    config = root / 'system1/Code/config/config.json'
    raw = json.loads(config.read_text())
    def configured(key): return below(config.parent / raw[key], root)
    governance = configured('governance_db')
    stores = [governance, configured('log_root') / 'source-assessments.sqlite',
        configured('log_root') / 'leader_state.sqlite', root / 'system2/runtime/workflow/workflow.sqlite',
        root / 'workbench/runtime/workbench.sqlite']
    optional_jobs = root / 'system2/runtime/jobs.sqlite3'
    if optional_jobs.is_file(): stores.append(optional_jobs)
    personal = root/'workbench/runtime/collaboration/personal'
    if personal.exists():
        stores.extend(sorted(below(path, root) for path in personal.rglob('workflow.sqlite')))
    for path in stores:
        if not path.is_file(): raise ValueError('A required owning store is missing; recovery package was not created.')
    return dict(config=config, stores=stores, source=configured('source_root'), logs=configured('log_root'),
        companion=governance.with_name(governance.stem+'-migration-input.xlsx'), workbook=configured('workbook'))

@contextmanager
def quiescent(root, info):
    with ExitStack() as stack:
        if info['workbook'].with_name('~$'+info['workbook'].name).exists():
            raise ValueError('Close the source Excel register before backup.')
        modern = info.get('modern')
        workflow = root/('workbench/workspace/sources/processing/main' if modern else 'system2/runtime/workflow')
        personal = root/('workbench/workspace/sources/collaboration/personal' if modern else 'workbench/runtime/collaboration/personal')
        if list(workflow.glob('~$*.xlsx')):
            raise ValueError('Close the System2 Excel register before backup.')
        state=root/('workbench/runtime/state' if info.get('modern') else 'workbench/runtime')
        marker = state/'server.json'
        if marker.exists():
            server_state = json.loads(marker.read_text())
            if process_alive(server_state['pid']): raise ValueError('Stop the workbench and wait for all processing to finish before backing up.')
        locks = [state/'service.lock', info['logs']/'.system1-run.lock',
            info['workbook'].parent/'.system1-source-management.lock',
            workflow/'.worker.lock', workflow/'.material-worker.lock']
        if personal.exists():
            locks.extend(path/'.material-worker.lock' for path in personal.iterdir() if path.is_dir())
        for path in locks:
            try: stack.enter_context(exclusive_lock(path))
            except BlockingIOError: raise ValueError('Another writer is active; no consistent backup can be made.') from None
        # Hold every database writer reservation throughout inventory and copy.
        # Separate read connections below can take SQLite backup snapshots safely.
        for path in sorted(info['stores']):
            conn = connect_sqlite(path.resolve().as_uri()+'?mode=rw', uri=True, timeout=0)
            stack.callback(conn.close)
            try: conn.execute('BEGIN IMMEDIATE')
            except sqlite3.OperationalError: raise ValueError('An owning database is busy; stop its writer before backing up.') from None
        yield


def file_references(value):
    if isinstance(value, dict):
        for item in value.values(): yield from file_references(item)
    elif isinstance(value, list):
        for item in value: yield from file_references(item)
    elif isinstance(value, str) and Path(value).is_absolute():
        yield Path(value)


def inventory(root, info):
    if info.get('modern'):
        files=set(info['stores'])
        for folder in [info['source'],root/'workbench/runtime/state',root/'workbench/runtime/settings']:
            files.update(p for p in folder.rglob('*') if p.is_file() and p.name not in {'server.json','listen-port.json','ai-provider.json','model-provider.json','model-provider.local.json','interpretation-provider.json'} and not p.name.endswith(('-wal','-shm','.lock','.tmp')))
        return sorted(files),[info['companion']]
    files = set(info['stores']) | {info['config'], info['companion'], info['workbook']}
    if not info['companion'].is_file(): raise ValueError('Immutable governance migration companion is missing.')
    directories = [info['source'], info['logs'], root/'workbench/runtime/uploads', root/'workbench/runtime/collaboration',
        root/'system2/runtime/workflow/material-originals', root/'system2/runtime/workflow/material-artifacts']
    for directory in directories:
        if directory.exists(): files.update(p for p in directory.rglob('*') if p.is_file())
    for directory in (root/'system1/Code/runtime', root/'workbench/runtime', root/'system2/runtime/workflow'):
        files.update(p for p in directory.glob('*') if p.is_file() and not p.name.endswith(('-wal','-shm','.lock','.tmp')))
    references = set()
    for path in info['stores']:
        with closing(connect_sqlite(path.resolve().as_uri()+'?mode=ro', uri=True)) as db:
            tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            for table in tables:
                for row in db.execute('SELECT * FROM '+quote(table)):
                    for value in row:
                        if not isinstance(value, str): continue
                        try: decoded = json.loads(value)
                        except ValueError: decoded = value
                        for ref in file_references(decoded):
                            if not ref.is_relative_to(root): continue  # Opaque retained historical text is not an active path.
                            if ref.is_file(): references.add(ref)
            if path.name == 'workflow.sqlite' and 'documents' in tables:
                for (payload,) in db.execute('SELECT data FROM documents'):
                    for entry in json.loads(payload).get('canonical', []):
                        ref = below(Path(entry['path']), root)
                        if not ref.is_file() or digest(ref) != entry['sha256']: raise ValueError('A bound Canonical artifact is missing or changed.')
                        references.add(ref)
                        files.update(p for p in ref.parent.rglob('*') if p.is_file())
    files.update(references)
    # Never include live socket metadata or copied database journals as recovery state.
    files = {below(p, root) for p in files if p.name not in {'server.json','listen-port.json','ai-provider.json','interpretation-provider.json'} and not p.name.startswith('.ai-provider-') and not p.name.endswith(('-wal','-shm','.lock','.tmp'))}
    for path in files:
        if not path.is_file(): raise ValueError('A required recovery resource is missing.')
    return sorted(files), sorted(references)


SOURCE_DECLARATIONS = (
    'ENVIRONMENT.md', 'README.md', 'AGENTS.md', 'Open Workbench.command', 'workbench/deployment/Open Workbench.cmd', 'workbench/deployment/Open Reviewer Workbench.cmd',
    'project-support/design/PRODUCT.md', 'project-support/design/DESIGN.md',
    'workbench/deployment/setup_windows.cmd', 'workbench/scripts/check_platform.py',
    'workbench/docs/windows-offline-review-checklist.md',
    'workbench/pyproject.toml', 'workbench/USER_GUIDE.md',
    'system2/pyproject.toml', 'system2/uv.lock', 'system2/USER_GUIDE.md',
    'system1/USER_GUIDE.md', 'system1/Code/ENGINEERING.md',
    'system1/Code/deployment/requirements.txt', 'system1/Code/deployment/setup_macos.command',
    'system1/Code/deployment/setup_windows.cmd', 'system1/Code/config/config.example.json',
    'system1/Code/config/schedule.example.json', 'system1/Code/config/model-provider.example.json',
    'system2/config/default.yaml', 'system2/config/pdf-intake-positioned.yaml',
    'system2/config/pdf-intake-local.yaml', 'system2/config/asc-sample-no-vl.yaml',
    'system2/config/html-auto.json', 'system2/config/html-template.json',
    'system2/config/model-provider.example.json',
)
SOURCE_REQUIRED = ('ENVIRONMENT.md', 'workbench/pyproject.toml', 'system2/pyproject.toml',
    'system2/uv.lock', 'system1/Code/deployment/requirements.txt', 'system1/Code/deployment/setup_macos.command')
SOURCE_SUFFIXES = {'.py', '.js', '.css', '.html', '.json', '.webp', '.svg', '.png', '.woff', '.woff2'}

def source_inventory(root):
    """Explicit source/asset locations and public declarations, never live config or environments."""
    if (root/'deployment.py').is_file():
        import importlib.util
        spec=importlib.util.spec_from_file_location('recovery_product_boundary',root/'workbench/deployment/check_app_boundary.py')
        policy=importlib.util.module_from_spec(spec);spec.loader.exec_module(policy)
        files={root/p for p in policy.ROOT_FILES|policy.WORKBENCH_FILES|policy.COMPONENT_FILES if (root/p).is_file()}
        for prefix in policy.PREFIXES:
            for folder,dirs,names in os.walk(root/prefix):
                dirs[:]=[d for d in dirs if d not in {'.venv','node_modules','__pycache__','.cache'}]
                files.update(Path(folder)/name for name in names if not policy.business_file((Path(folder)/name).relative_to(root).as_posix()))
        return sorted(files)
    missing = [relative for relative in SOURCE_REQUIRED if not (root/relative).is_file()]
    if missing: raise ValueError('Required source/dependency declarations are missing: '+', '.join(missing))
    files = {root/relative for relative in SOURCE_DECLARATIONS if (root/relative).is_file()}
    for relative in ('system1/Code/src', 'system2/src', 'workbench/src', 'workbench/ui', 'system2/config/schemas'):
        for code in (root/relative).rglob('*'):
            if code.is_file() and (code.suffix in SOURCE_SUFFIXES or code.is_relative_to(root/'workbench/ui/vendor')) and not any(part.startswith('.') or part in {'__pycache__', 'node_modules'} for part in code.relative_to(root).parts):
                files.add(code)
    return sorted(files)


def snapshot_code(root, destination, manifest):
    code_files = source_inventory(root)
    manifest['code_files'] = {}
    manifest['code_fingerprints'] = {}
    hashes = {path.relative_to(root).as_posix(): digest(path) for path in code_files}
    for source in code_files:
        relative = source.relative_to(root).as_posix(); target = destination/'code'/relative
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
        fingerprint = digest(target)
        if fingerprint != hashes[relative]: raise ValueError('Source changed while creating its recovery snapshot.')
        manifest['code_files'][relative] = {'sha256': fingerprint, 'bytes': target.stat().st_size}
        if source.suffix != '.md': manifest['code_fingerprints'][relative] = fingerprint
    if any(digest(root/relative) != value for relative, value in hashes.items()):
        raise ValueError('Source changed while creating its recovery snapshot.')
    manifest['source_snapshot'] = 'Exact local source, UI assets, dependency declarations/locks and setup guide; no environments, caches, live provider config, secrets or scheduler registration.'


def backup(root, destination):
    root = Path(root).resolve(); destination = Path(destination).resolve()
    if destination.exists(): raise ValueError('Backup destination must be new; previous packages are preserved.')
    info = layout(root)
    source_inventory(root)  # Fail before creating a package if reproducibility inputs are absent.
    if destination.is_relative_to(info['source']) or destination.is_relative_to(root/'system2/runtime/workflow'):
        raise ValueError('Choose a backup destination outside source and workflow assets.')
    with quiescent(root, info):
        files, references = inventory(root, info)
        required = sum(p.stat().st_size for p in files) + sum(p.stat().st_size for p in source_inventory(root))
        if shutil.disk_usage(destination.parent).free < required * 2 + 128 * 1024 * 1024:
            raise ValueError('Insufficient free space for the bounded recovery package and safety margin.')
        if any(destination.is_relative_to(path) for path in (info['logs'], root/'workbench/runtime/uploads', root/'workbench/runtime/collaboration')):
            raise ValueError('Backup destination overlaps an included resource directory.')
        hashes = {p.relative_to(root).as_posix(): value for p, value in digests(p for p in files if p not in info['stores']).items()}
        destination.mkdir(parents=True)
        manifest = {'format': 'workbench-recovery-v3' if info.get('modern') else 'workbench-recovery-v2', 'status': 'incomplete', 'created_at': datetime.now(timezone.utc).isoformat(),
            'original_root': str(root), 'stores': [p.relative_to(root).as_posix() for p in info['stores']],
            'references': [p.relative_to(root).as_posix() for p in references], 'files': {},
            'consistency': 'stopped service, process locks and simultaneous SQLite writer reservations',
            'browser_drafts': 'Unsaved browser-local drafts are not included.'}
        (destination/'incomplete.json').write_text(json.dumps(manifest, indent=2))
        def copy_resource(source):
            rel = source.relative_to(root).as_posix(); target = destination/'files'/rel
            target.parent.mkdir(parents=True, exist_ok=True)
            if source in info['stores']:
                with closing(connect_sqlite(source.as_uri()+'?mode=ro', uri=True)) as db, closing(connect_sqlite(target)) as out:
                    db.backup(out)
                    if out.execute('PRAGMA integrity_check').fetchone()[0] != 'ok': raise ValueError('Database backup integrity check failed.')
            else: shutil.copy2(source, target)
            return rel, {'sha256': digest(target), 'bytes': target.stat().st_size}
        # Keep local filesystem reads and copies bounded and sequential.
        manifest['files'] = dict(copy_resource(source) for source in files)
        current_hashes = digests(root/rel for rel in hashes)
        changed = {rel: {'before': old, 'after': current_hashes[root/rel], 'copy': manifest['files'][rel]['sha256']}
                   for rel, old in hashes.items()
                   if current_hashes[root/rel] != old or manifest['files'][rel]['sha256'] != old}
        if changed:
            (destination/'changed-resources.json').write_text(json.dumps(changed, indent=2))
            raise ValueError('A resource changed during backup. See changed-resources.json in the retained incomplete package.')
        snapshot_code(root, destination, manifest)
        manifest['status'] = 'complete'
        try:
            revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True, text=True, timeout=5)
            manifest['code_revision'] = revision.stdout.strip() if revision.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired): manifest['code_revision'] = None
        (destination/'manifest.json').write_text(json.dumps(manifest, indent=2))
        verify(destination)
        return {'status': 'complete', 'files': len(files), 'code_files': len(manifest['code_files']), 'stores': len(info['stores']), 'destination': str(destination)}


def verify(package):
    package = Path(package).resolve(); manifest = json.loads((package/'manifest.json').read_text())
    if manifest.get('format') not in {'workbench-recovery-v1', 'workbench-recovery-v2','workbench-recovery-v3'} or manifest.get('status') != 'complete': raise ValueError('Recovery package is incomplete or unsupported.')
    assets = package/'files'
    entries = list(assets.rglob('*'))
    if any(path.is_symlink() for path in entries):
        raise ValueError('Recovery packages cannot contain filesystem aliases.')
    if {path.relative_to(assets).as_posix() for path in entries if path.is_file()} != set(manifest['files']):
        raise ValueError('Recovery inventory differs from package files.')
    paths = {rel: below(package/'files'/rel, package/'files') for rel in manifest['files']}
    for rel, path in paths.items():
        if not path.is_file() or path.stat().st_size != manifest['files'][rel]['bytes']:
            raise ValueError('Recovery file verification failed; restoration refused.')
    actual = digests(paths.values())
    if any(actual[path] != manifest['files'][rel]['sha256'] for rel, path in paths.items()):
        raise ValueError('Recovery file verification failed; restoration refused.')
    for rel in manifest['stores']:
        if rel not in manifest['files']: raise ValueError('Recovery store is not inventoried.')
        with closing(connect_sqlite((package/'files'/rel).as_uri()+'?mode=ro&immutable=1', uri=True)) as db:
            if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok': raise ValueError('Recovery database integrity check failed.')
    if any(ref not in manifest['files'] for ref in manifest['references']): raise ValueError('Recovery reference is missing.')
    if manifest['format']=='workbench-recovery-v3':
        from local_workbench.workspace_integrity import inspect
        inspect(assets/'workbench/workspace/databases',assets/'workbench/workspace/sources')
    if manifest['format'] in {'workbench-recovery-v2','workbench-recovery-v3'}:
        records = manifest.get('code_files')
        if not isinstance(records, dict) or not records: raise ValueError('Recovery source snapshot is missing.')
        archive = package/'code'; entries = list(archive.rglob('*'))
        if any(path.is_symlink() for path in entries): raise ValueError('Recovery source snapshot cannot contain filesystem aliases.')
        if {path.relative_to(archive).as_posix() for path in entries if path.is_file()} != set(records):
            raise ValueError('Recovery source snapshot inventory differs from files.')
        for relative, record in records.items():
            path = below(archive/relative, archive)
            if not path.is_file() or path.stat().st_size != record['bytes'] or digest(path) != record['sha256']:
                raise ValueError('Recovery source snapshot verification failed.')
        if any(manifest['code_files'].get(relative, {}).get('sha256') != value for relative, value in manifest.get('code_fingerprints', {}).items()):
            raise ValueError('Recovery source version binding is inconsistent.')
    return manifest


def extract_code(package, destination):
    manifest = verify(package); destination = destination.resolve()
    if not manifest.get('code_files'): raise ValueError('This older recovery package contains fingerprints only, not source code.')
    if destination.exists(): raise ValueError('Source snapshot destination must be new.')
    if destination.is_relative_to(package.resolve()): raise ValueError('Extract source outside the immutable recovery package.')
    shutil.copytree(package.resolve()/'code', destination)
    for relative, record in manifest['code_files'].items():
        if digest(destination/relative) != record['sha256']: raise ValueError('Extracted source verification failed.')
    return {'status': 'source_extracted', 'files': len(manifest['code_files']), 'destination': str(destination),
        'environments': 'Recreate using this snapshot ENVIRONMENT.md before serve-restored.'}


def restore(package, destination):
    destination = destination.resolve()
    if destination.exists(): raise ValueError('Restore destination must be new; existing workspaces are never overwritten.')
    manifest = verify(package)
    if destination.is_relative_to(package.resolve()/'files'):
        raise ValueError('Restore destination must be outside the package asset tree.')
    shutil.copytree(package.resolve()/'files', destination)
    # Raw databases and history remain byte-identical. A mapping identifies paths
    # for isolated read verification; no silent text replacement in review history.
    mapping = {'original_root': manifest['original_root'], 'restored_root': str(destination),
        'package': str(package.resolve()), 'database_rewritten': False,
        'code_fingerprints': manifest.get('code_fingerprints', {}),
        'startup': 'Use verified source code and isolated runtime configuration; do not launch legacy references against the original workspace.'}
    (destination/'recovery-mapping.json').write_text(json.dumps(mapping, indent=2))
    for rel, record in manifest['files'].items():
        if digest(destination/rel) != record['sha256']: raise ValueError('Restored file verification failed.')
    return {'status': 'restored', 'destination': str(destination), 'files': len(manifest['files']), 'stores': len(manifest['stores']), 'database_rewritten': False}


def serve_restored(destination, code_root):
    """Launch an isolated inspection service without workers or business actions."""
    from http.server import ThreadingHTTPServer
    from urllib.parse import urlsplit
    from local_workbench.server import Application, Handler
    destination, code_root = destination.resolve(), code_root.resolve()
    mapping = json.loads((destination/'recovery-mapping.json').read_text())
    if destination == Path(mapping['original_root']).resolve() or destination == code_root:
        raise ValueError('Restored inspection must use a separate directory.')
    for relative, expected in mapping.get('code_fingerprints', {}).items():
        code = below(code_root/relative, code_root)
        if not code.is_file() or digest(code) != expected:
            raise ValueError('Restore inspection requires the code version recorded in the package.')
    info = layout(destination)
    for key in ('source', 'logs', 'companion', 'workbook', 'config'):
        below(info[key], destination)
    for path in info['stores']: below(path, destination)
    for component in (('workbench/backend/system1','workbench/backend/system2') if info.get('modern') else ('system1/Code','system2')):
        if not venv_python(code_root/component).is_file() or not (code_root/component/'src').is_dir():
            raise ValueError('Required local code or environment is unavailable.')
    # Immutable history keeps its original path strings. The inspection service
    # serves only bound material originals and reader resources from restored paths;
    # legacy evidence endpoints cannot follow historical paths into live storage.
    class RestoredHandler(Handler):
        def do_GET(self):
            path = urlsplit(self.path).path
            allowed = {'/health', '/api/state', '/api/runtime-status', '/api/collaboration/state', '/api/materials', '/api/material',
                '/api/material/history', '/api/material/candidate', '/api/material/conflict',
                '/api/material/reader', '/api/material/original', '/api/material/html'}
            if path.startswith('/api/') and path not in allowed:
                return self.send(403, {'error': 'Legacy and mutation-related reads are disabled in restored inspection.'})
            return super().do_GET()
        def do_POST(self):
            if self.path not in {'/api/actor', '/api/stop'}:
                return self.send(403, {'error': 'Restored inspection is read-only; business actions and extraction are disabled.'})
            return super().do_POST()
    # Explicit code/data paths avoid privileged Windows symlink creation. Neither
    # adapter is allowed to resolve an owning store through the selected code root.
    from local_workbench.adapter import System2
    from local_workbench.runtime_status import ObservedAdapter
    app = Application(destination/'workbench', system_root=code_root/('workbench/backend/system1' if info.get('modern') else 'system1'),
        config=info['config'], code_root=code_root, start_workers=False)
    app.read_only_restored = True
    if not info.get('modern'):
        app.system2 = ObservedAdapter(System2(code_root/'system2', code_root/'system1',
            info['config'], destination/'system2/runtime/workflow'), app.monitor, 2)
    server = ThreadingHTTPServer(('127.0.0.1', 0), RestoredHandler); server.app = app
    marker = app.runtime/'server.json'
    marker.write_text(json.dumps({'pid': os.getpid(), 'port': server.server_port, 'root': str(app.root), 'instance': app.instance, 'mode': 'restored_inspection'}))
    print(json.dumps({'status': 'serving', 'url': f'http://127.0.0.1:{server.server_port}/', 'mode': 'restored_inspection', 'workers': False}), flush=True)
    try: server.serve_forever(poll_interval=.3)
    finally: server.server_close(); app.close(); marker.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    create = sub.add_parser('backup'); create.add_argument('--root', type=Path, required=True); create.add_argument('--destination', type=Path, required=True)
    check = sub.add_parser('verify'); check.add_argument('package', type=Path)
    recover = sub.add_parser('restore'); recover.add_argument('package', type=Path); recover.add_argument('--destination', type=Path, required=True)
    source = sub.add_parser('extract-code'); source.add_argument('package', type=Path); source.add_argument('--destination', type=Path, required=True)
    inspect = sub.add_parser('serve-restored'); inspect.add_argument('destination', type=Path); inspect.add_argument('--code-root', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == 'serve-restored':
            serve_restored(args.destination, args.code_root); return
        if args.action == 'extract-code': result = extract_code(args.package, args.destination)
        elif args.action == 'backup': result = backup(args.root, args.destination)
        elif args.action == 'restore': result = restore(args.package, args.destination)
        else:
            manifest = verify(args.package); result = {'status': 'verified', 'files': len(manifest['files']), 'stores': len(manifest['stores'])}
        print(json.dumps(result))
    except (OSError, ValueError, sqlite3.Error) as exc:
        parser.exit(1, str(exc)+'\n')

if __name__ == '__main__': main()
