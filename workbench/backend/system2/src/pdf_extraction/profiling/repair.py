from __future__ import annotations

import re

from ..types import LayoutRegion, NativePage, OCRPage, PixelBox, RenderedPage
from .models import DocumentProfile, RequirementCandidate


def _points_to_pixels(page: RenderedPage, bbox: tuple[float, float, float, float]) -> PixelBox:
    sx = page.width_px / page.width_points
    sy = page.height_px / page.height_points
    x0, y0, x1, y1 = bbox
    margin_x = max(4, round(page.width_px * 0.006))
    margin_y = max(4, round(page.height_px * 0.006))
    return PixelBox(
        max(0, round(x0 * sx) - margin_x),
        max(0, round(y0 * sy) - margin_y),
        min(page.width_px, round(x1 * sx) + margin_x),
        min(page.height_px, round(y1 * sy) + margin_y),
    )


def _intersection_ratio(left: PixelBox, right: PixelBox) -> float:
    area = max(0, min(left.x1, right.x1) - max(left.x0, right.x0)) * max(
        0, min(left.y1, right.y1) - max(left.y0, right.y0)
    )
    return area / max(1, min(left.area, right.area))


def _repair_candidate(
    regions: list[LayoutRegion],
    page: RenderedPage,
    ocr_page: OCRPage,
    native_page: NativePage,
    candidate: RequirementCandidate,
    template_id: str,
) -> list[LayoutRegion]:
    box = _points_to_pixels(page, candidate.bbox_points)
    boundary_px = round(
        candidate.column_boundary_points * page.width_px / page.width_points
    )
    ocr_ids = [word.id for word in ocr_page.words if box.contains_center(word.bbox)]
    native_ids = [
        word.id for word in native_page.words
        if candidate.bbox_points[0] <= (word.bbox_points[0] + word.bbox_points[2]) / 2 <= candidate.bbox_points[2]
        and candidate.bbox_points[1] <= (word.bbox_points[1] + word.bbox_points[3]) / 2 <= candidate.bbox_points[3]
    ]
    word_lookup = {word.id: word for word in ocr_page.words}
    candidate_word_ids = set(ocr_ids)
    candidate_native_ids = set(native_ids)
    repaired: list[LayoutRegion] = []
    consumed_any = False
    for region in regions:
        if region.label in {"header", "footer", "figure"}:
            repaired.append(region)
            continue
        geometric_match = (
            box.contains_center(region.bbox)
            or _intersection_ratio(region.bbox, box) >= 0.15
        )
        inside_ids = [word_id for word_id in region.word_ids if word_id in candidate_word_ids]
        if not inside_ids and not geometric_match:
            repaired.append(region)
            continue
        outside_words = [
            word_lookup[word_id] for word_id in region.word_ids
            if word_id not in candidate_word_ids and word_id in word_lookup
        ]
        if outside_words:
            consumed_any = True
            region.word_ids = [word.id for word in outside_words]
            region.native_object_ids = [
                object_id for object_id in region.native_object_ids
                if object_id not in candidate_native_ids
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
            if region.label == "table":
                residual = re.sub(r"\s+", " ", region.text).strip().casefold()
                if not (
                    "indicator:" in residual
                    and "requirement:" in residual
                    and re.search(r"\b\d+(?:\.\d+)+\b", residual)
                ):
                    region.label = "paragraph"
                    region.profile_template_id = None
                    region.profile_repair = False
                    region.profile_column_boundary_px = None
            repaired.append(region)
            continue
        consumed_any = True

    if not consumed_any and not ocr_ids:
        return regions
    safe_number = re.sub(r"\W+", "_", candidate.requirement_number).strip("_")
    repaired.append(LayoutRegion(
        id=f"layout_p{page.page_index:04d}_profile_requirement_{safe_number}",
        label="table",
        bbox=box,
        confidence=candidate.confidence,
        text=" ".join(
            word.text for word in sorted(
                (word_lookup[word_id] for word_id in ocr_ids if word_id in word_lookup),
                key=lambda word: (
                    word.block_num, word.paragraph_num,
                    word.line_num, word.bbox.x0, word.bbox.y0,
                ),
            )
        ).strip(),
        word_ids=list(dict.fromkeys(ocr_ids)),
        native_object_ids=list(dict.fromkeys(native_ids)),
        profile_template_id=template_id,
        profile_repair=True,
        profile_column_boundary_px=boundary_px,
    ))
    repaired.sort(key=lambda region: (region.bbox.y0, region.bbox.x0))
    return repaired


def apply_profile_repairs(
    regions: list[LayoutRegion],
    page: RenderedPage,
    ocr_page: OCRPage,
    native_page: NativePage,
    profile: DocumentProfile,
    *,
    min_support: int = 3,
    min_confidence: float = 0.90,
) -> list[LayoutRegion]:
    template = profile.requirement_template
    if template is None or template.support_count < min_support or template.confidence < min_confidence:
        return regions
    output = list(regions)
    for candidate in profile.requirement_candidates:
        if candidate.page_index == page.page_index and candidate.confidence >= min_confidence:
            output = _repair_candidate(
                output, page, ocr_page, native_page, candidate, template.id
            )
    return output
