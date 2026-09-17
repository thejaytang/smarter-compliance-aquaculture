from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest

from pdf_extraction.review.source_verification import verify_page, comparison_input
from pdf_extraction.verification.source_comparison import compare
from pdf_extraction.verification.pdf_original import acquire
from .test_two_stage_workflow import system, current, decide, request, unit


def page(text='Fish farms shall not exceed 5 kg.', **extra):
    return dict(page_index=0, width=600, height=800, source_sha256='a'*64,
                lines=[dict(text=text, bbox=[20,20,180,40], engine='poppler')],
                unverified=[], evidence=[], **extra)


def record(text, bounds=(20,20,180,40)):
    return dict(id='clause', unit_id='clause', text=text,
                references=[dict(page_index=0, bbox=list(bounds))])


def test_unmapped_and_broad_box_cannot_explain_missing_text():
    assert compare(page(), [])['findings'][0]['code']=='source_region_unmapped'
    result=compare(page(), [record('Fish farms shall exceed 9 kg.', (0,0,600,800))])
    assert result['findings'][0]['code']=='source_critical_token_difference'
    assert {'not','5'} <= set(result['findings'][0]['missing_tokens'])
    assert compare(page(), [record('Fish farms shall not exceed 5 kg.')])['findings']==[]


def test_text_elsewhere_does_not_hide_omission_and_cells_are_not_combined():
    assert compare(page(), [record('Fish farms shall not exceed 5 kg.', (20,300,180,320))])['findings']
    records=[record('Fish farms shall'), dict(record('not exceed 5 kg.'),id='other')]
    assert compare(page(),records)['findings']


def test_raster_unknowns_are_not_excused_by_whole_page_illustration():
    p=page(unrecognized_regions=[[10,100,300,200]])
    r=compare(p,[record(p['lines'][0]['text'])])
    assert r['findings'][0]['code']=='source_visual_region_unverified'
    assert r['confidence'] is None


def test_synthetic_native_and_scan_acquisition():
    from system2.support.paths import LEGACY_ROOT
    root=LEGACY_ROOT
    for name,engines in [('born-digital-multicolumn.pdf',('docling-parse',)),('scanned-critical.pdf',('tesseract',))]:
        p=acquire(root/'gold/pdfs'/name,0,parser_engines=engines)
        assert p['lines'] and p['evidence'] and p['width']>0
        findings=compare(p,[])['findings']
        assert any(f['code']=='source_region_unmapped' for f in findings)
        if 'tesseract' in engines:
            assert any(u['code']=='shared_extraction_engine' for u in p['unverified'])


def prepare(system,tmp_path,monkeypatch):
    s,did=system;source=tmp_path/'original.pdf';source.write_bytes(b'%PDF-test')
    h=sha256(source.read_bytes()).hexdigest()
    with s.transaction() as db:
        d=s._load(db,did);d['source'].update(file_format='pdf',content_hash=h)
        d['total_pages']=1;d['processed_pages']=[0]
        u=next(u for u in d['units'] if u['id']=='clause')
        # The synthetic original observation contains the body only. The
        # generic fixture's internal label 'clause' is not printed source text.
        u['original']['fields']['identifier']=''
        u['original']['references']=[{'page_index':0,'bbox':[0,0,600,800]}]
        s._save(db,d)
    monkeypatch.setattr('pdf_extraction.verification.pdf_original.acquire',lambda *a,**kw:dict(page(),source_sha256=h))
    def run(**overrides):
        d=current(system)
        return verify_page(s,source,request(document_id=did,revision=d['revision'],source_sha256=h,page_index=0,**overrides))
    return s,did,source,h,run


def test_find_repair_recheck_history_export_and_stale_protection(system,tmp_path,monkeypatch):
    s,did,source,h,run=prepare(system,tmp_path,monkeypatch)
    original=deepcopy(current(system)['units'][1]['original'])
    before=current(system)['published']
    result=run();cid=result['unit_id']
    artifact=result['report']['evidence_artifact']
    assert sha256((s.root/artifact['path']).read_bytes()).hexdigest()==artifact['sha256']
    assert before and not current(system)['published']
    d=current(system);coverage=next(u for u in d['units'] if u['id']==cid)
    assert coverage['blockers'] and not coverage['content_human']
    decide(system,'correct',fields={'body':'Fish farms shall not exceed 5 kg.'},note='Isolated original check')
    cov=next(u for u in current(system)['units'] if u['id']==cid)
    assert cov['source_verification']['stale']
    with pytest.raises(ValueError,match='rerun_original'):
        decide(system,'resolve_content',cid,resolved_issues=['source_verification_stale'],note='Cannot bypass')
    second=run();assert second['report']['findings']==[]
    decide(system,'accept_content',cid)
    decide(system,'accept_content')
    decide(system,'classify',classification='requirement')
    assert current(system)['published']['clause']['fields']['body']=='Fish farms shall not exceed 5 kg.'
    assert next(u for u in current(system)['units'] if u['id']=='clause')['original']==original
    assert len([e for e in s.feed()['events'] if e['kind']=='source_verification'])==2
    from .test_requirement_workbook import export
    _,wb,_=export(system,tmp_path)
    assert any(c.value=='Fish farms shall not exceed 5 kg.' for row in wb['PA001'] for c in row)
    wb.close()


def test_replay_and_stale_results_are_atomic(system,tmp_path,monkeypatch):
    s,did,source,h,run=prepare(system,tmp_path,monkeypatch)
    req=request(document_id=did,revision=current(system)['revision'],source_sha256=h,page_index=0)
    first=verify_page(s,source,req)
    assert verify_page(s,source,req)==first
    req=request(document_id=did,revision=current(system)['revision'],source_sha256=h,page_index=0)
    def concurrent(*a,**kw):
        decide(system,'correct',fields={'body':'Concurrent edit'},note='Another writer')
        return dict(page(),source_sha256=h)
    monkeypatch.setattr('pdf_extraction.verification.pdf_original.acquire',concurrent)
    with pytest.raises(ValueError,match='verification_result_stale'):verify_page(s,source,req)
    assert len([e for e in s.feed()['events'] if e['kind']=='source_verification'])==1


def test_empty_page_can_be_checked_without_extracted_items(system,tmp_path,monkeypatch):
    s,did,source,h,run=prepare(system,tmp_path,monkeypatch)
    with s.transaction() as db:
        d=s._load(db,did)
        d['units']=[u for u in d['units'] if u['kind']=='coverage']
        s._recompute(db,d,s.policy(db));s._save(db,d)
    assert run()['report']['findings'][0]['code']=='source_region_unmapped'


@pytest.mark.parametrize(('original','output'), [
    ('Version 1.5', 'Version 5.1'),
    ('Sulphide ≤ 1,500 μMol /L', 'Sulphide ≤ 1.500 μMol /L'),
    ('Index ≥ 15', 'Index ≥ −15'),
    ('Index ≥ 15', 'Index ≥ − 15'),
    ('Farms shall record temperature.', 'Farms shall not record temperature.'),
    ('Water shall flow from inlet to outlet.', 'Water shall flow from outlet to inlet.'),
])
def test_ordered_numbers_insertions_and_token_order_are_detected(original,output):
    result=compare(page(original),[record(output)])
    assert len(result['findings'])==1
    assert result['confidence'] is None and result['acceptance']=='not_assessed'
    finding=result['findings'][0]
    assert finding['bbox']==[20,20,180,40] and finding['output_ids']==['clause']
    assert finding['source_text']==original
    expected_severity='major' if original=='Water shall flow from inlet to outlet.' else 'critical'
    assert finding['severity']==expected_severity


def test_output_only_text_is_not_treated_as_supported():
    result=compare(page('Farms record temperature.'),[record('Farms record temperature daily.')])
    assert result['findings'][0]['extra_tokens']==['daily']
    assert result['findings'][0]['output_text']=='Farms record temperature daily.'
    assert result['findings'][0]['severity']=='major'


def test_multiline_record_and_normalized_unicode_do_not_add_false_alarms():
    p=page('Farms record water')
    p['lines'].append(dict(text='temperature daily.',bbox=[20,41,180,60],engine='poppler'))
    assert compare(p,[record('Farms record water temperature daily.',(20,20,180,60))])['findings']==[]
    assert compare(page('Index ≥ −15'),[record('Index ≥ -15')])['findings']==[]


def test_two_directions_do_not_duplicate_one_tokenization_issue():
    r=compare(page('Aquacul ture'),[record('Aquaculture')])
    assert len(r['findings'])==1
    assert r['findings'][0]['code']=='source_tokenization_conflict'
    assert r['findings'][0]['reverse_comparisons'][0]['code']=='output_tokenization_conflict'


def test_multi_page_record_declares_reverse_comparison_scope():
    r=record('Farms record water temperature.')
    r['references'].append(dict(page_index=1,bbox=[20,20,180,40]))
    result=compare(page('Farms record water'),[r])
    assert result['findings']==[]
    assert any(u['code']=='cross_page_output_text_not_partitioned' for u in result['unverified'])


def test_new_method_marks_previous_report_stale_without_erasing_history(system,tmp_path,monkeypatch):
    s,did,source,h,run=prepare(system,tmp_path,monkeypatch)
    first=run();before_events=s.feed()['events']
    from pdf_extraction.review.source_verification import refresh_staleness
    with s.transaction() as db:
        d=s._load(db,did)
        u=next(u for u in d['units'] if u['id']==first['unit_id'])
        u['source_verification']['method']='original-page-comparison/1'
        refresh_staleness(d)
        assert u['source_verification']['stale']
        assert 'source_verification_stale' in u['blockers']
        s._save(db,d)
    assert s.feed()['events']==before_events
    second=run()
    from pdf_extraction.verification.source_comparison import METHOD
    assert second['report']['method']==METHOD
    assert not second['report']['stale']


def test_unchanged_source_reconciliation_reopens_checks_from_an_old_method(system,tmp_path,monkeypatch):
    s,did,source,h,run=prepare(system,tmp_path,monkeypatch)
    decide(system,'correct',fields={'body':'Fish farms shall not exceed 5 kg.'},note='Engineering source control')
    check=run()
    decide(system,'accept_content',check['unit_id'])
    decide(system,'accept_content')
    decide(system,'classify',classification='requirement')
    before=current(system)
    assert before['published']
    history=deepcopy(before['history'])
    monkeypatch.setattr('pdf_extraction.review.source_verification.METHOD','original-page-comparison/next-test')
    s.reconcile_sources({'PA001':dict(before['source'])})
    after=current(system)
    assert not after['published']
    coverage=next(u for u in after['units'] if u['id']==check['unit_id'])
    assert coverage['source_verification']['stale']
    assert 'source_verification_stale' in coverage['blockers']
    assert after['revision']>before['revision']
    assert after['history']==history
    events=s.feed()['events']
    assert any(e['kind']=='source_verification_method_updated' for e in events)
    # A normal poll must neither repeat invalidation nor create duplicate events.
    s.reconcile_sources({'PA001':dict(before['source'])})
    assert current(system)==after
    assert s.feed()['events']==events


def test_ambiguous_column_scope_blocks_downstream_delivery(system,tmp_path,monkeypatch):
    s,did,source,h,run=prepare(system,tmp_path,monkeypatch)
    p=page('INDICATOR')
    p['source_sha256']=h
    p['lines'].append(dict(text='REQUIREMENT',bbox=[320,20,490,40],engine='poppler'))
    monkeypatch.setattr('pdf_extraction.verification.pdf_original.acquire',lambda *a,**kw:p)
    with s.transaction() as db:
        d=s._load(db,did)
        left=next(u for u in d['units'] if u['id']=='clause')
        left['original']['fields']['body']='REQUIREMENT'
        right=deepcopy(left);right['id']='right'
        right['original']['fields']['body']='INDICATOR'
        d['units'].append(right);s._save(db,d)
    result=run()
    assert result['report']['findings']==[]
    scope=next(u for u in result['report']['unverified'] if u['code']=='output_spatial_ownership_ambiguous')
    assert scope['unit_ids']==['clause','right']
    coverage=next(u for u in current(system)['units'] if u['id']==result['unit_id'])
    assert any(b.startswith('source_scope:') for b in coverage['blockers'])
    assert not current(system)['published']
    with pytest.raises(ValueError,match='content_gate'):
        decide(system,'classify',classification='requirement')
