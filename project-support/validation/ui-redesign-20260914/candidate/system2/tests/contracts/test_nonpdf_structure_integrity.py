"""Discriminating source-layout and source-relationship regressions."""
from hashlib import sha256
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
import json
from pathlib import Path
import pytest
from pdf_extraction.formats.excel import parse_excel
from pdf_extraction.verification.excel import verify_excel
from pdf_extraction.contracts.excel import ExcelDocument
from pdf_extraction.contracts.html import HtmlDocument
from pdf_extraction.verification.html import verify_html
from tests.contracts.test_html_v2 import RAW, doc
from tests.contracts.test_source_intake import source
from tests.contracts.test_excel_document import workbook, mutate_zip


def shared_workbook(target='strings/custom.xml', *, decoy=True, relationship=True):
    raw=workbook()
    raw=mutate_zip(raw,'xl/worksheets/sheet1.xml',lambda b:b.replace(
        b'<c r="A1" t="inlineStr"><is><t>Requirement</t></is></c>',b'<c r="A1" t="s"><v>0</v></c>'))
    out=BytesIO()
    with ZipFile(BytesIO(raw)) as src, ZipFile(out,'w',ZIP_DEFLATED) as dst:
        for n in src.namelist():
            b=src.read(n)
            if n=='xl/_rels/workbook.xml.rels' and relationship:
                b=b.replace(b'</Relationships>',f'<Relationship Id="rStrings" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="{target}"/></Relationships>'.encode())
            dst.writestr(n,b)
        ns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
        dst.writestr('xl/strings/custom.xml',f'<sst xmlns="{ns}"><!-- source annotation --><si><t>Correct source text</t></si></sst>')
        if decoy:dst.writestr('xl/sharedStrings.xml',f'<sst xmlns="{ns}"><si><t>Wrong unrelated text</t></si></sst>')
    return out.getvalue()


def test_excel_uses_referenced_strings_not_conventional_filename():
    raw=shared_workbook();d=parse_excel(raw,source(raw,'xlsx'))
    assert d.sheets[0].cells[0].text=='Correct source text'
    assert verify_excel(raw,d)['status']=='passed'


def test_excel_verifier_rebuilds_reference_independently():
    raw=shared_workbook();value=parse_excel(raw,source(raw,'xlsx')).model_dump()
    value['sheets'][0]['cells'][0]['text']='Wrong unrelated text'
    assert verify_excel(raw,ExcelDocument(**value))['status']=='failed'


@pytest.mark.parametrize('target', ['../../outside.xml','https://example.invalid/strings.xml','strings/missing.xml'])
def test_invalid_string_part_target_fails_closed(target):
    raw=shared_workbook(target)
    with pytest.raises(ValueError,match='shared_string|relationship'):
        parse_excel(raw,source(raw,'xlsx'))


def test_missing_string_relationship_is_not_guessed():
    raw=shared_workbook(relationship=False)
    with pytest.raises(ValueError,match='shared_string'):
        parse_excel(raw,source(raw,'xlsx'))


@pytest.mark.parametrize('target', ['document','table','cell','list','issues'])
def test_html_uncalibrated_policy_and_issue_inventory_are_verified(target):
    raw=RAW.replace(b'<!-- -->',b'<a href="#missing">Missing note</a>')
    value=doc(raw).model_dump()
    if target=='document':value['confidence']=1.0
    elif target=='table':value['tables'][0]['confidence']=1.0
    elif target=='cell':value['tables'][0]['cells'][0]['confidence']=1.0
    elif target=='list':value['lists'][0]['confidence']=1.0
    else:value['issues']=[]
    assert verify_html(raw,HtmlDocument(**value))['status']=='failed'


def table_document(body):
    return ('<html><div id="documentMeta">Law</div><div id="documentBody"><table>'+body+'</table></div></html>').encode()


def test_rowspan_zero_stops_at_own_row_group():
    raw=table_document('<tbody><tr><td rowspan="0">Group A</td><td>A1</td></tr><tr><td>A2</td></tr></tbody><tbody><tr><td>B1</td><td>B2</td></tr></tbody>')
    d=doc(raw);t=d.tables[0]
    assert not t.issues and t.column_count==2
    assert [(c.row,c.column,c.rowspan) for c in t.cells]==[(0,0,2),(0,1,1),(1,1,1),(2,0,1),(2,1,1)]
    assert next(n for n in d.nodes if n.id==t.cells[0].node_id).attributes['rowspan']=='0'
    assert verify_html(raw,d)['status']=='passed'


def test_overlapping_cells_preserve_source_and_review_problem():
    raw=table_document('<tr><td>A</td><td rowspan="2">B</td></tr><tr><td colspan="2">Overlapping</td></tr>')
    d=doc(raw)
    assert any(x.startswith('overlapping_span:') for x in d.tables[0].issues)
    assert d.tables[0].column_count is None
    assert verify_html(raw,d)['status']=='passed'
    value=d.model_dump();value['tables'][0]['issues']=[];value['issues']=[]
    assert verify_html(raw,HtmlDocument(**value))['status']=='failed'


def test_bad_span_keeps_all_unresolved_coordinates_unknown():
    raw=table_document('<tr><td rowspan="bad">Unknown</td><td>A</td></tr>')
    d=doc(raw);value=d.model_dump();value['tables'][0]['cells'][0]['rowspan']=10
    assert verify_html(raw,HtmlDocument(**value))['status']=='failed'


@pytest.mark.parametrize('case,reason', [
    ('missing_anchor','shared_formula_anchor_missing:'),
    ('outside_anchor','shared_formula_outside_anchor_range:'),
    ('overlap_merge','overlapping_merge:'),
    ('invalid_merge','invalid_merge_range:'),
])
def test_excel_broken_formula_and_merge_relationships_are_explicit(case,reason):
    def change(b):
        if case=='missing_anchor':
            return b.replace(b'<f>B2*2</f>',b'<f t="shared" si="99"/>')
        if case=='outside_anchor':
            return b.replace(b'<f>B2*2</f>',b'<f t="shared" si="0" ref="C2:C3">B2*2</f>').replace(b'<f>SUM(B2,2)</f>',b'<f t="shared" si="0"/>')
        if case=='overlap_merge':
            return b.replace(b'</mergeCells>',b'<mergeCell ref="B4:D4"/></mergeCells>')
        return b.replace(b'ref="A4:C4"',b'ref="A4:XFE4"')
    raw=mutate_zip(workbook(),'xl/worksheets/sheet1.xml',change)
    d=parse_excel(raw,source(raw,'xlsx'))
    assert any(i.startswith(reason) for i in d.issues)
    assert verify_excel(raw,d)['status']=='passed'
    value=d.model_dump();value['issues']=[i for i in value['issues'] if not i.startswith(reason)]
    assert verify_excel(raw,ExcelDocument(**value))['status']=='failed'
