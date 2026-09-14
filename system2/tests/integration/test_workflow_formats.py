from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
import uuid
import json
import pytest

from pdf_extraction.orchestration.workflow import Runner,content_units
from pdf_extraction.orchestration.source_batch import run_item
from tests.contracts.test_source_intake import HTML,source,row,store


def req(**values):
    return dict(request_id=str(uuid.uuid4()),actor='Ana Jokic',**values)


def fake_runner(tmp_path,monkeypatch,snapshot,raw):
    root=tmp_path/'sources';store(root,snapshot,raw)
    r=Runner(tmp_path/'runtime',tmp_path/'system1')
    handoff=SimpleNamespace(records=[row(snapshot)],registry_sha256='a'*64,source_root=root,assert_current=lambda:None)
    monkeypatch.setattr(r,'handoff',lambda:handoff)
    return r


def test_html_two_gate_intake_without_external_model(tmp_path,monkeypatch):
    r=fake_runner(tmp_path,monkeypatch,source(),HTML)
    identity=r.start(req(source_ids=['PA001']))['documents'][0]
    assert r.tick()['status']=='processed'
    doc=r.store.snapshot()['documents'][0]
    assert doc['id']==identity and doc['units']
    assert not doc['published']
    assert all(u['content_status']=='pending' for u in doc['units'])
    assert r.tick()['status']=='idle'


def test_reconcile_publishes_source_only_change_without_rewriting_review_state(tmp_path,monkeypatch):
    r=fake_runner(tmp_path,monkeypatch,source(),HTML)
    r.start(req(source_ids=['PA001']));r.tick()
    before=r.store.snapshot()
    with r.store.connect() as db: events=list(db.execute('SELECT * FROM events'))
    handoff=r.handoff();handoff.registry_sha256='b'*64
    r.reconcile()
    marker=r.root/'source-version.json'
    assert json.loads(marker.read_text())['registry_sha256']=='b'*64
    assert r.store.snapshot()==before
    with r.store.connect() as db: assert [tuple(x) for x in db.execute('SELECT * FROM events')]==[tuple(x) for x in events]
    def unavailable():raise ValueError('source check unavailable')
    monkeypatch.setattr(r,'handoff',unavailable)
    with pytest.raises(ValueError,match='unavailable'):r.reconcile()
    assert json.loads(marker.read_text())['status']=='unknown'
    assert r.store.snapshot()==before


def test_explicit_conversion_preserves_original_and_records_lineage(tmp_path,monkeypatch):
    raw=bytes.fromhex('d0cf11e0a1b11ae1')+b'legacy fixture'
    snapshot=source(raw,'xls');r=fake_runner(tmp_path,monkeypatch,snapshot,raw)
    identity=r.start(req(source_ids=['PA001']))['documents'][0]
    r.tick();doc=r.store.snapshot()['documents'][0]
    assert doc['state']=='conversion_required'
    stage=tmp_path/'staging';stage.mkdir();copy=stage/'copy.html';copy.write_bytes(HTML)
    request=req(document_id=identity,revision=doc['revision'],staged_path=str(copy),staged_root=str(stage),
                staged_hash=sha256(HTML).hexdigest(),complete=True,method='Human export',note='Compared full source and copy')
    assert r.conversion(request)['status']=='applied'
    assert r.conversion(request)['status']=='applied'
    assert r.tick()['status']=='processed'
    doc=r.store.snapshot()['documents'][0]
    assert doc['source']['content_hash']==sha256(raw).hexdigest()
    assert doc['conversion']['parsing_copy_of']['original_sha256']==sha256(raw).hexdigest()
    assert (tmp_path/'sources'/snapshot.relative_path).read_bytes()==raw
    assert doc['units'] and not doc['published']


def test_xlsx_keeps_unmapped_cells_reviewable(tmp_path):
    from openpyxl import Workbook
    book=Workbook();sheet=book.active
    sheet.append(['Clause','Text']);sheet.append(['1','Fish farms shall retain records.'])
    p=tmp_path/'original.xlsx';book.save(p);raw=p.read_bytes()
    s=source(raw,'xlsx');root=tmp_path/'sources';store(root,s,raw)
    out=tmp_path/'result';result=run_item(s,root,out,{})
    assert result.canonical_path
    units,refs=content_units(out,result,s)
    assert units and refs
    assert any('Fish farms shall retain records.' in str(u['original']) for u in units)


def test_disabled_assistance_preserves_offline_review(tmp_path,monkeypatch):
    r=fake_runner(tmp_path,monkeypatch,source(),HTML)
    identity=r.start(req(source_ids=['PA001']))['documents'][0];r.tick()
    doc=r.store.snapshot()['documents'][0]
    result=r.suggest(req(document_id=identity,unit_id=doc['units'][0]['id'],revision=doc['revision']))
    assert result['mode']=='NO_API' and result['suggestions']==[]
    assert not r.store.snapshot()['documents'][0]['published']


def test_pdf_table_row_projection_keeps_columns_and_spans(tmp_path):
    import json
    from pdf_extraction.contracts.source import ParseResult
    s=source(b'%PDF-1.7','pdf')
    segment={'page_index':0,'bbox':{'x0':1,'y0':2,'x1':3,'y1':4}}
    cells=[dict(id='a',row=0,column=0,row_span=1,column_span=1,page_index=0,bbox=segment['bbox'],content={'native_text':'2.1.3 Number of taxa'}),
           dict(id='b',row=0,column=1,row_span=1,column_span=1,page_index=0,bbox=segment['bbox'],content={'native_text':'≥ 2 taxa'})]
    canonical={'blocks':{'table':{'type':'table','segments':[segment],'table':{'cells':cells},'quality':{'issues':[]}}}}
    (tmp_path/'canonical.json').write_text(json.dumps(canonical))
    result=ParseResult(source=s,format='pdf',status='review_required',canonical_path='canonical.json')
    units,_=content_units(tmp_path,result,s)
    item=next(u for u in units if u['kind']=='standard_indicator')
    assert item['original']['fields']=={'identifier':'2.1.3','body':'Number of taxa','criteria':'≥ 2 taxa'}
    assert len(item['dependencies'])==3 and len(item['original']['references'])==2
    assert 'coverage:pdf-page:0' in item['dependencies']
    assert sum(d.startswith('pdf:') for d in item['dependencies'])==1
