"""Read immutable registered originals; no conversion jobs, formulas or remote assets.

Paths are resolved by the owning server. Every call verifies the registered digest.
Reader locations are one-based; retained PDF evidence page_index is zero-based.
"""
from __future__ import annotations

import base64
from contextlib import closing
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import re
import json
import os
import tempfile
import math

from .review_preview import sanitized_region

VERSION = 'material-reader/9'
PDF_RENDER_LIMITS = dict(max_dimension=4096, max_pixels=12_000_000,
                         max_requested_width=32768, width_step=64)
MAX_BYTES = 128 * 1024 * 1024


def _bytes(path, expected_hash):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError('original_reader_size_limit')
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != expected_hash:
        raise ValueError('original_version_changed')
    return raw


def html_anchor(locator):
    return 'original-' + sha256(locator.encode()).hexdigest()[:16]


def _scope(kind, identity, label, **location):
    return {'id': identity, 'kind': kind, 'label': label, 'location': location}


def _sheet_info(sheet):
    """Scope helper retained for the separate explicit structural extractor."""
    from openpyxl.utils.cell import coordinate_to_tuple, range_boundaries
    from lxml import etree
    rows, columns = 1, 1
    for cell in sheet.cells:
        row, column = coordinate_to_tuple(cell.coordinate)
        rows, columns = max(rows,row), max(columns,column)
    ranges = list(sheet.merged_ranges)
    for xml in sheet.structure_xml:
        element = etree.fromstring(xml.encode())
        if etree.QName(element).localname == 'dimension': ranges.append(element.get('ref'))
    for region in ranges:
        try:
            _,_,x2,y2 = range_boundaries(region)
            rows, columns = max(rows,y2), max(columns,x2)
        except (ValueError,TypeError): pass
    return dict(name=sheet.name,state=sheet.state,rows=rows,columns=columns,part=sheet.part)


def _manifest(raw, suffix):
    if suffix == '.pdf':
        import pypdfium2 as pdfium
        with pdfium.PdfDocument(raw) as doc:
            count = len(doc)
        return {'kind': 'pdf', 'pages': count, 'scope': [_scope('page', f'page:{p}', f'Page {p}', page=p) for p in range(1, count + 1)], 'warnings': ['Native text can differ from visible page marks. Compare it with the original page image. Scanned pages may require manual transcription; no OCR is run when viewing.']}
    if suffix in {'.html', '.htm'}:
        return {'kind': 'html', 'scope': [_scope('html', 'html:document', 'Complete saved HTML document', anchor='original-document')], 'warnings': []}
    if suffix == '.xlsx':
        from .material_excel_reader import archive_reader
        sheets = archive_reader(raw, inventory_only=True)['sheets']
        return {'kind': 'spreadsheet', 'sheets': sheets, 'scope': [_scope('sheet', 'sheet:' + s['name'], 'Worksheet ' + s['name'], sheet=s['name'], part=s['part']) for s in sheets], 'warnings': ['Cell values and merge relationships are preserved; native styling, charts, drawings and conditional display are not reproduced. Hidden worksheets, rows and columns remain available and are labelled. Formulas are not calculated; saved caches may be missing or stale.']}
    if suffix == '.xls':
        return {'kind': 'unsupported', 'scope': [_scope('legacy_excel', 'legacy:workbook', 'Complete legacy workbook')], 'warnings': ['Legacy XLS requires an explicit human-created XLSX parsing copy with original lineage. The original is preserved; no automatic conversion is performed.']}
    raise ValueError('original_reader_format_not_supported')


def _cached(path, expected_hash, options, produce):
    # Integrity is checked before even a cache hit. The cache is never authority.
    raw = _bytes(path, expected_hash)
    key = sha256(json.dumps([VERSION, expected_hash, options], sort_keys=True).encode()).hexdigest()
    directory = Path(path).parent / '.reader-cache'
    target = directory / (key + '.json')
    try:
        envelope = json.loads(target.read_text())
        cached = envelope.get('result') if isinstance(envelope,dict) else None
        if isinstance(cached,dict) and envelope.get('key') == key and cached.get('schema_version') == VERSION and cached.get('source_sha256') == expected_hash:
            checksum = sha256(json.dumps(cached,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
            if checksum == envelope.get('checksum') and cached.get('kind') in {'pdf','html','spreadsheet','unsupported'}:
                return cached
    except (OSError, ValueError, TypeError):
        pass
    result = {'schema_version': VERSION, 'source_sha256': expected_hash, **produce(raw)}
    temporary = None
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', dir=directory, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump({'key':key,'checksum':sha256(json.dumps(result,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),'result':result}, stream, ensure_ascii=False)
        os.replace(temporary, target)
        entries = sorted(directory.glob('*.json'), key=lambda p:p.stat().st_mtime, reverse=True)
        total = 0
        for entry in entries:
            total += entry.stat().st_size
            if total > 128 * 1024 * 1024 and entry != target:
                entry.unlink(missing_ok=True)
    except OSError:
        pass
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)
    return result


def inspect_original(path, expected_hash):
    """Whole required original scope, including empty pages and worksheets."""
    return _cached(path, expected_hash, {'manifest': True}, lambda raw: _manifest(raw, Path(path).suffix.lower()))


def _html_navigation(soup, original_paths):
    """A reading outline, separate from the complete evidence-location inventory.

    Profile boundaries only choose navigation: they never remove source markup.
    Unknown or ambiguous profiles retain the generic complete-document reader.
    """
    from ..formats.html_profiles import HtmlProfileError, select_profile

    try:
        _, roots = select_profile(soup)
        roots = [root for root in roots if root.name != 'title']
    except HtmlProfileError:
        roots = []
        for selector in ('main, [role="main"]', 'article'):
            matches = soup.select(selector)
            if len(matches) == 1:
                roots = matches
                break
        if not roots:
            roots = [soup.body or soup.html]
    roots = [root for root in roots if root is not None]
    root_ids = {id(root) for root in roots}

    def is_content(element):
        inside = False
        for ancestor in [element, *element.parents]:
            if id(ancestor) in root_ids:
                inside = True
            if ancestor.name in {'head', 'nav', 'aside', 'footer', 'form', 'button',
                                  'select', 'script', 'style', 'ds-breadcrumbs'}:
                return False
            if ancestor.get('role') in {'navigation', 'banner', 'search', 'complementary'}:
                return False
            if {'nav-block', 'sidebar--filters'} & set(ancestor.get('class', [])):
                return False
            if ancestor.name == 'header' and ancestor.parent is soup.body:
                return False
        return inside

    navigation = []
    for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'caption', 'figcaption', 'summary']):
        label = element.get_text(' ', strip=True)
        if not label or not is_content(element):
            continue
        locator = original_paths[id(element)]
        kind = 'heading' if element.name.startswith('h') else 'caption' if element.name != 'summary' else 'disclosure'
        item = {'id': html_anchor(locator), 'locator': locator, 'label': label[:160], 'kind': kind}
        if kind == 'heading':
            item['level'] = int(element.name[1])
        navigation.append(item)

    # Prefer the document's visible title, not a website title in <head>.
    headings = [item for item in navigation if item['kind'] == 'heading']
    if headings:
        default = next((item for item in headings if item['level'] == 1), headings[0])['id']
    elif roots:
        locator = original_paths[id(roots[-1])]
        default = html_anchor(locator)
        navigation.insert(0, {'id': default, 'locator': locator, 'label': 'Document content', 'kind': 'content'})
    else:
        default = 'original-document'
    return navigation, default


def _html(raw):
    from bs4 import BeautifulSoup
    from ..formats.html import dom_path
    from lxml import html, etree
    soup = BeautifulSoup(raw, 'lxml')
    anchors = []
    original_paths = {id(el): dom_path(el) for el in soup.find_all(True)}
    navigation_anchors, default_anchor = _html_navigation(soup, original_paths)
    for element in soup.find_all(True):
        locator = original_paths[id(element)]
        anchor = html_anchor(locator)
        element['data-original-anchor'] = anchor
        if element.name == 'form':
            element.name = 'div'  # Retain readable source text while removing form behavior.
        if element.name not in {'script', 'style', 'head'}:
            anchors.append({'id': anchor, 'locator': locator, 'label': element.get_text(' ', strip=True)[:100] or element.name})
    from .material_html_display import describe_html_display
    display = describe_html_display(soup)
    markup, warnings = sanitized_region(str(soup).encode(), [], full=True)
    warnings.extend(display['warnings'])
    tree = html.document_fromstring(markup)
    # An allowlist complements the shared sanitizer. Source CSS is removed to
    # prevent invisible content and CSS navigation overlays in a whole reader.
    allowed = {'html', 'head', 'body', 'title', 'div', 'span', 'p', 'br', 'hr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'main', 'article', 'section', 'header', 'footer', 'nav', 'aside', 'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td', 'caption', 'col', 'colgroup', 'ul', 'ol', 'li', 'dl', 'dt', 'dd', 'a', 'b', 'strong', 'i', 'em', 'u', 's', 'small', 'sup', 'sub', 'pre', 'code', 'blockquote', 'figure', 'figcaption', 'img', 'details', 'summary', 'mark'}
    for element in list(tree.iter()):
        if not isinstance(element.tag, str):
            if element.getparent() is not None: element.getparent().remove(element)
            continue
        tag = element.tag.lower()
        if tag not in allowed:
            if element.getparent() is not None:
                if tag in {'script', 'style', 'svg', 'math', 'iframe', 'object', 'embed', 'audio', 'video', 'canvas'}:
                    element.drop_tree()
                else:
                    element.drop_tag()
            continue
        anchor = element.get('data-original-anchor')
        safe = {k: v for k, v in element.attrib.items() if k in {'rowspan', 'colspan', 'scope', 'alt', 'title', 'start', 'value', 'src'}}
        if 'src' in safe and not re.fullmatch(r'data:image/(?:png|jpeg|gif|webp);base64,[A-Za-z0-9+/=\s]+', safe['src'], re.I):
            del safe['src']
        element.attrib.clear()
        element.attrib.update(safe)
        if anchor: element.set('id', anchor)
        if tag == 'details': element.set('open', 'open')
        if tag == 'img' and 'src' not in safe:
            placeholder = etree.Element('span')
            placeholder.text = '[Image unavailable in offline snapshot: ' + (safe.get('alt') or 'no alternative text') + ']'
            element.addnext(placeholder)
    body = tree.find('body')
    if body is None: body = tree
    beginning = etree.Element('span', id='original-document')
    body.insert(0, beginning)
    # Only offer targets that survived sanitization. Full source anchor lookup is
    # retained below for compatibility; the outline is not a completeness claim.
    rendered_ids = {element.get('id') for element in body.iter()}
    navigation_anchors = [item for item in navigation_anchors if item['id'] in rendered_ids]
    if default_anchor not in rendered_ids:
        default_anchor = 'original-document'
    csp = "default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'none'; connect-src 'none'; form-action 'none'; base-uri 'none'"
    trusted_style = 'body{font:16px/1.6 system-ui,sans-serif;color:#1e293b;padding:20px;overflow-wrap:anywhere}table{border-collapse:collapse;max-width:100%}td,th{border:1px solid #9ca3af;padding:7px;vertical-align:top}img{max-width:100%}pre{white-space:pre-wrap}:target{outline:3px solid #3977bd;scroll-margin-top:12px}'
    output = '<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="' + csp + '"><style>' + trusted_style + '</style></head>' + html.tostring(body, encoding='unicode') + '</html>'
    warnings.append('Isolated complete saved markup with selectable text. Source scripts, styles and external assets are disabled; all static disclosure content is opened. This reading view does not claim native website styling fidelity.')
    return {'html': output, 'anchors': anchors, 'navigation_anchors': navigation_anchors,
            'display_fidelity': display,
            'default_anchor': default_anchor, 'warnings': warnings,
            'label': 'Complete bound HTML snapshot · offline reading view'}


def _render_width(value):
    if value is None:
        return None
    if type(value) is not int or not 1 <= value <= PDF_RENDER_LIMITS['max_requested_width']:
        raise ValueError('original_render_width_out_of_range: expected integer 1..32768')
    step = PDF_RENDER_LIMITS['width_step']
    return ((value + step - 1) // step) * step


def _pdf_render_scale(width, height, render_width):
    if not all(math.isfinite(v) and v > 0 for v in (width, height)):
        raise ValueError('original_page_dimensions_invalid')
    if render_width is None:
        return min(1.5, 1800 / max(width, height))
    maximum = PDF_RENDER_LIMITS['max_dimension']
    pixels = PDF_RENDER_LIMITS['max_pixels']
    scale = min(render_width / width, maximum / max(width, height),
                math.sqrt(pixels / (width * height)))
    # PDFium rounds each bitmap side upward. Include that rounding in the budget.
    def fits(value):
        w, h = math.ceil(width * value), math.ceil(height * value)
        return max(w, h) <= maximum and w * h <= pixels
    if not fits(scale):
        low, high = 0.0, scale
        for _ in range(48):
            middle = (low + high) / 2
            if fits(middle): low = middle
            else: high = middle
        scale = low
    return scale


def _pdf(raw, page, render_width=None):
    import pypdfium2 as pdfium
    with pdfium.PdfDocument(raw) as doc:
        if type(page) is not int or not 1 <= page <= len(doc): raise ValueError('original_page_out_of_range')
        with closing(doc[page - 1]) as current:
            width, height = current.get_size()
            with closing(current.get_textpage()) as textpage:
                native_text = textpage.get_text_range()
            bitmap = current.render(scale=_pdf_render_scale(width, height, render_width))
            try:
                buf = BytesIO()
                image = bitmap.to_pil()
                image_width, image_height = image.size
                image.save(buf, format='PNG')
            finally: bitmap.close()
    return {'page': page, 'native_text': native_text, 'selectable_native': bool(native_text.strip()),
            'image': 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode(), 'width': width, 'height': height,
            'image_width': image_width, 'image_height': image_height,
            'render_width_normalized': render_width, 'render_limits': dict(PDF_RENDER_LIMITS),
            'text_layer': 'native_unverified' if native_text.strip() else 'unavailable',
            'label': 'Bound original PDF page ' + str(page),
            'page_warning': 'Native text assistance is selectable but not independently verified against visible marks.' if native_text.strip() else 'No native text is available on this page. Use the page image and manually transcribe or supplement missing content. No OCR has run.'}


def read_material(path, expected_hash, *, sheet=None, row=1, column=1, row_count=80, column_count=24, page=1, render_width=None):
    normalized_width = _render_width(render_width)
    options = dict(sheet=sheet, row=row, column=column, row_count=row_count, column_count=column_count, page=page, render_width=normalized_width)
    def produce(raw):
        suffix = Path(path).suffix.lower()
        if suffix == '.xlsx':
            from .material_excel_reader import archive_reader
            window = archive_reader(raw, sheet=sheet, window=(row,column,row_count,column_count))
            manifest = dict(kind='spreadsheet',scope=[_scope('sheet','sheet:'+s['name'],'Worksheet '+s['name'],sheet=s['name'],part=s['part']) for s in window['sheets']], warnings=['Native styling, charts and conditional display are not reproduced. Hidden ranges are labelled. Formulas are not calculated; saved caches may be missing or stale.'])
            return {**manifest, **window}
        result = _manifest(raw, suffix)
        if result['kind'] == 'html': result.update(_html(raw))
        elif result['kind'] == 'pdf': result.update(_pdf(raw, page, normalized_width))
        return result
    result = _cached(path, expected_hash, options, produce)
    if result['kind'] == 'pdf':
        # Original requests may share a normalized cache entry. Request metadata
        # is applied after cache lookup, never borrowed from an earlier caller.
        result = dict(result, render_width_requested=render_width,
                      render_limited=render_width is not None and result['image_width'] < render_width)
    return result
