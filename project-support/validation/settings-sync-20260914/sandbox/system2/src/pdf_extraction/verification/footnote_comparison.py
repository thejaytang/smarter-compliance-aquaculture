"""Located note-marker/link contradictions, without resolving note semantics.

Original small raised markers and adjacent note text supply the question.
Output links supply the claim. Missing/contradictory links remain human issues;
neither a matching number nor a claimed table grid establishes correct scope.
"""
import re


def inspect(page, records, convert_box):
    def regions(record):
        return [b for r in record.get('references', [])
                if r.get('page_index') == page['page_index']
                and (b := convert_box(r.get('bbox'), page['width'], page['height'],
                                     r.get('coord_origin', 'top_left')))]

    def overlaps(a, b):
        return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])

    links = [(r, link) for r in records for link in r.get('structure', {}).get('related_content', [])
             if link.get('role') == 'notes']
    notes = []
    for line in page['lines']:
        marker = re.fullmatch(r'\s*(\d{1,3})\s*', line['text'])
        a = line['bbox']
        if marker:
            body = next((other for other in page['lines'] if other['engine'] == line['engine']
                         and other is not line and re.search(r'[A-Za-z]', other['text'])
                         and 0 <= other['bbox'][0]-a[2] <= 2*(a[3]-a[1])
                         and min(a[3], other['bbox'][3]) > max(a[1], other['bbox'][1])
                         and a[3]-a[1] < .8*(other['bbox'][3]-other['bbox'][1])), None)
            if body:
                notes.append((marker[1], line, body))
        else:
            # A combined original line is considered only when the output
            # itself explicitly claims a note link at this source position.
            marker = re.match(r'^\s*(\d{1,3})\s+[A-Za-z]', line['text'])
            if marker and any(overlaps(a, b) for _, link in links
                              for b in regions({'references': link.get('references', [])})):
                notes.append((marker[1], line, line))
    if not notes:
        return []
    first_note_y = min(line['bbox'][1] for _, line, _ in notes)
    tables = [r['structure']['table'] for r in records
              if r.get('structure', {}).get('table_scope') == 'whole_table'
              and r['structure'].get('table')]

    def owner_regions(owner):
        bounds = regions(owner)
        # A row view may name its left identifier cell. Expand it only through
        # one unambiguous claimed row, preserving the original cell positions.
        if owner.get('structure', {}).get('table_scope') == 'whole_table':
            return bounds
        for table in tables:
            hits = [c for c in table['cells'] if any(overlaps(a, b) for a in bounds for b in regions(c))]
            rows = {c['row'] for c in hits}
            if len(rows) == 1:
                row = next(iter(rows))
                return bounds + [b for c in table['cells']
                                 if c['row'] <= row < c['row']+c.get('row_span', 1)
                                 for b in regions(c)]
        return bounds

    findings = []
    seen = set()
    for number, marker, body in notes:
        calls = [line for line in page['lines'] if line['engine'] == marker['engine']
                 and line['bbox'][3] < first_note_y
                 and re.search(r'(?<![\w.])'+re.escape(number)+r'(?![\w.])', line['text'])
                 and re.search(r'[A-Za-z]', line['text'])]
        if not calls:
            continue
        target = [r for r in records if r.get('record_kind') != 'structure_only'
                  and re.match(r'^\s*'+re.escape(number)+r'\s', r.get('text', ''))
                  and any(overlaps(body['bbox'], b) for b in regions(r))]
        target_ids = {r['unit_id'] for r in target}
        if not target_ids or (number, tuple(sorted(target_ids))) in seen:
            continue
        seen.add((number, tuple(sorted(target_ids))))
        incoming = [(owner, link) for owner, link in links if link.get('target_unit_id') in target_ids]
        if incoming and any(overlaps(line['bbox'], b) for line in calls
                            for owner, _ in incoming for b in owner_regions(owner)):
            continue
        code = 'output_relation_target_conflict' if incoming else 'source_footnote_relation_missing'
        locs = [dict(page_index=page['page_index'], bbox=line['bbox']) for line in [*calls, marker, body]]
        locs = [r for i, r in enumerate(locs) if r not in locs[:i]]
        findings.append(dict(code=code, severity='critical', page_index=page['page_index'],
            bbox=[min(r['bbox'][0] for r in locs), min(r['bbox'][1] for r in locs),
                  max(r['bbox'][2] for r in locs), max(r['bbox'][3] for r in locs)],
            source_regions=locs, source_text='\n'.join(dict.fromkeys(line['text'] for line in [*calls, marker, body])),
            note_marker=number, output_ids=[r['id'] for r in target],
            unit_ids=sorted(target_ids | {r['unit_id'] for r, _ in incoming}),
            evidence_origin='original_note_marker_and_output_link', confidence=None,
            basis=('An original note and earlier matching marker are located, but no bound output note link exists.'
                   if not incoming else 'The declared note owner does not cover any located original callout. Its claimed row geometry was included; verify the actual owner and scope.'),
            unverified_scope='Number matching and claimed geometry do not establish the semantic scope of a note; source confirmation is still required.'))
    return findings
