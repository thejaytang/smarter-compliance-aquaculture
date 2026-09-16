from __future__ import annotations
import hashlib
import json
import mimetypes
import os
import re
import secrets
import socket
import threading
import time
import uuid
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs, quote, unquote
from .adapter import System1, System2
from .policies import Policies
from .store import Store
from .evidence import registered_pdf, pdf_range
from .dashboard import build_dashboard
from .export_status import read_status, cached_snapshot
from .export_schedule import ExportSchedule
from .runtime_identity import describe as runtime_evidence
from .runtime_status import RuntimeStatus, ObservedAdapter
from .original_stream import stream_original
from .collaboration import Collaboration, PackageSourceAdapter, COORDINATOR


def ui_content_type(path):
    # Registry MIME overrides differ across Windows installations. Module scripts
    # must have a browser-supported MIME type with nosniff enabled.
    return {'.js':'text/javascript','.mjs':'text/javascript','.html':'text/html',
            '.css':'text/css','.wasm':'application/wasm'}.get(
                Path(path).suffix.lower(), mimetypes.guess_type(path)[0] or 'application/octet-stream')


class Application:
    def __init__(self, root, system_root=None, config=None, *, start_workers=True, reviewer=False, code_root=None):
        self.root = Path(root).resolve()
        self.code_root = Path(code_root).resolve() if code_root else Path(__file__).resolve().parents[3]
        self.ui_root = self.code_root / 'workbench' / 'ui'
        self.reviewer = bool(reviewer)
        self.peer_sync = True
        self.runtime = self.root / "runtime"
        self.runtime.mkdir(parents=True, exist_ok=True)
        self.store = Store(self.runtime / "workbench.sqlite")
        self.adapter = System1(system_root or self.code_root / "system1", config)
        self.policies = Policies(self.runtime / 'workbench.sqlite')
        self.system2 = System2(self.code_root / 'system2', self.adapter.root, config,
                              self.runtime / 'system2-workflow' if self.reviewer or system_root or self.root != self.code_root / 'workbench' else None)
        self.collaboration = Collaboration(self, reviewer=self.reviewer)
        if self.reviewer:
            self.adapter = PackageSourceAdapter(self.collaboration, self.code_root / 'system1')
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
        self.parser_worker = threading.Thread(target=self.parse_work, daemon=True)
        if start_workers and not self.reviewer: self.parser_worker.start()
        self.material_worker = threading.Thread(target=self.material_work, daemon=True)
        if start_workers: self.material_worker.start()
        self.workbook_status = {'status': 'scheduled'}
        saved_status = self.runtime / 'excel-worker.json'
        if saved_status.is_file():
            try:
                previous = json.loads(saved_status.read_text())
                if previous.get('status') == 'failed': self.workbook_status = previous
            except (OSError, ValueError): pass
        self.workbook_worker = threading.Thread(target=self.refresh_workbook, daemon=True)
        if start_workers and not self.reviewer: self.workbook_worker.start()
        self.confidence_worker = threading.Thread(target=self.refresh_confidence, daemon=True)
        if start_workers and not self.reviewer: self.confidence_worker.start()

        if self.reviewer:
            self.workbook_status = {'status': 'unavailable', 'message': 'Master exports are disabled in a reviewer workspace.'}
            for component in ('legacy', 'excel', 'source_excel'):
                self.monitor.disable(component, 'Unavailable in an offline reviewer workspace.')

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
        while not self.stop.wait(self.monitor.backoff('legacy', 3)):
            try:
                self.sync_policy()
                self.system2_status = self.system2.call('tick')
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
        path = self.runtime / 'material-inspection-settings.json'
        settings = json.loads(path.read_text()) if path.is_file() else {}
        from .material_inspection_schedule import MaterialInspectionSchedule
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
        while not self.stop.wait(self.monitor.backoff('source_excel', 1)):
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
        if getattr(self, 'monitor', None): self.monitor.close()


class Handler(BaseHTTPRequestHandler):
    server_version = "LocalWorkbench"
    protocol_version = "HTTP/1.1"

    @property
    def app(self):
        return self.server.app

    def log_message(self, *args):
        pass

    def send(self, status, data, content_type="application/json; charset=utf-8", headers=None):
        if content_type.startswith("application/json"):
            data = json.dumps(data, ensure_ascii=False, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type",content_type)
        self.send_header("Content-Length",str(len(data)))
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("Referrer-Policy","no-referrer")
        headers = dict(headers or {})
        policy = headers.pop("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-src 'self' blob:; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
        self.send_header("Content-Security-Policy", policy)
        for k,v in (headers or {}).items():
            self.send_header(k,v)
        self.end_headers()
        self.wfile.write(data)

    def valid_host(self):
        return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

    def current_session(self, create=True):
        try:
            cookie=SimpleCookie(self.headers.get("Cookie",""))
            key = f"wb_session_{self.server.server_port}"
            # Cookies are host-scoped, not port-scoped. Separate workbench instances
            # must not replace one another's reviewer session on 127.0.0.1.
            token = cookie[key].value if key in cookie else (cookie["wb_session"].value if "wb_session" in cookie else "")
        except Exception:
            token=""
        if not create:
            # Downloading a retained package must not create even an anonymous session.
            with self.app.store.connect() as db:
                row = db.execute("SELECT s.token,a.id,a.name FROM sessions s LEFT JOIN actors a ON a.id=s.actor_id WHERE s.token=?", (token,)).fetchone()
            return dict(row) if row else {"token": token, "id": None, "name": None}
        return self.app.store.session(token)

    def saved_collection_download(self, actor, value):
        identity = str(uuid.UUID(value))
        record = self.app.collaboration.get('sent_collection', identity)
        if not record or record['actor'] != actor:
            raise ValueError('This saved package belongs to another reviewer.')
        data = (self.app.collaboration.root / 'packages' / (identity + '.zip')).read_bytes()
        return data, 'review-' + identity + '.zip', '/api/collaboration/collection-download?id=' + identity

    def do_GET(self):
        if not self.valid_host():
            return self.send(403,{"error":"Host not allowed."})
        parsed=urlsplit(self.path)
        try:
            inspection = bool(getattr(self.app, "read_only_restored", False))
            if self.app.reviewer and (parsed.path.startswith("/api/system2/") or parsed.path.startswith("/api/system3/") or parsed.path == "/api/system1/workbook"):
                return self.send(403, {"error": "Legacy processing and master exports are unavailable in a reviewer workspace."})
            if parsed.path=="/health":
                return self.send(200,{"service":"aquaculture-workbench","root":str(self.app.root),"instance":self.app.instance,
                    "runtime_evidence":runtime_evidence(self.app), "mode":self.app.collaboration.mode})
            if parsed.path in {'/api/sync/history','/api/sync/download'}:
                from .full_snapshot import FullSnapshot
                service = FullSnapshot(self.app.collaboration)
                actor = self.current_session()['name']
                from .collaboration import named
                named(actor)
                if parsed.path.endswith('/history'):
                    return self.send(200, {'events':service.history(), 'pending':[service.public(p) for p in self.app.collaboration.all('sync_plan') if p['actor']==actor and p['status']!='applied']})
                raw, filename = service.download(actor,parse_qs(parsed.query).get('id',[''])[0])
                return self.send(200, raw, 'application/zip', {'Content-Disposition':'attachment; filename="'+filename+'"'})
            if parsed.path == '/api/automation':
                from .automation_settings import AutomationSettings
                return self.send(200, AutomationSettings(self.app).read())
            if parsed.path == '/api/runtime-status':
                stores = [self.app.runtime / 'workbench.sqlite']
                workflow = self.app.system2.runtime / 'workflow.sqlite'
                if workflow.is_file() or not self.app.reviewer: stores.append(workflow)
                self.app.monitor.probe_storage(stores)
                for attr, component in (('worker', 'source'), ('parser_worker', 'legacy'), ('material_worker', 'material'), ('workbook_worker', 'excel'), ('confidence_worker', 'source_excel')):
                    worker = getattr(self.app, attr, None)
                    if worker and worker.ident is not None and not worker.is_alive() and not self.app.stop.is_set():
                        token = self.app.monitor.start(component, 'worker_stopped'); self.app.monitor.finish(token, RuntimeError())
                return self.send(200, self.app.monitor.snapshot())
            if parsed.path == '/api/sources/intake-original':
                session=self.current_session(create=False)
                if self.app.reviewer or not session['id']:raise ValueError('Select a local operator to inspect intake originals.')
                original=self.app.adapter.call('intake_original',operation_id=parse_qs(parsed.query).get('operation_id',[''])[0])
                path=Path(original['path']).resolve()
                if path.parent!=Path(original['root']).resolve():raise ValueError('Invalid intake original location.')
                data=path.read_bytes()
                if hashlib.sha256(data).hexdigest()!=original['hash']:raise ValueError('The intake original changed; reload the task.')
                is_pdf=path.suffix.lower()=='.pdf'
                return self.send(200,data,'application/pdf' if is_pdf else 'application/octet-stream',
                    {'Content-Disposition':('inline' if is_pdf else 'attachment')+'; filename="'+path.name+'"',
                     'Content-Security-Policy':"default-src 'none'; object-src 'self'; frame-ancestors 'self'"})
            if parsed.path == '/api/sources/check-updates':
                session=self.current_session(create=False)
                from .source_checks import get_check
                return self.send(200,get_check(self.app,session['name'],parse_qs(parsed.query).get('id',[''])[0]))
            if parsed.path == '/api/sources/intake':
                session=self.current_session(create=False)
                from .source_workflow import SourceWorkflow
                return self.send(200,SourceWorkflow(self.app.collaboration).intake_capabilities(session['name']))
            if parsed.path in {'/api/source-workspace','/api/source-workspace/detail'}:
                if inspection:return self.send(403,{'error':'Restored inspection cannot open personal source workspaces.'})
                from .source_workflow import SourceWorkflow
                session=self.current_session();service=SourceWorkflow(self.app.collaboration)
                return self.send(200,service.snapshot(session['name']) if parsed.path=='/api/source-workspace' else service.detail(session['name'],parse_qs(parsed.query).get('source_id',[''])[0]))
            if parsed.path == '/api/collaboration/collection-catalogue':
                from .collaboration_collection import Collection
                service=Collection(self.app.collaboration);actor=self.current_session()['name']
                return self.send(200,service.work_catalogue(actor) if parse_qs(parsed.query).get('kind',[''])[0]=='work' else service.receipt_catalogue(actor) if parse_qs(parsed.query).get('kind',[''])[0]=='receipt' else service.catalogue(actor))
            if parsed.path == '/api/collaboration/state':
                if inspection: return self.send(200, {'mode': 'inspection', 'read_only': True, 'can_adopt': False, 'sources': [], 'submissions': []})
                return self.send(200, self.app.collaboration.state(self.current_session()['name']))
            if parsed.path.startswith('/api/collaboration/') and inspection:
                return self.send(403, {'error': 'Restored inspection cannot open personal collaboration workspaces.'})
            if parsed.path == '/api/collaboration/collection-download':
                origin = f'http://127.0.0.1:{self.server.server_port}'
                referrer = self.headers.get('Referer')
                reference = urlsplit(referrer) if referrer else None
                if (self.headers.get('Origin') not in (None, origin)
                        or self.headers.get('Sec-Fetch-Site') not in (None, 'none', 'same-origin')
                        or reference and (reference.scheme + '://' + reference.netloc != origin)):
                    return self.send(403, {'error': 'Download this saved package from the local workbench.'})
                session = self.current_session(create=False)
                if not session['id']:
                    return self.send(403, {'error': 'Please select a reviewer first.'})
                query = parse_qs(parsed.query, keep_blank_values=True)
                if set(query) != {'id'} or len(query['id']) != 1:
                    raise ValueError('Choose one saved package to download.')
                data, filename, location = self.saved_collection_download(session['name'], query['id'][0])
                return self.send(200, data, 'application/zip', {
                    'Content-Disposition': 'attachment; filename="' + filename + '"',
                    'Content-Location': location})
            if parsed.path == '/api/collaboration/source-original':
                original = self.app.collaboration.source_original(self.current_session()['name'], parse_qs(parsed.query).get('source_id', [''])[0])
                source_path = Path(original['path']).resolve()
                allowed_root = Path(original['allowed_root']).resolve()
                if not source_path.is_relative_to(allowed_root): raise ValueError('Original is outside registered source storage.')
                extension = source_path.suffix.lower()
                if extension not in {'.pdf', '.html', '.htm', '.xlsx', '.xls'}: raise ValueError('This original format is unavailable.')
                pin_root = self.app.runtime / 'collaboration-originals'; pin_root.mkdir(exist_ok=True)
                pin = pin_root / (original['sha256'] + extension)
                if not pin.exists():
                    temporary = pin_root / (uuid.uuid4().hex + '.tmp')
                    try:
                        with source_path.open('rb') as source, temporary.open('xb') as target:
                            digest = hashlib.sha256()
                            while chunk := source.read(256 * 1024): digest.update(chunk); target.write(chunk)
                            target.flush(); os.fsync(target.fileno())
                        if digest.hexdigest() != original['sha256']: raise ValueError('Registered original changed during transfer.')
                        os.replace(temporary, pin)
                    finally: temporary.unlink(missing_ok=True)
                return stream_original(self, dict(original, path=str(pin)), pin_root)
            if parsed.path == '/api/collaboration/source':
                session = self.current_session()
                source_id = parse_qs(parsed.query).get('source_id', [''])[0]
                return self.send(200, self.app.collaboration.source_draft(session['name'], source_id))
            if parsed.path in {'/api/material-queue', '/api/material-inspection'}:
                from .material_queue import MaterialQueue
                service = MaterialQueue(self.app.collaboration)
                actor = self.current_session()['name']
                query = parse_qs(parsed.query)
                if parsed.path == '/api/material-inspection':
                    return self.send(200, service.detail(actor, query.get('task_id', [''])[0], query.get('current', ['false'])[0]=='true'))
                return self.send(200, service.listing(actor, query.get('bucket', ['pending'])[0],
                    offset=int(query.get('offset', ['0'])[0]), limit=int(query.get('limit', ['50'])[0]), query=query.get('query', [''])[0], task_type=query.get('task_type', [''])[0]))
            if parsed.path == '/api/settings/site-catalog':
                from .site_catalog import Catalog
                self.current_session()
                return self.send(200,Catalog(self.app.collaboration).read())
            if parsed.path == '/api/interpretations/drafts':
                from .interpretation_continuity import Drafts
                query=parse_qs(parsed.query)
                return self.send(200,Drafts(self.app.collaboration).listing(self.current_session()['name'],query.get('unit_id',[None])[0]))
            if parsed.path == '/api/settings/ai':
                from .ai_settings import AISettings
                self.current_session()
                return self.send(200, AISettings(self.app).public())
            if parsed.path in {'/api/interpretations', '/api/interpretations/run', '/api/interpretations/trace', '/api/interpretations/impacts', '/api/requirement-annotations'}:
                from .interpretations import Interpretations, annotations
                actor=self.current_session()['name'];query=parse_qs(parsed.query)
                if parsed.path == '/api/requirement-annotations':
                    return self.send(200, annotations(self.app.collaboration,actor,query.get('material_id',[''])[0]))
                service=Interpretations(self.app.collaboration)
                if parsed.path.endswith('/impacts'):return self.send(200,service.impacts(actor,query.get('material_id',[''])[0]))
                if parsed.path.endswith('/trace'):return self.send(200,service.trace(actor,query.get('unit_id',[''])[0],query.get('revision',[None])[0]))
                if parsed.path.endswith('/run'):return self.send(200,service.run(actor,query.get('id',[''])[0]))
                return self.send(200,service.read(actor,query.get('unit_id',[''])[0]))
            if parsed.path in {'/api/requirements', '/api/requirements/session', '/api/requirements/search'}:
                from .requirements import Requirements
                service = Requirements(self.app.collaboration)
                actor = self.current_session()['name']
                query = parse_qs(parsed.query)
                if parsed.path.endswith('/session'):
                    return self.send(200, service.read(actor, query.get('id', [''])[0]))
                if parsed.path.endswith('/search'):
                    return self.send(200, service.search(actor, query.get('q', [''])[0]))
                return self.send(200, service.listing(actor, query.get('material_id', [''])[0]))
            if parsed.path == '/api/materials':
                query = parse_qs(parsed.query)
                options = {key: int(query[key][0]) for key in ('offset', 'limit') if key in query}
                if 'query' in query: options['query'] = query['query'][0]
                if inspection: return self.send(200, self.app.system2.call('material_list', **({'options': options} if options else {})))
                return self.send(200, self.app.collaboration.list_materials(self.current_session()['name'], options))
            if parsed.path in {'/api/material', '/api/material/history', '/api/material/reader', '/api/material/original', '/api/material/html', '/api/material/candidate', '/api/material/conflict'}:
                query = parse_qs(parsed.query)
                identity = query.get('id', [''])[0]
                if not re.fullmatch(r'[0-9a-f]{32}', identity):
                    raise ValueError('Choose a registered material.')
                actor = self.current_session()['name']
                view = query.get('view', ['personal'])[0]
                if view not in {'personal', 'master', 'archive'}: raise ValueError('Unknown material view.')
                if view == 'archive':
                    from .collaboration import named
                    named(actor)
                if inspection: view = 'master'
                if view == 'master' and not inspection: self.app.collaboration.coordinator(actor)
                if parsed.path == '/api/material':
                    revision = int(query['revision'][0]) if 'revision' in query else None
                    if inspection:
                        material = self.app.system2.call('material_read', material_id=identity, **({'revision': revision} if revision is not None else {}))
                        material['collaboration'] = {'mode': 'inspection', 'view': 'master', 'read_only': True}
                    elif view == 'archive':
                        from .material_queue import MaterialQueue
                        if query.get('history') == ['true'] and revision is not None:
                            material = self.app.collaboration.read_material(actor, identity, revision=revision, view='master')
                            material['collaboration']['view']='archive_history'
                        else:
                            material = MaterialQueue(self.app.collaboration).read_archive(actor, identity, revision)
                    else:
                        material = self.app.collaboration.read_material(actor, identity, revision=revision, view=view)
                    if view in {'master', 'archive'} and material.get('original_url'):
                        material['original_url'] += '&view='+view
                    return self.send(200, material)
                adapter = self.app.system2 if view in {'master', 'archive'} else self.app.collaboration.personal_adapter(actor, identity)
                if parsed.path == '/api/material/history':
                    options = {key: int(query[key][0]) for key in ('offset', 'limit') if key in query}
                    return self.send(200, adapter.call('material_history', material_id=identity, **({'options': options} if options else {})))
                if parsed.path in {'/api/material/candidate', '/api/material/conflict'}:
                    kind = parsed.path.rsplit('/', 1)[1]
                    return self.send(200, adapter.call('material_' + kind, material_id=identity, **{kind + '_id': query.get(kind + '_id', [''])[0]}))
                if parsed.path == '/api/material/html':
                    reader = adapter.call('material_reader', material_id=identity, options={})
                    if reader['kind'] != 'html': raise ValueError('This material is not an HTML snapshot.')
                    return self.send(200, reader['html'].encode(), 'text/html; charset=utf-8',
                        {'Content-Security-Policy': "default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'none'; connect-src 'none'; form-action 'none'; base-uri 'none'; frame-ancestors 'self'; sandbox"})
                if parsed.path == '/api/material/reader':
                    options = {key: query[key][0] for key in ('sheet',) if key in query}
                    options.update({key: int(query[key][0]) for key in ('row', 'column', 'row_count', 'column_count', 'page') if key in query})
                    widths = parse_qs(parsed.query, keep_blank_values=True).get('render_width')
                    if widths is not None:
                        if len(widths) != 1 or not re.fullmatch(r'[0-9]{1,5}', widths[0]) or not 1 <= int(widths[0]) <= 32768:
                            raise ValueError('original_render_width_out_of_range: expected integer 1..32768')
                        options['render_width'] = int(widths[0])
                    reader = adapter.call('material_reader', material_id=identity, options=options)
                    if reader.get('kind') == 'pdf':
                        reader['interactive_pdf_reader'] = 'pdfjs-6.3.289'
                    return self.send(200, reader)
                original = adapter.call('material_original', material_id=identity)
                return stream_original(self, original, adapter.runtime / 'material-originals')
            if parsed.path=="/api/state":
                session=self.current_session()
                data=self.app.snapshot()
                # Machine payloads stay in System1; public projection contains reviewed fields only.
                def project_task(task):
                    result={k:v for k,v in task.items() if k!="payload_json"}
                    try:payload=json.loads(task.get("payload_json") or "{}")
                    except (ValueError,TypeError):payload={}
                    result["application_request_id"]=payload.get("workbench_applied")
                    review=payload.get("external_review")
                    if isinstance(review,dict):
                        result["external_review"]={k:review.get(k) for k in
                            ("artifact_sha256","row","reviewer","verdict","review_date")}
                    return result
                public={**data,"tasks":[project_task(t) for t in data["tasks"]],
                        "history":[project_task(t) for t in data["history"]],
                        "dashboard":build_dashboard(data,getattr(self.app,"snapshot_time",time.time())),
                        "qa_schedule":getattr(self.app,"qa_status",{})}
                if getattr(self.app,'system2_summary',None) is not None:
                    summary=self.app.system2_summary
                    card=public['dashboard']['systems'][1]
                    card.update(availability='live',status='Live extraction review',review_connected=True,
                        pending={'label':'Pending review items','value':summary['pending']},
                        metrics=[{'label':'Sources parsed','value':summary['parsed']},{'label':'Requirements available','value':summary['published']},
                                 {'label':'Sources needing follow-up','value':summary.get('processing_followups')}],
                        note='Explicitly started processing. Accepted items are incremental; source completion is tracked separately.',
                        action={'label':'Open extraction review','view':'system2'})
                from .qa import with_sampling
                public['dashboard']['weekly_qa']=with_sampling(public['dashboard']['weekly_qa'],getattr(self.app,'weekly_sampling',{}))
                return self.send(200,{**public,"actor":{"id":session["id"],"name":session["name"]},
                    "actors":self.app.store.actors(),"requests":self.app.store.requests(),"csrf":self.app.csrf,
                    "collaboration":{"peer_sync":not inspection,"mode":"inspection" if inspection else self.app.collaboration.mode,"coordinator":COORDINATOR,
                        "read_only":inspection,"can_adopt":not inspection and not self.app.reviewer and session["name"]==COORDINATOR}},
                    headers={"Set-Cookie":f"wb_session_{self.server.server_port}={session['token']}; HttpOnly; SameSite=Strict; Path=/; Max-Age=31536000"})
            if parsed.path=="/api/draft":
                session=self.current_session()
                task=parse_qs(parsed.query).get("task",[""])[0]
                return self.send(200,self.app.store.draft(session["id"],task) if session["id"] else {})
            if parsed.path == '/api/settings':
                return self.send(200, {'policy': self.app.policies.get(), 'history': self.app.policies.history(),
                    'system3': 'Not connected', 'api_mode': 'NO_API by default'})
            if parsed.path == '/api/system2/export-status':
                return self.send(200,read_status(self.app.system2.runtime,self.app.workbook_status))
            if parsed.path == '/api/system1/export-status':
                return self.send(200,self.app.adapter.call('export_status'))
            if parsed.path == '/api/system1/workbook':
                try:
                    meta=self.app.adapter.call('export_snapshot')
                    data=Path(meta['path']).read_bytes()
                    if hashlib.sha256(data).hexdigest()!=meta['sha256']:raise ValueError('The snapshot changed during download. Retry after synchronization.')
                except (OSError,ValueError,RuntimeError) as exc:
                    return self.send(409,{'error':str(exc)})
                return self.send(200,data,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    {'Content-Disposition':'attachment; filename="Requirement_Source_Registry.xlsx"','X-Snapshot-Revision':str(meta['revision'])})
            if parsed.path == '/api/system2/workbook' and parse_qs(parsed.query).get('cached')==['true']:
                marker=self.app.system2.runtime/'workbook.json'
                if not marker.is_file():return self.send(409,{'error':'Excel is preparing in the background. Try again after the export status updates.'})
                try:result,data=cached_snapshot(self.app.system2.runtime)
                except ValueError as exc:return self.send(409,{'error':str(exc)})
                return self.send(200,data,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',{'Content-Disposition':'attachment; filename="System2_Requirement_Register.xlsx"','X-Snapshot-Event':str(result['event_cursor'])})
            if self.app.reviewer and parsed.path in {'/api/system2/workbook', '/api/system3/input', '/api/system2/weekly-preview', '/api/system1/workbook'}:
                return self.send(403, {'error': 'Master processing and exports are unavailable in a reviewer workspace.'})
            if parsed.path == '/api/system2/workbook':
                self.app.sync_policy()
                result = self.app.system2.call('workbook')
                path = Path(result['path'])
                return self.send(200, path.read_bytes(),
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    {'Content-Disposition': 'attachment; filename="System2_Requirement_Register.xlsx"'})
            if parsed.path == '/api/system2/state':
                query = parse_qs(parsed.query)
                view = query.get('view', ['browser'])[0]
                if view not in {'browser', 'history', 'summary', 'unit', 'tasks', 'history_page','pages','page','outline'}:
                    raise ValueError('Unknown extraction view.')
                return self.send(200, self.app.extraction_state(view=view,
                    document_id=query.get('document_id', [None])[0], unit_id=query.get('unit_id', [None])[0], offset=int(query.get('offset',[0])[0]), query=query.get('query',[''])[0], chapter=query.get('chapter',[''])[0], task_type=query.get('task_type',[''])[0], include_reviewed=query.get('include_reviewed',['false'])[0]=='true',stage=query.get('stage',[''])[0],page_index=int(query['page_index'][0]) if 'page_index' in query else None,parent_id=query.get('parent_id',[None])[0]))
            if parsed.path == '/api/system3/input':
                self.app.sync_policy()
                return self.send(200, self.app.system2.call('feed', after=int(parse_qs(parsed.query).get('after', [0])[0])))
            if parsed.path == '/api/system2/qa':
                return self.send(200, {'batches':self.app.system2.call('qa_history')})
            if parsed.path == '/api/system2/weekly':
                return self.send(200,self.app.system2.call('weekly',item_id=parse_qs(parsed.query).get('item_id',[None])[0]))
            if parsed.path == '/api/system2/assessments':
                query=parse_qs(parsed.query)
                return self.send(200,self.app.system2.call('assessments',reference_id=query.get('reference_id',[None])[0],assessment_id=query.get('assessment_id',[None])[0]))
            if parsed.path == '/api/system2/references':
                query=parse_qs(parsed.query)
                return self.send(200,self.app.system2.call('references',document_id=query.get('document_id',[None])[0],reference_id=query.get('reference_id',[None])[0]))
            if parsed.path == '/api/system2/weekly-preview':
                iid=parse_qs(parsed.query)['item_id'][0]
                item=self.app.system2.call('weekly',item_id=iid)
                artifact=self.app.adapter.call('artifact',source_id=item['source']['source_id'])
                return self.send(200,self.app.system2.call('weekly_preview',item_id=iid,path=artifact['path']))
            if parsed.path.startswith("/api/original/"):
                source_id=parsed.path.rsplit("/",1)[-1]
                artifact=self.app.adapter.call("artifact",source_id=source_id)
                path=Path(artifact["path"])
                expected=parse_qs(parsed.query).get('expected_hash',[None])[0]
                if expected and hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('The original version changed. Reload the source task.')
                # Originals are download-only. Active source HTML never runs on our origin.
                return self.send(200,path.read_bytes(),"application/octet-stream",
                    {"Content-Disposition":"attachment; filename*=UTF-8''"+quote(path.name)})
            pdf_match = re.fullmatch(r"/api/pdf/([A-Za-z0-9_-]+)/([0-9a-f]{64})/([^/]+)", parsed.path)
            if pdf_match and not parsed.query:
                source_id, expected_hash, filename = pdf_match.groups()
                artifact = self.app.adapter.call("artifact", source_id=source_id)
                if unquote(filename) != Path(artifact["path"]).name:
                    raise ValueError("The original filename does not match the registry. Reopen the document.")
                data, fingerprint = registered_pdf(artifact, expected_hash)
                status, body, range_headers = pdf_range(data, self.headers.get("Range"))
                return self.send(status, body, "application/pdf", {
                    "Content-Disposition": "inline; filename*=UTF-8''" + quote(Path(artifact["path"]).name),
                    "Content-Security-Policy": "default-src 'none'; object-src 'self'; frame-ancestors 'self'",
                    "Accept-Ranges": "bytes", "ETag": '"' + fingerprint + '"', **range_headers,
                })
            if parsed.path == '/api/system2/preview':
                query=parse_qs(parsed.query)
                did=query['document_id'][0];uid=query.get('unit_id',[None])[0]
                summary=self.app.system2.call('state',view='summary')
                doc=next((d for d in summary['documents'] if d['id']==did),None)
                if not doc: raise ValueError('Source task not found.')
                artifact=self.app.adapter.call('artifact',source_id=doc['source']['source_id'])
                return self.send(200,self.app.system2.call('preview',document_id=did,unit_id=uid,path=artifact['path'],expected_hash=doc['source']['content_hash'],full=query.get('full',['false'])[0]=='true',page_index=int(query['page_index'][0]) if 'page_index' in query else None,cell_id=query.get('cell_id',[None])[0],region_index=int(query['region_index'][0]) if 'region_index' in query else None,guard=query.get('guard',[None])[0]))
            if parsed.path.startswith("/api/preview/"):
                source_id=parsed.path.rsplit("/",1)[-1]
                artifact=self.app.adapter.call("artifact",source_id=source_id)
                path=Path(artifact["path"])
                expected=parse_qs(parsed.query).get('expected_hash',[None])[0]
                if expected and hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
                    raise ValueError('The registered original version changed. Reload the extraction task.')
                if path.suffix.lower() == ".pdf":
                    _, fingerprint = registered_pdf(artifact)
                    return self.send(200, {"kind":"pdf", "filename":path.name,
                        "url":"/api/pdf/"+quote(source_id)+"/"+fingerprint+"/"+quote(path.name),
                        "label":"The registered full local PDF, with page, zoom and search controls."})
                if path.suffix.lower()=='.xlsx':
                    query=parse_qs(parsed.query)
                    return self.send(200,self.app.adapter.call('spreadsheet_preview',source_id=source_id,
                        sheet=query.get('sheet',[None])[0],row=query.get('row',[1])[0],column=query.get('column',[1])[0]))
                if path.suffix.lower() not in {".html",".htm",".txt"}:
                    return self.send(200,{"kind":"download","message":"Download and open the original to review it."})
                import html
                from html.parser import HTMLParser
                class TextOnly(HTMLParser):
                    def __init__(self):
                        super().__init__();self.parts=[];self.skip=0
                    def handle_starttag(self,tag,attrs):
                        if tag in {"script","style"}:self.skip+=1
                        if tag in {"p","br","tr","h1","h2","li","section"}:self.parts.append("\n")
                    def handle_endtag(self,tag):
                        if tag in {"script","style"}:self.skip=max(0,self.skip-1)
                    def handle_data(self,data):
                        if not self.skip:self.parts.append(data)
                parser=TextOnly();parser.feed(path.read_text(errors="replace"))
                return self.send(200,{"kind":"text","text":"".join(parser.parts),"label":"Text preview of the local snapshot. Open the original for its published layout."})
            if parsed.path.startswith('/vendor/pdfjs/'):
                vendor = self.app.ui_root / 'vendor' / 'pdfjs'
                relative = parsed.path.removeprefix('/vendor/pdfjs/')
                manifest = json.loads((vendor / 'manifest.json').read_text())
                if relative not in manifest['files']:
                    return self.send(404, {'error': 'Reader resource not found.'})
                asset = vendor / relative
                mime = ui_content_type(asset)
                return self.send(200, asset.read_bytes(), mime)
            if parsed.path in {'/pdf-reader.html', '/pdf-reader.js', '/pdf-reader.css'}:
                asset = self.app.ui_root / parsed.path.lstrip('/')
                # Scoped to this first-party reader; originals never execute scripts.
                policy = "default-src 'none'; script-src 'self'; worker-src 'self'; connect-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self' data: blob:; img-src 'self' data: blob:; frame-ancestors 'self'; base-uri 'none'; form-action 'none'; object-src 'none'"
                return self.send(200, asset.read_bytes(), ui_content_type(asset), {'Content-Security-Policy': policy})
            static={"/":"index.html","/app.js":"app.js","/style.css":"style.css", "/package-download.js":"package-download.js",
                    "/markdown-content.js":"markdown-content.js", "/markdown-content.css":"markdown-content.css", "/vendor/markdown/tools.mjs":"vendor/markdown/tools.mjs",
                    "/requirements.js":"requirements.js", "/requirements.css":"requirements.css", "/materials.js":"materials.js", "/materials.css":"materials.css",
                    "/interpretations.js":"interpretations.js", "/check-design.js":"check-design.js", "/site-catalog.js":"site-catalog.js", "/four-pane.css":"four-pane.css", "/global-settings.js":"global-settings.js", "/global-settings.css":"global-settings.css", "/collaboration.js":"collaboration.js", "/collaboration-relationships.js":"collaboration-relationships.js", "/collaboration.css":"collaboration.css",
                    "/material-editing.js":"material-editing.js", "/source-workspace.js":"source-workspace.js", "/shell-navigation.js":"shell-navigation.js", "/source-workspace.css":"source-workspace.css", "/submission-drawer.js":"submission-drawer.js", "/material-inspection.js":"material-inspection.js", "/material-navigation.js":"material-navigation.js", "/runtime-status.js":"runtime-status.js",
                    "/evidence-viewer.js":"evidence-viewer.js", "/pdf-repairs.js":"pdf-repairs.js", "/pdf-table-editor.js":"pdf-table-editor.js", "/pdf-table-rows.js":"pdf-table-rows.js", "/pdf-pages.js":"pdf-pages.js","/review-state.js":"review-state.js", "/source-check.js":"source-check.js", "/export-status.js":"export-status.js",
                    "/dashboard.js":"dashboard.js", "/qa-chart.js":"qa-chart.js", "/pdf-references.js":"pdf-references.js", "/pdf-assessments.js":"pdf-assessments.js",
                    "/extraction.js":"extraction.js", "/extraction.css":"extraction.css",
                    "/system2-review.js":"system2-review.js", "/system2-review.css":"system2-review.css",
                    "/system2-review-state.js":"system2-review-state.js",
                    "/system2-demo-data.js":"system2-demo-data.js",
                    "/demo-assets/cs005-page-20.webp":"demo-assets/cs005-page-20.webp",
                    "/demo-assets/cs005-page-21.webp":"demo-assets/cs005-page-21.webp"}
            if parsed.path not in static:
                return self.send(404,{"error":"Page not found."})
            path=self.app.ui_root/static[parsed.path]
            return self.send(200,path.read_bytes(),ui_content_type(path)+"; charset=utf-8")
        except Exception as exc:
            self.send(400,{"error":str(exc)})

    def do_POST(self):
        if (not self.valid_host() or self.headers.get("Origin")!=f"http://127.0.0.1:{self.server.server_port}"
                or self.headers.get("X-CSRF-Token")!=self.app.csrf):
            self.close_connection = True
            return self.send(403,{"error":"Invalid request origin. Submit from the local workbench."})
        try:
            length=int(self.headers.get("Content-Length","0"))
            limit = 256 * 1024 * 1024 if self.path in {'/api/collaboration/import','/api/sync/import'} else 55_000_000
            if length<1 or length>limit:
                self.close_connection = True
                return self.send(413,{"error":"The request is empty or exceeds the permitted package/file size."})
            session=self.current_session()
            if getattr(self.app,'read_only_restored',False) and (self.path.startswith('/api/sync/') or self.path=='/api/automation' or self.path=='/api/requirements/step' or self.path in ('/api/settings/ai','/api/settings/site-catalog') or self.path.startswith('/api/interpretations/')):
                self.close_connection=True
                return self.send(403,{'error':'Restored inspection keeps synchronization and automation read-only.'})
            if self.path == '/api/sync/import':
                from .full_snapshot import FullSnapshot
                if not session['id']: raise ValueError('Please select a reviewer first.')
                if self.headers.get('Content-Type', '').split(';',1)[0].strip() != 'application/zip':
                    self.close_connection = True
                    raise ValueError('Choose a full workspace ZIP snapshot.')
                raw = self.rfile.read(length)
                if len(raw) != length: raise ValueError('The package transfer was incomplete.')
                return self.send(200, FullSnapshot(self.app.collaboration).receive(session['name'], raw))
            if self.path == '/api/collaboration/import':
                if not session['id']: raise ValueError('Please select a reviewer first.')
                if self.headers.get('Content-Type', '').split(';', 1)[0].strip() != 'application/zip':
                    self.close_connection = True
                    raise ValueError('Choose a collaboration ZIP package.')
                raw = self.rfile.read(length)
                if len(raw) != length: raise ValueError('The package transfer was incomplete.')
                result = self.app.collaboration.import_package(session['name'], raw)
                self.app.snapshot_time = 0
                return self.send(409 if result.get('status') == 'conflict' else 200, result)
            if self.path == '/api/upload' and self.app.reviewer:
                self.close_connection = True
                return self.send(403, {'error': 'Reviewer packages cannot replace source originals.'})
            if self.path=="/api/upload":
                if not session["id"]:
                    raise ValueError("Please select a reviewer first.")
                suffix=self.headers.get("X-File-Extension","").lower()
                if suffix not in {".pdf",".html",".htm",".xlsx"}:
                    raise ValueError("Choose a PDF, HTML or XLSX original.")
                data=self.rfile.read(length)
                valid = data.startswith(b"%PDF-") if suffix==".pdf" else (data.startswith(b"PK") if suffix==".xlsx" else b"<" in data[:1000])
                if not valid:
                    raise ValueError("The file content does not match its extension.")
                upload_id=str(uuid.uuid4())
                root=self.app.runtime/"uploads";root.mkdir(exist_ok=True)
                file=root/(upload_id+suffix);file.write_bytes(data)
                metadata={"actor_name":session["name"],"actor_id":session["id"],"path":str(file),"hash":hashlib.sha256(data).hexdigest()}
                (root/(upload_id+".json")).write_text(json.dumps(metadata))
                return self.send(200,{"upload_id":upload_id,"hash":metadata["hash"],"size":length,
                    "message":"File staged and format check passed. Verify its identity, completeness and permissions before submitting."})
            if not self.headers.get("Content-Type","").startswith("application/json"):
                raise ValueError("Invalid request format.")
            body=json.loads(self.rfile.read(length))
            if self.path=="/api/actor":
                actor=self.app.store.select_actor(session["token"],body.get("name",""))
                return self.send(200,{"id":actor["id"],"name":actor["name"]})
            if not session["id"]:
                raise ValueError("Please select a reviewer first.")
            if self.path == '/api/settings/site-catalog':
                from .site_catalog import Catalog
                return self.send(200,Catalog(self.app.collaboration).save(session['name'],body))
            if self.path == '/api/settings/ai':
                from .ai_settings import AISettings
                return self.send(200,AISettings(self.app).save(session['name'],body))
            if self.path.startswith('/api/interpretations/'):
                from .interpretations import Interpretations
                service=Interpretations(self.app.collaboration)
                action=self.path.rsplit('/',1)[-1]
                if action=='context':result=service.context(session['name'],body['unit_id'],body.get('linked_material_ids',[]))
                elif action=='save':result=service.save(session['name'],body)
                elif action=='generate':result=service.generate(session['name'],body)
                elif action=='draft':
                    from .interpretation_continuity import Drafts
                    result=Drafts(self.app.collaboration).save(session['name'],body)
                else:raise ValueError('Unknown interpretation action.')
                return self.send(409 if result.get('status')=='conflict' else 200,result)
            if self.path == '/api/requirements/step':
                from .requirements import Requirements
                result = Requirements(self.app.collaboration).apply(session['name'], body)
                return self.send(409 if result.get('status') == 'conflict' else 200, result)
            if self.path.startswith('/api/sync/'):
                from .full_snapshot import FullSnapshot
                service = FullSnapshot(self.app.collaboration)
                action = self.path.rsplit('/',1)[1]
                method = {'export': service.export, 'preview': service.prepare, 'apply': service.apply}.get(action)
                if not method: raise ValueError('Unknown snapshot operation.')
                return self.send(200, method(session['name'], body))
            if self.path == '/api/automation':
                from .automation_settings import AutomationSettings
                return self.send(200, AutomationSettings(self.app).save(session['name'], body))
            if self.path == '/api/sources/open-original':
                from .source_workflow import SourceWorkflow
                return self.send(200,SourceWorkflow(self.app.collaboration).open_original(session['name'],body))
            if self.path == '/api/sources/check-updates':
                from .source_checks import start_check
                return self.send(200,start_check(self.app,session['name'],body))
            if self.path == '/api/sources/inspect':
                from .source_intake import inspect_source
                return self.send(200,inspect_source(self.app,session['name'],body))
            if self.path == '/api/sources/intake':
                from .source_workflow import SourceWorkflow
                return self.send(200,SourceWorkflow(self.app.collaboration).intake(session['name'],body))
            if self.path.startswith('/api/source-workspace/'):
                from .source_workflow import SourceWorkflow
                service=SourceWorkflow(self.app.collaboration);action=self.path.rsplit('/',1)[1]
                routes={'preview':service.preview,'save':service.save,'apply':service.apply_review,'reopen':service.reopen,
                    'task-save':lambda a,r:service.task(a,r),'task-apply':lambda a,r:service.task(a,r,apply=True)}
                if action not in routes:return self.send(404,{'error':'Unknown source action.'})
                result=routes[action](session['name'],body);self.app.snapshot_time=0
                return self.send(409 if result.get('status')=='conflict' else 200,result)
            if self.path == '/api/material/continue':
                if self.headers.get('X-Material-API-Version')!='3':return self.send(426,{'error':'Refresh the material workspace before continuing.'})
                if not isinstance(body,dict) or set(body)-{'request_id','material_id','expected_master_revision'}:raise ValueError('Only the current material identity and revision are accepted.')
                from .material_queue import MaterialQueue
                return self.send(200, MaterialQueue(self.app.collaboration).continue_work(session['name'],body))
            if self.path in {'/api/collaboration/inspection-create', '/api/collaboration/inspection-save'}:
                from .material_queue import MaterialQueue
                service = MaterialQueue(self.app.collaboration)
                action = service.create if self.path.endswith('inspection-create') else service.save
                return self.send(200, action(session['name'], body))
            collaboration_routes = {'source-save': 'save_source', 'preview': 'preview', 'resolve': 'resolve',
                'adopt': 'adopt', 'prepare-own': 'prepare_own', 'confirm-master': 'confirm_master',
                'machine-preview': 'machine_preview', 'machine-resolve': 'machine_resolve', 'machine-apply': 'machine_apply'}
            if self.path.startswith('/api/collaboration/'):
                action = self.path.rsplit('/', 1)[1]
                if not isinstance(body, dict): raise ValueError('Collaboration form fields must be an object.')
                if action.startswith('collection-'):
                    from .collaboration_collection import Collection
                    service=Collection(self.app.collaboration)
                    if action in ('collection-export','collection-download'):
                        if action=='collection-export':
                            identity = str(uuid.UUID(body['request_id']))
                            result,filename=service.export(session['name'],body)
                            location = '/api/collaboration/collection-download?id=' + identity
                        else:
                            result, filename, location = self.saved_collection_download(session['name'], body['id'])
                        return self.send(200,result,'application/zip',{'Content-Disposition':'attachment; filename="'+filename+'"', 'Content-Location': location})
                    method={'collection-preview':service.preview,'collection-adopt':service.adopt}.get(action)
                    if not method:raise ValueError('Unknown collection operation.')
                    return self.send(200,method(session['name'],body))
                if action in {'work-export', 'submission-export'}:
                    result, filename = getattr(self.app.collaboration, action.replace('-', '_'))(session['name'], body)
                    return self.send(200, result, 'application/zip',
                        {'Content-Disposition': 'attachment; filename="' + re.sub(r'[^A-Za-z0-9_.-]', '_', filename) + '"'})
                if action not in collaboration_routes: return self.send(404, {'error': 'Collaboration action not found.'})
                result = getattr(self.app.collaboration, collaboration_routes[action])(session['name'], body)
                if action == 'adopt': self.app.snapshot_time = 0
                if result.get('status') == 'conflict':
                    return self.send(409, dict(result, current=result.get('current') or result.get('material') or result.get('source_review')))
                return self.send(200, result)
            if self.path == '/api/decisions':
                return self.send(409, {'error': 'Save a personal source review and submit it for coordinator adoption.',
                    'code': 'personal_source_review_required'})
            if self.path.startswith('/api/system2/') or self.path == '/api/system1/assess':
                if self.app.reviewer or session['name'] != COORDINATOR:
                    return self.send(403, {'error': 'Master and legacy operations belong to the coordinator.'})
            material_actions = {'/api/material/' + action: action for action in ('open', 'save', 'candidate-draft', 'confirm', 'extract', 'adopt', 'process', 'import-legacy', 'source-issue')}
            if self.path in material_actions:
                if self.headers.get('X-Material-API-Version') != '3':
                    return self.send(426, {'error': 'This material interface was updated. Your draft is retained. Refresh the page before retrying.',
                        'code': 'material_client_upgrade_required', 'required_version': '3'})
                action = material_actions[self.path]
                common = {'request_id', 'material_id', 'expected_revision'}
                fields = {
                    'open': {'request_id', 'source_id'},
                    'candidate-draft': common | {'candidate_id','blocks','issues','checked_scope','association_reviewed'},
                    'save': common | {'blocks', 'issues', 'checked_scope', 'association_reviewed'},
                    'confirm': common | {'explicit_confirmation', 'checked_scope', 'association_reviewed', 'omissions_checked', 'dependencies_checked'},
                    'extract': common | {'replace_candidate_id'},
                    'import-legacy': common,
                    'source-issue': common | {'note'},
                    'adopt': common | {'candidate_id', 'action', 'reviewed_against_source', 'blocks', 'issues', 'checked_scope', 'association_reviewed'},
                    'process': common | {'scope', 'schema_version'},
                }
                if not isinstance(body, dict) or set(body) - fields[action]:
                    raise ValueError('Only material form fields are accepted; source paths, evidence and actors are server-owned.')
                if action == 'source-issue':
                    return self.send(409, {'error': 'Record source issues in your personal source review before coordinator adoption.',
                        'code': 'personal_source_review_required'})
                result = self.app.collaboration.material_action(session['name'], action, body)
                if result.get('status') == 'conflict':
                    return self.send(409, dict(result, current=result.get('material')))
                if result.get('status') in {'unavailable', 'not_connected'}:
                    return self.send(503, dict(result, error=result.get('message') or 'Requirement structure and processor are not connected.'))
                return self.send(200, result)
            if self.path == '/api/settings':
                if self.app.reviewer: return self.send(403, {'error':'This offline installation cannot apply shared confidence policies.'})
                policy = self.app.policies.save(body['values'], session['name'], body['revision'])
                self.app.sync_policy()
                return self.send(200, {'status': 'applied', 'policy': policy})
            if self.path == '/api/system1/assess':
                if set(body) != {'source_ids'}:
                    raise ValueError('Choose registered source IDs only.')
                self.app.sync_policy()
                result = self.app.adapter.call('assess_sources', source_ids=body['source_ids'])
                self.app.snapshot_time = 0
                return self.send(200, result)
            if self.path == '/api/system2/conversion':
                allowed={'request_id','document_id','revision','upload_id','method','note','complete'}
                if set(body)-allowed:raise ValueError('Unsupported conversion fields.')
                upload_id=str(uuid.UUID(body.pop('upload_id')))
                stage_root=self.app.runtime/'uploads'
                metadata=json.loads((stage_root/(upload_id+'.json')).read_text())
                if metadata['actor_id']!=session['id']:raise ValueError('The staged copy belongs to another reviewer.')
                body.update(actor=session['name'],staged_path=metadata['path'],staged_root=str(stage_root),staged_hash=metadata['hash'])
                return self.send(200,self.app.system2.call('conversion',request=body))
            if self.path == '/api/system2/qa':
                if set(body)-{'request_id','week','item_id','verdict','note'}:raise ValueError('Unsupported QA fields.')
                return self.send(200,self.app.system2.call('qa_decision',request=dict(body,actor=session['name'])))
            if self.path == '/api/system2/weekly':
                if set(body)-{'request_id','item_id','guard','result_guard','action','verdict','note'}:raise ValueError('Unsupported weekly inspection fields.')
                return self.send(200,self.app.system2.call('weekly_decision',request=dict(body,actor=session['name'])))
            if self.path == '/api/system2/verify-page':
                if set(body)-{'request_id','document_id','revision','source_sha256','page_index'}:
                    raise ValueError('Unsupported original-check fields.')
                return self.send(200,self.app.system2.call('verify_page',request=dict(body,actor=session['name'])))
            if self.path == '/api/system2/assessments':
                if set(body)-{'request_id','document_id','reference_id','reference_guard','assessment_id','source_sha256','action','guard','body','note'}:
                    raise ValueError('Unsupported assessment fields.')
                return self.send(200,self.app.system2.call('assessment_decision',request=dict(body,actor=session['name'])))
            if self.path == '/api/system2/references':
                if set(body)-{'request_id','document_id','reference_id','source_sha256','action','guard','page_index','supporting_pages','body','note'}:
                    raise ValueError('Unsupported reference fields.')
                return self.send(200,self.app.system2.call('reference_decision',request=dict(body,actor=session['name'])))
            workflow_actions = {'/api/system2/start': 'start', '/api/system2/decision': 'decision',
                                '/api/system2/control': 'control', '/api/system2/suggest':'suggest'}
            if self.path=='/api/system2/source-issue':
                allowed={'request_id','document_id','source_sha256','note'}
                if set(body)-allowed:raise ValueError('Unsupported source issue fields.')
                summary=self.app.system2.call('state',view='summary')
                doc=next((d for d in summary['documents'] if d['id']==body['document_id']),None)
                if not doc or doc['source']['content_hash']!=body['source_sha256']:raise ValueError('Source task version changed.')
                result=self.app.adapter.call('source_issue',request=dict(body,actor=session['name'],source_id=doc['source']['source_id']))
                self.app.snapshot_time=0
                self.app.system2.call('reconcile')
                return self.send(200,result)
            if self.path in workflow_actions:
                allowed = {'request_id','source_ids','document_id','revision','policy_revision','source_sha256',
                           'unit_id','action','note','fields','classification','resolved_issues','draft','locator',
                           'split_parts','split_spec','merge_ids','merge_fingerprints','structure','guard','target_unit_id','target_fingerprint','role','mode','table_owner_id','cell_id','text','restore_request_id','insert_after_id','anchor_fingerprint','hierarchy','table_geometry','cell_change','row_change','table_assembly',
                           'subdivision_schema','count_basis','complete_range_reviewed','subitems','remainder_reason','resolved_requirement_issues'}
                if set(body) - allowed:
                    raise ValueError('Unsupported fields in extraction request.')
                self.app.sync_policy()
                result = self.app.system2.call(workflow_actions[self.path], request=dict(body, actor=session['name']))
                return self.send(200, result)
            if self.path=="/api/draft":
                self.app.store.draft(session["id"],body["task_id"],body["draft"])
                return self.send(200,{"saved":True})
            if self.path=="/api/stop":
                if any(r["status"] in {"queued","running","waiting"} for r in self.app.store.requests()):
                    raise ValueError("Submitted tasks are still processing. Wait for them to finish before exiting.")
                self.send(200,{"message":"Workbench stopped."})
                threading.Thread(target=self.server.shutdown,daemon=True).start()
                return
            return self.send(404,{"error":"Action not found."})
        except ValueError as exc:
            if self.path=='/api/system2/decision' and str(exc).startswith('stale_'):
                try:
                    current=self.app.system2.call('state',view='unit',document_id=body['document_id'],unit_id=body['unit_id'])
                    return self.send(409,{'error':'This unit, its evidence or the policy changed. Your draft is retained. Compare it with the current result before submitting again.','current':current})
                except Exception:pass
            self.send(400,{"error":str(exc)})
        except Exception:
            self.send(503,{"error":"The application receipt is unavailable. Keep the request and retry the same action."})


class LocalHTTPServer(ThreadingHTTPServer):
    # Windows SO_REUSEADDR permits two listeners to bind the same port.
    allow_reuse_address = os.name != "nt"

    def server_bind(self):
        if os.name == "nt":
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def bind_local_server(runtime):
    """Retain the browser origin across restarts; this is device-local runtime state."""
    preferred = 0
    for path in (runtime / "listen-port.json", runtime / "server.json"):
        try:
            port = json.loads(path.read_text())["port"]
            if isinstance(port, int) and not isinstance(port, bool) and 1024 <= port <= 65535:
                preferred = port
                break
        except (OSError, ValueError, KeyError, TypeError):
            pass
    try:
        server = LocalHTTPServer(("127.0.0.1", preferred), Handler)
    except OSError:
        if not preferred:
            raise
        server = LocalHTTPServer(("127.0.0.1", 0), Handler)
    path = runtime / "listen-port.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"port": server.server_port}))
    tmp.replace(path)
    return server


def serve(root, system_root=None, config=None, *, reviewer=False, code_root=None):
    app=Application(root,system_root,config,reviewer=reviewer,code_root=code_root)
    server=bind_local_server(app.runtime)
    server.app=app
    state={"pid":os.getpid(),"port":server.server_port,"instance":app.instance,"root":str(app.root)}
    target=app.runtime/"server.json"
    tmp=target.with_suffix(".tmp");tmp.write_text(json.dumps(state));tmp.replace(target)
    try:
        server.serve_forever(poll_interval=.3)
    finally:
        server.server_close();app.close()
        if target.exists() and json.loads(target.read_text()).get("instance")==app.instance:target.unlink()
