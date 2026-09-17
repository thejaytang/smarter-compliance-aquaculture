"""Scheduler reads must preserve queue recovery and branch isolation."""
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest

from backend.shared.material_activity import material_activity
from backend.shared.workspace_storage import alias
from local_workbench.collaboration import Collaboration


class MaterialActivityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.runtime = self.root / 'material branch #1'
        self.runtime.mkdir()
        self.database = self.runtime / 'workflow.sqlite'
        with sqlite3.connect(self.database) as db:
            db.execute('CREATE TABLE material_candidates(id TEXT PRIMARY KEY, data TEXT)')
        self.calls = []
        self.scheduler = object.__new__(Collaboration)
        self.scheduler.all = lambda kind: [{'id': 'isolated'}]
        self.scheduler.workspace_runtime = lambda workspace: self.runtime
        self.scheduler.adapter = lambda runtime: SimpleNamespace(call=self.call)

    def candidate(self, state, identity='candidate-1'):
        with sqlite3.connect(self.database) as db:
            db.execute('INSERT OR REPLACE INTO material_candidates VALUES(?,?)',
                       (identity, json.dumps({'id': identity, 'status': state})))

    def call(self, command, **kwargs):
        self.calls.append(command)
        return {'status': 'idle'}

    def test_empty_and_finished_queues_launch_no_component_process(self):
        for status in (None, 'kept', 'adopted', 'merged', 'failed'):
            if status:
                self.candidate(status)
            before = self.database.read_bytes()
            for _ in range(4):
                self.assertEqual(self.scheduler.tick(), {'status': 'idle'})
            self.assertEqual(self.calls, [])
            self.assertEqual(self.database.read_bytes(), before)

    def test_submission_after_idle_is_discovered_without_restart(self):
        self.scheduler.tick()
        self.candidate('running')
        self.scheduler.tick()
        self.assertEqual(self.calls, ['material_tick'])
        # A restarted scheduler reads the durable queue rather than a memory flag.
        self.calls.clear()
        self.scheduler.tick()
        self.assertEqual(self.calls, ['material_tick'])

    def test_ready_partial_resolution_does_not_start_parser(self):
        for status in ('ready', 'partial'):
            self.calls.clear()
            self.candidate(status)
            self.scheduler.tick()
            self.assertEqual(self.calls, ['material_repeat-resolution'])

    def test_new_candidate_result_is_resolved_in_same_tick(self):
        self.candidate('running')
        def call(command, **kwargs):
            self.calls.append(command)
            if command == 'material_tick':
                self.candidate('ready')
                return {'status': 'candidate_available', 'candidate': {'id': 'candidate-1'}}
            return {'status': 'idle'}
        self.scheduler.adapter = lambda runtime: SimpleNamespace(call=call)
        self.assertEqual(self.scheduler.tick()['candidate']['id'], 'candidate-1')
        self.assertEqual(self.calls, ['material_tick', 'material_repeat-resolution'])

    def test_busy_worker_keeps_durable_work_pending(self):
        self.candidate('running')
        self.scheduler.adapter = lambda runtime: SimpleNamespace(call=lambda *a, **k: {'status': 'busy'})
        self.assertEqual(self.scheduler.tick(), {'status': 'idle'})
        self.assertTrue(material_activity(self.runtime)['extract'])

    def test_missing_or_old_store_is_unknown_and_never_created_by_probe(self):
        absent = self.root / 'absent'
        self.assertFalse(material_activity(absent)['known'])
        self.assertFalse(absent.exists())
        with sqlite3.connect(self.database) as db:
            db.execute('DROP TABLE material_candidates')
        self.assertFalse(material_activity(self.runtime)['known'])
        self.scheduler.tick()
        self.assertEqual(self.calls, ['material_tick', 'material_repeat-resolution'])

    def test_corrupt_database_and_json_are_errors_not_idle(self):
        with sqlite3.connect(self.database) as db:
            db.execute("INSERT INTO material_candidates VALUES('bad','not-json')")
        with self.assertRaises(sqlite3.DatabaseError):
            self.scheduler.tick()
        self.assertFalse(self.calls)
        self.database.write_bytes(b'not a SQLite database')
        with self.assertRaises(sqlite3.DatabaseError):
            material_activity(self.runtime)

    def test_routed_branch_is_read_only_and_isolated(self):
        physical = self.root / '四库 %23.sqlite'
        with sqlite3.connect(physical) as db:
            for prefix in ('', 'branch_a__', 'branch_b__'):
                db.execute(f'CREATE TABLE {prefix}material_candidates(id TEXT, data TEXT)')
            db.execute('INSERT INTO branch_b__material_candidates VALUES(?,?)',
                       ('other', json.dumps({'status': 'running'})))
        branch = self.root / 'branch 名称 # %'
        alias(branch, 'workflow.sqlite', physical, 'branch_a__')
        before = physical.read_bytes()
        self.assertEqual(material_activity(branch), {'known': True, 'extract': False, 'resolve': False})
        self.assertEqual(physical.read_bytes(), before)
        self.assertFalse((branch / 'workflow.sqlite').exists())
        with sqlite3.connect(physical) as db:
            db.execute('INSERT INTO branch_a__material_candidates VALUES(?,?)',
                       ('own', json.dumps({'status': 'partial'})))
        self.assertEqual(material_activity(branch), {'known': True, 'extract': False, 'resolve': True})


if __name__ == '__main__':
    unittest.main()
