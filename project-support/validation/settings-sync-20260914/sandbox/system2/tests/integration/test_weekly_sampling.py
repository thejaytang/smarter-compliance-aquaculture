"""Seeded engineering monitoring cases; no independent accuracy claims."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import pytest
from pypdf import PdfWriter
from pdf_extraction.review.workflow import Workflow
from pdf_extraction.review import original_sampling as original, weekly_sampling as qa
from .test_two_stage_workflow import request, unit, current, decide

MONDAY=datetime(2026,9,7,8,tzinfo=timezone.utc)


@pytest.fixture
def sample(tmp_path):
    path=tmp_path/'original.pdf';writer=PdfWriter()
    for _ in range(22):writer.add_blank_page(width=200,height=300)
    writer.write(path)
    store=Workflow(tmp_path/'workflow')
    source=dict(source_id='QA001',snapshot_id='QA001-001',content_hash=sha256(path.read_bytes()).hexdigest(),
        relative_path=path.name,selection_status='INCLUDE',file_format='pdf')
    did=store.enqueue([source],request())['documents'][0]
    units=[unit('coverage','coverage')]
    for i in range(6):
        u=unit('clause'+str(i));u['original']['references']=[{'page_index':0}]
        units.append(u)
    store.install(did,units,[],complete=False,total_pages=22,pages=[0])
    system=store,did
    for u in current(system)['units']:
        decide(system,'accept_content',u['id'])
    for i in range(6):decide(system,'classify','clause'+str(i),classification='requirement' if i<4 else 'non_requirement',note='Seeded classification')
    qa.create_due(store,tmp_path,enabled=True,now=MONDAY)
    return system,tmp_path


def item(sample,stage,unmapped=False):
    store=sample[0][0]
    for summary in next(b for b in qa.read(store)['batches'] if b['stage']==stage)['items']:
        detail=qa.read(store,summary['id'])
        if not unmapped or not detail.get('extracted'):return detail


def inspect(sample,identity,**changes):
    store=sample[0][0];detail=qa.read(store,identity)
    return qa.decide(store,request(item_id=identity,guard=detail['guard'],result_guard=detail['result_guard'],
        note='Seeded engineering original comparison.',**changes))


def test_original_pool_independent_of_output_and_b_covers_both_strata(sample):
    system,path=sample;store=system[0];before=qa.read(store)
    a,b=before['batches']
    assert a['stage']=='A' and a['requested']==a['sampled']==20 and a['population']==22
    assert b['sampled']==5 and {i['classification'] for i in b['items']}=={'requirement','non_requirement'}
    assert not a['complete'] and a['agreement'] is None
    raw=original.catalog(path/'original.pdf',current(system)['source']['content_hash'])
    assert len(raw['scopes'])==22 and item(sample,'A',True)['extracted']==[]
    assert qa.create_due(store,path,enabled=True,now=MONDAY)['status']=='already_created'
    assert qa.read(Workflow(store.root))==before


def test_read_and_disabled_tick_do_not_create_tables(tmp_path):
    store=Workflow(tmp_path)
    assert not qa.read(store)['batches']
    assert qa.create_due(store,tmp_path)['status']=='disabled'
    with store.connect() as db:assert not qa.exists(db)


def test_missing_region_finding_stays_pending_through_repair_until_recheck(sample):
    system,_=sample;store=system[0];detail=item(sample,'A',True);uid=detail['id']
    original_facts={u['id']:deepcopy(u['original']) for u in current(system)['units']}
    inspect(sample,uid,action='inspect',verdict='INCORRECT')
    found=qa.read(store,uid);coverage=found['repair_unit_id'];code='weekly_qa:'+uid
    assert found['status']=='finding_open'
    with pytest.raises(ValueError,match='repair_and_recheck'):inspect(sample,uid,action='resolve')
    decide(system,'supplement',coverage,fields={'body':'Seeded missing text from original.'},
        locator='page '+str(detail['scope']['page_index']+1),note='Seeded missing-region repair')
    added=next(u for u in current(system)['units'] if u['id'].startswith('manual:'))
    decide(system,'resolve_content',coverage,resolved_issues=[code],note='Compared entire original page and added missing content')
    with pytest.raises(ValueError,match='repair_and_recheck'):inspect(sample,uid,action='resolve')
    decide(system,'accept_content',added['id'])
    assert qa.read(store,uid)['status']=='finding_open'
    inspect(sample,uid,action='resolve')
    assert qa.read(store,uid)['status']=='complete' and qa.read(store,uid)['verdict']=='INCORRECT'
    assert len(qa.read(store,uid)['history'])==2
    assert all(u['original']==original_facts[u['id']] for u in current(system)['units'] if u['id'] in original_facts)


def test_b_finding_reclassification_and_receipt_guards(sample):
    system,_=sample;store=system[0];detail=item(sample,'B');uid=detail['id'];target=detail['unit_id']
    r=request(item_id=uid,guard=detail['guard'],result_guard=detail['result_guard'],action='inspect',verdict='INCORRECT',note='Seeded false positive/negative')
    receipt=qa.decide(store,r);assert qa.decide(store,r)==receipt
    with pytest.raises(ValueError,match='stale_weekly'):qa.decide(store,dict(r,request_id=request()['request_id']))
    u=next(u for u in current(system)['units'] if u['id']==target)
    assert u['content_status']=='human_accepted' and u['requirement_status']=='pending'
    with pytest.raises(ValueError,match='relationship_issues'):decide(system,'classify',target,classification='non_requirement',note='New judgment')
    decide(system,'classify',target,classification='non_requirement',note='Rechecked original: contextual statement',resolved_requirement_issues=['weekly_qa:'+uid])
    assert qa.read(store,uid)['status']=='finding_open'
    inspect(sample,uid,action='resolve')
    assert qa.read(store,uid)['verdict']=='INCORRECT'


def test_unverified_shortfall_and_source_change_remain_visible(sample):
    system,path=sample;store=system[0];detail=item(sample,'A');uid=detail['id']
    inspect(sample,uid,action='inspect',verdict='UNVERIFIED')
    assert qa.read(store,uid)['status']=='unverified'
    store.reconcile_sources({})
    with pytest.raises(ValueError,match='source_changed'):inspect(sample,uid,action='inspect',verdict='CORRECT')
    qa.create_due(store,path,enabled=True,now=datetime(2026,9,14,8,tzinfo=timezone.utc))
    a,b=qa.read(store)['batches'][:2]
    assert a['shortfall']==20 and b['shortfall']==5 and len(b['missing_strata'])==2
    assert not a['complete'] and b['agreement'] is None


def test_catalog_html_and_xlsx_are_original_positioned(tmp_path):
    from openpyxl import Workbook
    path=tmp_path/'raw.html';path.write_text('<html><body><p>Kept</p><p>Entirely omitted</p><img src="x.png"></body></html>')
    scopes=original.catalog(path,sha256(path.read_bytes()).hexdigest())['scopes']
    assert 'Entirely omitted' in scopes[0]['original_text'] and scopes[1]['visual_only']
    assert original.matches(scopes[0],[{'locator':'html:nth-of-type(1) > body:nth-of-type(1) > p:nth-of-type(2)'}])
    path=tmp_path/'raw.xlsx';book=Workbook();book.active['A1']='Kept';book.active['D20']='Omitted cell';book.save(path);book.close()
    scopes=original.catalog(path,sha256(path.read_bytes()).hexdigest())['scopes']
    assert [r['locator'] for r in scopes[0]['references']]==['xl/worksheets/sheet1.xml#A1','xl/worksheets/sheet1.xml#D20']


def test_week_boundary_and_naive_clock():
    assert qa.week_of(datetime(2027,1,3,20,tzinfo=timezone.utc),'Europe/Oslo')=='2026-12-28'
    with pytest.raises(ValueError,match='timezone'):qa.week_of(datetime(2026,9,7),'Europe/Oslo')


def test_frozen_items_and_histories_export_from_same_snapshot(sample,tmp_path):
    from .test_requirement_workbook import export
    system,_=sample;d=item(sample,'A',True)
    inspect(sample,d['id'],action='inspect',verdict='INCORRECT')
    result,book,path=export(system,tmp_path)
    rows=list(book['Weekly checks'].iter_rows(min_row=5,values_only=True))
    assert any(r[12]==d['id'] and r[5]=='finding_open' and r[6]=='INCORRECT' for r in rows)
    assert any(r[2]=='Batch' and r[1]=='A' and r[8:10]==(20,20) for r in rows)
    assert result['event_cursor']==system[0].feed()['cursor']
    book.close()


def test_concurrent_current_week_creation_is_single_batch_pair(sample):
    from concurrent.futures import ThreadPoolExecutor
    system,path=sample;store=system[0]
    later=datetime(2026,9,14,8,tzinfo=timezone.utc)
    with ThreadPoolExecutor(2) as pool:
        outcomes=list(pool.map(lambda _:qa.create_due(store,path,enabled=True,now=later),range(2)))
    assert sorted(r['status'] for r in outcomes)==['already_created','created']
    with store.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM sampling_batches WHERE week=?',('2026-09-14',)).fetchone()[0]==2
        assert db.execute('SELECT COUNT(*) FROM sampling_items WHERE week=?',('2026-09-14',)).fetchone()[0]==25
