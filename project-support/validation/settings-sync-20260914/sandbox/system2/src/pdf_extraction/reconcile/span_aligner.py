from __future__ import annotations

import re
from dataclasses import dataclass

from ..models import Block, BlockType, BoundingBox, EvidenceSpan, ResolutionStatus
from ..types import NativeObject, OCRPage, OCRWord, RenderedPage


TOKEN_RE = re.compile(
    r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}|"
    r"<=|>=|!=|≤|≥|<|>|=|§+|\b\d+(?:[.,]\d+)?%?\b|\b[A-Za-zδΔεΕ]+\b",
    re.UNICODE,
)
UNITS = {"mg", "kg", "g", "ml", "l", "usd", "eur", "nok", "%", "cm", "mm", "m", "km"}
NEGATIONS = {"not", "no", "unless", "except", "without", "neither", "never"}
MODALITIES = {"shall", "must", "may", "should", "required", "prohibited"}
SECTION_WORDS = {"section", "article", "paragraph", "clause", "table", "figure", "annex"}


@dataclass(frozen=True)
class TokenEvidence:
    text: str
    bbox: BoundingBox
    source_id: str
    index: int
    criticality: str


def classify_token(text: str, prior_text: str | None = None) -> str | None:
    folded = text.casefold()
    if re.fullmatch(r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}", text):
        return "date"
    if text in {"<", ">", "=", "<=", ">=", "!=", "≤", "≥"}:
        return "comparison_operator"
    if folded in NEGATIONS:
        return "negation"
    if folded in MODALITIES:
        return "modality"
    if folded in UNITS or text.endswith("%"):
        return "unit"
    if text.startswith("§") or (prior_text and prior_text.casefold() in SECTION_WORDS and re.search(r"\d", text)):
        return "section_reference"
    if re.fullmatch(r"\d+(?:[.,]\d+)?%?", text):
        return "numeric"
    return None


def _proportional_bbox(
    text: str, start: int, end: int, bbox: BoundingBox
) -> BoundingBox:
    length = max(1, len(text))
    width = bbox.x1 - bbox.x0
    x0 = bbox.x0 + width * start / length
    x1 = bbox.x0 + width * end / length
    return BoundingBox(x0=x0, y0=bbox.y0, x1=max(x0 + 0.01, x1), y1=bbox.y1)


def _native_tokens(objects: list[NativeObject]) -> list[TokenEvidence]:
    output: list[TokenEvidence] = []
    token_index = 0
    prior: str | None = None
    for item in objects:
        base = BoundingBox(
            x0=item.bbox_points[0], y0=item.bbox_points[1],
            x1=item.bbox_points[2], y1=item.bbox_points[3],
        )
        for match in TOKEN_RE.finditer(item.text):
            criticality = classify_token(match.group(0), prior)
            if criticality:
                output.append(TokenEvidence(
                    match.group(0), _proportional_bbox(item.text, match.start(), match.end(), base),
                    item.id, token_index, criticality,
                ))
            prior = match.group(0)
            token_index += 1
    return output


def _ocr_tokens(ocr_page: OCRPage, page: RenderedPage) -> list[TokenEvidence]:
    output: list[TokenEvidence] = []
    token_index = 0
    prior: str | None = None
    for word in ocr_page.words:
        x0, y0, x1, y1 = page.pixel_to_points(word.bbox)
        base = BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1)
        for match in TOKEN_RE.finditer(word.text):
            criticality = classify_token(match.group(0), prior)
            if criticality:
                output.append(TokenEvidence(
                    match.group(0), _proportional_bbox(word.text, match.start(), match.end(), base),
                    word.id, token_index, criticality,
                ))
            prior = match.group(0)
            token_index += 1
    return output


def _inside(box: BoundingBox, container: BoundingBox) -> bool:
    cx, cy = (box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2
    return container.x0 <= cx <= container.x1 and container.y0 <= cy <= container.y1


def _distance(left: BoundingBox, right: BoundingBox) -> float:
    lx, ly = (left.x0 + left.x1) / 2, (left.y0 + left.y1) / 2
    rx, ry = (right.x0 + right.x1) / 2, (right.y0 + right.y1) / 2
    return abs(lx - rx) + 2 * abs(ly - ry)


def _union(left: BoundingBox | None, right: BoundingBox | None) -> BoundingBox:
    boxes = [box for box in (left, right) if box is not None]
    return BoundingBox(
        x0=min(box.x0 for box in boxes), y0=min(box.y0 for box in boxes),
        x1=max(box.x1 for box in boxes), y1=max(box.y1 for box in boxes),
    )


def _normalized(value: str | None) -> str | None:
    return value.casefold().replace(",", ".") if value else None


def build_evidence_spans(
    block: Block,
    rendered_pages: dict[int, RenderedPage],
    native_words: dict[int, list[NativeObject]],
    ocr_pages: dict[int, OCRPage],
) -> list[EvidenceSpan]:
    spans: list[EvidenceSpan] = []
    span_index = 0
    physical_segments = [] if block.type == BlockType.FIGURE else block.segments
    for segment in physical_segments:
        page = rendered_pages[segment.page_index]
        native_objects_in_segment = [
            item for item in native_words.get(segment.page_index, [])
            if item.text.strip() and _inside(BoundingBox(
                x0=item.bbox_points[0], y0=item.bbox_points[1],
                x1=item.bbox_points[2], y1=item.bbox_points[3],
            ), segment.bbox)
        ]
        native = [
            token for token in _native_tokens(native_objects_in_segment)
            if _inside(token.bbox, segment.bbox)
        ]
        ocr_words_in_segment = []
        for word in ocr_pages[segment.page_index].words:
            x0, y0, x1, y1 = page.pixel_to_points(word.bbox)
            if _inside(BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1), segment.bbox):
                ocr_words_in_segment.append(word)
        ocr = [
            token for token in _ocr_tokens(ocr_pages[segment.page_index], page)
            if _inside(token.bbox, segment.bbox)
        ]
        used_ocr: set[int] = set()
        for native_token in native:
            candidates = [
                (index, token) for index, token in enumerate(ocr)
                if index not in used_ocr and token.criticality == native_token.criticality
            ]
            match_index: int | None = None
            ocr_token: TokenEvidence | None = None
            if candidates:
                match_index, ocr_token = min(
                    candidates,
                    key=lambda item: _distance(native_token.bbox, item[1].bbox)
                    + abs(native_token.index - item[1].index) * 2,
                )
                used_ocr.add(match_index)
            agrees = ocr_token is not None and _normalized(native_token.text) == _normalized(ocr_token.text)
            missing_from_active_ocr = ocr_token is None and bool(ocr_words_in_segment)
            status = (
                ResolutionStatus.RESOLVED
                if agrees or (ocr_token is None and not missing_from_active_ocr)
                else ResolutionStatus.AMBIGUOUS
            )
            resolved = native_token.text if status == ResolutionStatus.RESOLVED else None
            span = EvidenceSpan(
                id=f"span_{block.id}_{span_index:04d}", block_id=block.id,
                segment_id=segment.id, page_index=segment.page_index,
                bbox=_union(native_token.bbox, ocr_token.bbox if ocr_token else None),
                native_text=native_token.text,
                ocr_text=ocr_token.text if ocr_token else None,
                resolved_text=resolved,
                criticality=native_token.criticality,
                resolution_status=status,
                confidence=1.0 if agrees else 0.65 if ocr_token is None and not missing_from_active_ocr else 0.0,
                requires_human_review=status == ResolutionStatus.AMBIGUOUS,
                native_object_refs=[native_token.source_id],
                ocr_word_ids=[ocr_token.source_id] if ocr_token else [],
                trigger_rules=[f"critical_{native_token.criticality}"],
            )
            spans.append(span)
            span_index += 1
        for index, ocr_token in enumerate(ocr):
            if index in used_ocr:
                continue
            missing_from_active_native = bool(native_objects_in_segment)
            span = EvidenceSpan(
                id=f"span_{block.id}_{span_index:04d}", block_id=block.id,
                segment_id=segment.id, page_index=segment.page_index,
                bbox=ocr_token.bbox, ocr_text=ocr_token.text,
                resolved_text=None if missing_from_active_native else ocr_token.text,
                criticality=ocr_token.criticality,
                resolution_status=(
                    ResolutionStatus.AMBIGUOUS if missing_from_active_native else ResolutionStatus.RESOLVED
                ), confidence=0.0 if missing_from_active_native else 0.85,
                requires_human_review=missing_from_active_native,
                ocr_word_ids=[ocr_token.source_id],
                trigger_rules=[f"critical_{ocr_token.criticality}"],
            )
            spans.append(span)
            span_index += 1
    supplemental = next(
        (operation for operation in block.operations if operation.get("operation") == "compound_text_binding"),
        {},
    )
    if block.segments:
        segment = block.segments[0]
        for field, bbox_field in (("index", "index_bbox"), ("note", "note_bbox")):
            text = getattr(block, field)
            raw_bbox = supplemental.get(bbox_field)
            if not text or not isinstance(raw_bbox, list) or len(raw_bbox) != 4:
                continue
            bbox = BoundingBox(x0=raw_bbox[0], y0=raw_bbox[1], x1=raw_bbox[2], y1=raw_bbox[3])
            prior: str | None = None
            for match in TOKEN_RE.finditer(text):
                criticality = classify_token(match.group(0), prior)
                prior = match.group(0)
                if not criticality:
                    continue
                spans.append(EvidenceSpan(
                    id=f"span_{block.id}_{span_index:04d}", block_id=block.id,
                    segment_id=segment.id, page_index=segment.page_index,
                    bbox=_proportional_bbox(text, match.start(), match.end(), bbox),
                    ocr_text=match.group(0), resolved_text=match.group(0),
                    criticality=criticality, resolution_status=ResolutionStatus.RESOLVED,
                    confidence=0.85,
                    trigger_rules=[f"critical_{criticality}", f"compound_{field}"],
                ))
                span_index += 1
    return spans
