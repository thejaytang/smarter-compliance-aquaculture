"""Persisted preview-version boundaries in disposable stores; owner calls are fakes."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import json
import unittest
import uuid

from local_workbench.collaboration import Collaboration, body, fingerprint, source_review
from local_workbench.collaboration_merge import merge_documents

COORDINATOR = 'Weijie Tang'
REVIEWER = 'Ana Jokic'


def uid():
    return str(uuid.uuid4())


class PersistedMergeVersionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = {'source_id': 'TS-VERSION', 'source_revision': 's1', 'content_hash': 'original-hash'}
        self.base = {'id': 'material', 'revision': 1, 'content_revision': 1,
                     'source': {'source_id': 'TS-VERSION', 'snapshot_id': 'v1', 'content_hash': 'original-hash'},
                     'blocks': [{'id': 'heading', 'type': 'heading', 'level': 1, 'text': 'Conditions'},
                                {'id': 'body', 'type': 'text', 'text': 'Original text'},
                                {'id': 'table', 'type': 'table', 'table': {'rows': [['1', '2']], 'merges': []}}],
                     'issues': []}
        self.current = deepcopy(self.base)
        self.current.update(revision=2, content_revision=2)
        self.current['blocks'][1]['text'] = 'Preserve my exact human correction'
        self.incoming = deepcopy(self.base)
        self.incoming['blocks'][1]['text'] = 'Machine or colleague wording'
        self.incoming['blocks'][2]['table']['rows'] = [['New table shape'], ['Second row']]
        self.incoming['blocks'] = [self.incoming['blocks'][2], *self.incoming['blocks'][:2]]
        self.owner_calls = []
        self.candidate = {'id': 'candidate', 'status': 'ready', 'input_revision': 1,
                          'complete': True, 'base_blocks': deepcopy(self.base['blocks']),
                          'blocks': deepcopy(self.incoming['blocks'])}
        self.app = SimpleNamespace(runtime=self.root,
                                   system2=SimpleNamespace(runtime=self.root/'system2', call=self.owner))
        self.c = self.reopen()
        self.baseline = {'source': deepcopy(self.source), 'material': deepcopy(self.base)}
        self.submission = {'id': uid(), 'actor': REVIEWER, 'source_id': self.source['source_id'],
                           'material_id': self.base['id'], 'base': deepcopy(self.baseline),
                           'base_digest': fingerprint(self.baseline), 'material': deepcopy(self.incoming),
                           'source_review': source_review(self.source), 'status': 'pending'}
        self.c.put('baseline', self.submission['base_digest'], self.baseline)
        self.c.put('submission', self.submission['id'], self.submission)

    def tearDown(self):
        self.temporary.cleanup()

    def reopen(self):
        c = Collaboration(self.app)
        c.source = lambda _: deepcopy(self.source)
        c.source_issues = lambda _: []
        c.personal_adapter = lambda *_: SimpleNamespace(call=self.owner)
        c.annotate = lambda _, material, *args: deepcopy(material)
        return c

    def owner(self, command, **kwargs):
        if command == 'material_read':
            return deepcopy(self.current)
        if command == 'material_candidate':
            return deepcopy(self.candidate)
        if command in ('material_adopt-master', 'material_adopt'):
            request = deepcopy(kwargs['request'])
            self.owner_calls.append((command, request))
            material = deepcopy(self.current)
            material.update(blocks=request['blocks'], issues=request['issues'], revision=3)
            return {'status': 'applied', 'material': material}
        raise AssertionError('Unexpected owner command: '+command)

    def journal(self):
        with self.c.db() as db:
            return db.execute('SELECT kind,key,data FROM collaboration_objects ORDER BY kind,key').fetchall()

    def legacy_merge(self):
        return {'id': uid(), 'actor': COORDINATOR, 'submission_id': self.submission['id'],
                'source_id': self.source['source_id'], 'material_id': self.base['id'],
                'current_material': deepcopy(self.current), 'current_source': deepcopy(self.source),
                'master_digest': fingerprint(self.current), 'source_digest': fingerprint(self.source),
                'decisions': {}, 'status': 'preview', 'at': '2026-09-13T00:00:00Z'}

    def choices(self, preview):
        by_path = {d['path']: d for d in preview['differences']}
        self.assertEqual(by_path['/blocks']['kind'], 'order')
        self.assertEqual(by_path['/blocks']['incoming'], ['table', 'heading', 'body'])
        self.assertIn('/blocks/body/text', by_path)
        self.assertIn('/blocks/table/table', by_path)
        return {d['id']: {'action': 'current' if path == '/blocks/body/text' else 'incoming'}
                for path, d in by_path.items()}

    def check_combined(self, material):
        self.assertEqual([b['id'] for b in material['blocks']], ['table', 'heading', 'body'])
        by_id = {b['id']: b for b in material['blocks']}
        self.assertEqual(by_id['body']['text'], self.current['blocks'][1]['text'])
        self.assertEqual(by_id['table']['table'], self.incoming['blocks'][0]['table'])

    def test_missing_version_reuses_legacy_full_block_decision_after_restart_and_adopts_v1(self):
        documents = [{**body(m), 'source_review': source_review(self.source)}
                     for m in (self.base, self.current, self.incoming)]
        legacy = merge_documents(*documents)
        structural = next(d for d in legacy['differences'] if d['path'] == '/blocks')
        self.assertEqual(structural['kind'], 'structure')
        merge = self.legacy_merge()
        merge['decisions'] = {structural['id']: {'action': 'incoming'}}
        self.c.put('merge', merge['id'], merge)
        journal = self.journal()
        self.c = self.reopen()
        preview = self.c.preview(COORDINATOR, {'submission_id': self.submission['id']})
        self.assertEqual(preview['merge_id'], merge['id'])
        self.assertEqual(preview['material']['blocks'], self.incoming['blocks'])
        self.assertEqual(self.journal(), journal)
        self.assertNotIn('merge_version', self.c.get('merge', merge['id']))
        receipt = self.c.adopt(COORDINATOR, {'merge_id': merge['id'], 'request_id': uid()})
        self.assertEqual(receipt['status'], 'adopted')
        self.assertEqual(self.owner_calls[0][1]['blocks'], self.incoming['blocks'])
        self.assertEqual(self.c.get('merge', merge['id'])['decisions'], merge['decisions'])

    def test_new_coordinator_version_separates_order_manual_text_and_table_before_adoption(self):
        original = deepcopy(self.submission)
        preview = self.c.preview(COORDINATOR, {'submission_id': self.submission['id']})
        self.assertEqual(self.c.get('merge', preview['merge_id'])['merge_version'], 2)
        resolved = self.c.resolve(COORDINATOR, {'merge_id': preview['merge_id'], 'decisions': self.choices(preview)})
        self.check_combined(resolved['material'])
        self.c = self.reopen()
        repeated = self.c.preview(COORDINATOR, {'submission_id': self.submission['id']})
        self.check_combined(repeated['material'])
        self.assertEqual(repeated['merge_id'], preview['merge_id'])
        self.assertEqual(self.c.get('submission', self.submission['id']), original)
        self.c.adopt(COORDINATOR, {'merge_id': preview['merge_id'], 'request_id': uid()})
        self.check_combined({'blocks': self.owner_calls[0][1]['blocks']})
        self.assertEqual(self.owner_calls[0][0], 'material_adopt-master')

    def test_new_machine_version_preserves_explicit_content_decision_when_order_changes(self):
        candidate_before = deepcopy(self.candidate)
        preview = self.c.machine_preview(REVIEWER, {'material_id': self.base['id'], 'candidate_id': self.candidate['id']})
        self.assertEqual(self.c.get('merge', preview['merge_id'])['merge_version'], 2)
        decisions = self.choices(preview)
        resolved = self.c.machine_resolve(REVIEWER, {'merge_id': preview['merge_id'], 'decisions': decisions})
        self.check_combined(resolved['material'])
        self.c = self.reopen()
        self.check_combined(self.c.merge_view(self.c.get('merge', preview['merge_id']))['material'])
        result = self.c.machine_apply(REVIEWER, {'merge_id': preview['merge_id'], 'request_id': uid(), 'reviewed_against_source': True})
        self.assertEqual(result['status'], 'applied')
        self.check_combined({'blocks': self.owner_calls[0][1]['blocks']})
        self.assertEqual(self.owner_calls[0][0], 'material_adopt')
        self.assertEqual(self.candidate, candidate_before)

    def test_invalid_order_edits_never_change_coordinator_or_machine_journals(self):
        for machine in (False, True):
            preview = self.c.machine_preview(REVIEWER, {'material_id': 'material', 'candidate_id': 'candidate'}) if machine else self.c.preview(COORDINATOR, {'submission_id': self.submission['id']})
            order = next(d for d in preview['differences'] if d['path'] == '/blocks')
            self.assertEqual(order['kind'], 'order')
            resolve = self.c.machine_resolve if machine else self.c.resolve
            actor = REVIEWER if machine else COORDINATOR
            before = self.journal()
            for value in (['heading', 'body', 'body'], ['heading', 'body'], ['heading', 'body', 'table', 'unknown'], deepcopy(self.incoming['blocks']), None):
                with self.subTest(machine=machine, value=value):
                    with self.assertRaises(ValueError):
                        resolve(actor, {'merge_id': preview['merge_id'], 'decisions': {order['id']: {'action': 'edit', 'value': value}}})
                    self.assertEqual(self.journal(), before)
            self.assertEqual(self.owner_calls, [])

    def test_changed_identity_set_keeps_whole_structure_fallback_in_versioned_preview(self):
        self.submission['material']['blocks'][0]['id'] = 'split-table'
        self.c.put('submission', self.submission['id'], self.submission)
        preview = self.c.preview(COORDINATOR, {'submission_id': self.submission['id']})
        self.assertEqual(self.c.get('merge', preview['merge_id'])['merge_version'], 2)
        structural = next(d for d in preview['differences'] if d['path'] == '/blocks')
        self.assertEqual(structural['kind'], 'structure')
        self.assertIsInstance(structural['incoming'][0], dict)
        resolved = self.c.resolve(COORDINATOR, {'merge_id': preview['merge_id'], 'decisions': {structural['id']: {'action': 'incoming'}}})
        self.assertEqual(resolved['material']['blocks'], self.submission['material']['blocks'])

    def test_order_edit_cannot_move_unchanged_child_before_parent_or_modify_journal(self):
        for document in (self.base, self.current, self.incoming):
            next(b for b in document['blocks'] if b['id'] == 'body')['parent_id'] = 'heading'
        self.baseline['material'] = deepcopy(self.base)
        self.submission.update(base=deepcopy(self.baseline), base_digest=fingerprint(self.baseline), material=deepcopy(self.incoming))
        self.c.put('baseline', self.submission['base_digest'], self.baseline)
        self.c.put('submission', self.submission['id'], self.submission)
        self.candidate.update(base_blocks=deepcopy(self.base['blocks']), blocks=deepcopy(self.incoming['blocks']))
        for machine in (False, True):
            preview = self.c.machine_preview(REVIEWER, {'material_id': 'material', 'candidate_id': 'candidate'}) if machine else self.c.preview(COORDINATOR, {'submission_id': self.submission['id']})
            self.assertFalse(any(d['path'].endswith('/parent_id') for d in preview['differences']))
            order = next(d for d in preview['differences'] if d['kind'] == 'order')
            before = self.journal()
            resolve = self.c.machine_resolve if machine else self.c.resolve
            with self.assertRaisesRegex(ValueError, 'heading'):
                resolve(REVIEWER if machine else COORDINATOR, {'merge_id': preview['merge_id'], 'decisions': {order['id']: {'action': 'edit', 'value': ['body', 'heading', 'table']}}})
            self.assertEqual(self.journal(), before)

    def test_legacy_machine_apply_keeps_whole_list_choice_without_migrating_version(self):
        preview = self.c.machine_preview(REVIEWER, {'material_id': 'material', 'candidate_id': 'candidate'})
        merge = self.c.get('merge', preview['merge_id'])
        merge.pop('merge_version', None)
        legacy = self.c.merge_view(merge)
        structural = next(d for d in legacy['differences'] if d['path'] == '/blocks')
        merge['decisions'] = {structural['id']: {'action': 'incoming'}}
        self.c.put('merge', merge['id'], merge)
        self.c = self.reopen()
        result = self.c.machine_apply(REVIEWER, {'merge_id': merge['id'], 'request_id': uid(), 'reviewed_against_source': True})
        self.assertEqual(result['material']['blocks'], self.incoming['blocks'])
        self.assertEqual(self.owner_calls[0][1]['blocks'], self.incoming['blocks'])
        self.assertNotIn('merge_version', self.c.get('merge', merge['id']))

    def test_unknown_saved_version_is_rejected_instead_of_reinterpreting_decisions(self):
        merge = self.legacy_merge()
        merge['merge_version'] = 99
        self.c.put('merge', merge['id'], merge)
        before = self.journal()
        with self.assertRaisesRegex(ValueError, 'Unsupported comparison version'):
            self.c.preview(COORDINATOR, {'submission_id': self.submission['id']})
        self.assertEqual(self.journal(), before)
        self.assertEqual(self.owner_calls, [])

    def test_partial_machine_choices_survive_reopen_and_repeat_without_new_journal_rows(self):
        request = {'material_id': 'material', 'candidate_id': 'candidate'}
        preview = self.c.machine_preview(REVIEWER, request)
        text = next(d for d in preview['differences'] if d['path'] == '/blocks/body/text')
        resolved = self.c.machine_resolve(REVIEWER, {'merge_id': preview['merge_id'], 'decisions': {text['id']: {'action': 'current'}}})
        self.assertTrue(resolved['unresolved'])
        self.assertEqual(len(self.c.get('merge', preview['merge_id'])['decisions']), 1)
        before = self.journal()
        self.c = self.reopen()
        for _ in range(3):
            resumed = self.c.machine_preview(REVIEWER, request)
            self.assertEqual(resumed['merge_id'], preview['merge_id'])
            self.assertEqual(resumed['unresolved'], resolved['unresolved'])
            choice = next(d for d in resumed['differences'] if d['id'] == text['id'])
            self.assertEqual(choice['resolution'], 'current')
            self.assertEqual(self.journal(), before)
        self.assertEqual(len(self.c.all('machine_proposal')), 1)
        self.assertEqual(len(self.c.all('merge')), 1)
        self.assertEqual(self.owner_calls, [])

    def test_concurrent_duplicate_machine_preview_creates_one_proposal_and_merge(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        gate = Barrier(2)
        def preview():
            gate.wait(timeout=5)
            return self.c.machine_preview(REVIEWER, {'material_id': 'material', 'candidate_id': 'candidate'})
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(preview), pool.submit(preview)]
            results = [f.result(timeout=5) for f in futures]
        self.assertEqual(results[0]['merge_id'], results[1]['merge_id'])
        self.assertEqual(results[0], results[1])
        self.assertEqual(len(self.c.all('machine_proposal')), 1)
        self.assertEqual(len(self.c.all('merge')), 1)

    def test_changed_material_candidate_or_source_creates_fresh_machine_preview_retaining_old_choices(self):
        request = {'material_id': 'material', 'candidate_id': 'candidate'}
        first = self.c.machine_preview(REVIEWER, request)
        text = next(d for d in first['differences'] if d['path'] == '/blocks/body/text')
        self.c.machine_resolve(REVIEWER, {'merge_id': first['merge_id'], 'decisions': {text['id']: {'action': 'current'}}})
        saved = self.c.get('merge', first['merge_id'])
        original = deepcopy((self.current, self.candidate, self.source))
        previous_count = len(self.c.all('merge'))
        for change in ('material', 'candidate', 'source'):
            self.current, self.candidate, self.source = deepcopy(original)
            if change == 'material':
                self.current['revision'] += 1
                self.current['blocks'][1]['text'] = 'New saved human version'
            elif change == 'candidate':
                self.candidate['blocks'][-1]['text'] = 'Different candidate content under same candidate ID'
            else:
                self.source['source_revision'] = 'new-source-revision'
            with self.subTest(change=change):
                fresh = self.c.machine_preview(REVIEWER, request)
                self.assertNotEqual(fresh['merge_id'], first['merge_id'])
                self.assertEqual(self.c.get('merge', fresh['merge_id'])['decisions'], {})
                self.assertEqual(len(self.c.all('merge')), previous_count + 1)
                self.assertEqual(self.c.get('merge', first['merge_id']), saved)
                repeated = self.c.machine_preview(REVIEWER, request)
                self.assertEqual(repeated['merge_id'], fresh['merge_id'])
                previous_count += 1
        self.assertEqual(len(self.c.all('machine_proposal')), 4)

    def test_repeat_machine_preview_reuses_historical_versionless_full_list_choice(self):
        request = {'material_id': 'material', 'candidate_id': 'candidate'}
        first = self.c.machine_preview(REVIEWER, request)
        old = self.c.get('merge', first['merge_id'])
        old.pop('merge_version')
        legacy = self.c.merge_view(old)
        structural = next(d for d in legacy['differences'] if d['path'] == '/blocks')
        old['decisions'] = {structural['id']: {'action': 'incoming'}}
        self.c.put('merge', old['id'], old)
        before = self.journal()
        self.c = self.reopen()
        resumed = self.c.machine_preview(REVIEWER, request)
        self.assertEqual(resumed['merge_id'], old['id'])
        self.assertEqual(resumed['merge_version'], 1)
        self.assertEqual(resumed['material']['blocks'], self.incoming['blocks'])
        self.assertNotIn('merge_version', self.c.get('merge', old['id']))
        self.assertEqual(self.journal(), before)

    def test_later_empty_duplicate_never_shadows_saved_v1_or_v2_machine_choices(self):
        for version in (1, 2):
            self.candidate['id'] = 'candidate-version-' + str(version)
            request = {'material_id': 'material', 'candidate_id': self.candidate['id']}
            first = self.c.machine_preview(REVIEWER, request)
            saved = self.c.get('merge', first['merge_id'])
            if version == 1:
                saved.pop('merge_version')
                first = self.c.merge_view(saved)
                difference = next(d for d in first['differences'] if d['path'] == '/blocks')
            else:
                difference = next(d for d in first['differences'] if d['path'] == '/blocks/body/text')
            saved['decisions'] = {difference['id']: {'action': 'current'}}
            self.c.put('merge', saved['id'], saved)
            expected = self.c.merge_view(saved)
            # Reproduce the earlier program's later, empty duplicate and its distinct proposal.
            later = deepcopy(saved)
            later.update(id=uid(), submission_id=uid(), decisions={}, at='2026-09-14T00:00:00Z')
            proposal = deepcopy(self.c.get('machine_proposal', saved['submission_id']))
            proposal['id'] = later['submission_id']
            self.c.put('machine_proposal', proposal['id'], proposal)
            self.c.put('merge', later['id'], later)
            before = self.journal()
            self.c = self.reopen()
            resumed = self.c.machine_preview(REVIEWER, request)
            self.assertEqual(resumed['merge_id'], saved['id'])
            self.assertEqual(resumed['merge_version'], version)
            self.assertEqual(resumed['material'], expected['material'])
            self.assertEqual(resumed['unresolved'], expected['unresolved'])
            self.assertEqual(self.journal(), before)
            self.assertEqual(self.c.get('merge', later['id'])['decisions'], {})
            self.assertEqual(self.c.get('merge', saved['id']), saved)
