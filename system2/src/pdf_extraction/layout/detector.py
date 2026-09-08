from __future__ import annotations

import importlib.util
import json
import re
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from ..config import LayoutSettings, TableSettings
from ..ocr import configure_paddle_runtime
from ..types import (
    LayoutRegion,
    OCRPage,
    OCRWord,
    PixelBox,
    RenderedPage,
    join_ocr_words,
)
from .reading_order import (
    merge_recovered_regions,
    repair_fragmented_column_runs,
    repair_local_model_inversions,
    sort_regions,
)


@dataclass
class LayoutDetectionResult:
    regions: list[LayoutRegion]
    backend: str
    version: str | None
    fallback_reason: str | None = None


class LayoutDetector:
    name = "base"

    def detect(self, page: RenderedPage, ocr_page: OCRPage) -> LayoutDetectionResult:
        raise NotImplementedError


def _cluster_positions(indices: np.ndarray, tolerance: int = 3) -> list[int]:
    if indices.size == 0:
        return []
    groups: list[list[int]] = [[int(indices[0])]]
    for value in map(int, indices[1:]):
        if value - groups[-1][-1] <= tolerance:
            groups[-1].append(value)
        else:
            groups.append([value])
    return [round(sum(group) / len(group)) for group in groups]


def detect_table_boxes(image_path: Path, settings: TableSettings) -> list[PixelBox]:
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        return []
    binary = cv2.adaptiveThreshold(
        image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 12
    )
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(25, image.shape[1] // 35), 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(20, image.shape[0] // 45)))
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)
    grid = cv2.bitwise_or(horizontal, vertical)
    grid = cv2.dilate(grid, np.ones((3, 3), np.uint8), iterations=1)
    contours, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates: list[PixelBox] = []
    page_area = image.shape[0] * image.shape[1]
    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        if width < settings.min_width or height < settings.min_height:
            continue
        if width * height > page_area * 0.45:
            continue
        roi_h = horizontal[y:y + height, x:x + width]
        roi_v = vertical[y:y + height, x:x + width]
        horizontal_rows = _cluster_positions(np.where(np.sum(roi_h > 0, axis=1) > width * 0.35)[0])
        vertical_cols = _cluster_positions(np.where(np.sum(roi_v > 0, axis=0) > height * 0.35)[0])
        if len(horizontal_rows) >= 2 and len(vertical_cols) >= 2:
            margin = 6
            candidates.append(
                PixelBox(
                    max(0, x - margin), max(0, y - margin),
                    min(image.shape[1], x + width + margin),
                    min(image.shape[0], y + height + margin),
                )
            )
    candidates.sort(key=lambda box: (box.y0, box.x0))
    merged: list[PixelBox] = []
    for box in candidates:
        if merged and merged[-1].overlaps(box):
            prior = merged[-1]
            merged[-1] = PixelBox(
                min(prior.x0, box.x0), min(prior.y0, box.y0),
                max(prior.x1, box.x1), max(prior.y1, box.y1),
            )
        else:
            merged.append(box)
    return merged


def _text_from_words(words: list[OCRWord]) -> str:
    return join_ocr_words(words)


def _ocr_lines(words: list[OCRWord]) -> list[list[OCRWord]]:
    groups: dict[tuple[int, int, int], list[OCRWord]] = {}
    for word in words:
        if word.block_num or word.paragraph_num or word.line_num:
            key = (word.block_num, word.paragraph_num, word.line_num)
        else:
            # Coordinate fallback for engines that do not expose line metadata.
            key = (0, 0, round(word.bbox.y0 / max(8, word.bbox.height)))
        groups.setdefault(key, []).append(word)
    return sorted(
        groups.values(),
        key=lambda line: (min(word.bbox.y0 for word in line), min(word.bbox.x0 for word in line)),
    )


def _bind_indices_and_notes(
    regions: list[LayoutRegion], ocr_page: OCRPage, page: RenderedPage
) -> list[LayoutRegion]:
    """Attach nearby Table/Figure captions and Note/Source lines to compound blocks."""
    compounds = [region for region in regions if region.label in {"table", "figure"}]
    if not compounds:
        return regions
    consumed_word_ids: set[str] = set()
    lines = _ocr_lines(ocr_page.words)
    for line in lines:
        text = _text_from_words(line)
        line_box = _bbox_for_words(line)
        caption = re.match(r"^(Table|Figure|Fig\.)\s*\d+\b.*", text, flags=re.IGNORECASE)
        note = re.match(r"^(?:Note|Notes|Source)\s*[:.]", text, flags=re.IGNORECASE)
        if caption:
            wanted = "table" if caption.group(1).lower() == "table" else "figure"
            candidates = [
                region for region in compounds
                if region.label == wanted
                and 0 <= region.bbox.y0 - line_box.y1 <= page.height_px * 0.12
                and not (line_box.x1 < region.bbox.x0 or line_box.x0 > region.bbox.x1)
            ]
            if candidates:
                target = min(candidates, key=lambda region: region.bbox.y0 - line_box.y1)
                target.index_text = text
                target.index_bbox = line_box
                target.word_ids = list(dict.fromkeys(target.word_ids + [word.id for word in line]))
                target.auxiliary_word_ids = list(dict.fromkeys(
                    target.auxiliary_word_ids + [word.id for word in line]
                ))
                consumed_word_ids.update(word.id for word in line)
        elif note:
            candidates = [
                region for region in compounds
                if 0 <= line_box.y0 - region.bbox.y1 <= page.height_px * 0.1
                and not (line_box.x1 < region.bbox.x0 or line_box.x0 > region.bbox.x1)
            ]
            if candidates:
                target = min(candidates, key=lambda region: line_box.y0 - region.bbox.y1)
                target.note_text = text
                target.note_bbox = line_box
                target.word_ids = list(dict.fromkeys(target.word_ids + [word.id for word in line]))
                target.auxiliary_word_ids = list(dict.fromkeys(
                    target.auxiliary_word_ids + [word.id for word in line]
                ))
                consumed_word_ids.update(word.id for word in line)
    # Preserve short super-headings such as "Player B" that visually belong to a
    # table but are printed outside its border.
    for line in lines:
        if any(word.id in consumed_word_ids for word in line):
            continue
        text = _text_from_words(line)
        if not re.match(r"^(?:Player|Panel)\s+[A-Za-z0-9]+\b", text, re.I):
            continue
        line_box = _bbox_for_words(line)
        candidates = [
            region for region in compounds
            if region.label == "table" and region.index_text
            and (
                (
                    -5 <= region.bbox.y0 - line_box.y1 <= page.height_px * 0.06
                    and region.bbox.x0 <= (line_box.x0 + line_box.x1) / 2 <= region.bbox.x1
                )
                or region.bbox.contains_center(line_box)
            )
        ]
        if not candidates:
            candidates = [
                region for region in compounds
                if region.label == "table" and region.index_text
                and 0 <= region.bbox.x0 - line_box.x1 <= page.width_px * 0.09
                and region.bbox.y0 <= (line_box.y0 + line_box.y1) / 2 <= region.bbox.y1
            ]
        if candidates:
            target = min(candidates, key=lambda region: min(
                abs(region.bbox.y0 - line_box.y1), abs(region.bbox.x0 - line_box.x1)
            ))
            target.note_text = "; ".join(
                value for value in (target.note_text, text) if value
            )
            target.note_bbox = (
                PixelBox(
                    min(target.note_bbox.x0, line_box.x0), min(target.note_bbox.y0, line_box.y0),
                    max(target.note_bbox.x1, line_box.x1), max(target.note_bbox.y1, line_box.y1),
                ) if target.note_bbox else line_box
            )
            target.word_ids = list(dict.fromkeys(target.word_ids + [word.id for word in line]))
            target.auxiliary_word_ids = list(dict.fromkeys(
                target.auxiliary_word_ids + [word.id for word in line]
            ))
            consumed_word_ids.update(word.id for word in line)
    # Preserve a compact merged super-header immediately above the detected
    # table body (for example "Combined category"). Expanding the table crop
    # here lets the structure parser keep it as a spanning cell instead of a
    # detached paragraph or an unexplained visual region.
    for line in lines:
        if any(word.id in consumed_word_ids for word in line):
            continue
        text = _text_from_words(line)
        if not text or len(text.split()) > 4:
            continue
        line_box = _bbox_for_words(line)
        candidates = [
            region for region in compounds
            if region.label == "table" and region.index_text
            and 0 <= region.bbox.y0 - line_box.y1 <= page.height_px * 0.018
            and not (line_box.x1 < region.bbox.x0 or line_box.x0 > region.bbox.x1)
            and line_box.width <= region.bbox.width * 0.8
        ]
        if candidates:
            target = min(candidates, key=lambda region: region.bbox.y0 - line_box.y1)
            target.bbox = PixelBox(
                min(target.bbox.x0, line_box.x0), min(target.bbox.y0, line_box.y0),
                max(target.bbox.x1, line_box.x1), max(target.bbox.y1, line_box.y1),
            )
            target.word_ids = list(dict.fromkeys(target.word_ids + [word.id for word in line]))
            consumed_word_ids.update(word.id for word in line)
    if not consumed_word_ids:
        return regions
    filtered: list[LayoutRegion] = []
    for region in regions:
        region_words = set(region.word_ids)
        # Remove a caption/note only when that region contains no independent content.
        if region.label not in {"table", "figure"} and region_words and region_words <= consumed_word_ids:
            continue
        filtered.append(region)
    return filtered


def _bbox_for_words(words: list[OCRWord]) -> PixelBox:
    return PixelBox(
        min(word.bbox.x0 for word in words),
        min(word.bbox.y0 for word in words),
        max(word.bbox.x1 for word in words),
        max(word.bbox.y1 for word in words),
    )


def split_sparse_text_regions(
    regions: list[LayoutRegion],
    ocr_page: OCRPage,
) -> list[LayoutRegion]:
    """Split a coarse layout box when it bridges separate text bands.

    Slide decks and worksheets often place independent statements inside one
    detector rectangle. OCR line boxes are better local evidence for that case.
    Ordinary wrapped paragraphs are retained because a split is made only when
    the vertical whitespace is large relative to the median OCR-line height.
    """
    word_by_id = {word.id: word for word in ocr_page.words}
    output: list[LayoutRegion] = []
    text_labels = {"heading", "paragraph", "list", "footnote", "unknown"}
    for region in regions:
        if region.label not in text_labels:
            output.append(region)
            continue
        words = [
            word_by_id[word_id]
            for word_id in region.word_ids
            if word_id in word_by_id
        ]
        lines = _ocr_lines(words)
        if len(lines) < 2 or len(lines) > 4:
            output.append(region)
            continue
        line_boxes = [_bbox_for_words(line) for line in lines]
        median_height = float(np.median([box.height for box in line_boxes]))
        split_gap = max(12, round(median_height * 0.55))
        clusters: list[list[list[OCRWord]]] = [[lines[0]]]
        cluster_box = line_boxes[0]
        for line, line_box in zip(lines[1:], line_boxes[1:], strict=True):
            if line_box.y0 - cluster_box.y1 > split_gap:
                clusters.append([line])
                cluster_box = line_box
            else:
                clusters[-1].append(line)
                cluster_box = PixelBox(
                    min(cluster_box.x0, line_box.x0),
                    min(cluster_box.y0, line_box.y0),
                    max(cluster_box.x1, line_box.x1),
                    max(cluster_box.y1, line_box.y1),
                )
        if len(clusters) == 1:
            output.append(region)
            continue
        for cluster_index, cluster in enumerate(clusters):
            cluster_words = [word for line in cluster for word in line]
            output.append(LayoutRegion(
                id=f"{region.id}_band_{cluster_index:02d}",
                label=(
                    region.label if cluster_index == 0
                    else "paragraph" if region.label == "heading"
                    else region.label
                ),
                bbox=_bbox_for_words(cluster_words),
                confidence=region.confidence,
                text=_text_from_words(cluster_words),
                word_ids=[word.id for word in cluster_words],
                heading_level=region.heading_level if cluster_index == 0 else None,
            ))
    return output


def promote_spaced_lead_paragraphs(
    regions: list[LayoutRegion],
) -> list[LayoutRegion]:
    """Promote a short lead line separated above but attached below."""
    for region in regions:
        text = region.text.strip()
        if (
            region.label != "paragraph"
            or not text
            or len(text) > 80
            or re.search(r"[.!?;:。！？；：]$", text)
        ):
            continue
        same_lane = [
            other for other in regions
            if other is not region
            and max(
                0,
                min(region.bbox.x1, other.bbox.x1)
                - max(region.bbox.x0, other.bbox.x0),
            ) / max(1, min(region.bbox.width, other.bbox.width)) >= 0.35
        ]
        above = [other for other in same_lane if other.bbox.y1 <= region.bbox.y0]
        below = [other for other in same_lane if other.bbox.y0 >= region.bbox.y1]
        if not above or not below:
            continue
        prior = max(above, key=lambda item: item.bbox.y1)
        following = min(below, key=lambda item: item.bbox.y0)
        gap_before = region.bbox.y0 - prior.bbox.y1
        gap_after = following.bbox.y0 - region.bbox.y1
        if gap_before >= region.bbox.height * 0.6 and gap_after <= region.bbox.height * 0.2:
            region.label = "heading"
            region.heading_level = region.heading_level or 2
    return regions


def _label_text_region(text: str, box: PixelBox, page: RenderedPage, median_height: float) -> str:
    stripped = text.strip()
    normalized = re.sub(r"\s+", " ", stripped)
    if box.y0 < page.height_px * 0.055 and page.page_index > 0:
        return "header"
    if box.y1 > page.height_px * 0.94 and re.fullmatch(r"\d+", normalized):
        return "footer"
    if re.match(r"^Question\s+\d+\b", normalized, flags=re.IGNORECASE):
        return "heading"
    if re.match(
        r"^(?:Principle\s+\d+(?:\s*[-–—:]\s*.*)?|"
        r"Criterion\s+\d+(?:\.\d+)*(?:\s*[-–—:]\s*.*)?|"
        r"How do I interpret this requirement\?|"
        r"Evidence of implementation should be maintained,?\s*e\.g\.:?|"
        r"Auditors should confirm:|Useful Resources:?|Useful resources \(if applicable\))$",
        normalized,
        flags=re.IGNORECASE,
    ):
        return "heading"
    if box.y0 < page.height_px * 0.16 and (
        normalized.isupper() or box.height >= median_height * 1.35
    ):
        return "heading"
    if re.match(r"^(?:[a-z]\)|[a-z]\.|\d+\.|[•●▪])\s*", normalized, flags=re.IGNORECASE):
        return "list"
    return "paragraph"


class HeuristicLayoutDetector(LayoutDetector):
    name = "opencv-tesseract-layout"

    def __init__(self, table_settings: TableSettings, fallback_reason: str | None = None) -> None:
        self.table_settings = table_settings
        self.fallback_reason = fallback_reason

    def detect(self, page: RenderedPage, ocr_page: OCRPage) -> LayoutDetectionResult:
        table_boxes = detect_table_boxes(page.image_path, self.table_settings)
        words_in_tables = {
            word.id for word in ocr_page.words if any(box.contains_center(word.bbox) for box in table_boxes)
        }
        groups: dict[tuple[int, int], list[OCRWord]] = {}
        for word in ocr_page.words:
            if word.id in words_in_tables:
                continue
            key = (word.block_num, word.paragraph_num)
            groups.setdefault(key, []).append(word)
        heights = [word.bbox.height for word in ocr_page.words if word.bbox.height > 0]
        median_height = float(np.median(heights)) if heights else 12.0
        text_regions: list[LayoutRegion] = []
        caption_regions: dict[int, LayoutRegion] = {}
        for index, words in enumerate(groups.values()):
            box = _bbox_for_words(words)
            text = _text_from_words(words)
            if not text:
                continue
            region = LayoutRegion(
                id=f"layout_p{page.page_index:04d}_text_{index:04d}",
                label=_label_text_region(text, box, page, median_height),
                bbox=box,
                confidence=sum(word.confidence for word in words) / len(words),
                text=text,
                word_ids=[word.id for word in words],
                heading_level=(
                    2 if re.match(
                        r"^(?:Question\s+\d+\b|Principle\s+\d+|Criterion\s+\d+(?:\.\d+)*)",
                        text,
                        flags=re.IGNORECASE,
                    )
                    else 1 if (
                        _label_text_region(text, box, page, median_height) == "heading"
                        and box.y0 < page.height_px * 0.16
                        and (text.strip().isupper() or box.height >= median_height * 1.35)
                    )
                    else 3 if _label_text_region(text, box, page, median_height) == "heading"
                    else None
                ),
            )
            for table_index, table_box in enumerate(table_boxes):
                if (
                    re.match(r"^Table\s+\d+", text, flags=re.IGNORECASE)
                    and 0 <= table_box.y0 - box.y1 <= page.height_px * 0.1
                    and not (box.x1 < table_box.x0 or box.x0 > table_box.x1)
                ):
                    caption_regions[table_index] = region
            text_regions.append(region)
        consumed_caption_ids = {region.id for region in caption_regions.values()}
        text_regions = [region for region in text_regions if region.id not in consumed_caption_ids]
        table_regions = [
            LayoutRegion(
                id=f"layout_p{page.page_index:04d}_table_{index:04d}",
                label="table",
                bbox=box,
                confidence=0.75,
                word_ids=[word.id for word in ocr_page.words if box.contains_center(word.bbox)],
                index_text=caption_regions.get(index).text if index in caption_regions else None,
            )
            for index, box in enumerate(table_boxes)
        ]
        regions = _bind_indices_and_notes(text_regions + table_regions, ocr_page, page)
        return LayoutDetectionResult(
            regions=sort_regions(regions),
            backend=self.name,
            version=cv2.__version__,
            fallback_reason=self.fallback_reason,
        )


class PaddleLayoutDetector(LayoutDetector):
    name = "PP-DocLayoutV3"

    def __init__(self, settings: LayoutSettings) -> None:
        if importlib.util.find_spec("paddleocr") is None:
            raise RuntimeError("paddleocr package is not installed")
        configure_paddle_runtime()
        from paddleocr import LayoutDetection

        self.settings = settings
        self.model = LayoutDetection(
            model_name=settings.paddle_model,
            engine=settings.paddle_engine,
            device="cpu",
        )
        self.backend_version = version("paddleocr")

    def detect(self, page: RenderedPage, ocr_page: OCRPage) -> LayoutDetectionResult:
        output = list(self.model.predict(str(page.image_path), batch_size=1, layout_nms=True))
        model_regions: list[LayoutRegion] = []
        label_map = {
            "abstract": "paragraph", "content": "paragraph", "text": "paragraph",
            "reference_content": "paragraph", "footnote": "footnote",
            "vision_footnote": "footnote", "doc_title": "heading",
            "paragraph_title": "heading", "table": "table", "image": "figure",
            "chart": "figure", "header": "header", "header_image": "header",
            "footer": "footer", "footer_image": "footer",
            "display_formula": "equation", "inline_formula": "equation",
            "formula": "equation", "equation": "equation",
            "code": "code", "algorithm": "code",
        }
        for result in output:
            payload = result.json if hasattr(result, "json") else result
            if isinstance(payload, str):
                payload = json.loads(payload)
            data = payload.get("res", payload) if isinstance(payload, dict) else {}
            boxes = data.get("boxes", data.get("layout_det_res", {}).get("boxes", []))
            for index, item in enumerate(boxes):
                score = float(item.get("score", item.get("confidence", 0)))
                if score < self.settings.min_confidence:
                    continue
                raw_box = item.get("coordinate", item.get("bbox", item.get("box")))
                if not raw_box:
                    continue
                x0, y0, x1, y1 = map(int, raw_box)
                label = label_map.get(str(item.get("label", "unknown")).lower(), "unknown")
                box = PixelBox(x0, y0, x1, y1)
                words = [word for word in ocr_page.words if box.contains_center(word.bbox)]
                text = _text_from_words(words)
                inferred_heading = False
                if label == "paragraph" and re.match(
                    r"^(?:[a-z]\)|[a-z]\.|\d+\.|[•●▪])\s*", text, flags=re.IGNORECASE
                ):
                    label = "list"
                elif label == "paragraph" and _label_text_region(
                    text, box, page,
                    float(np.median([word.bbox.height for word in ocr_page.words if word.bbox.height > 0]))
                    if any(word.bbox.height > 0 for word in ocr_page.words) else 12.0,
                ) == "heading":
                    label = "heading"
                    inferred_heading = True
                raw_label = str(item.get("label", "unknown")).lower()
                if (
                    raw_label == "number"
                    and box.y0 > page.height_px * 0.84
                    and re.fullmatch(r"\d+", text)
                ):
                    label = "footer"
                model_regions.append(
                    LayoutRegion(
                        id=f"layout_p{page.page_index:04d}_{index:04d}",
                        label=label,
                        bbox=box,
                        confidence=score,
                        text=text,
                        word_ids=[word.id for word in words],
                        heading_level=(
                            1 if raw_label == "doc_title" or inferred_heading
                            or (label == "heading" and box.y0 < page.height_px * 0.16)
                            else 2 if raw_label == "paragraph_title" else None
                        ),
                    )
                )
        if not model_regions:
            raise RuntimeError("PP-DocLayoutV3 returned no usable regions")
        # Recover OCR lines that the layout model omitted entirely. This is a
        # completeness fallback, not a reclassification of model-owned words:
        # every recovered region carries lower confidence and exact OCR refs.
        assigned_word_ids = {
            word_id for region in model_regions for word_id in region.word_ids
        }
        heights = [word.bbox.height for word in ocr_page.words if word.bbox.height > 0]
        median_height = float(np.median(heights)) if heights else 12.0
        recovered_regions: list[LayoutRegion] = []
        for line_index, line in enumerate(_ocr_lines(ocr_page.words)):
            if any(word.id in assigned_word_ids for word in line):
                continue
            line_box = _bbox_for_words(line)
            if any(region.bbox.contains_center(line_box) for region in model_regions):
                continue
            text = _text_from_words(line)
            if not text:
                continue
            label = _label_text_region(text, line_box, page, median_height)
            recovered_regions.append(LayoutRegion(
                id=f"layout_p{page.page_index:04d}_recovered_{line_index:04d}",
                label=label, bbox=line_box,
                confidence=min(0.69, sum(word.confidence for word in line) / len(line) * 0.8),
                text=text, word_ids=[word.id for word in line],
                heading_level=(
                    2 if re.match(r"^Question\s+\d+\b", text, flags=re.IGNORECASE)
                    else 1 if label == "heading" else None
                ),
            ))
        model_regions = repair_local_model_inversions(model_regions)
        model_regions = repair_fragmented_column_runs(model_regions, page.width_px)
        regions = merge_recovered_regions(model_regions, recovered_regions)
        regions = split_sparse_text_regions(regions, ocr_page)
        regions = promote_spaced_lead_paragraphs(regions)
        regions = _bind_indices_and_notes(regions, ocr_page, page)
        # PP-DocLayoutV3 returns boxes in its predicted reading order. Do not
        # overwrite that order with a global y/x sort, which interleaves columns.
        return LayoutDetectionResult(regions, self.name, self.backend_version)


def create_layout_detector(
    layout_settings: LayoutSettings,
    table_settings: TableSettings,
) -> LayoutDetector:
    if layout_settings.backend in {"auto", "paddle"}:
        try:
            return PaddleLayoutDetector(layout_settings)
        except Exception as exc:
            if layout_settings.backend == "paddle":
                raise
            return HeuristicLayoutDetector(
                table_settings,
                f"Paddle layout unavailable: {exc}",
            )
    if layout_settings.backend == "heuristic":
        return HeuristicLayoutDetector(table_settings)
    raise ValueError(f"unsupported layout backend: {layout_settings.backend}")
