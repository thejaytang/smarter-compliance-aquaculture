"""Offline collaboration tests use isolated stores and registered test originals only."""
from copy import deepcopy
from hashlib import sha256
from types import SimpleNamespace
import uuid

import pytest

from pdf_extraction.orchestration.material_collaboration import command, normalized, retained_checks
from pdf_extraction.orchestration.material_service import MaterialService
from .test_material_service import integration, request, register


def block(value='Reviewed original'):
    return dict(id='b1', type='text', text=value, source_refs=[{'scope_id': 'html:document'}])


def exported(integration):
    service, _ = integration
    material = service.open(request(source_id='TS001'))
    service.mutate('save', request(material, blocks=[block()], association_reviewed=True))
    return command(service, 'export', {'material_id': material['id']})


def adopt(material, **extra):
    return request(material, actor='Weijie Tang', expected_source_hash=material['source']['content_hash'],
        blocks=material['blocks'], issues=material['issues'], submission_id=str(uuid.uuid4()),
        contributors=['Ana Jokic'], base_digest='isolated-baseline', **extra)


def clone(service, tmp_path):
    return MaterialService(tmp_path/'reviewer', service.system1)


def test_export_normalizes_head_history_and_preserves_candidate_evidence(integration):
    service, _ = integration
    data = exported(integration)
    service.mutate('extract', request(data['material']))
    data = command(service, 'export', {'material_id': data['material']['id']})
    assert not ({'candidates', 'conflicts', 'related_versions'} & data['material'].keys())
    assert data['history'][-1] == data['material']
    assert data['candidate_evidence'][0]['status'] == 'running'
    assert command(service, 'validate', data)['status'] == 'valid'


def test_seed_roundtrip_preserves_all_history_and_does_not_start_candidates(integration, tmp_path):
    service, _ = integration;data = exported(integration)
    service.mutate('extract', request(data['material']))
    data = command(service, 'export', {'material_id': data['material']['id']})
    reviewer = clone(service, tmp_path)
    seed = dict(data, original_path=data['original']['path'])
    command(reviewer, 'seed', seed)
    result = command(reviewer, 'export', {'material_id': data['material']['id']})
    assert result['material'] == data['material']
    assert result['history'] == data['history']
    assert reviewer.store.pending_candidates() == []
    assert result['candidate_evidence'] == data['candidate_evidence']
    command(reviewer, 'seed', seed)  # Exact replay is harmless.
    changed = reviewer.store.save(request(result['material'], blocks=[block('Personal correction')]))['material']
    with pytest.raises(ValueError, match='overwrite'): command(reviewer, 'seed', seed)
    assert reviewer.store.read(changed['id'])['blocks'] == changed['blocks']


@pytest.mark.parametrize('damage', ['cross_source', 'duplicate', 'missing', 'wrong_head', 'different_scope', 'bad_block', 'bad_stamp'])
def test_validate_rejects_entire_bad_history_without_writing(integration, tmp_path, damage):
    service, _ = integration;data = exported(integration)
    bad = deepcopy(data)
    if damage == 'cross_source': bad['history'][0]['source']['source_id'] = 'TS002'
    if damage == 'duplicate': bad['history'].append(deepcopy(bad['history'][0]))
    if damage == 'missing': bad['history'] = bad['history'][1:]
    if damage == 'wrong_head': bad['material']['title'] = 'Mismatch'
    if damage == 'different_scope': bad['history'][0]['scope'][0]['label'] = 'Different scope'
    if damage == 'bad_block': bad['history'][0]['blocks'] = [dict(block(), source_refs=[{'scope_id': 'foreign'}])]
    if damage == 'bad_stamp': bad['history'][0]['review_checks'] = {'html:document': {'actor': 'machine'}}
    reviewer = clone(service, tmp_path)
    with pytest.raises(ValueError): command(reviewer, 'validate', bad)
    with pytest.raises(ValueError): command(reviewer, 'seed', dict(bad, original_path=data['original']['path']))
    assert reviewer.store.list() == []
    assert not (reviewer.root/'material-originals').exists()


def test_seed_checks_real_original_scope_and_never_replaces_corrupt_existing_original(integration, tmp_path):
    service, _ = integration;data = exported(integration);reviewer = clone(service, tmp_path)
    bad = deepcopy(data)
    for doc in [bad['material'], *bad['history']]:
        doc['scope'].append({'id': 'fake', 'kind': 'html', 'label': 'Invented empty range', 'location': {}})
    with pytest.raises(ValueError, match='complete original'): command(reviewer, 'seed', dict(bad, original_path=data['original']['path']))
    assert reviewer.store.list() == []
    target = reviewer._path(data['material']['source']);target.parent.mkdir(exist_ok=True)
    target.write_bytes(b'Existing damaged evidence')
    with pytest.raises(ValueError, match='corrupt'): command(reviewer, 'seed', dict(data, original_path=data['original']['path']))
    assert target.read_bytes() == b'Existing damaged evidence'


def test_adoption_replay_is_durable_after_changed_source_and_conflict_is_preserved(integration):
    service, handoff = integration;data = exported(integration)
    req = adopt(data['material']);req['blocks'] = [block('Coordinator adopted correction')]
    result = command(service, 'adopt-master', req)
    assert result['status'] == 'applied' and result['material']['confirmation'] is None
    handoff.records = [register(handoff.source_root, b'<html>New source</html>', 2)]
    assert command(service, 'adopt-master', req) == result
    with pytest.raises(ValueError, match='reused'):
        command(service, 'adopt-master', dict(req, blocks=[block('Changed same UUID')]))
    conflict = command(service, 'adopt-master', adopt(data['material']))
    assert conflict['status'] == 'conflict'
    assert service.store.read(data['material']['id'])['blocks'] == req['blocks']


def test_adoption_checks_source_binding_and_handoff_again_before_commit(integration, monkeypatch):
    service, handoff = integration;data = exported(integration);before = service.store.history(data['material']['id'])
    wrong = adopt(data['material']);wrong['expected_source_hash'] = 'a' * 64
    with pytest.raises(ValueError, match='Source version'): command(service, 'adopt-master', wrong)
    count = 0
    def change_during_edit():
        nonlocal count
        count += 1
        if count == 2: raise ValueError('system1_changed_during_handoff')
    monkeypatch.setattr(handoff, 'assert_current', change_during_edit)
    with pytest.raises(ValueError, match='changed_during'): command(service, 'adopt-master', adopt(data['material']))
    assert service.store.history(data['material']['id']) == before
    assert count == 2


def test_adoption_rejects_corrupt_pinned_original_and_cross_material_review(integration):
    service, _ = integration;data = exported(integration)
    foreign = deepcopy(data['material']);foreign['scope'][0]['label'] = 'Another original range'
    with pytest.raises(ValueError, match='different material'): command(service, 'adopt-master', adopt(data['material'], review_origins=[foreign]))
    service._path(data['material']['source']).write_bytes(b'Changed pinned bytes')
    with pytest.raises(ValueError, match='integrity'): command(service, 'adopt-master', adopt(data['material']))


def test_retained_checks_keep_original_reviewer_and_scope_but_never_global_confirmation(integration, tmp_path):
    service, _ = integration;data = exported(integration);reviewer = clone(service, tmp_path)
    command(reviewer, 'seed', dict(data, original_path=data['original']['path']))
    material = data['material']
    for n in range(3):
        material = reviewer.store.save(request(material, blocks=[block('Personal '+str(n))]))['material']
    material = reviewer.store.confirm(request(material, actor='Ana Jokic', explicit_confirmation=True,
        checked_scope=['html:document'], association_reviewed=True))['material']
    req = adopt(data['material'], review_origins=[material]);req['blocks'] = material['blocks']
    result = command(service, 'adopt-master', req)['material']
    assert result['checked_scope'] == ['html:document']
    assert result['review_checks']['html:document']['actor'] == 'Ana Jokic'
    assert result['review_checks']['html:document']['content_revision'] == material['content_revision']
    assert result['review_checks']['html:document']['inherited_from']['revision'] == material['revision']
    assert result['confirmation'] is None and result['content_status'] != 'content_review_complete'
    command(service, 'export', {'material_id': result['id']})  # Inherited branch revision is not relabelled as a master revision.
    foreign = deepcopy(material);foreign['scope'][0]['label'] = 'Foreign range'
    assert retained_checks([foreign], material['blocks'], material['issues'], result) == {}


def test_repeat_resolution_only_reuses_same_current_input_and_adds_auditable_history(integration):
    service, _ = integration;data = exported(integration);material = data['material']
    started = service.store.start_candidate(request(material))
    finished = service.store.finish_candidate(material['id'], started['candidate']['id'], [block('Machine proposal')])
    material = service.store.reconcile(request(finished['material'], actor='Ana Jokic', candidate_id=started['candidate']['id'],
        action='keep', reviewed_against_source=True))['material']
    second = service.store.start_candidate(request(material))
    service.store.finish_candidate(material['id'], second['candidate']['id'], [block('Machine proposal')])
    before = service.store.read(material['id']);history = service.store.history(material['id'])
    result = command(service, 'repeat-resolution', {})
    assert result['reused_resolution_candidates'] == [second['candidate']['id']]
    after = service.store.read(material['id'])
    assert after['blocks'] == before['blocks'] and after['content_revision'] == before['content_revision']
    assert len(service.store.history(material['id'])) == len(history)+1
    assert after['last_action']['actor'] == 'system_reuse'
    assert after['collaboration_resolution_reuse'][-1]['adoption']['actor'] == 'Ana Jokic'
    assert command(service, 'repeat-resolution', {})['reused_resolution_candidates'] == []
    assert service.store.read(material['id'])['revision'] == after['revision']
    third = service.store.start_candidate(request(after))
    service.store.finish_candidate(material['id'], third['candidate']['id'], [block('Machine proposal')])
    latest = service.store.read(material['id'])
    service.store.save(request(latest, blocks=[block('New human content')]))
    assert command(service, 'repeat-resolution', {})['reused_resolution_candidates'] == []


def test_imported_candidate_evidence_is_read_only_but_prior_decision_can_be_reused(integration, tmp_path):
    service, _ = integration;data = exported(integration)
    started = service.store.start_candidate(request(data['material']))
    finished = service.store.finish_candidate(data['material']['id'], started['candidate']['id'], [block('Same proposal')])
    service.store.reconcile(request(finished['material'], actor='Ana Jokic', candidate_id=started['candidate']['id'],
        action='keep', reviewed_against_source=True))
    data = command(service, 'export', {'material_id': data['material']['id']})
    reviewer = clone(service, tmp_path)
    command(reviewer, 'seed', dict(data, original_path=data['original']['path']))
    assert reviewer.store.read(data['material']['id'])['candidates'] == []
    assert reviewer.store.pending_candidates() == []
    started = reviewer.store.start_candidate(request(data['material']))
    reviewer.store.finish_candidate(data['material']['id'], started['candidate']['id'], [block('Same proposal')])
    result = command(reviewer, 'repeat-resolution', {})
    assert result['reused_resolution_candidates'] == [started['candidate']['id']]
    result = command(reviewer, 'export', {'material_id': data['material']['id']})
    assert len(result['candidate_evidence']) == 2
    assert data['candidate_evidence'][0] in result['candidate_evidence']


def test_candidate_evidence_from_other_material_rejected_before_seed(integration, tmp_path):
    service, _ = integration;data = exported(integration)
    service.store.start_candidate(request(data['material']))
    data = command(service, 'export', {'material_id': data['material']['id']})
    data['candidate_evidence'][0]['material_id'] = 'other'
    reviewer = clone(service, tmp_path)
    with pytest.raises(ValueError, match='different material'): command(reviewer, 'validate', data)
    with pytest.raises(ValueError, match='different material'):
        command(reviewer, 'seed', dict(data, original_path=data['original']['path']))
    assert reviewer.store.list() == []
    assert not (reviewer.root/'material-originals').exists()
