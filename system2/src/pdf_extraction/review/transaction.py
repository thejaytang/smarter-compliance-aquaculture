"""Versioned PDF review transactions. Canonical replacement is the commit point.

The compatibility review functions run only inside a new isolated revision here.
Readers follow Canonical artifact references; earlier exports are retained.
"""
from __future__ import annotations

import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from ..config import AppConfig
from ..models import ArtifactReference, Document, ProcessingStatus
from ..validate import build_quality_report, validate_document
from .service import PageLabelDecision, ReviewDecision, apply_review_decision, correct_page_label


class ReviewConflict(ValueError):
    """Client must reload or retry the same request after a busy writer."""


class GuardedReviewRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: UUID
    expected_revision: int = Field(ge=0)
    expected_canonical_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    expected_source_sha256: str = Field(min_length=1)
    decision: ReviewDecision | PageLabelDecision


def review_context(path: str | Path) -> dict:
    raw = Path(path).read_bytes()
    document = Document.model_validate_json(raw)
    return {'document': document.model_dump(mode='json'),
            'canonical_sha256': sha256(raw).hexdigest(),
            'source_sha256': document.source.file_hash, 'revision': document.revision}


def _write(path: Path, raw: bytes) -> None:
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _artifact(path: Path) -> ArtifactReference:
    return ArtifactReference(path=str(path), media_type='application/json',
                             sha256=sha256(path.read_bytes()).hexdigest())


def _replay(document: Document, request: GuardedReviewRequest, digest: str, root: Path) -> Document | None:
    reference = document.artifacts.get('review_receipt')
    seen = set()
    while reference:
        path = Path(reference.path).resolve()
        if not path.is_relative_to(root) or path in seen:
            raise ReviewConflict('invalid_review_history_path')
        seen.add(path)
        raw = path.read_bytes()
        if sha256(raw).hexdigest() != reference.sha256:
            raise ReviewConflict('review_history_hash_mismatch')
        receipt = json.loads(raw)
        if receipt['request_id'] == str(request.request_id):
            if receipt['request_sha256'] != digest:
                raise ReviewConflict('request_id_reused_with_different_payload')
            revision_path = path.parent / 'canonical.json'
            revised = Document.model_validate_json(revision_path.read_bytes())
            # Return the exact receipt's applied version, even after later edits.
            if revised.revision != receipt['revision'] or revised.artifacts.get('review_receipt') != reference:
                raise ReviewConflict('review_history_revision_mismatch')
            payload = revised.model_copy(deep=True)
            payload.artifacts.pop('review_receipt', None)
            if sha256(payload.model_dump_json().encode()).hexdigest() != receipt['canonical_payload_sha256']:
                raise ReviewConflict('review_history_canonical_hash_mismatch')
            return revised
        previous = receipt.get('previous_receipt')
        reference = ArtifactReference.model_validate(previous) if previous else None
    return None


def apply_guarded_review(canonical_path: str | Path, request: GuardedReviewRequest,
                        config: AppConfig) -> Document:
    path = Path(canonical_path).resolve()
    root = path.parent
    digest = sha256(request.model_dump_json().encode()).hexdigest()
    with (root / '.review.lock').open('a+b') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ReviewConflict('review_writer_busy') from exc
        raw = path.read_bytes()
        current = Document.model_validate_json(raw)
        replayed = _replay(current, request, digest, root)
        if replayed is not None:
            return replayed
        if (request.expected_revision != current.revision
            or request.expected_canonical_sha256 != sha256(raw).hexdigest()
            or request.expected_source_sha256 != current.source.file_hash):
            raise ReviewConflict('stale_source_or_canonical_revision')

        revision_dir = root / 'review-revisions' / str(uuid4())
        revision_dir.mkdir(parents=True)
        _write(revision_dir / 'before-canonical.json', raw)
        _write(revision_dir / 'canonical.json', raw)
        _write(revision_dir / 'audit-events.jsonl', ''.join(
            json.dumps(e.model_dump(mode='json'), ensure_ascii=False) + '\n'
            for e in current.audit_events
        ).encode())
        decision = request.decision
        apply = correct_page_label if isinstance(decision, PageLabelDecision) else apply_review_decision
        document = apply(revision_dir / 'canonical.json', decision, config)
        document.processing.status = ProcessingStatus(document.quality.status.value)

        # Machine verification remains immutable evidence for its original run.
        # This separate report records the human decision and current revision.
        report_path = revision_dir / 'review-verification.json'
        _write(report_path, json.dumps({
            'schema_version': 'review-verification/1', 'revision': document.revision,
            'source_sha256': document.source.file_hash,
            'status': document.quality.status.value, 'review_queue': document.review_queue,
            'machine_verification': current.artifacts.get('verification_report').model_dump()
                if current.artifacts.get('verification_report') else None,
            'meaning': 'Human decision scope only; no new independent machine verification.',
        }, ensure_ascii=False, indent=2).encode())
        document.artifacts['review_verification'] = _artifact(report_path)
        quality_path = revision_dir / 'quality-report.json'
        quality_path.write_text(json.dumps(build_quality_report(document), ensure_ascii=False, indent=2))
        document.artifacts['quality_report'] = _artifact(quality_path)
        document.artifacts.pop('review_receipt', None)
        receipt_path = revision_dir / 'receipt.json'
        _write(receipt_path, json.dumps({
            'schema_version': 'review-receipt/1', 'request_id': str(request.request_id),
            'request_sha256': digest, 'revision': document.revision,
            'before_canonical_sha256': sha256(raw).hexdigest(),
            'canonical_payload_sha256': sha256(document.model_dump_json().encode()).hexdigest(),
            'previous_receipt': current.artifacts['review_receipt'].model_dump()
                if 'review_receipt' in current.artifacts else None,
        }, indent=2).encode())
        document.artifacts['review_receipt'] = _artifact(receipt_path)
        errors = validate_document(document)
        if errors:
            raise ValueError('invalid_review_revision: ' + '; '.join(errors))
        revised = document.model_dump_json(indent=2).encode()
        (revision_dir / 'canonical.json').write_bytes(revised)
        candidate = revision_dir / 'publish.json'
        _write(candidate, revised)
        # A non-cooperating writer must not be silently overwritten.
        if path.read_bytes() != raw:
            raise ReviewConflict('canonical_changed_during_review')
        os.replace(candidate, path)
        return document
