"""Synthetic controls for source follow-up, not real-source accuracy labels."""
from copy import deepcopy
from hashlib import sha256
import json
import uuid
import pytest
from pdf_extraction.review.workflow import Workflow
from pdf_extraction.review.browser_view import browser_state
from pdf_extraction.review.processing_failure import describe, html_observations
from pdf_extraction.evidence.review_preview import sanitized_region


def request(**kwargs):
    return dict(request_id=str(uuid.uuid4()),actor='Ana Jokic',**kwargs)


@pytest.fixture
def failure(tmp_path):
    store=Workflow(tmp_path)
    source={'source_id':'TEST01','snapshot_id':'TEST01-001','file_format':'html',
            'content_hash':'a'*64,'selection_status':'INCLUDE'}
    did=store.enqueue([source],request())['documents'][0]
    with store.transaction() as db:
        doc=store._load(db,did)
        doc.update(state='failed',issues=['HtmlProfileError:html_empty_body'])
        store._save(db,doc)
    return store,did


def test_zero_extracted_units_still_have_source_followup_without_fabricated_content(failure):
    store,did=failure;before=deepcopy(store.snapshot())
    summary=browser_state(store,'summary')
    assert summary['pending']==0 and summary['processing_followups']==1
    d=summary['documents'][0]
    assert d['unit_count']==0 and d['processing_failure']['missing_body']
    detail=browser_state(store,'unit',did,'processing-failure')
    assert detail['processing_failure']['source_sha256']=='a'*64
    assert 'unit' not in detail and detail['effective']['references']
    assert store.snapshot()==before


def test_pausing_does_not_hide_a_known_body_problem(failure):
    store,did=failure
    with store.transaction() as db:
        doc=store._load(db,did);doc['state']='paused';store._save(db,doc)
    assert browser_state(store,'summary')['processing_followups']==1


def test_retry_retains_attempt_and_replay_is_idempotent(failure):
    store,did=failure;before=store.snapshot()['documents'][0]
    req=request(document_id=did,revision=before['revision'],action='retry')
    receipt=store.control(req);events=store.feed()['events']
    assert len([e for e in events if e['kind']=='processing_failure'])==1
    assert store.control(req)==receipt and store.feed()['events']==events
    after=store.snapshot()['documents'][0]
    assert after['source']==before['source'] and after['units']==before['units']
    assert after['issues']==before['issues'] and describe(after)['missing_body']


def test_usable_result_retires_only_parser_failure_and_keeps_other_holds(failure):
    store,did=failure;before=store.snapshot()['documents'][0]
    store.control(request(document_id=did,revision=before['revision'],action='retry'))
    with store.transaction() as db:
        doc=store._load(db,did);doc['issues']+=['upstream_original_issue:reported','canonical_artifact_changed'];store._save(db,doc)
    path=store.root/'canonical.json';path.write_text('{}')
    store.install(did,[],[{'path':str(path),'sha256':sha256(path.read_bytes()).hexdigest()}])
    doc=store.snapshot()['documents'][0]
    assert doc['issues']==['upstream_original_issue:reported','canonical_artifact_changed']
    assert not doc['published'] and not doc['complete']
    assert len([e for e in store.feed()['events'] if e['kind']=='processing_recovered'])==1
    assert any(e['kind']=='processing_failure' and 'html_empty_body' in e['codes'][0] for e in store.feed()['events'])


def test_original_probe_and_preview_preserve_empty_body_and_never_follow_links():
    raw=b'''<html><head><title>Test original</title></head><body>
    <div><div id="documentMeta"><h1>Test metadata</h1></div><div id="documentBody"></div></div>
    <ul class="pager"><li class="complete"><a href="/dokument/test/*">Vis hele dokumentet</a></li>
    <li class="complete"><a href="javascript:alert(1)">Unsafe</a></li></ul><script>alert(1)</script></body></html>'''
    observed=html_observations(raw)
    assert observed['content_regions'][0]['empty'] and observed['content_regions'][0]['text_characters']==0
    assert observed['full_document_links']==[{'label':'Vis hele dokumentet','href':'/dokument/test/*'}]
    markup,warnings=sanitized_region(raw,observed['references'])
    assert 'documentBody' in markup and 'Test metadata' in markup
    assert 'javascript:' not in markup and '<script' not in markup
    assert html_observations(raw.replace(b'<div id="documentBody"></div>',b'<div id="documentBody">Actual text</div>'))['content_regions'][0]['text_characters']==11
