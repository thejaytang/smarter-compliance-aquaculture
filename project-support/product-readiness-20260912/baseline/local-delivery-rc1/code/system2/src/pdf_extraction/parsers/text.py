from __future__ import annotations

import re

import cv2
import numpy as np

from ..models import Resolution, ResolutionStatus, TextContent
from ..types import LayoutRegion, OCRPage, PixelBox, RenderedPage


CRITICAL_PATTERN = re.compile(
    r"(?:\b\d+(?:[.,]\d+)?%?\b|[<>≤≥=]|\b(?:mg|kg|g|ml|l|usd|eur|nok)\b|"
    r"\b(?:not|shall|must|may|unless|except)\b|§)",
    flags=re.IGNORECASE,
)


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.replace("\u00ad", "")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\s*\n\s*", " ", cleaned)
    return cleaned.strip() or None


def _critical_tokens(value: str | None) -> list[str]:
    return CRITICAL_PATTERN.findall(value or "")


def recover_visual_blank_text(
    page: RenderedPage,
    region: LayoutRegion,
    ocr_page: OCRPage,
) -> tuple[str | None, list[PixelBox]]:
    """Recover long printed answer blanks omitted by text OCR.

    The page image supplies the horizontal strokes and OCR supplies the words.
    Both are placed in x-order, preserving explicit blank fields as ``____``.
    """
    words_by_id = {word.id: word for word in ocr_page.words}
    words = [words_by_id[word_id] for word_id in region.word_ids if word_id in words_by_id]
    if not words or any("____" in word.text for word in words):
        return None, []
    image = cv2.imread(str(page.image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        return None, []
    box = region.bbox
    crop = image[box.y0:box.y1, box.x0:box.x1]
    if crop.size == 0:
        return None, []
    binary = cv2.threshold(crop, 190, 255, cv2.THRESH_BINARY_INV)[1]
    kernel_width = min(50, max(20, crop.shape[1] // 20))
    horizontal = cv2.morphologyEx(
        binary,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_width, 1)),
    )
    contours, _ = cv2.findContours(
        horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    blank_boxes: list[PixelBox] = []
    min_width = max(45, round(crop.shape[1] * 0.12))
    max_height = max(8, round(crop.shape[0] * 0.25))
    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        if width < min_width or height > max_height or width / max(1, height) < 12:
            continue
        candidate = PixelBox(box.x0 + x, box.y0 + y, box.x0 + x + width, box.y0 + y + height)
        if any(
            max(
                0,
                min(candidate.x1, word.bbox.x1)
                - max(candidate.x0, word.bbox.x0),
            ) / max(1, candidate.width) > 0.1
            for word in words
        ):
            continue
        blank_boxes.append(candidate)
    if not blank_boxes:
        return None, []
    tokens = [
        ((word.bbox.x0 + word.bbox.x1) / 2, word.text.strip())
        for word in words if word.text.strip()
    ]
    tokens.extend(
        ((blank.x0 + blank.x1) / 2, "____") for blank in blank_boxes
    )
    recovered = " ".join(value for _, value in sorted(tokens)).strip()
    recovered = re.sub(r"\s+([.,;:!?])", r"\1", recovered)
    return recovered or None, sorted(blank_boxes, key=lambda item: item.x0)


def build_text_content(
    native_text: str | None,
    ocr_text: str | None,
    native_confidence: float,
    ocr_confidence: float,
) -> tuple[TextContent, str | None, bool]:
    native = normalize_text(native_text)
    ocr = normalize_text(ocr_text)
    if native and ocr and native == ocr:
        return (
            TextContent(
                native_text=native,
                ocr_text=ocr,
                resolution=Resolution(
                    selected_source="both",
                    reason="native_ocr_agree",
                    confidence=min(native_confidence, ocr_confidence),
                ),
                resolved_text=native,
            ),
            None,
            False,
        )
    if native and not ocr:
        return (
            TextContent(
                native_text=native,
                resolution=Resolution(
                    selected_source="native",
                    reason="ocr_empty",
                    confidence=native_confidence,
                ),
                resolved_text=native,
            ),
            None,
            False,
        )
    if ocr and not native:
        return (
            TextContent(
                ocr_text=ocr,
                resolution=Resolution(
                    selected_source="ocr",
                    reason="native_empty",
                    confidence=ocr_confidence,
                ),
                resolved_text=ocr,
            ),
            None,
            False,
        )
    if native and ocr:
        native_critical = _critical_tokens(native)
        ocr_critical = _critical_tokens(ocr)
        critical = native_critical != ocr_critical
        conflict_type = "critical_text_conflict" if critical else "general_text_conflict"
        if critical:
            return (
                TextContent(
                    native_text=native,
                    ocr_text=ocr,
                    resolution=Resolution(
                        selected_source="none",
                        reason="unresolved_critical_conflict",
                        confidence=0.0,
                    ),
                    resolved_text=None,
                    resolution_status=ResolutionStatus.AMBIGUOUS,
                    requires_human_review=True,
                ),
                conflict_type,
                True,
            )
        selected = "native" if native_confidence >= ocr_confidence else "ocr"
        resolved = native if selected == "native" else ocr
        return (
            TextContent(
                native_text=native,
                ocr_text=ocr,
                resolution=Resolution(
                    selected_source=selected,
                    reason="higher_confidence_with_conflict",
                    confidence=max(native_confidence, ocr_confidence),
                ),
                resolved_text=resolved,
            ),
            conflict_type,
            critical,
        )
    return (
        TextContent(
            resolution=Resolution(selected_source="none", reason="no_text", confidence=0),
            resolved_text=None,
        ),
        "missing_content_conflict",
        False,
    )
