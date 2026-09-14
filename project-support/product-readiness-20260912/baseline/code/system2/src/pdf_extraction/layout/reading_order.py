from __future__ import annotations

from ..types import LayoutRegion


def sort_regions(regions: list[LayoutRegion]) -> list[LayoutRegion]:
    """Stable top-to-bottom ordering with a left-to-right tie break."""
    return sorted(regions, key=lambda region: (region.bbox.y0, region.bbox.x0, region.id))


def repair_local_model_inversions(
    model_regions: list[LayoutRegion],
) -> list[LayoutRegion]:
    """Repair short same-lane inversions without flattening model column order.

    Ordered detectors are substantially better than a global coordinate sort on
    multi-column pages, but can occasionally emit two nearby boxes in reverse
    vertical order. Bubble a region backwards only across strongly overlapping
    horizontal neighbours and only over a line-scale vertical distance. Boxes in
    separate columns therefore retain the detector's ordering.
    """
    ordered = list(model_regions)
    for current_index in range(1, len(ordered)):
        index = current_index
        while index > 0:
            current = ordered[index]
            previous = ordered[index - 1]
            overlap = max(
                0,
                min(previous.bbox.x1, current.bbox.x1)
                - max(previous.bbox.x0, current.bbox.x0),
            )
            max_width = max(1, previous.bbox.width, current.bbox.width)
            vertical_inversion = previous.bbox.y0 - current.bbox.y0
            local_limit = max(
                12,
                3 * max(1, min(previous.bbox.height, current.bbox.height)),
            )
            if not (
                overlap / max_width >= 0.35
                and 0 < vertical_inversion <= local_limit
            ):
                break
            ordered[index - 1], ordered[index] = current, previous
            index -= 1
    return ordered


def repair_fragmented_column_runs(
    model_regions: list[LayoutRegion],
    page_width: int,
) -> list[LayoutRegion]:
    """Repair repeated accidental bouncing between two dense text columns.

    A page made of independent panels may legitimately alternate columns once
    or twice.  We therefore intervene only when a dense text sequence switches
    lanes at least five times, a strong signal that late boxes from one column
    were emitted among the other column's boxes.
    """
    text_labels = {"heading", "paragraph", "list", "footnote", "unknown"}
    slots: list[int] = []
    lanes: list[str] = []
    candidates: list[LayoutRegion] = []
    for index, region in enumerate(model_regions):
        if region.label not in text_labels or region.bbox.width >= page_width * 0.58:
            continue
        center = (region.bbox.x0 + region.bbox.x1) / 2
        if center < page_width * 0.46:
            lane = "left"
        elif center > page_width * 0.54:
            lane = "right"
        else:
            continue
        slots.append(index)
        lanes.append(lane)
        candidates.append(region)
    if lanes.count("left") < 8 or lanes.count("right") < 8:
        return model_regions
    switches = sum(left != right for left, right in zip(lanes, lanes[1:]))
    if switches < 5:
        return model_regions
    first_lane = lanes[0]
    lane_order = (first_lane, "right" if first_lane == "left" else "left")
    reordered = [
        region
        for lane in lane_order
        for region in sorted(
            (item for item, item_lane in zip(candidates, lanes, strict=True) if item_lane == lane),
            key=lambda item: (item.bbox.y0, item.bbox.x0, item.id),
        )
    ]
    output = list(model_regions)
    for slot, region in zip(slots, reordered, strict=True):
        output[slot] = region
    return output


def merge_recovered_regions(
    model_regions: list[LayoutRegion],
    recovered_regions: list[LayoutRegion],
) -> list[LayoutRegion]:
    """Insert OCR-only regions without changing the model's relative order.

    Ordered layout models already resolve columns.  A global coordinate sort after
    inference destroys that information, so recovered OCR lines are anchored to the
    nearest horizontally overlapping model region while all model-owned regions keep
    their original relative order.
    """
    ordered = list(model_regions)
    for recovered in sort_regions(recovered_regions):
        overlapping: list[tuple[int, LayoutRegion]] = []
        for index, region in enumerate(ordered):
            overlap = max(
                0,
                min(region.bbox.x1, recovered.bbox.x1)
                - max(region.bbox.x0, recovered.bbox.x0),
            )
            denominator = max(1, min(region.bbox.width, recovered.bbox.width))
            if overlap / denominator >= 0.35:
                overlapping.append((index, region))

        if not overlapping:
            # This path is limited to OCR-only content with no usable model anchor.
            # It must not reorder regions for which the model did provide an order.
            insert_at = len(ordered)
            for index, region in enumerate(ordered):
                if (recovered.bbox.y0, recovered.bbox.x0) < (
                    region.bbox.y0,
                    region.bbox.x0,
                ):
                    insert_at = index
                    break
            ordered.insert(insert_at, recovered)
            continue

        below = [
            (index, region)
            for index, region in overlapping
            if region.bbox.y0 >= recovered.bbox.y1
        ]
        if below:
            insert_at = min(below, key=lambda item: item[1].bbox.y0)[0]
            ordered.insert(insert_at, recovered)
            continue

        above = [
            (index, region)
            for index, region in overlapping
            if region.bbox.y1 <= recovered.bbox.y0
        ]
        if above:
            insert_at = max(above, key=lambda item: item[1].bbox.y1)[0] + 1
            ordered.insert(insert_at, recovered)
            continue

        # An overlapping line is most likely a fragment omitted inside a detected
        # block. Keep it next to the closest visual anchor and preserve model order.
        anchor_index, _ = min(
            overlapping,
            key=lambda item: abs(
                (item[1].bbox.y0 + item[1].bbox.y1)
                - (recovered.bbox.y0 + recovered.bbox.y1)
            ),
        )
        ordered.insert(anchor_index + 1, recovered)
    return ordered
