"""Transactional two-gate review state and append-only downstream events.

Source facts remain in immutable parser Canonical artifacts. Fields in the index
are read-only projections; human edits are separate, versioned review overlays.
Every emitted row binds the original Canonical and the overlay revision.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import uuid

from ..contracts.hashing import encoded, digest
from ..verification.acceptance import DEFAULT_POLICY, GATE_VERSION, accepted, assess, validate_policy
from ..domains.requirements.classification import propose
from ..verification import requirement_scores
from . import row_store, effective, repairs


class Workflow:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.database = self.root / 'workflow.sqlite'
        with self.connect() as db:
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='review_units'").fetchone():return
            db.executescript('''
                CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS receipts(id TEXT PRIMARY KEY, digest TEXT NOT NULL, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events(sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT, kind TEXT NOT NULL, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS policies(revision INTEGER PRIMARY KEY, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS weekly_qa(week TEXT PRIMARY KEY, data TEXT NOT NULL);
            ''')
            db.execute('INSERT OR IGNORE INTO policies VALUES(?,?)', (1, encoded(DEFAULT_POLICY)))
            row_store.initialize(db)

    def connect(self):
        db = sqlite3.connect(self.database, timeout=30)
        db.row_factory = sqlite3.Row
        return db

    @contextmanager
    def transaction(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            yield db

    def policy(self, db=None):
        if db is None:
            with self.connect() as connection:
                return self.policy(connection)
        return json.loads(db.execute('SELECT data FROM policies ORDER BY revision DESC LIMIT 1').fetchone()[0])

    def _load(self, db, identity, focused=None):
        return row_store.load(db, identity, focused)

    def _save(self, db, doc):
        row_store.save(db, doc)

    def _event(self, db, doc, kind, data):
        db.execute('INSERT INTO events(document_id,kind,data) VALUES(?,?,?)',
                   (doc, kind, encoded(dict(data, at=datetime.now(timezone.utc).isoformat()))))

    def _request(self, db, request):
        rid = str(uuid.UUID(request['request_id']))
        if rid != request['request_id']:
            raise ValueError('request_id_must_be_canonical_uuid')
        actor = request.get('actor', '').strip()
        if not actor or actor == 'machine':
            raise ValueError('named_operator_required')
        row = db.execute('SELECT digest,data FROM receipts WHERE id=?', (rid,)).fetchone()
        if row:
            if row['digest'] != digest(request):
                raise ValueError('request_id_reused_with_different_payload')
            return json.loads(row['data'])

    def _receipt(self, db, request, result):
        db.execute('INSERT INTO receipts VALUES(?,?,?)',
                   (request['request_id'], digest(request), encoded(result)))
        return result

    def enqueue(self, sources, request):
        """Only the governed intake adapter may construct sources."""
        with self.transaction() as db:
            replay = self._request(db, request)
            if replay is not None:
                return replay
            ids = []
            for source in sources:
                if source.get('selection_status') != 'INCLUDE':
                    raise ValueError('source_not_included')
                identity = digest({k: source[k] for k in ('source_id', 'snapshot_id', 'content_hash')})[:32]
                ids.append(identity)
                if db.execute('SELECT 1 FROM documents WHERE id=?', (identity,)).fetchone():
                    continue
                doc = {'id': identity, 'source': source, 'revision': 0, 'state': 'queued',
                       'eligible': True, 'units': [], 'issues': [], 'history': [], 'published': {},
                       'parser_complete': False, 'source_complete': False, 'attempt': 0, 'generation':0,
                       'policy_revision': self.policy(db)['revision'], 'canonical': [], 'cursor': 0}
                self._save(db, doc)
                self._event(db, identity, 'queued', {'actor': request['actor']})
            return self._receipt(db, request, {'status': 'applied', 'documents': ids})

    def install(self, identity, units, canonical, *, issues=(), complete=True, cursor=0, generation=None, total_pages=None, pages=()):
        """Internal worker publication; Canonical hashes are checked before admission."""
        for ref in canonical:
            path = Path(ref['path']).resolve()
            if not path.is_relative_to(self.root) or sha256(path.read_bytes()).hexdigest() != ref['sha256']:
                raise ValueError('canonical_artifact_mismatch')
        with self.transaction() as db:
            doc = self._load(db, identity)
            if generation is not None and doc.get('generation',0)!=generation:
                return {'status':'superseded'}
            old_units = {u['id']: u for u in doc['units']}
            for unit in units:
                if unit['id'] in old_units:
                    if digest(old_units[unit['id']]['original']) != digest(unit['original']):
                        raise ValueError('unit_identity_collision')
                    continue
                unit = dict(unit, version=1, edits={}, touched=False, content_human=False,
                            requirement_human=False, classification='undetermined',
                            content_status='pending', requirement_status='blocked')
                old_units[unit['id']] = unit
            doc['units'] = list(old_units.values())
            doc['canonical'] = list({ref['path']: ref for ref in doc['canonical'] + canonical}.values())
            if doc['source'].get('file_format')=='pdf':
                from .migrate_hierarchy import populate
                changed=populate(doc,self.root)
                repairs.invalidate({u['id']:u for u in doc['units']},changed)
            from .processing_failure import recovered
            recovered(self,db,doc)
            doc['issues'] = list(dict.fromkeys(doc['issues'] + list(issues)))
            doc['cursor'] = cursor
            if total_pages is not None:
                doc['total_pages']=total_pages
                doc['processed_pages']=sorted(set(doc.get('processed_pages',[]))|set(pages))
            if doc['source'].get('file_format')=='pdf' and (doc.get('pdf_scope_version') or all(u.get('scope_version')=='pdf-pages/1' or u['kind']=='coverage' for u in doc['units'])):
                from .pdf_scope import refresh
                refresh(doc);doc['pdf_scope_version']='pdf-pages/1'
            doc['parser_complete'] = complete
            doc['error'] = None
            doc['revision'] += 1
            if doc['state'] != 'paused':
                doc['state'] = 'waiting_review' if complete else 'queued'
            self._recompute(db, doc, self.policy(db))
            self._save(db, doc)

    def _recompute(self, db, doc, policy):
        from . import requirement_subdivision as subdivision
        from .source_verification import refresh_staleness
        if doc.get('source_verification_pages'):
            refresh_staleness(doc)
        from .table_assembly import reconcile
        reconcile(doc)
        for ref in doc['canonical']:
            path = Path(ref['path']).resolve()
            if not path.is_relative_to(self.root) or not path.is_file() or sha256(path.read_bytes()).hexdigest() != ref['sha256']:
                if 'canonical_artifact_changed' not in doc['issues']:
                    doc['issues'].append('canonical_artifact_changed')
        for unit in doc['units']:
            content_drafts = any(d.get('stage') != 'requirement' for d in unit.get('drafts', {}).values())
            a = assess(unit.get('content_parts', []), policy['content'],
                       blockers=[*unit.get('blockers', []), *(['review_draft_pending'] if content_drafts else [])],
                       human=unit.get('content_human', False), touched=bool(unit.get('touched', False)),stage='content')
            unit.update(content_status=a['status'], content_confidence=a['confidence'], content_reasons=a['reasons'],
                        confidence_gate_version=GATE_VERSION)
        by_id = {u['id']: u for u in doc['units']}
        table_candidates = {u['id'] for u in doc['units'] if accepted(u['content_status']) and effective.table_source(u)}
        table_parents_with_rows = {owner['id'] for child in doc['units']
            if table_candidates.intersection(child.get('dependencies', [])) and not child.get('superseded_by')
            and (owner := effective.table_owner(child, by_id)) and owner['id'] != child['id']}
        # Resolve the entire dependency graph; missing nodes and cycles stay blocked.
        from collections import defaultdict, deque
        waiting = {u['id']: set(u.get('dependencies', [])) for u in doc['units'] if accepted(u['content_status'])}
        dependents = defaultdict(set)
        for uid, dependencies in waiting.items():
            for dependency in dependencies: dependents[dependency].add(uid)
        queue = deque(uid for uid, dependencies in waiting.items() if not dependencies)
        content_ready = set()
        while queue:
            uid = queue.popleft()
            content_ready.add(uid)
            for child in dependents[uid]:
                waiting[child].discard(uid)
                if not waiting[child]: queue.append(child)
        for unit in doc['units']:
            dependencies_ok = all(d in content_ready for d in unit.get('dependencies', []))
            a = {'status': unit['content_status']}
            if not accepted(a['status']):
                unit['requirement_status'] = 'blocked'
                continue
            if not dependencies_ok:
                unit['requirement_status'] = 'blocked'
                unit['requirement_reasons'] = ['content_dependencies_unverified']
                continue
            proposal = propose(self.resolved(unit, by_id))
            unit['requirement_score_version'] = requirement_scores.VERSION+':'+proposal['method']
            if not unit.get('requirement_human'):
                unit['classification'] = proposal['classification']
            blockers = list(unit.get('requirement_blockers', []))
            if unit.get('drafts'):
                blockers.append('review_draft_pending')
            if subdivision.stale(unit, self.resolved(unit, by_id), doc['source']):
                blockers.append('requirement_subdivision_stale')
            if unit['classification'] == 'requirement' and (unit['kind']=='coverage' or unit.get('table_assembly') or unit.get('evidence_only') or unit.get('superseded_by')):
                blockers.append('context_only_or_superseded')
            if unit['classification'] == 'requirement' and unit['id'] in table_parents_with_rows:
                blockers.append('table_has_independent_row_items')
            if unit['classification'] == 'undetermined':
                blockers.append('classification_undetermined')
            score_parts = requirement_scores.applicable_parts(unit, proposal)
            b = assess(score_parts, policy['requirement'],
                       blockers=blockers, human=unit.get('requirement_human', False),
                       touched=bool(unit.get('touched', False) or unit.get('drafts')),stage='requirement')
            if not unit.get('requirement_human') and any(p.get('score_binding_status') for p in score_parts):
                b['reasons'].append('classification_score_binding_stale')
            unit.update(requirement_status=b['status'], requirement_confidence=b['confidence'], requirement_reasons=b['reasons'])
        coverage = [u for u in doc['units'] if u['kind'] == 'coverage']
        pages_complete = 'total_pages' not in doc or len(doc.get('processed_pages',[]))==doc['total_pages']
        doc['source_complete'] = doc['parser_complete'] and pages_complete and bool(coverage) and all(accepted(u['content_status']) for u in coverage)
        valid = doc['eligible'] and not doc['issues']
        published = {}
        for u in doc['units']:
            dependencies_ok = all(d in content_ready for d in u.get('dependencies', []))
            if valid and dependencies_ok and u['kind'] != 'coverage' and not u.get('table_assembly') and not u.get('evidence_only') and not u.get('superseded_by') and u['classification'] == 'requirement' and accepted(u['content_status']) and accepted(u['requirement_status']):
                row = self.resolved(u, by_id)
                published[u['id']] = {'requirement_id': doc['source']['source_id'] + ':' + u['id'],
                    'source': doc['source'], 'unit_version': u['version'], 'fields': row['fields'],
                    'references': row.get('references', []), 'structure': row.get('structure', []),
                    'related_content':row.get('related_content',[]), 'table':row.get('table'),
                    'table_scope':row.get('table_scope'), 'table_owner_id':row.get('table_owner_id'),
                    'table_assembly':row.get('table_assembly'),
                    'hierarchy':row.get('hierarchy'),'ancestors':row.get('ancestors',[]),'reading_order_key':row.get('reading_order_key'),
                    'decision_origin': 'human' if u['requirement_human'] else 'machine',
                    'content_decision_origin': 'human' if u['content_human'] else 'machine',
                    'confidence': u.get('requirement_confidence'), 'canonical': doc['canonical']}
                if u.get('requirement_subdivision'):
                    published[u['id']] = subdivision.delivery(published[u['id']], u['requirement_subdivision'])
        previous = doc.get('published', {})
        for key in previous.keys() - published.keys():
            retired=by_id.get(key,{})
            kind='withdraw' if retired.get('requirement_human') and retired.get('classification')!='requirement' else 'suspend'
            self._event(db, doc['id'], kind, {'requirement_id': previous[key]['requirement_id'],
                        'revision': doc['revision'], 'policy_revision': policy['revision']})
        for key, row in published.items():
            if previous.get(key) != row:
                self._event(db, doc['id'], 'replace' if key in previous else 'add',
                            {'requirement': row, 'revision': doc['revision'], 'policy_revision': policy['revision']})
        doc['published'] = published
        doc['policy_revision'] = policy['revision']
        done = bool(doc['units']) and doc['source_complete'] and valid and all(
            accepted(u['content_status']) and accepted(u['requirement_status']) for u in doc['units'] if not u.get('superseded_by'))
        if doc['state'] not in {'paused', 'queued', 'running', 'failed', 'conversion_required'}:
            doc['state'] = 'complete' if done else ('partial' if published else 'waiting_review')
        doc['complete'] = done

    @staticmethod
    def resolved(unit, units=None):
        return effective.resolve(unit, units)

    @staticmethod
    def _invalidate_dependents(doc, identity):
        affected = {identity}
        while True:
            extra = {u['id'] for u in doc['units'] if affected.intersection(u.get('dependencies', []))} - affected
            if not extra: break
            affected.update(extra)
        for other in doc['units']:
            if other['id'] in affected - {identity}:
                other.update(content_human=False,requirement_human=False, touched=True, requirement_parts=[])
                other['version']+=1

    def decision(self, request):
        with self.transaction() as db:
            replay = self._request(db, request)
            if replay is not None:
                return replay
            roots=[request['unit_id'],*[request[k] for k in ('target_unit_id','table_owner_id') if request.get(k)]]
            doc = self._load(db, request['document_id'], focused=roots if request.get('guard') and request.get('action') not in {'merge','split','supplement','restore','structure','hierarchy','reading_order','table_geometry','table_cells','table_rows','table_assembly'} else None)
            policy = self.policy(db)
            if request.get('guard'):
                from .browser_view import guard
                if request['guard'] != guard(db,doc,request['unit_id']):
                    raise ValueError('stale_unit_or_dependency')
            if ((not request.get('guard') and request['revision'] != doc['revision']) or request['policy_revision'] != policy['revision']
                    or request['source_sha256'] != doc['source']['content_hash']):
                raise ValueError('stale_source_result_or_policy')
            if not doc['eligible']:
                raise ValueError('source_not_currently_eligible')
            unit = next((u for u in doc['units'] if u['id'] == request['unit_id']), None)
            if unit is None:
                raise ValueError('unit_not_found')
            action = request['action']
            if unit.get('table_assembly') and action not in {'draft','accept_content','resolve_content','classify','restore','reopen','unreadable','reject'}:
                raise ValueError('edit_the_original_table_fragment')
            if unit.get('superseded_by') and action!='restore':raise ValueError('superseded_source_unit_replaced_open_current_content')
            note = request.get('note', '').strip()
            resolved_requirement = request.get('resolved_requirement_issues', [])
            if resolved_requirement:
                if (action not in {'classify','clear_subdivision','subdivide_requirement'} or not note
                    or not isinstance(resolved_requirement,list)
                    or any(not isinstance(c,str) or not c.startswith('weekly_qa:') for c in resolved_requirement)
                    or not set(resolved_requirement) <= set(unit.get('requirement_blockers',[]))):
                    raise ValueError('weekly_requirement_resolution_requires_current_finding_and_note')
                unit['requirement_blockers']=[c for c in unit['requirement_blockers'] if c not in resolved_requirement]
            by_id={u['id']:u for u in doc['units']}
            before = self.resolved(unit, by_id)
            classification_before = unit.get('classification')
            from copy import deepcopy
            subdivision_before = deepcopy(unit.get('requirement_subdivision'))
            repair_before={}
            repair_created=[]
            created_units=[]
            if action == 'accept_content':
                if unit.get('blockers'):
                    raise ValueError('explicit_issue_resolution_required')
                unit['content_human'] = True
                unit['touched'] = False
            elif action == 'resolve_content':
                if 'source_verification_stale' in request.get('resolved_issues', []):
                    raise ValueError('rerun_original_page_check_before_acceptance')
                if any(code.startswith('table_assembly_') for code in request.get('resolved_issues',[])):
                    raise ValueError('repair_table_assembly_before_acceptance')
                if 'human_table_row_gaps' in request.get('resolved_issues',[]):raise ValueError('assign_remaining_table_rows_before_acceptance')
                if 'human_table_grid_gaps' in request.get('resolved_issues',[]):
                    raise ValueError('repair_remaining_table_grid_gaps_before_acceptance')
                if 'human_table_text_conflict' in request.get('resolved_issues',[]):
                    raise ValueError('choose_effective_table_values_before_resolving_conflict')
                if 'hierarchy_parent_after_child' in request.get('resolved_issues',[]):
                    raise ValueError('repair_parent_or_reading_order_before_resolving_conflict')
                if not note or not set(request.get('resolved_issues', [])) <= set(unit.get('blockers', [])) or (unit.get('blockers') and not request.get('resolved_issues')):
                    raise ValueError('resolve_each_content_issue_with_evidence_note')
                unit['resolved_issues']=list(dict.fromkeys(unit.get('resolved_issues',[])+request.get('resolved_issues',[])))
                unit['blockers'] = [c for c in unit.get('blockers',[]) if c not in request.get('resolved_issues',[])]
                unit['content_human'] = not unit['blockers']
                unit['touched'] = False
            elif action in {'correct', 'structure'}:
                updates = request.get('fields', {})
                if not note or not isinstance(updates,dict) or (action == 'correct' and not updates) or any(k not in {'identifier','title','body','criteria','level','context','notes','applicability','structure_note'}
                    or not isinstance(v, str) for k, v in updates.items()):
                    raise ValueError('correction_fields_and_evidence_note_required')
                if effective.table_owner(unit,by_id) and set(updates)&{'body','criteria','identifier'}:
                    raise ValueError('use_table_cell_repair_to_preserve_shared_values')
                unit['edits'].update(updates)
                if action == 'structure':
                    structure = request.get('structure')
                    if not isinstance(structure, list) or not structure or any(not isinstance(r,dict) or not r.get('locator') or not r.get('role') for r in structure):
                        raise ValueError('structure_requires_source_locators_and_explicit_roles')
                    unit['reviewed_structure'] = structure
                    region=next((r for r in structure if r.get('role')=='source_region'),None)
                    if region:
                        import re
                        locator=region['locator'].strip()
                        ref={'locator':locator,'source_sha256':doc['source']['content_hash']}
                        page=re.fullmatch(r'page\s+(\d+)(?:\s*:\s*([0-9., ]+))?',locator,re.I)
                        if page:
                            ref['page_index']=int(page[1])-1
                            if ref['page_index']<0 or ('total_pages' in doc and ref['page_index']>=doc['total_pages']):raise ValueError('original_page_out_of_range')
                            if page[2]:
                                coords=[float(v.strip()) for v in page[2].split(',')]
                                if len(coords)!=4 or min(coords)<0 or coords[2]<=coords[0] or coords[3]<=coords[1]:raise ValueError('invalid_region_coordinates')
                                ref['bbox']=coords
                        elif not ('nth-of-type(' in locator or re.fullmatch(r'xl/worksheets/[^#]+#[A-Z]+[0-9]+',locator)):
                            raise ValueError('Use a saved HTML locator, worksheet part and cell, or page N: x0,y0,x1,y1.')
                        unit['reviewed_references']=[ref]
                        unit['blockers']=list(dict.fromkeys(unit.get('blockers',[])+['human_location']))
                        if doc.get('pdf_scope_version'):
                            from .pdf_scope import refresh
                            old_coverage=[d for d in unit.get('dependencies',[]) if by_id.get(d,{}).get('coverage_scope')=='pdf_page']
                            refresh(doc);by_id.update({u['id']:u for u in doc['units']})
                            new_coverage=[d for d in unit.get('dependencies',[]) if by_id.get(d,{}).get('coverage_scope')=='pdf_page']
                            repairs.invalidate(by_id,set(old_coverage+new_coverage))
                unit['version'] += 1
                unit['content_human'] = False
                unit['requirement_human'] = False
                unit['touched'] = True
                unit['requirement_parts'] = [{'confidence': None, 'calibration_version': None,
                                               'evidence': self.resolved(unit, by_id).get('references', [])}]
                # Context changes invalidate every dependent classification.
                self._invalidate_dependents(doc, unit['id'])
            elif action in {'relation','table_cell','table_geometry','table_cells','table_rows','table_assembly','use_table_values','restore','hierarchy','reading_order'} or (action in {'merge','split'} and doc.get('hierarchy_version')):
                if not note:raise ValueError('repair_evidence_note_required')
                snapshots={uid:repairs.patch_state(u) for uid,u in by_id.items()}
                if action=='split':
                    from .splitting import split
                    changed,repair_created=split(doc,unit,request)
                    by_id.update({u['id']:u for u in doc['units']})
                    created_units=[self.resolved(by_id[uid],by_id) for uid in repair_created]
                elif action=='merge':
                    from .boundaries import merge
                    changed=merge(doc,unit,request)
                elif action=='relation':changed=repairs.relation(unit,by_id,request)
                elif action=='table_cell':changed=repairs.cell(unit,by_id,request)
                elif action=='table_geometry':
                    from .table_geometry import repair
                    changed=repair(doc,unit,request)
                elif action=='table_assembly':
                    from .table_assembly import repair
                    changed,repair_created=repair(doc,unit,request)
                    by_id.update({u['id']:u for u in doc['units']})
                    created_units=[self.resolved(by_id[uid],by_id) for uid in repair_created]
                elif action=='table_rows':
                    from .table_rows import repair
                    changed,repair_created=repair(doc,unit,request)
                    by_id.update({u['id']:u for u in doc['units']})
                    created_units=[self.resolved(by_id[uid],by_id) for uid in repair_created]
                elif action=='table_cells':
                    from .table_cells import repair
                    changed=repair(doc,unit,request)
                elif action=='use_table_values':changed=repairs.use_table_values(unit,by_id,request)
                elif action in {'hierarchy','reading_order'}:
                    from . import hierarchy
                    if not doc.get('hierarchy_version'):raise ValueError('source_hierarchy_projection_required')
                    changed=hierarchy.repair(doc,unit,request) if action=='hierarchy' else hierarchy.move(doc,unit,request)
                    hierarchy.validate(doc)
                else:
                    target=next((h for h in doc['history'] if h['request_id']==request.get('restore_request_id') and (h['unit_id']==unit['id'] or unit['id'] in h.get('created_ids',[]))),None)
                    if target is None:raise ValueError('restore_revision_not_found')
                    changed=repairs.restore(by_id,target)
                    if doc.get('hierarchy_version'):
                        from . import hierarchy
                        doc['units']=hierarchy.ordered(doc['units']);hierarchy.validate(doc)
                    elif target.get('action') in {'table_geometry','table_cells','table_rows','table_assembly'}:
                        from .hierarchy import ordered
                        doc['units']=ordered(doc['units'])
                changed=list(set(changed)|{uid for uid,u in by_id.items() if snapshots.get(uid)!=repairs.patch_state(u)})
                repair_before={uid:snapshots[uid] for uid in changed if uid in snapshots}
                affected=repairs.invalidate(by_id,changed)
            elif action == 'subdivide_requirement':
                from . import requirement_subdivision as subdivision
                if not accepted(unit['content_status']) or unit['requirement_status'] == 'blocked':
                    raise ValueError('content_gate_not_passed')
                if unit.get('requirement_blockers'):
                    raise ValueError('requirement_relationship_issues_unresolved')
                if any(child['id'] != unit['id'] and not child.get('superseded_by') and effective.table_owner(child, by_id) is unit for child in doc['units']):
                    raise ValueError('subdivide_the_original_numbered_row_not_its_table_container')
                unit['requirement_subdivision'] = subdivision.apply(unit, before, doc['source'], request)
                unit['requirement_subdivision_revision'] = unit['requirement_subdivision']['revision']
                unit.update(classification='requirement', requirement_human=True, touched=False)
            elif action in {'classify', 'clear_subdivision'}:
                if action == 'classify' and unit.get('requirement_subdivision'):
                    raise ValueError('explicitly_replace_or_remove_requirement_subitems')
                if action == 'clear_subdivision' and (not unit.get('requirement_subdivision') or not note):
                    raise ValueError('subdivision_removal_requires_current_subitems_and_reason')
                if not accepted(unit['content_status']) or unit['requirement_status'] == 'blocked':
                    raise ValueError('content_gate_not_passed')
                classification = request.get('classification')
                if classification == 'requirement' and unit.get('superseded_by'):
                    raise ValueError('superseded_unit_is_historical_context')
                if classification == 'requirement' and unit.get('table_assembly'):
                    raise ValueError('table_assembly_is_context_only')
                if classification == 'requirement' and unit['kind']=='coverage':
                    raise ValueError('coverage_is_context_only')
                if classification not in {'requirement', 'context', 'non_requirement'}:
                    raise ValueError('classification_invalid')
                if classification == 'requirement' and not any(self.resolved(unit, by_id)['fields'].get(k,'').strip() for k in ('body','criteria','title','notes')):
                    raise ValueError('requirement_requires_original_supported_text')
                if classification == 'requirement' and unit.get('evidence_only'):
                    raise ValueError('overlap_is_context_not_a_second_requirement')
                if classification != 'requirement' and not note:
                    raise ValueError('exclusion_or_context_reason_required')
                if unit.get('requirement_blockers'):
                    raise ValueError('requirement_relationship_issues_unresolved')
                unit['classification'] = classification
                unit['requirement_human'] = True
                unit['touched'] = False
                if action == 'clear_subdivision':
                    unit.pop('requirement_subdivision')
            elif action in {'unreadable', 'reject', 'reopen', 'location'}:
                if not note:
                    raise ValueError('followup_note_required')
                unit['touched'] = True
                unit['content_human'] = False
                unit['requirement_human'] = False
                unit['requirement_parts'] = []
                unit['blockers'] = list(set(unit.get('blockers', []) + ['human_' + action]))
                self._invalidate_dependents(doc, unit['id'])
            elif action == 'draft':
                if request.get('draft', {}).get('stage') != 'requirement':
                    unit['touched'] = True
                unit.setdefault('drafts', {})[request['actor']] = request.get('draft', {})
            elif action == 'supplement':
                fields = request.get('fields', {})
                if not fields.get('body') or not note or not request.get('locator'):
                    raise ValueError('supplement_requires_text_original_locator_and_note')
                sid = 'manual:' + request['request_id']
                ref=repairs.source_reference(request['locator'],doc)
                original = {'fields': fields, 'references': [ref], 'structure': []}
                added={'id': sid, 'kind': 'source_text', 'original': original,
                    'chapter':unit.get('chapter','Original order'), 'provenance':{'origin':'human_supplement','request_id':request['request_id'],'actor':request['actor']},
                    'version': 1, 'edits': {}, 'content_human': False, 'requirement_human': False,
                    'touched': True, 'classification': 'undetermined', 'content_parts': [], 'blockers': [],
                    'dependencies': [unit['id']] if unit['kind']=='coverage' else list(unit.get('dependencies',[]))}
                anchor=request.get('insert_after_id',unit['id'])
                index=next((i for i,u in enumerate(doc['units']) if u['id']==anchor),None)
                if index is None:raise ValueError('insertion_anchor_not_found')
                if anchor!=unit['id'] and request.get('anchor_fingerprint')!=digest(doc['units'][index]):raise ValueError('stale_insertion_anchor')
                if doc['units'][index]['kind']=='coverage' and 'page_index' in ref:
                    positions=[(i,r) for i,u in enumerate(doc['units']) for r in u['original'].get('references',[]) if r.get('page_index')==ref['page_index']]
                    if positions:index=max(i for i,r in positions)
                if not request.get('insert_after_id') and 'page_index' in ref and ref.get('bbox'):
                    def position(reference):
                        box=reference.get('bbox')
                        if reference.get('page_index') is None or not box:return None
                        return (reference['page_index'],box['y0'] if isinstance(box,dict) else box[1],box['x0'] if isinstance(box,dict) else box[0])
                    wanted=position(ref)
                    candidates=[(i,min(pos)) for i,u in enumerate(doc['units']) if (pos:=[p for r in u['original'].get('references',[]) if (p:=position(r)) is not None])]
                    later=next((i for i,pos in candidates if pos>wanted),None)
                    if later is not None:index=later-1
                    elif candidates:index=candidates[-1][0]
                    if index>=0:added['chapter']=doc['units'][index].get('chapter','Original order')
                doc['units'].insert(index+1,added)
                by_id[sid]=added
                if doc.get('pdf_scope_version'):
                    from .pdf_scope import refresh
                    refresh(doc);by_id.update({u['id']:u for u in doc['units']})
                created_units=[self.resolved(added,by_id)]
                for dependency in added['dependencies']:
                    if by_id.get(dependency,{}).get('kind')=='coverage':
                        by_id[dependency].update(content_human=False,requirement_human=False,touched=True)
                        by_id[dependency]['version']+=1
                        self._invalidate_dependents(doc,dependency)
            elif action in {'split', 'merge'}:
                if unit['kind']=='coverage' or unit.get('superseded_by') or unit.get('evidence_only'):
                    raise ValueError('boundary_requires_current_source_text')
                if not note or not accepted(unit['content_status']):
                    raise ValueError('boundary_correction_requires_verified_content_and_note')
                parents = [unit]
                if action == 'split':
                    parts = request.get('split_parts', [])
                    original_body = self.resolved(unit, by_id)['fields'].get('body', '')
                    if len(parts) < 2 or any(not isinstance(p,str) or not p.strip() for p in parts) or ''.join(''.join(parts).split()) != ''.join(original_body.split()):
                        raise ValueError('split_must_preserve_all_original_text_in_order')
                else:
                    identities = request.get('merge_ids', [])
                    if not identities or unit['id'] not in identities or len(identities) != len(set(identities)):
                        raise ValueError('merge_requires_unique_ordered_source_units')
                    parents = [next((u for u in doc['units'] if u['id']==identity), None) for identity in identities]
                    if len(parents)<2 or any(u is None or not accepted(u['content_status']) or u['kind']=='coverage' or u.get('superseded_by') or u.get('evidence_only') for u in parents):
                        raise ValueError('merge_requires_verified_source_units')
                    parts = ['\n'.join(self.resolved(p, by_id)['fields'].get('body','') for p in parents)]
                for index, body in enumerate(parts):
                    fields = dict(self.resolved(unit, by_id)['fields'], body=body)
                    fields['identifier'] = fields.get('identifier','') + (f' [{index+1}]' if action=='split' else '')
                    child_id = action + ':' + request['request_id'] + ':' + str(index)
                    doc['units'].append({'id':child_id,'kind':'source_text','version':1,
                        'original':{'fields':fields,'references':[r for p in parents for r in self.resolved(p, by_id).get('references',[])],
                                    'structure':[{'parent_unit_id':p['id']} for p in parents]},
                        'dependencies':list({d for p in parents for d in p.get('dependencies', [])}),
                        'edits':{},'content_human':False,'requirement_human':False,'touched':True,
                        'classification':'undetermined','blockers':[],'content_parts':[]})
                for parent in parents:
                    parent['classification']='context';parent['requirement_human']=True
                    parent['superseded_by']=request['request_id']
            else:
                raise ValueError('unsupported_review_action')
            if doc.get('hierarchy_version') and not doc.get('_partial'):
                from .hierarchy import ensure_order
                ensure_order(doc)
            if action!='draft':unit.get('drafts',{}).pop(request['actor'],None)
            doc['revision'] += 1
            history = {'actor': request['actor'], 'action': action, 'unit_id': unit['id'],
                       'request_id': request['request_id'], 'note': note, 'before': before,
                       'after': self.resolved(unit, by_id), 'revision': doc['revision'], 'policy_revision': policy['revision'],
                       'at': datetime.now(timezone.utc).isoformat(),
                       'source_version': {k:doc['source'].get(k) for k in ('source_id','snapshot_id','content_hash')}}
            if action in {'classify','clear_subdivision','subdivide_requirement'}:
                history.update(classification_before=classification_before,classification_after=unit['classification'])
            if resolved_requirement:history['resolved_requirement_issues']=resolved_requirement
            if subdivision_before or unit.get('requirement_subdivision'):
                history.update(subdivision_before=subdivision_before,
                               subdivision_after=deepcopy(unit.get('requirement_subdivision')))
            if created_units:history['created_units']=created_units
            if repair_before:
                history.update(repair_before=repair_before,repair_after={uid:repairs.patch_state(by_id[uid]) for uid in list(repair_before)+repair_created},affected_units=affected)
                if repair_created:history['created_ids']=repair_created
            if action != 'draft':
                doc['history'].append(history)
            self._event(db, doc['id'], 'draft' if action == 'draft' else 'review', history)
            self._recompute(db, doc, policy)
            self._save(db, doc)
            from .browser_view import guard
            return self._receipt(db, request, {'status': 'applied', 'revision': doc['revision'], 'state': doc['state'], 'unit_fingerprint':digest(unit), **({'guard':guard(db,doc,unit['id'])} if row_store.enabled(db) else {})})

    def set_policy(self, policy, request):
        validate_policy(policy)
        with self.transaction() as db:
            replay = self._request(db, request)
            if replay is not None:
                return replay
            old = self.policy(db)
            if policy['revision'] != old['revision'] + 1:
                raise ValueError('stale_policy_revision')
            db.execute('INSERT INTO policies VALUES(?,?)', (policy['revision'], encoded(policy)))
            for row in db.execute('SELECT data FROM documents').fetchall():
                doc = self._load(db, json.loads(row[0])['id'])
                doc['revision'] += 1
                self._recompute(db, doc, policy)
                self._save(db, doc)
            self._event(db, None, 'policy', {'actor': request['actor'], 'policy': policy})
            return self._receipt(db, request, {'status': 'applied', 'policy': policy})

    def control(self, request):
        with self.transaction() as db:
            replay = self._request(db, request)
            if replay is not None:
                return replay
            doc = self._load(db, request['document_id'])
            if request['revision'] != doc['revision']:
                raise ValueError('stale_result_revision')
            action = request['action']
            if action in {'retry','reprocess','resume'}:
                from .processing_failure import retain
                retain(self,db,doc)
            if action == 'pause':
                doc['state'] = 'paused'
            elif action == 'reprocess' and doc['eligible']:
                # Retain the complete reviewed generation before creating fresh parser artifacts.
                self._event(db, doc['id'], 'retired_generation', {'revision':doc['revision'],
                    'units':doc['units'], 'canonical':doc['canonical'], 'issues':doc['issues']})
                doc.update(units=[],canonical=[],issues=[],cursor=0,parser_complete=False,
                           source_complete=False,state='queued',error=None,processed_pages=[])
                doc['generation']=doc.get('generation',0)+1
            elif action in {'resume', 'retry'} and doc['state'] in {'paused', 'failed'}:
                if not doc['eligible']:raise ValueError('source_not_currently_eligible')
                doc['state'] = 'waiting_review' if doc['parser_complete'] else 'queued'
                doc['error'] = None
            else:
                raise ValueError('invalid_job_transition')
            doc['revision'] += 1
            self._recompute(db, doc, self.policy(db))
            self._save(db, doc)
            self._event(db, doc['id'], action, {'actor': request['actor']})
            return self._receipt(db, request, {'status': 'applied', 'revision': doc['revision']})

    def reconcile_sources(self, current, only_source=None):
        from .source_verification import METHOD, needs_method_refresh
        from ..domains.requirements.classification import VERSION as CLASSIFIER_VERSION
        score_version = requirement_scores.VERSION+':'+CLASSIFIER_VERSION
        with self.transaction() as db:
            for row in db.execute('SELECT data FROM documents').fetchall():
                doc = json.loads(row[0])
                if only_source and doc['source']['source_id']!=only_source:continue
                source = current.get(doc['source']['source_id'], {})
                eligible = (source.get('effective_selection', source.get('selection_status')) == 'INCLUDE'
                            and source.get('content_hash') == doc['source']['content_hash']
                            and source.get('snapshot_id') == doc['source'].get('snapshot_id'))
                original_issues=source.get('_original_issues',[])
                original_changed=doc.get('upstream_issues',[])!=original_issues
                changed = doc['eligible'] != eligible or original_changed
                verification_changed = needs_method_refresh(db, doc)
                broken = any(not Path(r['path']).is_file() or sha256(Path(r['path']).read_bytes()).hexdigest()!=r['sha256'] for r in doc['canonical'])
                if row_store.enabled(db):
                    gate_changed=bool(db.execute("""SELECT 1 FROM review_units WHERE document_id=?
                        AND (content_ok=1 OR requirement_ok=1)
                        AND (json_extract(data,'$.content_status')='machine_accepted'
                             OR json_extract(data,'$.requirement_status')='machine_accepted')
                        AND COALESCE(json_extract(data,'$.confidence_gate_version'),'')<>? LIMIT 1""",
                        (doc['id'],GATE_VERSION)).fetchone())
                    score_changed=bool(db.execute("""SELECT 1 FROM review_units WHERE document_id=?
                        AND json_extract(data,'$.requirement_status') IN ('machine_accepted','human_accepted')
                        AND COALESCE(json_extract(data,'$.requirement_score_version'),'')<>? LIMIT 1""",
                        (doc['id'],score_version)).fetchone())
                else:
                    gate_changed=any(u.get('confidence_gate_version')!=GATE_VERSION and
                        'machine_accepted' in (u.get('content_status'),u.get('requirement_status')) for u in doc.get('units',[]))
                    score_changed=any(u.get('requirement_status') in ('machine_accepted','human_accepted') and
                        u.get('requirement_score_version')!=score_version for u in doc.get('units',[]))
                if not changed and not broken and not gate_changed and not score_changed and not verification_changed and doc['policy_revision']==self.policy(db)['revision']:continue
                doc=self._load(db,doc['id'])
                if verification_changed:
                    doc['revision']+=1
                    self._event(db,doc['id'],'source_verification_method_updated',{'method':METHOD})
                if gate_changed:
                    doc['revision']+=1
                    self._event(db,doc['id'],'confidence_gate_updated',{'version':GATE_VERSION})
                if score_changed:
                    doc['revision']+=1
                    self._event(db,doc['id'],'classification_score_method_updated',{'version':score_version})
                if changed:
                    if original_changed:
                        doc['upstream_issues']=original_issues
                        doc['issues']=[i for i in doc['issues'] if not i.startswith('upstream_original_issue:')]+['upstream_original_issue:'+i['task_id'] for i in original_issues]
                        self._event(db,doc['id'],'upstream_original_issues',{'issues':original_issues})
                    doc['eligible'] = eligible
                    doc['revision'] += 1
                    if not eligible:
                        doc['state'] = 'paused'
                    self._event(db, doc['id'], 'eligibility', {'eligible': eligible})
                before = digest(doc)
                self._recompute(db, doc, self.policy(db))
                if changed or gate_changed or score_changed or verification_changed or digest(doc) != before:
                    self._save(db, doc)

    def snapshot(self):
        from .requirement_subdivision import count
        with self.connect() as db:
            docs = [self._load(db, row[0]) for row in db.execute('SELECT id FROM documents ORDER BY rowid')]
            return {'schema_version': 'system2-workflow/1', 'policy': self.policy(db), 'documents': docs,
                    'pending': sum(not accepted(u['content_status']) or not accepted(u['requirement_status'])
                                   for d in docs if d['eligible'] for u in d['units']),
                    'published': sum(count(d['published']) for d in docs)}

    def feed(self, after=0):
        from .requirement_subdivision import counted_rows
        with self.connect() as db:
            events = [dict(sequence=r['sequence'], document_id=r['document_id'], kind=r['kind'], **json.loads(r['data']))
                      for r in db.execute('SELECT * FROM events WHERE sequence>? ORDER BY sequence LIMIT 1001', (int(after),))]
            docs = [self._load(db, row[0]) for row in db.execute('SELECT id FROM documents ORDER BY rowid')]
        has_more=len(events)>1000
        events=events[:1000]
        return {'schema_version': 'system3-input/1', 'consumer_connected': False, 'events': events, 'has_more':has_more,
                'current_requirements':[item for d in docs for parent in d['published'].values() for item in counted_rows(parent)],
                'requirement_parents':[item for d in docs for item in d['published'].values() if item.get('subdivision')],
                'cursor': events[-1]['sequence'] if events else int(after),
                'documents': [{'id': d['id'], 'source_id': d['source']['source_id'], 'complete': d.get('complete', False),
                               'eligible': d['eligible'], 'state': d['state'],
                               'parser_complete':d['parser_complete'],
                               'unparsed_pages':[p+1 for p in range(d.get('total_pages',0)) if p not in d.get('processed_pages',[])],
                               'pending_ranges':[u['original']['references'] for u in d['units'] if u['kind']=='coverage' and not accepted(u['content_status'])],
                               'remaining': sum(
                                   not accepted(u['requirement_status']) for u in d['units'])}
                              for d in docs]}

    def weekly_qa(self, now=None, create=True):
        from datetime import timedelta
        from zoneinfo import ZoneInfo
        now = now or datetime.now(ZoneInfo('Europe/Oslo'))
        date = now.date(); week = (date - timedelta(days=date.weekday())).isoformat()
        with (self.transaction() if create else self.connect()) as db:
            if create and not db.execute('SELECT 1 FROM weekly_qa WHERE week=?',(week,)).fetchone():
                choices=[]
                for row in db.execute('SELECT data FROM documents').fetchall():
                    doc=self._load(db,json.loads(row[0])['id'])
                    for uid,item in doc['published'].items():
                        if item['decision_origin']=='machine':
                            choices.append({'document_id':doc['id'],'unit_id':uid,'unit_version':item['unit_version'],
                                            'source_sha256':doc['source']['content_hash'],'item':item})
                choices.sort(key=lambda value:digest([week,value['document_id'],value['unit_id']]))
                batch={'week':week,'items':[dict(c,id=digest([week,c['document_id'],c['unit_id']])[:32],
                           verdict=None,actor=None) for c in choices[:5]]}
                db.execute('INSERT INTO weekly_qa VALUES(?,?)',(week,encoded(batch)))
            batches=[json.loads(r[0]) for r in db.execute('SELECT data FROM weekly_qa ORDER BY week DESC LIMIT 5')]
        for batch in batches:
            n=len(batch['items']); reviewed=[x for x in batch['items'] if x['verdict']]
            batch['accuracy']=100*sum(x['verdict']=='CORRECT' for x in reviewed)/n if n and len(reviewed)==n else None
        return batches

    def qa_decision(self, request):
        with self.transaction() as db:
            replay=self._request(db,request)
            if replay is not None:return replay
            row=db.execute('SELECT data FROM weekly_qa WHERE week=?',(request['week'],)).fetchone()
            if not row:raise ValueError('qa_batch_not_found')
            batch=json.loads(row[0]);item=next((i for i in batch['items'] if i['id']==request['item_id']),None)
            if not item or item['verdict']:raise ValueError('qa_item_missing_or_already_reviewed')
            verdict=request['verdict'];note=request.get('note','').strip()
            if verdict not in {'CORRECT','INCORRECT'} or not note:raise ValueError('qa_verdict_and_evidence_note_required')
            doc=self._load(db,item['document_id']);unit=next((u for u in doc['units'] if u['id']==item['unit_id']),None)
            item.update(verdict=verdict,actor=request['actor'],note=note)
            if verdict=='INCORRECT' and unit and unit['version']==item['unit_version'] and doc['source']['content_hash']==item['source_sha256']:
                unit['blockers']=list(set(unit.get('blockers',[])+['human_reported_qa_issue']))
                unit['content_human']=False;unit['requirement_human']=False;unit['touched']=True
                unit['requirement_parts']=[]
                doc['revision']+=1
                self._recompute(db,doc,self.policy(db));self._save(db,doc)
            db.execute('UPDATE weekly_qa SET data=? WHERE week=?',(encoded(batch),request['week']))
            self._event(db,item['document_id'],'qa',item)
            return self._receipt(db,request,{'status':'applied','verdict':verdict})
