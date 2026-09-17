from __future__ import annotations

import re

from ..models import Block, NoteSpan


def populate_note_spans(blocks: dict[str, Block]) -> None:
    for block in blocks.values():
        if not block.note:
            continue
        spans: list[NoteSpan] = []
        evidence = next(
            (operation for operation in block.operations if operation.get("operation") == "compound_text_binding"),
            {},
        )
        raw_bbox = evidence.get("note_bbox")
        bbox = None
        if isinstance(raw_bbox, list) and len(raw_bbox) == 4:
            from ..models import BoundingBox
            bbox = BoundingBox(x0=raw_bbox[0], y0=raw_bbox[1], x1=raw_bbox[2], y1=raw_bbox[3])
        for part in re.split(r"\s*;\s*", block.note):
            folded = part.casefold()
            role = "source" if folded.startswith("source") else "note" if folded.startswith(("note", "notes")) else "warning" if folded.startswith(("warning", "caution")) else "unknown"
            spans.append(NoteSpan(
                text=part, role=role, bbox=bbox,
                confidence=1.0 if role != "unknown" else 0.6,
            ))
        block.note_spans = spans
