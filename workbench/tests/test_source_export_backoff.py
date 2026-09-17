"""An unavailable status probe must back off before the export schedule is reached."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from local_workbench.server import Application
from local_workbench.runtime_status import ObservedAdapter, RuntimeStatus


class SourceExportBackoffTests(unittest.TestCase):
    def test_status_failure_backoff_is_bounded_and_resets_after_recovery(self):
        clock = SimpleNamespace(now=0.)
        waits, probes, exports = [], [], []
        class Stop:
            def wait(self, seconds):
                waits.append(seconds)
                if len(waits) > 10: return True
                clock.now += seconds
                return False
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); config = root/'config.json'
            config.write_text(json.dumps({'governance_db': 'isolated.sqlite'}))
            def call(command, **kwargs):
                if command == 'export_status':
                    probes.append(clock.now)
                    if len(probes) <= 8: raise OSError('Isolated unavailable status probe')
                    return {'status': 'current', 'authority_version': {'revision': 1}}
                self.assertEqual(command, 'confidence_export')
                exports.append(clock.now)
                return {'status': 'current'}
            app = Application.__new__(Application)
            app.stop = Stop()
            with patch('local_workbench.server.time.monotonic', side_effect=lambda: clock.now):
                app.monitor = RuntimeStatus(root)
                app.adapter = ObservedAdapter(SimpleNamespace(config=config, call=call), app.monitor, 1)
                app.refresh_confidence()
            self.assertEqual(len(probes), 10)
            self.assertEqual(waits[:4], [5, 10, 20, 40])
            self.assertGreater(waits[7], waits[3])
            self.assertLessEqual(max(waits), 60)
            self.assertEqual(waits[5:9], [max(waits)]*4)
            self.assertEqual(waits[-2:], [5, 5])
            self.assertEqual(len(exports), 1)  # Recovery allows the scheduled export, then respects its interval.
            self.assertGreater(exports[0], probes[7])
            row = app.monitor.components['source_excel']
            self.assertEqual(row['failures'], 0)
            self.assertIsNone(row['error'])
            self.assertIsNotNone(row['last_error'])
            self.assertEqual(row['retry_seconds'], 0)
