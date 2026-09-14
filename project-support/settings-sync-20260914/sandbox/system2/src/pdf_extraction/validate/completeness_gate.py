from __future__ import annotations

import re

import cv2
import numpy as np

from ..config import CompletenessSettings
from ..models import BoundingBox, PageCompletenessReport
from ..types import LayoutRegion, NativeObject, NativePage, OCRPage, PixelBox, RenderedPage
from ..layout.native_visuals import bitmap_box_points


def _iou(left: PixelBox, right: PixelBox) -> float:
    x0, y0 = max(left.x0, right.x0), max(left.y0, right.y0)
    x1, y1 = min(left.x1, right.x1), min(left.y1, right.y1)
    intersection = max(0, x1 - x0) * max(0, y1 - y0)
    union = left.area + right.area - intersection
    return intersection / union if union else 0.0


def _contains_point(regions: list[LayoutRegion], x: float, y: float) -> bool:
    return any(region.bbox.x0 <= x <= region.bbox.x1 and region.bbox.y0 <= y <= region.bbox.y1 for region in regions)


def _contains_evidence(
    regions: list[LayoutRegion], ocr_page: OCRPage, x: float, y: float
) -> bool:
    if _contains_point(regions, x, y):
        return True
    explained_word_ids = {word_id for region in regions for word_id in region.word_ids}
    return any(
        word.id in explained_word_ids
        and word.bbox.x0 <= x <= word.bbox.x1
        and word.bbox.y0 <= y <= word.bbox.y1
        for word in ocr_page.words
    )


def _native_center_px(item: NativeObject, page: RenderedPage) -> tuple[float, float]:
    x0, y0, x1, y1 = item.bbox_points
    return (
        ((x0 + x1) / 2) * page.width_px / page.width_points,
        ((y0 + y1) / 2) * page.height_px / page.height_points,
    )


def _unexplained_regions(
    page: RenderedPage,
    native_page: NativePage,
    regions: list[LayoutRegion],
    ocr_page: OCRPage,
    settings: CompletenessSettings,
) -> list[BoundingBox]:
    image = cv2.imread(str(page.image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        return []
    ink = cv2.threshold(image, 210, 255, cv2.THRESH_BINARY_INV)[1]
    covered = np.zeros_like(ink)
    for region in regions:
        # Learned/profile tables are bounded by text geometry.  Their dark
        # header fill and outer stroke extend a few points beyond that box and
        # otherwise look like a large omitted visual region.  The larger table
        # margin covers only this known compound block perimeter.
        margin = 28 if region.label == "table" else 6
        cv2.rectangle(
            covered,
            (max(0, region.bbox.x0 - margin), max(0, region.bbox.y0 - margin)),
            (min(page.width_px - 1, region.bbox.x1 + margin), min(page.height_px - 1, region.bbox.y1 + margin)),
            255,
            thickness=-1,
        )
    # Full-page photographs and design backgrounds are visually large but not
    # independent semantic blocks. Mask them while preserving overlaid native
    # text as ordinary layout regions.
    page_area_points = max(1.0, native_page.width_points * native_page.height_points)
    for resource in native_page.bitmap_resources:
        points = bitmap_box_points(resource)
        if points is None:
            continue
        x0, y0, x1, y1 = points
        if (x1 - x0) * (y1 - y0) / page_area_points < 0.80:
            continue
        px0 = round(x0 * page.width_px / page.width_points)
        py0 = round(y0 * page.height_px / page.height_points)
        px1 = round(x1 * page.width_px / page.width_points)
        py1 = round(y1 * page.height_px / page.height_points)
        cv2.rectangle(covered, (px0, py0), (px1, py1), 255, thickness=-1)
    # Captions, notes and table super-headings can be canonical evidence without
    # being inside the compound block crop. Their word ids are attached during
    # layout binding, so mask their exact visual evidence as explained as well.
    explained_word_ids = {word_id for region in regions for word_id in region.word_ids}
    for word in ocr_page.words:
        if word.id not in explained_word_ids:
            continue
        margin = 4
        cv2.rectangle(
            covered,
            (max(0, word.bbox.x0 - margin), max(0, word.bbox.y0 - margin)),
            (min(page.width_px - 1, word.bbox.x1 + margin), min(page.height_px - 1, word.bbox.y1 + margin)),
            255,
            thickness=-1,
        )
    unexplained = cv2.bitwise_and(ink, cv2.bitwise_not(covered))
    unexplained = cv2.morphologyEx(
        unexplained,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (17, 5)),
    )
    contours, _ = cv2.findContours(unexplained, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    output: list[BoundingBox] = []
    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        if width * height < settings.min_visual_region_area or width < 6 or height < 4:
            continue
        x0, y0, x1, y1 = page.pixel_to_points(PixelBox(x, y, x + width, y + height))
        # Long, very thin rules are layout decoration rather than omitted
        # semantic content. Keep the gate sensitive to text/figures while
        # avoiding a false critical review for a page separator.
        if y1 - y0 <= 2.0 and (x1 - x0) / max(y1 - y0, 0.1) >= 20:
            continue
        # The same rule applies to narrow vertical separators.  Residual ink
        # only a few points wide cannot contain readable glyph evidence.
        if x1 - x0 <= 4.0 and (y1 - y0) / max(x1 - x0, 0.1) >= 8:
            continue
        # Page-edge crop seams and full-width design rules can be slightly
        # thicker after rasterisation.  Ignore them only when they touch the
        # physical page edge and remain strongly line-shaped.
        touches_edge = (
            x0 <= 1.0 or y0 <= 1.0
            or x1 >= page.width_points - 1.0
            or y1 >= page.height_points - 1.0
        )
        if touches_edge and min(x1 - x0, y1 - y0) <= 6.5 and (
            max(x1 - x0, y1 - y0) / max(min(x1 - x0, y1 - y0), 0.1) >= 20
        ):
            continue
        output.append(BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1))
    return sorted(output, key=lambda box: (box.y0, box.x0))


def build_page_completeness_report(
    page: RenderedPage,
    native_page: NativePage,
    ocr_page: OCRPage,
    regions: list[LayoutRegion],
    settings: CompletenessSettings,
) -> PageCompletenessReport:
    primary_native = [
        item for item in native_page.characters if item.text.strip()
    ] or [
        item for item in native_page.words if item.object_type != "page_text_fallback"
        and item.text.strip()
    ]
    native_count = len(primary_native) + len(native_page.bitmap_resources) + len(native_page.shapes)
    assigned_native = sum(
        _contains_evidence(regions, ocr_page, *_native_center_px(item, page))
        for item in primary_native
    )
    # A page-level bitmap is explained by visual blocks when at least one block exists.
    assigned_native += len(native_page.bitmap_resources) if regions else 0
    for shape in native_page.shapes:
        points = shape.get("points", [])
        if not points:
            continue
        x = sum(float(point.get("x", 0)) for point in points) / len(points)
        y = sum(float(point.get("y", 0)) for point in points) / len(points)
        px = x * page.width_px / page.width_points
        py = y * page.height_px / page.height_points
        assigned_native += int(_contains_evidence(regions, ocr_page, px, py))
    explained_word_ids = {word_id for region in regions for word_id in region.word_ids}
    assigned_ocr = sum(
        word.id in explained_word_ids
        or _contains_point(
            regions,
            (word.bbox.x0 + word.bbox.x1) / 2,
            (word.bbox.y0 + word.bbox.y1) / 2,
        )
        for word in ocr_page.words
    )
    duplicates: list[list[str]] = []
    for index, left in enumerate(regions):
        left_text = re.sub(r"\s+", " ", left.text).strip().casefold()
        for right in regions[index + 1:]:
            right_text = re.sub(r"\s+", " ", right.text).strip().casefold()
            if left_text and left_text == right_text and _iou(left.bbox, right.bbox) >= settings.duplicate_iou_threshold:
                duplicates.append([left.id, right.id])
    unexplained = (
        _unexplained_regions(page, native_page, regions, ocr_page, settings)
        if settings.enabled else []
    )
    unassigned = max(0, native_count - assigned_native)
    requires_review = (
        unassigned > 0
        or len(unexplained) > settings.max_unexplained_regions
        or bool(duplicates)
        or assigned_ocr < len(ocr_page.words)
    )
    return PageCompletenessReport(
        page_index=page.page_index,
        native_object_count=native_count,
        assigned_native_object_count=min(native_count, assigned_native),
        unassigned_native_object_count=unassigned,
        detected_block_count=len(regions),
        ocr_word_count=len(ocr_page.words),
        assigned_ocr_word_count=assigned_ocr,
        unexplained_visual_regions=unexplained,
        duplicate_regions=duplicates,
        status="review_required" if requires_review else "accepted",
    )
