from __future__ import annotations

import re
import statistics

from ..types import LayoutRegion, NativeObject, RenderedPage


def _line_text(line: list[NativeObject], excluded_text_ids: set[str]) -> str:
    visible = [
        word for word in line
        if word.id not in excluded_text_ids and word.text.strip()
    ]
    if not visible:
        return ""
    ordinary_heights = [
        word.bbox_points[3] - word.bbox_points[1]
        for word in visible if not re.fullmatch(r"\d{1,2}", word.text.strip())
    ]
    ordinary_bottoms = [
        word.bbox_points[3]
        for word in visible if not re.fullmatch(r"\d{1,2}", word.text.strip())
    ]
    median_height = statistics.median(ordinary_heights) if ordinary_heights else 0.0
    median_bottom = statistics.median(ordinary_bottoms) if ordinary_bottoms else 0.0
    parts: list[str] = []
    for position, word in enumerate(visible):
        token = word.text.strip()
        height = word.bbox_points[3] - word.bbox_points[1]
        is_superscript = (
            position > 0
            and bool(re.fullmatch(r"\d{1,2}", token))
            and median_height > 0
            and height <= median_height * 0.72
            and word.bbox_points[3] <= median_bottom - median_height * 0.18
        )
        if is_superscript:
            parts.append(f"[^{token}]")
        else:
            parts.append(token)
    text = " ".join(parts)
    text = re.sub(r"\s+(\[\^\d+\])", r"\1", text)
    return re.sub(r"\s+([,.;:!?])", r"\1", text).strip()


def native_text_for_region(
    region: LayoutRegion,
    page: RenderedPage,
    native_words: list[NativeObject],
    *,
    excluded_text_ids: set[str] | None = None,
    extra_ref_ids: list[str] | None = None,
) -> tuple[str | None, list[str]]:
    x0, y0, x1, y1 = page.pixel_to_points(region.bbox)
    selected: list[NativeObject] = []
    for word in native_words:
        wx0, wy0, wx1, wy1 = word.bbox_points
        cx = (wx0 + wx1) / 2
        cy = (wy0 + wy1) / 2
        if x0 <= cx <= x1 and y0 <= cy <= y1:
            selected.append(word)
    excluded_text_ids = excluded_text_ids or set()
    # Native glyph baselines often differ by a few points (notably bullets).
    # Cluster vertically-overlapping words into visual lines before x ordering.
    ordered = sorted(selected, key=lambda item: (item.bbox_points[1], item.bbox_points[0]))
    lines: list[list[NativeObject]] = []
    for word in ordered:
        wy0, wy1 = word.bbox_points[1], word.bbox_points[3]
        best_line: list[NativeObject] | None = None
        best_overlap = 0.0
        for line in lines:
            ly0 = min(item.bbox_points[1] for item in line)
            ly1 = max(item.bbox_points[3] for item in line)
            overlap = max(0.0, min(wy1, ly1) - max(wy0, ly0))
            ratio = overlap / max(0.1, min(wy1 - wy0, ly1 - ly0))
            if ratio > best_overlap:
                best_overlap = ratio
                best_line = line
        if best_line is not None and best_overlap >= 0.35:
            best_line.append(word)
        else:
            lines.append([word])
    lines.sort(key=lambda line: min(item.bbox_points[1] for item in line))
    parts: list[str] = []
    for line in lines:
        line.sort(key=lambda item: item.bbox_points[0])
        line_text = _line_text(line, excluded_text_ids)
        if line_text:
            parts.append(line_text)
    refs = list(dict.fromkeys(
        [word.id for word in selected] + (extra_ref_ids or [])
    ))
    joined: list[str] = []
    for part in parts:
        if joined and joined[-1].endswith("-") and re.match(r"^[a-z]", part):
            right_token = part.split(maxsplit=1)[0]
            preserve = (
                "http://" in joined[-1]
                or "https://" in joined[-1]
                or "www." in joined[-1]
                or joined[-1].count("-") >= 2
                or "-" in right_token
            )
            joined[-1] = joined[-1] + part if preserve else joined[-1][:-1] + part
        else:
            joined.append(part)
    text = " ".join(joined).strip()
    return (text or None), refs
