"""A persisted score may not validate a different classification method."""
from copy import deepcopy
from .test_two_stage_workflow import unit, current, system


def test_previous_method_scores_do_not_release_current_proposal(system):
    store,identity=system
    with store.transaction() as db:
        doc=store._load(db,identity)
        for p in doc['units'][1]['requirement_parts']:
            p.update(method='literal-requirements/3',proposal_sha256='b'*64)
        store._recompute(db,doc,store.policy(db));store._save(db,doc)
    result=current(system)
    assert result['units'][1]['requirement_status']=='pending'
    assert not result['published']


def test_missing_binding_is_unmeasured_and_recorded_scores_are_retained(system):
    store,identity=system
    with store.transaction() as db:
        doc=store._load(db,identity)
        raw=doc['units'][1]['requirement_parts']
        for p in raw:p.pop('rule_binding')
        before=deepcopy(raw)
        store._recompute(db,doc,store.policy(db));store._save(db,doc)
    result=current(system)
    assert result['units'][1]['requirement_parts']==before
    assert result['units'][1]['requirement_confidence'] is None
    assert 'classification_score_binding_stale' in result['units'][1]['requirement_reasons']
    assert not result['published']


def test_method_upgrade_reconciles_once_and_retracts_machine_delivery(system,monkeypatch):
    from pdf_extraction.domains.requirements import classification
    store,identity=system
    before=current(system)
    raw=deepcopy(before['units'][1]['requirement_parts'])
    assert len(before['published'])==1
    monkeypatch.setattr(classification,'VERSION','synthetic-next-method')
    source=before['source']
    current_sources={source['source_id']:dict(source,effective_selection='INCLUDE')}
    store.reconcile_sources(current_sources)
    after=current(system)
    assert not after['published']
    assert after['units'][1]['requirement_parts']==raw
    assert after['units'][1]['requirement_confidence'] is None
    assert after['history']==before['history']
    events=store.feed()['events']
    assert sum(e['kind']=='classification_score_method_updated' for e in events)==1
    cursor=store.feed()['cursor']
    store.reconcile_sources(current_sources)
    assert store.feed(cursor)['events']==[]


def test_method_upgrade_preserves_named_human_decision(system,monkeypatch):
    from .test_two_stage_workflow import decide
    from pdf_extraction.domains.requirements import classification
    store,identity=system
    decide(system,'classify','coverage',classification='context',note='Engineering fixture: coverage judgment')
    decide(system,'classify',classification='requirement',note='Engineering fixture: explicit human judgment')
    before=current(system);source=before['source']
    monkeypatch.setattr(classification,'VERSION','synthetic-next-method')
    store.reconcile_sources({source['source_id']:dict(source,effective_selection='INCLUDE')})
    after=current(system)
    assert after['units'][1]['requirement_status']=='human_accepted'
    assert after['units'][1]['classification']=='requirement'
    assert after['units'][1]['requirement_confidence'] is None
    assert after['history']==before['history']
    assert len(after['published'])==1


def test_validated_rule_activation_binds_the_current_proposal(tmp_path):
    from types import SimpleNamespace
    import json
    from pdf_extraction.contracts.hashing import digest
    from pdf_extraction.domains.requirements.classification import propose,VERSION
    from pdf_extraction.verification.calibration import calibrate,apply_calibrated_rules
    from pdf_extraction.verification.requirement_scores import applicable_parts
    u=unit('clause');source=SimpleNamespace(content_hash='a'*64,file_format='html')
    proposal=propose(dict(u['original'],kind=u['kind']))
    scope=dict(format='html',language='en',stage='requirement',aspect='classification')
    # Synthetic calibration metadata exercises serialization/binding only.
    labels=[dict(id=str(i),split='calibration',label_origin='independent_human',score=.99,correct=True) for i in range(100)]
    a=calibrate(labels,method=VERSION,scope=scope,prediction_hash='b'*64)
    (tmp_path/'test-calibration.json').write_text(json.dumps(a))
    rule=dict(source_sha256=source.content_hash,original_sha256=digest(u['original']),unit_id=u['id'],stage='requirement',aspect='classification',calibration_path='test-calibration.json',method=VERSION,proposal_sha256=digest(proposal),score=.99)
    (tmp_path/'scoring-rules.local.json').write_text(json.dumps(dict(source_languages={source.content_hash:'en'},rules=[rule])))
    apply_calibrated_rules([u],source,tmp_path)
    p=next(p for p in applicable_parts(u,proposal) if p['aspect']=='classification')
    assert p['confidence'] is not None
    assert p['rule_binding']['proposal_sha256']==digest(proposal)
    assert all(p['confidence'] is None for p in u['requirement_parts'] if p['aspect']!='classification')
