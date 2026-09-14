"""Material categories and version-bound, explicitly requested archive inspections.

Material bodies and acceptance history stay in System2. This module reads its
existing projections and stores only inspection tasks/receipts in the workbench
collaboration journal. No scheduler and no inferred human decisions.
"""
from copy import deepcopy
import json
import sqlite3
from local_workbench.sqlite_support import connect as connect_sqlite
import uuid
from pathlib import Path


def active_candidates(candidates):
    return any(candidate.get('status') in ('running', 'ready', 'partial') for candidate in candidates)


def acceptance_key(material):
    from .collaboration import fingerprint
    return fingerprint({k: material.get(k) for k in ('id', 'content_revision', 'source', 'confirmation')})


def read_index(runtime):
    path = (Path(runtime) / 'workflow.sqlite').resolve()
    return connect_sqlite(path.as_uri() + '?mode=ro', uri=True, timeout=30)


class MaterialQueue:
    def __init__(self, collaboration):
        self.c = collaboration

    def archives(self):
        with read_index(self.c.app.system2.runtime) as db:
            rows = db.execute("""SELECT data FROM material_revision_index r
                WHERE revision=(SELECT MAX(revision) FROM material_revision_index a
                  WHERE a.material_id=r.material_id AND json_extract(a.data,'$.content_status')='content_review_complete'
                  AND json_extract(a.data,'$.last_action.kind')='content_confirmed'
                  AND json_extract(a.data,'$.confirmation.actor') IS NOT NULL
                  AND json_extract(a.data,'$.confirmation.content_revision')=json_extract(a.data,'$.content_revision'))""")
            return {m['id']: m for m in (json.loads(row[0]) for row in rows)}

    def tasks(self, material_id=None):
        return [t for t in self.c.all('material_inspection') if material_id is None or t['material_id'] == material_id]

    def listing(self, actor, bucket, offset=0, limit=50, query='', task_type=''):
        from .collaboration import named, fingerprint
        actor = named(actor)
        if task_type not in ('', 'first', 'review', 'inspection') or bucket not in ('pending', 'archive') or type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 50 or not isinstance(query, str) or len(query) > 300:
            raise ValueError('Invalid material category or page.')
        # Refresh source bindings through the owning service before reading projections.
        base = self.c.app.system2.call('material_list', options={'limit': 1})
        with read_index(self.c.app.system2.runtime) as db:
            current = [json.loads(r[0]) for r in db.execute('SELECT data FROM material_read_index ORDER BY rowid DESC')]
            candidates = {}
            for row in db.execute("SELECT material_id,data FROM material_candidate_index ORDER BY rowid"):
                candidates.setdefault(row[0], []).append(json.loads(row[1]))
        archives, tasks = self.archives(), self.tasks()
        incoming = {s.get('material_id') for s in self.c.all('submission') if s.get('status') not in ('adopted', 'adopted_partial')}
        # Source issue evidence is public authority, not copied personal decisions.
        try:
            snapshot = self.c.app.adapter.call('read')
            issue_sources = {t.get('source_id') for t in snapshot.get('tasks', []) if t.get('human_issue')}
        except (OSError, ValueError, RuntimeError):
            issue_sources = set()
        rows = []
        for master in current:
            identity = master['id']; archived = archives.get(identity)
            relevant = [t for t in tasks if t['material_id'] == identity]
            open_tasks = [t for t in relevant if t['status'] in ('pending', 'finding_open')]
            row = deepcopy(archived if bucket == 'archive' and archived else master)
            row['collaboration_view'] = 'archive' if bucket == 'archive' else 'master'
            workspace = self.c.get('workspace', actor + ':' + identity)
            reopened = self.c.get('material_reopen', actor + ':' + identity, {})
            personal_changed = reopened.get('master_revision') == master.get('revision')
            personal_candidates = []
            if workspace and bucket == 'pending':
                with read_index(self.c.workspace_runtime(workspace)) as db:
                    saved = db.execute('SELECT data FROM material_read_index WHERE id=?', (identity,)).fetchone()
                    personal = json.loads(saved[0]) if saved else None
                    personal_candidates = [json.loads(r[0]) for r in db.execute("SELECT data FROM material_candidate_index WHERE material_id=? ORDER BY rowid", (identity,))]
                    raw = db.execute("SELECT json_extract(data,'$.blocks'),json_extract(data,'$.issues') FROM material_documents WHERE id=?", (identity,)).fetchone()
                if personal:
                    # An unchanged stale baseline isn't a new contribution. Saved edits
                    # adopted into the master stop being pending personal work.
                    changed_from_base = personal.get('revision') != workspace['base_material'].get('revision')
                    with read_index(self.c.app.system2.runtime) as db:
                        main_body = db.execute("SELECT json_extract(data,'$.blocks'),json_extract(data,'$.issues') FROM material_documents WHERE id=?", (identity,)).fetchone()
                    personal_changed = personal_changed or (changed_from_base and raw != main_body)
                    row = personal
                    row['collaboration_view'] = 'personal'
            qualified = bool(archived and master.get('content_status') == 'content_review_complete' and master.get('confirmation') and not master.get('source_stale') and not active_candidates(candidates.get(identity, [])) and master['source']['source_id'] not in issue_sources)
            personal_followup = active_candidates(personal_candidates) or bool(personal_candidates and personal_candidates[-1].get('status') == 'failed')
            master_failure = bool(candidates.get(identity) and candidates[identity][-1].get('status') == 'failed')
            if bucket == 'archive' and not archived:
                continue
            if bucket == 'pending' and qualified and not (open_tasks or personal_changed or personal_followup or master_failure or identity in incoming):
                continue
            row['source_stale'] = master.get('source_stale', False)
            row['candidates'] = personal_candidates if bucket == 'pending' and workspace else candidates.get(identity, [])
            row['queue'] = {'bucket': bucket, 'archive_revision': archived.get('revision') if archived else None,
                'master_revision': master['revision'], 'master_content_revision': master['content_revision'],
                'master_content_status': master.get('content_status'), 'master_review_current': qualified,
                'archive_current': qualified, 'personal_changes': personal_changed,
                'incoming_submission': identity in incoming,
                'inspection_only': qualified and bool(open_tasks) and not personal_changed and not personal_followup and not master_failure and identity not in incoming,
                'inspections': relevant, 'open_inspections': open_tasks,
                'needs_revision': bool(archived and not qualified)}
            if query.casefold() in (str(row.get('title', '')) + ' ' + row['source']['source_id']).casefold():
                rows.append(row)
        if bucket == 'pending':
            opened = {(m['source']['source_id'], m['source'].get('snapshot_id'), m['source'].get('content_hash')) for m in current}
            for source in base.get('sources', []):
                binding = (source['source_id'], source.get('snapshot_id'), source.get('content_hash'))
                if binding in opened: continue
                row = {'id': None, 'title': source.get('title') or source['source_id'], 'source': source,
                    'content_status': 'not_extracted', 'blocks': [], 'candidates': [],
                    'queue': {'bucket': 'pending', 'unopened': True, 'open_inspections': []}}
                if query.casefold() in (row['title'] + ' ' + source['source_id']).casefold(): rows.append(row)
        for row in rows:
            queue = row['queue']
            queue['task_type'] = ('inspection' if queue.get('open_inspections') else
                'first' if queue.get('unopened') or row.get('content_status') == 'not_extracted' else 'review')
        if task_type and bucket == 'pending':
            rows = [row for row in rows if row['queue']['task_type'] == task_type]
        return {**base, 'materials': rows[offset:offset+limit], 'total': len(rows), 'offset': offset, 'limit': limit,
            'has_more': offset+limit < len(rows), 'bucket': bucket, 'counts_scope': 'master'}

    def read_archive(self, actor, material_id, revision=None):
        from .collaboration import named
        named(actor)
        archive = self.archives().get(material_id)
        if not archive: raise ValueError('This material has no accepted content archive.')
        revision = archive['revision'] if revision is None else revision
        material = self.c.app.system2.call('material_read', material_id=material_id, revision=revision)
        if material.get('last_action', {}).get('kind') != 'content_confirmed' or not material.get('confirmation'):
            raise ValueError('This is not a confirmed archive version.')
        material = self.c.annotate(actor, material, 'archive')
        material['collaboration']['inspections'] = self.tasks(material_id)
        material['collaboration']['master_revision'] = self.c.app.system2.call('material_read', material_id=material_id)['revision']
        return material

    def create(self, actor, request):
        from .collaboration import named, now, fingerprint
        self.c.coordinator(actor)
        actor = named(actor)
        material_id = str(request.get('material_id', ''))
        rid = str(uuid.UUID(request['request_id']))
        with self.c.lock:
            self.c.claim_request('inspection-create', rid, fingerprint(request), actor)
            replay = self.c.get('inspection_receipt', rid)
            if replay: return replay
            archive = self.archives().get(material_id)
            if not archive or request.get('archive_revision') != archive['revision']:
                raise ValueError('The archived version changed. Reload Archive before creating a check.')
            material = self.c.app.system2.call('material_read', material_id=material_id, revision=archive['revision'])
            selected = request.get('scope', [])
            if not isinstance(selected,list) or any(not isinstance(s,str) for s in selected):
                raise ValueError('Select original range identifiers.')
            scope = sorted(set(selected))
            available = {s['id'] for s in material['scope']}
            if not scope or not set(scope) <= available:
                raise ValueError('Select at least one original range in this archived material.')
            assignee = named(request.get('assignee', actor))
            reason = request.get('reason', '')
            if not isinstance(reason,str): raise ValueError('Record a text reason for this spot-check.')
            reason=reason.strip()
            if not reason or len(reason) > 4000: raise ValueError('Record a bounded reason for this spot-check.')
            task = {'id': str(uuid.uuid4()), 'material_id': material_id, 'title': material.get('title', material_id),
                'archive_revision': archive['revision'], 'archive_content_revision': material['content_revision'],
                'archive_key': acceptance_key(material), 'source_hash': material['source']['content_hash'],
                'scope': scope, 'assignee': assignee, 'created_by': actor, 'reason': reason, 'at': now(),
                'revision': 0, 'status': 'pending', 'checked_scope': [], 'note': '', 'history': []}
            result = {'status': 'created', 'inspection': task}
            self.c.put_many([('material_inspection', task['id'], task), ('inspection_initial', task['id'], deepcopy(task)), ('inspection_receipt', rid, result)])
            return result

    def detail(self, actor, task_id, current=False):
        from .collaboration import named
        named(actor)
        task = self.c.get('material_inspection', task_id)
        if not task: raise ValueError('Spot-check task not found.')
        revision = None if current else task['archive_revision']
        assigned=self.c.get('inspection_assigned',task_id)
        material = deepcopy(assigned['archive']) if assigned and not current else self.c.app.system2.call('material_read', material_id=task['material_id'], revision=revision)
        material = self.c.annotate(actor, material, 'inspection')
        material['collaboration']['inspection'] = task
        material['collaboration']['inspection_current'] = current
        latest=self.archives().get(task['material_id'])
        return {'inspection': task, 'material': material, 'latest_archive_revision': latest['revision'] if latest else None}

    def save(self, actor, request):
        from .collaboration import named, now, fingerprint, COORDINATOR
        actor = named(actor); rid = str(uuid.UUID(request['request_id']))
        with self.c.lock:
            self.c.claim_request('inspection-save', rid, fingerprint(request), actor)
            replay = self.c.get('inspection_receipt', rid)
            if replay: return replay
            task = self.c.get('material_inspection', request.get('task_id', ''))
            if not task or request.get('material_id') != task['material_id']: raise ValueError('Spot-check material identity does not match.')
            if actor not in (task['assignee'], COORDINATOR): raise ValueError('This spot-check is assigned to another reviewer.')
            if request.get('expected_revision') != task['revision']: raise ValueError('Spot-check changed. Reopen it before saving.')
            if task['status'] in ('passed', 'resolved', 'superseded'): raise ValueError('This check is complete. Create a new check to review again.')
            action = request.get('action')
            if action not in ('save', 'pass', 'finding', 'resolve', 'restart'): raise ValueError('Unknown spot-check action.')
            note = request.get('note', '')
            if not isinstance(note, str) or len(note) > 10000: raise ValueError('Spot-check notes must be bounded text.')
            if action == 'restart':
                if task['status'] != 'pending': raise ValueError('Resolve open findings explicitly; they cannot be superseded.')
                latest = self.archives().get(task['material_id'])
                if not latest or latest['revision'] <= task['archive_revision']:
                    raise ValueError('There is no newer archive for this check.')
                material = self.c.app.system2.call('material_read', material_id=task['material_id'], revision=latest['revision'])
                available = {s['id'] for s in material['scope']}
                selected = task['scope'] if set(task['scope']) <= available else sorted(available)
                replacement = dict(deepcopy(task), id=str(uuid.uuid4()), revision=0, status='pending',
                    archive_revision=latest['revision'], archive_content_revision=material['content_revision'],
                    archive_key=acceptance_key(material), source_hash=material['source']['content_hash'],
                    scope=selected, checked_scope=[], note='', history=[], at=now(), created_by=actor,
                    supersedes=task['id'])
                replacement.pop('progress_target_revision', None)
                task = deepcopy(task);task.update(status='superseded',revision=task['revision']+1,replaced_by=replacement['id'])
                task['history'].append({'actor':actor,'at':now(),'action':'restart_on_new_archive','note':note,
                    'target_revision':task['archive_revision'],'replacement_id':replacement['id']})
                result={'status':'saved','inspection':task,'replacement':replacement}
                self.c.put_many([('material_inspection',task['id'],task),('material_inspection',replacement['id'],replacement),('inspection_receipt',rid,result)])
                return result
            scope = task['scope']
            target_revision = task['archive_revision']
            if action == 'resolve' or (action == 'save' and request.get('expected_master_revision') is not None):
                if task['status'] != 'finding_open': raise ValueError('There is no open finding to resolve.')
                material = self.c.app.system2.call('material_read', material_id=task['material_id'])
                if request.get('expected_master_revision') != material['revision']: raise ValueError('Master changed. Reopen the current content before resolving.')
                if material.get('source_stale') or material.get('source_check_error') or material.get('source_issues'):
                    raise ValueError('Current source problems require follow-up before resolving this finding.')
                scope = [s['id'] for s in material['scope']]
                target_revision = material['revision']
            checked = request.get('checked_scope', [])
            if not isinstance(checked, list) or any(not isinstance(s,str) for s in checked) or not set(checked) <= set(scope): raise ValueError('Checked ranges do not belong to this task.')
            if action in ('pass', 'resolve'):
                if not note.strip() or request.get('explicit_confirmation') is not True or set(checked) != set(scope):
                    raise ValueError('Check the complete selected scope and explicitly confirm the result with evidence.')
                if action == 'pass':
                    if task['status'] == 'finding_open': raise ValueError('Resolve the recorded finding against current content first.')
                    current = self.c.app.system2.call('material_read', material_id=task['material_id'])
                    if current.get('source_stale') or current.get('source_check_error') or current.get('source_issues'):
                        raise ValueError('Source changed or requires follow-up. Record a finding instead of passing this check.')
                    latest = self.archives().get(task['material_id'])
                    if not latest or latest['revision'] != task['archive_revision']:
                        raise ValueError('A newer archived version exists. This old check cannot pass as current; create a check of the new version.')
            if action == 'finding' and not note.strip(): raise ValueError('Describe the observed problem and original location.')
            task = deepcopy(task)
            task.update(revision=task['revision']+1, note=note, checked_scope=checked, progress_target_revision=target_revision,
                status={'pass':'passed', 'finding':'finding_open', 'resolve':'resolved'}.get(action,task['status']))
            task['history'].append({'actor': actor, 'at': now(), 'action': action, 'note': note,
                'checked_scope': checked, 'target_revision': target_revision, 'revision': task['revision']})
            result = {'status': 'saved', 'inspection': task}
            self.c.put_many([('material_inspection',task['id'],task),('inspection_receipt',rid,result)])
            return result

    def continue_work(self, actor, request):
        from .collaboration import named, fingerprint, now
        actor = named(actor)
        with self.c.lock:
            rid = str(uuid.UUID(request['request_id']))
            self.c.claim_request('material-continue', rid, fingerprint(request), actor)
            old = self.c.get('continue_receipt', rid)
            if old: return old
            main = self.c.app.system2.call('material_read', material_id=request['material_id'])
            if main['revision'] != request.get('expected_master_revision'):
                raise ValueError('Master changed. Reopen the archive before continuing.')
            self.c.workspace(actor, main['id'])
            marker = {'actor':actor, 'material_id':main['id'], 'master_revision':main['revision'], 'at':now()}
            result = {'status':'opened', 'material_id':main['id'], 'draft_policy':'Existing personal work is restored; current master seeds only an absent workspace.'}
            self.c.put_many([('material_reopen',actor+':'+main['id'],marker),('continue_receipt',rid,result)])
            return result
