"""Offline personal work, immutable exchange and explicitly adopted main versions.

The owning System1/System2 stores remain authoritative. This journal holds only
exchange baselines, personal workspace references, proposals and adoption receipts.
No received SQLite database is opened or merged.
"""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from backend.shared.sqlite_support import connect as connect_sqlite
import threading
import uuid

from local_workbench.adapter import System2
from backend.shared.collaboration_exchange import pack, unpack, segment
from backend.shared.identities import canonical_name, REVIEWERS, named
from backend.shared.records import encoded, fingerprint, now

COORDINATOR = 'Weijie Tang'
SCORE_FIELDS = ('authority_quality', 'scope_relevance', 'version_currency', 'traceability', 'access_permission')
SOURCE_FIELDS = ('official_url', 'retrieval_url', 'issuer', 'version', 'provenance_status',
    'acquisition_channel', 'applicability_reference', 'inclusion_rationale', 'primary_source_id')










def body(material):
    return {key: deepcopy(material.get(key, [])) for key in ('blocks', 'issues')}


def source_review(source):
    return {'fields': {key: source.get(key) or '' for key in SOURCE_FIELDS},
        'scores': {key: source.get(key) or '' for key in SCORE_FIELDS},
        'selection': source.get('effective_selection') or source.get('operator_selection_decision') or 'PENDING',
        'note': '', 'issue_verified': False, 'issue_checks': {}, 'task_checks': {}, 'new_issues': []}


def validate_source_review(review):
    if not isinstance(review, dict) or not isinstance(review.get('fields'), dict) or not isinstance(review.get('scores'), dict):
        raise ValueError('Source review requires fields and scores objects.')
    if set(review) - {'fields', 'scores', 'selection', 'note', 'issue_verified', 'issue_checks', 'task_checks', 'new_issues'}:
        raise ValueError('Unsupported personal source review field.')
    if set(review.get('fields', {})) - set(SOURCE_FIELDS) or set(review.get('scores', {})) - set(SCORE_FIELDS):
        raise ValueError('This submission cannot add sources or replace originals.')
    if any(not isinstance(v, str) or len(v) > 4000 for v in review.get('fields', {}).values()):
        raise ValueError('Source fields must contain bounded text.')
    if any(v not in ('', 'HIGH', 'MEDIUM', 'LOW') for v in review.get('scores', {}).values()):
        raise ValueError('Source ratings must be HIGH, MEDIUM, LOW or not yet checked.')
    if review.get('selection') not in ('INCLUDE', 'PENDING', 'EXCLUDE'):
        raise ValueError('Invalid source selection proposal.')
    if not isinstance(review.get('note', ''), str) or len(review.get('note', '')) > 10000:
        raise ValueError('Source notes must be bounded text.')
    if type(review.get('issue_verified', False)) is not bool:
        raise ValueError('Issue verification must be an explicit checkbox.')
    checks=review.get('issue_checks',{})
    if not isinstance(checks,dict) or any(not isinstance(k,str) or not isinstance(v,str) or len(v)!=64 for k,v in checks.items()):raise ValueError('Issue checks must bind exact issue evidence.')
    checks=review.get('task_checks',{})
    if not isinstance(checks,dict) or any(not isinstance(k,str) or not isinstance(v,str) or len(v)!=64 for k,v in checks.items()):raise ValueError('Task checks require exact task revisions.')
    issues=review.get('new_issues',[])
    if not isinstance(issues,list) or len(issues)>100 or len({i.get('id') for i in issues if isinstance(i,dict)})!=len(issues):raise ValueError('Invalid source problem list.')
    for issue in issues:
        if set(issue)!={'id','note'} or not isinstance(issue['note'],str) or not issue['note'].strip() or len(issue['note'])>4000:raise ValueError('Describe the source problem.')
        uuid.UUID(issue['id'])
    return review


class PackageSourceAdapter:
    """Read-only source evidence for a reviewer clone without a governance DB."""
    def __init__(self, collaboration, root):
        self.collaboration, self.root = collaboration, Path(root)
        self.config = None

    def call(self, command, **kwargs):
        if command == 'read':
            sources = self.collaboration.source_records()
            evidence=[p.get('evidence',{}) for p in self.collaboration.all('source_catalog')]
            tasks=[t for e in evidence for t in e.get('tasks',[])]
            history=[t for e in evidence for t in e.get('history',[])]
            return {'sources': sources, 'tasks': tasks, 'history': history, 'revision': fingerprint(sources),
                'authority': {'kind': 'offline_review_package', 'revision': 0},
                'counts': {'sources': len(sources), 'tasks': len(tasks),
                    'snapshots': sum(s.get('snapshot_status') == 'STORED' for s in sources),
                    'included': sum(s.get('effective_selection') == 'INCLUDE' for s in sources),
                    'excluded': sum(s.get('effective_selection') == 'EXCLUDE' for s in sources)}}
        if command == 'export_status':
            return {'status': 'unavailable', 'message': 'Reviewer workspace: no master Excel publication.'}
        raise ValueError('Reviewer workspace cannot apply source decisions, retrieve sources or run business jobs.')


class Collaboration:
    def __init__(self, app, reviewer=False):
        self.app = app
        self.mode = 'reviewer' if reviewer else 'coordinator'
        self.layout = getattr(app,'layout',None)
        self.root = self.layout.workspace / 'sources/collaboration' if self.layout else app.runtime / 'collaboration'
        self.root.mkdir(parents=True,exist_ok=True)
        self.database = self.layout.journal if self.layout else app.runtime / 'workbench.sqlite'
        self.lock = getattr(app,'operation_lock',threading.RLock())
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS collaboration_objects(kind TEXT,key TEXT,data TEXT,PRIMARY KEY(kind,key))')
            if self.layout:
                db.execute('CREATE TABLE IF NOT EXISTS source_workspace_objects(kind TEXT,key TEXT,data TEXT,PRIMARY KEY(kind,key))')
                # Transactional one-time relocation of the shared source journal.
                db.execute("INSERT OR IGNORE INTO source_workspace_objects SELECT * FROM collaboration_objects WHERE kind LIKE 'source_%' OR kind LIKE 'archived_source_%' OR kind IN ('sync_source','source_catalog')")
                db.execute("DELETE FROM collaboration_objects WHERE kind LIKE 'source_%' OR kind LIKE 'archived_source_%' OR kind IN ('sync_source','source_catalog')")
        if reviewer and not (app.system2.runtime / 'offline-source.json').exists():
            self._write_reviewer_catalog()

    @property
    def packages(self):
        return self.layout.workspace/'packages/collaboration' if self.layout else self.root/'packages'

    def db(self):
        return self.layout.connect() if self.layout else connect_sqlite(self.database, timeout=30)

    def object_table(self,kind):
        return 'source_workspace_objects' if self.layout and (kind.startswith(('source_','archived_source_')) or kind in {'sync_source','source_catalog'}) else 'collaboration_objects'

    def get(self, kind, key, default=None):
        with self.db() as db:
            row = db.execute('SELECT data FROM '+self.object_table(kind)+' WHERE kind=? AND key=?', (kind, key)).fetchone()
        return json.loads(row[0]) if row else default

    def put(self, kind, key, value):
        with self.db() as db:
            db.execute('INSERT INTO '+self.object_table(kind)+' VALUES(?,?,?) ON CONFLICT(kind,key) DO UPDATE SET data=excluded.data',
                (kind, key, encoded(value)))
        return value

    def put_many(self, records):
        with self.db() as db:
            for kind, key, value in records:
                db.execute('INSERT INTO '+self.object_table(kind)+' VALUES(?,?,?) ON CONFLICT(kind,key) DO UPDATE SET data=excluded.data',
                    (kind, key, encoded(value)))

    def claim_request(self, operation, identity, target, actor):
        binding = {'operation': operation, 'target': target, 'actor': actor}
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('INSERT OR IGNORE INTO collaboration_objects VALUES(?,?,?)',
                ('request_binding', identity, encoded(binding)))
            row = db.execute('SELECT data FROM collaboration_objects WHERE kind=? AND key=?',
                ('request_binding', identity)).fetchone()
            if json.loads(row[0]) != binding:
                raise ValueError('Request identity is already bound to another collaboration operation.')

    def all(self, kind):
        with self.db() as db:
            return [json.loads(row[0]) for row in db.execute('SELECT data FROM '+self.object_table(kind)+' WHERE kind=? ORDER BY rowid', (kind,))]

    def coordinator(self, actor):
        if self.mode != 'coordinator' or (named(actor) != COORDINATOR and not getattr(self.app,'peer_sync',False)):
            raise ValueError('Only the main workspace coordinator can adopt or confirm main versions.')

    def can_adopt(self, actor):
        return self.mode == 'coordinator' and actor in REVIEWERS and (actor == COORDINATOR or getattr(self.app,'peer_sync',False))

    def state(self, actor=None):
        snapshot = self.app.snapshot() if self.mode == 'coordinator' else None
        return {'mode': self.mode, 'peer_sync': getattr(self.app,'peer_sync',False), 'coordinator': COORDINATOR,
            'sources': [{'source_id': s['source_id'], 'title': s.get('source_title') or s['source_id']} for s in self.source_records(snapshot)],
            'submissions': [{key: item.get(key) for key in ('id', 'actor', 'source_id', 'material_id', 'title', 'summary', 'status', 'at')}
                for item in self.all('submission')],
            'work_packages': [{key: p.get(key) for key in ('id', 'source_id', 'material_id', 'title', 'at')} for p in self.all('work')],
            'can_adopt': self.can_adopt(actor)}

    def source_records(self, snapshot=None):
        sources = (snapshot if snapshot is not None else self.app.adapter.call('read'))['sources'] if self.mode == 'coordinator' else [item['source'] for item in self.all('source_catalog')]
        by_id = {item['source_id']: item for item in sources}
        for item in self.all('sync_source'):
            # Foreign records retain their original evidence. Locally governed
            # sources keep the owning registry as authority until human review.
            by_id.setdefault(item['source']['source_id'], item['source'])
        return list(by_id.values())

    def source(self, source_id):
        found = [source for source in self.source_records() if source['source_id'] == source_id]
        if len(found) != 1:
            raise ValueError('Choose one registered source from this workspace.')
        return found[0]

    def source_issues(self, source_id, snapshot=None):
        if self.mode == 'reviewer':
            catalog = self.get('source_catalog', source_id)
            return catalog['offline_source'].get('evidence', {}).get('source_open_issues', []) if catalog else []
        result = []
        for task in (snapshot if snapshot is not None else self.app.adapter.call('read')).get('tasks', []):
            issue = task.get('human_issue')
            if task.get('source_id') != source_id or task.get('is_open') is False or not isinstance(issue, dict):
                continue
            for item in [issue, *issue.get('related_reports', [])]:
                if isinstance(item, dict) and item.get('resolved') is not True and str(item.get('status', '')).lower() not in ('resolved', 'closed', 'completed'):
                    result.append({'task_id': task.get('operation_id'), **item, 'source_id': source_id, 'issue_key':task['operation_id']+':'+fingerprint(item), 'issue_digest':fingerprint(item)})
        return result

    def source_original(self, actor, source_id):
        named(actor); source = self.source(source_id)
        mirror = self.get('sync_source', source_id)
        local_ids = {s['source_id'] for s in self.app.adapter.call('read')['sources']} if self.mode == 'coordinator' else set()
        if mirror and source_id not in local_ids:
            root = Path(mirror['offline_source']['source_root'])
        elif self.mode == 'reviewer':
            catalog = self.get('source_catalog', source_id)
            if catalog.get('work_id'):
                root = self.root / 'originals' / str(uuid.UUID(catalog['work_id']))
            else:
                root = Path(catalog['offline_source']['source_root'])
        else:
            config = json.loads(self.app.adapter.config.read_text())
            root = (self.app.adapter.config.parent / config['source_root']).resolve()
        path = (root / segment(source['folder_code']) / segment(source['stored_filename'])).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError('Registered original is unavailable.')
        if sha256(path.read_bytes()).hexdigest() != source['content_hash']:
            raise ValueError('Registered original fingerprint differs.')
        return {'path': str(path), 'sha256': source['content_hash'], 'filename': path.name,
            'file_format': source.get('file_format'), 'size': path.stat().st_size, 'allowed_root': str(root)}

    def source_draft(self, actor, source_id):
        actor = named(actor)
        key = actor + ':' + source_id
        current = self.source(source_id)
        draft = self.get('source_draft', key)
        if draft is None:
            draft = {'actor': actor, 'source_id': source_id, 'base_source': current,
                'source_review': source_review(current), 'revision': 0, 'history': []}
        return {'source': current, 'source_review': draft['source_review'], 'draft_revision': draft['revision'],
            'issues':self.source_issues(source_id), 'mode': self.mode, 'fields': [{'key': key, 'label': key.replace('_', ' ').title()} for key in SOURCE_FIELDS],
            'score_fields': list(SCORE_FIELDS), 'base_source': draft['base_source'], 'history': draft['history']}

    def save_source(self, actor, request):
        actor = named(actor)
        with self.lock:
            sid = request['source_id']; current = self.source_draft(actor, sid)
            if request.get('expected_revision') != current['draft_revision']:
                return {'status': 'conflict', 'error': 'Your source draft has a newer saved version.', **current}
            review = deepcopy(request['source_review'])
            validate_source_review(review)
            revision = current['draft_revision'] + 1
            record = {'actor': actor, 'source_id': sid, 'base_source': current['base_source'],
                'source_review': review, 'revision': revision,
                'history': [*current['history'], {'actor': actor, 'at': now(), 'revision': revision, 'source_review': review}]}
            self.put('source_draft', actor + ':' + sid, record)
            return {'status': 'saved_personal', **self.source_draft(actor, sid)}

    def adapter(self, runtime):
        master = self.app.system2
        if self.layout:
            identity=Path(runtime).name
            prefix='branch_'+str(uuid.UUID(identity)).replace('-','')+'__'
            self.layout.material_branch(runtime,prefix)
        adapter = System2(master.root, master.system1, master.config, runtime)
        adapter.gate=self.lock
        adapter.pool = getattr(self.app, 'component_pool', None)
        if getattr(self.app, 'monitor', None):
            from local_workbench.runtime_status import ObservedAdapter
            return ObservedAdapter(adapter, self.app.monitor, 2)
        return adapter

    def workspace_runtime(self, workspace):
        identity = str(uuid.UUID(workspace['id']))
        if identity != workspace['id']:
            raise ValueError('Personal workspace identity is invalid.')
        path = (self.root / 'personal' / identity).resolve()
        if not path.is_relative_to((self.root / 'personal').resolve()):
            raise ValueError('Personal workspace path leaves this workspace.')
        if self.mode == 'reviewer':
            baseline = self.get('baseline', workspace['base_digest'])
            if not baseline or not baseline.get('id'):
                raise ValueError('The personal workspace has no retained work-package baseline.')
            source = workspace['base_source']
            descriptor = {'records': [dict(source, selection_status=source.get('effective_selection', 'PENDING'))],
                'source_root': str(self.root / 'originals' / str(uuid.UUID(baseline['id']))),
                'evidence': baseline.get('source_evidence', {'source_open_issues': []})}
            mirror = self.get('sync_source', source['source_id'])
            if mirror and mirror['source'].get('content_hash') == source.get('content_hash'):
                descriptor = mirror['offline_source']
            marker = path / 'offline-source.json'
            content = encoded(descriptor)
            if marker.exists() and marker.read_text(encoding='utf-8') != content:
                temporary = marker.with_suffix('.tmp')
                temporary.write_text(content, encoding='utf-8'); temporary.replace(marker)
        return path

    def workspace(self, actor, material_id):
        actor = named(actor)
        with self.lock:
            key = actor + ':' + material_id
            workspace = self.get('workspace', key)
            if workspace:
                return dict(workspace, runtime=str(self.workspace_runtime(workspace)))
            exported = self.app.system2.call('material_export', request={'material_id': material_id})
            material = exported['material']
            source = self.source(material['source']['source_id'])
            if self.mode == 'reviewer':
                catalog = self.get('material_catalog', material_id)
                baseline = self.get('work', catalog['work_id']) if catalog else None
                if not baseline:
                    raise ValueError('No imported baseline for this material.')
                material, source = baseline['material'], baseline['source']
                exported = dict(exported, material=material, history=baseline.get('history', []),
                    candidate_evidence=baseline.get('candidate_evidence', []), conflict_evidence=baseline.get('conflict_evidence', []))
            identity = str(uuid.uuid4())
            runtime = self.root / 'personal' / identity
            runtime.mkdir(parents=True)
            adapter = self.adapter(runtime)
            # Source evidence in a reviewer clone is frozen per imported baseline.
            if self.mode == 'reviewer':
                catalog = self.get('material_catalog', material_id)
                if not catalog:
                    raise ValueError('No imported work package for this material.')
                descriptor = catalog['offline_source']
                (runtime / 'offline-source.json').write_text(encoded(descriptor), encoding='utf-8')
            adapter.call('material_seed', request={**exported, 'original_path': exported['original']['path']})
            workspace = {'id': identity, 'actor': actor, 'material_id': material_id,
                'source_id': source['source_id'], 'runtime': str(runtime),
                'base_material': material, 'base_source': source,
                'base_digest': fingerprint({'material': material, 'source': source}), 'at': now()}
            return self.put('workspace', key, workspace)

    def personal_adapter(self, actor, material_id):
        return self.adapter(self.workspace(actor, material_id)['runtime'])

    def annotate(self, actor, material, view='personal'):
        material = deepcopy(material)
        workspace = self.get('workspace', named(actor) + ':' + material['id'])
        provenance = material.get('collaboration_provenance', [])
        for block in material.get('blocks', []):
            path = '/blocks/' + block['id'].replace('~', '~0').replace('/', '~1')
            scopes = {r.get('scope_id') for r in block.get('source_refs', [])}
            image_ref = block.get('image', {}).get('source_ref')
            if image_ref:
                scopes.add(image_ref.get('scope_id'))
            checks = material.get('review_checks', {})
            for record in provenance:
                if record.get('path') == path or str(record.get('path', '')).startswith(path + '/'):
                    if scopes and scopes <= set(material.get('checked_scope', [])) and scopes <= set(checks) and all(checks[x].get('source_hash') == material['source']['content_hash'] and checks[x].get('actor') and checks[x].get('at') for x in scopes) and not material.get('source_stale'):
                        record['status'] = 'human_reviewed'
                        record['reviewers'] = sorted({checks[x]['actor'] for x in scopes})
                        record['reviewer'] = ', '.join(record['reviewers'])
                    else:
                        record.pop('reviewer', None); record.pop('reviewers', None)
                        record['status'] = 'machine_unreviewed' if record.get('origin') == 'machine' else 'human_unreviewed'
        material['collaboration'] = {'mode': self.mode, 'view': view,
            'draft_revision': material['revision'], 'coordinator': COORDINATOR,
            'master_digest': workspace.get('base_digest') if workspace else None,
            'provenance': material.get('collaboration_provenance', [])}
        return material

    def list_materials(self, actor, options=None):
        actor = named(actor)
        result = self.app.system2.call('material_list', options=options or {})
        for index, material in enumerate(result['materials']):
            workspace = self.get('workspace', actor + ':' + material['id'])
            if workspace:
                path = self.workspace_runtime(workspace) / 'workflow.sqlite'
                with connect_sqlite(path.as_uri() + '?mode=ro', uri=True) as db:
                    row = db.execute('SELECT data FROM material_read_index WHERE id=?', (material['id'],)).fetchone()
                if row:
                    personal = json.loads(row[0])
                    personal['source_issues'] = material.get('source_issues', [])
                    result['materials'][index] = personal
            result['materials'][index]['collaboration_view'] = 'personal' if workspace else 'master'
        # The counts describe main authority, while rows explicitly name their view.
        result['counts_scope'] = 'master'
        return result

    def read_material(self, actor, material_id, revision=None, view='personal'):
        adapter = self.app.system2 if view == 'master' else self.personal_adapter(actor, material_id)
        return self.annotate(actor, adapter.call('material_read', material_id=material_id, revision=revision), view)

    def material_action(self, actor, action, request):
        actor = named(actor)
        if action == 'confirm' and getattr(self.app,'peer_sync',False):
            from local_workbench.peer_review import confirm
            return confirm(self, actor, request)
        if action == 'open':
            if self.mode == 'reviewer':
                items = [p for p in self.all('work') if p['source_id'] == request['source_id'] and p.get('material_id')]
                if not items:
                    raise ValueError('Ask the coordinator for a work package containing this material.')
                return self.read_material(actor, items[-1]['material_id'])
            material = self.app.system2.call('material_open', request=dict(request, actor=actor))
            return self.read_material(actor, material['id'])
        adapter = self.personal_adapter(actor, request['material_id'])
        result = adapter.call('material_' + action, request=dict(request, actor=actor))
        if result.get('material'):
            result['material'] = self.annotate(actor, result['material'])
        return result

    def tick(self):
        from backend.shared.material_work import pending_work
        from backend.shared.platform_support import exclusive_lock
        for workspace in self.all('workspace'):
            runtime = self.workspace_runtime(workspace)
            pending = pending_work(runtime)
            if not pending['run'] and not pending['resolve']:
                continue
            adapter = self.adapter(runtime)
            result = {'status': 'idle'}
            if pending['run']:
                try:
                    # Retain single-worker ownership throughout prepare/compute/
                    # finalize, without holding the interactive write gate during
                    # pure parsing. A crash leaves the same running candidate.
                    with exclusive_lock(runtime / '.material-worker.lock'):
                        job = adapter.call('material_prepare-job')
                        if job:
                            parsed = adapter.call('material_compute', request=job)
                            result = adapter.call('material_finish-job', request={'job': job, 'parsed': parsed})
                except BlockingIOError:
                    result = {'status': 'busy'}
            if pending['resolve'] or result.get('status') not in ('idle', 'busy'):
                adapter.call('material_repeat-resolution', request={})
            if result.get('status') not in ('idle', 'busy'):
                return result
        return {'status': 'idle'}

    def _work_metadata(self, actor, source_id, material_id=None):
        self.coordinator(actor)
        source = self.source(source_id)
        exported = None
        if not material_id and source.get('effective_selection') == 'INCLUDE' and source.get('snapshot_status') == 'STORED':
            opened = self.app.system2.call('material_open', request={'source_id': source_id, 'actor': actor, 'request_id': str(uuid.uuid4())})
            material_id = opened['id']
        if material_id:
            exported = self.app.system2.call('material_export', request={'material_id': material_id})
            if exported['material']['source']['source_id'] != source_id:
                raise ValueError('Material and source do not match.')
        files = {}
        if exported:
            original = Path(exported['original']['path'])
            name = 'original' + original.suffix.lower()
            files[name] = original.read_bytes()
            if sha256(files[name]).hexdigest() != exported['material']['source']['content_hash']:
                raise ValueError('Original changed during work-package export.')
        elif source.get('snapshot_status') == 'STORED' and source.get('stored_filename'):
            config = json.loads(self.app.adapter.config.read_text())
            original_root = (self.app.adapter.config.parent / config['source_root']).resolve()
            original = (original_root / source['folder_code'] / source['stored_filename']).resolve()
            if not original.is_relative_to(original_root):
                raise ValueError('Unsafe registered original path.')
            name = 'original' + original.suffix.lower(); files[name] = original.read_bytes()
            if sha256(files[name]).hexdigest() != source.get('content_hash'):
                raise ValueError('Registered original fingerprint mismatch.')
        else:
            name = None
        material = exported['material'] if exported else None
        metadata = {'id': str(uuid.uuid4()), 'actor': actor, 'at': now(), 'source_id': source_id,
            'material_id': material['id'] if material else None, 'title': source.get('source_title') or source_id,
            'source': source, 'material': material, 'history': exported['history'] if exported else [],
            'candidate_evidence': exported.get('candidate_evidence', []) if exported else [],
            'conflict_evidence': exported.get('conflict_evidence', []) if exported else [],
            'original': name, 'source_review': source_review(source),
            'source_tasks':[t for t in self.app.adapter.call('read').get('tasks',[]) if t.get('source_id')==source_id],
            'source_history':[t for t in self.app.adapter.call('read').get('history',[]) if t.get('source_id')==source_id],
            'source_evidence': {'source_open_issues': self.source_issues(source_id)}}
        metadata['base_digest'] = fingerprint({'source': source, 'material': material})
        return metadata, files

    def work_export(self, actor, request):
        with self.lock:
            metadata, files = self._work_metadata(actor, request['source_id'], request.get('material_id'))
            blob = pack('work', metadata, files)
            self._archive(metadata['id'], blob)
            self.put('baseline', metadata['base_digest'], metadata)
            self.put('baseline', fingerprint({'source': metadata['source'], 'material': None}), {'source': metadata['source'], 'material': None})
            self.put('work', metadata['id'], metadata)
            return blob, 'review-work-' + metadata['source_id'] + '.zip'

    def _archive(self, identity, blob):
        identity = str(uuid.UUID(identity))
        folder = self.packages; folder.mkdir(parents=True,exist_ok=True)
        path = folder / (identity + '.zip')
        if path.exists():
            if path.read_bytes() != blob:
                raise ValueError('A different package already uses this submission identity.')
        else:
            with path.open('xb') as stream:
                stream.write(blob)
        return path

    def import_package(self, actor, blob):
        actor = named(actor)
        package = unpack(blob)
        if package['kind']=='collection':
            from local_workbench.collaboration_collection import Collection
            return Collection(self).import_collection(actor,blob,package)
        metadata = package['metadata']; identity = str(uuid.UUID(metadata['id']))
        named(metadata.get('actor'))
        if package['kind'] == 'submission' and package['files']:
            raise ValueError('Return packages cannot contain or replace original files.')
        if package['kind'] == 'work' and set(package['files']) != ({metadata['original']} if metadata.get('original') else set()):
            raise ValueError('Work package contains unrelated attachments.')
        with self.lock:
            old = self.get('package_receipt', identity)
            if old:
                if old['digest'] != package['digest']:
                    raise ValueError('Submission identity was reused for different contents.')
                return dict(old, status='already_imported')
            # Retain the validated immutable archive before resumable owning-store writes.
            self._archive(identity, blob)
            if package['kind'] == 'work':
                if self.mode != 'reviewer':
                    raise ValueError('Import work packages in a separate reviewer workspace.')
                self._import_work(metadata, package['files'])
            else:
                self.coordinator(actor)
                self._import_submission(metadata)
            self._archive(identity, blob)
            receipt = {'id': identity, 'kind': package['kind'], 'digest': package['digest'],
                'status': 'imported', 'source_id': metadata['source_id'], 'material_id': metadata.get('material_id')}
            self.put('package_receipt', identity, receipt)
            return receipt

    def _import_work(self, metadata, files, dry_run=False):
        source = metadata['source']; material = metadata.get('material')
        if not isinstance(source, dict) or not isinstance(source.get('source_id'), str) or not source['source_id'].strip():
            raise ValueError('Work package needs one registered source identity.')
        if not isinstance(metadata.get('history', []), list):
            raise ValueError('Material history must be a list.')
        evidence = metadata.get('source_evidence', {'source_open_issues': []})
        if not isinstance(evidence, dict) or not isinstance(evidence.get('source_open_issues', []), list):
            raise ValueError('Source evidence must contain an issue list.')
        for field in ('source_tasks','source_history'):
            records=metadata.get(field,[])
            if not isinstance(records,list) or any(not isinstance(t,dict) or t.get('source_id')!=source['source_id'] for t in records):raise ValueError('Work package contains unrelated source task history.')
        if any(not isinstance(i, dict) or i.get('source_id') != source['source_id'] for i in evidence.get('source_open_issues', [])):
            raise ValueError('Work package contains unrelated source issues.')
        if metadata.get('original'):
            for key in ('snapshot_id', 'file_format', 'content_hash', 'folder_code', 'stored_filename'):
                if not isinstance(source.get(key), str) or not source[key]:
                    raise ValueError('Original source metadata is incomplete.')
            if source['file_format'].lower().lstrip('.') not in ('pdf', 'html', 'htm', 'xlsx', 'xls'):
                raise ValueError('Original format is unsupported.')
        if source['source_id'] != metadata['source_id']:
            raise ValueError('Work-package source identity mismatch.')
        if metadata['base_digest'] != fingerprint({'source': source, 'material': material}):
            raise ValueError('Work-package baseline fingerprint mismatch.')
        folder_name = segment(source['folder_code']) if metadata.get('original') else None
        filename = segment(source['stored_filename']) if metadata.get('original') else None
        if material:
            if material['source']['source_id'] != source['source_id'] or material['source']['content_hash'] != source.get('content_hash') or material['id'] != metadata.get('material_id'):
                raise ValueError('Material source or identity mismatch.')
            self.app.system2.call('material_validate', request={'material': material, 'history': metadata.get('history', []), 'candidate_evidence': metadata.get('candidate_evidence', []), 'conflict_evidence': metadata.get('conflict_evidence', [])})
        target = (self.root / 'originals' / metadata['id']).resolve()
        original_name = metadata.get('original')
        original = None
        if original_name:
            raw = files[original_name]
            if sha256(raw).hexdigest() != source['content_hash']:
                raise ValueError('Work-package original fingerprint mismatch.')
            folder = (target / folder_name).resolve()
            original = (folder / filename).resolve()
            if original.parent != folder or not original.is_relative_to(target):
                raise ValueError('Unsafe source name in work package.')
            if not dry_run:folder.mkdir(parents=True, exist_ok=True)
            if not dry_run and not original.exists():
                original.write_bytes(raw)
            elif original.exists() and original.read_bytes() != raw:
                raise ValueError('Existing package original differs.')
        if dry_run:return
        records = [dict(source, selection_status=source.get('effective_selection', source.get('operator_selection_decision', 'PENDING')))]
        descriptor = {'records': records, 'source_root': str(target), 'evidence': metadata.get('source_evidence', {'source_open_issues': []})}
        if material:
            if not original or material['source']['source_id'] != source['source_id']:
                raise ValueError('Material package lacks its bound original.')
            if not self.get('material_catalog', material['id']):
                self.app.system2.call('material_seed', request={'material': material, 'history': metadata.get('history', []), 'original_path': str(original),
                    'candidate_evidence': metadata.get('candidate_evidence', []), 'conflict_evidence': metadata.get('conflict_evidence', [])})
            self.put('material_catalog', material['id'], {'offline_source': descriptor, 'work_id': metadata['id']})
        self.put('source_catalog', source['source_id'], {'source': source, 'offline_source': descriptor, 'work_id': metadata['id']})
        self.put('baseline', metadata['base_digest'], metadata)
        self.put('baseline', fingerprint({'source': source, 'material': None}), {'source': source, 'material': None})
        self.put('work', metadata['id'], metadata)
        self._write_reviewer_catalog()

    def _write_reviewer_catalog(self):
        # All originals have their own retained package directories. Opening a
        # source uses that source's catalog; existing material reads use its pin.
        catalogs = self.all('source_catalog')
        records = [dict(item['source'], selection_status=item['source'].get('effective_selection', 'PENDING')) for item in catalogs]
        marker = self.app.system2.runtime / 'offline-source.json'
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(encoded({'records': records, 'source_root': str(self.root / 'originals'),
            'evidence': {'source_open_issues': [issue for item in catalogs for issue in item['offline_source'].get('evidence', {}).get('source_open_issues', [])]}}), encoding='utf-8')

    def _submission(self, actor, request):
        actor = named(actor); sid = request['source_id']; mid = request.get('material_id')
        source_draft = self.source_draft(actor, sid)
        exported = None
        if mid:
            workspace = self.workspace(actor, mid)
            if workspace['source_id'] != sid:
                raise ValueError('Source and personal material do not match.')
            exported = self.adapter(self.workspace_runtime(workspace)).call('material_export', request={'material_id': mid})
            base_material, base_source = workspace['base_material'], workspace['base_source']
        else:
            base_material, base_source = None, source_draft['base_source']
        baseline = {'source': base_source, 'material': base_material}
        base_digest = fingerprint(baseline)
        metadata = {'id': str(uuid.uuid4()), 'actor': actor, 'source_id': sid, 'material_id': mid,
            'title': base_source.get('source_title') or sid, 'at': now(), 'summary': str(request.get('summary', ''))[:4000],
            'base_digest': base_digest, 'base': baseline,
            'material': exported['material'] if exported else None,
            'history': exported['history'] if exported else [],
            'candidate_evidence': exported.get('candidate_evidence', []) if exported else [],
            'conflict_evidence': exported.get('conflict_evidence', []) if exported else [],
            'source_review': source_draft['source_review'], 'source_history': source_draft['history'],
            'status': 'pending'}
        # A source draft cannot quietly switch to a different material baseline.
        if source_draft['history'] and source_draft['base_source'] != base_source:
            raise ValueError('Source and material drafts use different baselines; reconcile the source proposal first.')
        if self.mode == 'coordinator':
            self.put('baseline', base_digest, {**baseline, 'base_digest': base_digest})
        elif not self.get('baseline', base_digest):
            # Work packages with no material allow a newly opened empty material;
            # their source baseline stays known, but its new material requires a
            # coordinator-issued material baseline before collaborative merging.
            raise ValueError('Export a coordinator work package containing this material before submitting it.')
        return metadata

    def submission_export(self, actor, request):
        with self.lock:
            metadata = self._submission(actor, request)
            blob = pack('submission', metadata, {})
            self._archive(metadata['id'], blob)
            self.put('sent_submission', metadata['id'], metadata)
            return blob, 'personal-review-' + metadata['source_id'] + '.zip'

    def _import_submission(self, metadata, dry_run=False):
        sid = metadata['source_id']; source = self.source(sid)
        validate_source_review(metadata.get('source_review'))
        history = metadata.get('source_history', [])
        if not isinstance(history, list):
            raise ValueError('Source review history must be a list.')
        for index, entry in enumerate(history, 1):
            if entry.get('actor') != metadata['actor'] or entry.get('revision') != index or not entry.get('at'):
                raise ValueError('Source review history identity or revision is inconsistent.')
            validate_source_review(entry.get('source_review'))
        if history and history[-1]['source_review'] != metadata['source_review']:
            raise ValueError('Submitted source review does not match its saved history.')
        baseline = metadata['base']
        if fingerprint(baseline) != metadata['base_digest'] or baseline['source']['source_id'] != sid:
            raise ValueError('Submission common baseline is inconsistent.')
        known = self.get('baseline', metadata['base_digest'])
        status = 'pending' if known else 'unknown_baseline'
        if metadata.get('material'):
            m, base = metadata['material'], baseline.get('material')
            if not base or m['id'] != base['id'] or m['id'] != metadata['material_id'] or m['source'] != base['source']:
                raise ValueError('A submission cannot replace the original or change material identity.')
            for record in metadata.get('history', []):
                if record.get('id') != m['id'] or record.get('source') != base['source']:
                    raise ValueError('Submission contains unrelated history.')
        if metadata.get('material'):
            self.app.system2.call('material_validate', request={'material': metadata['material'], 'history': metadata.get('history', []), 'candidate_evidence': metadata.get('candidate_evidence', []), 'conflict_evidence': metadata.get('conflict_evidence', [])})
        if set(metadata.get('source_review', {}).get('fields', {})) - set(SOURCE_FIELDS):
            raise ValueError('Source creation and original replacement are not submission operations.')
        existing = self.get('submission', metadata['id'])
        if existing:
            if any(existing.get(key) != value for key, value in metadata.items() if key != 'status'):
                raise ValueError('Submission identity already has different contents.')
            return
        if not dry_run:self.put('submission', metadata['id'], dict(metadata, status=status))

    @staticmethod
    def own_preparation_digest(metadata):
        # Generated IDs/timestamps and later application receipts are not new work.
        fields = ('actor', 'source_id', 'material_id', 'base_digest', 'base', 'material',
                  'history', 'candidate_evidence', 'conflict_evidence', 'source_review', 'source_history', 'summary')
        return fingerprint({key: metadata.get(key) for key in fields})

    def prepare_own(self, actor, request):
        self.coordinator(actor)
        with self.lock:
            metadata = self._submission(actor, request)
            identity = str(uuid.uuid5(uuid.NAMESPACE_URL, 'local-workbench/own-preparation/' + self.own_preparation_digest(metadata)))
            existing = self.get('submission', identity)
            if not existing:
                # Reuse older identical preparations too, preserving their saved choices.
                matches = [entry for entry in self.all('submission') if entry.get('actor') == actor
                           and self.own_preparation_digest(entry) == self.own_preparation_digest(metadata)]
                existing = next((entry for entry in matches if entry.get('adoption_merge_id')), None)
                if existing is None and matches:
                    existing = max(matches, key=lambda entry: entry.get('at', ''))
            if not existing:
                metadata['id'] = identity
                self._import_submission(metadata)
                existing = metadata
            return self.preview(actor, {'submission_id': existing['id']})

    def preview(self, actor, request):
        with self.lock:
            return self._preview(actor, request)

    def _preview(self, actor, request):
        self.coordinator(actor)
        submission = self.get('submission', request['submission_id'])
        if not submission:
            raise ValueError('Submission not found.')
        if not self.get('baseline', submission['base_digest']):
            raise ValueError('Common baseline is unavailable; import is retained without guessing a merge.')
        if submission['status'] in ('adopted', 'adopted_partial'):
            raise ValueError('This submission already has a main-version adoption receipt.')
        if submission.get('adoption_merge_id'):
            return self.merge_view(self.get('merge', submission['adoption_merge_id']))
        sid, mid = submission['source_id'], submission.get('material_id')
        current_source = self.source(sid)
        material = self.app.system2.call('material_read', material_id=mid) if mid else None
        master_digest, source_digest = fingerprint(material), fingerprint(current_source)
        for retained in reversed(self.all('merge')):
            if (retained.get('actor') == actor and retained.get('submission_id') == submission['id']
                    and retained.get('kind') != 'machine' and retained.get('status') == 'preview'
                    and retained.get('master_digest') == master_digest and retained.get('source_digest') == source_digest):
                return self.merge_view(retained)
        merge = {'id': str(uuid.uuid4()), 'actor': actor, 'submission_id': submission['id'],
            'merge_version': 2,
            'source_id': sid, 'material_id': mid, 'current_material': material, 'current_source': current_source,
            'master_digest': fingerprint(material), 'source_digest': fingerprint(current_source),
            'decisions': {}, 'status': 'preview', 'at': now()}
        self.put('merge', merge['id'], merge)
        return self.merge_view(merge)

    def merge_view(self, merge, *, validate_relationships=False):
        from backend.shared.collaboration_merge import merge_documents
        from backend.shared.collaboration_relationships import display_context, validate_decisions
        incoming = self.get('machine_proposal' if merge.get('kind') == 'machine' else 'submission', merge['submission_id']); baseline = incoming['base']
        base = {**body(baseline.get('material') or {}), 'source_review': source_review(baseline['source'])}
        current = {**body(merge.get('current_material') or {}), 'source_review': source_review(merge['current_source'])}
        proposed = {**body(incoming.get('material') or {}), 'source_review': incoming['source_review']}
        for candidate in incoming.get('candidate_evidence', []):
            if candidate.get('status') in ('running', 'ready', 'partial'):
                proposed['issues'].append({'id': 'submission-candidate-' + candidate['id'],
                    'message': 'Submitted work has an unresolved extraction candidate: ' + candidate['id'],
                    'resolved': False, 'scope_ids': [x['id'] for x in (incoming.get('material') or {}).get('scope', [])]})
        comparison_version = merge.get('merge_version', 1)
        result = merge_documents(base, current, proposed, merge['decisions'], version=comparison_version)
        if merge.get('kind') == 'machine' and current['blocks']:
            required = {d['id'] for d in result['differences'] if d.get('resolution') not in ('auto_current', 'same') and d['id'] not in merge['decisions']}
            if required:
                result = merge_documents(base, current, proposed, {**merge['decisions'], **{key: {'action': 'current'} for key in required}}, version=comparison_version)
                for difference in result['differences']:
                    if difference['id'] in required:
                        difference.update(conflict=True, resolution=None)
                        if difference['kind'] != 'order':
                            difference['kind'] = 'machine_difference'
                result['unresolved'] = list(dict.fromkeys([*result['unresolved'], *sorted(required)]))
        if validate_relationships:
            validate_decisions(result['differences'], merge['decisions'], result['merged'].get('blocks', []))
        material = deepcopy(merge['current_material']) if merge['current_material'] else None
        provenance = deepcopy((material or {}).get('collaboration_provenance', []))
        for difference in result['differences']:
            if difference.get('resolution') in ('auto_incoming', 'incoming', 'edit', 'same'):
                provenance_path = difference['path']
                existing = [p for p in (incoming.get('material') or {}).get('collaboration_provenance', []) if provenance_path == p.get('path') or provenance_path.startswith(str(p.get('path', '')) + '/')]
                record = deepcopy(existing[-1]) if existing else {'origin': 'human', 'actor': incoming['actor']}
                if merge.get('kind') == 'machine':
                    record.update(origin='machine', actor=None, candidate_id=merge['candidate_id'])
                if difference.get('resolution') == 'edit':
                    record.update(origin='human', actor=merge['actor'])
                provenance.append({**record, 'path': provenance_path,
                    'submission_id': incoming['id'], 'status': 'pending_adoption'})
        if material:
            material.update(blocks=result['merged']['blocks'], issues=result['merged']['issues'])
            material['collaboration'] = {'mode': self.mode, 'view': 'merge', 'provenance': provenance}
        return {**{k: merge[k] for k in ('kind', 'candidate_id', 'input_revision', 'stale', 'complete') if k in merge},
            'merge_version': comparison_version,
            'merge_id': merge['id'], 'resume_request_id': merge.get('adoption_request_id'), 'material': material, 'source_review': result['merged']['source_review'],
            'reference_context': display_context(base, current, proposed, result['differences']),
            'differences': result['differences'], 'unresolved': result['unresolved'], 'master_digest': merge['master_digest'],
            'source_id': merge['source_id'], 'submission_id': incoming['id'], 'actor': incoming['actor'], 'provenance': provenance}

    def resolve(self, actor, request):
        self.coordinator(actor)
        with self.lock:
            merge = self.get('merge', request['merge_id'])
            if not merge or merge['actor'] != actor or merge['status'] != 'preview' or merge.get('adoption_request_id'):
                raise ValueError('This comparison is unavailable or already adopted.')
            merge['decisions'].update(request.get('decisions', {}))
            result = self.merge_view(merge, validate_relationships=True)
            self.put('merge', merge['id'], merge)
            return result

    def adopt(self, actor, request):
        self.coordinator(actor)
        rid = str(uuid.UUID(request['request_id']))
        with self.lock:
            receipt = self.get('adoption_receipt', rid)
            if receipt:
                if receipt['merge_id'] != request['merge_id']:
                    raise ValueError('Adoption request identity was reused.')
                return receipt
            merge = self.get('merge', request['merge_id'])
            if not merge or merge['actor'] != actor or merge['status'] == 'adopted':
                raise ValueError('Choose an unadopted comparison prepared by this coordinator.')
            self.claim_request('adopt', rid, merge['id'], actor)
            if merge.get('adoption_request_id') not in (None, rid):
                raise ValueError('Resume this adoption using its original request identity.')
            view = self.merge_view(merge)
            if view['unresolved']:
                raise ValueError('Resolve all required conflicts before adopting this working version.')
            sid, mid = merge['source_id'], merge['material_id']
            incoming = self.get('submission', merge['submission_id'])
            if incoming.get('adoption_merge_id') not in (None, merge['id']):
                raise ValueError('This submission is already being adopted; resume its saved comparison.')
            if not merge.get('adoption_request_id'):
                current_source = self.source(sid)
                if fingerprint(current_source) != merge['source_digest']:
                    return {'status': 'conflict', 'error': 'Main source changed. Prepare a new comparison; choices are retained.'}
                if mid:
                    current = self.app.system2.call('material_read', material_id=mid)
                    if fingerprint(current) != merge['master_digest']:
                        return {'status': 'conflict', 'error': 'Main material changed. Prepare a new comparison; choices are retained.'}
                    merge['material_request'] = {
                        'request_id': str(uuid.uuid5(uuid.UUID(rid), 'material')), 'actor': actor,
                        'material_id': mid, 'expected_revision': current['revision'],
                        'expected_source_hash': current['source']['content_hash'],
                        'blocks': view['material']['blocks'], 'issues': view['material']['issues'],
                        'review_origins': [incoming['material']], 'provenance': view['provenance'],
                        'contributors': [incoming['actor']], 'submission_id': incoming['id'],
                        'decisions': merge['decisions'], 'base_digest': incoming['base_digest']}
                if view['source_review'] != source_review(merge['current_source']):
                    merge['source_request'] = {
                        'request_id': str(uuid.uuid5(uuid.UUID(rid), 'source')), 'actor': actor,
                        'source_id': sid, 'expected_source_revision': merge['current_source']['source_revision'],
                        'expected_source_hash': merge['current_source'].get('content_hash'),
                        'base_review': source_review(merge['current_source']), 'review': view['source_review'],
                        'submission_id': incoming['id'], 'contributor': incoming['actor']}
                merge['adoption_request_id'] = rid
                incoming['adoption_merge_id'] = merge['id']
                self.put_many([('merge', merge['id'], merge), ('submission', incoming['id'], incoming)])
            # Persist each owning-store receipt separately. Replay uses the exact
            # same payload, even after a process failure between store and journal.
            if merge.get('source_request') and not merge.get('source_receipt'):
                result = self.app.adapter.call('collaboration_apply', request=dict(merge['source_request'], peer_sync=getattr(self.app,'peer_sync',False)))
                if result.get('status') not in ('applied', 'saved_partial'):
                    return result
                merge['source_receipt'] = result
                merge['source_status'] = result['status']
                self.put('merge', merge['id'], merge)
                self.app.snapshot_time = 0
            if mid and not merge.get('material_receipt'):
                result = self.app.system2.call('material_adopt-master', request=merge['material_request'])
                if result.get('status') != 'applied':
                    return dict(result, source_status=merge.get('source_status', 'unchanged'),
                        resume_request_id=rid)
                merge['material_receipt'] = result
                self.put('merge', merge['id'], merge)
            result = merge.get('material_receipt')
            partial = merge.get('source_status') == 'saved_partial'
            receipt = {'status': 'adopted_partial' if partial else 'adopted', 'request_id': rid, 'merge_id': merge['id'],
                'source_status': merge.get('source_status', 'unchanged'),
                'source_receipt': merge.get('source_receipt'), 'material_status': 'applied' if mid else 'not_present',
                'material': self.annotate(actor, result['material'], 'master') if result else None,
                'submission_id': incoming['id'], 'actor': actor, 'contributor': incoming['actor'], 'at': now()}
            self.put_many([('adoption_receipt', rid, receipt),
                ('merge', merge['id'], dict(merge, status='adopted')),
                ('submission', incoming['id'], dict(incoming, status=receipt['status'], adoption=receipt))])
            if incoming['actor'] == actor:
                for kind, key in [('workspace', actor + ':' + str(mid)), ('source_draft', actor + ':' + sid)]:
                    old = self.get(kind, key)
                    if old:
                        self.put('archived_' + kind, old.get('id', str(uuid.uuid4())), old)
                        with self.db() as db:
                            db.execute('DELETE FROM '+self.object_table(kind)+' WHERE kind=? AND key=?', (kind, key))
            return receipt

    def machine_preview(self, actor, request):
        with self.lock:
            return self._machine_preview(actor, request)

    def _machine_preview(self, actor, request):
        actor = named(actor); mid = request['material_id']
        adapter = self.personal_adapter(actor, mid)
        material = adapter.call('material_read', material_id=mid)
        candidate = adapter.call('material_candidate', material_id=mid, candidate_id=request['candidate_id'])
        if candidate['status'] not in ('ready', 'partial', 'failed'):
            raise ValueError('This candidate is already resolved or still processing.')
        source = self.source(material['source']['source_id'])
        material_digest, candidate_digest, source_digest = fingerprint(material), fingerprint(candidate), fingerprint(source)
        matching = []
        for retained in reversed(self.all('merge')):
            if (retained.get('kind') == 'machine' and retained.get('status') == 'preview'
                    and retained.get('actor') == actor and retained.get('material_id') == mid
                    and retained.get('candidate_id') == candidate['id']
                    and retained.get('master_digest') == material_digest
                    and retained.get('candidate_digest') == candidate_digest
                    and retained.get('source_digest') == source_digest):
                matching.append(retained)
        if matching:
            # Earlier releases created a blank comparison on every reopen. Such
            # a duplicate must not hide the person's saved choices. Historical
            # variants remain untouched; only select which preview to resume.
            retained = next((item for item in matching if item.get('decisions')), matching[0])
            return self.merge_view(retained)
        identity = str(uuid.uuid4())
        incoming = {'id': identity, 'actor': actor, 'kind': 'machine', 'source_id': source['source_id'],
            'base': {'source': source, 'material': dict(material, blocks=candidate.get('base_blocks', []))},
            'material': dict(material, blocks=candidate.get('blocks', [])), 'source_review': source_review(source)}
        self.put('machine_proposal', identity, incoming)
        merge = {'id': identity, 'actor': actor, 'kind': 'machine', 'submission_id': identity,
            'merge_version': 2,
            'source_id': source['source_id'], 'material_id': mid, 'current_material': material,
            'current_source': source, 'master_digest': material_digest, 'source_digest': source_digest,
            'decisions': {}, 'status': 'preview', 'at': now(), 'candidate_id': candidate['id'],
            'candidate_digest': candidate_digest, 'input_revision': candidate['input_revision'],
            'stale': candidate.get('stale', False), 'complete': candidate.get('complete', False)}
        self.put('merge', identity, merge)
        return self.merge_view(merge)

    def machine_resolve(self, actor, request):
        actor = named(actor)
        with self.lock:
            merge = self.get('merge', request['merge_id'])
            if not merge or merge.get('kind') != 'machine' or merge['actor'] != actor or merge['status'] != 'preview' or merge.get('apply_request'):
                raise ValueError('Choose your own unresolved machine comparison.')
            merge['decisions'].update(request.get('decisions', {}))
            result = self.merge_view(merge, validate_relationships=True)
            self.put('merge', merge['id'], merge)
            return result

    def machine_apply(self, actor, request):
        actor = named(actor)
        with self.lock:
            merge = self.get('merge', request['merge_id'])
            if not merge or merge.get('kind') != 'machine' or merge['actor'] != actor:
                raise ValueError('Choose your own machine comparison.')
            if request.get('reviewed_against_source') is not True:
                raise ValueError('Confirm that you checked these differences against the original.')
            rid = str(uuid.UUID(request['request_id']))
            self.claim_request('machine_apply', rid, merge['id'], actor)
            if merge.get('apply_request') and merge['apply_request']['request_id'] != rid:
                raise ValueError('Resume with the original resolution request identity.')
            if merge.get('receipt'):
                return merge['receipt']
            adapter = self.personal_adapter(actor, merge['material_id'])
            if not merge.get('apply_request'):
                current = adapter.call('material_read', material_id=merge['material_id'])
                candidate = adapter.call('material_candidate', material_id=merge['material_id'], candidate_id=merge['candidate_id'])
                if fingerprint(current) != merge['master_digest'] or fingerprint(candidate) != merge['candidate_digest']:
                    return {'status': 'conflict', 'error': 'Input changed. Reopen this comparison before applying choices.'}
                view = self.merge_view(merge)
                if view['unresolved']:
                    raise ValueError('Resolve the remaining machine differences first.')
                unchanged = body(view['material']) == body(current)
                merge['apply_request'] = {'material_id': merge['material_id'], 'request_id': rid,
                    'actor': actor, 'expected_revision': current['revision'], 'candidate_id': merge['candidate_id'],
                    'action': 'keep' if unchanged else 'merge', 'reviewed_against_source': True,
                    'blocks': view['material']['blocks'], 'issues': view['material']['issues'],
                    'association_reviewed': False, '_choice_provenance': view['provenance']}
                self.put('merge', merge['id'], merge)
            result = adapter.call('material_adopt', request=merge['apply_request'])
            if result.get('material'):
                result['material'] = self.annotate(actor, result['material'])
            if result.get('status') == 'applied':
                self.put('merge', merge['id'], dict(merge, status='resolved', receipt=result))
            return result

    def confirm_master(self, actor, request):
        with self.lock:
            from local_workbench.material_queue import MaterialQueue
            if any(t['status']=='finding_open' for t in MaterialQueue(self).tasks(request.get('material_id'))):
                raise ValueError('Resolve the open archive inspection finding before confirming a new master archive.')
            return self._confirm_master(actor, request)

    def _confirm_master(self, actor, request):
        self.coordinator(actor)
        if request.get('omissions_checked') is not True or request.get('dependencies_checked') is not True:
            raise ValueError('Confirm complete omissions and association checks explicitly.')
        result = self.app.system2.call('material_confirm', request=dict(request, actor=actor))
        if result.get('material'):
            result['material'] = self.annotate(actor, result['material'], 'master')
        return result
