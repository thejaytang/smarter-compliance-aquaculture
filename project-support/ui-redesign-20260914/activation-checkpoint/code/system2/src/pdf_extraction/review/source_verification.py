"""Version-bound original checks enter the existing page completeness task."""
from hashlib import sha256
from pathlib import Path
import time
import os
import tempfile

from ..contracts.hashing import digest, encoded
from ..verification.source_comparison import METHOD, compare
from . import repairs
from .pdf_scope import refresh
from .source_verification_input import comparison_input


def needs_method_refresh(db, doc):
    """Check cached report versions without hydrating an unchanged document."""
    if not doc.get('source_verification_pages'):
        return False
    from . import row_store
    if row_store.enabled(db):
        return bool(db.execute("""SELECT 1 FROM review_units WHERE document_id=?
            AND json_extract(data,'$.source_verification') IS NOT NULL
            AND COALESCE(json_extract(data,'$.source_verification.stale'),0)=0
            AND COALESCE(json_extract(data,'$.source_verification.method'),'')<>?
            LIMIT 1""", (doc['id'], METHOD)).fetchone())
    return any(report and not report.get('stale') and report.get('method') != METHOD
               for unit in doc.get('units', [])
               for report in [unit.get('source_verification')])


def refresh_staleness(doc):
    changed = []
    for unit in doc['units']:
        report = unit.get('source_verification')
        if not report or report.get('stale'):
            continue
        if (report.get('method') != METHOD
                or report['input_sha256'] != digest(comparison_input(doc, report['page_index']))):
            report['stale'] = True
            if 'source_verification_stale' not in unit['blockers']:
                unit['blockers'].append('source_verification_stale')
            changed.append(unit['id'])
    repairs.invalidate({u['id']: u for u in doc['units']}, changed)


def verify_page(store, source_path, request, *, parser_engines=(), language='eng'):
    """Run outside the write lock; reject changed source/results on application.

    Caller resolves source_path from the governed registry, never browser paths.
    Findings are machine evidence. They do not impersonate a human approval.
    """
    from ..verification.pdf_original import acquire
    started = time.monotonic()
    p = request['page_index']
    with store.connect() as db:
        replay = store._request(db, request)
        if replay is not None:
            return replay
        doc = store._load(db, request['document_id'])
        if (doc['source'].get('file_format') != 'pdf' or type(p) is not int or not 0 <= p < doc.get('total_pages', 0)):
            raise ValueError('invalid_original_page')
        if not doc['eligible'] or request['source_sha256'] != doc['source']['content_hash'] or request['revision'] != doc['revision']:
            raise ValueError('stale_source_or_result')
        records = comparison_input(doc, p)
    source_path = Path(source_path).resolve()
    if sha256(source_path.read_bytes()).hexdigest() != doc['source']['content_hash']:
        raise ValueError('source_artifact_mismatch')
    original = acquire(source_path, p, parser_engines=parser_engines, language=language)
    result = compare(original, records)
    # Keep the exact original-side observations and effective input used for a
    # comparison. Failed/stale runs may leave an unreferenced evidence artifact;
    # only a committed database event gives it business authority.
    bundle = encoded({'schema': 'source-verification-evidence/1', 'original': original, 'records': records}).encode()
    artifact_hash = sha256(bundle).hexdigest()
    evidence_root = store.root / 'source-verification'
    evidence_root.mkdir(exist_ok=True)
    artifact = evidence_root / (artifact_hash+'.json')
    fd, name = tempfile.mkstemp(dir=evidence_root, prefix='.check-')
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(bundle); handle.flush(); os.fsync(handle.fileno())
        Path(name).replace(artifact)
    finally:
        Path(name).unlink(missing_ok=True)
    report = dict(result, schema_version='source-verification/1', page_index=p,
                  source_sha256=original['source_sha256'], input_sha256=digest(records),
                  evidence=original['evidence'], parser_engines=list(parser_engines),
                  dimensions={'width': original['width'], 'height': original['height']},
                  method=METHOD, stale=False,
                  evidence_artifact={'path': str(artifact.relative_to(store.root)), 'sha256': artifact_hash},
                  tool_versions=original.get('tool_versions', {}), timing_scope='precommit_comparison',
                  elapsed_seconds=round(time.monotonic()-started, 3))
    report['report_id'] = digest(report)
    with store.transaction() as db:
        replay = store._request(db, request)
        if replay is not None:
            return replay
        current = store._load(db, doc['id'])
        if (not current['eligible'] or current['revision'] != doc['revision']
                or digest(comparison_input(current, p)) != report['input_sha256']
                or sha256(source_path.read_bytes()).hexdigest() != report['source_sha256']):
            raise ValueError('verification_result_stale')
        # Creates original-side scope even when the extractor emitted no item.
        from ..domains.requirements.pdf_review_scope import localize
        existing = {u['id'] for u in current['units']}
        for value in localize(current['units'], [p]):
            if value['id'] not in existing:
                value.update(version=1, edits={}, touched=False, content_human=False,
                             requirement_human=False, classification='undetermined',
                             content_status='pending', requirement_status='blocked')
                current['units'].append(value)
        refresh(current)
        coverage = next(u for u in current['units'] if u['id'] == 'coverage:pdf-page:'+str(p))
        old_codes = set(coverage.get('source_verification_codes', []))
        codes = ['source_check:'+f['id'] for f in report['findings']]
        codes += ['source_scope:'+digest(u)[:24] for u in report['unverified']]
        coverage['blockers'] = list(dict.fromkeys([c for c in coverage['blockers']
            if c not in old_codes and c != 'source_verification_stale']+codes))
        coverage['source_verification'] = report
        coverage['source_verification_codes'] = codes
        # A recheck preserves all earlier human history, but cannot inherit a
        # page acceptance from a different comparison run.
        repairs.invalidate({u['id']: u for u in current['units']}, [coverage['id']])
        current['source_verification_pages'] = sorted(set(current.get('source_verification_pages', [])) | {p})
        current['revision'] += 1
        store._recompute(db, current, store.policy(db))
        store._event(db, current['id'], 'source_verification', {'actor': request['actor'], 'report': report})
        store._save(db, current)
        return store._receipt(db, request, {'status': 'applied', 'revision': current['revision'],
                                           'unit_id': coverage['id'], 'report': report})
