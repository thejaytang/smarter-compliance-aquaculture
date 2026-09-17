from copy import deepcopy
import json
import pytest

from pdf_extraction.contracts.hashing import digest
from pdf_extraction.review.browser_view import browser_state
from pdf_extraction.review.effective import table_view
from .test_two_stage_workflow import system,current,decide
from .test_pdf_repairs import table_units,get
from .test_review_rows import guarded
from .test_table_rows import row_request


def setup(system):
    s,did=system;t,row=table_units();raw=json.loads(t['original']['fields']['body'])
    glyphs=deepcopy(raw['cells'])
    for c in glyphs:c.update(id='artifact-'+c['id'],content={'resolved_text':'|'})
    for c in raw['cells']:c['row']=1
    raw.update(row_count=2,cells=glyphs+raw['cells']);t['original']['fields']['body']=json.dumps(raw)
    ghost=deepcopy(row);ghost['id']='artifact-row';ghost['original']['fields']={'body':'| |'}
    for ref in ghost['original']['references']:ref['locator']='artifact-'+ref['locator']
    s.install(did,[t,row,ghost],[])
    return s,did


def removal(system):
    return row_request(system,{'mode':'exclude_absent','row':0,'confirmed_absent':True,
        'row_fingerprints':{uid:digest(get(system,uid)) for uid in ('row','artifact-row')}})


def test_absent_row_retains_originals_invalidates_output_and_restores(system,tmp_path):
    s,did=setup(system);originals={uid:deepcopy(get(system,uid)['original']) for uid in ('table','row','artifact-row')}
    for uid in ('table','row','artifact-row'):decide(system,'accept_content',uid)
    decide(system,'classify','row',classification='requirement')
    assert 'row' in current(system)['published']
    r=removal(system);receipt=s.decision(r);assert s.decision(r)==receipt
    table=get(system,'table');view=browser_state(s,'unit',did,'table')
    assert view['effective']['table']['row_count']==1
    assert all(not c['id'].startswith('artifact-') and c['row']==0 for c in table_view(table)['cells'])
    assert get(system,'row')['table_row_binding']==0
    assert get(system,'artifact-row')['superseded_by']=='table'
    assert 'row' not in current(system)['published']
    assert len(view['table_context']['row_exclusions'])==1
    assert {c['content']['resolved_text'] for c in table['table_row_exclusions'][0]['cells']}=={'|'}
    for uid,original in originals.items():assert get(system,uid)['original']==original
    for uid in ('table','row'):decide(system,'accept_content',uid)
    decide(system,'classify','row',classification='requirement')
    assert current(system)['published']['row']['fields']['criteria']=='≥ 2 highly abundant taxa'
    from .test_requirement_workbook import export
    _,book,_=export(system,tmp_path)
    assert any('≥ 2 highly abundant taxa' in str(c.value) for row in book['PA001'] for c in row);book.close()
    s.decision(guarded(system,'table',action='restore',restore_request_id=r['request_id'],note='Undo this isolated removal'))
    assert table_view(get(system,'table'))['row_count']==2
    assert not get(system,'artifact-row').get('superseded_by')
    assert get(system,'row').get('table_row_binding') is None
    assert 'row' not in current(system)['published']


@pytest.mark.parametrize('change,error',[
    (lambda r:r['row_change'].pop('confirmed_absent'),'confirm_row_absent'),
    (lambda r:r['row_change']['row_fingerprints'].update(row='stale'),'stale_table_item'),
    (lambda r:r.update(target_fingerprint='stale'),'stale_table_version'),
])
def test_invalid_absent_row_request_is_atomic(system,change,error):
    s,did=setup(system);r=removal(system);change(r);before=current(system)
    with pytest.raises(ValueError,match=error):s.decision(r)
    assert current(system)==before


def test_related_content_and_unsubmitted_work_are_not_discarded(system):
    s,did=setup(system)
    s.decision(guarded(system,'clause',action='relation',target_unit_id='artifact-row',
        target_fingerprint=digest(get(system,'artifact-row')),role='reference',note='Preserve this existing reference'))
    before=current(system)
    with pytest.raises(ValueError,match='incoming_row_relationship'):s.decision(removal(system))
    assert current(system)==before
    s.decision(guarded(system,'clause',action='relation',target_unit_id='artifact-row',
        target_fingerprint=digest(get(system,'artifact-row')),role='reference',mode='detach',note='Explicitly correct the mistaken reference'))
    decide(system,'draft','row',draft={'body':'An unfinished independent edit'})
    with pytest.raises(ValueError,match='unsubmitted_draft'):s.decision(removal(system))


def test_shared_cells_require_an_explicit_boundary_repair(system):
    s,did=setup(system)
    with s.transaction() as db:
        d=s._load(db,did);t=next(u for u in d['units'] if u['id']=='table');raw=json.loads(t['original']['fields']['body'])
        raw['cells'][0]['row_span']=2;t['original']['fields']['body']=json.dumps(raw);s._save(db,d)
    before=current(system)
    with pytest.raises(ValueError,match='shared_cell_boundaries'):s.decision(removal(system))
    assert current(system)==before


def test_absent_row_refreshes_cross_page_view_and_reopens_later_judgment(system):
    from .test_table_assembly import setup as cross_page,join_request,assembly
    s,did=cross_page(system)
    with s.transaction() as db:
        d=s._load(db,did);owner=next(u for u in d['units'] if u['id']=='table')
        raw=json.loads(owner['original']['fields']['body']);artifacts=[]
        for c in raw['cells']:
            c['row']+=1
            if c.get('is_header'):
                ghost=deepcopy(c);ghost.update(id='artifact-'+c['id'],row=0,is_header=False,content={'resolved_text':'|'});artifacts.append(ghost)
        raw['cells']+=artifacts;raw['row_count']=3;owner['original']['fields']['body']=json.dumps(raw)
        owner['table_row_dispositions']={'0':{'mode':'table_only'},'1':{'mode':'table_only'}};s._save(db,d)
    s.decision(join_request(system));aid=assembly(system)['id']
    for uid in ('table','second','row','r2',aid):decide(system,'accept_content',uid)
    decide(system,'classify','r2',classification='requirement');assert 'r2' in current(system)['published']
    s.decision(row_request(system,{'mode':'exclude_absent','row':0,'confirmed_absent':True,'row_fingerprints':{'row':digest(get(system,'row'))}}))
    v=browser_state(s,'unit',did,aid)['effective']
    assert v['table']['row_count']==3
    assert [c['text'] for c in v['table_assembly']['column_headers']]==['INDICATOR','REQUIREMENT']
    assert not get(system,aid)['content_human'] and 'r2' not in current(system)['published']
