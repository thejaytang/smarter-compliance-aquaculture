from copy import deepcopy
import json
import pytest
from pdf_extraction.contracts.hashing import digest
from pdf_extraction.review.browser_view import browser_state
from .test_two_stage_workflow import system,current,decide,unit
from .test_pdf_repairs import get,table_units
from .test_review_rows import guarded


def setup(system):
    s,did=system;t,row=table_units();second=deepcopy(t);second['id']='second';r2=deepcopy(row);r2['id']='r2';r2['dependencies']=['second','coverage']
    raw=json.loads(t['original']['fields']['body']);raw['row_count']=2
    headers=[]
    for i,c in enumerate(raw['cells']):
        c['row']=1;c['page_index']=18
        h=deepcopy(c);h.update(id='h'+str(i),row=0,is_header=True);h['content']={'resolved_text':['INDICATOR','REQUIREMENT'][i]};headers.append(h)
    raw['cells']+=headers;t['original']['fields']['body']=json.dumps(raw);t['original']['references'][0]['page_index']=18
    for ref in row['original']['references']:ref['page_index']=18
    second['original']['references'][0]['page_index']=19
    with s.transaction() as db:
        d=s._load(db,did);d['source']['file_format']='pdf';s._save(db,d)
    s.install(did,[t,row,second,r2,unit('note')],[])
    return s,did


def join_request(system):
    return guarded(system,'table',action='table_assembly',note='Compared matching columns on consecutive original pages',table_assembly={
        'fragments':[{'unit_id':uid,'fingerprint':digest(get(system,uid))} for uid in ('table','second')],
        'header_source_id':'table','header_cell_ids':['h0','h1']})


def assembly(system):return next(u for u in current(system)['units'] if u.get('table_assembly') and not u.get('superseded_by'))


def test_join_duplicate_cell_ids_source_evidence_delivery_and_restore(system,tmp_path):
    s,did=setup(system);originals={i:deepcopy(get(system,i)['original']) for i in ('table','second','row','r2')}
    r=join_request(system);receipt=s.decision(r);assert s.decision(r)==receipt
    added=assembly(system);v=browser_state(s,'unit',did,added['id'])['effective']
    assert v['table_scope']=='cross_page_table' and v['table']['row_count']==3
    assert len({c['id'] for c in v['table']['cells']})==6
    assert {c['page_index'] for c in v['table']['cells']}=={18,19}
    assert [h['text'] for h in v['table_assembly']['column_headers']]==['INDICATOR','REQUIREMENT']
    assert browser_state(s,'unit',did,'r2')['effective']['table_assembly']['id']==added['id']
    assert added['id'] in get(system,'r2')['dependencies'] and added['id'] not in get(system,'second')['dependencies']
    for uid in ('table','second','row','r2',added['id']):decide(system,'accept_content',uid)
    with pytest.raises(ValueError,match='context_only'):decide(system,'classify',added['id'],classification='requirement')
    decide(system,'classify','r2',classification='requirement')
    assert current(system)['published']['r2']['table_assembly']['column_headers'][1]['text']=='REQUIREMENT'
    from .test_requirement_workbook import export
    _,book,_=export(system,tmp_path)
    assert any('Combined table' in str(c.value) for row in book['PA001'] for c in row);book.close()
    s.decision(guarded(system,'table',action='restore',restore_request_id=r['request_id'],note='Undo only the new correspondence'))
    assert get(system,added['id'])['superseded_by']=='table'
    assert not get(system,'r2').get('table_assembly_id') and added['id'] not in get(system,'r2')['dependencies']
    for uid,original in originals.items():assert get(system,uid)['original']==original
    assert 'r2' not in current(system)['published']


def test_fragment_edit_updates_assembly_and_local_notes_do_not_leak(system):
    s,did=setup(system)
    s.decision(guarded(system,'second',action='relation',target_unit_id='note',target_fingerprint=digest(get(system,'note')),role='notes',note='Only the second page cites this note'))
    r=join_request(system);s.decision(r);aid=assembly(system)['id']
    for uid in ('table','second','row','r2',aid):decide(system,'accept_content',uid)
    decide(system,'classify','r2',classification='requirement')
    assert browser_state(s,'unit',did,'row')['display_fields'].get('notes') is None
    assert browser_state(s,'unit',did,'r2')['display_fields']['notes']=='Fish farms shall keep records.'
    s.decision(guarded(system,'r2',action='table_cell',table_owner_id='second',target_fingerprint=digest(get(system,'second')),cell_id='c1',text='≥ 3 highly abundant taxa',note='Correct the second original page'))
    v=browser_state(s,'unit',did,aid)['effective']
    assert '≥ 3 highly abundant taxa' in v['fields']['body'] and '≥ 2 highly abundant taxa' in v['fields']['body']
    assert not get(system,aid)['content_human'] and 'r2' not in current(system)['published']
    with pytest.raises(ValueError,match='restore_conflicts'):s.decision(guarded(system,'table',action='restore',restore_request_id=r['request_id'],note='Must not overwrite the later cell edit'))
    with pytest.raises(ValueError,match='edit_the_original'):s.decision(guarded(system,aid,action='correct',fields={'body':'overwrite'},note='Not a fragment'))


@pytest.mark.parametrize('alter,message',[
    (lambda r:r['table_assembly']['fragments'][1].update(fingerprint='stale'),'stale_table_assembly'),
    (lambda r:r['table_assembly'].update(header_cell_ids=['missing']),'header_changed'),
    (lambda r:r['table_assembly'].update(fragments=list(reversed(r['table_assembly']['fragments']))),'fragment_order'),
])
def test_invalid_join_rolls_back(system,alter,message):
    s,did=setup(system);r=join_request(system);alter(r);before=current(system)
    with pytest.raises(ValueError,match=message):s.decision(r)
    assert current(system)==before


def test_concurrent_target_draft_and_grid_drift_stay_pending(system):
    s,did=setup(system);decide(system,'draft','second',draft={'text':'Review in progress'})
    with pytest.raises(ValueError,match='unsubmitted_draft'):s.decision(join_request(system))
    with s.transaction() as db:
        doc=s._load(db,did);next(u for u in doc['units'] if u['id']=='second')['drafts']={};s._save(db,doc)
    s.decision(join_request(system));aid=assembly(system)['id']
    with s.transaction() as db:
        doc=s._load(db,did);owner=next(u for u in doc['units'] if u['id']=='table')
        raw=json.loads(owner['original']['fields']['body']);owner['reviewed_cells']=[c for c in raw['cells'] if c['id']!='h0']
        s._recompute(db,doc,s.policy(db));s._save(db,doc)
    assert 'table_assembly_header_changed' in get(system,aid)['blockers']
    assert browser_state(s,'unit',did,aid)['effective']['table_assembly']['error']=='table_assembly_header_changed'
    with pytest.raises(ValueError):decide(system,'accept_content',aid)


def test_later_row_creation_keeps_assembly_gate_and_can_be_restored(system):
    s,did=setup(system)
    with s.transaction() as db:
        doc=s._load(db,did);doc['units']=[u for u in doc['units'] if u['id']!='r2'];s._save(db,doc)
    s.decision(join_request(system));aid=assembly(system)['id']
    r=guarded(system,'second',action='table_rows',table_owner_id='second',target_fingerprint=digest(get(system,'second')),row_change={'mode':'create','row':0},note='Restore missing row review identity')
    s.decision(r);new=next(u for u in current(system)['units'] if u['id'].startswith('table-row:'))
    assert aid in new['dependencies'] and new['table_assembly_id']==aid
    assert browser_state(s,'unit',did,new['id'])['effective']['table_assembly']['column_headers'][0]['text']=='INDICATOR'
    s.decision(guarded(system,'second',action='restore',restore_request_id=r['request_id'],note='Undo only the new row identity'))
    assert get(system,new['id'])['superseded_by']=='second'
    assert get(system,'second')['table_assembly_id']==aid


def test_reopened_assembly_has_an_explicit_resolution_path(system):
    s,did=setup(system);s.decision(join_request(system));aid=assembly(system)['id']
    decide(system,'reopen',aid,note='The reviewer needs to compare the page boundary again')
    blockers=get(system,aid)['blockers'];assert 'human_reopen' in blockers
    with pytest.raises(ValueError):decide(system,'accept_content',aid)
    decide(system,'resolve_content',aid,resolved_issues=blockers,note='Original page boundary has now been compared')
    assert get(system,aid)['content_human'] is True
