"""Engineering cases, not independent source-quality labels."""
from copy import deepcopy
import pytest
from pdf_extraction.review.workflow import Workflow
from pdf_extraction.review.requirement_subdivision import SCHEMA
from .test_two_stage_workflow import system, current, decide, request, threshold
from .test_requirement_workbook import export


def subdivide(system, **changes):
    body = current(system)['units'][1]['original']['fields']['body']
    cut = body.index('shall')
    payload = dict(subdivision_schema=SCHEMA, count_basis='subitems', complete_range_reviewed=True,
        note='Engineering span/link test; not a reference judgment.', remainder_reason='Shared parent context retained.',
        subitems=[dict(field='body',start=0,end=cut,text=body[:cut]),
                  dict(field='body',start=cut,end=len(body),text=body[cut:])])
    payload.update(changes)
    return decide(system, 'subdivide_requirement', **payload)


def test_parent_retained_children_counted_once_and_reversible(system, tmp_path):
    old = deepcopy(current(system)['units'][1])
    subdivide(system)
    doc = current(system)
    parent = doc['units'][1]
    assert parent['original'] == old['original'] and parent['version'] == old['version']
    assert len(doc['units']) == 2 and not parent.get('superseded_by')
    assert doc['published_count'] == system[0].snapshot()['published'] == 2
    feed = system[0].feed()
    assert len(feed['current_requirements']) == 2 and len(feed['requirement_parents']) == 1
    assert all(c['original_number'] is None and c['parent_original_number'] == 'clause' for c in feed['current_requirements'])
    assert all(c['parent_context']['fields'] == old['original']['fields'] for c in feed['current_requirements'])
    _, book, _ = export(system, tmp_path)
    rows = list(book.worksheets[1].iter_rows(min_row=11, values_only=True))
    assert sum(r[35] for r in rows) == 2
    assert len([r for r in rows if r[5] == 'Available']) == 2
    assert all(r[0] is None for r in rows if r[33])
    assert any(r[1] == old['original']['fields']['body'] for r in rows)
    book.close()
    subdivide(system, count_basis='parent')
    assert current(system)['published_count'] == 1
    assert len(system[0].feed()['current_requirements']) == 1
    assert current(system)['units'][1]['requirement_subdivision']['revision'] == 2
    decide(system, 'clear_subdivision', classification='requirement', note='Return to complete parent counting.')
    assert current(system)['published_count'] == 1
    assert not current(system)['units'][1].get('requirement_subdivision')
    assert current(system)['history'][-1]['subdivision_before']['revision'] == 2
    subdivide(system)
    assert current(system)['units'][1]['requirement_subdivision']['revision'] == 3
    assert Workflow(system[0].root).snapshot() == system[0].snapshot()


def test_a_change_suspends_subitems_after_content_acceptance_until_new_b_review(system):
    subdivide(system)
    prior = deepcopy(current(system)['units'][1]['requirement_subdivision'])
    decide(system, 'correct', fields={'notes':'This condition applies to all subitems.'}, note='Seeded context change.')
    decide(system, 'accept_content')
    u = current(system)['units'][1]
    assert not current(system)['published'] and u['requirement_status'] == 'pending'
    assert 'requirement_subdivision_stale' in u['requirement_reasons']
    assert u['requirement_subdivision'] == prior
    with pytest.raises(ValueError, match='explicitly_replace'):
        decide(system, 'classify', classification='requirement')
    subdivide(system)
    assert current(system)['published_count'] == 2


def test_requirement_draft_keeps_a_accepted_but_suspends_b_until_submit(system):
    decide(system, 'accept_content')
    decide(system, 'classify', classification='requirement')
    decide(system, 'draft', draft={'stage':'requirement','note':'Unfinished B change'})
    u = current(system)['units'][1]
    assert u['content_status'] == 'human_accepted' and u['requirement_status'] == 'pending'
    assert not current(system)['published']
    subdivide(system)
    assert current(system)['published_count'] == 2


def test_content_draft_blocks_even_prior_human_acceptance(system):
    decide(system, 'accept_content')
    decide(system, 'classify', classification='requirement')
    decide(system, 'draft', draft={'stage':'content','note':'Unfinished A correction'})
    assert current(system)['units'][1]['content_status'] == 'pending'
    assert not current(system)['published']


@pytest.mark.parametrize('changes,error', [
    ({'count_basis':'both'}, 'choose_provisional'),
    ({'subdivision_schema':'future'}, 'policy_version_changed'),
    ({'complete_range_reviewed':False}, 'complete_parent_review'),
    ({'subitems':[dict(field='body',start=0,end=4,text='fake')]*2}, 'match_accepted'),
    ({'subitems':[dict(field='body',start=0,end=4,text='Fish')]*2}, 'overlap'),
    ({'subitems':[dict(field='body',start=0,end=4,text='Fish'),dict(field='body',start=5,end=10,text='farms')], 'remainder_reason':''}, 'unassigned'),
])
def test_invalid_subdivision_is_atomic(system, changes, error):
    before = system[0].snapshot()
    with pytest.raises(ValueError, match=error): subdivide(system, **changes)
    assert system[0].snapshot() == before


def test_a_and_dependency_gate_still_required(system):
    threshold(system, 1, 1)
    with pytest.raises(ValueError, match='content_gate'): subdivide(system)
    decide(system, 'accept_content')
    with pytest.raises(ValueError, match='content_gate'): subdivide(system)
    decide(system, 'accept_content', 'coverage')
    subdivide(system)
    assert current(system)['published_count'] == 2


def test_guarded_subdivision_replay_and_stale_span_request(system):
    from .test_review_rows import guarded
    r=guarded(system,'clause',action='subdivide_requirement',subdivision_schema=SCHEMA,count_basis='parent',
        complete_range_reviewed=True,note='Isolated replay test',remainder_reason='Shared wording',
        subitems=[dict(field='body',start=0,end=4,text='Fish'),dict(field='body',start=5,end=10,text='farms')])
    receipt=system[0].decision(r)
    assert system[0].decision(r)==receipt and current(system)['published_count']==1
    stale=dict(r,request_id=request()['request_id'])
    with pytest.raises(ValueError,match='stale_unit_or_dependency'):system[0].decision(stale)


def test_source_number_requires_actual_complete_prefix_and_unicode_offsets(system):
    text='🐟 1.2 Keep records. 2.4 Avoid pollution.'
    decide(system,'correct',fields={'body':text},note='Synthetic Unicode/source-number binding case')
    decide(system,'accept_content')
    first=text.index('1.2');second=text.index('2.4')
    parts=[dict(field='body',start=first,end=second-1,text=text[first:second-1],original_number='1.2'),
           dict(field='body',start=second,end=len(text),text=text[second:],original_number='2.4')]
    subdivide(system,subitems=parts)
    rows=system[0].feed()['current_requirements']
    assert [r['original_number'] for r in rows]==['1.2','2.4']
    assert rows[0]['original_number_span']['start']==2
    for value in ['9.9','1']:
        bad=deepcopy(parts);bad[0]['original_number']=value
        with pytest.raises(ValueError,match='original_number'):subdivide(system,subitems=bad)


def test_whole_table_cannot_double_count_its_original_row_items(system):
    from .test_pdf_repairs import table_units
    t,row=table_units();system[0].install(system[1],[t,row],[])
    decide(system,'accept_content','table')
    decide(system,'classify','table',classification='requirement')
    assert 'table' not in current(system)['published']
    with pytest.raises(ValueError,match='original_numbered_row'):
        decide(system,'subdivide_requirement','table')
