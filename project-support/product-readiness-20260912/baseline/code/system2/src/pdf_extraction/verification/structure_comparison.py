"""Bounded contradictions in output structure; not independent table recognition.

Claimed row/column geometry is compared with claimed PDF positions. Original
snippets make the conflict inspectable; they do not certify either claim.
"""
from itertools import combinations
from fractions import Fraction


def inspect(page, records, convert_box):
    findings, unverified = [], []
    relations = {}

    def regions(refs):
        result = []
        for ref in refs:
            if ref.get('page_index') != page['page_index']:
                continue
            b = convert_box(ref.get('bbox'), page['width'], page['height'], ref.get('coord_origin', 'top_left'))
            if b:
                result.append(dict(page_index=page['page_index'], bbox=b))
        return result

    def evidence(record, refs):
        located = regions(refs)
        result = dict(page_index=page['page_index'], unit_ids=[record['unit_id']],
                      output_ids=[record['id']], record_id=record['id'], confidence=None)
        if located:
            result.update(source_regions=located, bbox=[
                min(r['bbox'][0] for r in located), min(r['bbox'][1] for r in located),
                max(r['bbox'][2] for r in located), max(r['bbox'][3] for r in located)])
        return result

    def issue(record, code, basis, refs, **extra):
        details = evidence(record, refs)
        snippets = [line['text'] for line in page['lines'] if any(
            min(line['bbox'][2], r['bbox'][2]) > max(line['bbox'][0], r['bbox'][0])
            and min(line['bbox'][3], r['bbox'][3]) > max(line['bbox'][1], r['bbox'][1])
            for r in details.get('source_regions', []))]
        cells = record.get('structure', {}).get('table', {}).get('cells', [])
        compared = [{k: c[k] for k in ('id','row','column','row_span','column_span') if k in c}
                    for c in cells if c['id'] in extra.get('cell_ids', [])]
        previous = next((f for f in findings if f['record_id'] == record['id']
                         and f['code'] == code and f.get('axis') == extra.get('axis')), None)
        if previous is None:
            findings.append(dict(details, code=code, severity='critical', basis=basis,
                                 source_text='\n'.join(dict.fromkeys(snippets)),
                                 evidence_origin='output_structure_and_claimed_positions',
                                 compared_structure=compared, conflicts=[extra], **extra))
        else:
            previous['conflicts'].append(extra)
            previous['cell_ids'] = sorted(set(previous.get('cell_ids', [])+extra.get('cell_ids', [])))
            previous['source_text'] = '\n'.join(dict.fromkeys(previous['source_text'].splitlines()+snippets))
            for key, values in (('source_regions', details.get('source_regions', [])), ('compared_structure', compared)):
                for value in values:
                    if value not in previous.setdefault(key, []):
                        previous[key].append(value)
            located = previous.get('source_regions', [])
            if located:
                previous['bbox'] = [min(r['bbox'][0] for r in located), min(r['bbox'][1] for r in located),
                                    max(r['bbox'][2] for r in located), max(r['bbox'][3] for r in located)]

    # Compare only spatially separate, aligned peers. Side-by-side columns,
    # nested row/table views and cross-page assemblies do not establish a
    # simple vertical reading order. This detects a contradiction, not a
    # complete independent reconstruction of the reading sequence.
    ordered = []
    for record in records:
        claim = record.get('structure', {})
        if (claim.get('schema') != 'pdf-output-structure/1'
                or claim.get('table_scope') in {'selected_cells', 'row'}
                or claim.get('assembly_definition')):
            continue
        try:
            key = Fraction(str(claim['reading_order_key']))
        except (KeyError, ValueError, ZeroDivisionError):
            continue
        refs = record.get('references', [])
        if any(r.get('page_index') != page['page_index'] for r in refs):
            continue
        located = regions(refs)
        if not located:
            continue
        bounds = [min(r['bbox'][0] for r in located), min(r['bbox'][1] for r in located),
                  max(r['bbox'][2] for r in located), max(r['bbox'][3] for r in located)]
        ordered.append((record, key, bounds))
    for (left, lk, a), (right, rk, b) in combinations(ordered, 2):
        if left['unit_id'] == right['unit_id']:
            continue
        overlap = min(a[2], b[2]) - max(a[0], b[0])
        if overlap <= .5 * min(a[2]-a[0], b[2]-b[0]):
            continue
        if (a[3] < b[1] and lk > rk) or (b[3] < a[1] and rk > lk):
            issue(left, 'output_reading_order_conflict',
                  'Reading-order keys reverse two vertically separate, horizontally aligned source regions. Verify the intended reading sequence.',
                  left.get('references', []) + right.get('references', []),
                  related_output_ids=[left['id'], right['id']],
                  reading_order_keys=[str(lk), str(rk)])

    for record in records:
        claim = record.get('structure', {})
        if claim.get('schema') != 'pdf-output-structure/1':
            if record.get('record_kind') == 'structure_only':
                unverified.append(dict(evidence(record, record.get('references', [])),
                                       code='output_structure_schema_unverified'))
            continue
        # An explicit typed link is a checkable question, not proof that its
        # marker/meaning belongs to the selected source item.
        for link in claim.get('related_content', []):
            owner = link.get('inherited_from_table', record['unit_id'])
            key = (owner, link['role'], link['target_unit_id'])
            if key not in relations:
                relations[key] = dict(evidence(record, record.get('references', [])),
                    code='output_relation_source_unverified', role=link['role'],
                    target_unit_id=link['target_unit_id'], target_references=link.get('references', []),
                    basis='The output link is retained. Its original marker, scope and target meaning require source confirmation.')
            value = relations[key]
            value['unit_ids'] = sorted(set(value['unit_ids']+[record['unit_id'], link['target_unit_id']]))

        assembly = claim.get('table_assembly', {})
        if claim.get('assembly_definition'):
            refs = record.get('references', [])
            scope = dict(evidence(record, refs), code='output_cross_page_relation_unverified',
                         basis='Page-order consistency does not establish that fragments form one table or that headers/notes carry across pages.')
            unverified.append(scope)
            if assembly.get('error'):
                issue(record, 'output_table_assembly_invalid', 'The effective assembly cannot be resolved.',
                      refs, assembly_error=assembly['error'])
            else:
                prior = None
                for fragment in assembly.get('fragments', []):
                    p = sorted({r['page_index'] for r in fragment.get('references', [])
                                if type(r.get('page_index')) is int})
                    if p and prior is not None and min(p) <= prior:
                        issue(record, 'output_table_fragment_order_conflict',
                              'Logical table fragments contradict their claimed physical page order.',
                              refs, fragment_unit_ids=[f['unit_id'] for f in assembly['fragments']])
                        break
                    prior = max(p) if p else None

        table = claim.get('table')
        # Physical owners check cells once. Row views and logical assemblies
        # retain their mappings but must not multiply cell alarms.
        if not table or claim.get('table_scope') != 'whole_table':
            continue
        cells = table['cells']
        valid = []
        for cell in cells:
            values = [cell.get(k) for k in ('row', 'column', 'row_span', 'column_span')]
            rows, cols = table.get('row_count'), table.get('column_count')
            good = (all(type(v) is int for v in values+[rows, cols]) and rows > 0 and cols > 0
                    and values[0] >= 0 and values[1] >= 0 and values[2] > 0 and values[3] > 0
                    and values[0]+values[2] <= rows and values[1]+values[3] <= cols)
            if not good:
                issue(record, 'output_table_cell_outside_grid',
                      'A cell row/column/span contradicts the declared table dimensions.',
                      cell.get('references', []), cell_ids=[cell['id']])
            else:
                valid.append(cell)
        for left, right in combinations(valid, 2):
            row_overlap = min(left['row']+left['row_span'], right['row']+right['row_span']) > max(left['row'], right['row'])
            col_overlap = min(left['column']+left['column_span'], right['column']+right['column_span']) > max(left['column'], right['column'])
            refs = left.get('references', [])+right.get('references', [])
            if row_overlap and col_overlap:
                issue(record, 'output_table_grid_overlap', 'Two cells occupy the same logical grid slot.',
                      refs, cell_ids=[left['id'], right['id']])
                continue
            a, b = regions(left.get('references', [])), regions(right.get('references', []))
            if len(a) != 1 or len(b) != 1:
                continue
            a, b = a[0]['bbox'], b[0]['bbox']
            # Strict separation plus overlapping orthogonal extents avoids
            # treating normal merged cells or staggered text as a reversal.
            for axis, logical_overlap in (('row', col_overlap), ('column', row_overlap)):
                start = 1 if axis == 'row' else 0
                other = 1-start
                spatial_overlap = min(a[other+2], b[other+2])-max(a[other], b[other])
                if not logical_overlap or spatial_overlap <= .5*min(a[other+2]-a[other], b[other+2]-b[other]):
                    continue
                before = left[axis]+left[axis+'_span'] <= right[axis]
                after = right[axis]+right[axis+'_span'] <= left[axis]
                if (before and b[start+2] <= a[start]) or (after and a[start+2] <= b[start]):
                    issue(record, 'output_table_position_order_conflict',
                          'Declared grid order contradicts claimed PDF positions under top-to-bottom rows and left-to-right columns.',
                          refs, axis=axis, cell_ids=[left['id'], right['id']])
    unverified.extend(relations.values())
    return findings, unverified
