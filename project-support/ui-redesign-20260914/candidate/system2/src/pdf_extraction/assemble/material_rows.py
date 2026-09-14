"""Reassemble same-row native fragments only when the source text proves the join."""
from hashlib import sha256
import re

MARKER = re.compile(r'(?:\d+(?:\.\d+)+[.)]?|\d+[.)]|[a-z][.)]|[•●▪◦])')


def join_source_rows(blocks, page_width, native_text, lines, image_boxes=()):
    """Return derived rows and complete member evidence, without rewriting source tokens.

    Called in native order before geometric sorting. Separate columns, table/image
    intersections, numbering markers, missing source text and ambiguous geometry
    remain separate. Offsets describe whitespace-normalized native text, not glyphs.
    """
    normalized = re.sub(r'\s+', ' ', native_text).strip()
    alignment, cursor = {}, 0
    for index, line in enumerate(lines):
        text = re.sub(r'\s+', ' ', line.text).strip()
        start = normalized.find(text, cursor) if text else -1
        if start >= 0:
            alignment[line.id] = (index, start, start + len(text))
            cursor = start + len(text)
    obstacles = [*image_boxes, *[b['source_refs'][0]['bbox'] for b in blocks if b['type'] in {'table', 'image', 'heading'}]]

    def eligible(block):
        return (block['type'] == 'text' and block.get('text', '').strip()
                and not MARKER.fullmatch(block['text'].strip())
                and len(block.get('source_refs', [])) == 1
                and block['source_refs'][0].get('native_id') in alignment)

    output, groups, index = [], [], 0
    while index < len(blocks):
        first = blocks[index]; members = [first]; index += 1
        if not eligible(first):
            output.append(first); continue
        ref = first['source_refs'][0]
        bounds = list(ref['bbox'])
        common_top, common_bottom = bounds[1], bounds[3]
        while index < len(blocks) and eligible(blocks[index]):
            left, right = members[-1], blocks[index]
            a, b = left['source_refs'][0], right['source_refs'][0]
            ai, start, end = alignment[a['native_id']]
            bi, next_start, next_end = alignment[b['native_id']]
            x0, y0, x1, y1 = a['bbox']; bx0, by0, bx1, by1 = b['bbox']
            gap = bx0-x1
            overlap = max(0., min(y1, by1)-max(y0, by0)) / max(.1, min(y1-y0, by1-by0))
            source_gap = normalized[end:next_start]
            union = [min(bounds[0], bx0), min(bounds[1], by0), max(bounds[2], bx1), max(bounds[3], by1)]
            if (a.get('page_index') != b.get('page_index') or bi != ai+1
                    or next_start < end or source_gap.strip()
                    or not 0 <= gap <= min(page_width*.025, max(6., min(y1-y0, by1-by0)*1.6))
                    or overlap < .7 or min(common_bottom, by1) <= max(common_top, by0)
                    or any(union[0] < ox1 and union[2] > ox0 and union[1] < oy1 and union[3] > oy0
                           for ox0, oy0, ox1, oy1 in obstacles)):
                break
            members.append(right); index += 1; bounds = union
            common_top, common_bottom = max(common_top, by0), min(common_bottom, by1)
        if len(members) == 1:
            output.append(first); continue
        start = alignment[ref['native_id']][1]
        end = alignment[members[-1]['source_refs'][0]['native_id']][2]
        identity = 'block-' + sha256(('native-row:'+':'.join(b['id'] for b in members)).encode()).hexdigest()[:24]
        union_ref = {key: ref[key] for key in ('scope_id', 'page_index', 'page') if key in ref}
        union_ref['bbox'] = bounds
        row = {**first, 'id':identity, 'text':normalized[start:end],
               'source_refs':[union_ref, *[r for member in members for r in member['source_refs']]]}
        output.append(row)
        groups.append({'operation':'source_exact_native_row', 'row_block_id':identity,
                       'normalized_native_interval':[start,end], 'source_text':normalized[start:end],
                       'fragments':members})
    return output, groups
