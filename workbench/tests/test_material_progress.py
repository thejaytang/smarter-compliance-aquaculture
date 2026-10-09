"""Completion must bind all saved panes without changing their source revisions."""
from copy import deepcopy
from types import MethodType, SimpleNamespace
import unittest
import uuid
from unittest.mock import patch

import test_interpretations as fixture
from local_workbench.collaboration import Collaboration
from local_workbench.material_progress import MaterialProgress, STAGES


class MaterialProgressTests(unittest.TestCase):
    tearDown = fixture.InterpretationTests.tearDown
    fields = fixture.InterpretationTests.fields
    request = fixture.InterpretationTests.request
    step = fixture.InterpretationTests.step

    def setUp(self):
        fixture.InterpretationTests.setUp(self)
        self.c.app.peer_sync = True
        self.c.read_material = lambda a, i, view='personal': deepcopy(self.material)
        self.c.object_table = lambda kind: 'collaboration_objects'
        with self.c.db() as db:
            db.execute('CREATE TABLE collaboration_objects(kind TEXT,key TEXT,data TEXT,PRIMARY KEY(kind,key))')
        for method in ('get', 'put', 'put_many', 'all', 'claim_request'):
            setattr(self.c, method, MethodType(getattr(Collaboration, method), self.c))
        self.material.update(title='Synthetic fixture', scope=[dict(id='page:1')], checked_scope=['page:1'], association_review_required=False, issues=[])
        self.step('assign', field='Subject', start=0, end=48)
        request = self.request()
        for field in request['fields'].values():
            field.update(state='not_stated', absence_reason='Not explicitly stated in the reviewed passage.')
        request['approve_cards'] = {key: None for key in ('scope', 'condition', 'demand')}
        self.s.save(fixture.ACTOR, request)
        self.progress = MaterialProgress(self.c)

    def decision(self, stage, complete=True):
        state = self.progress.inspect(fixture.ACTOR, self.material['id'])
        return dict(material_id=self.material['id'], expected_revision=state['revision'],
                    expected_progress=state['version'],
                    stage=stage, signature=state['stages'][stage]['signature'], complete=complete, request_id=str(uuid.uuid4()))

    def complete_all(self):
        for stage in STAGES:
            self.progress.confirm(fixture.ACTOR, self.decision(stage))

    def test_all_three_required_and_completion_does_not_stale_interpretation(self):
        before = self.s.read(fixture.ACTOR, self.uid)
        with self.assertRaisesRegex(ValueError, 'bottom'):
            self.progress.require_complete(fixture.ACTOR, self.material['id'])
        self.complete_all()
        state = self.progress.inspect(fixture.ACTOR, self.material['id'])
        self.assertTrue(state['archive_ready'])
        self.assertEqual(state['completed'], 3)
        after = self.s.read(fixture.ACTOR, self.uid)
        self.assertEqual(before['revision'], after['revision'])
        self.assertEqual(before['context']['fingerprint'], after['context']['fingerprint'])
        self.assertFalse(after['stale'])

    def test_hidden_requirement_edit_invalidates_downstream_only(self):
        self.complete_all()
        self.step('assign', field='Object', start=0, end=48)
        state = self.progress.inspect(fixture.ACTOR, self.material['id'])
        self.assertTrue(state['stages']['content']['complete'])
        self.assertFalse(state['stages']['requirements']['complete'])
        self.assertFalse(state['stages']['interpretation']['complete'])

    def test_reopen_preserves_history_and_requires_downstream_confirmation(self):
        self.complete_all()
        self.progress.confirm(fixture.ACTOR, self.decision('requirements', False))
        state = self.progress.inspect(fixture.ACTOR, self.material['id'])
        self.assertEqual(state['completed'], 1)
        self.assertEqual(len(self.c.all('material_progress_confirmation')), 5)

    def test_idempotent_replay_and_changed_request_rejected(self):
        request = self.decision('content')
        first = self.progress.confirm(fixture.ACTOR, request)
        self.assertEqual(self.progress.confirm(fixture.ACTOR, request), first)
        self.assertEqual(len(self.c.all('material_progress_confirmation')), 1)
        with self.assertRaises(ValueError):
            self.progress.confirm(fixture.ACTOR, dict(request, complete=False))

    def test_stale_signature_and_incomplete_hidden_interpretation_rejected(self):
        request = self.decision('requirements')
        self.step('assign', field='Object', start=0, end=48)
        self.assertEqual(self.progress.confirm(fixture.ACTOR, request)['status'], 'conflict')
        with self.assertRaises(ValueError):
            self.progress.confirm(fixture.ACTOR, self.decision('interpretation'))

    def test_interrupted_journal_write_retries_without_duplicate_confirmation(self):
        request = self.decision('content')
        with patch.object(self.c, 'put_many', side_effect=OSError('interrupted')):
            with self.assertRaises(OSError):
                self.progress.confirm(fixture.ACTOR, request)
        self.assertEqual(self.c.all('material_progress_confirmation'), [])
        self.progress.confirm(fixture.ACTOR, request)
        self.assertEqual(len(self.c.all('material_progress_confirmation')), 1)

    def test_concurrent_completion_decisions_conflict_without_changing_material(self):
        old = self.decision('requirements')
        self.progress.confirm(fixture.ACTOR, self.decision('content'))
        self.assertEqual(self.progress.confirm(fixture.ACTOR, old)['status'], 'conflict')
        self.assertEqual(self.material['revision'], 1)

    def test_archive_guard_frozen_progress_and_response_replay(self):
        from local_workbench.peer_review import confirm
        self.material['title'] = 'Synthetic fixture'
        base = deepcopy(self.material)
        writes = []
        def personal(command, **kwargs):
            if command == 'material_reader':
                return {}
            if command == 'material_read':
                return deepcopy(self.material)
            if command == 'material_confirm':
                writes.append(command)
                self.material['revision'] += 1
                self.material['content_status'] = 'content_review_complete'
                self.material['confirmation'] = {'actor': fixture.ACTOR}
                return dict(status='applied', material=deepcopy(self.material))
            if command == 'material_export':
                return dict(material=deepcopy(self.material), original={'path': 'synthetic-original'})
            self.fail(command)
        def shared(command, **kwargs):
            if command == 'material_read':
                return deepcopy(base)
            if command == 'material_sync':
                writes.append(command)
                return dict(status='applied', material=dict(self.material, revision=9))
            self.fail(command)
        self.c.personal_adapter = lambda *args: SimpleNamespace(call=personal)
        self.c.app.system2 = SimpleNamespace(call=shared)
        self.c.workspace = lambda *args: {'base_material': base}
        self.c.annotate = lambda actor, material: material
        request = dict(request_id=str(uuid.uuid4()), material_id=self.material['id'], expected_revision=1, explicit_confirmation=True)
        with self.assertRaisesRegex(ValueError, 'bottom'):
            confirm(self.c, fixture.ACTOR, request)
        self.assertEqual(writes, [])
        self.complete_all()
        result = confirm(self.c, fixture.ACTOR, request)
        self.assertEqual(confirm(self.c, fixture.ACTOR, request), result)
        self.assertEqual(writes, ['material_confirm', 'material_sync'])
        with patch('local_workbench.material_queue.MaterialQueue.read_archive', return_value=dict(self.material, revision=9)):
            state = self.progress.inspect(fixture.ACTOR, self.material['id'], 'archive', 9)
        self.assertTrue(state['historical'])
        self.assertEqual(state['completed'], 3)

    def test_imported_confirmation_is_validated_and_never_survives_changed_content(self):
        from local_workbench.material_progress import validate_confirmation
        self.complete_all()
        records = self.c.all('material_progress_confirmation')
        for record in records:
            validate_confirmation(record)
            self.c.put('sync_shared_record', record['id'], dict(key='history:material_progress_confirmation:'+record['id'], value=record))
        with self.assertRaises(ValueError):
            validate_confirmation(dict(records[0], actor='Nobody'))
        self.material['blocks'][0]['text'] += ' Changed.'
        state = self.progress.inspect(fixture.ACTOR, self.material['id'])
        self.assertEqual(state['completed'], 0)
