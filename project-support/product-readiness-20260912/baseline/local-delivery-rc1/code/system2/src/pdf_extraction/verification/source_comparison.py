"""Bounded original-to-result comparison. No parser or acceptance writes.

Signals are discrepancy candidates, never calibrated probabilities. Spatial
matching is deliberately local: text elsewhere on a page cannot explain a gap.
"""
from collections import Counter
import re
import unicodedata

from ..contracts.hashing import digest
from .occurrence_accounting import shortfalls
from .structure_comparison import inspect as inspect_structure
from .footnote_comparison import inspect as inspect_footnotes

METHOD = 'original-page-comparison/6'


def tokens(text):
    # A decimal, grouped number, date or clause number is one ordered token.
    # Splitting 1.5 into a bag of '1' and '5' silently equates it with 5.1.
    normalized = unicodedata.normalize('NFKC', text).casefold().replace('−', '-')
    return [re.sub(r'\s+', '', token) for token in re.findall(
        r"(?:[+\-]\s*)?\d+(?:[.,:/]\d+)*|\w+|[≥≤<>%=]", normalized)]


def critical_tokens(values):
    return [t for t in values if any(c.isdigit() for c in t)
            or t in {'not', 'no', 'never', 'without', 'ikke', 'ingen', '≥', '≤', '>', '<', '%'}]


def box(value, width, height, origin='top_left'):
    if isinstance(value, dict):
        value = [value[k] for k in ('x0', 'y0', 'x1', 'y1')]
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    try:
        b = [float(v) for v in value]
    except (TypeError, ValueError):
        return None
    import math
    if not all(math.isfinite(v) for v in b):
        return None
    if max(b) <= 1:
        b = [b[0]*width, b[1]*height, b[2]*width, b[3]*height]
    if origin == 'bottom_left':
        b = [b[0], height-b[3], b[2], height-b[1]]
    return b if b[2] > b[0] and b[3] > b[1] else None


def overlaps(a, b):
    return min(a[2], b[2]) > max(a[0], b[0])-1 and min(a[3], b[3]) > max(a[1], b[1])-1


def compare(page, records):
    """Compare independently observed original lines with located output records.

    Table records must be individual cells, not a concatenated table/page body.
    Original OCR confidence is retained as evidence, not used as acceptance.
    """
    positioned = []
    unverified = list(page.get('unverified', []))
    for record in records:
        if record.get('record_kind') == 'structure_only':
            continue
        regions = [box(r.get('bbox'), page['width'], page['height'], r.get('coord_origin', 'top_left'))
                   for r in record.get('references', []) if r.get('page_index') == page['page_index']]
        regions = [b for b in regions if b]
        if not regions:
            unverified.append({'code': 'output_position_unverified', 'record_id': record['id']})
        else:
            positioned.append((record, regions))
    findings = []
    for line in page['lines']:
        expected = tokens(line['text'])
        if not expected:
            continue
        nearby = [r for r, bounds in positioned if any(overlaps(line['bbox'], b) for b in bounds)]
        # Each spatial candidate is checked separately. Joining unrelated output
        # can hide a missing repeated value or a row/cell ownership error.
        missing = Counter(expected)
        best = None
        for record in nearby:
            residual = Counter(expected) - Counter(tokens(record['text']))
            if best is None or sum(residual.values()) < sum(missing.values()):
                missing, best = residual, record
        if not missing:
            continue
        critical = critical_tokens(missing.elements())
        code = 'source_region_unmapped' if not nearby else 'source_critical_token_difference' if critical else 'source_text_difference'
        compact=lambda text: ''.join(tokens(text))
        if nearby and any(compact(line['text']) in compact(r['text']) for r in nearby):
            code='source_tokenization_conflict'
        elif nearby and not (Counter(expected)-Counter(t for r in nearby for t in tokens(r['text']))):
            code='source_text_fragmented_across_records'
        findings.append({'code': code, 'severity': 'critical' if critical or not nearby else 'major',
                         'page_index': page['page_index'], 'bbox': line['bbox'],
                         'source_text': line['text'], 'missing_tokens': list(missing.elements()),
                         'output_ids': [r['id'] for r in nearby],
                         'unit_ids': sorted({r['unit_id'] for r in nearby}),
                         'evidence_origin': line['engine'], 'ocr_confidence': line.get('confidence'),
                         'basis': 'original_line_to_spatial_output', 'confidence': None})
    # Reverse the comparison too: preserving every original word does not
    # justify an added 'not', changed sign, or invented output sentence.
    for record, bounds in positioned:
        if any(r.get('page_index') != page['page_index'] for r in record.get('references', [])):
            unverified.append({'code': 'cross_page_output_text_not_partitioned', 'record_id': record['id']})
            continue
        nearby = [line for line in page['lines'] if any(overlaps(line['bbox'], b) for b in bounds)]
        # Distinct evidence engines are alternatives, not additive word counts.
        groups = {}
        for line in nearby:
            groups.setdefault(line['engine'], []).append(line)
        observed = tokens(record['text'])
        if not observed:
            continue
        candidates = [(Counter(observed) - Counter(t for line in lines for t in tokens(line['text'])), lines)
                      for lines in groups.values()]
        extra, original_lines = min(candidates, key=lambda item: sum(item[0].values())) if candidates else (Counter(observed), [])
        source_text = '\n'.join(line['text'] for line in original_lines)
        if extra:
            code = 'output_critical_token_difference' if critical_tokens(extra.elements()) else 'output_text_difference'
            # Split OCR/native words remain an explicit uncertainty, not an
            # invented-text claim or a silently accepted normalization.
            if original_lines and ''.join(observed) in ''.join(tokens(source_text)):
                code = 'output_tokenization_conflict'
            severity = 'critical' if critical_tokens(extra.elements()) else 'major'
        elif len(original_lines) == 1 and Counter(observed) == Counter(tokens(source_text)) and observed != tokens(source_text):
            code = 'source_token_order_difference'
            severity = 'critical' if critical_tokens(observed) else 'major'
        else:
            continue
        reverse = {'code': code, 'severity': severity,
                         'page_index': page['page_index'], 'bbox': bounds[0],
                         'source_text': source_text, 'output_text': record['text'],
                         'extra_tokens': list(extra.elements()), 'missing_tokens': [],
                         'output_ids': [record['id']], 'unit_ids': [record['unit_id']],
                         'evidence_origin': original_lines[0]['engine'] if original_lines else 'no_located_original_text',
                         'basis': 'spatial_output_to_original_lines', 'confidence': None}
        existing = next((f for f in findings if record['id'] in f['output_ids']
                         and f['basis'] == 'original_line_to_spatial_output'
                         and any(overlaps(f['bbox'], b) for b in bounds)), None)
        if existing is not None:
            # One human issue may contain both directions of the same local
            # discrepancy. Retain evidence without creating duplicate alarms.
            existing.setdefault('reverse_comparisons', []).append(reverse)
            if severity == 'critical':
                existing['severity'] = 'critical'
        else:
            findings.append(reverse)
    for check in shortfalls(page['lines'], positioned, tokens, overlaps):
        relevant = [page['lines'][i] for i in check['source_line_indices']]
        outputs = [positioned[i][0] for i in check['output_indices']]
        # Do not duplicate an existing located text discrepancy. Record the
        # occurrence evidence there, including its unsatisfied count.
        previous = next((f for f in findings if f['evidence_origin'] == check['engine']
                         and check['token'] in f.get('missing_tokens', [])
                         and any(f['bbox'] == line['bbox'] for line in relevant)), None)
        if previous is not None:
            previous.setdefault('occurrence_checks', []).append(check)
            continue
        regions = [dict(page_index=page['page_index'], bbox=line['bbox']) for line in relevant]
        bounds = [min(r['bbox'][0] for r in regions), min(r['bbox'][1] for r in regions),
                  max(r['bbox'][2] for r in regions), max(r['bbox'][3] for r in regions)]
        related = next((f for f in findings if f['code'] == 'source_occurrence_shortfall'
                        and f['source_regions'] == regions and f['evidence_origin'] == check['engine']), None)
        if related is not None:
            related['occurrence_checks'].append(check)
            related['missing_tokens'].append(check['token'])
            if critical_tokens([check['token']]):
                related['severity'] = 'critical'
            continue
        findings.append({'code': 'source_occurrence_shortfall',
                         'severity': 'critical' if critical_tokens([check['token']]) else 'major',
                         'page_index': page['page_index'], 'bbox': bounds, 'source_regions': regions,
                         'source_text': '\n'.join(line['text'] for line in relevant),
                         'missing_tokens': [check['token']], 'occurrence_checks': [check],
                         'unit_ids': sorted({r['unit_id'] for r in outputs}),
                         'output_ids': [r['id'] for r in outputs], 'evidence_origin': check['engine'],
                         'basis': 'Original occurrences cannot all be assigned without reusing output tokens. The exact missing occurrence may be ambiguous.',
                         'confidence': None})
    # Several output records claiming the same parallel source lines leave
    # column ownership ambiguous. A legitimate numbered paragraph represented
    # by one record is not itself an ownership conflict.
    def intersects_interior(a, b):
        return (min(a[2], b[2]) > max(a[0], b[0])
                and min(a[3], b[3])-max(a[1], b[1]) > .25*(a[3]-a[1]))

    conflicts = {}
    for i, left in enumerate(page['lines']):
        a = left['bbox']
        for right in page['lines'][i+1:]:
            if left['engine'] != right['engine']:
                continue
            b = right['bbox']
            shared_height = min(a[3], b[3])-max(a[1], b[1])
            gap = max(a[0], b[0])-min(a[2], b[2])
            if shared_height <= .5*min(a[3]-a[1], b[3]-b[1]) or gap <= max(a[3]-a[1], b[3]-b[1]):
                continue
            claims = tuple(n for n, (_, bounds) in enumerate(positioned)
                           if any(intersects_interior(a, region) for region in bounds)
                           and any(intersects_interior(b, region) for region in bounds))
            if len(claims) > 1:
                conflicts.setdefault(claims, set()).update([tuple(a), tuple(b)])
    for claims, regions in conflicts.items():
        selected = [positioned[i][0] for i in claims]
        unverified.append({'code': 'output_spatial_ownership_ambiguous',
                           'page_index': page['page_index'], 'record_id': selected[0]['id'],
                           'output_ids': [r['id'] for r in selected],
                           'unit_ids': sorted({r['unit_id'] for r in selected}),
                           'bbox': [min(b[0] for b in regions), min(b[1] for b in regions),
                                    max(b[2] for b in regions), max(b[3] for b in regions)],
                           'source_regions': [dict(page_index=page['page_index'], bbox=list(b)) for b in sorted(regions)],
                           'basis': 'Multiple output records claim the same separate column text. Verify cell/column ownership or correct positions.'})
    for region in page.get('unrecognized_regions', []):
        findings.append({'code': 'source_visual_region_unverified', 'severity': 'major',
                         'page_index': page['page_index'], 'bbox': region,
                         'source_text': '', 'unit_ids': [], 'output_ids': [], 'confidence': None,
                         'evidence_origin': 'raster_ink',
                         'basis': 'Original ink without native/OCR word evidence; inspect text, table or illustration role.'})
    structure_findings, structure_scope = inspect_structure(page, records, box)
    findings.extend(structure_findings)
    findings.extend(inspect_footnotes(page, records, box))
    unverified.extend(structure_scope)
    for finding in findings:
        finding['id'] = digest(finding)[:24]
    return {'method': METHOD, 'findings': findings, 'unverified': unverified,
            'signals': {'original_lines': len(page['lines']), 'output_records': len(records),
                        'structure_records': sum(r.get('record_kind') == 'structure_only' for r in records),
                        'discrepant_lines': sum(f['basis'] == 'original_line_to_spatial_output' for f in findings)},
            'confidence': None, 'acceptance': 'not_assessed'}
