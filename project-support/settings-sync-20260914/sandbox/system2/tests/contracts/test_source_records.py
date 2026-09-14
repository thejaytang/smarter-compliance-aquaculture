"""Mapping fidelity, inventory, audit-column isolation and immutable provenance."""
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from openpyxl import Workbook
import pytest
from pdf_extraction.contracts.excel import LocalExcelSource
from pdf_extraction.contracts.source_records import SourceRecords,GLOBALGAP_HEADERS
from pdf_extraction.formats.excel import parse_excel
from pdf_extraction.domains.requirements.source_records import map_source_records
from pdf_extraction.verification.source_records import verify_source_records
from pdf_extraction.orchestration.source_records import emit_records
from pdf_extraction.orchestration.source_batch import run_item
from tests.contracts.test_html_v2 import doc
from tests.contracts.test_source_intake import source,store


def xlsx_document(*, duplicate=False, formula_body=False, shifted=False):
    w=Workbook();s=w.active;s.title='Checklist'
    columns=list(GLOBALGAP_HEADERS)+['Answer Confirmation','Justification','Due date']
    if shifted:columns=['Unused']+list(reversed(columns))
    s.append(columns)
    values={'Standard':'IFA','Version':'IFA v6 Smart','Product Category':'AQ','Principle':'AQ-Smart 01.01.01',
        'Section':'AQ 01 CONTEXT','Description':'=1+1' if formula_body else 'The producer keeps records.',
        'Criteria':'Records shall cover all units.','NIG':'','Level':'Major Must',
        'Answer Confirmation':'Yes','Justification':'OPERATOR COMMENT','Due date':'2099-01-01'}
    s.append([values.get(h) for h in columns]);s.append([values.get(h) if h!='Principle' or duplicate else 'AQ-Smart 01.01.02' for h in columns])
    stream=BytesIO();w.save(stream);raw=stream.getvalue()
    return parse_excel(raw,LocalExcelSource(relative_path='sample.xlsx',content_hash=sha256(raw).hexdigest()))


HTML=b'''<html><div id="documentMeta">Law</div><div id="documentBody"><div class="kapittel"><h2>Chapter 1</h2><div class="paragraf" id="c1"><h3><span class="paragrafValue">1.</span><span class="paragrafTittel">Scope</span></h3>Before<p>Operators <b>shall</b> keep records.</p>Between<table class="fotnote"><tr><td>Note one.</td></tr></table><p>After note.</p>After<a class="share-paragraf">Share this provision</a></div><div class="paragraf" id="c2"><h3><span class="paragrafValue">2.</span><span class="paragrafTittel">Action</span></h3><p>Second clause.</p></div></div></div></html>'''


def mapping(d):return map_source_records(d,'a'*64,'b'*64)
def verify(d,m):return verify_source_records(d,m,'a'*64,'b'*64)


@pytest.mark.parametrize('shifted',[False,True])
def test_excel_labels_drive_mapping_and_audit_data_is_not_normative(shifted):
    d=xlsx_document(shifted=shifted);before=d.model_dump_json();m=mapping(d)
    assert len(m.records)==2 and verify(d,m)['status']=='passed'
    assert m.records[0].fields['body'][0].text=='The producer keeps records.'
    assert m.records[0].fields['criteria'][0].text=='Records shall cover all units.'
    assert 'OPERATOR COMMENT' not in json.dumps([r.model_dump() for r in m.records])
    assert any(r.reference.locator.endswith('#L2') for r in m.residual) if not shifted else m.residual
    assert d.model_dump_json()==before


def test_html_text_order_notes_context_and_controls():
    d=doc(HTML);m=mapping(d);assert verify(d,m)['status']=='passed'
    r=m.records[0]
    assert [v.text for v in r.fields['body']]==['Before','Operators shall keep records.','Between','After note.','After']
    assert r.fields['notes'][0].text=='Note one.' and r.fields['context'][0].text=='Chapter 1'
    assert all('Share' not in (f.text or '') for r in m.records for values in r.fields.values() for f in values)
    assert any(r.reason=='source_control' for r in m.residual)


@pytest.mark.parametrize('case',['drop_record','mutate_text','drop_body','swap_fields','wrong_locator','drop_residual','wrong_hash','wrong_count','drop_issue','swap_records'])
def test_mapper_verification_detects_corruption(case):
    d=xlsx_document(duplicate=True);value=mapping(d).model_dump()
    if case=='drop_record':value['records'].pop()
    elif case=='mutate_text':value['records'][0]['fields']['body'][0]['text']='Invented'
    elif case=='drop_body':value['records'][0]['fields']['body']=[]
    elif case=='swap_fields':value['records'][0]['fields']['criteria']=value['records'][0]['fields']['body']
    elif case=='wrong_locator':value['records'][0]['fields']['body'][0]['references'][0]['locator']='wrong'
    elif case=='drop_residual':value['residual'].pop()
    elif case=='wrong_hash':value['canonical_sha256']='c'*64
    elif case=='wrong_count':value['mapped_reference_count']=0
    elif case=='drop_issue':value['records'][0]['issues']=[]
    else:value['records'].reverse()
    assert verify(d,SourceRecords(**value))['status']=='failed'


def test_formula_and_duplicate_identifiers_keep_review():
    d=xlsx_document(duplicate=True,formula_body=True);m=mapping(d)
    assert len(m.records)==2 and verify(d,m)['status']=='passed'
    assert m.records[0].fields['body'][0].text is None
    assert {'duplicate_source_identifier','nonliteral_field:body','missing_or_empty_field:body'}<=set(m.records[0].issues)


def test_html_missing_identifiers_are_not_dropped():
    raw=HTML.replace(b'<span class="paragrafValue">1.</span>',b'')
    d=doc(raw);m=mapping(d);assert len(m.records)==2 and verify(d,m)['status']=='passed'
    assert 'missing_or_ambiguous_field:identifier' in m.records[0].issues


def test_unsupported_template_keeps_source_residual():
    raw=b'<html><main><div class="sidebar--filters">Filter</div><h1>Standard</h1><p>Source</p></main></html>'
    d=doc(raw);m=mapping(d)
    assert m.status=='not_supported' and m.residual and verify(d,m)['status']=='passed'


def test_new_batch_emits_mapping_and_refuses_mismatched_proof(tmp_path):
    s=source(HTML);store(tmp_path/'sources',s,HTML)
    r=run_item(s,tmp_path/'sources',tmp_path/'run',{'template':'auto'})
    assert r.status=='review_required'
    m=json.loads((tmp_path/'run/source-records.json').read_text());assert len(m['records'])==2
    original=(tmp_path/'run/canonical.json').read_bytes()
    proof=tmp_path/'run/verification.json';value=json.loads(proof.read_text());value['canonical_artifact_sha256']='0'*64;proof.write_text(json.dumps(value))
    target=tmp_path/'invalid';target.mkdir()
    with pytest.raises(ValueError,match='matching_passed'):emit_records(tmp_path/'run/canonical.json',proof,target)
    assert not list(target.iterdir()) and (tmp_path/'run/canonical.json').read_bytes()==original


def test_schema_matches_published():
    assert json.loads(Path('config/schemas/source-records.schema.json').read_text())==SourceRecords.model_json_schema()


def test_nested_clause_and_inline_notes_do_not_leak_into_parent():
    raw=HTML.replace(b'Operators <b>shall</b> keep records.',b'Operators <b>shall</b> keep <span class="fotnote">Inline note.</span>records.').replace(
        b'<p>After note.</p>',b'<div class="paragraf" id="nested"><h4><span class="paragrafValue">1a.</span><span class="paragrafTittel">Nested</span></h4><p>Nested body.</p></div><p>After note.</p>')
    d=doc(raw);m=mapping(d)
    assert len(m.records)==3 and verify(d,m)['status']=='passed'
    assert all('Nested body' not in (f.text or '') and 'Inline note' not in (f.text or '') for f in m.records[0].fields['body'])
    assert any(f.text=='Inline note.' for f in m.records[0].fields['notes'])


def test_field_reference_reorder_and_hidden_footnotes_fail():
    d=doc(HTML);value=mapping(d).model_dump();value['records'][0]['fields']['body'].reverse()
    assert verify(d,SourceRecords(**value))['status']=='failed'
    value=mapping(d).model_dump();value['records'][0]['fields']['notes']=[]
    assert verify(d,SourceRecords(**value))['status']=='failed'


def test_batch_mapping_failure_propagates_without_losing_canonical(tmp_path,monkeypatch):
    import pdf_extraction.orchestration.source_records as module
    def fail(*args):raise ValueError('simulated_mapping_failure')
    monkeypatch.setattr(module,'emit_records',fail)
    s=source(HTML);store(tmp_path/'sources',s,HTML)
    result=run_item(s,tmp_path/'sources',tmp_path/'run',{'template':'auto'})
    assert result.status=='failed' and result.canonical_path=='canonical.json'
    assert any('simulated_mapping_failure' in r for r in result.reason_codes)
    assert (tmp_path/'run/canonical.json').exists()
