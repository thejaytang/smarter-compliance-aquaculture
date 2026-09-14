"""Controllable-clock weekly dispatch on isolated persisted archive projections."""
from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import patch
import unittest
import tempfile
from pathlib import Path
import test_material_queue as fixtures
A, B = fixtures.A, fixtures.B
from local_workbench.collaboration import Collaboration
from local_workbench.material_inspection_schedule import MaterialInspectionSchedule

class MaterialInspectionScheduleTests(unittest.TestCase):
    setUp = fixtures.MaterialQueueTests.setUp
    tearDown = fixtures.MaterialQueueTests.tearDown
    db = fixtures.MaterialQueueTests.db
    write = fixtures.MaterialQueueTests.write

    def settings(self):
        return {'enabled': True, 'timezone': 'Europe/Oslo', 'sample_size': 5, 'assignee': B}

    def clock(self):
        return datetime(2026, 9, 13, 22, 30, tzinfo=timezone.utc)  # Monday in Oslo

    def test_disabled_has_no_tasks_or_batches_and_reviewer_cannot_enable(self):
        schedule = MaterialInspectionSchedule(self.c)
        with patch.object(schedule.queue, 'archives', side_effect=AssertionError('Disabled schedule must not read archive')):
            self.assertEqual(schedule.run_due()['status'], 'disabled')
        self.assertEqual(self.c.all('material_inspection_batch'), [])
        self.c.mode = 'reviewer'
        with self.assertRaises(ValueError):schedule.run_due(self.settings(), self.clock)
        self.assertEqual(self.q.tasks(), [])

    def test_week_boundary_restart_dedup_full_scope_and_archive_preservation(self):
        before = self.app.system2.call('material_read', material_id=self.material['id'])
        batch = MaterialInspectionSchedule(self.c).run_due(self.settings(), self.clock)
        self.assertEqual(batch['iso_week'], '2026-W38')
        self.assertEqual(batch['selected_count'], 1)
        self.assertEqual(batch['requested_count'], 5)
        task = self.q.tasks()[0]
        self.assertEqual(task['archive_revision'], 2)
        self.assertEqual(task['scope'], ['page:1', 'page:2'])
        self.assertEqual(task['source_hash'], before['source']['content_hash'])
        self.assertEqual(self.q.listing(A, 'pending')['total'], 1)
        self.assertEqual(self.q.listing(A, 'archive')['total'], 1)
        restored = Collaboration(self.app)
        self.assertEqual(MaterialInspectionSchedule(restored).run_due(self.settings(), self.clock), batch)
        self.assertEqual(len(self.q.tasks()), 1)
        self.assertEqual(self.app.system2.call('material_read', material_id=self.material['id']), before)

    def test_interrupted_after_create_recovers_receipt_without_duplicate(self):
        schedule = MaterialInspectionSchedule(self.c)
        create = schedule.queue.create
        def crash(*args, **kwargs):
            create(*args, **kwargs)
            raise RuntimeError('Simulated interruption after durable task receipt')
        with patch.object(schedule.queue, 'create', side_effect=crash):
            with self.assertRaises(RuntimeError):schedule.run_due(self.settings(), self.clock)
        self.assertEqual(len(self.q.tasks()), 1)
        result = MaterialInspectionSchedule(Collaboration(self.app)).run_due(self.settings(), self.clock)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(len(self.q.tasks()), 1)

    def test_new_week_skips_open_task_and_never_catches_up_old_weeks(self):
        first = MaterialInspectionSchedule(self.c).run_due(self.settings(), self.clock)
        later = lambda: datetime(2026, 10, 5, 8, tzinfo=timezone.utc)
        second = MaterialInspectionSchedule(self.c).run_due(self.settings(), later)
        self.assertEqual(second['items'][0]['status'], 'already_pending')
        self.assertEqual(len(self.q.tasks()), 1)
        self.assertEqual(len(self.c.all('material_inspection_batch')), 2)
        self.assertNotEqual(first['id'], second['id'])

    def test_interrupted_frozen_plan_never_silently_switches_archive_revision(self):
        schedule = MaterialInspectionSchedule(self.c)
        with patch.object(schedule.queue, 'create', side_effect=RuntimeError('Before task creation')):
            with self.assertRaises(RuntimeError):schedule.run_due(self.settings(), self.clock)
        newer = deepcopy(self.material)
        newer.update(revision=4, content_revision=2, confirmation={'actor': A, 'content_revision': 2})
        self.write(newer)
        result = MaterialInspectionSchedule(Collaboration(self.app)).run_due(self.settings(), self.clock)
        self.assertEqual(result['items'][0]['archive_revision'], 2)
        self.assertEqual(result['items'][0]['status'], 'skipped')
        self.assertEqual(self.q.tasks(), [])

    def test_empty_week_is_durable_and_configuration_is_explicit(self):
        with self.db() as db:db.execute('DELETE FROM material_revision_index')
        schedule = MaterialInspectionSchedule(self.c)
        for settings in ({'enabled': True}, dict(self.settings(), sample_size=True)):
            with self.assertRaises(ValueError):schedule.run_due(settings, self.clock)
        with self.assertRaises(ValueError):schedule.run_due(self.settings(), lambda: datetime(2026, 9, 14))
        empty = schedule.run_due(self.settings(), self.clock)
        self.assertEqual(empty['selected_count'], 0)
        self.write(dict(self.material, revision=3))
        self.assertEqual(MaterialInspectionSchedule(Collaboration(self.app)).run_due(self.settings(), self.clock), empty)
        self.assertEqual(self.q.tasks(), [])

    def test_unchanged_pass_preserves_archive_then_next_week_can_sample_new_finalization(self):
        import uuid
        schedule = MaterialInspectionSchedule(self.c)
        before = self.app.system2.call('material_read', material_id=self.material['id'])
        schedule.run_due(self.settings(), self.clock)
        task = self.q.tasks()[0]
        self.q.save(B, {'request_id': str(uuid.uuid4()), 'task_id': task['id'],
            'material_id': task['material_id'], 'expected_revision': 0, 'action': 'pass',
            'checked_scope': task['scope'], 'note': 'Unchanged original checked in isolated test.', 'explicit_confirmation': True})
        self.assertEqual(self.q.listing(A, 'pending')['total'], 0)
        self.assertEqual(self.app.system2.call('material_read', material_id=self.material['id']), before)
        newer = deepcopy(self.material)
        newer.update(revision=4, content_revision=2, confirmation={'actor': A, 'content_revision': 2})
        self.write(newer)
        schedule.run_due(self.settings(), lambda: datetime(2026, 9, 21, 8, tzinfo=timezone.utc))
        tasks = self.q.tasks()
        self.assertEqual(sorted(t['archive_revision'] for t in tasks), [2, 4])
        self.assertEqual(self.app.system2.call('material_read', material_id=self.material['id'], revision=2), before)

class WorkerDispatchTests(unittest.TestCase):
    def test_worker_defaults_to_disabled_and_reviewer_does_not_dispatch(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from local_workbench.server import Application
        with tempfile.TemporaryDirectory() as directory:
            app=SimpleNamespace(reviewer=False,runtime=Path(directory),collaboration=object())
            with patch('local_workbench.material_inspection_schedule.MaterialInspectionSchedule') as schedule:
                Application.dispatch_material_inspections(app)
                schedule.return_value.run_due.assert_called_once_with({})
                Application.dispatch_material_inspections(app)
                schedule.return_value.run_due.assert_called_once()
                app.reviewer=True;app.material_inspection_next=0
                Application.dispatch_material_inspections(app)
                schedule.return_value.run_due.assert_called_once()
