"""Local operational evidence. Never persist exception text or document payloads."""
from __future__ import annotations
import json
import os
import sqlite3
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from .platform_support import peak_rss_bytes

COMPONENTS = {'source': 'Source service', 'material': 'Material extraction',
              'storage': 'Saved material storage', 'excel': 'Excel output',
              'source_excel': 'Source Excel output', 'legacy': 'Legacy processing'}

def utc():
    return datetime.now(timezone.utc).isoformat()

def error_info(exc):
    kind = type(exc).__name__
    if kind in {'TimeoutExpired', 'TimeoutError'}:
        return 'timeout', 'The operation exceeded its time limit. Saved work is retained.'
    if isinstance(exc, OSError):
        return 'local_io', 'A local resource could not be read or written. Check storage and access, then retry.'
    return 'operation_failed', 'The local operation did not complete. Retry the action using its existing request identifier.'

class RuntimeStatus:
    def __init__(self, runtime):
        self.path = runtime / 'runtime-status.json'
        self.log = runtime / 'runtime-events.jsonl'
        self.lock = threading.RLock()
        self.active = {}
        self.last_flush = 0.
        self.started = time.monotonic()
        self.persistence_error = None
        previous = {}
        try: previous = json.loads(self.path.read_text()).get('components', {})
        except FileNotFoundError: pass
        except (ValueError, OSError): self.persistence_error = {'code': 'status_read_failed', 'message': 'Previous runtime status could not be read.'}
        self.components = {}
        for key, name in COMPONENTS.items():
            old = previous.get(key, {})
            self.components[key] = dict(id=key, name=name, state='starting', last_checked=None,
                last_success=old.get('last_success'), current_task=None, duration=0, error=None,
                failures=0, retry_seconds=0, last_error=old.get('last_error'))
            if old.get('state') == 'running':
                self.components[key]['state'] = 'waiting'
                self.components[key]['error'] = {'code': 'interrupted', 'message': 'A previous operation was interrupted. Durable pending work will be checked on restart.', 'event_id': uuid.uuid4().hex, 'at': utc()}
                self.components[key]['last_error'] = self.components[key]['error']
        self._persist(True)

    def _persist(self, force=False, event=None):
        if not force and time.monotonic() - self.last_flush < 15: return
        try:
            if event:
                with self.log.open('a', encoding='utf8') as out:
                    out.write(json.dumps(event) + '\n'); out.flush(); os.fsync(out.fileno())
            temp = self.path.with_suffix('.tmp')
            with temp.open('w', encoding='utf8') as out:
                json.dump({'components': self.components}, out); out.flush(); os.fsync(out.fileno())
            temp.replace(self.path)
            self.last_flush = time.monotonic()
            self.persistence_error = None
        except OSError:
            self.persistence_error = {'code': 'status_write_failed', 'message': 'Runtime evidence could not be saved. This does not confirm whether material saving succeeded; keep the action receipt.'}

    def disable(self, key, reason):
        """Declare an intentionally unavailable component without inventing success."""
        with self.lock:
            if any(item[0] == key for item in self.active.values()):
                raise ValueError('Cannot disable an active runtime component.')
            row = self.components[key]
            changed = row['state'] != 'disabled' or row.get('unavailable_reason') != reason
            row.update(state='disabled', unavailable_reason=reason, current_task=None,
                error=None, failures=0, retry_seconds=0)
            event = dict(component=key, state='disabled', at=utc()) if changed else None
            self._persist(bool(event), event)

    def start(self, key, task, request_id=None):
        token = uuid.uuid4().hex
        with self.lock:
            safe_id = str(request_id) if request_id and re.fullmatch(r'[a-fA-F0-9-]{32,36}', str(request_id)) else None
            self.active[token] = (key, time.monotonic(), task, safe_id)
            row = self.components[key]
            row.update(state='running', current_task=task, request_id=safe_id, last_checked=utc())
            self._persist()
        return token

    def finish(self, token, error=None, state='idle'):
        with self.lock:
            key, started, task, request_id = self.active.pop(token)
            row = self.components[key]; old = row['error']
            row.update(last_checked=utc(), duration=round(time.monotonic()-started, 3), current_task=None)
            if error:
                code, message = error_info(error)
                failure = dict(code=code, message=message, event_id=uuid.uuid4().hex, request_id=request_id, at=utc())
                row.update(state='failed', error=failure, last_error=failure, failures=row['failures']+1)
                event = dict(component=key, state='failed', task=task, **failure) if not old or old['code'] != code else None
            else:
                row.update(state=state, last_success=utc(), error=None, failures=0, retry_seconds=0)
                event = dict(component=key, state='recovered', at=utc()) if old else None
            pending = [item for item in self.active.values() if item[0] == key]
            if pending: row.update(state='running', current_task=pending[0][2])
            self._persist(bool(event), event)

    def backoff(self, key, base):
        with self.lock:
            failures = self.components[key]['failures']
            delay = min(60, base * 2 ** min(failures, 5)) if failures else base
            self.components[key]['retry_seconds'] = delay if failures else 0
            return delay

    def snapshot(self):
        with self.lock:
            rows = json.loads(json.dumps(list(self.components.values())))
            now = time.monotonic()
            for row in rows:
                active = [v for v in self.active.values() if v[0] == row['id']]
                if active: row['duration'] = round(now - min(v[1] for v in active), 3)
            status = 'degraded' if self.persistence_error or any(r['error'] for r in rows) else ('starting' if any(r['state'] == 'starting' for r in rows) else 'healthy')
            return dict(status=status, checked_at=utc(), components=rows, persistence_error=self.persistence_error,
                resources={'uptime_seconds': round(time.monotonic()-self.started, 3), 'active_threads': threading.active_count(),
                    'peak_rss_bytes': peak_rss_bytes(),
                    'memory_measurement': 'process lifetime high-water resident memory, not current memory'})

    def probe_storage(self, paths):
        if time.monotonic() - getattr(self, '_storage_probe', 0) < 15: return
        self._storage_probe = time.monotonic()
        token = self.start('storage', 'check_saved_stores')
        try:
            for path in paths:
                with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=1) as db:
                    db.execute('SELECT count(*) FROM sqlite_master').fetchone()
        except Exception as exc: self.finish(token, exc)
        else: self.finish(token)

    def close(self):
        with self.lock:
            for row in self.components.values(): row.update(state='stopped', current_task=None)
            self._persist(True)

VALIDATION_CODES = frozenset(['all_content_requires_original_association', 'all_original_ranges_including_empty_ranges_require_review', 'block_dependency_cycle', 'block_ids_must_be_unique', 'block_text_must_be_string', 'blocks_must_be_list', 'candidate_not_available_for_reconciliation', 'candidate_not_found_for_material', 'candidate_reconciliation_required', 'candidate_result_already_final', 'checked_scope_outside_material', 'complete_original_scope_required', 'content_issue_ids_must_be_unique', 'explicit_human_confirmation_required', 'heading_level_required', 'heading_parent_level_invalid', 'image_reference_outside_material', 'image_source_or_attributed_attachment_required', 'invalid_block_type', 'invalid_candidate_action', 'invalid_content_issues', 'invalid_imported_content_issues', 'legacy_provenance_required', 'material_not_found', 'material_revision_not_found', 'merged_blocks_required', 'named_operator_required', 'open_request_source_mismatch', 'parent_must_be_preceding_heading', 'renewed_source_review_required', 'request_id_must_be_canonical_uuid', 'request_id_reused_with_different_payload', 'source_reference_outside_material', 'source_version_requires_reconciliation', 'stale_or_partial_candidate_cannot_be_adopted', 'structural_associations_require_review', 'table_merge_out_of_bounds', 'table_merges_overlap', 'table_must_be_rectangular_text_cells', 'table_notes_must_be_list', 'table_rows_required', 'unresolved_block_dependency', 'unresolved_content_issues', 'unresolved_issue_cannot_be_silently_removed'])

class ObservedAdapter:
    def __init__(self, delegate, monitor, system):
        self.delegate, self.monitor, self.system = delegate, monitor, system
    def __getattr__(self, name): return getattr(self.delegate, name)
    def call(self, command, **kwargs):
        if self.system == 1: key = 'source_excel' if command in {'export_status', 'confidence_export'} else 'source'
        else:
            key = 'material' if command == 'material_tick' else ('storage' if command.startswith('material_') else ('excel' if command == 'workbook' else 'legacy'))
        # Command names are fixed server-side verbs, never request bodies or paths.
        token = self.monitor.start(key, command, (kwargs.get('request') or {}).get('request_id'))
        try: result = self.delegate.call(command, **kwargs)
        except Exception as exc:
            # Form validation and version conflicts are expected business refusals.
            expected = isinstance(exc, ValueError) and str(exc) in VALIDATION_CODES
            self.monitor.finish(token, None if expected else exc)
            raise
        failed = isinstance(result, dict) and result.get('status') in {'failed', 'blocked', 'pending_refresh'}
        if command == 'material_tick' and isinstance(result, dict):
            candidate = result.get('candidate') or {}
            failed = failed or candidate.get('status') == 'failed'
        self.monitor.finish(token, RuntimeError() if failed else None,
            'waiting' if isinstance(result, dict) and result.get('status') in {'busy', 'waiting', 'deferred'} else 'idle')
        return result
