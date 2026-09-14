"""Visible omissions must survive HTML cleanup without running source content."""
from bs4 import BeautifulSoup

from pdf_extraction.evidence.material_html_display import describe_html_display


def test_nested_visuals_count_one_region_and_keep_exact_outer_anchor():
    soup = BeautifulSoup('''<main><p data-original-anchor="before">Limit: 5 mg/L.</p>
      <svg data-original-anchor="figure" onload="unsafe()"><text>hidden fallback</text>
      <foreignObject><math data-original-anchor="nested">x</math></foreignObject></svg>
      <p data-original-anchor="after">Except during cleaning.</p></main>''', 'lxml')
    result = describe_html_display(soup)
    assert [(row['kind'], row['anchor']) for row in result['omissions']] == [('svg', 'figure')]
    assert soup.select_one('[data-original-anchor=figure]').name == 'span'
    assert not soup.select('svg, math, [onload]')
    assert soup.select_one('[data-original-anchor=before]').text == 'Limit: 5 mg/L.'
    assert soup.select_one('[data-original-anchor=after]').text == 'Except during cleaning.'
    assert 'hidden fallback' not in str(soup)


def test_missing_resources_distinguish_safe_embedded_images_and_styles():
    soup = BeautifulSoup('''<html><head><link rel="stylesheet" href="https://example.invalid/a.css">
      <style>p{display:none}</style></head><body><p style="color:red">Text</p>
      <img src="https://example.invalid/a.png"><img src="local.png">
      <img src="data:image/png;base64,AAAA"><img src="data:image/svg+xml;base64,AAAA">
      <math data-original-anchor="equation"><mi>x</mi><mo>&lt;</mo><mn>3</mn></math>
      <canvas data-original-anchor="canvas"></canvas></body></html>''', 'lxml')
    result = describe_html_display(soup)
    assert result['resources'] == {'external_stylesheets': 1, 'embedded_styles_removed': 1,
                                   'inline_styles_removed': 1, 'unavailable_images': 3}
    assert [row['anchor'] for row in result['omissions']] == ['equation', 'canvas']
    assert not result['original_layout_preserved']
    assert 'Mathematical expression cannot be displayed' in soup.get_text()
    assert 'Canvas content cannot be displayed' in soup.get_text()


def test_plain_text_is_not_reported_as_visual_loss():
    soup = BeautifulSoup('<main><h1>Title</h1><p>Must retain 5 kg.</p></main>', 'lxml')
    before = str(soup)
    result = describe_html_display(soup)
    assert str(soup) == before
    assert result['omissions'] == [] and result['warnings'] == []


def test_actual_reader_marks_omissions_at_original_anchors_and_keeps_source(tmp_path):
    from hashlib import sha256
    from pdf_extraction.evidence.material_reader import read_material, html_anchor
    from pdf_extraction.formats.html import dom_path

    raw = b'''<html><head><link rel="stylesheet" href="https://example.invalid/layout.css">
      <style>p{display:none}</style><script>unsafe()</script></head><body>
      <h1>Local display fixture</h1><p>Must not exceed 5 mg/L.</p>
      <svg onload="unsafe()"><text>Source figure</text></svg>
      <math><mi>x</mi><mo>&lt;</mo><mn>5</mn></math>
      <iframe src="https://example.invalid/embedded"></iframe>
      <img src="https://example.invalid/image.png" alt="Source figure image">
      <p>Except during cleaning.</p></body></html>'''
    original = BeautifulSoup(raw, 'lxml')
    expected = [html_anchor(dom_path(node)) for node in original.find_all(['svg', 'math', 'iframe'])]
    path = tmp_path/'snapshot.html'
    path.write_bytes(raw)
    result = read_material(path, sha256(raw).hexdigest())
    rendered = BeautifulSoup(result['html'], 'lxml')
    assert [row['anchor'] for row in result['display_fidelity']['omissions']] == expected
    for anchor in expected:
        assert 'cannot be displayed' in rendered.find(id=anchor).text
    assert not rendered.select('svg, math, iframe, script, [onload], [href]')
    assert 'example.invalid' not in result['html'] and 'unsafe()' not in result['html']
    assert 'Must not exceed 5 mg/L.' in rendered.get_text()
    assert 'Except during cleaning.' in rendered.get_text()
    assert 'Image unavailable in offline snapshot' in rendered.get_text()
    assert result['display_fidelity']['resources']['external_stylesheets'] == 1
    assert path.read_bytes() == raw
    assert read_material(path, sha256(raw).hexdigest()) == result
