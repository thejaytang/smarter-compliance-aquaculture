from copy import deepcopy
import json
import pytest
from pdf_extraction.review.browser_view import browser_state
from .test_two_stage_workflow import system, current, decide


def test_browser_list_omits_evidence_but_unit_read_is_exact(system):
    store, identity = system
    with store.transaction() as db:
        doc = store._load(db, identity)
        doc['units'][1]['original']['structure'] = [{'large': 'x' * 1000000}]
        store._save(db, doc)
    before = deepcopy(current(system))
    view = browser_state(store)
    item = next(u for u in view['documents'][0]['units'] if u['id']=='clause')
    assert item['_summary'] and item['original']['structure'] == []
    assert len(json.dumps(view)) < 10000
    detail = browser_state(store, 'unit', identity, 'clause')
    assert detail['unit'] == before['units'][1]
    assert detail['revision'] == before['revision']
    assert current(system) == before


def test_summary_counts_history_and_unknown_units(system):
    store, identity = system
    decide(system, 'draft', draft={'note':'unfinished'})
    view = browser_state(store, 'summary')
    assert not view['documents'][0]['units']
    assert view['documents'][0]['unit_count'] == 2
    assert view['pending'] == store.snapshot()['pending']
    assert view['published'] == store.snapshot()['published']
    assert browser_state(store, 'history')['documents'][0]['history'] == current(system)['history']
    with pytest.raises(ValueError, match='unit_not_found'):
        browser_state(store, 'unit', identity, 'missing')


def test_unit_read_exposes_latest_revision_and_corrected_text(system):
    store, identity = system
    old = browser_state(store)['documents'][0]['revision']
    decide(system, 'correct', fields={'body':'Corrected source text.'}, note='Source check')
    detail = browser_state(store, 'unit', identity, 'clause')
    assert detail['revision'] > old
    assert detail['unit']['edits']['body'] == 'Corrected source text.'
    listed = browser_state(store)['documents'][0]['units'][1]
    assert listed['original']['fields']['body'] == 'Corrected source text.'
