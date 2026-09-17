from copy import deepcopy
import json
import pytest
from pdf_extraction.contracts.hashing import digest
from pdf_extraction.review.browser_view import browser_state
from .test_two_stage_workflow import system,current,decide
from .test_pdf_repairs import table_units,get
from .test_review_rows import guarded


def prepare(system):
    s,did=system;t,a=table_units();b=deepcopy(a);b['id']='row2'
    data=json.loads(t['original']['fields']['body']);data['row_count']=2
    second=deepcopy(data['cells'])
    for i,c in enumerate(second):c.update(id='d'+str(i),row=1,is_header=False)
    second[0]['content']['resolved_text']='2.1.4 Definition of AZE';second[1]['content']['resolved_text']='Yes'
    data['cells'].extend(second);t['original']['fields']['body']=json.dumps(data)
    b['original']['fields']={'identifier':'2.1.4','body':'Definition of AZE','criteria':'Yes'}
    b['original']['references']=[{'locator':c['id'],'page_index':19,'bbox':c['bbox']} for c in second]
    s.install(did,[t,a,b],[]);return s,did


def request(system):
    s,did=system;ctx=browser_state(s,'unit',did,'table')['table_context']
    return guarded(system,'table',action='table_geometry',table_owner_id='table',target_fingerprint=ctx['fingerprint'],note='Checked original rows and cell ranges',table_geometry={
        'row_count':ctx['table']['row_count'],'column_count':ctx['table']['column_count'],
        'cells':[dict({k:c[k] for k in ('id','row','column','row_span','column_span')},is_header=False) for c in ctx['table']['cells']],
        'row_bindings':{r['id']:{'row':r['row'],'fingerprint':r['fingerprint']} for r in ctx['rows']}})


def test_grid_reorder_updates_rows_html_structure_delivery_and_restore(system):
    s,did=prepare(system);originals={u['id']:deepcopy(u['original']) for u in current(system)['units']}
    decide(system,'accept_content','table');decide(system,'accept_content','row');decide(system,'classify','row',classification='requirement')
    assert current(system)['published']['row']['fields']['criteria']=='≥ 2 highly abundant taxa'
    r=request(system)
    for c in r['table_geometry']['cells']:c['row']=1-c['row']
    r['table_geometry']['row_bindings']['row']['row']=1;r['table_geometry']['row_bindings']['row2']['row']=0
    receipt=s.decision(r);assert s.decision(r)==receipt
    v=browser_state(s,'unit',did,'table')['effective'];row=browser_state(s,'unit',did,'row')['effective']
    assert v['fields']['body'].startswith('2.1.4') and row['fields']['identifier']=='2.1.3'
    assert v['table']['html'].index('2.1.4')<v['table']['html'].index('2.1.3')
    assert '<th' not in v['table']['html'] and '2.1.4' not in row['table']['html']
    assert row['structure'][0]['row']==1 and 'row' not in current(system)['published']
    assert [u['id'] for u in current(system)['units']].index('row2')<[u['id'] for u in current(system)['units']].index('row')
    assert {u['id']:u['original'] for u in current(system)['units']}==originals
    s.decision(guarded(system,'table',action='restore',restore_request_id=r['request_id'],note='Restore prior layout'))
    assert browser_state(s,'unit',did,'table')['effective']['fields']['body'].startswith('2.1.3')
    assert [u['id'] for u in current(system)['units']].index('row')<[u['id'] for u in current(system)['units']].index('row2')


@pytest.mark.parametrize('change,match',[
    (lambda g:g['cells'].pop(),'preserve_every_table_cell'),
    (lambda g:g['cells'][0].update(column_span=2),'overlap'),
    (lambda g:g.update(column_count=3),'unresolved_gaps'),
    (lambda g:g['cells'][0].update(row=-1),'outside_grid'),
    (lambda g:g['cells'][0].update(row_span=0),'outside_grid'),
    (lambda g:g['row_bindings']['row'].update(row=1),'same_table_row'),
    (lambda g:g['row_bindings']['row'].update(fingerprint='stale'),'stale_table_row'),
    (lambda g:g['row_bindings'].pop('row'),'bind_every_existing'),
])
def test_invalid_grid_is_atomic(system,change,match):
    s,did=prepare(system);r=request(system);before=deepcopy(get(system,'table'));change(r['table_geometry'])
    with pytest.raises(ValueError,match=match):s.decision(r)
    assert get(system,'table')==before


def test_shared_row_rebinding_and_text_edit_use_same_effective_cells(system):
    s,did=prepare(system);r=request(system)
    s.decision(guarded(system,'clause',action='relation',target_unit_id='row',target_fingerprint=digest(get(system,'row')),role='reference',note='Reference the effective table item'))
    r=request(system)
    # An explicitly corrected logical-row assignment must also replace its source references.
    r['table_geometry']['row_bindings']['row']['row']=1;r['table_geometry']['row_bindings']['row2']['row']=0
    s.decision(r)
    v=browser_state(s,'unit',did,'row');assert v['display_fields']['identifier']=='2.1.4'
    assert {r['locator'] for r in v['effective']['references']}=={'d0','d1'}
    s.decision(guarded(system,'row',action='table_cell',table_owner_id='table',target_fingerprint=digest(get(system,'table')),cell_id='d1',text='Corrected value < 3',note='Checked source'))
    v=browser_state(s,'unit',did,'row');assert v['display_fields']['criteria']=='Corrected value < 3'
    linked=browser_state(s,'unit',did,'clause')['effective']['related_content'][0]['fields']
    assert linked['identifier']=='2.1.4' and linked['criteria']=='Corrected value < 3'
    assert 'Corrected value &lt; 3' in v['effective']['table']['html']
    with pytest.raises(ValueError,match='restore_conflicts'):
        s.decision(guarded(system,'table',action='restore',restore_request_id=r['request_id'],note='Cannot overwrite later cell correction'))


def test_merged_span_preserves_cell_evidence_and_flags(system):
    s,did=system;t,a=table_units();data=json.loads(t['original']['fields']['body'])
    # Two cells placed vertically can be reconstructed as two full-width rows.
    s.install(did,[t],[]);r=request(system);r['table_geometry'].update(row_count=2,column_count=2)
    for i,c in enumerate(r['table_geometry']['cells']):c.update(row=i,column=0,column_span=2,is_header=i==0)
    s.decision(r);table=browser_state(s,'unit',did,'table')['effective']['table']
    assert 'colspan="2"' in table['html'] and '<th' in table['html']
    assert [c['bbox'] for c in table['cells']]==[c['bbox'] for c in data['cells']]


def test_shared_vertical_cell_keeps_each_row_column_order(system):
    s,did=system;t,a=table_units();data=json.loads(t['original']['fields']['body'])
    data['row_count']=2;data['column_count']=3
    data['cells'][0]['content']['resolved_text']='Canada';data['cells'][1]['content']['resolved_text']='1'
    shared=deepcopy(data['cells'][1]);shared.update(id='global',column=2,row_span=2);shared['content']['resolved_text']='3**';data['cells'].append(shared)
    for i,text in enumerate(('Norway','5')):
        c=deepcopy(data['cells'][i]);c.update(id='norway'+str(i),row=1);c['content']['resolved_text']=text;data['cells'].append(c)
    t['original']['fields']['body']=json.dumps(data)
    a['original']['references']=[{'locator':c['id'],'page_index':19,'bbox':c['bbox']} for c in data['cells'] if c['row']==0]
    b=deepcopy(a);b['id']='row2';b['original']['references']=[{'locator':c['id'],'page_index':19,'bbox':c['bbox']} for c in data['cells'] if c['row']==1]
    s.install(did,[t,a,b],[]);r=request(system);s.decision(r)
    view=browser_state(s,'unit',did,'row2')['effective']
    assert view['fields']['body']=='Norway\n5\n3**'
    assert view['table']['html'].count('<tr>')==1
    assert view['table']['html'].index('Norway')<view['table']['html'].index('5')<view['table']['html'].index('3**')
    assert view['table']['selected_row']==1
    assert next(c for c in view['table']['cells'] if c['id']=='global')['row_span']==2
