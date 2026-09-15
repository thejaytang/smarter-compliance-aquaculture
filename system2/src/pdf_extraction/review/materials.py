"""Human-led material drafts in additive tables of the owning Workflow store.

No operation in this module parses, classifies, exports, or changes legacy rows.
Original snapshots, parser candidates and immutable human revisions are separate.
The HTTP boundary must supply the authenticated named actor, never a form value.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from pdf_extraction.sqlite_support import connect as connect_sqlite
import uuid

from ..contracts.hashing import digest, encoded
from .material_reads import MaterialReads


def now():
    return datetime.now(timezone.utc).isoformat()


def validate_blocks(blocks, scope):
    """Validate editable structure without inventing a Requirement domain schema."""
    if not isinstance(blocks, list):
        raise ValueError('blocks_must_be_list')
    scope_ids = {s['id'] for s in scope}
    ids = [b.get('id') for b in blocks]
    if any(not isinstance(i, str) or not i.strip() for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('block_ids_must_be_unique')
    by_id = {b['id']: b for b in blocks}
    positions = {b['id']: i for i, b in enumerate(blocks)}
    for block in blocks:
        if block.get('type') not in ('text', 'heading', 'table', 'image'):
            raise ValueError('invalid_block_type')
        if not isinstance(block.get('text', ''), str):
            raise ValueError('block_text_must_be_string')
        if block['type'] == 'heading' and (type(block.get('level')) is not int or not 1 <= block['level'] <= 6):
            raise ValueError('heading_level_required')
        if 'markdown_source' in block and not isinstance(block['markdown_source'], str):
            raise ValueError('invalid_markdown_source')
        markdown = block.get('markdown')
        if markdown is not None:
            if not isinstance(markdown, dict) or markdown.get('version') != 1 or not all(isinstance(markdown.get(k), str) for k in ('source', 'baseline')):
                raise ValueError('invalid_markdown_cell')
            if 'original' in markdown and (not isinstance(markdown['original'], dict) or markdown['original'].get('id') != block['id'] or 'markdown' in markdown['original']):
                raise ValueError('invalid_markdown_original')
        parent = block.get('parent_id')
        if parent:
            if parent not in by_id or by_id[parent]['type'] != 'heading' or positions[parent] >= positions[block['id']]:
                raise ValueError('parent_must_be_preceding_heading')
            if block['type'] == 'heading' and by_id[parent]['level'] >= block['level']:
                raise ValueError('heading_parent_level_invalid')
        dependencies = block.get('dependencies', [])
        if not isinstance(dependencies, list) or any(dep not in by_id or dep == block['id'] for dep in dependencies):
            raise ValueError('unresolved_block_dependency')
        refs = block.get('source_refs', [])
        if not isinstance(refs, list) or any(not isinstance(ref, dict) or ref.get('scope_id') not in scope_ids for ref in refs):
            raise ValueError('source_reference_outside_material')
        if block['type'] == 'table':
            table = block.get('table', {})
            rows = table.get('rows', [])
            if not rows or not all(isinstance(row, list) for row in rows) or not rows[0]:
                raise ValueError('table_rows_required')
            width = len(rows[0])
            if any(len(row) != width or any(not isinstance(cell, str) for cell in row) for row in rows):
                raise ValueError('table_must_be_rectangular_text_cells')
            occupied = set()
            for merge in table.get('merges', []):
                r, c, rs, cs = (merge.get(key) for key in ('row', 'col', 'rowspan', 'colspan'))
                if any(type(v) is not int for v in (r, c, rs, cs)) or min(r, c) < 0 or min(rs, cs) < 1 or r + rs > len(rows) or c + cs > width:
                    raise ValueError('table_merge_out_of_bounds')
                cells = {(rr, cc) for rr in range(r, r + rs) for cc in range(c, c + cs)}
                if cells & occupied:
                    raise ValueError('table_merges_overlap')
                occupied |= cells
            if not isinstance(table.get('notes', []), list):
                raise ValueError('table_notes_must_be_list')
        if block['type'] == 'image':
            image = block.get('image', {})
            ref = image.get('source_ref')
            if ref and ref.get('scope_id') not in scope_ids:
                raise ValueError('image_reference_outside_material')
    # Iterative walk also handles long legitimate dependency chains.
    visiting, done = set(), set()
    for identity in ids:
        stack = [(identity, False)]
        while stack:
            current, leaving = stack.pop()
            if leaving:
                visiting.discard(current)
                done.add(current)
                continue
            if current in done:
                continue
            if current in visiting:
                raise ValueError('block_dependency_cycle')
            visiting.add(current)
            stack.append((current, True))
            stack.extend((other, False) for other in by_id[current].get('dependencies', []))
    encoded(blocks)  # Reject non-JSON values and NaN before opening a write.


class MaterialStore(MaterialReads):
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.database = self.root / 'workflow.sqlite'
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS material_documents(id TEXT PRIMARY KEY, source_id TEXT NOT NULL, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS material_revisions(material_id TEXT NOT NULL, revision INTEGER NOT NULL, data TEXT NOT NULL, PRIMARY KEY(material_id,revision));
                CREATE TABLE IF NOT EXISTS material_receipts(id TEXT PRIMARY KEY, digest TEXT NOT NULL, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS material_candidates(id TEXT PRIMARY KEY, material_id TEXT NOT NULL, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS material_conflicts(id TEXT PRIMARY KEY, material_id TEXT NOT NULL, data TEXT NOT NULL);
            ''')
            self.ensure_read_indexes(db)

    def connect(self):
        db = connect_sqlite(self.database, timeout=30)
        db.row_factory = sqlite3.Row
        return db

    @contextmanager
    def transaction(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            yield db

    def _load(self, db, identity):
        row = db.execute('SELECT data FROM material_documents WHERE id=?', (identity,)).fetchone()
        if row is None:
            raise ValueError('material_not_found')
        return json.loads(row['data'])

    def _write(self, db, material, kind, actor):
        material['updated_at'] = now()
        from .material_provenance import record_changes
        previous = db.execute('SELECT data FROM material_documents WHERE id=?', (material['id'],)).fetchone()
        previous = json.loads(previous[0]) if previous else None
        if previous and not previous.get('provenance_version'):
            reconstructed = None
            for row in db.execute('SELECT data FROM material_revisions WHERE material_id=? ORDER BY revision', (material['id'],)):
                version = json.loads(row[0])
                action = version.get('last_action', {})
                if reconstructed and not version.get('collaboration_provenance'):
                    version['collaboration_provenance'] = reconstructed.get('collaboration_provenance', [])
                record_changes(reconstructed, version, action.get('kind', 'retained_history'), action.get('actor'), action.get('at'))
                reconstructed = version
            if reconstructed and kind != 'collaboration_adopted':
                material['collaboration_provenance'] = reconstructed.get('collaboration_provenance', [])
        record_changes(previous, material, kind, actor, material['updated_at'])
        material['last_action'] = {'kind': kind, 'actor': actor, 'at': material['updated_at']}
        data = encoded(material)
        db.execute('INSERT INTO material_documents VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',
                   (material['id'], material['source']['source_id'], data))
        db.execute('INSERT INTO material_revisions VALUES(?,?,?)', (material['id'], material['revision'], data))

    def _view(self, db, material):
        result = dict(material)
        result['candidates'] = []
        for row in db.execute('SELECT data FROM material_candidates WHERE material_id=? ORDER BY rowid', (material['id'],)):
            candidate = json.loads(row[0])
            candidate['stale'] = candidate['input_revision'] != material['content_revision'] or bool(material['source_stale'])
            result['candidates'].append(candidate)
        result['related_versions'] = [dict(id=m['id'], title=m['title'], source=m['source'], content_status=m['content_status'], source_stale=m['source_stale'])
            for row in db.execute('SELECT data FROM material_documents WHERE source_id=? AND id!=?', (material['source']['source_id'], material['id']))
            for m in [json.loads(row[0])]]
        result['conflicts'] = [json.loads(row[0]) for row in db.execute('SELECT data FROM material_conflicts WHERE material_id=? ORDER BY rowid', (material['id'],))]
        return result

    @staticmethod
    def _open_request(request):
        rid = request.get('request_id', '')
        try:
            valid = str(uuid.UUID(rid)) == rid
        except (ValueError, TypeError, AttributeError):
            valid = False
        if not valid:
            raise ValueError('request_id_must_be_canonical_uuid')
        actor = request.get('actor', '')
        if not isinstance(actor, str) or not actor.strip() or actor.strip().lower() in ('machine', 'system', 'anonymous'):
            raise ValueError('named_operator_required')
        return dict(request, operation='open')

    def _open_replay(self, db, request):
        row = db.execute('SELECT digest,data FROM material_receipts WHERE id=?', (request['request_id'],)).fetchone()
        if not row:
            return None
        if row['digest'] != digest(request):
            raise ValueError('request_id_reused_with_different_payload')
        return self._view(db, self._load(db, json.loads(row['data'])['material_id']))

    def open_receipt(self, request):
        """Resume the original material identity even after System1 has changed."""
        request = self._open_request(request)
        with self.connect() as db:
            return self._open_replay(db, request)

    def open(self, source, title, scope, legacy=None, request=None):
        request = self._open_request(request) if request is not None else None
        if request is not None and request.get('source_id') != source['source_id']:
            raise ValueError('open_request_source_mismatch')
        identity = digest({k: source[k] for k in ('source_id', 'snapshot_id', 'content_hash')})[:32]
        if not scope or len({s.get('id') for s in scope}) != len(scope) or any(not isinstance(s.get('id'), str) or not s['id'] for s in scope):
            raise ValueError('complete_original_scope_required')
        with self.transaction() as db:
            if request is not None:
                replay = self._open_replay(db, request)
                if replay is not None:
                    return replay
            if db.execute('SELECT 1 FROM material_documents WHERE id=?', (identity,)).fetchone():
                if request is not None:
                    self._receipt(db, request, {'material_id': identity})
                return self._view(db, self._load(db, identity))
            # Existing source-bound reviews are retained as historical versions.
            for row in db.execute('SELECT data FROM material_documents WHERE source_id=?', (source['source_id'],)).fetchall():
                old = json.loads(row[0])
                if not old['source_stale']:
                    old['source_stale'] = True
                    old['review_impact'] = {'from_content_revision': old['content_revision'],
                        'affected_scope': [s['id'] for s in old['scope']], 'retained_scope': [],
                        'affected_blocks': [], 'structural': True, 'full_review_required': True,
                        'reason': 'source_version_changed'}
                    old['checked_scope'] = []
                    old['review_checks'] = {}
                    old['newer_material_id'] = identity
                    old['revision'] += 1
                    self._write(db, old, 'source_version_observed', 'source_intake')
            material = {'id': identity, 'source': source, 'title': title, 'scope': scope,
                'revision': 0, 'content_revision': 0, 'blocks': [], 'issues': [], 'checked_scope': [],
                'content_status': 'not_extracted', 'requirement_status': 'not_connected',
                'confirmation': None, 'source_stale': False, 'created_at': now(),
                'legacy': legacy, 'association_review_required': False}
            # Legacy is an immutable reference/provenance record, never a new human confirmation.
            self._write(db, material, 'opened', 'source_intake')
            if request is not None:
                self._receipt(db, request, {'material_id': identity})
            return self._view(db, material)

    def read(self, identity, revision=None):
        with self.connect() as db:
            if revision is not None:
                row = db.execute('SELECT data FROM material_revisions WHERE material_id=? AND revision=?', (identity, revision)).fetchone()
                if not row:
                    raise ValueError('material_revision_not_found')
                result = json.loads(row[0])
                result['historical'] = True
                result['candidates'] = []
                return result
            return self._view(db, self._load(db, identity))

    def mark_source_version(self, source_id, snapshot_id, content_hash):
        """Reconcile metadata against System1's observed current eligible snapshot."""
        changed = []
        with self.transaction() as db:
            for row in db.execute('SELECT data FROM material_documents WHERE source_id=?', (source_id,)).fetchall():
                material = json.loads(row[0])
                stale = material['source']['snapshot_id'] != snapshot_id or material['source']['content_hash'] != content_hash
                if stale != material['source_stale']:
                    material['source_stale'] = stale
                    if stale:
                        material['review_impact'] = {'from_content_revision': material['content_revision'],
                            'affected_scope': [s['id'] for s in material['scope']], 'retained_scope': [],
                            'affected_blocks': [], 'structural': True, 'full_review_required': True,
                            'reason': 'source_version_changed'}
                        material['checked_scope'] = []
                        material['review_checks'] = {}
                    else:
                        # A historical confirmation cannot silently become active
                        # when a source is reselected or returns to earlier bytes.
                        # Its original confirmed revision remains immutable.
                        material['confirmation'] = None
                        material['checked_scope'] = []
                        material['review_checks'] = {}
                        material['association_review_required'] = True
                        material['content_status'] = ('not_extracted' if not material['blocks']
                            and material['content_status'] == 'not_extracted' else 'draft')
                        material['review_impact'] = {'from_content_revision': material['content_revision'],
                            'affected_scope': [s['id'] for s in material['scope']], 'retained_scope': [],
                            'affected_blocks': [], 'structural': True, 'full_review_required': True,
                            'reason': 'source_current_again_requires_review'}
                        material.pop('newer_material_id', None)
                    material['revision'] += 1
                    self._write(db, material, 'source_version_observed', 'source_intake')
                    changed.append(material['id'])
        return changed

    def pending_candidates(self):
        with self.connect() as db:
            return [candidate for row in db.execute("SELECT c.data FROM material_candidates c JOIN material_candidate_index i ON i.id=c.id WHERE json_extract(i.data,'$.status')='running' ORDER BY c.rowid")
                    for candidate in [json.loads(row[0])] if candidate['status'] == 'running']

    def process(self, request):
        """The reserved button cannot run a processor or change results."""
        from .material_processor import process, input_hash
        with self.transaction() as db:
            request, material, replay = self._begin(db, request, 'process')
            if replay is not None:
                return replay
            scope = request.get('scope', [s['id'] for s in material['scope']])
            result = process({'request_id': request['request_id'], 'input_revision': material['content_revision'],
                              'material_id':material['id'], 'source':material['source'], 'scope':scope,
                              'input_hash':input_hash(material['id'],material['source'],material['content_revision'],scope,material['blocks'])})
            result['status'] = 'unavailable'
            result['material'] = self._view(db, material)
            return self._receipt(db, request, result)

    def list(self):
        with self.connect() as db:
            return [self._view(db, json.loads(row[0])) for row in db.execute('SELECT data FROM material_documents ORDER BY rowid DESC').fetchall()]

    def history(self, identity):
        with self.connect() as db:
            self._load(db, identity)
            return [json.loads(row[0]) for row in db.execute('SELECT data FROM material_revisions WHERE material_id=? ORDER BY revision DESC', (identity,))]

    def _begin(self, db, request, operation):
        rid = request.get('request_id', '')
        try:
            valid = str(uuid.UUID(rid)) == rid
        except (ValueError, TypeError, AttributeError):
            valid = False
        if not valid:
            raise ValueError('request_id_must_be_canonical_uuid')
        actor = request.get('actor', '')
        if not isinstance(actor, str) or not actor.strip() or actor.strip().lower() in ('machine', 'system', 'anonymous'):
            raise ValueError('named_operator_required')
        request = dict(request, operation=operation)
        row = db.execute('SELECT digest,data FROM material_receipts WHERE id=?', (rid,)).fetchone()
        if row:
            if row['digest'] != digest(request):
                raise ValueError('request_id_reused_with_different_payload')
            return request, None, json.loads(row['data'])
        material = self._load(db, request['material_id'])
        if request.get('expected_revision') != material['revision']:
            conflict = {'id': str(uuid.uuid4()), 'material_id': material['id'], 'actor': actor,
                        'request': request, 'current_revision': material['revision'], 'at': now()}
            db.execute('INSERT INTO material_conflicts VALUES(?,?,?)', (conflict['id'], material['id'], encoded(conflict)))
            result = {'status': 'conflict', 'conflict_id': conflict['id'], 'material': self._view(db, material),
                      'error': 'newer_material_revision_saved_draft_preserved'}
            self._receipt(db, request, result)
            return request, None, result
        return request, material, None

    def _receipt(self, db, request, result):
        db.execute('INSERT INTO material_receipts VALUES(?,?,?)', (request['request_id'], digest(request), encoded(result)))
        return result

    @staticmethod
    def _checks(material, request):
        checked = request.get('checked_scope', material['checked_scope'])
        if not isinstance(checked, list) or any(i not in {s['id'] for s in material['scope']} for i in checked):
            raise ValueError('checked_scope_outside_material')
        return list(dict.fromkeys(checked))

    def _edit(self, material, request):
        blocks = request.get('blocks', material['blocks'])
        validate_blocks(blocks, material['scope'])
        issues = request.get('issues', material['issues'])
        if not isinstance(issues, list) or any(not isinstance(i, dict) or not i.get('id') or not isinstance(i.get('message'), str) or type(i.get('resolved', False)) is not bool for i in issues):
            raise ValueError('invalid_content_issues')
        if len({i['id'] for i in issues}) != len(issues):
            raise ValueError('content_issue_ids_must_be_unique')
        if any(not old.get('resolved') and old['id'] not in {i['id'] for i in issues} for old in material['issues']):
            raise ValueError('unresolved_issue_cannot_be_silently_removed')
        old_ids = {b['id'] for b in material['blocks']}
        new_ids = {b['id'] for b in blocks}
        structural = old_ids != new_ids or any(
            {k: old.get(k) for k in ('type', 'level', 'parent_id', 'dependencies', 'source_refs', 'table', 'numbering')} !=
            {k: new.get(k) for k in ('type', 'level', 'parent_id', 'dependencies', 'source_refs', 'table', 'numbering')}
            for old, new in zip(material['blocks'], blocks))
        changed = digest(blocks) != digest(material['blocks']) or digest(issues) != digest(material['issues'])
        from .material_impact import review_impact, stamp_checks
        if changed:
            impact = review_impact(material, blocks, issues)
            material['review_impact'] = impact
            material['content_revision'] += 1
            material['confirmation'] = None
            material['checked_scope'] = impact['retained_scope']
            material['review_checks'] = {key: material.get('review_checks', {})[key] for key in impact['retained_scope']}
            material['association_review_required'] = structural or impact['structural'] or material['association_review_required']
        if request.get('association_reviewed') is True:
            material['association_review_required'] = False
        elif request.get('association_reviewed') is False:
            material['association_review_required'] = True
        material['blocks'], material['issues'] = blocks, issues
        # A checklist submitted together with changed content may belong to the
        # previous draft. Persist the edit first, then review the saved revision.
        if not changed:
            material['checked_scope'] = self._checks(material, request)
            if 'checked_scope' in request:
                material['review_checks'] = stamp_checks(material, material['checked_scope'], request['actor'], now())
        material['content_status'] = 'review_in_progress' if material['checked_scope'] else 'draft'
        return changed

    def save(self, request):
        with self.transaction() as db:
            request, material, replay = self._begin(db, request, 'save')
            if replay is not None:
                return replay
            old_confirmation = material['confirmation']
            changed = self._edit(material, request)
            if not changed and old_confirmation:
                if (set(material['checked_scope']) == {s['id'] for s in material['scope']}
                        and not material['association_review_required']):
                    material['content_status'] = 'content_review_complete'
                else:
                    material['confirmation'] = None
            material['revision'] += 1
            self._write(db, material, 'saved', request['actor'])
            return self._receipt(db, request, {'status': 'applied', 'material': self._view(db, material)})

    def save_candidate_draft(self, request):
        """Save an empty-input candidate as personal work without claiming review."""
        with self.transaction() as db:
            request, material, replay = self._begin(db, request, 'candidate_draft')
            if replay is not None: return replay
            row = db.execute('SELECT data FROM material_candidates WHERE id=? AND material_id=?',
                (request.get('candidate_id'),material['id'])).fetchone()
            if not row: raise ValueError('candidate_not_found_for_material')
            candidate = json.loads(row[0])
            if material['blocks'] or material['source_stale'] or candidate['status'] not in ('ready','partial') or candidate['input_revision'] != material['content_revision'] or candidate['source'] != material['source']:
                raise ValueError('Candidate input changed; compare it against the current work.')
            validate_blocks(request.get('blocks'), material['scope'])
            # Both versions commit atomically. The first retains machine output,
            # the second records only the person's edits and remains unreviewed.
            self._edit(material,dict(request,blocks=candidate['blocks'],checked_scope=[],association_reviewed=False))
            material['last_candidate_id']=candidate['id'];material['revision']+=1
            self._write(db,material,'candidate_draft',request['actor'])
            self._edit(material,dict(request,checked_scope=[],association_reviewed=False))
            material['revision']+=1
            self._write(db,material,'saved',request['actor'])
            candidate['status']='merged';candidate['resolution']={'action':'save_personal_draft','actor':request['actor'],'at':now(),'reviewed_against_source':False}
            db.execute('UPDATE material_candidates SET data=? WHERE id=?',(encoded(candidate),candidate['id']))
            return self._receipt(db,request,{'status':'applied','material':self._view(db,material)})

    def confirm(self, request):
        with self.transaction() as db:
            request, material, replay = self._begin(db, request, 'confirm')
            if replay is not None:
                return replay
            if request.get('explicit_confirmation') is not True:
                raise ValueError('explicit_human_confirmation_required')
            if material['source_stale']:
                raise ValueError('source_version_requires_reconciliation')
            validate_blocks(material['blocks'], material['scope'])
            if any(not block.get('source_refs') for block in material['blocks']):
                raise ValueError('all_content_requires_original_association')
            if any(block['type'] == 'image' and not block.get('image',{}).get('source_ref')
                   and not (block.get('image',{}).get('attachment') and block.get('image',{}).get('attribution'))
                   for block in material['blocks']):
                raise ValueError('image_source_or_attributed_attachment_required')
            checked = self._checks(material, request)
            if set(checked) != {s['id'] for s in material['scope']}:
                raise ValueError('all_original_ranges_including_empty_ranges_require_review')
            if any(not issue.get('resolved') for issue in material['issues']):
                raise ValueError('unresolved_content_issues')
            if request.get('association_reviewed') is False or (material['association_review_required'] and request.get('association_reviewed') is not True):
                raise ValueError('structural_associations_require_review')
            if any(c['status'] in ('running', 'ready', 'partial') for c in self._view(db, material)['candidates']):
                raise ValueError('candidate_reconciliation_required')
            material['checked_scope'] = checked
            from .material_impact import stamp_checks
            material['review_checks'] = stamp_checks(material, checked, request['actor'], now())
            material['association_review_required'] = False
            material['confirmation'] = {'actor': request['actor'], 'at': now(), 'content_revision': material['content_revision'],
                                        'checked_scope': checked, 'source_hash': material['source']['content_hash']}
            material['content_status'] = 'content_review_complete'
            material['revision'] += 1
            self._write(db, material, 'content_confirmed', request['actor'])
            return self._receipt(db, request, {'status': 'applied', 'material': self._view(db, material)})

    def start_candidate(self, request):
        with self.transaction() as db:
            request, material, replay = self._begin(db, request, 'extract')
            if replay is not None:
                return replay
            if material['source_stale']:
                raise ValueError('source_version_requires_reconciliation')
            existing = [c for c in self._view(db, material)['candidates'] if c['status'] == 'running']
            if existing:
                return self._receipt(db, request, {'status': 'already_running', 'candidate': existing[-1], 'material': self._view(db, material)})
            replace_id = request.get('replace_candidate_id')
            if replace_id is not None:
                row = db.execute('SELECT data FROM material_candidates WHERE id=? AND material_id=?', (replace_id, material['id'])).fetchone()
                prior = json.loads(row[0]) if row else None
                if (material['blocks'] or material.get('confirmation') or not prior or prior.get('origin')
                        or prior['status'] not in ('ready', 'partial') or prior['source'] != material['source']
                        or prior['input_revision'] != material['content_revision']):
                    raise ValueError('Only an unsaved machine preview can be refreshed; preserve existing human work.')
            candidate = {'id': str(uuid.uuid4()), 'material_id': material['id'], 'input_revision': material['content_revision'],
                'source': material['source'], 'scope': material['scope'], 'base_blocks': material['blocks'],
                'replaces_candidate_id': replace_id,
                'status': 'running', 'blocks': [], 'complete': False, 'error': None, 'warnings': [],
                'started_at': now(), 'actor': request['actor'], 'request_id': request['request_id']}
            db.execute('INSERT INTO material_candidates VALUES(?,?,?)', (candidate['id'], material['id'], encoded(candidate)))
            material['revision'] += 1
            self._write(db, material, 'extraction_started', request['actor'])
            return self._receipt(db, request, {'status': 'applied', 'candidate': candidate, 'material': self._view(db, material)})

    def import_candidate(self, request, blocks, provenance, issues=None):
        """Explicitly bring retained legacy effective work into a reviewable candidate.

        The service supplies immutable legacy document/revision references and
        effective content. Import does not rewrite, accept or relabel old decisions.
        """
        with self.transaction() as db:
            issues = [] if issues is None else issues
            if (not isinstance(issues, list) or any(not isinstance(i,dict) or not i.get('id')
                    or not isinstance(i.get('message'),str) or type(i.get('resolved',False)) is not bool for i in issues)
                    or len({i['id'] for i in issues}) != len(issues)):
                raise ValueError('invalid_imported_content_issues')
            request = dict(request, imported_blocks=blocks, provenance=provenance, imported_issues=issues)
            request, material, replay = self._begin(db, request, 'import_legacy')
            if replay is not None:
                return replay
            validate_blocks(blocks, material['scope'])
            if not isinstance(provenance, dict) or not provenance:
                raise ValueError('legacy_provenance_required')
            candidate = {'id': str(uuid.uuid4()), 'material_id': material['id'], 'input_revision': material['content_revision'],
                'source': material['source'], 'scope': material['scope'], 'base_blocks': material['blocks'],
                'status': 'ready', 'blocks': blocks, 'complete': True, 'error': None,
                'warnings': ['Imported legacy content requires new full-scope human review. Historical decisions retain their original provenance.'],
                'started_at': now(), 'finished_at': now(), 'actor': request['actor'], 'request_id': request['request_id'],
                'origin': 'legacy_effective_content', 'issues': issues,
                'metadata': {'legacy_provenance': provenance, 'imported_issues': issues},
                'differences': {'mapping': 'Legacy mapping requires explicit evidence review.'}}
            db.execute('INSERT INTO material_candidates VALUES(?,?,?)', (candidate['id'], material['id'], encoded(candidate)))
            material['revision'] += 1
            self._write(db, material, 'legacy_candidate_imported', request['actor'])
            return self._receipt(db, request, {'status': 'applied', 'candidate': candidate, 'material': self._view(db, material)})

    def finish_candidate(self, material_id, candidate_id, blocks, *, complete=True, error=None, warnings=(), metadata=None):
        with self.transaction() as db:
            material = self._load(db, material_id)
            row = db.execute('SELECT data FROM material_candidates WHERE id=? AND material_id=?', (candidate_id, material_id)).fetchone()
            if not row:
                raise ValueError('candidate_not_found_for_material')
            candidate = json.loads(row[0])
            result_hash = digest({'blocks': blocks, 'complete': complete, 'error': error, 'warnings': list(warnings), 'metadata': metadata})
            if candidate['status'] != 'running':
                if candidate.get('result_hash') != result_hash:
                    raise ValueError('candidate_result_already_final')
                return {'status': 'replayed', 'candidate': candidate, 'material': self._view(db, material)}
            validate_blocks(blocks, material['scope'])
            candidate.update(blocks=blocks, complete=bool(complete and not error), error=error, warnings=list(warnings),
                status='failed' if error else ('ready' if complete else 'partial'), finished_at=now(), result_hash=result_hash,
                metadata=metadata or {})
            # Only a successful refresh supersedes the untouched machine preview.
            # Keep its complete payload and never stamp a human review decision.
            if candidate.get('replaces_candidate_id') and candidate['status'] == 'ready':
                prior_row = db.execute('SELECT data FROM material_candidates WHERE id=? AND material_id=?',
                    (candidate['replaces_candidate_id'], material_id)).fetchone()
                prior = json.loads(prior_row[0]) if prior_row else None
                if (prior and prior['status'] in ('ready', 'partial') and not material['blocks']
                        and material['content_revision'] == candidate['input_revision'] and not material['source_stale']):
                    prior['status'] = 'superseded'
                    prior['replacement'] = {'candidate_id': candidate_id, 'at': now(), 'reason': 'requested_machine_preview_refresh'}
                    db.execute('UPDATE material_candidates SET data=? WHERE id=?', (encoded(prior), prior['id']))
            old = {b['id']: b for b in candidate['base_blocks']}
            new = {b['id']: b for b in blocks}
            candidate['differences'] = {'added': sorted(new.keys() - old.keys()), 'missing': sorted(old.keys() - new.keys()),
                'changed': sorted(i for i in old.keys() & new.keys() if digest(old[i]) != digest(new[i])),
                'mapping': 'Stable IDs only; ambiguous or missing blocks require whole-scope review.'}
            db.execute('UPDATE material_candidates SET data=? WHERE id=?', (encoded(candidate), candidate_id))
            material['revision'] += 1
            self._write(db, material, 'extraction_result', 'local_parser')
            return {'status': 'applied', 'candidate': dict(candidate, stale=candidate['input_revision'] != material['content_revision'] or material['source_stale']), 'material': self._view(db, material)}

    def reconcile(self, request):
        with self.transaction() as db:
            request, material, replay = self._begin(db, request, 'reconcile')
            if replay is not None:
                return replay
            row = db.execute('SELECT data FROM material_candidates WHERE id=? AND material_id=?', (request.get('candidate_id'), material['id'])).fetchone()
            if not row:
                raise ValueError('candidate_not_found_for_material')
            candidate = json.loads(row[0])
            if candidate['status'] not in ('ready', 'partial', 'failed'):
                raise ValueError('candidate_not_available_for_reconciliation')
            action = request.get('action')
            if action not in ('keep', 'adopt', 'merge'):
                raise ValueError('invalid_candidate_action')
            if request.get('reviewed_against_source') is not True:
                raise ValueError('renewed_source_review_required')
            stale = candidate['input_revision'] != material['content_revision'] or material['source_stale']
            if action == 'adopt' and (stale or not candidate['complete']):
                raise ValueError('stale_or_partial_candidate_cannot_be_adopted')
            if action != 'keep':
                if action == 'merge' and not isinstance(request.get('blocks'), list):
                    raise ValueError('merged_blocks_required')
                edit = dict(request, blocks=candidate['blocks'] if action == 'adopt' else request['blocks'])
                imported_issues = candidate.get('metadata',{}).get('imported_issues',[])
                if imported_issues:
                    current_issues = edit.get('issues',material['issues'])
                    if not isinstance(current_issues,list) or any(not isinstance(i,dict) or not i.get('id') for i in current_issues):
                        raise ValueError('invalid_content_issues')
                    merged_issues = {i['id']:i for i in current_issues}
                    for issue in imported_issues:
                        if not issue.get('resolved') or issue['id'] not in merged_issues:
                            merged_issues[issue['id']] = issue
                    edit['issues'] = list(merged_issues.values())
                self._edit(material, edit)
            else:
                material['confirmation'] = None
                material['checked_scope'] = []
                material['content_status'] = 'draft'
            if request.get('_choice_provenance') is not None:
                material['collaboration_provenance'] = request['_choice_provenance']
            material['last_candidate_id'] = candidate['id']
            candidate['status'] = {'keep': 'kept', 'adopt': 'adopted', 'merge': 'merged'}[action]
            candidate['adoption'] = {'actor': request['actor'], 'at': now(), 'action': action,
                'reviewed_against_source': True, 'stale_input': stale, 'result_content_revision': material['content_revision']}
            db.execute('UPDATE material_candidates SET data=? WHERE id=?', (encoded(candidate), candidate['id']))
            material['revision'] += 1
            self._write(db, material, 'candidate_' + action, request['actor'])
            return self._receipt(db, request, {'status': 'applied', 'material': self._view(db, material)})
