import fcntl
from hashlib import sha256
import json
from pathlib import Path
from uuid import uuid4

import pytest

from pdf_extraction.config import AppConfig
from pdf_extraction.models import Document
from pdf_extraction.review.transaction import (
    GuardedReviewRequest, ReviewConflict, apply_guarded_review, review_context,
)
from tests.integration.test_review_integrity import save_document


def request_for(path, **updates):
    context = review_context(path)
    payload = dict(
        request_id=uuid4(), expected_revision=context['revision'],
        expected_canonical_sha256=context['canonical_sha256'],
        expected_source_sha256=context['source_sha256'],
        decision=dict(actor='Tester', action='modify', target_type='block', target_id='rule',
                      new_value='The operator shall not exceed 4 mg.'),
    )
    payload.update(updates)
    return GuardedReviewRequest(**payload)


def test_commit_backup_and_replay_after_later_revision(tmp_path):
    _, path = save_document(tmp_path)
    old = path.read_bytes()
    request = request_for(path)
    first = apply_guarded_review(path, request, AppConfig())
    assert first.revision == 1
    revision_dir = path.parent / 'review-revisions'
    assert next(revision_dir.glob('*/before-canonical.json')).read_bytes() == old
    assert all(Path(a.path).is_file() for a in first.artifacts.values())
    for a in first.artifacts.values():
        assert a.sha256 == sha256(Path(a.path).read_bytes()).hexdigest()
    second_request = request_for(path, decision=dict(actor='Tester', page_index=0, label='A-1'))
    second = apply_guarded_review(path, second_request, AppConfig())
    before_replay = path.read_bytes()
    replayed = apply_guarded_review(path, request, AppConfig())
    assert replayed == first
    assert path.read_bytes() == before_replay and second.revision == 2
    assert len(list(revision_dir.iterdir())) == 2
    assert len(second.audit_events) == 2
    assert second.processing.status.value == second.quality.status.value


@pytest.mark.parametrize('updates', [
    {'expected_revision': 9}, {'expected_canonical_sha256': 'a'*64},
    {'expected_source_sha256': 'other-source'},
])
def test_stale_request_leaves_bytes_unchanged(tmp_path, updates):
    _, path = save_document(tmp_path)
    old = path.read_bytes()
    with pytest.raises(ReviewConflict, match='stale'):
        apply_guarded_review(path, request_for(path, **updates), AppConfig())
    assert path.read_bytes() == old
    assert not (path.parent / 'review-revisions').exists()


def test_request_id_cannot_be_reused_for_another_decision(tmp_path):
    _, path = save_document(tmp_path)
    request = request_for(path)
    apply_guarded_review(path, request, AppConfig())
    old = path.read_bytes()
    altered = request.model_copy(deep=True)
    altered.decision.new_value = 'Different'
    with pytest.raises(ReviewConflict, match='reused'):
        apply_guarded_review(path, altered, AppConfig())
    assert path.read_bytes() == old


def test_concurrent_writer_defers(tmp_path):
    _, path = save_document(tmp_path)
    with (path.parent / '.review.lock').open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(ReviewConflict, match='busy'):
            apply_guarded_review(path, request_for(path), AppConfig())
    assert Document.model_validate_json(path.read_bytes()).revision == 0


def test_publish_failure_retains_canonical_and_retry_is_safe(tmp_path, monkeypatch):
    from pdf_extraction.review import transaction
    _, path = save_document(tmp_path)
    request = request_for(path)
    before = path.read_bytes()
    replace = transaction.os.replace
    def fail(*args):
        raise OSError('simulated publication failure')
    monkeypatch.setattr(transaction.os, 'replace', fail)
    with pytest.raises(OSError, match='publication'):
        apply_guarded_review(path, request, AppConfig())
    assert path.read_bytes() == before
    monkeypatch.setattr(transaction.os, 'replace', replace)
    committed = apply_guarded_review(path, request, AppConfig())
    assert committed.revision == 1
    assert len(committed.audit_events) == 1


def test_export_failure_never_changes_current_outputs(tmp_path, monkeypatch):
    from pdf_extraction.review import service
    _, path = save_document(tmp_path)
    before = path.read_bytes()
    def fail(*args):
        raise OSError('simulated export failure')
    monkeypatch.setattr(service, 'write_derived_artifacts', fail)
    with pytest.raises(OSError, match='export'):
        apply_guarded_review(path, request_for(path), AppConfig())
    assert path.read_bytes() == before


def test_guarded_http_endpoint_reloads_current_quality(tmp_path):
    from fastapi.testclient import TestClient
    from pdf_extraction.api.app import create_app
    from tests.support.paths import PROJECT_ROOT
    _, path = save_document(tmp_path)
    config = tmp_path / 'config.yaml'
    config.write_text('{}')
    app = create_app(tmp_path/'jobs.sqlite', PROJECT_ROOT/'ui')
    job = app.state.store.create(str(tmp_path/'source.pdf'), str(path.parent), str(config))
    client = TestClient(app)
    ctx = client.get(f'/jobs/{job.id}/review-context').json()
    assert ctx['canonical_sha256'] == sha256(path.read_bytes()).hexdigest()
    request = request_for(path)
    response = client.post(f'/jobs/{job.id}/reviews/guarded', json=request.model_dump(mode='json'))
    assert response.status_code == 200, response.text
    quality = client.get(f'/jobs/{job.id}/quality').json()
    assert quality['audit_event_count'] == 1
    stale = request.model_copy(update={'request_id':uuid4()})
    assert client.post(f'/jobs/{job.id}/reviews/guarded', json=stale.model_dump(mode='json')).status_code == 409
