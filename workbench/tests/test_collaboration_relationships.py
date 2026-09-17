from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from local_workbench.collaboration import Collaboration, source_review
from backend.shared.collaboration_merge import merge_documents
from backend.shared.collaboration_relationships import display_context, validate_decisions


def document(title='Measurements', parent=None, dependencies=None):
    return {'blocks': [{'id': 'heading', 'type': 'heading', 'level': 1, 'text': title},
                       {'id': 'body', 'type': 'text', 'text': 'Recorded value', 'parent_id': parent,
                        'dependencies': dependencies or []}], 'issues': []}


class RelationshipTests(unittest.TestCase):
    def test_exact_side_labels_do_not_use_merged_heading_name(self):
        base = document('Old title', 'heading')
        current = document('Current title')
        incoming = document('<Candidate title>', 'heading')
        before = deepcopy((base, current, incoming))
        result = merge_documents(base, current, incoming)
        context = display_context(base, current, incoming, result['differences'])
        self.assertEqual(context['base']['heading']['text'], 'Old title')
        self.assertEqual(context['current']['heading']['text'], 'Current title')
        self.assertEqual(context['incoming']['heading']['text'], '<Candidate title>')
        self.assertNotIn('body', context['incoming'])
        self.assertEqual((base, current, incoming), before)

    def test_missing_side_target_is_not_borrowed_from_another_side(self):
        base = document(parent='heading'); current = document(); current['blocks'].pop(0)
        incoming = document('New title', parent='heading')
        differences = [{'path': '/blocks/body/parent_id', 'base': 'heading', 'current': None, 'incoming': 'heading'}]
        context = display_context(base, current, incoming, differences)
        self.assertNotIn('heading', context['current'])
        self.assertIn('heading', context['incoming'])

    def test_explicit_missing_parent_rejected_without_repairing_blocks(self):
        base = document(); incoming = document(parent='gone')
        first = merge_documents(base, base, incoming); diff = first['differences'][0]
        decisions = {diff['id']: {'action': 'incoming'}}
        result = merge_documents(base, base, incoming, decisions)
        before = deepcopy(result)
        with self.assertRaisesRegex(ValueError, 'selected heading is not in the combined content'):
            validate_decisions(result['differences'], decisions, result['merged']['blocks'])
        self.assertEqual(result, before)
        validate_decisions(first['differences'], {}, first['merged']['blocks'])

    def test_parent_position_type_level_and_dependency_cycle_guards(self):
        for kind, value in [('parent_id', 'body'), ('dependencies', ['gone']), ('dependencies', ['body'])]:
            base = document(); incoming = deepcopy(base); incoming['blocks'][1][kind] = value
            first = merge_documents(base, base, incoming); diff = first['differences'][0]
            decisions = {diff['id']: {'action': 'incoming'}}; result = merge_documents(base, base, incoming, decisions)
            with self.assertRaises(ValueError): validate_decisions(result['differences'], decisions, result['merged']['blocks'])
        base = document(); base['blocks'][0]['dependencies'] = ['body']
        incoming = deepcopy(base); incoming['blocks'][1]['dependencies'] = ['heading']
        first = merge_documents(base, base, incoming); diff = first['differences'][0]
        decisions = {diff['id']: {'action': 'incoming'}}; result = merge_documents(base, base, incoming, decisions)
        with self.assertRaisesRegex(ValueError, 'circular'): validate_decisions(result['differences'], decisions, result['merged']['blocks'])
        relation = {'id': 'parent-choice', 'path': '/blocks/body/parent_id'}
        selected = {'parent-choice': {'action': 'incoming'}}
        later = document(parent='heading')['blocks'][::-1]
        with self.assertRaisesRegex(ValueError, 'appears before'):
            validate_decisions([relation], selected, later)
        peers = document(parent='heading')['blocks']; peers[1].update(type='heading', level=1)
        with self.assertRaisesRegex(ValueError, 'hierarchy level'):
            validate_decisions([relation], selected, peers)

    def test_valid_selected_ids_and_unrelated_values_remain_exact(self):
        base = document(); incoming = document(parent='heading', dependencies=['heading'])
        incoming['blocks'][1]['confidence'] = 0.75
        first = merge_documents(base, base, incoming)
        decisions = {diff['id']: {'action': 'incoming'} for diff in first['differences']}
        result = merge_documents(base, base, incoming, decisions)
        validate_decisions(result['differences'], decisions, result['merged']['blocks'])
        self.assertEqual(result['merged'], incoming)

    def test_real_preview_resolve_preserves_journal_on_missing_target(self):
        with TemporaryDirectory() as directory:
            collaboration = Collaboration(SimpleNamespace(runtime=Path(directory)))
            source = {'source_id': 'TS002'}
            current = dict(document('Current title'), id='material', revision=3)
            proposed = dict(document('Candidate title', 'heading'), id='material', revision=3)
            incoming = {'id': 'proposal', 'actor': 'Ana Jokic', 'base': {'material': current, 'source': source},
                        'material': proposed, 'source_review': source_review(source)}
            merge = {'id': 'merge', 'actor': 'Weijie Tang', 'status': 'preview', 'submission_id': 'proposal',
                     'current_material': current, 'current_source': source, 'master_digest': 'fixed',
                     'source_id': 'TS002', 'decisions': {}}
            collaboration.put('submission', 'proposal', incoming); collaboration.put('merge', 'merge', merge)
            preview = collaboration.merge_view(merge)
            self.assertEqual(preview['reference_context']['current']['heading']['text'], 'Current title')
            self.assertEqual(preview['reference_context']['incoming']['heading']['text'], 'Candidate title')
            diff = next(d for d in preview['differences'] if d['path'].endswith('/parent_id'))
            with self.assertRaisesRegex(ValueError, 'not in the combined content'):
                collaboration.resolve('Weijie Tang', {'merge_id': 'merge', 'decisions': {diff['id']: {'action': 'edit', 'value': 'gone'}}})
            self.assertEqual(collaboration.get('merge', 'merge')['decisions'], {})
            result = collaboration.resolve('Weijie Tang', {'merge_id': 'merge', 'decisions': {diff['id']: {'action': 'edit', 'value': 'heading'}}})
            self.assertEqual(result['material']['blocks'][1]['parent_id'], 'heading')
            self.assertEqual(collaboration.get('submission', 'proposal'), incoming)
            self.assertEqual(collaboration.get('merge', 'merge')['current_material'], current)

    def test_real_machine_preview_rejects_missing_target_without_recording_a_choice(self):
        with TemporaryDirectory() as directory:
            collaboration = Collaboration(SimpleNamespace(runtime=Path(directory)))
            source = {'source_id': 'TS002'}; current = dict(document(), id='material', revision=3)
            incoming = {'id': 'candidate', 'actor': 'Ana Jokic', 'base': {'material': current, 'source': source},
                        'material': dict(document(parent='gone'), id='material', revision=3), 'source_review': source_review(source)}
            merge = {'id': 'merge', 'kind': 'machine', 'candidate_id': 'candidate', 'actor': 'Ana Jokic',
                     'status': 'preview', 'submission_id': 'candidate', 'current_material': current,
                     'current_source': source, 'master_digest': 'fixed', 'source_id': 'TS002', 'decisions': {}}
            collaboration.put('machine_proposal', 'candidate', incoming); collaboration.put('merge', 'merge', merge)
            preview = collaboration.merge_view(merge)
            diff = next(d for d in preview['differences'] if d['path'].endswith('/parent_id'))
            self.assertIn(diff['id'], preview['unresolved'])
            with self.assertRaisesRegex(ValueError, 'not in the combined content'):
                collaboration.machine_resolve('Ana Jokic', {'merge_id': 'merge', 'decisions': {diff['id']: {'action': 'incoming'}}})
            self.assertEqual(collaboration.get('merge', 'merge')['decisions'], {})
            # Earlier saved invalid choices must stay readable so a person can repair them.
            historical = deepcopy(merge); historical['decisions'] = {diff['id']: {'action': 'incoming'}}
            self.assertEqual(collaboration.merge_view(historical)['material']['blocks'][1]['parent_id'], 'gone')
            repaired = collaboration.machine_resolve('Ana Jokic', {'merge_id': 'merge', 'decisions': {diff['id']: {'action': 'edit', 'value': None}}})
            self.assertIsNone(repaired['material']['blocks'][1]['parent_id'])
            self.assertEqual(collaboration.get('machine_proposal', 'candidate'), incoming)


if __name__ == '__main__': unittest.main()
