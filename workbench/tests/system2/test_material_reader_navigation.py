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


def test_document_information_uses_source_identity_not_website_or_body(tmp_path):
    raw = '''<html><head><meta charset="utf-8"><title>Website title</title></head><body>
    <nav><h1>Website menu</h1></nav><div id="documentMeta"><h1>Regulation &amp; scope</h1>
    <table><tr><th>Dato</th><td>FOR-2022-08-22-1484</td></tr>
    <tr><th>Hjemmel</th><td><a href="https://example.invalid">Law § 10</a></td></tr></table></div>
    <div id="documentBody"><h2>Chapter 1</h2><p>Requirement text</p></div></body></html>'''.encode()
    result = read_snapshot(tmp_path, raw)
    info = result['document_information']
    assert info['title']['value'] == 'Regulation & scope'
    assert [(f['label'], f['value']) for f in info['fields']] == [
        ('Dato', 'FOR-2022-08-22-1484'), ('Hjemmel', 'Law § 10')]
    rendered = html.document_fromstring(result['html'])
    for item in [info['title'], *info['fields']]:
        assert rendered.get_element_by_id(item['anchor']).text_content().strip() == item['value']


def test_document_information_does_not_invent_missing_fields(tmp_path):
    result = read_snapshot(tmp_path, b'<nav><h1>Menu</h1></nav><main><h1>Document title</h1><p>Body</p></main>')
    assert result['document_information']['title']['value'] == 'Document title'
    assert result['document_information']['fields'] == []
    result = read_snapshot(tmp_path, b'<nav><h1>Menu</h1></nav><p>Body</p>')
    assert result['document_information']['title'] is None


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

def test_hydration_comment_tails_are_preserved_in_original_title_and_body(tmp_path):
    raw=b'<html><head><meta charset="utf-8"></head><body><main><h1><!--[0--><!-- -->Fish welfare<!-- --></h1><p><!-- -->First <b>bold</b><!-- --> last.</p></main></body></html>'
    result=read_snapshot(tmp_path,raw)
    rendered=html.document_fromstring(result['html'])
    assert rendered.get_element_by_id(result['document_information']['title']['anchor']).text_content()=='Fish welfare'
    assert 'First bold last.' in rendered.text_content()


def test_journal_title_and_head_only_document_title(tmp_path):
    journal=read_snapshot(tmp_path,b'<html><head><title>technical.xml</title></head><body><p class="oj-doc-ti">REGULATION</p><p class="oj-doc-ti">Animal Health Law</p></body></html>')
    assert journal['document_information']['title']['value']=='REGULATION\nAnimal Health Law'
    head=read_snapshot(tmp_path,b'<html><head><title>Aquaculture guidance</title></head><body><p>Guidance</p></body></html>')
    assert head['document_information']['title']['value']=='Aquaculture guidance'
    assert head['document_information']['title']['anchor'] is None


def test_registered_html_reader_uses_full_sanitizer_without_store_or_cache(tmp_path, monkeypatch, capsys):
    import io
    import json
    from pdf_extraction.orchestration import material_service
    raw = b'''<html><head><script>window.SCRIPT_RAN=true</script><style>body{display:none}</style>
    <link href="https://external.invalid/style"><base href="https://external.invalid/"></head><body>
    <h1>Fixture scope</h1><ul><li>All facilities</li></ul><table><tr><td>3 metres</td></tr></table>
    <form action="https://external.invalid/submit"><p>Readable form text</p><input><button>Submit</button></form>
    <img src="https://external.invalid/pixel" onerror="UNSAFE()" alt="source image">
    <iframe src="https://external.invalid/frame"></iframe><svg onload="UNSAFE()"></svg>
    <a href="javascript:UNSAFE()">Readable link</a></body></html>'''
    path = tmp_path / 'original.htm'
    path.write_bytes(raw)
    expected = sha256(raw).hexdigest()
    def forbidden(*args, **kwargs):
        raise AssertionError('Preview must not initialize MaterialService or business stores')
    monkeypatch.setattr(material_service, 'MaterialService', forbidden)
    monkeypatch.setattr(material_service.sys, 'stdin', io.StringIO(json.dumps({
        'command': 'material_source-html', 'path': str(path), 'expected_hash': expected})))
    assert material_service.main() == 0
    envelope = json.loads(capsys.readouterr().out)
    assert envelope['ok'] is True
    result = envelope['data']
    assert result['kind'] == 'html' and result['source_sha256'] == expected
    rendered = html.document_fromstring(result['html'])
    assert rendered.xpath('//h1')[0].text == 'Fixture scope'
    assert rendered.xpath('//li')[0].text == 'All facilities'
    assert rendered.xpath('//td')[0].text == '3 metres'
    assert 'Readable form text' in rendered.text_content() and 'Readable link' in rendered.text_content()
    assert not rendered.xpath('//script | //form | //iframe | //svg | //input | //button | //base | //link | //@href | //@onerror')
    assert 'external.invalid' not in result['html'] and 'SCRIPT_RAN' not in result['html']
    assert "default-src 'none'" in result['html'] and "form-action 'none'" in result['html']
    assert list(tmp_path.iterdir()) == [path] and path.read_bytes() == raw
    path.write_bytes(b'<h1>Changed</h1>')
    monkeypatch.setattr(material_service.sys, 'stdin', io.StringIO(json.dumps({
        'command': 'material_source-html', 'path': str(path), 'expected_hash': expected})))
    assert material_service.main() == 1
    assert json.loads(capsys.readouterr().out)['error'] == 'original_version_changed'


def test_registered_html_crosses_owning_adapter_without_creating_runtime(tmp_path):
    from pathlib import Path
    from local_workbench.adapter import System2
    original = tmp_path / 'registered.html'
    original.write_bytes(b'<h1>Registered fixture</h1><p>Original source.</p>')
    fingerprint = sha256(original.read_bytes()).hexdigest()
    component = Path(__file__).resolve().parents[2] / 'backend/system2'
    adapter = System2(component, tmp_path / 'unused-system1', runtime=tmp_path / 'untouched-runtime')
    result = adapter.call('material_source-html', path=str(original), expected_hash=fingerprint)
    assert result['kind'] == 'html' and result['source_sha256'] == fingerprint
    assert 'Registered fixture' in result['html']
    assert not (tmp_path / 'untouched-runtime').exists()
    assert not (tmp_path / '.reader-cache').exists()
    assert sha256(original.read_bytes()).hexdigest() == fingerprint


def test_local_references_only_reach_unique_surviving_original_targets(tmp_path):
    raw = '''<html><head><meta charset="utf-8"></head><body>
    <p id="reference"><a href="#note" onclick="UNSAFE()">Footnote</a></p>
    <p id="note">Exact note <a href="#reference">Return</a></p>
    <p id="blå">Unicode note</p><a href="#bl%C3%A5">Unicode reference</a>
    <p id="duplicate">First</p><p id="duplicate">Second</p>
    <script id="removed">UNSAFE()</script><form id="form"><p>Retained form text</p></form>
    <a href="#duplicate">Ambiguous</a><a href="#missing">Missing</a>
    <a href="#removed">Removed</a><a href="#%FF">Invalid encoding</a>
    <a href="https://example.invalid/#note">External</a>
    <a href="file:///tmp/original.html#note">File</a>
    <a href="javascript:UNSAFE()">Script</a><a href="//example.invalid/#note">Protocol relative</a>
    <a href="#form">Readable transformed target</a></body></html>'''.encode()
    result = read_snapshot(tmp_path, raw)
    original = BeautifulSoup(raw, 'lxml')
    rendered = html.document_fromstring(result['html'])
    expected = {'Footnote': 'note', 'Return': 'reference',
                'Unicode reference': 'blå', 'Readable transformed target': 'form'}
    links = {link.text_content(): link for link in rendered.xpath('//a')}
    for label, source_id in expected.items():
        target = html_anchor(dom_path(original.find(id=source_id)))
        assert links[label].get('href') == '#' + target
        assert rendered.get_element_by_id(target) is not None
    assert all(link.get('href') is None for label, link in links.items() if label not in expected)
    assert not rendered.xpath('//script | //form | //@onclick | //@target | //@download')
    assert 'example.invalid' not in result['html'] and 'file:' not in result['html']
    assert "script-src 'none'" in result['html'] and "base-uri 'none'" in result['html']
    assert result == read_material(tmp_path / 'original.html', sha256(raw).hexdigest())


def test_ordered_list_numbering_retains_only_applicable_declarative_attributes(tmp_path):
    raw = b'''<main><ol type="a" start="4" reversed><li>Fourth</li><li value="2">Second</li></ol>
    <ol type="I" start="9"><li>Ninth</li></ol><ol type="A"><li>Upper letter</li></ol>
    <ol type="i" reversed="false"><li>Lower roman</li></ol><ol type="1" start="-2"><li>Negative</li></ol>
    <ol type="url(javascript:bad)" start="1px" style="display:none"><li value="2.5">Invalid</li></ol>
    <ul type="a" start="5" reversed><li type="I" start="9" reversed value="+7">Unordered</li></ul>
    <p start="3" value="4" type="a" reversed>Paragraph</p></main>'''
    result = read_snapshot(tmp_path, raw)
    rendered = html.document_fromstring(result['html'])
    lists = rendered.xpath('//ol')
    assert [node.get('type') for node in lists] == ['a', 'I', 'A', 'i', '1', None]
    assert [node.get('start') for node in lists] == ['4', '9', None, None, '-2', None]
    assert [node.get('reversed') is not None for node in lists] == [True, False, False, True, False, False]
    assert lists[0][1].get('value') == '2' and lists[5][0].get('value') is None
    assert rendered.xpath('//ul/li')[0].get('value') == '+7'
    for node in rendered.xpath('//ul | //ul/li | //p'):
        assert not any(name in node.attrib for name in ('type', 'start', 'reversed'))
    assert 'value' not in rendered.xpath('//p')[0].attrib
    assert not rendered.xpath('//*[@style or @onclick]')
    assert 'url(javascript:bad)' not in result['html']
