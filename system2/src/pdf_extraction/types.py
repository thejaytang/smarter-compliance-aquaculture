from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re


@dataclass(frozen=True)
class PixelBox:
    x0: int
    y0: int
    x1: int
    y1: int

    @property
    def width(self) -> int:
        return max(0, self.x1 - self.x0)

    @property
    def height(self) -> int:
        return max(0, self.y1 - self.y0)

    @property
    def area(self) -> int:
        return self.width * self.height

    def contains_center(self, other: "PixelBox") -> bool:
        cx = (other.x0 + other.x1) / 2
        cy = (other.y0 + other.y1) / 2
        return self.x0 <= cx <= self.x1 and self.y0 <= cy <= self.y1

    def overlaps(self, other: "PixelBox") -> bool:
        return not (
            self.x1 <= other.x0
            or other.x1 <= self.x0
            or self.y1 <= other.y0
            or other.y1 <= self.y0
        )


@dataclass(frozen=True)
class NativeObject:
    id: str
    text: str
    bbox_points: tuple[float, float, float, float]
    confidence: float = 1.0
    object_type: str = "word"
    font_name: str | None = None
    font_key: str | None = None
    from_ocr: bool | None = None


@dataclass
class NativePage:
    page_index: int
    width_points: float
    height_points: float
    words: list[NativeObject] = field(default_factory=list)
    bitmap_boxes_points: list[tuple[float, float, float, float]] = field(default_factory=list)
    characters: list[NativeObject] = field(default_factory=list)
    text_lines: list[NativeObject] = field(default_factory=list)
    shapes: list[dict[str, object]] = field(default_factory=list)
    bitmap_resources: list[dict[str, object]] = field(default_factory=list)
    backend: str = "docling-parse"
    fallback_reason: str | None = None


@dataclass(frozen=True)
class OCRWord:
    id: str
    text: str
    confidence: float
    bbox: PixelBox
    block_num: int = 0
    paragraph_num: int = 0
    line_num: int = 0


@dataclass
class OCRPage:
    page_index: int
    words: list[OCRWord]
    backend: str
    version: str | None = None
    fallback_reason: str | None = None
    raw_ref: Path | None = None


def ocr_reading_order(word: OCRWord) -> tuple[int, int, int, int, int]:
    """Prefer OCR engine line metadata, then use visual coordinates."""
    if word.block_num or word.paragraph_num or word.line_num:
        return (
            word.block_num,
            word.paragraph_num,
            word.line_num,
            word.bbox.x0,
            word.bbox.y0,
        )
    return (0, 0, word.bbox.y0, word.bbox.x0, 0)


def join_ocr_words(words: list[OCRWord]) -> str:
    """Join OCR units in reading order and repair visual line-end hyphenation."""
    ordered = sorted(words, key=ocr_reading_order)
    parts: list[str] = []
    prior_line: tuple[int, int, int] | None = None
    for word in ordered:
        current_line = (word.block_num, word.paragraph_num, word.line_num)
        text = word.text.strip()
        if not text:
            continue
        is_new_line = prior_line is not None and current_line != prior_line
        if is_new_line and parts and parts[-1].endswith("-") and re.match(r"^[a-z]", text):
            right_token = text.split(maxsplit=1)[0]
            preserve = (
                "http://" in parts[-1]
                or "https://" in parts[-1]
                or "www." in parts[-1]
                or parts[-1].count("-") >= 2
                or "-" in right_token
            )
            parts[-1] = parts[-1] + text if preserve else parts[-1][:-1] + text
        else:
            parts.append(text)
        prior_line = current_line
    return " ".join(parts).strip()


@dataclass
class LayoutRegion:
    id: str
    label: str
    bbox: PixelBox
    confidence: float
    text: str = ""
    word_ids: list[str] = field(default_factory=list)
    auxiliary_word_ids: list[str] = field(default_factory=list)
    index_text: str | None = None
    note_text: str | None = None
    index_bbox: PixelBox | None = None
    note_bbox: PixelBox | None = None
    heading_level: int | None = None
    native_object_ids: list[str] = field(default_factory=list)
    list_marker: str | None = None
    list_level: int | None = None
    indent_points: float | None = None
    profile_template_id: str | None = None
    profile_repair: bool = False
    profile_column_boundary_px: int | None = None
    visual_reclassification_reason: str | None = None


@dataclass
class RenderedPage:
    page_index: int
    image_path: Path
    width_points: float
    height_points: float
    width_px: int
    height_px: int
    rotation: int

    def pixel_to_points(self, box: PixelBox) -> tuple[float, float, float, float]:
        sx = self.width_points / self.width_px
        sy = self.height_points / self.height_px
        return box.x0 * sx, box.y0 * sy, box.x1 * sx, box.y1 * sy
