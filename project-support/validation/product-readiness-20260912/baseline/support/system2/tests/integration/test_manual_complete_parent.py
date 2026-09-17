"""A deliberately manual complete-parent alternative to automatic row joining."""
from copy import deepcopy
import json

from pdf_extraction.contracts.hashing import digest
from pdf_extraction.review.browser_view import browser_state
from .test_two_stage_workflow import system,current,decide
from .test_pdf_repairs import table_units,get
from .test_review_rows import guarded


def test_complete_advisory_parent_keeps_both_pages_and_reopens_after_context_edit(system,tmp_path):
    s,did=system;first,row=table_units();second=deepcopy(first);tail=deepcopy(row)
    second['id']='second';tail['id']='tail';tail['dependencies']=['second','coverage']
    fragments=[(first,row,0,['9.1 Daily check','Operators should record water temperature at']),
               (second,tail,1,['','the inlet and outlet before feeding.'])]
    for table,item,page,texts in fragments:
        raw=json.loads(table['original']['fields']['body'])
        for cell,text in zip(raw['cells'],texts):cell.update(page_index=page,content={'resolved_text':text})
        table['original']['fields']['body']=json.dumps(raw)
        for u in (table,item):
            u['content_parts']=[];u['requirement_parts']=[]
            for ref in u['original']['references']:ref['page_index']=page
    s.install(did,[first,row,second,tail],[])
    originals={uid:deepcopy(get(system,uid)['original']) for uid in ('table','row','second','tail')}
    fields={'identifier':'9.1','body':'Daily check',
            'criteria':'Operators should record water temperature at the inlet and outlet before feeding.'}
    r=guarded(system,'coverage',action='supplement',fields=fields,locator='page 1:0,0,200,100',
              note='Complete original numbered parent transcribed across both pages; physical fragments remain context.')
    receipt=s.decision(r);assert s.decision(r)==receipt
    parent='manual:'+r['request_id']
    for uid in ('row','tail'):
        s.decision(guarded(system,parent,action='relation',target_unit_id=uid,target_fingerprint=digest(get(system,uid)),
                           role='context',note='Physical original fragment of complete item 9.1'))
    for uid in ('coverage','clause','table','row','second','tail',parent):decide(system,'accept_content',uid)
    for uid in ('coverage','clause','table','row','second','tail'):
        decide(system,'classify',uid,classification='context',note='Original source evidence; only the complete parent is delivered')
    # Simulate a saved erroneous negative judgment, then correct it through the same public decision API.
    decide(system,'classify',parent,classification='non_requirement',note='Injected negative judgment for correction test')
    assert not current(system)['published']
    decide(system,'classify',parent,classification='requirement',note='Should is advisory wording; the whole original item is a requirement')
    decisions=[h for h in browser_state(s,'history_page',did)['items'] if h['unit_id']==parent and h['action']=='classify']
    assert decisions[0]['classification_before']=='non_requirement'
    assert decisions[0]['classification_after']=='requirement'
    assert decisions[1]['classification_after']=='non_requirement'
    assert decisions[0]['at'] and decisions[0]['source_version']['content_hash']=='a'*64
    published=current(system)['published'];assert set(published)=={parent}
    assert published[parent]['fields']['criteria']==fields['criteria']
    assert {r['page_index'] for c in published[parent]['related_content'] for r in c['references']}=={0,1}
    assert [c['target_unit_id'] for c in browser_state(s,'unit',did,parent)['effective']['related_content']]==['row','tail']
    from .test_requirement_workbook import export
    _,book,_=export(system,tmp_path)
    records=[r for r in book['PA001'] if r[17].value==parent]
    assert len(records)==1
    record=records[0]
    assert record[9].value==fields['criteria']
    assert 'Linked context · pages 1' in record[6].value and 'Linked context · pages 2' in record[6].value
    assert 'the inlet and outlet before feeding.' in record[6].value
    assert 'Linked original pages 1, 2' in record[7].value
    assert json.loads(record[25].value)['canonical_sha256']==[current(system)['canonical'][0]['sha256']]
    assert {r['page_index'] for c in json.loads(record[26].value)['related_content'] for r in c['references']}=={0,1}
    book.close()
    s.decision(guarded(system,'tail',action='table_cell',table_owner_id='second',cell_id='c1',
                      target_fingerprint=digest(get(system,'second')),text='the inlet and outlet after feeding.',
                      note='Injected later correction must suspend the dependent parent'))
    assert parent not in current(system)['published']
    assert not get(system,parent)['content_human'] and not get(system,parent)['requirement_human']
    assert get(system,parent)['edits']=={}
    for uid,original in originals.items():assert get(system,uid)['original']==original
