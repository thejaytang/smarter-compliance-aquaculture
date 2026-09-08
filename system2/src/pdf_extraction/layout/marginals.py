from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import math
import re

from ..types import LayoutRegion, NativeObject, NativePage, OCRPage, PixelBox, RenderedPage


@dataclass(frozen=True)
class MarginalAnnotation:
    page_index: int
    label: str
    bbox_points: tuple[float, float, float, float]
    text: str
    native_object_ids: tuple[str, ...]


def _normalize_template(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text).strip().casefold()
    normalized = re.sub(r"\bpage\s+\d+\s+of\s+\d+\b", "page {n} of {n}", normalized)
    normalized = re.sub(r"\b\d+\b", "{n}", normalized)
    return normalized


def _candidate_lines(page: NativePage) -> list[tuple[str, NativeObject]]:
    candidates: list[tuple[str, NativeObject]] = []
    for line in page.text_lines:
        text = re.sub(r"\s+", " ", line.text).strip()
        if not text:
            continue
        if not re.search(r"[\w]", text, flags=re.UNICODE):
            continue
        # These are recurring document-body anchors, not running headers. Their
        # numbers and wording intentionally repeat across standards documents.
        if re.match(
            r"^(?:Principle\s+\d+|Criterion\s+\d+(?:\.\d+)*\b|"
            r"Indicator\s*:|Requirement\s*:|"
            r"How do I interpret this requirement\?)",
            text,
            flags=re.IGNORECASE,
        ):
            continue
        y0, y1 = line.bbox_points[1], line.bbox_points[3]
        center = (y0 + y1) / 2
        if center <= page.height_points * 0.10:
            candidates.append(("header", line))
        elif center >= page.height_points * 0.90:
            candidates.append(("footer", line))
    return candidates


def _has_local_run(indices: list[int], minimum: int = 3) -> bool:
    if len(indices) < minimum:
        return False
    run = 1
    for left, right in zip(indices, indices[1:], strict=False):
        run = run + 1 if right == left + 1 else 1
        if run >= minimum:
            return True
    return False


def detect_repeating_marginals(
    pages: list[NativePage],
) -> dict[int, list[MarginalAnnotation]]:
    """Detect global, odd/even, and section-local repeating marginal templates."""
    total = len(pages)
    if total < 2:
        return {}
    grouped: dict[tuple[str, str, int], list[tuple[NativePage, NativeObject]]] = defaultdict(list)
    for page in pages:
        for label, line in _candidate_lines(page):
            # A small y bucket tolerates Word/PDF baseline jitter while keeping
            # separate footer rows distinct.
            y_bucket = round(((line.bbox_points[1] + line.bbox_points[3]) / 2) / 6)
            grouped[(label, _normalize_template(line.text), y_bucket)].append((page, line))

    accepted: dict[int, list[tuple[str, str, NativeObject]]] = defaultdict(list)
    global_min = max(2, math.ceil(total * 0.50))
    for (label, _template, _bucket), matches in grouped.items():
        page_indices = sorted({page.page_index for page, _ in matches})
        global_repeat = len(page_indices) >= global_min
        parity_repeat = False
        for parity in (0, 1):
            available = [page.page_index for page in pages if page.page_index % 2 == parity]
            observed = [index for index in page_indices if index % 2 == parity]
            if len(available) >= 2 and len(observed) >= max(2, math.ceil(len(available) * 0.60)):
                parity_repeat = True
        local_repeat = _has_local_run(page_indices)
        if global_repeat or parity_repeat or local_repeat:
            for page, line in matches:
                accepted[page.page_index].append((label, _template, line))

    annotations: dict[int, list[MarginalAnnotation]] = defaultdict(list)
    for page_index, matches in accepted.items():
        # Keep independently learned templates separate.  Combining every
        # accepted line on a page merely because both are near the top/bottom
        # can enlarge a marginal annotation into genuine body content.
        by_template: dict[tuple[str, str], list[NativeObject]] = defaultdict(list)
        for label, template, line in matches:
            by_template[(label, template)].append(line)
        for (label, _template), lines in by_template.items():
            annotations[page_index].append(MarginalAnnotation(
                page_index=page_index,
                label=label,
                bbox_points=(
                    min(line.bbox_points[0] for line in lines),
                    min(line.bbox_points[1] for line in lines),
                    max(line.bbox_points[2] for line in lines),
                    max(line.bbox_points[3] for line in lines),
                ),
                text=" | ".join(line.text.strip() for line in sorted(
                    lines, key=lambda item: (item.bbox_points[1], item.bbox_points[0])
                )),
                native_object_ids=tuple(line.id for line in lines),
            ))
    return dict(annotations)


def _points_to_pixels(page: RenderedPage, bbox: tuple[float, float, float, float]) -> PixelBox:
    sx = page.width_px / page.width_points
    sy = page.height_px / page.height_points
    x0, y0, x1, y1 = bbox
    return PixelBox(
        max(0, round(x0 * sx)), max(0, round(y0 * sy)),
        min(page.width_px, round(x1 * sx)), min(page.height_px, round(y1 * sy)),
    )


def _overlap_ratio(left: PixelBox, right: PixelBox) -> float:
    intersection = max(0, min(left.x1, right.x1) - max(left.x0, right.x0)) * max(
        0, min(left.y1, right.y1) - max(left.y0, right.y0)
    )
    return intersection / max(1, min(left.area, right.area))


def apply_repeating_marginals(
    regions: list[LayoutRegion],
    page: RenderedPage,
    ocr_page: OCRPage,
    annotations: list[MarginalAnnotation],
) -> list[LayoutRegion]:
    output = list(regions)
    for annotation_index, annotation in enumerate(annotations):
        box = _points_to_pixels(page, annotation.bbox_points)
        # Include small baseline/crop differences around the learned band.
        # Marginal templates often include rules or whitespace objects slightly
        # above/below the repeated text. Cover the learned marginal band, not
        # only the glyph boxes, so completeness does not report those as body loss.
        margin = max(3, round(page.height_px * 0.008))
        margin_x = max(margin, round(page.width_px * 0.015))
        expanded = PixelBox(
            max(0, box.x0 - margin_x), max(0, box.y0 - margin),
            min(page.width_px, box.x1 + margin_x), min(page.height_px, box.y1 + margin),
        )
        matched = [
            region for region in output
            if _overlap_ratio(region.bbox, expanded) >= 0.20
            or expanded.contains_center(region.bbox)
            or region.bbox.contains_center(expanded)
        ]
        ocr_lookup = {word.id: word for word in ocr_page.words}
        marginal_words = [word for word in ocr_page.words if expanded.contains_center(word.bbox)]
        ocr_ids = [word.id for word in marginal_words]
        if matched:
            matched_ids: set[str] = set()
            for region in matched:
                outside_words = [
                    ocr_lookup[word_id] for word_id in region.word_ids
                    if word_id in ocr_lookup
                    and not expanded.contains_center(ocr_lookup[word_id].bbox)
                ]
                if outside_words:
                    region.word_ids = [word.id for word in outside_words]
                    region.native_object_ids = [
                        object_id for object_id in region.native_object_ids
                        if object_id not in annotation.native_object_ids
                    ]
                    region.bbox = PixelBox(
                        min(word.bbox.x0 for word in outside_words),
                        min(word.bbox.y0 for word in outside_words),
                        max(word.bbox.x1 for word in outside_words),
                        max(word.bbox.y1 for word in outside_words),
                    )
                    region.text = " ".join(
                        word.text for word in sorted(
                            outside_words,
                            key=lambda word: (
                                word.block_num, word.paragraph_num,
                                word.line_num, word.bbox.x0, word.bbox.y0,
                            ),
                        )
                    ).strip()
                else:
                    matched_ids.add(region.id)
            output = [region for region in output if region.id not in matched_ids]
            output.append(LayoutRegion(
                id=f"layout_p{page.page_index:04d}_{annotation.label}_template_{annotation_index:02d}",
                label=annotation.label,
                bbox=expanded,
                confidence=max(region.confidence for region in matched),
                text=annotation.text,
                word_ids=ocr_ids,
                native_object_ids=list(annotation.native_object_ids),
            ))
            continue
        output.append(LayoutRegion(
            id=f"layout_p{page.page_index:04d}_{annotation.label}_template_{annotation_index:02d}",
            label=annotation.label,
            bbox=expanded,
            confidence=1.0,
            text=annotation.text,
            word_ids=ocr_ids,
            native_object_ids=list(annotation.native_object_ids),
        ))
    return output


_GLYPH_MARKERS = {"o", "○", "◦", "•", "●", "▪", "▫", "-", "–", "—"}


def annotate_list_markers(
    regions: list[LayoutRegion],
    page: RenderedPage,
    native_words: list[NativeObject],
) -> list[LayoutRegion]:
    """Recover list markers omitted by layout/OCR and infer indentation levels."""
    marked: list[tuple[LayoutRegion, NativeObject]] = []
    for region in regions:
        if region.label not in {"paragraph", "list", "heading", "unknown"}:
            continue
        rx0, ry0, rx1, ry1 = page.pixel_to_points(region.bbox)
        body_words = [
            word for word in native_words
            if rx0 <= (word.bbox_points[0] + word.bbox_points[2]) / 2 <= rx1
            and ry0 <= (word.bbox_points[1] + word.bbox_points[3]) / 2 <= ry1
            and word.text.strip()
        ]
        if not body_words:
            continue
        first_y0 = min(word.bbox_points[1] for word in body_words)
        first_line = [
            word for word in body_words
            if word.bbox_points[1] <= first_y0 + max(6.0, word.bbox_points[3] - word.bbox_points[1])
        ]
        body_candidates = [
            word for word in first_line if word.text.strip() not in _GLYPH_MARKERS
        ]
        if not body_candidates:
            continue
        body_x0 = min(word.bbox_points[0] for word in body_candidates)
        line_y0 = min(word.bbox_points[1] for word in first_line)
        line_y1 = max(word.bbox_points[3] for word in first_line)
        candidates = []
        for word in native_words:
            marker = word.text.strip()
            if marker not in _GLYPH_MARKERS:
                continue
            wx0, wy0, wx1, wy1 = word.bbox_points
            vertical_overlap = max(0.0, min(wy1, line_y1) - max(wy0, line_y0))
            if (
                body_x0 - 40.0 <= wx0 < body_x0
                and 0 <= body_x0 - wx1 <= 24.0
                and vertical_overlap / max(0.1, min(wy1 - wy0, line_y1 - line_y0)) >= 0.30
            ):
                candidates.append(word)
        if not candidates:
            continue
        marker_word = min(candidates, key=lambda word: body_x0 - word.bbox_points[2])
        marker_box = _points_to_pixels(page, marker_word.bbox_points)
        region.bbox = PixelBox(
            min(region.bbox.x0, marker_box.x0), min(region.bbox.y0, marker_box.y0),
            max(region.bbox.x1, marker_box.x1), max(region.bbox.y1, marker_box.y1),
        )
        region.label = "list"
        region.heading_level = None
        region.list_marker = marker_word.text.strip()
        region.indent_points = marker_word.bbox_points[0]
        region.native_object_ids = list(dict.fromkeys(
            region.native_object_ids + [marker_word.id]
        ))
        marked.append((region, marker_word))

    if not marked:
        return regions
    clusters: list[float] = []
    for position in sorted(region.indent_points for region, _ in marked if region.indent_points is not None):
        if not clusters or position - clusters[-1] > 8.0:
            clusters.append(position)
        else:
            clusters[-1] = (clusters[-1] + position) / 2
    for region, _ in marked:
        region.list_level = min(
            range(len(clusters)), key=lambda index: abs(clusters[index] - (region.indent_points or 0))
        )
    # Native PDFs often expose a bullet glyph as its own text line as well as a
    # separate object beside the body line. Once that glyph has been attached
    # as list_marker, remove the marker-only duplicate region.
    consumed_marker_region_ids: set[str] = set()
    for body_region, marker_word in marked:
        marker_box = _points_to_pixels(page, marker_word.bbox_points)
        marker_text = marker_word.text.strip()
        for candidate in regions:
            if candidate.id == body_region.id or candidate.text.strip() != marker_text:
                continue
            if candidate.bbox.contains_center(marker_box):
                consumed_marker_region_ids.add(candidate.id)
    return [
        region for region in regions if region.id not in consumed_marker_region_ids
    ]
