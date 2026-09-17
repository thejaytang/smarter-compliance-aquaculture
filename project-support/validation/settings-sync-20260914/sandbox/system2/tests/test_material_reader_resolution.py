"""Resolution changes read exactly one bound original page; never extract."""
import base64
from hashlib import sha256
from io import BytesIO
import math
import pytest
from PIL import Image
from reportlab.pdfgen import canvas
from pdf_extraction.evidence import material_reader as reader


def original(tmp_path, size=(612, 792)):
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=size)
    for label in ('FIRST exact 17.5 mg/L shall not change', 'SECOND different page'):
        pdf.drawString(20, 40, label)
        pdf.showPage()
    pdf.save()
    raw = output.getvalue()
    path = tmp_path / 'bound.pdf'
    path.write_bytes(raw)
    return path, sha256(raw).hexdigest(), raw


def pixels(result):
    with Image.open(BytesIO(base64.b64decode(result['image'].split(',', 1)[1]))) as image:
        assert image.size == (result['image_width'], result['image_height'])
        return image.size


def test_real_pdf_resizes_only_selected_page_and_preserves_original(tmp_path, monkeypatch):
    import pypdfium2 as pdfium
    path, digest, raw = original(tmp_path)
    rendered = []
    original_render = pdfium.PdfPage.render
    def render(page, *args, **kwargs):
        rendered.append(kwargs['scale'])
        return original_render(page, *args, **kwargs)
    monkeypatch.setattr(pdfium.PdfPage, 'render', render)
    default = reader.read_material(path, digest, page=2)
    medium = reader.read_material(path, digest, page=2, render_width=1536)
    high = reader.read_material(path, digest, page=2, render_width=2304)
    assert pixels(default) == (918, 1188)
    assert pixels(medium)[0] == 1536
    assert pixels(high)[0] == 2304
    assert len(rendered) == 3  # No rendering of the other page or a whole-document conversion.
    for result in (default, medium, high):
        assert result['native_text'] == default['native_text']
        assert 'SECOND' in result['native_text'] and 'FIRST' not in result['native_text']
        assert result['width'] == 612 and result['height'] == 792
        assert result['source_sha256'] == digest and result['pages'] == 2
        assert not result['render_limited']
    assert default['render_width_requested'] is None
    assert path.read_bytes() == raw
    assert set(p.name for p in tmp_path.iterdir()) == {'bound.pdf', '.reader-cache'}


@pytest.mark.parametrize('size', [(612,792), (792,612), (600,600), (10,2000)])
def test_actual_bitmap_honors_dimension_and_area_caps(tmp_path, size):
    path, digest, _ = original(tmp_path, size)
    result = reader.read_material(path, digest, render_width=32768)
    w, h = pixels(result)
    assert max(w,h) <= 4096 and w*h <= 12_000_000
    assert result['render_limited'] and result['render_width_requested'] == 32768
    assert math.isclose(w/h, size[0]/size[1], rel_tol=0.03)


@pytest.mark.parametrize('invalid', [0, -1, 32769, 10**100, True, False, 1.5, '1024', '', [], {}])
def test_invalid_width_rejected_before_source_or_cache_access(tmp_path, invalid):
    with pytest.raises(ValueError, match='original_render_width_out_of_range'):
        reader.read_material(tmp_path/'missing.pdf', 'f'*64, render_width=invalid)
    assert not list(tmp_path.iterdir())


def test_normalized_cache_does_not_reuse_wrong_request_or_wrong_version(tmp_path, monkeypatch):
    path, digest, raw = original(tmp_path)
    first = reader.read_material(path, digest, render_width=1000)
    def forbidden(*args, **kwargs):
        raise AssertionError('normalized request should hit verified cache')
    with monkeypatch.context() as patch:
        patch.setattr(reader, '_pdf', forbidden)
        second = reader.read_material(path, digest, render_width=1001)
        assert first['image'] == second['image']
        assert second['render_width_requested'] == 1001
        assert second['render_width_normalized'] == 1024
        path.write_bytes(raw+b'changed')
        with pytest.raises(ValueError, match='original_version_changed'):
            reader.read_material(path, digest, render_width=1001)
        path.write_bytes(raw)
    cache = list((tmp_path/'.reader-cache').glob('*.json'))
    assert len(cache) == 1
    cache[0].write_text('{broken cache')
    assert reader.read_material(path, digest, render_width=1001)['image'] == first['image']
    monkeypatch.setattr(reader, 'VERSION', 'material-reader/test-next-version')
    assert reader.read_material(path, digest, render_width=1001)['schema_version'] == reader.VERSION
    assert len(list((tmp_path/'.reader-cache').glob('*.json'))) == 2
    assert path.read_bytes() == raw
