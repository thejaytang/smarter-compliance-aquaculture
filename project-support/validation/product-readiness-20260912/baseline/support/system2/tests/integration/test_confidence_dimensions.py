"""Engineering gate tests. Calibrations here are synthetic control inputs."""
from copy import deepcopy
import pytest
from pdf_extraction.verification.acceptance import assess,ASPECTS
from pdf_extraction.review.browser_view import browser_state
from .test_two_stage_workflow import system,current,decide


@pytest.mark.parametrize('stage',ASPECTS)
def test_one_high_dimension_cannot_hide_missing_others(stage):
    part={'aspect':ASPECTS[stage][0],'confidence':.999,'calibration_version':'seeded-test-only','evidence':['original']}
    result=assess([part],.95,stage=stage)
    assert result['status']=='pending' and result['confidence'] is None
    assert set('confidence_dimension_missing:'+a for a in ASPECTS[stage][1:])<=set(result['reasons'])


def test_duplicate_unknown_and_low_order_score_block_content():
    parts=[{'aspect':a,'confidence':.99,'calibration_version':'seeded-test-only','evidence':['original']} for a in ASPECTS['content']]
    assert assess(parts,.95,stage='content')['status']=='machine_accepted'
    parts[-1]['confidence']=.7
    assert assess(parts,.95,stage='content')['confidence']==.7
    assert assess(parts,.95,stage='content')['status']=='pending'
    parts[-1]['confidence']=.99
    for bad in (parts+[parts[0]],parts+[dict(parts[0],aspect='invented_dimension')]):
        assert assess(bad,.95,stage='content')['status']=='pending'


def test_missing_order_suspends_delivery_but_retains_human_history(system):
    store,did=system
    before=deepcopy(current(system))
    with store.transaction() as db:
        doc=store._load(db,did);u=doc['units'][1]
        u['content_parts']=[p for p in u['content_parts'] if p['aspect']!='order']
        store._recompute(db,doc,store.policy(db));store._save(db,doc)
    assert current(system)['published_count']==0
    detail=browser_state(store,'unit',did,'clause')
    order=next(x for x in detail['confidence_dimensions']['content'] if x['aspect']=='order')
    assert order['status']=='missing' and order['confidence'] is None
    assert current(system)['history']==before['history']
    assert current(system)['units'][1]['original']==before['units'][1]['original']
    decide(system,'accept_content')
    assert current(system)['units'][1]['content_status']=='human_accepted'
    assert current(system)['units'][1]['content_confidence'] is None
    assert next(x for x in browser_state(store,'unit',did,'clause')['confidence_dimensions']['content'] if x['aspect']=='order')['status']=='missing'


def test_missing_b_association_cannot_use_classification_score(system):
    store,did=system
    with store.transaction() as db:
        doc=store._load(db,did);u=doc['units'][1]
        u['requirement_parts']=[p for p in u['requirement_parts'] if p['aspect']!='association']
        store._recompute(db,doc,store.policy(db));store._save(db,doc)
    assert current(system)['published_count']==0
    u=current(system)['units'][1]
    assert u['content_status']=='machine_accepted' and u['requirement_status']=='pending'


@pytest.mark.parametrize('change',[
    {'calibration_version':None}, {'evidence':[]}, {'conflict':True}, {'confidence':float('nan')},
])
def test_unsupported_scores_remain_unknown_even_after_human_confirmation(change):
    parts=[{'aspect':a,'confidence':.99,'calibration_version':'seeded-test-only','evidence':['original']} for a in ASPECTS['content']]
    parts[0].update(change)
    result=assess(parts,.95,stage='content')
    assert result['status']=='pending' and result['confidence'] is None
    human=assess(parts,.95,stage='content',human=True)
    assert human['status']=='human_accepted' and human['confidence'] is None
    assert assess(parts,.95,stage='content',human=True,blockers=['critical_numeric_error'])['status']=='pending'


def test_reconciliation_refreshes_legacy_machine_acceptance_once(system):
    store,did=system
    before=deepcopy(current(system))
    with store.transaction() as db:
        doc=store._load(db,did)
        for u in doc['units']:
            u.pop('confidence_gate_version',None)
            u['content_parts']=[p for p in u['content_parts'] if p['aspect']!='order']
        # Preserve the earlier stored decision to simulate an upgrade, without
        # recomputing it through the new gate before the experiment.
        store._save(db,doc)
    assert len(store.feed()['current_requirements'])==1
    store.reconcile_sources({'PA001':before['source']})
    after=current(system)
    assert not store.feed()['current_requirements']
    assert after['history']==before['history']
    assert [u['original'] for u in after['units']]==[u['original'] for u in before['units']]
    events=store.feed()['events']
    assert len([e for e in events if e['kind']=='confidence_gate_updated'])==1
    store.reconcile_sources({'PA001':before['source']})
    assert store.feed()['events']==events


def test_gate_version_does_not_trigger_blanket_human_review(system):
    store,did=system
    for uid in ('coverage','clause'):
        decide(system,'accept_content',uid)
        decide(system,'classify',uid,classification='context' if uid=='coverage' else 'requirement',note='Isolated control: source coverage is context.')
    with store.transaction() as db:
        doc=store._load(db,did)
        for u in doc['units']:u.pop('confidence_gate_version',None)
        store._save(db,doc)
    before=current(system);events=store.feed()['events']
    store.reconcile_sources({'PA001':before['source']})
    assert current(system)==before and store.feed()['events']==events
