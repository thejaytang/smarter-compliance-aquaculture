"""Low-level region normalization helpers used during canonical construction."""

from __future__ import annotations

import re

from ..models import BlockType, BoundingBox
from ..types import LayoutRegion, OCRPage, RenderedPage, join_ocr_words


def region_bbox(page: RenderedPage, region: LayoutRegion) -> BoundingBox:
    x0, y0, x1, y1 = page.pixel_to_points(region.bbox)
    return BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1)


def region_ocr_text(
    region: LayoutRegion,
    ocr_page: OCRPage,
) -> tuple[str | None, float]:
    word_ids = set(region.word_ids)
    words = [word for word in ocr_page.words if word.id in word_ids]
    if not words:
        return region.text or None, region.confidence
    return join_ocr_words(words) or None, (
        sum(word.confidence for word in words) / len(words)
    )


def normalized_block_type(label: str) -> BlockType:
    try:
        return BlockType(label)
    except ValueError:
        return BlockType.UNKNOWN


def figure_index_from_source_text(value: str | None) -> str | None:
    if not value:
        return None
    first_line = next(
        (" ".join(line.split()) for line in value.splitlines() if line.strip()),
        "",
    )
    first_sentence = re.split(r"(?<=[.!?])\s+", first_line, maxsplit=1)[0].strip()
    if first_sentence == first_line and len(first_sentence) > 120:
        return None
    candidate = first_sentence[:180].strip(" |:;,-")
    if not (3 <= len(re.findall(r"[A-Za-z]{2,}", candidate)) <= 30):
        return None
    readable = sum(
        char.isalnum() or char.isspace() or char in "-(),./&"
        for char in candidate
    )
    if readable / max(1, len(candidate)) < 0.90:
        return None
    return candidate


__all__ = [
    "figure_index_from_source_text",
    "normalized_block_type",
    "region_bbox",
    "region_ocr_text",
]
