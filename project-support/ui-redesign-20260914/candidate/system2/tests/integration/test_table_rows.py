from copy import deepcopy
import json
import pytest
from pdf_extraction.contracts.hashing import digest
from pdf_extraction.review.browser_view import browser_state
from .test_two_stage_workflow import system,current,decide
from .test_pdf_repairs import table_units,get
from .test_review_rows import guarded


def row_request(system,change):
    return guarded(system,'table',action='table_rows',table_owner_id='table',target_fingerprint=digest(get(system,'table')),row_change=change,note='Compared the original table and row scope')


def test_create_missing_row_output_restore_and_conflict(system):
    s,did=system;t,row=table_units();s.install(did,[t],[])
    raw=deepcopy(get(system,'table')['original']);r=row_request(system,{'mode':'create','row':0})
    receipt=s.decision(r);assert s.decision(r)==receipt
    added=next(u for u in current(system)['units'] if u['id'].startswith('table-row:'))
    view=browser_state(s,'unit',did,added['id'])
    assert view['display_fields']['identifier']=='2.1.3' and view['display_fields']['criteria']=='≥ 2 highly abundant taxa'
    assert view['unit']['content_status']=='pending' and get(system,'table')['original']==raw
    decide(system,'accept_content','table');decide(system,'accept_content',added['id']);decide(system,'classify',added['id'],classification='requirement')
    assert current(system)['published'][added['id']]['fields']['criteria']=='≥ 2 highly abundant taxa'
    s.decision(guarded(system,'table',action='restore',restore_request_id=r['request_id'],note='Return to before row creation'))
    assert get(system,added['id'])['superseded_by']=='table' and added['id'] not in current(system)['published']
    r=row_request(system,{'mode':'create','row':0});s.decision(r)
    new=next(u for u in current(system)['units'] if u['id'].startswith('table-row:') and not u.get('superseded_by'))
    s.decision(guarded(system,'clause',action='relation',target_unit_id=new['id'],target_fingerprint=digest(new),role='reference',note='New incoming reference'))
    with pytest.raises(ValueError,match='restore_conflicts'):s.decision(guarded(system,'table',action='restore',restore_request_id=r['request_id'],note='Must preserve later relationships'))


def test_unassigned_rows_block_then_whole_table_scope_remains_reviewed(system):
    s,did=system;t,row=table_units();raw=json.loads(t['original']['fields']['body']);raw['row_count']=2
    for c in deepcopy(raw['cells']):c.update(id='second-'+c['id'],row=1);raw['cells'].append(c)
    t['original']['fields']['body']=json.dumps(raw);s.install(did,[t],[])
    s.decision(row_request(system,{'mode':'create','row':0}))
    assert 'human_table_row_gaps' in get(system,'table')['blockers']
    with pytest.raises(ValueError,match='assign_remaining_table_rows'):s.decision(guarded(system,'table',action='resolve_content',resolved_issues=['human_table_row_gaps'],note='Cannot dismiss actual unassigned rows'))
    s.decision(row_request(system,{'mode':'table_only','row':1}))
    table=get(system,'table');assert 'human_table_row_gaps' not in table['blockers']
    assert table['content_status']=='pending' and table['table_row_dispositions']['1']['mode']=='table_only'
    assert len(browser_state(s,'unit',did,'table')['effective']['table']['cells'])==4


def duplicates(system):
    s,did=system;t,row=table_units();duplicate=deepcopy(row);duplicate['id']='duplicate';s.install(did,[t,row,duplicate],[])
    return s,did


def retire(system):
    return row_request(system,{'mode':'retire_duplicate','unit_id':'duplicate','fingerprint':digest(get(system,'duplicate')),'replacement_id':'row','replacement_fingerprint':digest(get(system,'row'))})


def test_retire_duplicate_redirects_and_restores_incoming_reference(system):
    s,did=duplicates(system)
    s.decision(guarded(system,'clause',action='relation',target_unit_id='duplicate',target_fingerprint=digest(get(system,'duplicate')),role='reference',note='Original incoming reference'))
    raw=deepcopy(get(system,'duplicate')['original']);r=retire(system);s.decision(r)
    assert get(system,'duplicate')['superseded_by']=='row'
    assert get(system,'clause')['content_relations'][0]['target_unit_id']=='row'
    assert get(system,'duplicate')['original']==raw
    s.decision(guarded(system,'table',action='restore',restore_request_id=r['request_id'],note='Restore duplicate decision for re-review'))
    assert not get(system,'duplicate').get('superseded_by')
    assert get(system,'clause')['content_relations'][0]['target_unit_id']=='duplicate'


@pytest.mark.parametrize('change,match',[
    (lambda c:c.update(fingerprint='stale'),'stale_table_item'),
    (lambda c:c.update(replacement_id='table'),'choose_two_current'),
])
def test_invalid_retirement_is_atomic(system,change,match):
    s,did=duplicates(system);r=retire(system);change(r['row_change']);before=deepcopy(current(system))
    with pytest.raises(ValueError,match=match):s.decision(r)
    assert current(system)==before


def test_duplicate_text_conflict_and_draft_are_preserved(system):
    s,did=duplicates(system)
    with s.transaction() as db:
        doc=s._load(db,did);next(u for u in doc['units'] if u['id']=='duplicate')['edits']={'notes':'Unresolved source note'};s._save(db,doc)
    with pytest.raises(ValueError,match='resolve_duplicate_text'):s.decision(retire(system))
    decide(system,'draft','duplicate',draft={'body':'Unsaved correction'})
    with pytest.raises(ValueError,match='unsubmitted_draft'):s.decision(retire(system))


def test_new_row_cannot_promote_overlap_evidence_to_requirement(system):
    s,did=system;t,_=table_units();t['evidence_only']=True;s.install(did,[t],[])
    s.decision(row_request(system,{'mode':'create','row':0}))
    new=next(u for u in current(system)['units'] if u['id'].startswith('table-row:'))
    assert new['evidence_only'] is True
    decide(system,'accept_content','table');decide(system,'accept_content',new['id'])
    with pytest.raises(ValueError):decide(system,'classify',new['id'],classification='requirement')
    assert new['id'] not in current(system)['published']
