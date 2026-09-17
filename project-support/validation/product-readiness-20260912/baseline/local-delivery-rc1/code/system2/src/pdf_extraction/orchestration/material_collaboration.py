"""Trusted local adapter commands for isolated drafts and explicit master adoption.

These commands are never browser-facing; Workbench validates package, actor and
workspace ownership before supplying their arguments. Existing saved versions
remain the authority, and inherited checks retain their original provenance.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import os
import tempfile
from datetime import datetime
import uuid

from ..contracts.hashing import digest, encoded
from ..review.materials import validate_blocks, now
from ..contracts.source import Snapshot
from ..evidence.material_reader import inspect_original
from ..review.material_impact import review_impact
from ..intake.system1 import System1Handoff, _version


def offline_handoff(root):
    marker = Path(root) / 'offline-source.json'
    if not marker.exists():
        return None
    data = json.loads(marker.read_text())
    # Only a workspace-owned immutable catalog is used; submitted source edits
    # do not alter this extraction authority.
    return System1Handoff(data['records'], digest(data['records']),
        Path(data['source_root']), data.get('evidence', {}), {marker: _version(marker)})


# Reader/HTTP projections are not saved document state and must not participate in
# portable baseline hashes or become executable candidate rows in a reviewer clone.
DERIVED = {'candidates', 'conflicts', 'related_versions', 'source_issues',
           'source_check_error', 'historical', 'collaboration', 'block_count',
           'scope_count', 'checked_scope_count', 'candidate_count', 'conflict_count'}
IDENTITY_FIELDS = ('source_id', 'snapshot_id', 'content_hash')


def normalized(material):
    if not isinstance(material, dict):
        raise ValueError('Package material must be an object.')
    return deepcopy({k: v for k, v in material.items() if k not in DERIVED})


def _named(value):
    return isinstance(value, str) and value.strip() and value.strip().lower() not in ('machine', 'system', 'anonymous')


def _check_stamp(check, material):
    if not isinstance(check, dict) or not _named(check.get('actor')):
        return False
    try:
        datetime.fromisoformat(check['at'])
    except (ValueError, TypeError, KeyError):
        return False
    limit = material['content_revision']
    origin = check.get('inherited_from')
    if origin is not None:
        if (not isinstance(origin, dict) or origin.get('material_id') != material['id']
                or origin.get('source_hash') != material['source']['content_hash']
                or type(origin.get('content_revision')) is not int or origin['content_revision'] < 0
                or type(origin.get('revision')) is not int or origin['revision'] < origin['content_revision']):
            return False
        limit = origin['content_revision']
    return (type(check.get('content_revision')) is int
            and 0 <= check['content_revision'] <= limit
            and check.get('source_hash') == material['source']['content_hash'])


def _document(material):
    try:
        Snapshot(**material['source'])
        expected = digest({k: material['source'][k] for k in IDENTITY_FIELDS})[:32]
        if material['id'] != expected:
            raise ValueError('Package material identity does not match its original.')
        if any(type(material.get(k)) is not int or material[k] < 0 for k in ('revision', 'content_revision')):
            raise ValueError('Package material revisions must be nonnegative integers.')
        if material['content_revision'] > material['revision']:
            raise ValueError('Package content revision exceeds the material revision.')
        scope = material['scope']
        if (not isinstance(scope, list) or not scope or any(not isinstance(s, dict)
                or not isinstance(s.get('id'), str) or not s['id'] for s in scope)
                or len({s['id'] for s in scope}) != len(scope)):
            raise ValueError('Package original scope must be complete and uniquely identified.')
        validate_blocks(material['blocks'], scope)
        issues = material['issues']
        if (not isinstance(issues, list) or any(not isinstance(i, dict) or not isinstance(i.get('id'), str)
                or not i['id'] or not isinstance(i.get('message'), str)
                or type(i.get('resolved', False)) is not bool for i in issues)
                or len({i['id'] for i in issues}) != len(issues)):
            raise ValueError('Package content issues are invalid.')
        scopes = {s['id'] for s in scope}
        checked, checks = material['checked_scope'], material.get('review_checks', {})
        if (not isinstance(checked, list) or any(s not in scopes for s in checked)
                or len(set(checked)) != len(checked) or not isinstance(checks, dict)
                or any(s not in scopes or not _check_stamp(c, material) for s, c in checks.items())):
            raise ValueError('Package review checks are outside the original or lack valid provenance.')
        if type(material['source_stale']) is not bool or type(material['association_review_required']) is not bool:
            raise ValueError('Package review state is invalid.')
        if material.get('requirement_status') != 'not_connected':
            raise ValueError('Structured Requirement processing is not connected.')
        if material.get('content_status') not in ('not_extracted', 'draft', 'review_in_progress', 'content_review_complete'):
            raise ValueError('Unknown material content status.')
        confirmation = material.get('confirmation')
        if confirmation is not None and (not _check_stamp(confirmation, material)
                or set(confirmation.get('checked_scope', [])) != scopes):
            raise ValueError('Package confirmation provenance or scope is invalid.')
        # A stale material may retain an older confirmation as immutable evidence.
        if material['content_status'] == 'content_review_complete' and not confirmation:
            raise ValueError('Completed content review requires a historical human confirmation.')
        encoded(material)
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError('Malformed package material document.') from exc
    return material


def validate_package(request):
    material = _document(normalized(request['material']))
    raw_history = request.get('history')
    if not isinstance(raw_history, list) or not raw_history:
        raise ValueError('Complete material history is required.')
    history = [_document(normalized(r)) for r in raw_history]
    revisions = [r['revision'] for r in history]
    if len(set(revisions)) != len(revisions) or sorted(revisions) != list(range(material['revision'] + 1)):
        raise ValueError('Package material history has duplicate, missing or future revisions.')
    history.sort(key=lambda r: r['revision'])
    for revision in history:
        if (revision['id'] != material['id'] or revision['source'] != material['source']
                or revision['scope'] != material['scope']):
            raise ValueError('Cross-material source or original scope in package history.')
    if history[-1] != material:
        raise ValueError('Package current material differs from its final historical revision.')
    for previous, current in zip(history, history[1:]):
        if current['content_revision'] not in (previous['content_revision'], previous['content_revision'] + 1):
            raise ValueError('Package content revision history is not monotonic.')
        if (current['blocks'] != previous['blocks'] or current['issues'] != previous['issues']) and current['content_revision'] == previous['content_revision']:
            raise ValueError('Package changed content without a content revision.')
    return material, history


def retained_checks(origins, blocks, issues, material):
    result = {}
    scope_ids = {s['id'] for s in material['scope']}
    for origin in origins:
        if not isinstance(origin, dict) or origin.get('id') != material['id']:
            continue
        if (origin.get('scope') != material['scope'] or origin.get('source_stale')
                or any(origin.get('source', {}).get(k) != material['source'].get(k) for k in IDENTITY_FIELDS)):
            continue
        allowed = review_impact(origin, blocks, issues)['retained_scope']
        for scope in allowed:
            check = origin.get('review_checks', {}).get(scope)
            if scope in scope_ids and _check_stamp(check, origin):
                retained = deepcopy(check)
                if origin is not material and 'inherited_from' not in retained:
                    retained['inherited_from'] = {'material_id': origin['id'], 'revision': origin['revision'],
                        'content_revision': origin['content_revision'], 'source_hash': origin['source']['content_hash']}
                result.setdefault(scope, retained)
    return result


def _evidence(request, material):
    result = {}
    for kind in ('candidate', 'conflict'):
        rows = request.get(kind+'_evidence', [])
        if not isinstance(rows, list):
            raise ValueError('Package evidence must be a list.')
        ids = set()
        for item in rows:
            try:
                valid_id = isinstance(item, dict) and str(uuid.UUID(item['id'])) == item['id']
            except (ValueError, TypeError, KeyError, AttributeError):
                valid_id = False
            if not valid_id or item['id'] in ids or item.get('material_id') != material['id']:
                raise ValueError('Package evidence identity belongs to a different material or is duplicated.')
            ids.add(item['id'])
            if kind == 'candidate':
                if (item.get('source') != material['source'] or item.get('scope') != material['scope']
                        or type(item.get('input_revision')) is not int
                        or not 0 <= item['input_revision'] <= material['content_revision']
                        or item.get('status') not in ('running', 'ready', 'partial', 'failed', 'kept', 'adopted', 'merged')):
                    raise ValueError('Package candidate evidence input or status is invalid.')
                validate_blocks(item.get('blocks'), material['scope'])
                validate_blocks(item.get('base_blocks'), material['scope'])
            encoded(item)
        result[kind] = rows
    return result


def _saved_evidence(db, identity=None):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='material_collaboration_evidence'").fetchone():
        return []
    query = 'SELECT kind,material_id,data FROM material_collaboration_evidence'
    return [(r[0], r[1], json.loads(r[2])) for r in db.execute(
        query + (' WHERE material_id=?' if identity else ''), (identity,) if identity else ())]


def _pin_package(service, material, source):
    path = service._path(material['source'])
    expected = material['source']['content_hash']
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix=path.suffix, delete=False) as target:
            temporary = Path(target.name)
            fingerprint = sha256()
            with Path(source).open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    target.write(chunk);fingerprint.update(chunk)
            target.flush();os.fsync(target.fileno())
        if fingerprint.hexdigest() != expected:
            raise ValueError('Package original fingerprint differs from the material.')
        if inspect_original(temporary, expected)['scope'] != material['scope']:
            raise ValueError('Package scope differs from the complete original document.')
        try:
            os.link(temporary, path)
        except FileExistsError:
            if sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError('Existing original is corrupt; source was not replaced.')
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return path


def _source_guard(service, material, request):
    if material['source_stale'] or request.get('expected_source_hash') != material['source']['content_hash']:
        raise ValueError('Source version changed; prepare a new collaboration comparison.')
    handoff = service.handoff()
    current = next((r for r in handoff.records if r['source_id'] == material['source']['source_id']), {})
    if (any(current.get(k) != material['source'][k] for k in IDENTITY_FIELDS)
            or any(current.get(k) != value for k, value in
                   {'selection_status': 'INCLUDE', 'snapshot_status': 'STORED',
                    'source_status': 'CURRENT', 'download_status': 'SUCCESS'}.items())):
        raise ValueError('Source original or eligibility changed; adoption requires a new comparison.')
    path = service._path(material['source'])
    if sha256(path.read_bytes()).hexdigest() != material['source']['content_hash']:
        raise ValueError('pinned_original_integrity_failure')
    handoff.assert_current()
    return handoff


def command(service, action, request):
    store = service.store
    if action == 'export':
        with store.connect() as db:
            # One read snapshot prevents exporting a head from one revision and a
            # history from a concurrent write. Derived UI state stays separate.
            db.execute('BEGIN')
            material = normalized(store._load(db, request['material_id']))
            history = [json.loads(r[0]) for r in db.execute(
                'SELECT data FROM material_revisions WHERE material_id=? ORDER BY revision', (material['id'],))]
            evidence = {key: [json.loads(r[0]) for r in db.execute(
                'SELECT data FROM '+table+' WHERE material_id=? ORDER BY rowid', (material['id'],))]
                for key, table in [('candidates', 'material_candidates'), ('conflicts', 'material_conflicts')]}
            for kind, _, item in _saved_evidence(db, material['id']):
                if item['id'] not in {r['id'] for r in evidence[kind+'s']}:
                    evidence[kind+'s'].append(item)
        material, history = validate_package({'material': material, 'history': history})
        return {'material': material, 'history': history, 'original': service.original(material['id']),
                'candidate_evidence': evidence['candidates'], 'conflict_evidence': evidence['conflicts']}
    if action == 'validate':
        material, history = validate_package(request)
        _evidence(request, material)
        return {'status': 'valid', 'material_id': material['id'], 'revision': material['revision'],
                'history_count': len(history), 'digest': digest(material)}
    if action == 'seed':
        material, history = validate_package(request)
        evidence = _evidence(request, material)
        with store.transaction() as db:
            prior = db.execute('SELECT data FROM material_documents WHERE id=?', (material['id'],)).fetchone()
            if prior:
                if normalized(json.loads(prior[0])) != material:
                    raise ValueError('Existing material differs; a package cannot overwrite saved local work.')
                existing = [normalized(json.loads(r[0])) for r in db.execute(
                    'SELECT data FROM material_revisions WHERE material_id=? ORDER BY revision', (material['id'],))]
                if existing != history:
                    raise ValueError('Existing material history differs; no historical version was replaced.')
                _pin_package(service, material, request['original_path'])
            else:
                _pin_package(service, material, request['original_path'])
                db.execute('INSERT INTO material_documents VALUES(?,?,?)',
                    (material['id'], material['source']['source_id'], encoded(material)))
                for revision in history:
                    db.execute('INSERT INTO material_revisions VALUES(?,?,?)',
                        (material['id'], revision['revision'], encoded(revision)))
            db.execute('CREATE TABLE IF NOT EXISTS material_collaboration_evidence('
                       'kind TEXT NOT NULL, material_id TEXT NOT NULL, id TEXT NOT NULL, data TEXT NOT NULL,'
                       'PRIMARY KEY(kind,material_id,id))')
            for kind, rows in evidence.items():
                for item in rows:
                    old = db.execute('SELECT data FROM material_collaboration_evidence WHERE kind=? AND material_id=? AND id=?',
                                     (kind, material['id'], item['id'])).fetchone()
                    if old and json.loads(old[0]) != item:
                        raise ValueError('Existing candidate/conflict evidence cannot be overwritten.')
                    if not old:
                        db.execute('INSERT INTO material_collaboration_evidence VALUES(?,?,?,?)',
                                   (kind, material['id'], item['id'], encoded(item)))
        return store.read_compact(material['id'])
    if action == 'adopt-master':
        if request.get('actor') != 'Weijie Tang':
            raise ValueError('Only the coordinator may adopt a main material version.')
        with store.transaction() as db:
            req, material, replay = store._begin(db, request, 'collaboration_adopt')
            if replay is not None:
                return replay
            handoff = _source_guard(service, material, req)
            blocks, issues = req['blocks'], req['issues']
            origins = []
            for origin in req.get('review_origins', []):
                origin = _document(normalized(origin))
                if (origin['id'] != material['id'] or origin['scope'] != material['scope']
                        or any(origin['source'][k] != material['source'][k] for k in IDENTITY_FIELDS)):
                    raise ValueError('Review origin belongs to a different material or original scope.')
                origins.append(origin)
            checks = retained_checks([material, *origins], blocks, issues, material)
            store._edit(material, dict(req, checked_scope=[]))
            material['checked_scope'] = sorted(checks)
            material['review_checks'] = checks
            material['confirmation'] = None
            material['content_status'] = 'review_in_progress' if checks else 'draft'
            material['collaboration_provenance'] = deepcopy(req.get('provenance', []))
            material.setdefault('collaboration_adoptions', []).append({
                'request_id': req['request_id'], 'actor': req['actor'], 'at': now(),
                'submission_id': req['submission_id'], 'contributors': req.get('contributors', []),
                'decisions': req.get('decisions', {}), 'base_digest': req['base_digest']})
            handoff.assert_current()
            material['revision'] += 1
            store._write(db, material, 'collaboration_adopted', req['actor'])
            return store._receipt(db, req, {'status': 'applied', 'material': store._view(db, material)})
    if action == 'repeat-resolution':
        with store.transaction() as db:
            rows = [(r[0], r[1], json.loads(r[2])) for r in db.execute('SELECT id,material_id,data FROM material_candidates')]
            prior_rows = rows + [(item['id'], mid, item) for kind, mid, item in _saved_evidence(db) if kind == 'candidate']
            changed = []
            for cid, mid, candidate in rows:
                if candidate['status'] not in ('ready', 'partial'):
                    continue
                material = store._load(db, mid)
                if (material.get('source_stale') or candidate['input_revision'] != material['content_revision']
                        or candidate['source'] != material['source'] or candidate['scope'] != material['scope']
                        or candidate['base_blocks'] != material['blocks']):
                    continue
                for previous_id, previous_mid, previous in prior_rows:
                    adoption = previous.get('adoption', {})
                    if (previous_mid == mid and previous_id != cid and adoption
                            and previous.get('status') in ('kept', 'adopted', 'merged')
                            and all(previous.get(k) == candidate.get(k)
                                    for k in ('source', 'scope', 'blocks', 'complete', 'warnings', 'error'))
                            and adoption.get('reviewed_against_source') is True and _named(adoption.get('actor'))
                            and adoption.get('result_content_revision') == material['content_revision']):
                        candidate['status'] = 'kept'
                        provenance = {'candidate_id': cid, 'prior_candidate_id': previous_id,
                                      'at': now(), 'adoption': deepcopy(adoption),
                                      'reason': 'Identical candidate output and unchanged human result; prior explicit resolution reused.'}
                        candidate['prior_resolution'] = provenance
                        db.execute('UPDATE material_candidates SET data=? WHERE id=?', (encoded(candidate), cid))
                        material.setdefault('collaboration_resolution_reuse', []).append(provenance)
                        material['revision'] += 1
                        store._write(db, material, 'candidate_prior_resolution_reused', 'system_reuse')
                        changed.append(cid)
                        break
            return {'reused_resolution_candidates': changed}
    raise ValueError('Unknown collaboration material command.')
