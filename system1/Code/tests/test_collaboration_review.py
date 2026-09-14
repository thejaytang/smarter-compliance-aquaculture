import copy
import hashlib
import json
import unittest
import uuid
from unittest.mock import patch
from test_operator_journeys import OperatorJourneyTests
import human_operations as h
import source_updater as u
from system1 import workbench_bridge as bridge
from system1.collaboration_review import collaboration_apply, review_document
from system1.governance_store import GovernanceStore


class CollaborationReviewTests(unittest.TestCase):
    setUp = OperatorJourneyTests.setUp
    tearDown = OperatorJourneyTests.tearDown
    _build_workbook = OperatorJourneyTests._build_workbook

    def activate(self):
        cfg = u.read_config(self.config_path)
        wb = u.open_registry(cfg)
        u.save_workbook_atomic(wb, self.workbook, u.workbook_mtime(self.workbook));wb.close()
        store = GovernanceStore.migrate(cfg, self.runtime/'governance/state.sqlite')
        raw = json.loads(self.config_path.read_text());raw['governance_db'] = str(store.path)
        self.config_path.write_text(json.dumps(raw))
        return store

    def source(self):
        return bridge.read(self.config_path)['sources'][0]

    def request(self, **review):
        source = self.source()
        base = review_document(source)
        proposed = copy.deepcopy(base);proposed.update(review)
        return {'request_id': str(uuid.uuid4()), 'actor': 'Weijie Tang', 'source_id': 'PA001',
                'expected_source_revision': source['source_revision'], 'base_review': base,
                'expected_source_hash': source['content_hash'],
                'review': proposed, 'submission_id': str(uuid.uuid4()), 'contributor': 'Ana Jokic'}

    def apply(self, request):
        with patch('source_updater.run_updates', side_effect=AssertionError('No network/downloads')):
            return collaboration_apply(self.config_path, request)

    def test_completed_source_re_review_appends_history_without_replaying_old_decision(self):
        first = self.apply(self.request(note='Earlier direct coordinator review.'))
        store = self.activate()
        before = store.snapshot()
        original = (self.authority/self.current_name).read_bytes()
        request = self.request(note='Ana reviewed the revised issuer spelling.')
        request['review']['fields']['issuer'] = 'Verified government issuer'
        result = self.apply(request)
        self.assertEqual(result['status'], 'applied')
        self.assertEqual(self.source()['issuer'], 'Verified government issuer')
        after = store.snapshot()
        self.assertEqual(after['operations'][0], before['operations'][0])
        self.assertEqual(len(after['operations']), len(before['operations'])+1)
        self.assertEqual(after['operations'][-1]['record']['operator'], 'Weijie Tang')
        payload = h.parse_payload(after['operations'][-1]['record']['payload_json'])
        self.assertEqual(payload['collaboration_receipt']['contributor'], 'Ana Jokic')
        self.assertNotEqual(first['operation_id'], result['operation_id'])
        with store.connect() as db:
            history = db.execute('SELECT * FROM history WHERE revision=?', (after['state']['revision'],)).fetchall()
        self.assertEqual({r['entity'] for r in history}, {'sources', 'operations'})
        self.assertEqual({r['actor'] for r in history}, {'Weijie Tang'})
        self.assertEqual((self.authority/self.current_name).read_bytes(), original)

    def test_partial_scores_are_staged_as_a_bundle_without_mixing_main_scores(self):
        self.activate()
        request = self.request(note='Only two scores reviewed so far.')
        request['review']['scores'] = {k: '' for k in u.SCORE_FIELDS}
        request['review']['scores']['authority_quality'] = 'LOW'
        request['review']['selection'] = 'EXCLUDE'
        result = self.apply(request)
        self.assertEqual(result['status'], 'saved_partial')
        self.assertEqual(self.source()['operator_selection_decision'], 'INCLUDE')
        self.assertEqual(self.source()['authority_quality'], 'HIGH')
        self.assertIn(request['review']['note'], self.source()['notes'])
        task = next(t for t in bridge.read(self.config_path)['tasks'] if t['operation_id']==result['operation_id'])
        self.assertEqual(h.parse_payload(task['payload_json'])['adopted_review']['scores'], request['review']['scores'])
        self.assertEqual(task['decision'], 'PENDING')

    def test_score_selection_conflict_is_rejected_without_any_write(self):
        store = self.activate();before = store.snapshot()
        request = self.request(note='Contradictory review must fail.')
        request['review']['scores']['scope_relevance'] = 'LOW'
        with self.assertRaisesRegex(ValueError, 'five-HIGH'): self.apply(request)
        self.assertEqual(store.snapshot(), before)

    def test_durable_replay_precedes_stale_guard_and_id_reuse_rejected(self):
        store = self.activate();request = self.request(note='Committed once.')
        receipt = self.apply(request)
        later = self.request(note='Subsequent review.')
        later['review']['fields']['version'] = 'v2'
        self.apply(later);before = store.snapshot()
        self.assertEqual(self.apply(request), receipt)
        self.assertEqual(store.snapshot(), before)
        altered = copy.deepcopy(request);altered['review']['note'] = 'Different input'
        with self.assertRaisesRegex(ValueError, 'identity'): self.apply(altered)
        altered['request_id'] = str(uuid.uuid4())
        with self.assertRaisesRegex(ValueError, 'STALE'): self.apply(altered)
        self.assertEqual(store.snapshot(), before)

    def test_false_baseline_and_non_coordinator_rejected(self):
        request = self.request();request['base_review']['fields']['issuer'] = 'Different'
        with self.assertRaisesRegex(ValueError, 'baseline'): self.apply(request)
        request = self.request();request['actor'] = 'Ana Jokic'
        with self.assertRaisesRegex(ValueError, 'coordinator'): self.apply(request)

    def issue(self):
        cfg = u.read_config(self.config_path);wb = u.open_registry(cfg)
        ops = wb[h.HUMAN_SHEET];headers = h.operation_headers(ops)
        h.append_operation(ops, headers, {'operation_id': 'ISSUE-1', 'operation_type': 'SOURCE_REVIEW',
            'source_id': 'PA001', 'decision': 'PENDING', 'operator': 'Daniel Restad',
            'program_status': 'WAITING_FOR_HUMAN', 'payload_json': json.dumps({
                'human_reported_issue': {'reason': 'Original heading differs', 'action': 'Verify original', 'evidence_id': 'e1'}})})
        u.save_registry(wb, cfg, u.registry_revision(cfg));wb.close()

    def test_note_only_keeps_issue_until_explicit_verification_and_preserves_old_actor(self):
        self.issue();store = self.activate()
        receipt = self.apply(self.request(note='Formatting note only.'))
        self.assertEqual(receipt['status'], 'saved_partial')
        self.assertEqual(len(h.pending_human_reported_issues(self.config_path)), 1)
        with self.assertRaisesRegex(ValueError, 'requires a note'):
            self.apply(self.request(issue_verified=True))
        legacy = self.apply(self.request(note='Legacy general confirmation.', issue_verified=True))
        self.assertEqual(legacy['status'],'saved_partial')
        self.assertEqual(len(h.pending_human_reported_issues(self.config_path)),1)
        issue=next(t for t in bridge.read(self.config_path)['tasks'] if t['operation_id']=='ISSUE-1')['human_issue']
        digest=hashlib.sha256(json.dumps(issue,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
        verified = self.apply(self.request(selection='INCLUDE', note='Compared heading against registered original.', issue_checks={'ISSUE-1:'+digest:digest}))
        self.assertEqual(verified['status'], 'applied')
        self.assertEqual(h.pending_human_reported_issues(self.config_path), [])
        old = next(t for t in bridge.read(self.config_path)['history'] if t['operation_id']=='ISSUE-1')
        self.assertEqual(old['operator'], 'Daniel Restad')
        self.assertEqual(old['decision'], 'PENDING')
        with store.connect() as db:
            changes = db.execute("SELECT before_data,after_data FROM history WHERE entity='operations' AND entity_id='ISSUE-1' AND before_data IS NOT NULL").fetchall()
        self.assertEqual(len(changes), 1)
        self.assertIsNotNone(changes[0]['before_data'])

    def test_complete_scores_do_not_bypass_acquisition_gate(self):
        cfg = u.read_config(self.config_path);wb = u.open_registry(cfg)
        ws = wb[cfg['sheet_name']];sh = u.workbook_headers(ws, 2)
        ws.cell(3, sh['download_status']).value = 'PAYWALL_BLOCKED'
        ws.cell(3, sh['snapshot_status']).value = 'NOT_COLLECTED'
        u.save_registry(wb, cfg, u.registry_revision(cfg));wb.close()
        self.activate()
        result = self.apply(self.request(selection='INCLUDE', note='Scoring complete; original still absent.'))
        self.assertEqual(result['status'], 'saved_partial')
        self.assertEqual(result['effective_selection'], 'PENDING')
        self.assertTrue(any('PAYWALL' in reason for reason in result['unresolved_reasons']))

    def test_save_failure_does_not_persist_source_or_receipt(self):
        store = self.activate();before = store.snapshot()
        request = self.request(note='Crash before authority commit.')
        with patch('source_updater.save_registry', side_effect=OSError('Injected save failure')):
            with self.assertRaises(OSError): self.apply(request)
        self.assertEqual(store.snapshot(), before)
        self.assertEqual(self.apply(request)['status'], 'applied')

    def test_original_hash_change_rejects_even_when_manual_revision_is_unchanged(self):
        store = self.activate();request = self.request(note='Reviewed old original.')
        cfg = u.read_config(self.config_path);wb = u.open_registry(cfg)
        ws = wb[cfg['sheet_name']];sh = u.workbook_headers(ws, 2)
        from hashlib import sha256
        newer = b'Updated isolated original for source version guard'
        (self.authority/'PA001-002_New.html').write_bytes(newer)
        ws.cell(3, sh['content_hash']).value = sha256(newer).hexdigest()
        ws.cell(3, sh['snapshot_id']).value = 'PA001-002'
        ws.cell(3, sh['stored_filename']).value = 'PA001-002_New.html'
        u.save_registry(wb, cfg, u.registry_revision(cfg));wb.close()
        self.assertEqual(self.source()['source_revision'], request['expected_source_revision'])
        before = store.snapshot()
        with self.assertRaisesRegex(ValueError, 'original changed'): self.apply(request)
        self.assertEqual(store.snapshot(), before)


del OperatorJourneyTests
