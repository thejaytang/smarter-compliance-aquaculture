from __future__ import annotations

import json
import math
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

from ..config import TextRoutingSettings
from ..types import NativeObject, NativePage, OCRPage, OCRWord, PixelBox, RenderedPage


@dataclass(frozen=True)
class TextLayerDecision:
    page_index: int
    route: str
    reason: str
    word_count: int
    character_count: int
    suspicious_character_ratio: float
    valid_bbox_ratio: float
    bitmap_count: int
    confidence: float


def _meaningful_text(words: list[NativeObject]) -> str:
    return " ".join(word.text.strip() for word in words if word.text.strip())


def _suspicious_ratio(text: str) -> float:
    if not text:
        return 1.0
    suspicious = sum(
        char == "\ufffd"
        or (unicodedata.category(char).startswith("C") and not char.isspace())
        for char in text
    )
    return suspicious / len(text)


def _valid_bbox_ratio(page: NativePage, words: list[NativeObject]) -> float:
    if not words:
        return 0.0
    valid = 0
    for word in words:
        x0, y0, x1, y1 = word.bbox_points
        valid += int(
            math.isfinite(x0 + y0 + x1 + y1)
            and 0 <= x0 < x1 <= page.width_points + 1
            and 0 <= y0 < y1 <= page.height_points + 1
        )
    return valid / len(words)


def assess_text_layer(
    page: NativePage, settings: TextRoutingSettings
) -> TextLayerDecision:
    words = [
        word for word in page.words
        if word.object_type != "page_text_fallback" and word.text.strip()
    ]
    text = _meaningful_text(words)
    suspicious = _suspicious_ratio(text)
    valid_bbox = _valid_bbox_ratio(page, words)
    usable = (
        len(words) >= settings.min_word_count
        and len(text) >= settings.min_character_count
        and suspicious <= settings.max_suspicious_character_ratio
        and valid_bbox >= settings.min_valid_bbox_ratio
    )
    if not usable:
        route = "ocr"
        reason = "missing_or_low_quality_native_text_layer"
        confidence = min(0.99, 0.70 + (1.0 - min(1.0, valid_bbox)) * 0.20)
    elif page.bitmap_resources:
        route = "native_with_visual_fallback"
        reason = "usable_native_text_with_embedded_visual_content"
        confidence = 0.95
    else:
        route = "native"
        reason = "usable_native_text_layer"
        confidence = 0.99
    return TextLayerDecision(
        page_index=page.page_index,
        route=route,
        reason=reason,
        word_count=len(words),
        character_count=len(text),
        suspicious_character_ratio=suspicious,
        valid_bbox_ratio=valid_bbox,
        bitmap_count=len(page.bitmap_resources),
        confidence=confidence,
    )


def _line_number(word: NativeObject, lines: list[NativeObject]) -> int:
    x0, y0, x1, y1 = word.bbox_points
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    matches: list[tuple[float, int]] = []
    for index, line in enumerate(lines, start=1):
        lx0, ly0, lx1, ly1 = line.bbox_points
        if lx0 - 1 <= cx <= lx1 + 1 and ly0 - 1 <= cy <= ly1 + 1:
            matches.append(((lx1 - lx0) * (ly1 - ly0), index))
    if matches:
        return min(matches)[1]
    return max(1, round(cy * 10))


def _merge_adjacent_line_fragments(
    lines: list[NativeObject], page_width: float
) -> list[NativeObject]:
    """Join PDF text-line fragments that share a baseline and small horizontal gap."""
    clusters: list[list[NativeObject]] = []
    max_gap = max(18.0, page_width * 0.05)
    for line in sorted(lines, key=lambda item: (item.bbox_points[1], item.bbox_points[0])):
        lx0, ly0, lx1, ly1 = line.bbox_points
        matched: list[NativeObject] | None = None
        for cluster in reversed(clusters[-6:]):
            cx0 = min(item.bbox_points[0] for item in cluster)
            cy0 = min(item.bbox_points[1] for item in cluster)
            cx1 = max(item.bbox_points[2] for item in cluster)
            cy1 = max(item.bbox_points[3] for item in cluster)
            overlap = max(0.0, min(ly1, cy1) - max(ly0, cy0))
            vertical_ratio = overlap / max(0.1, min(ly1 - ly0, cy1 - cy0))
            horizontal_gap = max(0.0, max(lx0, cx0) - min(lx1, cx1))
            if vertical_ratio >= 0.70 and horizontal_gap <= max_gap:
                matched = cluster
                break
        if matched is None:
            clusters.append([line])
        else:
            matched.append(line)
    merged: list[NativeObject] = []
    for index, cluster in enumerate(clusters):
        ordered = sorted(cluster, key=lambda item: item.bbox_points[0])
        merged.append(NativeObject(
            id=f"native_line_cluster_{index:06d}",
            text=" ".join(item.text.strip() for item in ordered if item.text.strip()),
            bbox_points=(
                min(item.bbox_points[0] for item in cluster),
                min(item.bbox_points[1] for item in cluster),
                max(item.bbox_points[2] for item in cluster),
                max(item.bbox_points[3] for item in cluster),
            ),
            object_type="text_line_cluster",
        ))
    return merged


def native_analysis_page(
    native_page: NativePage,
    rendered_page: RenderedPage,
    raw_dir: Path,
    decision: TextLayerDecision,
) -> OCRPage:
    """Expose native words to layout code without relabelling them as OCR evidence."""
    lines = _merge_adjacent_line_fragments(
        [line for line in native_page.text_lines if line.text.strip()],
        native_page.width_points,
    )
    sx = rendered_page.width_px / rendered_page.width_points
    sy = rendered_page.height_px / rendered_page.height_points
    analysis_words: list[OCRWord] = []
    for index, word in enumerate(native_page.words):
        if word.object_type == "page_text_fallback" or not word.text.strip():
            continue
        x0, y0, x1, y1 = word.bbox_points
        line_number = _line_number(word, lines)
        analysis_words.append(OCRWord(
            id=f"native_analysis_p{native_page.page_index:04d}_w{index:06d}",
            text=word.text,
            confidence=word.confidence,
            bbox=PixelBox(
                max(0, round(x0 * sx)),
                max(0, round(y0 * sy)),
                min(rendered_page.width_px, round(x1 * sx)),
                min(rendered_page.height_px, round(y1 * sy)),
            ),
            # The heuristic layout backend groups by block/paragraph before it
            # considers line order. Native words therefore need a real grouping
            # key; otherwise the entire page collapses into one giant region.
            paragraph_num=line_number,
            line_num=line_number,
        ))
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_ref = raw_dir / f"analysis-text-page-{native_page.page_index + 1:04d}.json"
    raw_ref.write_text(json.dumps({
        "route": asdict(decision),
        "source": "native_text_layer",
        "words": [
            {
                "id": word.id,
                "text": word.text,
                "confidence": word.confidence,
                "bbox": [word.bbox.x0, word.bbox.y0, word.bbox.x1, word.bbox.y1],
                "line_num": word.line_num,
            }
            for word in analysis_words
        ],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return OCRPage(
        page_index=native_page.page_index,
        words=analysis_words,
        backend="native-text-layer",
        version=None,
        fallback_reason=decision.reason,
        raw_ref=raw_ref,
    )
