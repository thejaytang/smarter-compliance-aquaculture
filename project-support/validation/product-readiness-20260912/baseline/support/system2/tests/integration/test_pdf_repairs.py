from copy import deepcopy
import json
import pytest
from pdf_extraction.review import effective
from pdf_extraction.contracts.hashing import digest
from pdf_extraction.review.browser_view import browser_state
from .test_two_stage_workflow import system,current,unit,request,decide
from .test_review_rows import guarded
from .test_requirement_workbook import export


def get(system,uid):return next(u for u in current(system)['units'] if u['id']==uid)


def table_units():
    table=unit('table','context');row=unit('row','standard_indicator')
    cells=[{'id':'c0','row':0,'column':0,'row_span':1,'column_span':1,'page_index':19,'bbox':[0,0,100,100],
        'content':{'resolved_text':'2.1.3 Number of taxa'}},
        {'id':'c1','row':0,'column':1,'row_span':1,'column_span':1,'page_index':19,'bbox':[100,0,200,100],
        'content':{'resolved_text':'≥ 2 highly abundant taxa'}}]
    table['original']['fields']={'body':json.dumps({'row_count':1,'column_count':2,'cells':cells})}
    table['original']['references']=[{'page_index':19,'block_id':'t','bbox':[0,0,200,100]}]
    row['original']['fields']={'identifier':'2.1.3','body':'Number of taxa','criteria':'≥ 2 highly abundant taxa'}
    row['original']['references']=[{'locator':c['id'],'page_index':19,'block_id':'t','bbox':c['bbox']} for c in cells]
    row['dependencies']=['table','coverage']
    return table,row


def test_footnote_link_is_effective_and_invalidates_shared_outputs(system,tmp_path):
    s,did=system;s.install(did,[unit('note','source_note'),unit('independent')],[])
    original=deepcopy(get(system,'clause')['original'])
    req=guarded(system,'clause',action='relation',target_unit_id='note',target_fingerprint=digest(get(system,'note')),role='notes',note='Linked original footnote')
    first=s.decision(req);assert s.decision(req)==first
    assert 'note' in get(system,'clause')['dependencies']
    decide(system,'accept_content');decide(system,'classify',classification='requirement')
    assert current(system)['published']['clause']['fields']['notes']=='Fish farms shall keep records.'
    decide(system,'correct','note',fields={'body':'Verified corrected note.'},note='Source checked')
    assert 'clause' not in current(system)['published']
    assert 'independent' in current(system)['published']
    assert get(system,'clause')['content_status']=='pending'
    assert get(system,'clause')['original']==original
    assert browser_state(s,'unit',did,'clause')['display_fields']['notes']=='Verified corrected note.'
    _,wb,_=export(system,tmp_path)
    assert any('Verified corrected note.' in str(c.value) for row in wb['PA001'] for c in row)
    wb.close()


def test_relation_rejects_cycles_stale_target_and_invalid_identity(system):
    s,did=system;s.install(did,[unit('note')],[])
    req=guarded(system,'clause',action='relation',target_unit_id='note',target_fingerprint=digest(get(system,'note')),role='notes',note='Source link')
    decide(system,'draft','note',draft={'note':'Concurrent edit'})
    with pytest.raises(ValueError,match='stale_relation_target'):s.decision(req)
    req.update(request_id=request()['request_id'],target_fingerprint=digest(get(system,'note')))
    s.decision(req)
    with pytest.raises(ValueError,match='cycle'):
        s.decision(guarded(system,'note',action='relation',target_unit_id='clause',target_fingerprint=digest(get(system,'clause')),role='notes',note='Cycle'))


def test_table_cell_single_owner_output_and_restore(system,tmp_path):
    s,did=system;s.install(did,list(table_units()),[])
    original=deepcopy(get(system,'table')['original'])
    r=guarded(system,'row',action='table_cell',table_owner_id='table',cell_id='c1',target_fingerprint=digest(get(system,'table')),text='≥ 3 highly abundant taxa',note='Isolated injected correction')
    s.decision(r)
    for uid in ('row','table'):
        view=browser_state(s,'unit',did,uid)
        assert '≥ 3' in str(view['display_fields'])
        assert effective.cell_text(view['effective']['table']['cells'][-1])=='≥ 3 highly abundant taxa'
    assert get(system,'table')['original']==original and not get(system,'row').get('cell_edits')
    assert 'row' not in current(system)['published']
    decide(system,'accept_content','table');decide(system,'accept_content','row');decide(system,'classify','row',classification='requirement')
    assert current(system)['published']['row']['fields']['criteria']=='≥ 3 highly abundant taxa'
    _,wb,_=export(system,tmp_path)
    assert any(c.value=='≥ 3 highly abundant taxa' for row in wb['PA001'] for c in row);wb.close()
    s.decision(guarded(system,'row',action='restore',restore_request_id=r['request_id'],note='Restore prior cell value'))
    assert browser_state(s,'unit',did,'row')['display_fields']['criteria']=='≥ 2 highly abundant taxa'
    assert 'row' not in current(system)['published']
    assert get(system,'table')['version']>1


def test_supplement_keeps_position_and_reopens_coverage(system,tmp_path):
    s,did=system
    with s.transaction() as db:
        d=s._load(db,did);d['source']['file_format']='pdf';d['total_pages']=21;s._save(db,d)
    req=guarded(system,'clause',action='supplement',fields={'body':'Missing original note'},locator='page 20: 10,20,100,200',note='Checked original')
    s.decision(req);d=current(system);idx=next(i for i,u in enumerate(d['units']) if u['id']=='clause');added=d['units'][idx+1]
    assert added['id'].startswith('manual:') and added['original']['references'][0]['page_index']==19
    assert added['original']['references'][0]['bbox']==[10,20,100,200]
    assert get(system,'coverage')['content_status']=='pending' and not d['published']
    assert s.decision(req)['status']=='applied'
    _,wb,_=export(system,tmp_path);assert any('Pages 20' in str(c.value) for row in wb['PA001'] for c in row);wb.close()
    with pytest.raises(ValueError,match='out_of_range'):
        s.decision(guarded(system,'clause',action='supplement',fields={'body':'Bad page'},locator='page 22',note='Test'))


def test_restore_does_not_overwrite_later_cell_edit(system):
    s,did=system;s.install(did,list(table_units()),[])
    first=guarded(system,'row',action='table_cell',table_owner_id='table',cell_id='c1',target_fingerprint=digest(get(system,'table')),text='First checked value',note='Test')
    s.decision(first)
    second=guarded(system,'row',action='table_cell',table_owner_id='table',cell_id='c1',target_fingerprint=digest(get(system,'table')),text='Later checked value',note='Test')
    s.decision(second)
    with pytest.raises(ValueError,match='restore_conflicts'):
        s.decision(guarded(system,'row',action='restore',restore_request_id=first['request_id'],note='Old restoration'))
    assert browser_state(s,'unit',did,'row')['display_fields']['criteria']=='Later checked value'


def test_supplement_inserts_by_original_page_coordinates(system):
    s,did=system
    left=unit('left');right=unit('right')
    left['original']['references']=[{'page_index':19,'bbox':[20,500,200,520]}]
    right['original']['references']=[{'page_index':19,'bbox':[20,580,200,600]}]
    s.install(did,[left,right],[])
    req=guarded(system,'clause',action='supplement',fields={'body':'Footnote 7'},locator='page 20: 20,530,200,560',note='Original location')
    s.decision(req)
    ids=[u['id'] for u in current(system)['units']]
    assert ids.index('left')<ids.index('manual:'+req['request_id'])<ids.index('right')
    history=current(system)['history'][-1]
    assert history['created_units'][0]['references'][0]['page_index']==19


def test_legacy_row_override_requires_an_explicit_choice(system):
    s,did=system;s.install(did,list(table_units()),[])
    with s.transaction() as db:
        doc=s._load(db,did)
        next(u for u in doc['units'] if u['id']=='row')['edits']['criteria']='Prior human row wording'
        s._save(db,doc)
    s.decision(guarded(system,'row',action='table_cell',table_owner_id='table',cell_id='c1',target_fingerprint=digest(get(system,'table')),text='New verified cell wording',note='Test'))
    assert 'human_table_text_conflict' in get(system,'row')['blockers']
    with pytest.raises(ValueError,match='choose_effective_table_values'):
        s.decision(guarded(system,'row',action='resolve_content',resolved_issues=['human_table_text_conflict'],note='Cannot merely dismiss conflict'))
    s.decision(guarded(system,'row',action='use_table_values',table_owner_id='table',target_fingerprint=digest(get(system,'table')),note='Explicitly prefer original-supported cell wording'))
    assert browser_state(s,'unit',did,'row')['display_fields']['criteria']=='New verified cell wording'
    assert 'human_table_text_conflict' not in get(system,'row')['blockers']
    assert get(system,'row')['content_status']=='pending'


def test_table_wide_note_reaches_row_output_and_cannot_be_detached_locally(system):
    s,did=system;t,row=table_units();s.install(did,[t,row,unit('table-note','source_note')],[])
    s.decision(guarded(system,'table',action='relation',target_unit_id='table-note',target_fingerprint=digest(get(system,'table-note')),role='notes',note='Original note applies to the complete table'))
    view=browser_state(s,'unit',did,'row')['effective']
    assert view['fields']['notes']=='Fish farms shall keep records.'
    assert view['related_content'][0]['inherited_from_table']=='table'
    with pytest.raises(ValueError,match='complete_table'):
        s.decision(guarded(system,'row',action='relation',target_unit_id='table-note',target_fingerprint=digest(get(system,'table-note')),role='notes',mode='detach',note='Cannot silently detach an inherited table note'))
    decide(system,'accept_content','table-note');decide(system,'accept_content','table');decide(system,'accept_content','row');decide(system,'classify','row',classification='requirement')
    assert current(system)['published']['row']['fields']['notes']=='Fish farms shall keep records.'
    decide(system,'correct','table-note',fields={'body':'Corrected table-wide original note.'},note='Original note corrected')
    assert 'row' not in current(system)['published']
    assert browser_state(s,'unit',did,'row')['effective']['fields']['notes']=='Corrected table-wide original note.'
