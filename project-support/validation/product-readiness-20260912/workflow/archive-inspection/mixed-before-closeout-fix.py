"""Workload-based owning-service integration; run with the Workbench interpreter.

Every invocation requires a new named fixture. No UI acceptance, production writes,
fixed-duration soak, external send, real business review or Windows claim.
"""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import argparse
import json
from pathlib import Path
import re
import resource
import sqlite3
import subprocess
import sys
import time
import traceback
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'workbench/src'))
sys.path.insert(0, str(ROOT / 'workbench/scripts'))
from local_workbench.collaboration_collection import Collection
from local_workbench.collaboration_exchange import unpack
from local_workbench.material_queue import MaterialQueue
from local_workbench.platform_support import lock_file, unlock_file
import check_offline_collaboration as helpers

ACTOR, A, B = helpers.ACTOR, helpers.A, helpers.B


def now(): return datetime.now(timezone.utc).isoformat()
def uid(): return str(uuid.uuid4())
def digest(value): return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def code_manifest():
    result = {}
    for relative in ('workbench/src', 'workbench/ui', 'system2/src', 'system2/config'):
        for path in (ROOT / relative).rglob('*'):
            if path.is_file() and path.suffix in ('.py', '.js', '.css', '.html', '.yaml', '.json') and '__pycache__' not in path.parts:
                result[str(path.relative_to(ROOT))] = sha256(path.read_bytes()).hexdigest()
    return result


class Workload:
    def __init__(self, name, label, require_stable=False):
        if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,70}', name):
            raise ValueError('Use a short unique run name without path separators.')
        self.report = Path(__file__).resolve().parent / 'runs' / name
        self.fixture = ROOT / 'workbench/runtime/product-readiness-20260912' / ('workload-' + name)
        if self.report.exists() or self.fixture.exists():
            raise ValueError('Preserve previous evidence. Choose a new run name.')
        self.report.mkdir(parents=True)
        self.label, self.require_stable = label, require_stable
        self.started, self.clock = now(), time.monotonic()
        self.harness_hash = sha256(Path(__file__).read_bytes()).hexdigest()
        self.before_code = code_manifest()
        (self.report / 'code-before.json').write_text(json.dumps(self.before_code, indent=2))
        self.operations, self.groups, self.failures = Counter(), [], []
        self.history, self.artifacts = {}, {}
        self.log = (self.report / 'operations.jsonl').open('x')
        self.materials = {}

    def record(self, operation, result=None, elapsed=None, **fields):
        self.operations[operation] += 1
        row = {'at': now(), 'operation': operation, 'elapsed_seconds': elapsed, **fields}
        if isinstance(result, dict):
            row['result_status'] = result.get('status')
            for key in ('id', 'material_id', 'submission_id', 'merge_id', 'request_id', 'revision', 'conflict_id'):
                if result.get(key) is not None: row[key] = result[key]
        self.log.write(json.dumps(row, ensure_ascii=False) + '\n'); self.log.flush()

    def call(self, operation, fn):
        started = time.monotonic()
        result = fn()
        self.record(operation, result, time.monotonic() - started)
        return result

    def group(self, name, fn):
        started = time.monotonic()
        try:
            details = fn() or {}
            row = {'name': name, 'status': 'PASS', 'seconds': time.monotonic() - started, 'details': details}
        except Exception as exc:
            row = {'name': name, 'status': 'FAIL', 'seconds': time.monotonic() - started, 'error': str(exc), 'traceback': traceback.format_exc()}
            self.failures.append(name)
        row['rss_peak_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        self.groups.append(row)
        (self.report / 'groups.json').write_text(json.dumps(self.groups, indent=2))
        print(json.dumps({key: value for key, value in row.items() if key not in ('traceback',)}, ensure_ascii=False), flush=True)

    def capture(self):
        # Read-only integrity snapshots of every previously created revision and parser artifact.
        for path in self.fixture.rglob('workflow.sqlite'):
            if path.is_symlink() or not path.resolve().is_relative_to(self.fixture): continue
            with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
                if not db.execute("SELECT 1 FROM sqlite_master WHERE name='material_revisions'").fetchone(): continue
                for mid, revision, raw in db.execute('SELECT material_id,revision,data FROM material_revisions'):
                    key = (str(path.relative_to(self.fixture)), mid, revision)
                    value = sha256(raw.encode()).hexdigest()
                    if key in self.history: assert self.history[key] == value, ('Historical revision changed', key)
                    self.history[key] = value
        for path in self.fixture.rglob('material-artifacts'):
            if not path.resolve().is_relative_to(self.fixture): continue
            for artifact in path.rglob('*'):
                if not artifact.is_file(): continue
                key = str(artifact.relative_to(self.fixture)); value = sha256(artifact.read_bytes()).hexdigest()
                if key in self.artifacts: assert self.artifacts[key] == value, ('Retained parser artifact changed', key)
                self.artifacts[key] = value

    def build(self):
        builder = "import importlib.util,sys;from pathlib import Path;s=importlib.util.spec_from_file_location('fixture',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.TARGET=Path(sys.argv[2]);m.build()"
        result = subprocess.run([str(ROOT/'system2/.venv/bin/python'), '-c', builder, str(ROOT/'workbench/scripts/material_fixture.py'), str(self.fixture)], capture_output=True, text=True)
        (self.report/'fixture-build.log').write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stderr
        helpers.FIX = self.fixture
        self.main = helpers.app('coordinator')
        self.c = self.main.collaboration
        self.originals = {str(path.relative_to(self.fixture/'Data')): sha256(path.read_bytes()).hexdigest() for path in (self.fixture/'Data').rglob('*') if path.is_file()}
        assert self.main.system2.runtime.resolve().is_relative_to(self.fixture)
        self.record('build_isolated_fixture', source_count=len(self.originals))
        return {'fixture': str(self.fixture), 'source_count': len(self.originals), 'live_business_writes': False}

    def reopen(self):
        self.main = helpers.app('coordinator'); self.c = self.main.collaboration
        self.record('reopen_coordinator_store')

    def read(self, mid): return self.call('read_personal_material', lambda: self.c.read_material(ACTOR, mid))

    def initialize(self, sid):
        m = self.call('open_source', lambda: self.c.material_action(ACTOR, 'open', {'source_id': sid, 'request_id': uid()}))
        self.materials[sid] = m['id']
        master = self.c.read_material(ACTOR, m['id'], view='master'); assert not master['blocks']
        request = {'material_id': m['id'], 'expected_revision': m['revision'], 'request_id': uid()}
        started = self.call('request_extract', lambda: self.c.material_action(ACTOR, 'extract', request))
        replay = self.call('replay_extract_request', lambda: self.c.material_action(ACTOR, 'extract', request))
        assert replay == started
        self.call('run_explicit_worker', self.c.tick)
        m = self.read(m['id']); candidate = next(c for c in m['candidates'] if c['id'] == started['candidate']['id'])
        assert candidate['status'] in ('ready', 'partial'), candidate
        detail = self.c.personal_adapter(ACTOR, m['id']).call('material_candidate', material_id=m['id'], candidate_id=candidate['id'])
        self.record('read_full_candidate', detail)
        assert self.c.read_material(ACTOR, m['id'], view='master')['blocks'] == []
        body = deepcopy(detail['blocks'])
        if not body:
            scope = m['scope'][0]
            body = [{'id': 'manual-empty', 'type': 'text', 'text': 'ENGINEERING ONLY manual recovery fixture', 'source_refs': [{'scope_id': scope['id'], **scope.get('location', {})}]}]
        saved = self.call('save_first_candidate_draft', lambda: self.c.material_action(ACTOR, 'candidate-draft', {'material_id': m['id'], 'expected_revision': m['revision'], 'request_id': uid(), 'candidate_id': candidate['id'], 'blocks': body, 'issues': []}))
        assert saved['status'] == 'applied' and not saved['material']['confirmation']
        self.capture()
        return {'source': sid, 'material_id': m['id'], 'parser_status': candidate.get('extraction', {}).get('parser_status'), 'candidate_status': candidate['status'], 'automatic_quality_claim': False}

    def edited(self, m, text):
        blocks = deepcopy(m['blocks'])
        index = next((i for i, block in enumerate(blocks) if block['type'] == 'text'), None)
        if index is not None: blocks[index]['text'] = text
        elif any(block['type'] == 'table' for block in blocks):
            table = next(block['table'] for block in blocks if block['type'] == 'table')
            table['rows'][0][0] = text
        else:
            scope = m['scope'][0]
            blocks.append({'id': 'engineering-note', 'type': 'text', 'text': text, 'source_refs': [{'scope_id': scope['id'], **scope.get('location', {})}]})
        return blocks

    def adopt(self, preview):
        if preview['unresolved']:
            preview = self.call('resolve_engineering_merge', lambda: self.c.resolve(ACTOR, {'merge_id': preview['merge_id'], 'decisions': {identity: {'action': 'incoming'} for identity in preview['unresolved']}}))
        request = {'merge_id': preview['merge_id'], 'request_id': uid()}
        result = self.call('adopt_engineering_master', lambda: self.c.adopt(ACTOR, request))
        assert result['status'] == 'adopted', result
        replay = self.call('replay_master_adoption', lambda: self.c.adopt(ACTOR, request)); assert replay == result
        assert not result.get('material', {}).get('confirmation')
        return result

    def cycle(self, sid, number):
        mid = self.materials[sid]; m = self.read(mid)
        self.call('read_original', lambda: self.c.personal_adapter(ACTOR, mid).call('material_reader', material_id=mid))
        blocks = self.edited(m, f'ENGINEERING WORKLOAD ONLY {sid} cycle {number}')
        request = {'material_id': mid, 'expected_revision': m['revision'], 'request_id': uid(), 'blocks': blocks, 'issues': m['issues']}
        saved = self.call('save_human_overlay', lambda: self.c.material_action(ACTOR, 'save', request))
        assert saved['status'] == 'applied' and saved['material']['blocks'] == blocks
        replay = self.call('replay_save', lambda: self.c.material_action(ACTOR, 'save', request)); assert replay == saved
        stale = dict(request, request_id=uid(), blocks=self.edited(m, 'ENGINEERING rejected stale write'))
        conflict = self.call('reject_stale_save', lambda: self.c.material_action(ACTOR, 'save', stale))
        assert conflict['status'] == 'conflict' and conflict['material']['blocks'] == blocks
        preparation = {'source_id': sid, 'material_id': mid}
        preview = self.call('prepare_own', lambda: self.c.prepare_own(ACTOR, preparation))
        repeated = self.call('repeat_prepare_own', lambda: self.c.prepare_own(ACTOR, preparation))
        assert (preview['submission_id'], preview['merge_id']) == (repeated['submission_id'], repeated['merge_id'])
        self.reopen()
        resumed = self.call('resume_prepare_own', lambda: self.c.prepare_own(ACTOR, preparation))
        assert (resumed['submission_id'], resumed['merge_id']) == (preview['submission_id'], preview['merge_id'])
        current = self.read(mid); assert current['blocks'] == blocks
        self.adopt(resumed); self.capture()
        return {'source': sid, 'cycle': number, 'saved_revision': saved['material']['revision'], 'conflict_id': conflict['conflict_id'], 'same_preparation_after_reopen': True}

    def machine_order_content_resume(self):
        """One owning-service path: order changes never discard chosen human fields."""
        mid = self.materials['TS001']; m = self.read(mid)
        master_fields = ('id', 'source', 'revision', 'content_revision', 'blocks', 'issues', 'confirmation', 'checked_scope')
        master = self.c.read_material(ACTOR, mid, view='master')
        master_before = {key: deepcopy(master.get(key)) for key in master_fields}
        blocks = deepcopy(m['blocks'])
        text_index = next(i for i, block in enumerate(blocks) if block['type'] == 'text')
        table_index = next(i for i, block in enumerate(blocks) if block['type'] == 'table')
        low, high = sorted((text_index, table_index))
        assert not any(block['type'] == 'heading' for block in blocks[low:high + 1]), 'Fixture needs text and table under the same preceding headings.'
        text_block, table_block = blocks[text_index], blocks[table_index]
        text_block['text'] = 'ENGINEERING ONLY retained human correction: water measured at 14 C.'
        width = len(table_block['table']['rows'][0])
        table_block['table']['rows'].append(['ENGINEERING extra row'] + ['Retained human cells'] * (width - 1))
        blocks[text_index], blocks[table_index] = blocks[table_index], blocks[text_index]
        saved = self.call('save_mixed_order_text_table', lambda: self.c.material_action(ACTOR, 'save',
            {'material_id': mid, 'expected_revision': m['revision'], 'request_id': uid(), 'blocks': blocks, 'issues': m['issues']}))
        assert saved['status'] == 'applied' and saved['material']['blocks'] == blocks
        assert not saved['material'].get('confirmation')
        started = self.call('request_mixed_comparison_extract', lambda: self.c.material_action(ACTOR, 'extract',
            {'material_id': mid, 'expected_revision': saved['material']['revision'], 'request_id': uid()}))
        self.call('run_mixed_comparison_worker', self.c.tick)
        current = self.read(mid)
        candidate_id = started['candidate']['id']
        adapter = self.c.personal_adapter(ACTOR, mid)
        candidate = self.call('read_mixed_comparison_candidate', lambda: adapter.call('material_candidate', material_id=mid, candidate_id=candidate_id))
        assert candidate['status'] in ('ready', 'partial')
        assert current['blocks'] == blocks
        assert {b['id'] for b in candidate['blocks']} == {b['id'] for b in blocks}
        self.capture()
        request = {'material_id': mid, 'candidate_id': candidate_id}
        preview = self.call('preview_mixed_machine_changes', lambda: self.c.machine_preview(ACTOR, request))
        assert preview['merge_version'] == 2
        pointer = lambda identity: identity.replace('~', '~0').replace('/', '~1')
        by_path = {d['path']: d for d in preview['differences']}
        order = by_path['/blocks']
        assert order['kind'] == 'order'
        text_difference = by_path['/blocks/' + pointer(text_block['id']) + '/text']
        table_difference = by_path['/blocks/' + pointer(table_block['id']) + '/table']
        assert {order['id'], text_difference['id'], table_difference['id']} <= set(preview['unresolved'])
        partial = self.call('save_machine_order_choice_only', lambda: self.c.machine_resolve(ACTOR,
            {'merge_id': preview['merge_id'], 'decisions': {order['id']: {'action': 'incoming'}}}))
        assert set(partial['unresolved']) == set(preview['unresolved']) - {order['id']}
        decisions = deepcopy(self.c.get('merge', preview['merge_id'])['decisions'])
        def journal():
            with self.c.db() as db:
                return db.execute('SELECT kind,key,data FROM collaboration_objects ORDER BY kind,key').fetchall()
        journal_before = journal()
        counts_before = (len(self.c.all('machine_proposal')), len(self.c.all('merge')))
        self.reopen()
        for _ in range(2):
            resumed = self.call('resume_saved_machine_order_choice', lambda: self.c.machine_preview(ACTOR, request))
            assert resumed['merge_id'] == preview['merge_id'] and resumed['merge_version'] == 2
            assert set(resumed['unresolved']) == set(partial['unresolved'])
            assert self.c.get('merge', preview['merge_id'])['decisions'] == decisions
            assert (len(self.c.all('machine_proposal')), len(self.c.all('merge'))) == counts_before
            assert journal() == journal_before
        assert self.read(mid)['blocks'] == blocks
        try:
            self.c.machine_resolve(ACTOR, {'merge_id': preview['merge_id'],
                'decisions': {order['id']: {'action': 'edit', 'value': order['incoming'][:-1]}}})
        except ValueError as exc:
            self.record('reject_incomplete_machine_order', error=str(exc))
        else:
            raise AssertionError('Incomplete order unexpectedly accepted.')
        assert journal() == journal_before
        resolved = self.call('keep_human_text_and_table_choices', lambda: self.c.machine_resolve(ACTOR,
            {'merge_id': preview['merge_id'], 'decisions': {identity: {'action': 'current'} for identity in partial['unresolved']}}))
        assert not resolved['unresolved']
        by_id = {b['id']: b for b in blocks}
        expected = [deepcopy(by_id[identity]) for identity in order['incoming']]
        assert resolved['material']['blocks'] == expected
        apply_request = {'merge_id': preview['merge_id'], 'request_id': uid(), 'reviewed_against_source': True}
        applied = self.call('apply_mixed_machine_choices', lambda: self.c.machine_apply(ACTOR, apply_request))
        assert applied['status'] == 'applied' and applied['material']['blocks'] == expected
        replay = self.call('replay_mixed_machine_application', lambda: self.c.machine_apply(ACTOR, apply_request))
        assert replay == applied
        final = self.read(mid)
        assert final['blocks'] == expected and not final.get('confirmation')
        final_master = self.c.read_material(ACTOR, mid, view='master')
        assert {key: final_master.get(key) for key in master_fields} == master_before
        retained_candidate = self.c.personal_adapter(ACTOR, mid).call('material_candidate', material_id=mid, candidate_id=candidate_id)
        for key in ('blocks', 'base_blocks', 'metadata', 'source'):
            assert retained_candidate.get(key) == candidate.get(key)
        self.capture()
        return {'source': 'TS001', 'merge_version': 2, 'merge_id': preview['merge_id'],
            'initial_unresolved': len(preview['unresolved']), 'saved_partial_unresolved': len(partial['unresolved']),
            'resumed_preview_count': 2, 'duplicate_rows_created': 0, 'invalid_order_journal_unchanged': True,
            'mixed_order_text_table_preserved': True, 'application_replay_identical': True,
            'master_unchanged': True, 'personal_confirmation': False}

    def faults(self):
        sid = 'TS001'; mid = self.materials[sid]; m = self.read(mid)
        adapter = self.c.personal_adapter(ACTOR, mid); runtime = adapter.runtime
        assert runtime.resolve().is_relative_to(self.fixture)
        started = self.c.material_action(ACTOR, 'extract', {'material_id': mid, 'expected_revision': m['revision'], 'request_id': uid()})
        self.record('fault_extract_requested', started)
        with (runtime/'.material-worker.lock').open('a+b') as handle:
            lock_file(handle)
            try:
                result = self.call('worker_lock_conflict', lambda: adapter.call('material_tick'))
                assert result['status'] == 'busy', result
            finally: unlock_file(handle)
        abort = "import os,sys;from pdf_extraction.orchestration.material_service import MaterialService;from pdf_extraction.orchestration import material_parser;material_parser.parse_material=lambda *a,**k:os._exit(73);MaterialService(sys.argv[1],sys.argv[2],sys.argv[3]).tick()"
        child = subprocess.run([str(ROOT/'system2/.venv/bin/python'), '-c', abort, str(runtime), str(ROOT/'system1'), str(self.fixture/'config/config.json')], cwd=ROOT/'system2', env={**__import__('os').environ, 'PYTHONPATH': str(ROOT/'system2/src')}, capture_output=True, text=True)
        self.record('abrupt_isolated_worker_exit', exit_code=child.returncode)
        assert child.returncode == 73, child.stderr
        pending = self.read(mid); assert pending['blocks'] == m['blocks'] and next(c for c in pending['candidates'] if c['id'] == started['candidate']['id'])['status'] == 'running'
        self.reopen(); resumed = self.call('resume_interrupted_worker', self.c.tick)
        current = self.read(mid); candidate = next(c for c in current['candidates'] if c['id'] == started['candidate']['id'])
        assert candidate['status'] in ('ready', 'partial') and current['blocks'] == m['blocks']
        kept = self.c.material_action(ACTOR, 'adopt', {'material_id': mid, 'expected_revision': current['revision'], 'request_id': uid(), 'candidate_id': candidate['id'], 'action': 'keep', 'reviewed_against_source': True})
        self.record('keep_human_work_after_retry', kept); current = kept['material']
        database = runtime/'workflow.sqlite'
        with sqlite3.connect(database) as db:
            db.execute("CREATE TRIGGER workload_save_failure BEFORE UPDATE ON material_documents BEGIN SELECT RAISE(ABORT,'ENGINEERING injected save failure'); END")
        failed = False
        try:
            self.c.material_action(ACTOR, 'save', {'material_id': mid, 'expected_revision': current['revision'], 'request_id': uid(), 'blocks': self.edited(current, 'Rejected failed save'), 'issues': current['issues']})
        except ValueError as exc:
            assert 'ENGINEERING injected save failure' in str(exc), str(exc)
            failed = True; self.record('injected_save_failure', error=str(exc))
        finally:
            with sqlite3.connect(database) as db: db.execute('DROP TRIGGER workload_save_failure')
        assert failed
        recovered = self.read(mid); assert recovered['revision'] == current['revision'] and recovered['blocks'] == current['blocks']
        self.capture()
        return {'worker_exit': 73, 'worker_resumed': True, 'lock_conflict': 'busy', 'failed_save_preserved_revision': current['revision']}

    def exchange(self):
        mid = self.materials['TS001']; m = self.c.read_material(ACTOR, mid, view='master')
        self.call('confirm_synthetic_master_for_archive', lambda: self.c.confirm_master(ACTOR, {'material_id': mid, 'expected_revision': m['revision'], 'request_id': uid(), 'explicit_confirmation': True, 'checked_scope': [s['id'] for s in m['scope']], 'association_reviewed': True, 'omissions_checked': True, 'dependencies_checked': True}))
        queue = MaterialQueue(self.c); archive = queue.read_archive(ACTOR, mid)
        task = queue.create(ACTOR, {'material_id': mid, 'archive_revision': archive['revision'], 'scope': [archive['scope'][0]['id']], 'assignee': A, 'reason': 'ENGINEERING ONLY work-package recovery', 'request_id': uid()})['inspection']
        self.record('create_synthetic_archive_check', task)
        reviewers = [(helpers.app('reviewer-ana', True), A), (helpers.app('reviewer-daniel', True), B)]
        exporter = Collection(self.c)
        work_request = {'request_id': uid(), 'kind': 'work', 'items': [{'type': 'source', 'key': sid} for sid in ('TS001','TS002','TS003')] + [{'type': 'inspection', 'key': task['id']}]}
        work, _ = self.call('export_multi_item_work', lambda: exporter.export(ACTOR, work_request))
        assert exporter.export(ACTOR, work_request)[0] == work; self.record('replay_work_export')
        returns = []
        for app, actor in reviewers:
            c = app.collaboration
            imported = self.call('reviewer_import_work', lambda: c.import_package(actor, work))
            assert c.import_package(actor, work)['status'] == 'already_imported'; self.record('replay_work_import')
            personal = c.read_material(actor, mid); blocks = self.edited(personal, actor + ' ENGINEERING parallel edit')
            saved = self.call('reviewer_save_parallel_edit', lambda: c.material_action(actor, 'save', {'material_id': mid, 'expected_revision': personal['revision'], 'request_id': uid(), 'blocks': blocks, 'issues': personal['issues']}))
            items = [{'type':'material','key':mid}]
            if actor == A:
                q = MaterialQueue(c)
                self.call('reviewer_save_partial_inspection', lambda: q.save(actor, {'task_id': task['id'], 'material_id': mid, 'expected_revision': 0, 'request_id': uid(), 'action': 'save', 'checked_scope': [], 'note': 'ENGINEERING partial spot-check, not passed'}))
                items.append({'type':'inspection','key':task['id']})
            command = {'request_id':uid(), 'kind':'submission','items':items,'summary':'ENGINEERING ONLY partial collaborator return'}
            returned, _ = self.call('reviewer_export_submission', lambda: Collection(c).export(actor, command))
            assert Collection(c).export(actor, command)[0] == returned; self.record('replay_submission_export')
            self.call('coordinator_import_submission', lambda: self.c.import_package(ACTOR, returned))
            assert self.c.import_package(ACTOR, returned)['status'] == 'already_imported'; self.record('replay_submission_import')
            returns.append(actor)
            restored = helpers.app('reviewer-ana' if actor == A else 'reviewer-daniel', True)
            assert restored.collaboration.read_material(actor, mid)['blocks'] == blocks; self.record('reviewer_store_reopen')
        assert self.c.read_material(ACTOR, mid, view='master')['blocks'] == archive['blocks']
        receipts = []
        for actor in returns:
            submission = next(s for s in self.c.all('submission') if s['actor'] == actor and s.get('material_id') == mid)
            preview = self.call('preview_returned_submission', lambda: self.c.preview(ACTOR, {'submission_id':submission['id']}))
            if actor == B: assert preview['unresolved'], 'Parallel edit must be a conflict.'
            receipt = self.adopt(preview); receipts.append({'type':'receipt','key':receipt['request_id']})
        task_result = next(item for item in self.c.all('collection_item') if item.get('item_type') == 'inspection_submission')
        comparison = Collection(self.c).preview(ACTOR, {'item_id':task_result['id']})
        applied = self.call('adopt_partial_inspection_return', lambda: Collection(self.c).adopt(ACTOR, {'item_id':task_result['id'],'request_id':uid(),'expected_current_digest':comparison['current_digest'],'choice':'incoming','explicit_confirmation':True}))
        assert queue.tasks(mid)[0]['status'] == 'pending' and not queue.tasks(mid)[0]['checked_scope']
        receipts.append({'type':'receipt','key':applied['id']})
        blob, _ = self.call('export_adoption_receipts', lambda: Collection(self.c).export(ACTOR, {'request_id':uid(),'kind':'receipt','items':receipts}))
        self.call('reviewer_import_receipts', lambda: reviewers[0][0].collaboration.import_package(A, blob))
        assert reviewers[0][0].collaboration.all('received_adoption')
        assert queue.read_archive(ACTOR, mid)['blocks'] == archive['blocks']
        self.capture()
        return {'reviewers':returns,'receipt_count':len(receipts),'parallel_conflict':True,'archive_retained':True,'partial_check_still_pending':True,'actual_windows':False}

    def verify_preservation(self):
        self.capture()
        after_originals = {str(path.relative_to(self.fixture/'Data')): sha256(path.read_bytes()).hexdigest() for path in (self.fixture/'Data').rglob('*') if path.is_file()}
        assert after_originals == self.originals
        for (relative, mid, revision), expected in self.history.items():
            path = self.fixture/relative
            with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as db:
                row = db.execute('SELECT data FROM material_revisions WHERE material_id=? AND revision=?',(mid,revision)).fetchone()
            assert row and sha256(row[0].encode()).hexdigest() == expected
        for relative, expected in self.artifacts.items(): assert sha256((self.fixture/relative).read_bytes()).hexdigest() == expected
        return {'source_files': len(self.originals), 'immutable_revisions': len(self.history), 'parser_artifacts': len(self.artifacts)}

    def finish(self):
        after_code = code_manifest(); changed = sorted(k for k in self.before_code.keys()|after_code.keys() if self.before_code.get(k) != after_code.get(k))
        (self.report/'code-after.json').write_text(json.dumps(after_code,indent=2))
        if self.require_stable and changed: self.failures.append('code_changed_during_required_stable_run')
        result = {'status':'FAIL' if self.failures else 'PASS','label':self.label,'evidence_kind':'owning-service API integration; not browser acceptance',
            'frozen_candidate_stability':False,'execution_mode':getattr(self,'execution_mode','full-workload'),'exercised_sources':list(self.materials),'harness_sha256':self.harness_hash,'started_at':self.started,'finished_at':now(),'actual_duration_seconds':time.monotonic()-self.clock,
            'group_count':len(self.groups),'failed_groups':self.failures,'operations':dict(self.operations),'operation_count':sum(self.operations.values()),
            'fixture':str(self.fixture),'source_files_preserved':len(self.originals),'immutable_revisions_checked':len(self.history),'parser_artifacts_checked':len(self.artifacts),
            'code_changed_during_run':changed,'require_code_stable':self.require_stable,'rss_peak_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'limits':['Synthetic local business decisions only','Real service restart and browser interaction are separate checks','No Windows device','No automatic extraction accuracy conclusion','No fixed-duration or multi-day reliability claim', 'Operation count covers explicitly logged actions; read assertions may make additional service calls', 'RSS is this harness process only, not combined worker memory']}
        (self.report/'result.json').write_text(json.dumps(result,indent=2)); self.log.close(); print(json.dumps(result,ensure_ascii=False),flush=True)
        return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-name',required=True);parser.add_argument('--label',default='development mixed workload');parser.add_argument('--require-code-stable',action='store_true');parser.add_argument('--only-group',choices=['machine_order_content_resume']);args=parser.parse_args()
    run=Workload(args.run_name,args.label,args.require_code_stable)
    run.execution_mode = 'targeted:' + args.only_group if args.only_group else 'full-workload'
    run.group('isolation_setup',run.build)
    if not run.failures:
        for sid in (('TS001',) if args.only_group else ('TS001','TS002','TS003')):
            run.group('initialize_'+sid,lambda sid=sid:run.initialize(sid))
            if sid not in run.materials: continue
            for cycle in ([] if args.only_group else range(1,5)): run.group(f'{sid}_cycle_{cycle}',lambda sid=sid,cycle=cycle:run.cycle(sid,cycle))
        if 'TS001' in run.materials:
            run.group('machine_order_content_resume',run.machine_order_content_resume)
            if not args.only_group:
                run.group('worker_and_save_faults',run.faults)
                run.group('three_workspace_exchange',run.exchange)
        run.group('final_preservation',run.verify_preservation)
        result=run.finish()
    else:
        result={'status':'FAIL','failed_groups':run.failures};(run.report/'result.json').write_text(json.dumps(result,indent=2));run.log.close()
    raise SystemExit(0 if result['status']=='PASS' else 1)


if __name__=='__main__':main()
