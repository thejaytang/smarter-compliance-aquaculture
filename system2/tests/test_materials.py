from copy import deepcopy
import sqlite3
import uuid

import pytest

from pdf_extraction.review.materials import MaterialStore, validate_blocks
from pdf_extraction.review.material_processor import capability, input_envelope, process, validate_output


def req(material, **kwargs):
    return dict(request_id=str(uuid.uuid4()), actor='Isolated Reviewer', material_id=material['id'], expected_revision=material['revision'], **kwargs)


def source(snapshot='one', source_id='fixture'):
    return dict(source_id=source_id, snapshot_id=snapshot, content_hash=snapshot + '-hash', file_format='pdf')


def scope():
    return [{'id': 'page:1', 'kind': 'page', 'label': 'Page 1', 'location': {'page': 1}},
            {'id': 'page:2', 'kind': 'page', 'label': 'Empty page 2', 'location': {'page': 2}}]


def text(value='Human original', identity='b1'):
    return {'id': identity, 'type': 'text', 'text': value, 'source_refs': [{'scope_id': 'page:1', 'page': 1}]}


@pytest.fixture
def setup(tmp_path):
    store = MaterialStore(tmp_path)
    return store, store.open(source(), 'Isolated test material', scope())


def test_durable_save_reopen_and_material_isolation(setup):
    store, material = setup
    other = store.open(source(source_id='another'), 'Other', scope())
    save = req(material, blocks=[text()])
    saved = store.save(save)
    assert saved == store.save(save)
    reopened = MaterialStore(store.root).read(material['id'])
    assert reopened['blocks'] == [text()]
    assert reopened['content_status'] == 'draft'
    assert reopened['confirmation'] is None
    assert store.read(other['id'])['blocks'] == []
    assert len(store.history(material['id'])) == 2
    with pytest.raises(ValueError, match='reused'):
        store.save(dict(save, blocks=[text('Other')]))


def test_concurrent_save_preserves_rejected_draft_and_receipt(setup):
    store, material = setup
    first = store.save(req(material, blocks=[text('First')]))['material']
    request = req(material, blocks=[text('Second unsaved draft')])
    conflict = store.save(request)
    assert conflict['status'] == 'conflict'
    assert MaterialStore(store.root).save(request) == conflict
    latest = store.read(material['id'])
    assert latest['blocks'] == first['blocks']
    assert latest['conflicts'][0]['request']['blocks'][0]['text'] == 'Second unsaved draft'
    assert len(store.history(material['id'])) == 2


def test_confirmation_requires_all_original_ranges_and_human(setup):
    store, material = setup
    material = store.save(req(material, blocks=[text()], association_reviewed=True))['material']
    with pytest.raises(ValueError, match='all_original_ranges'):
        store.confirm(req(material, explicit_confirmation=True, checked_scope=['page:1']))
    with pytest.raises(ValueError, match='explicit_human'):
        store.confirm(req(material, checked_scope=['page:1', 'page:2']))
    with pytest.raises(ValueError, match='named_operator'):
        store.confirm(dict(req(material), actor='machine'))
    result = store.confirm(req(material, explicit_confirmation=True, checked_scope=['page:1', 'page:2']))['material']
    assert result['content_status'] == 'content_review_complete'
    assert result['requirement_status'] == 'not_connected'
    assert result['confirmation']['actor'] == 'Isolated Reviewer'
    assert store.read(material['id'])['candidates'] == []


def test_unresolved_issue_and_association_review_guards(setup):
    store, material = setup
    material = store.save(req(material, blocks=[text()], issues=[{'id': 'missing', 'message': 'Missing figure', 'resolved': False}]))['material']
    with pytest.raises(ValueError, match='unresolved_content'):
        store.confirm(req(material, explicit_confirmation=True, checked_scope=['page:1', 'page:2']))
    material = store.save(req(material, issues=[{'id': 'missing', 'message': 'Transcribed and checked figure', 'resolved': True}]))['material']
    with pytest.raises(ValueError, match='associations'):
        store.confirm(req(material, explicit_confirmation=True, checked_scope=['page:1', 'page:2']))


def test_extract_never_replaces_human_content_or_confirmation(setup):
    store, material = setup
    material = store.save(req(material, blocks=[text()], association_reviewed=True))['material']
    material = store.confirm(req(material, explicit_confirmation=True, checked_scope=['page:1', 'page:2']))['material']
    request = req(material)
    start = store.start_candidate(request)
    assert start == store.start_candidate(request)
    assert len(store.read(material['id'])['candidates']) == 1
    result = store.finish_candidate(material['id'], start['candidate']['id'], [text('Parser alternative')])
    assert result['material']['blocks'] == material['blocks']
    assert result['material']['confirmation'] == material['confirmation']
    assert store.finish_candidate(material['id'], start['candidate']['id'], [text('Parser alternative')])['status'] == 'replayed'
    with pytest.raises(ValueError, match='already_final'):
        store.finish_candidate(material['id'], start['candidate']['id'], [text('Different retry')])
    with pytest.raises(ValueError, match='reconciliation'):
        store.confirm(req(result['material'], explicit_confirmation=True, checked_scope=['page:1', 'page:2']))
    adopted = store.reconcile(req(result['material'], candidate_id=start['candidate']['id'], action='adopt', reviewed_against_source=True))['material']
    assert adopted['blocks'][0]['text'] == 'Parser alternative'
    assert adopted['confirmation'] is None
    assert any(v['confirmation'] == material['confirmation'] for v in store.history(material['id']))


def test_stale_processing_result_can_be_kept_but_not_adopted(setup):
    store, material = setup
    start = store.start_candidate(req(material))
    edited = store.save(req(start['material'], blocks=[text('Concurrent human correction')]))['material']
    result = store.finish_candidate(material['id'], start['candidate']['id'], [text('Old input result')])
    assert result['candidate']['stale'] is True
    assert result['material']['blocks'] == edited['blocks']
    with pytest.raises(ValueError, match='stale_or_partial'):
        store.reconcile(req(result['material'], candidate_id=start['candidate']['id'], action='adopt', reviewed_against_source=True))
    kept = store.reconcile(req(result['material'], candidate_id=start['candidate']['id'], action='keep', reviewed_against_source=True))['material']
    assert kept['blocks'] == edited['blocks']
    assert kept['candidates'][0]['adoption']['stale_input']


def test_partial_failure_restart_and_cross_material_binding(setup):
    store, material = setup
    start = store.start_candidate(req(material))
    other = store.open(source(source_id='other'), 'Other', scope())
    with pytest.raises(ValueError, match='candidate_not_found'):
        store.finish_candidate(other['id'], start['candidate']['id'], [])
    restarted = MaterialStore(store.root)
    assert restarted.read(material['id'])['candidates'][0]['status'] == 'running'
    result = restarted.finish_candidate(material['id'], start['candidate']['id'], [text()], complete=False)
    assert result['candidate']['status'] == 'partial'
    assert result['material']['blocks'] == []
    with pytest.raises(ValueError, match='stale_or_partial'):
        store.reconcile(req(result['material'], candidate_id=start['candidate']['id'], action='adopt', reviewed_against_source=True))


def test_source_revision_preserves_human_versions_and_legacy_store(setup):
    store, material = setup
    with sqlite3.connect(store.database) as db:
        db.execute('CREATE TABLE legacy_history(data TEXT)')
        db.execute("INSERT INTO legacy_history VALUES('original human decision')")
    material = store.save(req(material, blocks=[text()]))['material']
    new = store.open(source('two'), 'Replacement snapshot', scope())
    old = store.read(material['id'])
    assert old['source_stale']
    assert old['blocks'] == material['blocks']
    assert new['blocks'] == []
    assert new['related_versions'][0]['id'] == old['id']
    with sqlite3.connect(store.database) as db:
        assert db.execute('SELECT data FROM legacy_history').fetchone()[0] == 'original human decision'


def test_editor_structure_table_image_and_dependency_checks():
    heading = dict(text('Heading', 'h'), type='heading', level=1)
    paragraph = dict(text(), parent_id='h', dependencies=['h'])
    table = dict(text('', 'table'), type='table', table={'rows': [['A', ''], ['B', 'C']], 'merges': [{'row': 0, 'col': 0, 'rowspan': 1, 'colspan': 2}], 'notes': ['Source note']})
    image = dict(text('Original figure', 'image'), type='image', image={'source_ref': {'scope_id': 'page:1', 'bbox': [0, 0, 50, 50]}})
    validate_blocks([heading, paragraph, table, image], scope())
    invalid = deepcopy(table)
    invalid['table']['merges'][0]['colspan'] = 3
    with pytest.raises(ValueError, match='merge_out_of_bounds'):
        validate_blocks([invalid], scope())
    with pytest.raises(ValueError, match='preceding_heading'):
        validate_blocks([paragraph, heading], scope())
    with pytest.raises(ValueError, match='cycle'):
        validate_blocks([dict(text(identity='a'), dependencies=['b']), dict(text(identity='b'), dependencies=['a'])], scope())
    with pytest.raises(ValueError, match='outside_material'):
        validate_blocks([dict(text(), source_refs=[{'scope_id': 'another-material'}])], scope())


def test_future_contract_unavailable_and_confirmed_input_boundary(setup):
    store, material = setup
    assert capability()['connected'] is False
    with pytest.raises(ValueError, match='confirmed_current'):
        input_envelope(material, request_id='fixture')
    material = store.save(req(material, blocks=[text()], association_reviewed=True))['material']
    material = store.confirm(req(material, explicit_confirmation=True, checked_scope=['page:1', 'page:2']))['material']
    envelope = input_envelope(material, request_id='fixture')
    result = validate_output(envelope, process(envelope))
    assert result['state'] == 'unavailable'
    assert result['candidate_payload'] is None
    assert result['input_revision'] == material['content_revision']
    with pytest.raises(ValueError, match='identity_mismatch'):
        validate_output(envelope, dict(result, input_revision=999))
    with pytest.raises(ValueError, match='cannot_confirm'):
        validate_output(envelope, dict(result, human_confirmed=True))


def test_metadata_only_source_observation_and_historical_read(setup):
    store, material = setup
    saved = store.save(req(material, blocks=[text()]))['material']
    assert store.mark_source_version('fixture', None, None) == [material['id']]
    assert store.mark_source_version('fixture', None, None) == []
    assert store.read(material['id'])['source_stale']
    historical = store.read(material['id'], revision=saved['revision'])
    assert historical['blocks'] == saved['blocks']
    assert historical['source_stale'] is False
    assert historical['historical'] is True


def test_process_rejection_and_legacy_import_are_explicit(setup):
    store, material = setup
    request = req(material)
    result = store.process(request)
    assert result['status'] == 'unavailable'
    assert store.process(request) == result
    assert store.read(material['id'])['revision'] == 0
    imported = store.import_candidate(req(material), [text('Legacy human correction')], {'document_id': 'old', 'revision': 12})
    assert imported['material']['blocks'] == []
    assert imported['material']['confirmation'] is None
    adopted = store.reconcile(req(imported['material'], candidate_id=imported['candidate']['id'], action='adopt', reviewed_against_source=True))['material']
    assert adopted['blocks'][0]['text'] == 'Legacy human correction'
    assert adopted['confirmation'] is None
    assert adopted['content_status'] == 'draft'


def test_failed_candidate_and_pending_resume(setup):
    store, material = setup
    start = store.start_candidate(req(material))
    assert MaterialStore(store.root).pending_candidates()[0]['id'] == start['candidate']['id']
    other = store.start_candidate(req(start['material']))
    assert other['status'] == 'already_running'
    result = store.finish_candidate(material['id'], start['candidate']['id'], [], error='Isolated parser failure', metadata={'canonical_artifacts': []})
    assert result['candidate']['status'] == 'failed'
    assert result['material']['blocks'] == []
    assert store.pending_candidates() == []
    assert len(store.read(material['id'])['candidates']) == 1


def test_simultaneous_writers_only_one_applies_and_other_draft_survives(setup):
    from concurrent.futures import ThreadPoolExecutor
    store, material = setup
    requests = [req(material, blocks=[text(label)]) for label in ('A', 'B')]
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda request: MaterialStore(store.root).save(request), requests))
    assert sorted(r['status'] for r in results) == ['applied', 'conflict']
    latest = store.read(material['id'])
    assert latest['revision'] == 1
    assert len(latest['conflicts']) == 1
    assert {latest['blocks'][0]['text'], latest['conflicts'][0]['request']['blocks'][0]['text']} == {'A', 'B'}


def test_changed_save_invalidates_affected_scope_not_empty_unaffected_page(setup):
    store, material = setup
    saved = store.save(req(material, blocks=[text()], checked_scope=['page:1', 'page:2']))['material']
    assert saved['checked_scope'] == []
    saved = store.save(req(saved, checked_scope=['page:1', 'page:2']))['material']
    assert len(saved['checked_scope']) == 2
    changed = store.save(req(saved, blocks=[text('Changed')], checked_scope=['page:1', 'page:2']))['material']
    assert changed['checked_scope'] == ['page:2']
    assert changed['review_checks']['page:2'] == saved['review_checks']['page:2']
    assert changed['confirmation'] is None


def test_first_candidate_is_editable_personal_draft_without_review(setup):
    store, m = setup
    started=store.start_candidate(req(m))
    candidate=started['candidate']
    store.finish_candidate(m['id'],candidate['id'],[text('Machine original')])
    m=store.read(m['id'])
    request=req(m,candidate_id=candidate['id'],blocks=[text('Human correction')])
    result=store.save_candidate_draft(request)
    assert result['status']=='applied'
    assert store.save_candidate_draft(request)==result
    saved=store.read(m['id'])
    assert saved['blocks'][0]['text']=='Human correction'
    assert saved['confirmation'] is None
    assert saved['checked_scope']==[]
    assert saved['candidates'][0]['resolution']['reviewed_against_source'] is False
    versions=store.history(m['id'])
    assert any(v['blocks'] and v['blocks'][0]['text']=='Machine original' for v in versions)
    assert saved['content_status']!='content_review_complete'
