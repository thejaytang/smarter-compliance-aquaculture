"""Governed, button-only material actions, separate from legacy recomputation.

Runs in System2's environment. Workbench owns sessions; this adapter accepts
only server-resolved actors and source IDs, never a browser-supplied path.
"""
from __future__ import annotations
import contextlib
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import uuid

from ..contracts.source import Snapshot
from ..platform_support import lock_file
from ..intake.system1 import read_system1
from ..intake.registry import build_manifest, read_snapshot
from ..review.materials import MaterialStore
from ..review.material_reads import compact_candidate
from ..evidence.material_reader import inspect_original, read_material


class MaterialService:
    def __init__(self, root, system1, config=None):
        self.root = Path(root).resolve()
        self.system1 = Path(system1).resolve()
        self.config = Path(config).resolve() if config else None
        self.store = MaterialStore(self.root)

    def handoff(self):
        from .material_collaboration import offline_handoff
        return offline_handoff(self.root) or read_system1(self.system1, self.config)

    def annotate(self, material, handoff=None):
        """Keep transient source authority visible after reads and saved receipts."""
        try:
            handoff = handoff or self.handoff()
            material['source_issues'] = [i for i in getattr(handoff, 'evidence', {}).get('source_open_issues', [])
                if i.get('source_id') == material['source']['source_id']]
        except (ValueError, OSError, subprocess.SubprocessError):
            material['source_check_error'] = 'System1 is unavailable. Saved work is recoverable; confirmation requires a current source check.'
        return material

    def _path(self, source):
        suffix = '.' + source['file_format'].lower().lstrip('.')
        if suffix not in {'.pdf', '.html', '.htm', '.xlsx', '.xls'}:
            raise ValueError('material_format_not_supported_use_source_follow_up')
        fingerprint = source['content_hash']
        if len(fingerprint) != 64 or any(c not in '0123456789abcdef' for c in fingerprint):
            raise ValueError('invalid_original_fingerprint')
        return self.root / 'material-originals' / (fingerprint + suffix)

    def _pin(self, source, source_root):
        raw = read_snapshot(Snapshot(**source), source_root)
        path = self._path(source)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, path)
            except FileExistsError:
                if sha256(path.read_bytes()).hexdigest() != source['content_hash']:
                    raise ValueError('pinned_original_integrity_failure')
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return path

    def observe_sources(self, handoff):
        current = {r['source_id']: r for r in handoff.records}
        for source in self.store.source_bindings():
            row = current.get(source['source_id'], {})
            eligible = row.get('selection_status') == 'INCLUDE' and row.get('source_status') == 'CURRENT'
            stale = not eligible or source['snapshot_id'] != row.get('snapshot_id') or source['content_hash'] != row.get('content_hash')
            if stale == bool(source['source_stale']):
                continue
            self.store.mark_source_version(source['source_id'],
                row.get('snapshot_id') if eligible else None, row.get('content_hash') if eligible else None)

    def listing(self, **options):
        handoff = self.handoff()
        self.observe_sources(handoff)
        sources = [dict(source_id=r['source_id'], title=r.get('source_title') or r['source_id'],
            file_format=r.get('file_format'), snapshot_id=r.get('snapshot_id'), content_hash=r.get('content_hash'),
            source_revision=r.get('source_revision')) for r in handoff.records
            if r.get('selection_status') == 'INCLUDE' and r.get('snapshot_status') == 'STORED']
        page = self.store.list_page(**options)
        materials = page['materials']
        issues = getattr(handoff, 'evidence', {}).get('source_open_issues', [])
        for material in materials:
            material['source_issues'] = [i for i in issues if i.get('source_id') == material['source']['source_id']]
        return {'sources': sources, **page, 'counts': self.store.counts(i.get('source_id') for i in issues), 'schema_version': 'human-material-workbench/2'}

    def open(self, request):
        # Opening pins a registered snapshot and creates an empty editable layer;
        # it never extracts, classifies, accepts or exports content.
        replay = self.store.open_receipt(request)
        if replay is not None:
            return self.store.compact_view(self.annotate(replay))
        handoff = self.handoff()
        manifest = build_manifest(handoff.records, handoff.registry_sha256, handoff.source_root, {request['source_id']})
        if manifest['rejected']:
            raise ValueError('Source needs System1 follow-up: ' + json.dumps(manifest['rejected']))
        source = manifest['items'][0]
        path = self._pin(source, handoff.source_root)
        reader = inspect_original(path, source['content_hash'])
        row = next(r for r in handoff.records if r['source_id'] == request['source_id'])
        handoff.assert_current()
        self.observe_sources(handoff)
        legacy = []
        with self.store.connect() as db:
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='documents'").fetchone():
                for identity, data in db.execute('SELECT id,data FROM documents'):
                    previous = json.loads(data)
                    if previous['source']['source_id'] == source['source_id']:
                        legacy.append({'document_id': identity, 'source': previous['source'],
                            'revision': previous['revision'], 'notice': 'Retained legacy extraction and review. Its decisions are not new material confirmation.'})
        material = self.store.open(source, row.get('source_title') or source['source_id'], reader['scope'],
            legacy={'documents': legacy, 'notice': 'Existing corrections and decisions remain in Legacy review and history.'} if legacy else None,
            request=request)
        return self.store.compact_view(self.annotate(material, handoff))

    def read(self, identity, revision=None):
        # Source observation changes only staleness metadata, never content.
        try:
            handoff = self.handoff()
            self.observe_sources(handoff)
        except (ValueError, OSError, subprocess.SubprocessError):
            material = self.store.read_compact(identity, revision=revision)
            material['source_check_error'] = 'System1 is unavailable. Saved work is recoverable; confirmation requires a current source check.'
            return material
        material = self.store.read_compact(identity, revision=revision)
        material['source_issues'] = [i for i in getattr(handoff, 'evidence', {}).get('source_open_issues', [])
            if i.get('source_id') == material['source']['source_id']]
        return material

    def reader(self, identity, **options):
        source = self.store.source_metadata(identity)
        result = read_material(self._path(source), source['content_hash'], **options)
        result['original_url'] = '/api/material/original?id=' + identity
        return result

    def original(self, identity):
        source = self.store.source_metadata(identity)
        path = self._path(source)
        return {'path': str(path), 'size': path.stat().st_size, 'filename': Path(source['relative_path']).name,
                'file_format': source['file_format'], 'sha256': source['content_hash']}

    def mutate(self, action, request):
        # Saving a historical/partially completed draft stays possible; completion
        # and extraction need current source authority.
        handoff = None
        if action in {'confirm', 'extract', 'adopt'}:
            handoff = self.handoff()
            self.observe_sources(handoff)
            material = self.store.read(request['material_id'])
            if action == 'confirm' and any(i.get('source_id') == material['source']['source_id']
                    for i in getattr(handoff, 'evidence', {}).get('source_open_issues', [])):
                raise ValueError('Resolve the original document issue in System1 before confirming content review.')
            if action in {'confirm', 'extract'}:
                raw = self._path(material['source']).read_bytes()
                if sha256(raw).hexdigest() != material['source']['content_hash']:
                    raise ValueError('pinned_original_integrity_failure')
            handoff.assert_current()
        elif action == 'save':
            try:
                handoff = self.handoff()
                self.observe_sources(handoff)
            except (ValueError, OSError, subprocess.SubprocessError):
                pass  # Durable partial work must survive temporary source unavailability.
        if action == 'import-legacy':
            from .material_legacy import legacy_candidate
            material = self.store.read(request['material_id'])
            imported = legacy_candidate(self.root, material)
            result = self.store.import_candidate(request, imported['blocks'], imported['provenance'], issues=imported['issues'])
        else:
            function = {'candidate-draft': self.store.save_candidate_draft, 'save': self.store.save, 'confirm': self.store.confirm,
                        'extract': self.store.start_candidate, 'adopt': self.store.reconcile,
                        'process': self.store.process}[action]
            result = function(request)
        if result.get('candidate'):
            result['candidate'] = compact_candidate(result['candidate'])
        if result.get('material'):
            result['material'] = self.store.compact_view(self.annotate(result['material'], handoff))
        return result

    def tick(self):
        # Only durable candidates created by Extract are eligible. A crash resumes
        # the same candidate ID under the single-worker lock; prior attempts stay.
        with (self.root / '.material-worker.lock').open('a+b') as lock:
            try:
                lock_file(lock)
            except BlockingIOError:
                return {'status': 'busy'}
            pending = self.store.pending_candidates()
            if not pending:
                return {'status': 'idle'}
            candidate = pending[0]
            material = self.store.read(candidate['material_id'])
            source = candidate['source']
            output = self.root / 'material-artifacts' / material['id'] / candidate['id'] / str(uuid.uuid4())
            try:
                from .material_parser import parse_material
                pinned = self._path(source)
                source_copy = Snapshot(**dict(source, relative_path=pinned.name))
                parsed = parse_material(source_copy, pinned.parent, output)
                try:
                    self.observe_sources(self.handoff())
                except (ValueError, OSError, subprocess.SubprocessError):
                    parsed.setdefault('warnings', []).append('Source availability could not be rechecked; confirm requires current authority.')
                return self.store.finish_candidate(material['id'], candidate['id'], parsed['blocks'],
                    complete=parsed.get('status') == 'candidate_available' and not parsed.get('unresolved'),
                    error=parsed.get('error'), warnings=parsed.get('warnings', []),
                    metadata={'parser_status': parsed.get('status'), **{key: parsed.get(key) for key in ('parser_version', 'canonical_artifacts', 'covered_scope', 'processed_scope', 'usable_scope', 'unprocessed_scope', 'unresolved')}})
            except Exception as exc:
                return self.store.finish_candidate(material['id'], candidate['id'], [], complete=False, error=str(exc))


def main():
    envelope = json.load(sys.stdin)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            service = MaterialService(envelope['root'], envelope['system1'], envelope.get('system1_config'))
            command = envelope['command'].removeprefix('material_')
            payload = envelope.get('request', {})
            if command in {'seed', 'export', 'validate', 'adopt-master', 'repeat-resolution'}:
                from .material_collaboration import command as collaboration_command
                result = collaboration_command(service, command, payload)
            elif command == 'list':
                result = service.listing(**envelope.get('options', {}))
            elif command == 'open':
                result = service.open(payload)
            elif command == 'read':
                result = service.read(envelope['material_id'], envelope.get('revision'))
            elif command == 'history':
                result = service.store.history_page(envelope['material_id'], **envelope.get('options', {}))
            elif command == 'candidate':
                result = service.store.candidate_detail(envelope['material_id'], envelope['candidate_id'])
            elif command == 'conflict':
                result = service.store.conflict_detail(envelope['material_id'], envelope['conflict_id'])
            elif command == 'reader':
                result = service.reader(envelope['material_id'], **envelope.get('options', {}))
            elif command == 'original':
                result = service.original(envelope['material_id'])
            elif command == 'tick':
                result = service.tick()
                if result.get('candidate'): result['candidate'] = compact_candidate(result['candidate'])
                if result.get('material'): result['material'] = service.store.compact_view(result['material'])
            else:
                result = service.mutate(command, payload)
        print(json.dumps({'ok': True, 'data': result}, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
