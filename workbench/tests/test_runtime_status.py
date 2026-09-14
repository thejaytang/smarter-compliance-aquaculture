import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from local_workbench.runtime_status import RuntimeStatus, ObservedAdapter

class RuntimeStatusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.status = RuntimeStatus(self.root)
    def test_failure_sanitized_persisted_recovered_and_backoff_capped(self):
        secret = 'private material text /confidential/document.pdf secret-key'
        def fail(*args, **kwargs): raise subprocess.TimeoutExpired(secret, 3, output=secret)
        wrapped = ObservedAdapter(SimpleNamespace(call=fail), self.status, 2)
        for _ in range(10):
            with self.assertRaises(subprocess.TimeoutExpired): wrapped.call('material_tick')
        self.assertEqual(self.status.backoff('material', 2), 60)
        self.assertNotIn(secret, self.status.path.read_text()+self.status.log.read_text())
        self.assertEqual(len(self.status.log.read_text().splitlines()), 1)
        restarted = RuntimeStatus(self.root)
        self.assertEqual(restarted.components['material']['last_error']['code'], 'timeout')
        token = self.status.start('material', 'material_tick'); self.status.finish(token)
        self.assertIsNone(self.status.components['material']['error'])
        self.assertIsNotNone(self.status.components['material']['last_error'])
        self.assertEqual(self.status.backoff('material', 2), 2)
        self.assertEqual(len(self.status.log.read_text().splitlines()), 2)
    def test_interrupted_current_task_and_io_evidence_failure_visible(self):
        self.status.start('material', 'material_tick'); self.status._persist(True)
        restarted = RuntimeStatus(self.root)
        self.assertEqual(restarted.components['material']['error']['code'], 'interrupted')
        with patch.object(Path, 'open', side_effect=PermissionError('confidential')):
            token = restarted.start('storage', 'material_save'); restarted.finish(token, OSError('secret'))
        self.assertEqual(restarted.snapshot()['persistence_error']['code'], 'status_write_failed')
        self.assertNotIn('confidential', json.dumps(restarted.snapshot()))
    def test_validation_is_not_infrastructure_failure_and_concurrency_visible(self):
        wrapped = ObservedAdapter(SimpleNamespace(call=lambda *a, **k: (_ for _ in ()).throw(ValueError('heading_level_required'))), self.status, 2)
        with self.assertRaises(ValueError): wrapped.call('material_save')
        self.assertIsNone(self.status.components['storage']['error'])
        first = self.status.start('storage', 'material_save'); second = self.status.start('storage', 'material_read')
        self.status.finish(second)
        self.assertEqual(self.status.components['storage']['state'], 'running')
        self.status.finish(first); self.assertEqual(self.status.components['storage']['state'], 'idle')
    def test_success_heartbeat_does_not_write_each_poll(self):
        with patch.object(self.status.path.__class__, 'replace') as replace:
            for _ in range(10):
                token = self.status.start('material', 'material_tick'); self.status.finish(token)
            self.assertEqual(replace.call_count, 0)

    def test_disabled_offline_component_is_not_a_failure_or_success(self):
        monitor=RuntimeStatus(self.root)
        token=monitor.start('excel','workbook')
        with self.assertRaisesRegex(ValueError,'active'):monitor.disable('excel','Offline reviewer has no master Excel output.')
        monitor.finish(token,OSError('isolated storage failure'))
        previous=monitor.components['excel']['last_error']
        monitor.disable('excel','Offline reviewer has no master Excel output.')
        row=monitor.components['excel']
        self.assertEqual(row['state'],'disabled');self.assertIsNone(row['error'])
        self.assertIsNone(row['last_success']);self.assertEqual(row['last_error'],previous)
        self.assertEqual(row['retry_seconds'],0)
        before=monitor.log.read_bytes()
        monitor.disable('excel','Offline reviewer has no master Excel output.')
        self.assertEqual(monitor.log.read_bytes(),before)
        for key in monitor.components:
            if key!='excel':monitor.finish(monitor.start(key,'isolated_check'))
        self.assertEqual(monitor.snapshot()['status'],'healthy')
