"""Coalesce touching font-run fragments only when native characters agree."""
from dataclasses import replace
from ..types import NativeObject, NativePage

VERSION = 'native-character-spacing/1'
TOLERANCE_POINTS = .12


def coalesce(page: NativePage) -> tuple[list[NativeObject], list[dict]]:
    if not page.characters:
        return list(page.words), []
    joins = {}
    t = TOLERANCE_POINTS
    for i, left in enumerate(page.words):
        lx, ly, rx, by = left.bbox_points
        if not left.font_key or left.from_ocr or not left.text.strip():
            continue
        candidates = [(j, right) for j, right in enumerate(page.words)
            if j != i and right.font_key and right.font_key != left.font_key
            and not right.from_ocr and right.text.strip()
            and abs(right.bbox_points[1]-ly) <= t
            and abs(right.bbox_points[3]-by) <= t
            and -t <= right.bbox_points[0]-rx <= t
            and right.bbox_points[0] > lx]
        if len(candidates) != 1:
            continue
        j, right = candidates[0]
        edge = right.bbox_points[2]
        chars = sorted([c for c in page.characters
            if lx <= (c.bbox_points[0]+c.bbox_points[2])/2 <= edge
            and abs(c.bbox_points[1]-ly) <= t
            and abs(c.bbox_points[3]-by) <= t], key=lambda c:c.bbox_points[0])
        # Exact characters include any encoded whitespace. No dictionary,
        # punctuation substitution, cross-line joining or OCR inference.
        if ''.join(c.text for c in chars) != left.text + right.text:
            continue
        joins[i] = j
    incoming = {}
    for i,j in joins.items():incoming.setdefault(j,[]).append(i)
    joins={i:j for i,j in joins.items() if len(incoming[j])==1}
    consumed=set(joins.values());words=[];operations=[]
    for i, first in enumerate(page.words):
        if i in consumed:continue
        chain=[first];j=i
        while j in joins:
            j=joins[j];chain.append(page.words[j])
        if len(chain)==1:
            words.append(first);continue
        value=replace(first,text=''.join(w.text for w in chain),
            bbox_points=(first.bbox_points[0],first.bbox_points[1],chain[-1].bbox_points[2],first.bbox_points[3]),
            confidence=min(w.confidence for w in chain))
        words.append(value)
        operations.append(dict(method=VERSION,source_word_ids=[w.id for w in chain],
            source_texts=[w.text for w in chain],text=value.text,bbox_points=value.bbox_points))
    return words,operations
