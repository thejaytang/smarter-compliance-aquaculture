"""Acquire one original PDF page without invoking the extraction pipeline.

Native evidence: Poppler. Raster evidence: Poppler + local Tesseract plus ink
regions. Shared-engine use is explicitly disclosed and remains unverified.
"""
import csv
from functools import lru_cache
from hashlib import sha256
import io
from pathlib import Path
import subprocess
import tempfile

import cv2


def _run(args):
    return subprocess.run(args, check=True, capture_output=True, timeout=45).stdout


@lru_cache(maxsize=1)
def versions():
    result = {}
    for name, flag in [('pdftotext', '-v'), ('pdftoppm', '-v'), ('tesseract', '--version')]:
        try:
            run = subprocess.run([name, flag], capture_output=True, check=True, timeout=5)
            result[name] = (run.stdout+run.stderr).decode(errors='replace').splitlines()[0]
        except (OSError, subprocess.SubprocessError, IndexError):
            result[name] = 'unavailable'
    result['opencv'] = cv2.__version__
    return result


def acquire(path, page_index, *, parser_engines=(), language='eng'):
    path = Path(path).resolve()
    if type(page_index) is not int or page_index < 0:
        raise ValueError('invalid_original_page')
    source_hash = sha256(path.read_bytes()).hexdigest()
    page = {'page_index': page_index, 'lines': [], 'unverified': [], 'unrecognized_regions': [],
            'source_sha256': source_hash, 'parser_engines': list(parser_engines), 'evidence': [],
            'tool_versions': versions()}
    with tempfile.TemporaryDirectory(prefix='source-verify-') as temp:
        dest = Path(temp)
        n = str(page_index+1)
        # TSV avoids the installed Poppler HTML-metadata crash on empty PDF
        # Keywords, while retaining positioned word evidence from the original.
        raw = _run(['pdftotext', '-f', n, '-l', n, '-tsv', str(path), '-'])
        native = list(csv.DictReader(io.StringIO(raw.decode()), delimiter='\t'))
        original = next((e for e in native if e['level'] == '1'), None)
        if original is None:
            raise ValueError('original_page_not_found')
        page.update(width=float(original['width']), height=float(original['height']))
        native_boxes = []
        groups = {}
        for word in native:
            if word['level'] != '5':
                continue
            x,y,rw,rh = [float(word[k]) for k in ('left','top','width','height')]
            groups.setdefault(tuple(word[k] for k in ('par_num','block_num','line_num')), []).append((word['text'],[x,y,x+rw,y+rh]))
        for words in groups.values():
            bounds = [b for _, b in words]
            native_boxes.extend(bounds)
            page['lines'].append({'text': ' '.join(t for t, _ in words),
                                  'bbox': [min(b[0] for b in bounds),min(b[1] for b in bounds),max(b[2] for b in bounds),max(b[3] for b in bounds)],
                                  'engine': 'poppler'})
        page['evidence'].append({'engine': 'poppler', 'sha256': sha256(raw).hexdigest()})
        _run(['pdftoppm', '-f', n, '-l', n, '-singlefile', '-scale-to', '1800', '-png', str(path), str(dest/'page')])
        raster = dest/'page.png'
        gray = cv2.imread(str(raster), cv2.IMREAD_GRAYSCALE)
        if gray is None:
            raise ValueError('original_render_unavailable')
        h, w = gray.shape
        page['evidence'].append({'engine': 'poppler_raster', 'sha256': sha256(raster.read_bytes()).hexdigest()})
        # OCR also probes native pages, so scan inserts/mixed regions are not
        # omitted just because the page has some selectable text.
        ocr_boxes = []
        try:
            tsv = _run(['tesseract', str(raster), 'stdout', '-l', language, '--psm', '3', 'tsv'])
            page['evidence'].append({'engine': 'tesseract', 'sha256': sha256(tsv).hexdigest(), 'language': language})
            groups = {}
            for word in csv.DictReader(io.StringIO(tsv.decode()), delimiter='\t'):
                if word['level'] != '5' or not word.get('text', '').strip():
                    continue
                x, y, rw, rh = [int(word[k]) for k in ('left', 'top', 'width', 'height')]
                b = [x*page['width']/w, y*page['height']/h, (x+rw)*page['width']/w, (y+rh)*page['height']/h]
                ocr_boxes.append(b)
                # Native overlap is evaluated per word, never per page/image.
                cx, cy = (b[0]+b[2])/2, (b[1]+b[3])/2
                if any(a[0]-1 <= cx <= a[2]+1 and a[1]-1 <= cy <= a[3]+1 for a in native_boxes):
                    continue
                key = tuple(word[k] for k in ('block_num', 'par_num', 'line_num'))
                groups.setdefault(key, []).append((word['text'], b, float(word['conf'])))
            for words in groups.values():
                page['lines'].append({'text': ' '.join(t for t, _, _ in words),
                    'bbox': [min(b[0] for _, b, _ in words), min(b[1] for _, b, _ in words),
                             max(b[2] for _, b, _ in words), max(b[3] for _, b, _ in words)],
                    'engine': 'tesseract', 'confidence': min(c for _, _, c in words)})
        except (OSError, subprocess.SubprocessError, ValueError):
            page['unverified'].append({'code': 'ocr_evidence_unavailable', 'page_index': page_index})
        ink = cv2.threshold(gray, 210, 255, cv2.THRESH_BINARY_INV)[1]
        for b in native_boxes+ocr_boxes:
            cv2.rectangle(ink, (max(0, int(b[0]*w/page['width'])-2), max(0, int(b[1]*h/page['height'])-2)),
                          (int(b[2]*w/page['width'])+2, int(b[3]*h/page['height'])+2), 0, -1)
        joined = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (13, 3)))
        contours, _ = cv2.findContours(joined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            x, y, rw, rh = cv2.boundingRect(contour)
            if rw*rh >= 100 and rw >= 5 and rh >= 5:
                page['unrecognized_regions'].append([x*page['width']/w, y*page['height']/h,
                                                      (x+rw)*page['width']/w, (y+rh)*page['height']/h])
        page['unrecognized_regions'].sort(key=lambda b: (b[1], b[0]))
    used = {line['engine'] for line in page['lines']}
    for engine in used & set(parser_engines):
        page['unverified'].append({'code': 'shared_extraction_engine', 'engine': engine,
                                  'page_index': page_index})
    if not parser_engines:
        page['unverified'].append({'code': 'extraction_lineage_unknown', 'page_index': page_index})
    page['unverified'].extend({'code': code, 'page_index': page_index} for code in (
        'table_grid_and_merged_cells_not_independently_verified', 'reading_order_not_independently_verified',
        'footnote_and_cross_page_links_not_independently_verified', 'illustration_role_not_independently_verified',
        'output_insertions_and_token_order_not_independently_verified'))
    if sha256(path.read_bytes()).hexdigest() != source_hash:
        raise ValueError('original_changed_during_verification')
    return page
