from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
from types import SimpleNamespace

import pytest
from pypdf import PdfWriter

from pdf_extraction.review.coverage_preview import references
from pdf_extraction.evidence.review_preview import preview


def test_range_inventory_includes_pages_without_any_output(tmp_path):
    path=tmp_path/'canonical.json'
    path.write_text(json.dumps(dict(pages=[dict(page_index=18),dict(page_index=19)],blocks={})))
    digest=sha256(path.read_bytes()).hexdigest()
    doc=dict(source=dict(file_format='pdf'),canonical=[dict(path=str(path),sha256=digest)])
    refs=[dict(canonical_sha256=digest,locator='whole parsed range')]
    before=deepcopy(refs)
    result=references(SimpleNamespace(root=tmp_path),doc,dict(kind='coverage'),refs)
    assert [r['page_index'] for r in result]==[18,19]
    assert refs==before
    path.write_text('{}')
    assert references(SimpleNamespace(root=tmp_path),doc,dict(kind='coverage'),refs)==before


def test_unregistered_or_outside_canonical_cannot_supply_a_page(tmp_path):
    ref=dict(canonical_sha256='wrong',locator='whole parsed range')
    doc=dict(source=dict(file_format='pdf'),canonical=[])
    assert references(SimpleNamespace(root=tmp_path),doc,dict(kind='coverage'),[ref])==[ref]


def test_unlocated_pdf_never_masquerades_as_bound_page_one(tmp_path):
    p=tmp_path/'source.pdf';p.write_bytes(b'%PDF-unlocated')
    result=preview(p,sha256(p.read_bytes()).hexdigest(),[dict(locator='whole parsed range')],tmp_path/'cache')
    assert result['kind']=='unlocated'
    assert 'image' not in result and 'page' not in result
    assert 'no verified page location' in result['label']


def test_explicit_range_uses_first_bound_page_and_checks_all_indices(tmp_path):
    writer=PdfWriter()
    for _ in range(3):writer.add_blank_page(width=100,height=100)
    raw=BytesIO();writer.write(raw);p=tmp_path/'source.pdf';p.write_bytes(raw.getvalue())
    digest=sha256(raw.getvalue()).hexdigest()
    result=preview(p,digest,[dict(page_index=1),dict(page_index=2)],tmp_path/'cache')
    assert result['page']==2 and result['image']
    assert '2, 3' in result['warnings'][0]
    with pytest.raises(ValueError,match='original_page_out_of_range'):
        preview(p,digest,[dict(page_index=1),dict(page_index=3)],tmp_path/'cache')
