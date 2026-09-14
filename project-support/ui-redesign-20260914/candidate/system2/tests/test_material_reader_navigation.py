"""The original outline is a convenience, never a source-content filter."""
from hashlib import sha256

from bs4 import BeautifulSoup
from lxml import html

from pdf_extraction.evidence.material_reader import html_anchor, read_material
from pdf_extraction.formats.html import dom_path


def read_snapshot(tmp_path, raw):
    path = tmp_path / 'original.html'
    path.write_bytes(raw)
    result = read_material(path, sha256(raw).hexdigest())
    assert path.read_bytes() == raw
    return result


def test_outline_uses_meaningful_content_and_preserves_all_legacy_anchors(tmp_path):
    raw = b'''<html><head><title>Website title</title><meta name="x" content="x">
    <link href="https://example.invalid/style"><script>UNSAFE()</script></head>
    <body><header><h1>Website brand</h1></header><nav><h2>Site navigation</h2>
    <p>Retained navigation text</p></nav><main><div><div><h1>Document title</h1></div></div>
    <section><h2>Clause 1</h2><p>Must not exceed 5 mg/L except during cleaning.</p>
    <table><caption>Limits</caption><tr><td>5 mg/L</td></tr></table></section>
    <aside><h2>Related links</h2><p>Retained aside text</p></aside>
    <details><summary>Note</summary><p>Retained closed note</p></details></main>
    <footer>Retained footer text</footer></body></html>'''
    result = read_snapshot(tmp_path, raw)
    original = BeautifulSoup(raw, 'lxml')
    expected = [{'id': html_anchor(dom_path(el)), 'locator': dom_path(el),
                 'label': el.get_text(' ', strip=True)[:100] or el.name}
                for el in original.find_all(True) if el.name not in {'script', 'style', 'head'}]
    assert result['anchors'] == expected
    assert [a['label'] for a in result['navigation_anchors']] == ['Document title', 'Clause 1', 'Limits', 'Note']
    assert result['default_anchor'] == result['navigation_anchors'][0]['id']
    rendered = html.document_fromstring(result['html'])
    for text in ['Website brand', 'Retained navigation text', 'Retained aside text',
                 'Retained footer text', 'Retained closed note', 'Must not exceed 5 mg/L except during cleaning.']:
        assert text in rendered.text_content()
    assert not rendered.xpath('//script | //iframe | //@href | //@onload')
    assert 'UNSAFE()' not in result['html'] and 'example.invalid' not in result['html']
    assert rendered.xpath('//*[@id="original-document"]')
    for anchor in result['navigation_anchors']:
        assert rendered.xpath('//*[@id=$target]', target=anchor['id'])
    assert read_material(tmp_path / 'original.html', sha256(raw).hexdigest()) == result


def test_lovdata_section_roots_open_document_title_not_site_navigation(tmp_path):
    raw = '''<html><head><title>Saved law - Lovdata</title></head><body>
    <nav><h1>Lovdata</h1></nav><section id="documentMeta"><h1>Aquaculture regulation</h1>
    <p>Version 2026</p></section><section id="documentBody"><section class="kapittel">
    <h2>Chapter I</h2><section class="paragraf"><h3>§ 1. Scope</h3><p>Applies to farms.</p>
    </section></section></section><h2>Other website information</h2></body></html>'''.encode()
    result = read_snapshot(tmp_path, raw)
    assert [a['label'] for a in result['navigation_anchors']] == ['Aquaculture regulation', 'Chapter I', '§ 1. Scope']
    title = BeautifulSoup(raw, 'lxml').select_one('#documentMeta h1')
    assert result['default_anchor'] == html_anchor(dom_path(title))
    assert 'Other website information' in result['html']


def test_unknown_template_without_headings_has_readable_content_fallback(tmp_path):
    result = read_snapshot(tmp_path, b'<main><p>Unnumbered content.</p><table><tr><td>12 kg</td></tr></table></main>')
    assert [a['label'] for a in result['navigation_anchors']] == ['Document content']
    assert result['default_anchor'] == result['navigation_anchors'][0]['id']
    assert html.document_fromstring(result['html']).xpath('//*[@id=$target]', target=result['default_anchor'])
    assert 'Unnumbered content.' in result['html'] and '12 kg' in result['html']


def test_ambiguous_profile_falls_back_without_hiding_either_document(tmp_path):
    result = read_snapshot(tmp_path, b'''<body><div id="documentMeta">Incomplete template</div>
    <article><h2>First record</h2><p>First text</p></article>
    <article><h2>Second record</h2><p>Second text</p></article></body>''')
    assert [a['label'] for a in result['navigation_anchors']] == ['First record', 'Second record']
    assert 'Incomplete template' in result['html']
    assert 'First text' in result['html'] and 'Second text' in result['html']
