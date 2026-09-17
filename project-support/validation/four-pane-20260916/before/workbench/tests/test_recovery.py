from local_workbench.sqlite_support import connect as connect_sqlite
from local_workbench.platform_support import exclusive_lock
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from local_workbench.recovery import backup, restore, verify, digest, extract_code, source_inventory, SOURCE_REQUIRED

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'project'; self.root.mkdir()
        self.package = Path(self.temp.name)/'package'
        for relative in SOURCE_REQUIRED:
            path = self.root/relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('Isolated dependency fixture')
        code = self.root/'workbench/src/example.py'; code.parent.mkdir(parents=True); code.write_text('VALUE = 7\n')
        for relative in ('.env', 'workbench/.venv/secret.py', 'workbench/src/__pycache__/secret.py', 'system2/config/model-provider.json'):
            path = self.root/relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('excluded secret sentinel')
        config = self.root/'system1/Code/config/config.json'; config.parent.mkdir(parents=True)
        config.write_text(json.dumps(dict(governance_db='../runtime/governance.sqlite', log_root='../runtime/logs',
            source_root='../../Data', workbook='../../Requirement_Source_Registry.xlsx')))
        self.stores = ['system1/Code/runtime/governance.sqlite','system1/Code/runtime/logs/source-assessments.sqlite',
            'system2/runtime/workflow/workflow.sqlite','system2/runtime/jobs.sqlite3','workbench/runtime/workbench.sqlite',
            'system1/Code/runtime/logs/leader_state.sqlite']
        for rel in self.stores:
            path = self.root/rel; path.parent.mkdir(parents=True, exist_ok=True)
            with connect_sqlite(path) as db:
                db.execute('CREATE TABLE history (id INTEGER PRIMARY KEY, body TEXT)')
                db.execute('INSERT INTO history VALUES (1, ?)', (json.dumps({'human_text': 'Isolated engineering history'}),))
        for rel in ['system1/Code/runtime/governance-migration-input.xlsx','system1/Requirement_Source_Registry.xlsx','system1/Data/original.html']:
            path = self.root/rel; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('isolated original bytes')
        canonical = self.root/'system2/runtime/workflow/artifacts/a/canonical.json'; canonical.parent.mkdir(parents=True); canonical.write_text('{}')
        with connect_sqlite(self.root/self.stores[2]) as db:
            db.execute('CREATE TABLE documents(data TEXT)'); db.execute('INSERT INTO documents VALUES (?)', (json.dumps({'canonical': [{'path': str(canonical), 'sha256': digest(canonical)}]}),))
    def test_copy_verify_restore_history_and_original_without_live_files(self):
        result = backup(self.root, self.package); self.assertEqual(result['stores'], 6)
        manifest = verify(self.package)
        self.root.rename(self.root.with_name('source-offline'))
        restored = Path(self.temp.name)/'restored'; restore(self.package, restored)
        for rel, record in manifest['files'].items(): self.assertEqual(digest(restored/rel), record['sha256'])
        self.assertEqual(json.loads((restored/'recovery-mapping.json').read_text())['database_rewritten'], False)
        with self.assertRaises(ValueError): restore(self.package, restored)
    def test_running_service_and_busy_database_refuse_before_package(self):
        marker = self.root/'workbench/runtime/server.json'; marker.write_text(json.dumps({'pid': os.getpid()}))
        with self.assertRaisesRegex(ValueError, 'Stop the workbench'): backup(self.root, self.package)
        self.assertFalse(self.package.exists()); marker.unlink()
        with connect_sqlite(self.root/self.stores[2]) as db:
            db.execute('BEGIN IMMEDIATE')
            with self.assertRaisesRegex(ValueError, 'database is busy'): backup(self.root, self.package)
        self.assertFalse(self.package.exists())
    def test_busy_process_lock_and_corrupt_package_rejected(self):
        lock = self.root/'workbench/runtime/service.lock'
        with exclusive_lock(lock):
            with self.assertRaisesRegex(ValueError, 'writer is active'): backup(self.root, self.package)
        backup(self.root, self.package)
        (self.package/'files/system1/Data/original.html').write_text('corruption')
        with self.assertRaisesRegex(ValueError, 'verification failed'): restore(self.package, Path(self.temp.name)/'restore')
        self.assertFalse((Path(self.temp.name)/'restore').exists())
    def test_insufficient_space_stops_before_creating_package(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        with patch('local_workbench.recovery.shutil.disk_usage',return_value=SimpleNamespace(free=0)):
            with self.assertRaisesRegex(ValueError,'Insufficient free space'):
                backup(self.root,self.package)
        self.assertFalse(self.package.exists())

    def test_pdf_vendor_binary_assets_and_licenses_are_recoverable(self):
        assets = ['cmaps/78-EUC-H.bcmap', 'wasm/qcms_bg.wasm', 'standard_fonts/font.ttf', 'LICENSE']
        for name in assets:
            path = self.root/'workbench/ui/vendor/pdfjs'/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'bounded vendor fixture')
        paths = source_inventory(self.root)
        for name in assets:
            self.assertIn(self.root/'workbench/ui/vendor/pdfjs'/name, paths)

    def test_missing_bound_reference_and_manifest_escape_rejected(self):
        (self.root/'system2/runtime/workflow/artifacts/a/canonical.json').unlink()
        with self.assertRaisesRegex(ValueError, 'Canonical'): backup(self.root, self.package)

    def test_exact_source_snapshot_survives_source_loss_and_rejects_tampering(self):
        backup(self.root, self.package)
        manifest = verify(self.package)
        self.assertEqual(manifest['format'], 'workbench-recovery-v2')
        self.assertIn('ENVIRONMENT.md', manifest['code_files'])
        self.assertIn('system2/uv.lock', manifest['code_files'])
        self.assertNotIn('system2/config/model-provider.json', manifest['code_files'])
        self.assertFalse(any('.venv' in name or '__pycache__' in name or name=='.env' for name in manifest['code_files']))
        self.root.rename(self.root.with_name('source-lost'))
        matching = Path(self.temp.name)/'matching-code'; extract_code(self.package, matching)
        self.assertEqual((matching/'workbench/src/example.py').read_text(), 'VALUE = 7\n')
        with self.assertRaises(ValueError): extract_code(self.package, matching)
        (self.package/'code/workbench/src/example.py').write_text('VALUE = 8\n')
        with self.assertRaisesRegex(ValueError, 'source snapshot verification failed'): verify(self.package)
        with self.assertRaisesRegex(ValueError, 'source snapshot verification failed'): restore(self.package, Path(self.temp.name)/'blocked-restore')
        self.assertFalse((Path(self.temp.name)/'blocked-restore').exists())

    def test_leader_store_is_a_locked_snapshot_and_jobs_store_is_optional(self):
        leader = self.root/'system1/Code/runtime/logs/leader_state.sqlite'
        with connect_sqlite(leader) as db:
            db.execute('BEGIN IMMEDIATE')
            with self.assertRaisesRegex(ValueError, 'database is busy'): backup(self.root, self.package)
        self.assertFalse(self.package.exists())
        # Removing a purpose-built empty engineering jobs fixture models an installation without that optional service.
        (self.root/'system2/runtime/jobs.sqlite3').unlink()
        result = backup(self.root, self.package)
        self.assertEqual(result['stores'], 5)
        manifest = verify(self.package)
        self.assertIn('system1/Code/runtime/logs/leader_state.sqlite', manifest['stores'])
        self.assertNotIn('system2/runtime/jobs.sqlite3', manifest['stores'])

    def test_wal_store_verification_never_creates_sidecars_in_package(self):
        live = sqlite3.connect(self.root/'system2/runtime/workflow/workflow.sqlite')
        self.addCleanup(live.close)
        with live as db:
            self.assertEqual(db.execute('PRAGMA journal_mode=WAL').fetchone()[0], 'wal')
            db.execute('INSERT INTO history VALUES (2, ?)', ('Saved WAL-mode history',))
        wal = self.root/'system2/runtime/workflow/workflow.sqlite-wal'
        self.assertTrue(wal.is_file())
        self.assertGreater(wal.stat().st_size, 0)
        # Keep the committed WAL connection live until verification finishes.
        backup(self.root, self.package)
        before = {str(path.relative_to(self.package)): digest(path) for path in self.package.rglob('*') if path.is_file()}
        for _ in range(3): verify(self.package)
        after = {str(path.relative_to(self.package)): digest(path) for path in self.package.rglob('*') if path.is_file()}
        self.assertEqual(before, after)
        self.assertFalse(any(path.endswith(('-wal', '-shm')) for path in after))
        restored = Path(self.temp.name)/'restored-wal'; restore(self.package, restored)
        with closing(connect_sqlite((restored/'system2/runtime/workflow/workflow.sqlite').as_uri()+'?mode=ro&immutable=1', uri=True)) as db:
            self.assertEqual(db.execute('SELECT body FROM history WHERE id=2').fetchone()[0], 'Saved WAL-mode history')

    def test_personal_collaboration_store_and_assets_are_consistent_snapshots(self):
        personal = self.root/'workbench/runtime/collaboration/personal/actor-uuid'
        personal.mkdir(parents=True)
        database = personal/'workflow.sqlite'
        with closing(connect_sqlite(database)) as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE human_history(body TEXT)')
            db.execute('INSERT INTO human_history VALUES (?)', ('工程审核 ø',)); db.commit()
            self.assertGreater(Path(str(database)+'-wal').stat().st_size, 0)
            (personal/'offline-source.json').write_text('{}')
            asset = personal/'material-originals/pinned.html'; asset.parent.mkdir(); asset.write_text('isolated original')
            with exclusive_lock(personal/'.material-worker.lock'):
                with self.assertRaisesRegex(ValueError, 'writer is active'): backup(self.root, self.package)
            db.execute('BEGIN IMMEDIATE')
            with self.assertRaisesRegex(ValueError, 'database is busy'): backup(self.root, self.package)
            db.rollback()
            result = backup(self.root, self.package)
        self.assertEqual(result['stores'], 7)
        manifest = verify(self.package)
        relative = database.relative_to(self.root).as_posix()
        self.assertIn(relative, manifest['stores'])
        self.assertIn(asset.relative_to(self.root).as_posix(), manifest['files'])
        with closing(connect_sqlite((self.package/'files'/relative).as_uri()+'?immutable=1', uri=True)) as snapshot:
            self.assertEqual(snapshot.execute('SELECT body FROM human_history').fetchone()[0], '工程审核 ø')

    def test_restored_personal_runtime_rebases_without_rewriting_historical_paths(self):
        from types import SimpleNamespace
        from local_workbench.collaboration import Collaboration
        identity='10000000-0000-4000-8000-000000000001'
        personal=self.root/'workbench/runtime/collaboration/personal'/identity
        personal.mkdir(parents=True)
        with closing(connect_sqlite(personal/'workflow.sqlite')) as db:
            db.execute('CREATE TABLE history(text TEXT)');db.execute('INSERT INTO history VALUES (?)',('preserved reviewer text',));db.commit()
        app=SimpleNamespace(runtime=self.root/'workbench/runtime')
        collaboration=Collaboration(app)
        original={'id':identity,'runtime':str(personal),'actor':'Ana Jokic','material_id':'fixture'}
        collaboration.put('workspace','Ana Jokic:fixture',original)
        backup(self.root,self.package)
        restored=Path(self.temp.name)/'restored-personal';restore(self.package,restored)
        self.root.rename(self.root.with_name('unavailable-original'))
        reopened=Collaboration(SimpleNamespace(runtime=restored/'workbench/runtime'))
        record=reopened.get('workspace','Ana Jokic:fixture')
        self.assertEqual(record,original)
        actual=reopened.workspace_runtime(record)
        self.assertEqual(actual,(restored/'workbench/runtime/collaboration/personal'/identity).resolve())
        self.assertTrue((actual/'workflow.sqlite').is_file())
        self.assertFalse(Path(record['runtime']).exists())
        with closing(connect_sqlite((actual/'workflow.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
            self.assertEqual(db.execute('SELECT text FROM history').fetchone()[0],'preserved reviewer text')

    def test_hash_reads_only_advertised_length_without_an_extra_eof_read(self):
        from unittest.mock import patch
        from contextlib import nullcontext
        from types import SimpleNamespace
        import hashlib
        payload=b'protected content';path=self.root/'bounded.bin';path.write_bytes(payload)
        calls=[]
        with path.open('rb') as real:
            def bounded(size):
                calls.append(size)
                self.assertEqual(size,len(payload))
                if len(calls)>1:raise AssertionError('Unexpected EOF read')
                return payload
            proxy=SimpleNamespace(fileno=real.fileno,read=bounded)
            with patch.object(Path,'open',return_value=nullcontext(proxy)):
                self.assertEqual(digest(path),hashlib.sha256(payload).hexdigest())
        self.assertEqual(calls,[len(payload)])

    def test_truncated_read_cannot_become_empty_fingerprint(self):
        from unittest.mock import patch
        from contextlib import nullcontext
        path = self.root/'resource.bin'; path.write_bytes(b'protected content')
        from types import SimpleNamespace
        with path.open('rb') as real:
            truncated=SimpleNamespace(fileno=real.fileno,read=lambda *args:b'')
            with patch.object(Path,'open',return_value=nullcontext(truncated)):
                with self.assertRaisesRegex(OSError,'Incomplete'): digest(path)
        import hashlib
        self.assertEqual(digest(path),hashlib.sha256(b'protected content').hexdigest())

    def test_empty_resource_uses_valid_empty_hash(self):
        from unittest.mock import patch
        import hashlib
        path=self.root/'empty.bin'; path.write_bytes(b'')
        self.assertEqual(digest(path),hashlib.sha256(b'').hexdigest())

    def test_resource_size_change_during_hash_is_rejected(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        path=self.root/'size.bin'; path.write_bytes(b'content')
        with patch('local_workbench.recovery.os.fstat',side_effect=[SimpleNamespace(st_size=7),SimpleNamespace(st_size=8)]):
            with self.assertRaisesRegex(OSError,'size changed'):digest(path)

    def test_timestamp_only_change_is_not_a_content_change(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        import hashlib
        path=self.root/'time.bin'; path.write_bytes(b'content')
        with patch('local_workbench.recovery.os.fstat',side_effect=[SimpleNamespace(st_size=7,st_mtime_ns=1),SimpleNamespace(st_size=7,st_mtime_ns=2)]):
            self.assertEqual(digest(path),hashlib.sha256(b'content').hexdigest())
