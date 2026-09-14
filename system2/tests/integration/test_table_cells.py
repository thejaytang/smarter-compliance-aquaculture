from copy import deepcopy
import json
import pytest
from pdf_extraction.contracts.hashing import digest
from pdf_extraction.review.browser_view import browser_state
from .test_two_stage_workflow import system,current,decide
from .test_pdf_repairs import table_units,get
from .test_review_rows import guarded
from .test_table_geometry import request as layout_request


def prepare(system):
    s,did=system;s.install(did,list(table_units()),[])
    return s,did


def merge_request(system):
    r=layout_request(system);r.update(action='table_cells',cell_change={'mode':'merge','cell_ids':['c0','c1'],'separator':'\n'})
    r['table_geometry']['cells']=[{'id':'new:0','row':0,'column':0,'row_span':1,'column_span':2,'is_header':False}]
    return r


def test_merge_split_correct_restore_preserves_cells_and_shared_rows(system):
    s,did=prepare(system);raw=deepcopy(get(system,'table')['original']);req=merge_request(system);a=s.decision(req);assert s.decision(req)==a
    t=browser_state(s,'unit',did,'table')['effective']['table'];cell=t['cells'][0]
    assert len(t['cells'])==1 and cell['column_span']==2
    assert len(cell['source_regions'])==2 and cell['bbox']==[0,0,200,100]
    assert browser_state(s,'unit',did,'row')['effective']['table']['cells'][0]['id']==cell['id']
    split=layout_request(system);split.update(action='table_cells',cell_change={'mode':'split','cell_ids':[cell['id']],'parts':[
        {'text':'2.1.3 Number of taxa\n','reference_indices':[0]}, {'text':'≥ 2 highly abundant taxa','reference_indices':[1]}]})
    split['table_geometry']['cells']=[{'id':'new:'+str(i),'row':0,'column':i,'row_span':1,'column_span':1,'is_header':False} for i in range(2)]
    s.decision(split);v=browser_state(s,'unit',did,'row');assert v['display_fields']['identifier']=='2.1.3' and v['display_fields']['criteria']=='≥ 2 highly abundant taxa'
    assert len(v['effective']['references'])==2
    assert v['effective']['references'][1]['cell_text_range']['start']==len('2.1.3 Number of taxa\n')
    assert get(system,'table')['original']==raw
    newcell=v['effective']['table']['cells'][1]['id']
    change=guarded(system,'row',action='table_cell',table_owner_id='table',cell_id=newcell,target_fingerprint=digest(get(system,'table')),text='≥ 3 highly abundant taxa',note='Later source correction')
    s.decision(change);assert browser_state(s,'unit',did,'row')['display_fields']['criteria']=='≥ 3 highly abundant taxa'
    with pytest.raises(ValueError,match='restore_conflicts'):
        s.decision(guarded(system,'table',action='restore',restore_request_id=split['request_id'],note='Do not overwrite newer text'))
    with pytest.raises(ValueError,match='table_cell_invalid'):
        s.decision(guarded(system,'row',action='table_cell',table_owner_id='table',cell_id='c1',target_fingerprint=digest(get(system,'table')),text='Obsolete target',note='Must remain historical'))


def test_merge_restore_returns_exact_source_cell_projection(system):
    s,did=prepare(system);before=browser_state(s,'unit',did,'table')['effective']['table'];r=merge_request(system);s.decision(r)
    s.decision(guarded(system,'table',action='restore',restore_request_id=r['request_id'],note='Restore source cells'))
    assert browser_state(s,'unit',did,'table')['effective']['table']==before
    assert {x['locator'] for x in browser_state(s,'unit',did,'row')['effective']['references']}=={'c0','c1'}


@pytest.mark.parametrize('change,match',[
    (lambda r:r['cell_change'].update(cell_ids=['c0','c0']),'invalid_source_cell'),
    (lambda r:r['cell_change'].update(separator='invented text'),'original_separator'),
    (lambda r:r['table_geometry']['cells'][0].update(column_span=1),'unresolved_gaps'),
    (lambda r:r['table_geometry']['row_bindings'].clear(),'bind_every_existing'),
])
def test_invalid_cell_change_is_atomic(system,change,match):
    s,did=prepare(system);r=merge_request(system);before=deepcopy(current(system));change(r)
    with pytest.raises(ValueError,match=match):s.decision(r)
    assert current(system)==before


def test_split_rejects_text_loss_and_missing_regions(system):
    s,did=prepare(system);r=layout_request(system);r.update(action='table_cells',cell_change={'mode':'split','cell_ids':['c0'],'parts':[{'text':'Changed','reference_indices':[0]},{'text':'text','reference_indices':[0]}]})
    with pytest.raises(ValueError,match='preserve_every_character'):s.decision(r)
    r['cell_change']['parts']=[{'text':'2.1.3 ','reference_indices':[]},{'text':'Number of taxa','reference_indices':[0]}]
    with pytest.raises(ValueError,match='original_regions'):s.decision(r)


def test_supplement_missing_cell_has_original_region_and_is_not_accepted(system):
    s,did=system;t,row=table_units();raw=json.loads(t['original']['fields']['body']);raw['cells'].pop();t['original']['fields']['body']=json.dumps(raw);row['original']['references']=row['original']['references'][:1];s.install(did,[t,row],[])
    with s.transaction() as db:
        d=s._load(db,did);d['source']['file_format']='pdf';d['total_pages']=21;s._save(db,d)
    r=layout_request(system);r.update(action='table_cells',cell_change={'mode':'supplement','cell_ids':[],'text':'≥ 2 highly abundant taxa','locator':'page 20: 100,0,200,100'})
    r['table_geometry']['cells'].append({'id':'new:0','row':0,'column':1,'row_span':1,'column_span':1,'is_header':False})
    s.decision(r);v=browser_state(s,'unit',did,'row');assert v['display_fields']['criteria']=='≥ 2 highly abundant taxa'
    assert v['unit']['content_status']=='pending' and 'row' not in current(system)['published']
    assert v['effective']['references'][1]['source_sha256']==current(system)['source']['content_hash']


def test_partial_table_repair_remains_blocked_until_grid_is_filled(system):
    s,did=prepare(system);r=layout_request(system);r['table_geometry'].update(column_count=3,allow_incomplete=True)
    s.decision(r)
    v=browser_state(s,'unit',did,'table');assert 'human_table_grid_gaps' in v['unit']['blockers'] and v['task']['type']=='structure'
    with pytest.raises(ValueError,match='remaining_table_grid_gaps'):
        decide(system,'resolve_content','table',resolved_issues=['human_table_grid_gaps'],note='Cannot dismiss a physical gap')
    r=layout_request(system);r['table_geometry']['column_count']=2;s.decision(r)
    assert 'human_table_grid_gaps' not in get(system,'table')['blockers']
    assert get(system,'table')['content_status']=='pending'


def test_cell_preview_is_bound_to_current_guard_and_recorded_region(system):
    from pdf_extraction.review.table_cells import preview_regions
    s,did=prepare(system);v=browser_state(s,'unit',did,'table')
    assert preview_regions(v,'c1',0,v['guard'])[0]['bbox']==[100,0,200,100]
    with pytest.raises(ValueError,match='version_changed'):preview_regions(v,'c1',0,'old')
    with pytest.raises(ValueError,match='not_found'):preview_regions(v,'invented',0,v['guard'])
    with pytest.raises(ValueError,match='out_of_range'):preview_regions(v,'c1',1,v['guard'])


def test_cell_boundary_invalidates_delivery_and_republishes_only_after_review(system):
    s,did=prepare(system)
    decide(system,'accept_content','table');decide(system,'accept_content','row');decide(system,'classify','row',classification='requirement')
    expected=current(system)['published']['row']['fields']['criteria']
    s.decision(merge_request(system))
    assert 'row' not in current(system)['published']
    cell=browser_state(s,'unit',did,'table')['effective']['table']['cells'][0]
    r=layout_request(system);r.update(action='table_cells',cell_change={'mode':'split','cell_ids':[cell['id']],'parts':[
        {'text':'2.1.3 Number of taxa\n','reference_indices':[0]}, {'text':expected,'reference_indices':[1]}]})
    r['table_geometry']['cells']=[{'id':'new:'+str(i),'row':0,'column':i,'row_span':1,'column_span':1,'is_header':False} for i in range(2)]
    s.decision(r)
    assert 'row' not in current(system)['published']
    decide(system,'accept_content','table');decide(system,'accept_content','row');decide(system,'classify','row',classification='requirement')
    assert current(system)['published']['row']['fields']['criteria']==expected
