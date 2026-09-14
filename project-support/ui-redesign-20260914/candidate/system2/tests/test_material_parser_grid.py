"""Geometry guards retain source evidence instead of accepting inconsistent cells."""
from dataclasses import asdict
from hashlib import sha256
from io import BytesIO
import json
from types import SimpleNamespace

import pytest
from reportlab.pdfgen import canvas

from pdf_extraction.orchestration.material_parser import _inspect_pdf_table_grid, parse_material
from pdf_extraction.types import NativeObject, NativePage


def inspect(boxes, specs=None, ys=None):
    lines = [NativeObject(id=f'line-{i}', text=f'Unchanged source {i}',
                          bbox_points=tuple(box), object_type='text_line')
             for i,box in enumerate(boxes)]
    page = NativePage(page_index=0, width_points=200, height_points=80,
                      words=lines, text_lines=lines, backend='pypdfium2')
    result = _inspect_pdf_table_grid(page, SimpleNamespace(x0=0,y0=0),
                                    [0,150,300], ys or [0,120],
                                    specs if specs is not None else [(0,0,1,1),(0,1,1,1)],
                                    [0,0,200,80])
    assert result['original_positioned_line_fallback'] == [asdict(line) for line in lines]
    return result


def test_true_merged_cell_does_not_count_its_latent_internal_edge():
    result = inspect([[20,10,180,20],[10,50,70,60],[120,50,190,60]],
                     [(0,0,1,2),(1,0,1,1),(1,1,1,1)], [0,60,120])
    assert result['reject'] is False
    assert result['crossing_line_numerator'] == 0
    assert result['captured_line_denominator'] == 3


@pytest.mark.parametrize(('overflow','reject'), [(1.0,False),(1.01,True)])
def test_grid_tolerates_one_point_rounding_but_not_more(overflow,reject):
    result = inspect([[90,10,100+overflow,20]])
    assert result['reject'] is reject


@pytest.mark.parametrize(('denominator','reject'), [(4,True),(5,False)])
def test_crossing_ratio_threshold_counts_lines_once(denominator,reject):
    # One line can cross a boundary deeply; severity does not multiply its vote.
    result = inspect([[90,10,115,20]] + [[10,30,50,40]]*(denominator-1))
    assert result['captured_line_denominator'] == denominator
    assert result['crossing_line_numerator'] == 1
    assert result['reject'] is reject


@pytest.mark.parametrize(('specs','reason'), [
    ([(0,1,1,1)],'missing_cell_owner'),
    ([(0,0,1,1),(0,0,1,2)],'multiple_cell_owners'),
])
def test_uncertain_cell_ownership_rejects_region_without_throwing(specs,reason):
    result = inspect([[10,10,40,20]],specs)
    assert result['reject'] is True
    assert result['reason'] == 'cell_ownership_uncertain'
    assert result['uncertain_lines'][0]['reason'] == reason
    assert result['captured_line_denominator'] == 0
    assert result['crossing_ratio'] is None


def test_no_native_line_evidence_is_not_a_successful_grid_check():
    result = inspect([])
    assert result['reject'] is True
    assert result['reason'] == 'native_line_evidence_missing'
    assert result['crossing_ratio'] is None


def test_rejected_grid_keeps_exact_positioned_text_refs_and_other_page_table(tmp_path):
    text = 'Must not exceed 5 mg unless exempt.'
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    for x in (40,140,240,340):
        pdf.line(x,550,x,650)
    for y in (550,650):
        pdf.line(40,y,340,y)
    pdf.drawString(60,600,text)
    pdf.showPage()
    for x in (40,180,360):
        pdf.line(x,500,x,650)
    for y in (500,550,600,650):
        pdf.line(40,y,360,y)
    for x,y,value in [(50,620,'Item'),(190,620,'Limit'),(50,570,'A'),
                      (190,570,'5 mg'),(50,520,'B'),(190,520,'7 mg')]:
        pdf.drawString(x,y,value)
    pdf.save()
    raw = buffer.getvalue()
    source_root = tmp_path/'originals'
    source_root.mkdir()
    original = source_root/'mixed-grids.pdf'
    original.write_bytes(raw)
    source = dict(source_id='TS001',snapshot_id='TS001-001',relative_path=original.name,
                  content_hash=sha256(raw).hexdigest(),file_format='pdf',
                  operator_selection_decision='INCLUDE',selection_status='INCLUDE',
                  snapshot_status='STORED',source_status='CURRENT',download_status='SUCCESS',
                  registry_sha256='0'*64)
    output = tmp_path/'candidate'
    result = parse_material(source,source_root,output)
    assert original.read_bytes() == raw
    assert result['status'] == 'partial'
    assert result['usable_scope'] == ['page:1','page:2']
    issue, = result['unresolved']
    assert issue['scope_id'] == 'page:1' and issue['code'] == 'table_grid_inconsistent'
    assert issue['message'] in result['warnings']
    review = json.loads((output/issue['evidence_ref']).read_text())
    rejected, = review['rejected']
    assert rejected['candidate']['id'] == issue['rejected_candidate_id']
    assert rejected['source_refs'] == issue['source_refs']
    assert issue['source_refs'][0]['page_index'] == 0
    native = json.loads((output/'pdf-native-0001.json').read_text())
    line, = native['pages'][0]['text_lines']
    assert rejected['original_positioned_line_fallback'] == [line]
    block, = [b for b in result['blocks'] if b['text'] == text]
    assert block['source_refs'][0]['native_id'] == line['id']
    assert block['source_refs'][0]['bbox'] == line['bbox_points']
    assert block['source_refs'][0]['scope_id'] == 'page:1'
    table, = [b for b in result['blocks'] if b['type']=='table']
    assert table['source_refs'][0]['page_index'] == 1
    assert table['table']['rows'] == [['Item','Limit'],['A','5 mg'],['B','7 mg']]

