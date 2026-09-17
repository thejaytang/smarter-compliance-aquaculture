from __future__ import annotations

from ..types import LayoutRegion, NativePage, OCRPage, PixelBox, RenderedPage


def bitmap_box_points(resource: dict[str, object]) -> tuple[float, float, float, float] | None:
    rect = resource.get("rect")
    if not isinstance(rect, dict):
        return None
    try:
        xs = [float(rect[f"r_x{index}"]) for index in range(4)]
        ys = [float(rect[f"r_y{index}"]) for index in range(4)]
    except (KeyError, TypeError, ValueError):
        return None
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    return (x0, y0, x1, y1) if x1 > x0 and y1 > y0 else None


def _to_pixels(page: RenderedPage, box: tuple[float, float, float, float]) -> PixelBox:
    x0, y0, x1, y1 = box
    sx = page.width_px / page.width_points
    sy = page.height_px / page.height_points
    return PixelBox(round(x0 * sx), round(y0 * sy), round(x1 * sx), round(y1 * sy))


def _contains(left: PixelBox, right: PixelBox) -> bool:
    return (
        left.x0 <= right.x0 and left.y0 <= right.y0
        and left.x1 >= right.x1 and left.y1 >= right.y1
    )


def apply_native_visual_regions(
    regions: list[LayoutRegion],
    page: RenderedPage,
    native_page: NativePage,
    analysis_page: OCRPage,
    *,
    min_area_ratio: float = 0.02,
    decorative_background_ratio: float = 0.80,
) -> list[LayoutRegion]:
    """Promote embedded bitmaps to figures and suppress table boxes inside them."""
    page_area = max(1.0, native_page.width_points * native_page.height_points)
    candidates: list[PixelBox] = []
    has_full_page_background = False
    for resource in native_page.bitmap_resources:
        points = bitmap_box_points(resource)
        if points is None:
            continue
        x0, y0, x1, y1 = points
        ratio = (x1 - x0) * (y1 - y0) / page_area
        if ratio >= decorative_background_ratio:
            has_full_page_background = True
        if min_area_ratio <= ratio < decorative_background_ratio:
            candidates.append(_to_pixels(page, points))

    # Keep the largest box when one bitmap is merely a nested layer of another.
    candidates.sort(key=lambda box: box.area, reverse=True)
    figures: list[PixelBox] = []
    for box in candidates:
        if any(_contains(existing, box) for existing in figures):
            continue
        figures.append(box)

    output = list(regions)
    if has_full_page_background:
        page_pixel_area = max(1, page.width_px * page.height_px)
        for region in output:
            if region.label != "table" or region.bbox.area / page_pixel_area > 0.08:
                continue
            native_words = [
                word for word in analysis_page.words
                if region.bbox.contains_center(word.bbox)
            ]
            if native_words:
                continue
            # A small grid-like patch inside a full-page photograph, with no
            # native text anchor, is visual content rather than a trustworthy
            # semantic table. Preserve it as a figure instead of OCRing icons
            # into fabricated cells.
            region.label = "figure"
            region.confidence = min(region.confidence, 0.90)
            region.visual_reclassification_reason = (
                "ungrounded_table_on_full_page_native_background"
            )
    for index, box in enumerate(sorted(figures, key=lambda item: (item.y0, item.x0))):
        consumed = [
            region for region in output
            if region.label not in {"header", "footer"}
            and box.contains_center(region.bbox)
        ]
        consumed_ids = {region.id for region in consumed}
        word_ids = [
            word.id for word in analysis_page.words if box.contains_center(word.bbox)
        ]
        output = [region for region in output if region.id not in consumed_ids]
        output.append(LayoutRegion(
            id=f"layout_p{page.page_index:04d}_native_figure_{index:04d}",
            label="figure",
            bbox=box,
            confidence=0.99,
            text=" ".join(region.text for region in consumed if region.text).strip(),
            word_ids=list(dict.fromkeys(
                word_ids + [word_id for region in consumed for word_id in region.word_ids]
            )),
            visual_reclassification_reason=(
                "embedded_bitmap_region"
                if any(region.label == "table" for region in consumed)
                else None
            ),
        ))
    return sorted(output, key=lambda region: (region.bbox.y0, region.bbox.x0))
