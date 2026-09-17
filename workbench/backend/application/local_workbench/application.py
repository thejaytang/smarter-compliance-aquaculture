"""Application composition and local worker coordination."""
from __future__ import annotations
import json
import secrets
import threading
import time
import uuid
from pathlib import Path
from local_workbench.adapter import System1, System2
from backend.shared.policies import Policies
from local_workbench.store import Store
from local_workbench.export_status import read_status
from local_workbench.export_schedule import ExportSchedule
from local_workbench.runtime_status import RuntimeStatus, ObservedAdapter
from local_workbench.collaboration import Collaboration, PackageSourceAdapter
from local_workbench.operation_gate import OperationGate
from backend.shared.component_process import ComponentPool


class Application:
    def __init__(self, root, system_root=None, config=None, *, start_workers=True, reviewer=False, code_root=None):
        self.root = Path(root).resolve()
        self.code_root = Path(code_root).resolve() if code_root else __import__("local_workbench").PROJECT
        self.ui_root = self.code_root / 'workbench/frontend'
        self.reviewer = bool(reviewer)
        self.peer_sync = True
        self.operation_lock = OperationGate()
        self.component_pool = ComponentPool()
        from backend.shared.workspace import Workspace, active
        self.layout = Workspace(self.root) if active(self.root) else None
        self.runtime = self.layout.runtime/"state" if self.layout else self.root / "runtime"
        self.runtime.mkdir(parents=True, exist_ok=True)
        self.uploads = self.layout.workspace/"sources/uploads" if self.layout else self.runtime/"uploads"
        self.store = Store(self.layout.journal if self.layout else self.runtime / "workbench.sqlite")
        self.adapter = System1(system_root or self.code_root / "workbench/backend/system1", config or (self.layout.source_config if self.layout else None))
        self.policies = Policies(self.layout.journal if self.layout else self.runtime / 'workbench.sqlite')
        self.system2 = System2(self.code_root / 'workbench/backend/system2', self.adapter.root, config or (self.layout.source_config if self.layout else None),
                              self.layout.materials if self.layout else self.runtime / 'system2-workflow' if self.reviewer or system_root or self.root != self.code_root / 'workbench' else None)
        self.adapter.gate=self.operation_lock
        self.system2.gate=self.operation_lock
        self.adapter.pool = self.system2.pool = self.component_pool
        self.collaboration = Collaboration(self, reviewer=self.reviewer)
        if self.reviewer:
            self.adapter = PackageSourceAdapter(self.collaboration, self.code_root / 'workbench/backend/system1')
        self.monitor = RuntimeStatus(self.runtime)
        self.adapter = ObservedAdapter(self.adapter, self.monitor, 1)
        self.system2 = ObservedAdapter(self.system2, self.monitor, 2)
        self.system2_lock = threading.Lock()
        self.system2_status = {'status': 'idle'}
        self.system2_summary = None
        self.system2_qa = []
        self.csrf = secrets.token_urlsafe(32)
        self.instance = secrets.token_urlsafe(24)
        self.stop = threading.Event()
        self.snapshot_lock = threading.Lock()
        self.snapshot_cache = None
        self.snapshot_time = 0
        self.qa_next_check = 0
        self.qa_status = {}
        self.worker = threading.Thread(target=self.work, daemon=True)
        if start_workers and not self.reviewer: self.worker.start()
        self.parser_worker = threading.Thread(target=self.operation_lock.run_background, args=(self.parse_work,), daemon=True)
        if start_workers and not self.reviewer: self.parser_worker.start()
        self.material_worker = threading.Thread(target=self.operation_lock.run_background, args=(self.material_work,), daemon=True)
        if start_workers: self.material_worker.start()
        self.workbook_status = {'status': 'scheduled'}
        saved_status = self.runtime / 'excel-worker.json'
        if saved_status.is_file():
            try:
                previous = json.loads(saved_status.read_text())
                if previous.get('status') == 'failed': self.workbook_status = previous
            except (OSError, ValueError): pass
        self.workbook_worker = threading.Thread(target=self.operation_lock.run_background, args=(self.refresh_workbook,), daemon=True)
        if start_workers and not self.reviewer: self.workbook_worker.start()
        self.confidence_worker = threading.Thread(target=self.operation_lock.run_background, args=(self.refresh_confidence,), daemon=True)
        if start_workers and not self.reviewer: self.confidence_worker.start()

        if self.reviewer:
            self.workbook_status = {'status': 'unavailable', 'message': 'Master exports are disabled in a reviewer workspace.'}
            for component in ('legacy', 'excel', 'source_excel'):
                self.monitor.disable(component, 'Unavailable in an offline reviewer workspace.')

    def static_path(self,name):
        folder='pages' if name.endswith('.html') else 'components' if name.endswith(('.js','.mjs')) and '/' not in name else 'assets'
        return self.ui_root/folder/name

    def sync_policy(self):
        if self.reviewer: raise ValueError('Reviewer workspaces cannot apply master policies.')
        # Apply every revision, not just the final value, so review history is reproducible.
        with self.system2_lock:
            if getattr(self,'synced_policy',None)==self.policies.get()['revision']:return
            for entry in self.policies.history()[1:]:
                policy = entry['policy']
                self.system2.call('policy', request={'request_id': str(uuid.uuid5(uuid.NAMESPACE_URL,
                    str(self.root) + '/policy/' + str(policy['revision']))), 'actor': entry['actor'], 'policy': policy})
            policy = self.policies.get()
            self.adapter.call('assessment_policy', revision=policy['revision'], threshold=policy['system1'])
            self.synced_policy=policy['revision']

    def parse_work(self):
        interval = 3
        while not self.stop.wait(self.monitor.backoff('legacy', interval)):
            try:
                self.sync_policy()
                self.system2_status = self.system2.call('tick')
                interval = 10 if self.system2_status.get('status') == 'idle' else 3
                summary=self.system2.call('state', view='summary')
                self.system2_summary={'pending':summary['pending'],'published':summary['published'],
                    'parsed':sum(d['parser_complete'] for d in summary['documents']),
                    'processing_followups':summary.get('processing_followups')}
                if not getattr(self,'qa2_next',0) or time.time()>=self.qa2_next:
                    self.qa2_next=time.time()+60
                    self.system2_qa=self.system2.call('qa')
                    self.weekly_sampling_status=self.system2.call('weekly_tick')
                    self.weekly_sampling=self.system2.call('weekly')
            except Exception as exc:
                self.system2_status = {'status': 'waiting', 'message': 'Local processing failed; inspect Runtime status.'}
                self.system2_summary = None
                if not self.monitor.components['legacy']['error']:
                    token = self.monitor.start('legacy', 'check_processing_state'); self.monitor.finish(token, exc)

    def material_work(self):
        """Resume only already requested material candidates, never enqueue on view."""
        while not self.stop.wait(self.monitor.backoff('material', 2)):
            try:
                token = self.monitor.start('material', 'personal_material_tick')
                self.material_status = self.collaboration.tick()
                self.dispatch_material_inspections()
                self.monitor.finish(token)
            except Exception as exc:
                self.monitor.finish(token, exc)
                self.material_status = {'status': 'failed', 'message': 'Local processing failed; inspect Runtime status.'}

    def dispatch_material_inspections(self):
        """Opt-in coordinator scheduler; called by worker only, never a page read."""
        if self.reviewer:
            return
        stamp = time.monotonic()
        if stamp < getattr(self, 'material_inspection_next', 0):
            return
        self.material_inspection_next = stamp + 60
        path = (self.layout.runtime/'settings' if self.layout else self.runtime) / 'material-inspection-settings.json'
        settings = json.loads(path.read_text()) if path.is_file() else {}
        from local_workbench.material_inspection_schedule import MaterialInspectionSchedule
        self.material_inspection_status = MaterialInspectionSchedule(self.collaboration).run_due(settings)
        if settings.get('interval_days') and self.material_inspection_status.get('status') == 'complete':
            from datetime import datetime, timezone, timedelta
            # Only advance the exact configuration that was dispatched. A saved
            # preference change during a run must not be overwritten.
            with self.collaboration.lock:
                current = json.loads(path.read_text()) if path.is_file() else {}
                if current == settings:
                    instant = datetime.now(timezone.utc)
                    current['next_run_at'] = (instant + timedelta(days=settings['interval_days'])).isoformat()
                    temporary = path.with_suffix('.tmp')
                    temporary.write_text(json.dumps(current, indent=2)); temporary.replace(path)

    def refresh_workbook(self):
        schedule = ExportSchedule(time.monotonic())
        while not self.stop.wait(1):
            state = read_status(self.system2.runtime)
            version = (state.get('saved_event_cursor'), state.get('saved_policy_revision'),
                       state.get('saved_registry_sha256'),state.get('saved_registry_kind'))
            if not schedule.due(version, state['status'] != 'current', time.monotonic()):
                if state['status'] == 'current' and self.monitor.components['excel']['state'] == 'starting':
                    token = self.monitor.start('excel', 'read_export_status'); self.monitor.finish(token)
                continue
            started = time.monotonic()
            try:
                self.workbook_status = {'status': 'refreshing'}
                self.workbook_status = self.system2.call('workbook')
            except Exception as exc:
                self.workbook_status = {'status': 'failed', 'message': str(exc)}
            schedule.finished(self.workbook_status.get('status') == 'current', time.monotonic())
            self.workbook_status['generation_seconds'] = round(time.monotonic()-started, 3)
            self.workbook_status['retry_seconds'] = max(0, round(schedule.next_attempt-time.monotonic(), 1))
            self.workbook_status['checked_at'] = time.time()
            try:
                marker = self.runtime / 'excel-worker.json'
                temp = marker.with_suffix('.tmp')
                temp.write_text(json.dumps(self.workbook_status))
                temp.replace(marker)
            except OSError as exc:
                token = self.monitor.start('excel', 'save_export_status')
                self.monitor.finish(token, exc)

    def refresh_confidence(self):
        # Source-governance export cannot delay System2's durable-state snapshot.
        schedule=ExportSchedule(time.monotonic());legacy_next=time.monotonic()+60
        while not self.stop.wait(self.monitor.backoff('source_excel', 5)):
            try:
                config=json.loads(self.adapter.config.read_text())
                if not config.get('governance_db'):
                    if time.monotonic()<legacy_next:continue
                    legacy_next=time.monotonic()+60
                else:
                    state=self.adapter.call('export_status')
                    version=json.dumps(state.get('authority_version'),sort_keys=True)
                    if not schedule.due(version,state['status']!='current',time.monotonic()):continue
                self.confidence_export_status=self.adapter.call('confidence_export')
                schedule.finished(True,time.monotonic())
            except Exception as exc:
                self.confidence_export_status={'status':'pending_refresh','message':'Source output could not refresh; inspect Runtime status.'}
                if not self.monitor.components['source_excel']['error']:
                    token = self.monitor.start('source_excel', 'check_source_export'); self.monitor.finish(token, exc)
                schedule.finished(False,time.monotonic())

    def extraction_state(self, **options):
        # Display reads never wait for policy application, parser writes or Excel generation.
        result = self.system2.call('state', view=options.pop('view', 'browser'), **options)
        result['workbook'] = getattr(self, 'workbook_status', {'status': 'scheduled'})
        return result

    def snapshot(self):
        with self.snapshot_lock:
            if self.snapshot_cache is None or time.time() - self.snapshot_time > 3:
                self.snapshot_cache = self.adapter.call("read")
                self.snapshot_time = time.time()
            return self.snapshot_cache

    def work(self):
        while not self.stop.wait(self.monitor.backoff('source', .4)):
            try:
                self.work_once()
            except Exception as exc:
                token = self.monitor.start('source', 'request_journal_or_schedule')
                self.monitor.finish(token, exc)

    def work_once(self):
        if self.reviewer: return
        req = self.store.next_request()
        if not req:
            if time.time() >= self.qa_next_check:
                self.qa_next_check = time.time() + 60
                try:
                    self.qa_status = self.adapter.call("random_qa")
                    if self.qa_status.get("generated_count"):
                        self.snapshot_time = 0
                except Exception as exc:
                    self.qa_status = {"status": "WAITING", "message": str(exc)}
                path = self.runtime / "qa-schedule-status.json"
                tmp = path.with_suffix(".tmp")
                tmp.write_text(json.dumps({"checked_at": time.time(), **self.qa_status}))
                tmp.replace(path)
            return
        try:
            result = self.adapter.call("apply", request=json.loads(req["body"]))
            status, message = result["status"], result["message"]
        except Exception as exc:
            message = str(exc)
            if "STALE:" in message:
                status = "stale"
            elif any(t in message.lower() for t in ("workbook is open", "save and close", "already running")):
                status, message = "waiting", "Waiting for Excel to close or the current system task to finish. Processing will resume automatically."
            else:
                status = "blocked"
        self.store.finish(req["id"], status, message)
        self.snapshot_time = 0

    def close(self):
        self.stop.set()
        # Every adapter has a bounded subprocess timeout. Drain all writers before
        # releasing the service lock so migration/restart cannot race orphaned exports.
        for worker in (self.worker, self.parser_worker, self.workbook_worker, self.confidence_worker):
            if worker.ident is not None: worker.join()
        if getattr(self, 'material_worker', None):
            if self.material_worker.ident is not None: self.material_worker.join()
        self.component_pool.close()
        if getattr(self, 'monitor', None): self.monitor.close()
