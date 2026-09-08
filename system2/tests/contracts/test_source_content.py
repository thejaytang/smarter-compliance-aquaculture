"""V2 source fields, full content accounting and adversarial mapping checks."""
from pathlib import Path
import json
import pytest

from pdf_extraction.contracts.source_content import ContentRecords
from pdf_extraction.domains.requirements.source_content import map_content_records
from pdf_extraction.domains.requirements.source_records import map_source_records
from pdf_extraction.verification.source_records import verify_source_records
from tests.contracts.test_html_v2 import doc
from tests.contracts.test_source_records import xlsx_document

RAW = b'''<html><head><title>Standard</title></head><main><aside class="sidebar--filters">Filter controls</aside>
<article><h1>Standard</h1><section id="annex"><h2>Annex A</h2><p>Before <b>nested</b> content.</p>
<div class="indicator-row indicator-row--not-in-use filter--cages" hidden>
<div class="indicator-id"><p>1.1.1</p></div><div class="indicator-content"><p>Keep <b>records</b>.
<span class="footnote-link">1<span class="popup-inner">Source note.</span></span></p></div>
<div class="indicator-applicability"><div class="popup-inner"><p>Applicable to</p><div>Cages</div></div></div></div>
<table><caption>Limits</caption><tr><th rowspan="2">Agent</th><th>Limit</th></tr><tr><td>2 <sup>mg</sup>/L
<table><tr><td>Nested cell</td></tr></table>After nested<span class="fotnote">Cell note</span></td></tr></table>
<ul><li>Parent<ul><li>Child</li></ul>After child</li></ul><p>See <a href="#annex">Annex</a></p>
<a href="https://example.test/attachment"></a><a href="https://example.test/image"><img src="figure.png" alt="Figure"/></a>
<nav>Page navigation</nav><button>Print</button></section></article></main></html>'''


def mapping(d): return map_content_records(d, 'a'*64, 'b'*64)
def verify(d, m): return verify_source_records(d, m, 'a'*64, 'b'*64)
def text(record): return ''.join(f.text or '' for values in record.fields.values() for f in values)


def test_asc_fields_notes_and_conditional_source_state():
    d=doc(RAW);before=d.model_dump_json();m=mapping(d)
    assert verify(d,m)['status']=='passed'
    r=next(r for r in m.records if r.kind=='standard_indicator')
    assert r.fields['identifier'][0].text=='1.1.1'
    assert 'Keep records.' in r.fields['body'][0].text and 'Source note.' not in r.fields['body'][0].text
    assert r.fields['applicability'][0].text=='Applicable toCages'
    assert 'source_marked_not_in_use' in r.issues
    assert any('Source note.' in text(r) for r in m.records if r.kind=='source_note')
    node=d.nodes[int(next(p.pointer for p in r.structure if p.locator==r.locator).split('/')[2])]
    assert 'hidden' in node.attributes and 'filter--cages' in node.attributes['class']
    assert d.model_dump_json()==before


def test_annex_table_cells_keep_geometry_nested_ownership_and_notes():
    d=doc(RAW);m=mapping(d)
    cells=[r for r in m.records if r.kind=='source_table_cell']
    assert len(cells)==4 and verify(d,m)['status']=='passed'
    outer=next(r for r in cells if '2 mg/L' in text(r))
    assert 'Nested cell' not in text(outer) and 'Cell note' not in text(outer)
    assert any('After nested' in f.text for f in outer.fields['body'])
    assert any(p.pointer.startswith('/tables/0/cells/') for p in outer.structure)
    header=next(r for r in cells if text(r)=='Agent')
    ptr=next(p.pointer for p in header.structure if p.pointer.startswith('/tables/0/cells/'))
    assert d.tables[0].cells[int(ptr.rsplit('/',1)[1])].rowspan==2
    assert any(d.nodes[int(p.pointer.split('/')[2])].attributes.get('id')=='annex'
               for p in outer.structure if p.pointer.startswith('/nodes/'))


def test_complete_literal_content_and_nontext_evidence_accounting():
    d=doc(RAW);m=mapping(d);used={p.pointer for r in m.records for values in r.fields.values() for f in values for p in f.references}
    assert all(f'/atoms/{i}/text' in used or any(r.reference.pointer==f'/atoms/{i}/text' for r in m.residual)
               for i,a in enumerate(d.atoms) if a.text.strip())
    assert {'source_image','source_link','source_caption','source_list_item','source_heading'} <= {r.kind for r in m.records}
    assert all('Filter controls' not in text(r) and 'Page navigation' not in text(r) and 'Print' not in text(r) for r in m.records)
    assert verify(d,m)['status']=='passed'


@pytest.mark.parametrize('mutation',['drop_cell','swap_cell_fields','drop_structure','wrong_geometry','wrong_scope',
    'drop_note','drop_image','drop_link','drop_inactive','mutate_applicability','merge_runs','reorder','drop_residual'])
def test_independent_verifier_detects_missing_or_misassociated_content(mutation):
    d=doc(RAW);payload=mapping(d).model_dump();rs=payload['records']
    cell=next(r for r in rs if r['kind']=='source_table_cell' and '2 mg/L' in ''.join(f['text'] or '' for f in r['fields']['body']))
    indicator=next(r for r in rs if r['kind']=='standard_indicator')
    if mutation=='drop_cell':rs.remove(cell)
    elif mutation=='swap_cell_fields':cell['fields']=next(r for r in rs if r['kind']=='source_table_cell' and r is not cell)['fields']
    elif mutation=='drop_structure':cell['structure']=[]
    elif mutation=='wrong_geometry':next(p for p in cell['structure'] if '/cells/' in p['pointer'])['pointer']='/tables/0/cells/0'
    elif mutation=='wrong_scope':cell['structure'][0]['locator']='wrong annex'
    elif mutation=='drop_note':rs.remove(next(r for r in rs if r['kind']=='source_note'))
    elif mutation=='drop_image':rs.remove(next(r for r in rs if r['kind']=='source_image'))
    elif mutation=='drop_link':rs.remove(next(r for r in rs if r['kind']=='source_link'))
    elif mutation=='drop_inactive':indicator['issues']=[]
    elif mutation=='mutate_applicability':indicator['fields']['applicability'][0]['text']='All systems'
    elif mutation=='merge_runs':
        fields=cell['fields']['body'];assert len(fields)>1
        fields[0]['text']=''.join(f['text'] for f in fields);fields[0]['references']=[p for f in fields for p in f['references']]
        cell['fields']['body']=fields[:1]
    elif mutation=='reorder':rs.reverse()
    else:payload['residual'].pop()
    assert verify(d,ContentRecords(**payload))['status']=='failed'


def test_missing_asc_field_and_nested_indicator_are_preserved():
    raw=RAW.replace(b'<div class="indicator-id"><p>1.1.1</p></div>', b'')
    d=doc(raw);m=mapping(d);r=next(r for r in m.records if r.kind=='standard_indicator')
    assert 'missing_or_ambiguous_field:identifier' in r.issues and r.fields['identifier'][0].text is None
    assert verify(d,m)['status']=='passed'


@pytest.mark.parametrize('applicability', [b'', b'<p>Indicator applicability: land-based systems</p>'])
def test_asc_appendix_alternate_source_columns(applicability):
    raw=RAW.replace(b'<table><caption>', b'<div class="table-row indicator-row"><div class="table-cell indicator"><strong>14.1</strong></div><div class="table-cell">'+applicability+b'<p>Appendix duty.</p></div></div><table><caption>')
    d=doc(raw);m=mapping(d);r=next(r for r in m.records if r.kind=='standard_indicator' and r.fields['identifier'][0].text=='14.1')
    assert r.fields['body'][0].text=='Appendix duty.'
    assert r.fields['applicability'][0].text==('Indicator applicability: land-based systems' if applicability else None)
    assert ('source_field_not_separately_stated:applicability' in r.issues)==(not applicability)
    assert verify(d,m)['status']=='passed'


def test_excel_fields_and_version_one_contract_stay_compatible():
    d=xlsx_document();v1=map_source_records(d,'a'*64,'b'*64);v2=mapping(d)
    assert [r.model_dump(exclude={'structure'}) for r in v2.records]==[r.model_dump() for r in v1.records]
    assert v2.residual==v1.residual and verify(d,v1)['status']==verify(d,v2)['status']=='passed'
    assert json.loads(Path('config/schemas/source-records-v2.schema.json').read_text())==ContentRecords.model_json_schema()
