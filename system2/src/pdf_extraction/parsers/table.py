from __future__ import annotations

import html
import importlib.util
import json
import re
import tempfile
import statistics
from collections import Counter
from dataclasses import dataclass
from html.parser import HTMLParser
from importlib.metadata import version
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from ..config import TableSettings
from ..models import BoundingBox, Resolution, ResolutionStatus, TableCell, TableData, TextContent
from ..ocr import OCRBackend
from ..ocr import configure_paddle_runtime
from ..types import LayoutRegion, OCRPage, OCRWord, PixelBox, RenderedPage, ocr_reading_order
from ..ingest.renderer import PDFRenderer


def _cluster(indices: np.ndarray, tolerance: int = 3) -> list[int]:
    if indices.size == 0:
        return []
    groups: list[list[int]] = [[int(indices[0])]]
    for value in map(int, indices[1:]):
        if value - groups[-1][-1] <= tolerance:
            groups[-1].append(value)
        else:
            groups.append([value])
    return [round(sum(group) / len(group)) for group in groups]


def _grid_positions(image: np.ndarray) -> tuple[list[int], list[int]]:
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 12
    )
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(12, image.shape[1] // 8), 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(10, image.shape[0] // 6)))
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)
    ys = _cluster(np.where(np.sum(horizontal > 0, axis=1) > image.shape[1] * 0.25)[0])
    xs = _cluster(np.where(np.sum(vertical > 0, axis=0) > image.shape[0] * 0.25)[0])
    # A border exactly at the crop edge can disappear during morphology. Restore it
    # only when the opposite border proves that the grid itself starts at that edge.
    if xs and xs[0] <= 12 and image.shape[1] - 1 - xs[-1] > 12:
        xs.append(image.shape[1] - 1)
    if ys and ys[0] <= 12 and image.shape[0] - 1 - ys[-1] > 12:
        ys.append(image.shape[0] - 1)
    return xs, ys


def _merged_cell_specs(
    image: np.ndarray, xs: list[int], ys: list[int]
) -> list[tuple[int, int, int, int]]:
    """Infer rectangular row/column spans from missing internal ruled-line segments."""
    rows, columns = len(ys) - 1, len(xs) - 1
    parents = list(range(rows * columns))

    def find(value: int) -> int:
        while parents[value] != value:
            parents[value] = parents[parents[value]]
            value = parents[value]
        return value

    def union(left: int, right: int) -> None:
        a, b = find(left), find(right)
        if a != b:
            parents[b] = a

    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    ink = gray < 160
    for row in range(rows):
        y0, y1 = ys[row] + 3, ys[row + 1] - 3
        for boundary in range(1, columns):
            x = xs[boundary]
            band = ink[max(0, y0):max(y0 + 1, y1), max(0, x - 2):min(image.shape[1], x + 3)]
            coverage = float(np.mean(np.any(band, axis=1))) if band.size else 1.0
            if coverage < 0.45:
                union(row * columns + boundary - 1, row * columns + boundary)
    for boundary in range(1, rows):
        y = ys[boundary]
        for column in range(columns):
            x0, x1 = xs[column] + 3, xs[column + 1] - 3
            band = ink[max(0, y - 2):min(image.shape[0], y + 3), max(0, x0):max(x0 + 1, x1)]
            coverage = float(np.mean(np.any(band, axis=0))) if band.size else 1.0
            if coverage < 0.45:
                union((boundary - 1) * columns + column, boundary * columns + column)

    groups: dict[int, list[tuple[int, int]]] = {}
    for row in range(rows):
        for column in range(columns):
            groups.setdefault(find(row * columns + column), []).append((row, column))
    specs: list[tuple[int, int, int, int]] = []
    for members in groups.values():
        row_values = [item[0] for item in members]
        column_values = [item[1] for item in members]
        r0, r1 = min(row_values), max(row_values)
        c0, c1 = min(column_values), max(column_values)
        if len(members) != (r1 - r0 + 1) * (c1 - c0 + 1):
            specs.extend((row, column, 1, 1) for row, column in members)
        else:
            specs.append((r0, c0, r1 - r0 + 1, c1 - c0 + 1))
    return sorted(specs)


def _split_profile_requirement_spans(
    specs: list[tuple[int, int, int, int]],
    words: list[OCRWord],
    region: PixelBox,
    xs: list[int],
    ys: list[int],
    *,
    profile_template_id: str | None,
) -> tuple[list[tuple[int, int, int, int]], bool]:
    """Restore the two semantic columns when a repeated requirement row lacks a rule.

    The dark header often exposes the two-column grid while the white body omits the
    vertical stroke. OpenCV correctly observes the missing stroke as a visual span,
    but the learned document template tells us that a numbered indicator and its
    requirement are separate semantic cells. Split only when the left side contains
    exactly a hierarchical requirement number and the right side contains text.
    """
    if not profile_template_id or len(xs) - 1 != 2:
        return specs, False
    repaired: list[tuple[int, int, int, int]] = []
    changed = False
    for row, column, row_span, column_span in specs:
        if row > 0 and column == 0 and row_span == 1 and column_span == 2:
            left = PixelBox(
                region.x0 + xs[0], region.y0 + ys[row],
                region.x0 + xs[1], region.y0 + ys[row + 1],
            )
            right = PixelBox(
                region.x0 + xs[1], region.y0 + ys[row],
                region.x0 + xs[2], region.y0 + ys[row + 1],
            )
            left_text, _ = _text_for_words(_words_in_box(words, left))
            right_text, _ = _text_for_words(_words_in_box(words, right))
            if re.fullmatch(r"\d+(?:\.\d+)+[.:]?", left_text.strip()) and right_text.strip():
                repaired.extend(((row, 0, 1, 1), (row, 1, 1, 1)))
                changed = True
                continue
        repaired.append((row, column, row_span, column_span))
    return sorted(repaired), changed


def _words_in_box(words: list[OCRWord], box: PixelBox) -> list[OCRWord]:
    return [word for word in words if box.contains_center(word.bbox)]


def _text_for_words(words: list[OCRWord]) -> tuple[str, float]:
    ordered = sorted(words, key=ocr_reading_order)
    text = " ".join(word.text for word in ordered).strip()
    confidence = sum(word.confidence for word in ordered) / len(ordered) if ordered else 0.0
    return text, confidence


def _profile_text_for_words(words: list[OCRWord], boundary: int) -> tuple[str, float]:
    """Join requirement-cell words without flattening semantic sub-lists.

    Physical line wrapping is joined with spaces.  Lines that start a labelled
    clause or bullet remain separated so a downstream Markdown cell can render
    the requirement's internal structure with ``<br>``.
    """
    ordered = sorted(words, key=ocr_reading_order)
    lines: list[list[OCRWord]] = []
    line_keys: list[tuple[int, int, int] | int] = []
    for word in ordered:
        if word.block_num or word.paragraph_num or word.line_num:
            line_key: tuple[int, int, int] | int = (
                word.block_num, word.paragraph_num, word.line_num
            )
        else:
            line_key = word.bbox.y0
        if not line_keys or line_key != line_keys[-1]:
            line_keys.append(line_key)
            lines.append([])
        lines[-1].append(word)

    rendered: list[str] = []
    for line_words in lines:
        visible = [word for word in line_words if word.text.strip()]
        ordinary_heights = [
            word.bbox.height for word in visible
            if not re.fullmatch(r"\d{1,2}", word.text.strip())
        ]
        ordinary_bottoms = [
            word.bbox.y1 for word in visible
            if not re.fullmatch(r"\d{1,2}", word.text.strip())
        ]
        median_height = statistics.median(ordinary_heights) if ordinary_heights else 0.0
        median_bottom = statistics.median(ordinary_bottoms) if ordinary_bottoms else 0.0
        parts: list[str] = []
        for position, word in enumerate(visible):
            token = word.text.strip()
            is_superscript = (
                position > 0
                and bool(re.fullmatch(r"\d{1,2}", token))
                and median_height > 0
                and word.bbox.height <= median_height * 0.72
                and word.bbox.y1 <= median_bottom - median_height * 0.18
            )
            parts.append(f"[^{token}]" if is_superscript else token)
        if not parts:
            continue
        if (
            parts[0] in {"o", "○", "◦"}
            and len(parts) > 1
            and line_words[0].bbox.x0 >= boundary + 2
        ):
            parts[0] = "•"
        value = re.sub(r"\s+(\[\^\d+\])", r"\1", " ".join(parts))
        rendered.append(re.sub(r"\s+([,.;:!?])", r"\1", value).strip())

    semantic_start = re.compile(r"^(?:[a-z][.)]|[•●▪▫])\s+", flags=re.I)
    combined: list[str] = []
    for value in rendered:
        if not combined:
            combined.append(value)
            continue
        starts_new_item = bool(semantic_start.match(value))
        applicability_then_requirement = (
            combined[-1].casefold().startswith(("indicator applicability:", "indicator scope:"))
            and value.casefold().startswith("the uoc shall")
        )
        if starts_new_item or applicability_then_requirement:
            combined.append(value)
        else:
            combined[-1] = f"{combined[-1]} {value}"
    text = "\n".join(combined).strip()
    confidence = sum(word.confidence for word in ordered) / len(ordered) if ordered else 0.0
    return text, confidence


def _profile_indicator_text_for_words(words: list[OCRWord]) -> tuple[str, float]:
    """Preserve an optional semantic label below a numbered Indicator.

    Some repeated two-column tables place labels such as ``Reporting`` in the
    Indicator cell beneath the number.  It remains one semantic cell, but the
    requirement identifier must stay machine-readable as its first line.
    """
    text, confidence = _text_for_words(words)
    match = re.match(r"^(\d+(?:\.\d+)+)[.:]?(?:\s+(.+))?$", text.strip(), flags=re.S)
    if not match:
        return text, confidence
    label = (match.group(2) or "").strip()
    return (f"{match.group(1)}\n{label}" if label else match.group(1)), confidence


def _repair_profile_row_scope_leakage(
    texts: dict[tuple[int, int], str], body_rows: int,
) -> list[dict[str, object]]:
    """Move a duplicated next-row scope line out of the preceding row.

    Italic scope text can sit a few pixels above its Indicator number.  Native
    geometry then appends the next row's scope to the prior Requirement.  The
    repair is allowed only when the exact same scope already starts the prior
    row and is duplicated at its end, while the next row starts directly with
    the normative sentence.
    """
    repairs: list[dict[str, object]] = []
    for row in range(1, body_rows):
        current = texts.get((row, 1), "").strip()
        following = texts.get((row + 1, 1), "").strip()
        first_line = current.split("\n", 1)[0].strip()
        if (
            not first_line.casefold().startswith(("indicator applicability:", "indicator scope:"))
            or current.count(first_line) < 2
            or not current.endswith(first_line)
            or not following.casefold().startswith("the uoc shall")
        ):
            continue
        texts[(row, 1)] = current[:-len(first_line)].rstrip()
        texts[(row + 1, 1)] = f"{first_line}\n{following}"
        repairs.append({"from_row": row, "to_row": row + 1, "text": first_line})
    return repairs


def _html_cell_text(value: str) -> str:
    return html.escape(value).replace("\n", "<br>")


def _to_bbox(page: RenderedPage, box: PixelBox) -> BoundingBox:
    x0, y0, x1, y1 = page.pixel_to_points(box)
    return BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1)


def _profile_requirement_table(
    page: RenderedPage,
    region: LayoutRegion,
    ocr_page: OCRPage,
    crop_ref: Path,
    block_id: str,
) -> ParsedTable | None:
    """Build the learned Indicator/Requirement schema from native word geometry.

    A physical table can contain one or several numbered requirements.  The
    document profile fixes the semantic grid at two columns; numbered anchors in
    the left column define body-row boundaries.  This prevents a generic cell
    detector from turning prose words into many narrow columns on border-light
    tables.
    """
    boundary = region.profile_column_boundary_px
    if not region.profile_template_id or boundary is None:
        return None
    words = _words_in_box(ocr_page.words, region.bbox)
    numbered = [
        word for word in words
        if re.fullmatch(r"\d+(?:\.\d+)+[.:]?", word.text.strip())
        and (word.bbox.x0 + word.bbox.x1) / 2 < boundary
    ]
    if not numbered:
        return None
    numbered.sort(key=lambda word: (word.bbox.y0, word.bbox.x0))
    number_word = numbered[0]
    header_words = [word for word in words if word.bbox.y1 < number_word.bbox.y0]
    groups: dict[tuple[int, int], list[OCRWord]] = {
        (0, 0): [word for word in header_words if (word.bbox.x0 + word.bbox.x1) / 2 < boundary],
        (0, 1): [word for word in header_words if (word.bbox.x0 + word.bbox.x1) / 2 >= boundary],
    }
    row_word_groups: list[list[OCRWord]] = []
    for index, anchor in enumerate(numbered):
        next_top = numbered[index + 1].bbox.y0 if index + 1 < len(numbered) else region.bbox.y1 + 1
        row_words = [
            word for word in words
            if word.bbox.y0 >= anchor.bbox.y0 and word.bbox.y0 < next_top
        ]
        row_word_groups.append(row_words)
        groups[(index + 1, 0)] = [
            word for word in row_words
            if (word.bbox.x0 + word.bbox.x1) / 2 < boundary
        ]
        groups[(index + 1, 1)] = [
            word for word in row_words
            if (word.bbox.x0 + word.bbox.x1) / 2 >= boundary
        ]
    texts = {}
    for position, group in groups.items():
        if position[0] > 0 and position[1] == 1:
            texts[position] = _profile_text_for_words(group, boundary)[0]
        elif position[0] > 0 and position[1] == 0:
            texts[position] = _profile_indicator_text_for_words(group)[0]
        else:
            texts[position] = _text_for_words(group)[0]
    row_scope_repairs = _repair_profile_row_scope_leakage(texts, len(numbered))
    if (
        not texts[(0, 0)].casefold().startswith("indicator")
        or not texts[(0, 1)].casefold().startswith("requirement")
        or any(
            not re.match(r"^\d+(?:\.\d+)+(?:\n|$)", texts[(row, 0)].strip())
            or not texts[(row, 1)].strip()
            for row in range(1, len(numbered) + 1)
        )
    ):
        return None
    header_bottom = max(word.bbox.y1 for word in header_words)
    body_top = min(word.bbox.y0 for word in row_word_groups[0])
    header_boundary = round((header_bottom + body_top) / 2)
    row_boundaries = [region.bbox.y0, header_boundary]
    for index in range(len(numbered) - 1):
        current_bottom = max(word.bbox.y1 for word in row_word_groups[index])
        row_boundaries.append(round((current_bottom + numbered[index + 1].bbox.y0) / 2))
    row_boundaries.append(region.bbox.y1)
    boxes: dict[tuple[int, int], PixelBox] = {}
    for row in range(len(numbered) + 1):
        boxes[(row, 0)] = PixelBox(
            region.bbox.x0, row_boundaries[row], boundary, row_boundaries[row + 1]
        )
        boxes[(row, 1)] = PixelBox(
            boundary, row_boundaries[row], region.bbox.x1, row_boundaries[row + 1]
        )
    cells: list[TableCell] = []
    for (row, column), group in groups.items():
        if row > 0 and column == 1:
            _, confidence = _profile_text_for_words(group, boundary)
            text = texts[(row, column)]
        elif row > 0 and column == 0:
            text, confidence = _profile_indicator_text_for_words(group)
        else:
            text, confidence = _text_for_words(group)
        cells.append(TableCell(
            id=f"{block_id}_cell_r{row:03d}_c{column:03d}",
            row=row,
            column=column,
            bbox=_to_bbox(page, boxes[(row, column)]),
            page_index=page.page_index,
            content=TextContent(
                ocr_text=text,
                resolved_text=text,
                resolution=Resolution(
                    selected_source="ocr",
                    reason="document_profile_semantic_cell",
                    confidence=confidence,
                ),
            ),
            is_header=row == 0,
        ))
    table_html = (
        "<table><tr><th>" + _html_cell_text(texts[(0, 0)]) + "</th><th>"
        + _html_cell_text(texts[(0, 1)]) + "</th></tr>"
        + "".join(
            "<tr><td>" + _html_cell_text(texts[(row, 0)]) + "</td><td>"
            + _html_cell_text(texts[(row, 1)]) + "</td></tr>"
            for row in range(1, len(numbered) + 1)
        )
        + "</table>"
    )
    return ParsedTable(
        data=TableData(
            row_count=len(numbered) + 1,
            column_count=2,
            cells=cells,
            parser_backend=f"document-profile+{ocr_page.backend}",
            html=table_html,
        ),
        crop_ref=crop_ref,
        issues=[],
        operation={
            "operation": "table_structure_resolution",
            "selected": "document_profile_semantic_grid",
            "template_id": region.profile_template_id,
            "profile_column_repair": True,
            "row_scope_reassignments": row_scope_repairs,
            "missing_source_tokens": [],
            "fallback_reason": None,
        },
    )


def _implicit_row_boundaries(
    words: list[OCRWord], region: PixelBox, crop_height: int
) -> list[int]:
    """Infer unruled table rows from OCR baselines inside a vertically ruled grid."""
    local_words = _words_in_box(words, region)
    if not local_words:
        return []
    ordered = sorted(
        (
            ((word.bbox.y0 + word.bbox.y1) / 2 - region.y0, max(1, word.bbox.height))
            for word in local_words
        ),
        key=lambda item: item[0],
    )
    groups: list[list[tuple[float, int]]] = []
    for center, height in ordered:
        if not groups:
            groups.append([(center, height)])
            continue
        prior_center = sum(item[0] for item in groups[-1]) / len(groups[-1])
        prior_height = sum(item[1] for item in groups[-1]) / len(groups[-1])
        tolerance = max(3.0, min(prior_height, height) * 0.60)
        if center - prior_center <= tolerance:
            groups[-1].append((center, height))
        else:
            groups.append([(center, height)])
    centers = [sum(item[0] for item in group) / len(group) for group in groups]
    if len(centers) < 2:
        return []
    boundaries = [0]
    boundaries.extend(round((left + right) / 2) for left, right in zip(centers, centers[1:]))
    boundaries.append(crop_height)
    return [
        max(0, min(crop_height, value))
        for index, value in enumerate(boundaries)
        if index == 0 or value > boundaries[index - 1]
    ]


def _normalize_table_math_text(value: str) -> str:
    """Convert compact OCR math into a stable inline-LaTeX representation."""
    text = value.strip()
    indexed = re.fullmatch(r"([A-Za-z])\s*([0-9]+)", text)
    if indexed:
        return f"${indexed.group(1)}_{{{indexed.group(2)}}}$"

    derivative = re.fullmatch(
        r"([A-Za-z])([il1])\s*=\s*∂\s*([A-Za-z])\s*/\s*∂\s*"
        r"([A-Za-z])(?:([,il1]))?",
        text,
    )
    if derivative:
        index = "i" if derivative.group(2) in {"i", "l", "1"} else derivative.group(2)
        return (
            f"${derivative.group(1)}_{{{index}}}=\\partial {derivative.group(3)} "
            f"/ \\partial {derivative.group(4)}_{{{index}}}$"
        )

    product = re.fullmatch(
        r"\|([A-Za-z])([il1])\|\s*[×x]\s*([A-Za-z])\("
        r"([A-Za-z])([il1])\)",
        text,
    )
    if product:
        index = "i" if product.group(5) in {"i", "l", "1"} else product.group(5)
        return (
            f"$\\left|{product.group(1)}_{{{index}}}\\right| \\times "
            f"{product.group(3)}\\left({product.group(4)}_{{{index}}}\\right)$"
        )
    return text


def _postprocess_table_cells(cells: list[TableCell]) -> None:
    replacements: dict[str, tuple[str, str]] = {}
    for cell in cells:
        original = cell.content.resolved_text or ""
        normalized = _normalize_table_math_text(original)
        if normalized != original:
            replacements[cell.id] = (normalized, "deterministic_table_math_normalization")

    columns_with_seconds = {
        cell.column
        for cell in cells
        if re.fullmatch(r"\d+(?:\.\d+)?\s*s", cell.content.resolved_text or "", re.I)
    }
    for cell in cells:
        if cell.column not in columns_with_seconds:
            continue
        original = cell.content.resolved_text or ""
        duration = re.fullmatch(r"(\d+(?:\.\d+)?)\s*[8n]", original, re.I)
        if duration:
            replacements[cell.id] = (
                f"{duration.group(1)}s",
                "table_column_unit_consistency",
            )

    for cell in cells:
        replacement = replacements.get(cell.id)
        if replacement is None:
            continue
        normalized, reason = replacement
        confidence = cell.content.resolution.confidence
        cell.content.review_text = normalized
        cell.content.resolved_text = normalized
        cell.content.resolution = Resolution(
            selected_source="review",
            reason=reason,
            confidence=confidence,
        )


@dataclass
class ParsedTable:
    data: TableData
    crop_ref: Path
    issues: list[str]
    operation: dict[str, object]
    ancillary_text: str | None = None


class _StructureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[tuple[int, int]]] = []
        self.current: list[tuple[int, int]] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self.current = []
        elif tag in {"td", "th"} and self.current is not None:
            values = dict(attrs)
            self.current.append((int(values.get("rowspan") or 1), int(values.get("colspan") or 1)))

    def handle_endtag(self, tag: str) -> None:
        if tag == "tr" and self.current is not None:
            self.rows.append(self.current)
            self.current = None


@dataclass(frozen=True)
class RecognitionHTMLCell:
    row_span: int
    column_span: int
    text: str
    is_header: bool


class _RecognitionHTMLParser(HTMLParser):
    """Parse the text and span evidence emitted by PP-TableMagic."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[RecognitionHTMLCell]] = []
        self.current_row: list[RecognitionHTMLCell] | None = None
        self.current_cell: dict[str, object] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.casefold()
        if tag == "tr":
            self.current_row = []
        elif tag in {"td", "th"} and self.current_row is not None:
            values = dict(attrs)
            self.current_cell = {
                "row_span": max(1, int(values.get("rowspan") or 1)),
                "column_span": max(1, int(values.get("colspan") or 1)),
                "text": [],
                "is_header": tag == "th",
            }
        elif tag == "br" and self.current_cell is not None:
            text_parts = self.current_cell["text"]
            assert isinstance(text_parts, list)
            text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.current_cell is not None:
            text_parts = self.current_cell["text"]
            assert isinstance(text_parts, list)
            text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if tag in {"td", "th"} and self.current_cell is not None and self.current_row is not None:
            text_parts = self.current_cell["text"]
            assert isinstance(text_parts, list)
            self.current_row.append(RecognitionHTMLCell(
                row_span=int(self.current_cell["row_span"]),
                column_span=int(self.current_cell["column_span"]),
                text=re.sub(r"\s+", " ", "".join(text_parts)).strip(),
                is_header=bool(self.current_cell["is_header"]),
            ))
            self.current_cell = None
        elif tag == "tr" and self.current_row is not None:
            self.rows.append(self.current_row)
            self.current_row = None


@dataclass(frozen=True)
class StructureProposal:
    rows: int
    columns: int
    confidence: float
    cells: list[tuple[int, int, int, int, PixelBox]]


@dataclass(frozen=True)
class RecognitionProposal:
    rows: int
    columns: int
    confidence: float
    cells: list[tuple[int, int, int, int, PixelBox, str, bool]]
    html: str
    geometry_repairs: tuple[str, ...] = ()


def _repair_recognition_geometry(proposal: RecognitionProposal) -> RecognitionProposal:
    """Repair a model HTML row/column assignment contradicted by cell boxes."""
    if (
        proposal.columns != 1
        or proposal.rows < 2
        or len(proposal.cells) != proposal.rows
        or any(cell[2] != 1 or cell[3] != 1 for cell in proposal.cells)
    ):
        return proposal
    ordered = sorted(proposal.cells, key=lambda cell: cell[4].x0)
    reference = ordered[0][4]
    for prior, current in zip(ordered, ordered[1:], strict=False):
        overlap = max(0, prior[4].x1 - current[4].x0)
        overlap_tolerance = max(4, round(min(prior[4].width, current[4].width) * 0.12))
        if overlap > overlap_tolerance:
            return proposal
    for cell in ordered[1:]:
        box = cell[4]
        overlap = max(0, min(reference.y1, box.y1) - max(reference.y0, box.y0))
        if overlap / max(1, min(reference.height, box.height)) < 0.70:
            return proposal
    header_like = all(cell[5].strip().endswith(":") for cell in ordered)
    repaired = [
        (0, column, 1, 1, cell[4], cell[5], cell[6] or header_like)
        for column, cell in enumerate(ordered)
    ]
    return RecognitionProposal(
        rows=1,
        columns=len(repaired),
        confidence=proposal.confidence,
        cells=repaired,
        html=proposal.html,
        geometry_repairs=proposal.geometry_repairs + ("same_band_cells_transposed_to_columns",),
    )


def _recognition_geometry_consistent(proposal: RecognitionProposal) -> bool:
    """Return whether model cells form an ordered, non-overlapping grid."""
    tolerance = 2
    for row in range(proposal.rows):
        cells = sorted(
            (cell for cell in proposal.cells if cell[0] == row),
            key=lambda cell: cell[1],
        )
        if not cells:
            return False
        prior_column_end = 0
        prior_x1: int | None = None
        for _, column, _, column_span, box, _, _ in cells:
            if column < prior_column_end:
                return False
            if prior_x1 is not None and box.x0 < prior_x1 - tolerance:
                return False
            if box.x1 <= box.x0:
                return False
            prior_column_end = column + column_span
            prior_x1 = box.x1
    return True


class PaddleTableRecognitionBackend:
    """Full PP-TableMagic pipeline with table classification, cells and OCR."""

    name = "PP-TableMagic/TableRecognitionPipelineV2"

    def __init__(self) -> None:
        if importlib.util.find_spec("paddleocr") is None:
            raise RuntimeError("paddleocr package is not installed")
        self.version = version("paddleocr")
        self._model = None

    def _load(self) -> None:
        if self._model is not None:
            return
        configure_paddle_runtime()
        from paddleocr import TableRecognitionPipelineV2

        self._model = TableRecognitionPipelineV2(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_layout_detection=False,
            use_ocr_model=True,
            engine="paddle",
            device="cpu",
        )

    def analyze(self, crop_ref: Path) -> RecognitionProposal:
        self._load()
        assert self._model is not None
        output = list(self._model.predict(
            str(crop_ref),
            use_layout_detection=False,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_ocr_results_with_table_cells=True,
        ))
        if not output:
            raise RuntimeError("PP-TableMagic full pipeline returned no result")
        payload = output[0].json if hasattr(output[0], "json") else output[0]
        if isinstance(payload, str):
            payload = json.loads(payload)
        data = payload.get("res", payload)
        candidates = data.get("table_res_list") or []
        if not candidates:
            raise RuntimeError("PP-TableMagic full pipeline returned no table")

        parsed: list[tuple[dict[str, object], _RecognitionHTMLParser]] = []
        for candidate in candidates:
            parser = _RecognitionHTMLParser()
            parser.feed(str(candidate.get("pred_html") or ""))
            if parser.rows:
                parsed.append((candidate, parser))
        if not parsed:
            raise RuntimeError("PP-TableMagic full pipeline returned no HTML rows")
        candidate, parser = max(
            parsed,
            key=lambda item: sum(len(row) for row in item[1].rows),
        )

        positions: list[tuple[int, int, int, int, str, bool]] = []
        occupied_until: dict[int, int] = {}
        max_columns = 0
        for row_index, row in enumerate(parser.rows):
            column = 0
            for cell in row:
                while occupied_until.get(column, 0) > row_index:
                    column += 1
                positions.append((
                    row_index, column, cell.row_span, cell.column_span,
                    cell.text, cell.is_header,
                ))
                for offset in range(cell.column_span):
                    occupied_until[column + offset] = max(
                        occupied_until.get(column + offset, 0),
                        row_index + cell.row_span,
                    )
                column += cell.column_span
            while occupied_until.get(column, 0) > row_index:
                column += 1
            max_columns = max(max_columns, column)

        boxes: list[PixelBox] = []
        for raw_box in candidate.get("cell_box_list") or []:
            values = raw_box.tolist() if hasattr(raw_box, "tolist") else list(raw_box)
            if len(values) == 4:
                x0, y0, x1, y1 = values
            elif len(values) >= 8:
                x_values, y_values = values[0::2], values[1::2]
                x0, x1, y0, y1 = min(x_values), max(x_values), min(y_values), max(y_values)
            else:
                continue
            boxes.append(PixelBox(
                max(0, round(float(x0))), max(0, round(float(y0))),
                max(1, round(float(x1))), max(1, round(float(y1))),
            ))
        if len(boxes) < len(positions):
            raise RuntimeError(
                "PP-TableMagic cell boxes do not cover the recognized HTML cells"
            )
        cells = [
            (*position[:4], box, position[4], position[5])
            for position, box in zip(positions, boxes, strict=False)
        ]
        # Cell detectors occasionally return one outlier box for trailing
        # ancillary text. When the HTML describes a regular grid, robust row
        # and column medians recover shared boundaries without changing spans.
        if len(parser.rows) >= 2 and max_columns >= 2:
            row_tops = {
                row: round(float(np.median([
                    cell[4].y0 for cell in cells
                    if cell[0] == row and cell[2] == 1
                ])))
                for row in range(len(parser.rows))
                if any(cell[0] == row and cell[2] == 1 for cell in cells)
            }
            row_bottoms = {
                row: round(float(np.median([
                    cell[4].y1 for cell in cells
                    if cell[0] == row and cell[2] == 1
                ])))
                for row in range(len(parser.rows))
                if any(cell[0] == row and cell[2] == 1 for cell in cells)
            }
            column_lefts = {
                column: round(float(np.median([
                    cell[4].x0 for cell in cells
                    if cell[1] == column and cell[3] == 1
                ])))
                for column in range(max_columns)
                if any(cell[1] == column and cell[3] == 1 for cell in cells)
            }
            column_rights = {
                column: round(float(np.median([
                    cell[4].x1 for cell in cells
                    if cell[1] == column and cell[3] == 1
                ])))
                for column in range(max_columns)
                if any(cell[1] == column and cell[3] == 1 for cell in cells)
            }
            if (
                len(row_tops) == len(parser.rows)
                and len(row_bottoms) == len(parser.rows)
                and len(column_lefts) == max_columns
                and len(column_rights) == max_columns
            ):
                regularized: list[tuple[int, int, int, int, PixelBox, str, bool]] = []
                for row, column, row_span, column_span, _, text, is_header in cells:
                    x0, x1 = column_lefts[column], column_rights[column + column_span - 1]
                    y0, y1 = row_tops[row], row_bottoms[row + row_span - 1]
                    if x1 > x0 and y1 > y0:
                        regularized.append((
                            row, column, row_span, column_span,
                            PixelBox(x0, y0, x1, y1), text, is_header,
                        ))
                if len(regularized) == len(cells):
                    cells = regularized
        ocr = candidate.get("table_ocr_pred") or {}
        scores = [float(value) for value in ocr.get("rec_scores", [])]
        confidence = sum(scores) / len(scores) if scores else 0.85
        return RecognitionProposal(
            rows=len(parser.rows),
            columns=max_columns,
            confidence=confidence,
            cells=cells,
            html=str(candidate.get("pred_html") or ""),
        )


class PaddleTableStructureBackend:
    """PP-TableMagic structure proposal using its compact SLANet_plus component."""

    name = "PP-TableMagic/SLANet_plus"

    def __init__(self, settings: TableSettings) -> None:
        if importlib.util.find_spec("paddleocr") is None:
            raise RuntimeError("paddleocr package is not installed")
        configure_paddle_runtime()
        from paddleocr import TableStructureRecognition

        self.model = TableStructureRecognition(
            model_name="SLANet_plus",
            engine=settings.paddle_engine,
            device="cpu",
        )
        self.version = version("paddleocr")

    def analyze(self, crop_ref: Path) -> StructureProposal:
        output = list(self.model.predict(str(crop_ref)))
        if not output:
            raise RuntimeError("PP-TableMagic returned no result")
        payload = output[0].json if hasattr(output[0], "json") else output[0]
        if isinstance(payload, str):
            payload = json.loads(payload)
        data = payload.get("res", payload)
        parser = _StructureParser()
        parser.feed("".join(data.get("structure", [])))
        if not parser.rows:
            raise RuntimeError("PP-TableMagic returned no table rows")
        occupied: dict[int, int] = {}
        max_columns = 0
        positions: list[tuple[int, int, int, int]] = []
        for row_index, row in enumerate(parser.rows):
            column = 0
            for row_span, column_span in row:
                while occupied.get(column, 0) > row_index:
                    column += 1
                positions.append((row_index, column, row_span, column_span))
                for offset in range(column_span):
                    occupied[column + offset] = max(
                        occupied.get(column + offset, 0), row_index + row_span
                    )
                column += column_span
            max_columns = max(max_columns, column)
        boxes: list[PixelBox] = []
        for raw_box in data.get("bbox", []):
            values = raw_box.tolist() if hasattr(raw_box, "tolist") else raw_box
            xs = list(map(int, values[0::2]))
            ys = list(map(int, values[1::2]))
            boxes.append(PixelBox(min(xs), min(ys), max(xs), max(ys)))
        cells = [(*position, box) for position, box in zip(positions, boxes, strict=False)]
        return StructureProposal(
            len(parser.rows), max_columns, float(data.get("structure_score", 0.0)), cells
        )


class Img2TableStructureBackend:
    """Bordered-table structure extraction using img2table's real detector."""

    name = "img2table"

    def __init__(self) -> None:
        if importlib.util.find_spec("img2table") is None:
            raise RuntimeError("img2table package is not installed")
        self.version = version("img2table")

    def analyze(self, crop_ref: Path) -> StructureProposal:
        from img2table.document import Image as Img2TableImage

        tables = Img2TableImage(src=str(crop_ref), detect_rotation=False).extract_tables(
            ocr=None,
            implicit_rows=True,
            implicit_columns=True,
            borderless_tables=False,
            min_confidence=50,
        )
        if not tables:
            raise RuntimeError("img2table returned no bordered table")
        table = max(tables, key=lambda item: len(item.content) * max((len(row) for row in item.content.values()), default=0))
        rows = len(table.content)
        columns = max((len(row) for row in table.content.values()), default=0)
        if not rows or not columns:
            raise RuntimeError("img2table returned an empty cell graph")
        positions: dict[tuple[int, int, int, int], list[tuple[int, int]]] = {}
        boxes: dict[tuple[int, int, int, int], PixelBox] = {}
        for row_index, row in table.content.items():
            for column_index, cell in enumerate(row):
                key = (cell.bbox.x1, cell.bbox.y1, cell.bbox.x2, cell.bbox.y2)
                positions.setdefault(key, []).append((int(row_index), column_index))
                boxes[key] = PixelBox(*key)
        cells: list[tuple[int, int, int, int, PixelBox]] = []
        for key, members in positions.items():
            row_values = [item[0] for item in members]
            column_values = [item[1] for item in members]
            row, column = min(row_values), min(column_values)
            cells.append((
                row, column, max(row_values) - row + 1,
                max(column_values) - column + 1, boxes[key],
            ))
        return StructureProposal(rows, columns, 0.90, sorted(cells))


class GMFTTableStructureBackend:
    """Complex/borderless structure extraction using gmft Table Transformer."""

    name = "gmft/Table Transformer"

    def __init__(self) -> None:
        if importlib.util.find_spec("gmft") is None:
            raise RuntimeError("gmft package is not installed")
        self.version = version("gmft")
        self._detector = None
        self._formatter = None

    def _load(self) -> None:
        from gmft.auto import AutoFormatConfig, AutoTableDetector, AutoTableFormatter

        if self._detector is None:
            self._detector = AutoTableDetector()
        if self._formatter is None:
            self._formatter = AutoTableFormatter(config=AutoFormatConfig(
                torch_device="cpu", remove_null_rows=False,
                semantic_spanning_cells=True, verbosity=0,
            ))

    def analyze(self, crop_ref: Path) -> StructureProposal:
        from gmft.pdf_bindings import PyPDFium2Document

        self._load()
        with Image.open(crop_ref) as image:
            width, height = image.size
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as stream:
                temp_pdf = Path(stream.name)
            image.convert("RGB").save(temp_pdf, "PDF", resolution=72)
        document = PyPDFium2Document(temp_pdf)
        try:
            detected = self._detector.extract(document.get_page(0))
            if not detected:
                raise RuntimeError("gmft returned no table")
            table = max(detected, key=lambda item: item.confidence_score)
            formatted = self._formatter.format(table)
            formatted.df()
            effective = formatted.predictions.effective
            rows = sorted(effective["rows"], key=lambda item: item["bbox"][1])
            columns = sorted(effective["columns"], key=lambda item: item["bbox"][0])
            if not rows or not columns:
                raise RuntimeError("gmft returned no row/column structure")
            cells: list[tuple[int, int, int, int, PixelBox]] = []
            covered: set[tuple[int, int]] = set()
            spans = effective.get("spanning", [])
            for span in spans:
                sx0, sy0, sx1, sy1 = span["bbox"]
                row_ids = [
                    index for index, row in enumerate(rows)
                    if min(sy1, row["bbox"][3]) > max(sy0, row["bbox"][1])
                ]
                column_ids = [
                    index for index, column in enumerate(columns)
                    if min(sx1, column["bbox"][2]) > max(sx0, column["bbox"][0])
                ]
                if not row_ids or not column_ids:
                    continue
                row, column = min(row_ids), min(column_ids)
                cells.append((
                    row, column, len(row_ids), len(column_ids),
                    PixelBox(max(0, round(sx0)), max(0, round(sy0)), min(width, round(sx1)), min(height, round(sy1))),
                ))
                covered.update((r, c) for r in row_ids for c in column_ids)
            for row_index, row in enumerate(rows):
                for column_index, column in enumerate(columns):
                    if (row_index, column_index) in covered:
                        continue
                    x0 = max(0, round(max(row["bbox"][0], column["bbox"][0])))
                    y0 = max(0, round(max(row["bbox"][1], column["bbox"][1])))
                    x1 = min(width, round(min(row["bbox"][2], column["bbox"][2])))
                    y1 = min(height, round(min(row["bbox"][3], column["bbox"][3])))
                    if x1 > x0 and y1 > y0:
                        cells.append((row_index, column_index, 1, 1, PixelBox(x0, y0, x1, y1)))
            confidence = min(
                [float(table.confidence_score)]
                + [float(item["confidence"]) for item in rows + columns]
            )
            return StructureProposal(len(rows), len(columns), confidence, sorted(cells))
        finally:
            document.close()
            temp_pdf.unlink(missing_ok=True)


class TableParser:
    def __init__(self, settings: TableSettings, ocr_backend: OCRBackend) -> None:
        self.settings = settings
        self.ocr_backend = ocr_backend
        self.structure_backend: PaddleTableStructureBackend | None = None
        self.recognition_backend: PaddleTableRecognitionBackend | None = None
        self.bordered_backend: Img2TableStructureBackend | None = None
        self._gmft_backend: GMFTTableStructureBackend | None = None
        self._gmft_attempted = False
        self.fallback_reason: str | None = None
        if settings.recognition_pipeline_enabled and settings.backend in {"auto", "paddle"}:
            try:
                self.recognition_backend = PaddleTableRecognitionBackend()
            except Exception as exc:
                if settings.backend == "paddle":
                    raise
                self.fallback_reason = f"PP-TableMagic full pipeline unavailable: {exc}"
        if settings.backend in {"auto", "paddle"}:
            try:
                self.structure_backend = PaddleTableStructureBackend(settings)
            except Exception as exc:
                if settings.backend == "paddle":
                    raise
                self.fallback_reason = f"PP-TableMagic unavailable: {exc}"
        if settings.img2table_enabled:
            try:
                self.bordered_backend = Img2TableStructureBackend()
            except Exception as exc:
                suffix = f"img2table unavailable: {exc}"
                self.fallback_reason = "; ".join(value for value in (self.fallback_reason, suffix) if value)

    def parse(
        self,
        page: RenderedPage,
        region: LayoutRegion,
        ocr_page: OCRPage,
        crop_dir: str | Path,
        block_id: str,
    ) -> ParsedTable:
        crop_ref = Path(crop_dir) / f"{block_id}.png"
        PDFRenderer.crop(page, region.bbox, crop_ref)
        profile_table = _profile_requirement_table(
            page, region, ocr_page, crop_ref, block_id
        )
        if profile_table is not None:
            return profile_table
        with Image.open(crop_ref) as pil_image:
            image = np.array(pil_image.convert("RGB"))
        xs, ys = _grid_positions(image)
        recognition_error: str | None = None
        if self.recognition_backend is not None:
            try:
                recognition = self.recognition_backend.analyze(crop_ref)
                recognition = _repair_recognition_geometry(recognition)
                if recognition.rows >= 1 and recognition.columns >= 1 and recognition.cells:
                    implicit_rows = _implicit_row_boundaries(
                        ocr_page.words, region.bbox, image.shape[0]
                    )
                    if (
                        len(xs) >= 3
                        and len(ys) <= 3
                        and len(ys) - 1 < len(implicit_rows) - 1
                        and len(implicit_rows) >= 4
                        and len(implicit_rows) - 1 > recognition.rows
                        and recognition.columns == len(xs) - 1
                        and not _recognition_geometry_consistent(recognition)
                    ):
                        implicit_cells = [
                            (
                                row, column, 1, 1,
                                PixelBox(
                                    xs[column], implicit_rows[row],
                                    xs[column + 1], implicit_rows[row + 1],
                                ),
                            )
                            for row in range(len(implicit_rows) - 1)
                            for column in range(len(xs) - 1)
                        ]
                        refined = self._table_from_proposal(
                            page, region, ocr_page, crop_ref,
                            StructureProposal(
                                rows=len(implicit_rows) - 1,
                                columns=len(xs) - 1,
                                confidence=max(0.90, recognition.confidence),
                                cells=implicit_cells,
                            ),
                            selected=f"implicit-rows+{ocr_page.backend}",
                            reason="ocr_rows_exceed_full_pipeline_rows",
                            fallback_reason=None,
                            header_row=False,
                        )
                        if not refined.issues:
                            return refined
                    return self._table_from_recognition(
                        page, region, ocr_page, crop_ref, recognition
                    )
            except Exception as exc:
                recognition_error = str(exc)
        issues: list[str] = []
        proposal: StructureProposal | None = None
        proposal_error: str | None = None
        if self.structure_backend is not None:
            try:
                proposal = self.structure_backend.analyze(crop_ref)
            except Exception as exc:
                proposal_error = "; ".join(
                    value for value in (recognition_error, str(exc)) if value
                )
        if proposal_error is None:
            proposal_error = recognition_error
        bordered_proposal: StructureProposal | None = None
        bordered_error: str | None = None
        if len(xs) >= 2 and len(ys) >= 2 and self.bordered_backend is not None:
            try:
                bordered_proposal = self.bordered_backend.analyze(crop_ref)
            except Exception as exc:
                bordered_error = str(exc)
        if len(xs) < 2 or len(ys) < 2:
            issues.append("table_grid_incomplete")
            if self.settings.gmft_enabled:
                try:
                    if not self._gmft_attempted:
                        self._gmft_backend = GMFTTableStructureBackend()
                        self._gmft_attempted = True
                    if self._gmft_backend is not None:
                        gmft_proposal = self._gmft_backend.analyze(crop_ref)
                        gmft_result = self._table_from_proposal(
                            page, region, ocr_page, crop_ref, gmft_proposal,
                            selected=f"gmft/Table Transformer+{ocr_page.backend}",
                            reason="complex_or_borderless_table",
                            fallback_reason=proposal_error or self.fallback_reason,
                        )
                        if not gmft_result.issues:
                            return gmft_result
                        proposal_error = "; ".join(value for value in (
                            proposal_error,
                            "gmft rejected after evidence check: " + ",".join(gmft_result.issues),
                        ) if value)
                except Exception as exc:
                    proposal_error = "; ".join(
                        value for value in (proposal_error, f"gmft unavailable: {exc}") if value
                    )
            return self._fallback_word_grid(
                page, region, ocr_page, crop_ref, issues, proposal, proposal_error
            )
        if (
            bordered_proposal
            and bordered_proposal.rows == len(ys) - 1
            and bordered_proposal.columns == len(xs) - 1
        ):
            bordered_result = self._table_from_proposal(
                page, region, ocr_page, crop_ref, bordered_proposal,
                selected=f"img2table+{ocr_page.backend}",
                reason="clear_bordered_table",
                fallback_reason=proposal_error or self.fallback_reason,
            )
            if not bordered_result.issues:
                return bordered_result
            bordered_error = (
                "img2table rejected after evidence check: "
                + ",".join(bordered_result.issues)
            )
        cells: list[TableCell] = []
        page_words = _words_in_box(ocr_page.words, region.bbox)
        grid_box = PixelBox(
            region.bbox.x0 + xs[0],
            region.bbox.y0 + ys[0],
            region.bbox.x0 + xs[-1],
            region.bbox.y0 + ys[-1],
        )
        ancillary_words = [word for word in page_words if not grid_box.contains_center(word.bbox)]
        ancillary_groups: dict[tuple[int, int, int], list[OCRWord]] = {}
        for word in ancillary_words:
            ancillary_groups.setdefault(
                (word.block_num, word.paragraph_num, word.line_num), []
            ).append(word)
        ancillary_lines = [
            _text_for_words(words)[0]
            for _, words in sorted(
                ancillary_groups.items(),
                key=lambda item: min(word.bbox.y0 for word in item[1]),
            )
        ]
        ancillary_text = "; ".join(text for text in ancillary_lines if text)
        cell_specs, profile_column_repair = _split_profile_requirement_spans(
            _merged_cell_specs(image, xs, ys),
            page_words,
            region.bbox,
            xs,
            ys,
            profile_template_id=region.profile_template_id,
        )
        for row, column, row_span, column_span in cell_specs:
                local = PixelBox(
                    xs[column], ys[row], xs[column + column_span], ys[row + row_span]
                )
                absolute = PixelBox(
                    region.bbox.x0 + local.x0,
                    region.bbox.y0 + local.y0,
                    region.bbox.x0 + local.x1,
                    region.bbox.y0 + local.y1,
                )
                words = _words_in_box(page_words, absolute)
                text, confidence = _text_for_words(words)
                if not text:
                    cell_crop = Image.fromarray(image[local.y0:local.y1, local.x0:local.x1])
                    text, confidence = self.ocr_backend.recognize_crop(cell_crop)
                content = TextContent(
                    ocr_text=text or None,
                    resolved_text=text or None,
                    resolution=Resolution(
                        selected_source="ocr" if text else "none",
                        reason="table_cell_ocr" if text else "empty_cell",
                        confidence=confidence,
                    ),
                )
                cells.append(
                    TableCell(
                        id=f"{block_id}_cell_r{row:03d}_c{column:03d}",
                        row=row,
                        column=column,
                        row_span=row_span,
                        column_span=column_span,
                        bbox=_to_bbox(page, absolute),
                        page_index=page.page_index,
                        content=content,
                        is_header=row == 0,
                    )
                )
        row_count = len(ys) - 1
        column_count = len(xs) - 1
        body_words = [word for word in page_words if grid_box.contains_center(word.bbox)]
        source_tokens = Counter(
            token.casefold()
            for word in body_words
            for token in re.findall(r"[A-Za-z0-9.]+", word.text)
        )
        cell_tokens = Counter(
            token.casefold()
            for cell in cells
            for token in re.findall(r"[A-Za-z0-9.]+", cell.content.resolved_text or "")
        )
        missing_tokens = source_tokens - cell_tokens
        if sum(missing_tokens.values()) > 0:
            issues.append("table_cell_text_omission")
        _postprocess_table_cells(cells)
        proposal_matches = bool(
            proposal and proposal.rows == row_count and proposal.columns == column_count
        )
        parser_backend = f"opencv-grid+{ocr_page.backend}"
        if proposal:
            parser_backend = f"PP-TableMagic-resolved/{parser_backend}"
        return ParsedTable(
            data=TableData(
                row_count=row_count,
                column_count=column_count,
                cells=cells,
                parser_backend=parser_backend,
                html=self._to_html(row_count, column_count, cells),
            ),
            crop_ref=crop_ref,
            issues=issues,
            operation={
                "operation": "table_structure_resolution",
                "selected": "opencv_grid",
                "pp_tablemagic_proposal": (
                    {"rows": proposal.rows, "columns": proposal.columns, "confidence": proposal.confidence}
                    if proposal else None
                ),
                "proposal_matches_selected_grid": proposal_matches,
                "profile_column_repair": profile_column_repair,
                "missing_source_tokens": list(missing_tokens.elements()),
                "fallback_reason": (
                    bordered_error or proposal_error or self.fallback_reason
                    or (
                        "PP-TableMagic row/column proposal disagreed with the detected ruled grid"
                        if proposal and not proposal_matches else None
                    )
                ),
            },
            ancillary_text=ancillary_text or None,
        )

    def _table_from_recognition(
        self,
        page: RenderedPage,
        region: LayoutRegion,
        ocr_page: OCRPage,
        crop_ref: Path,
        proposal: RecognitionProposal,
    ) -> ParsedTable:
        with Image.open(crop_ref) as crop:
            crop_width, crop_height = crop.size
        cells: list[TableCell] = []
        page_words = _words_in_box(ocr_page.words, region.bbox)
        for row, column, row_span, column_span, local, text, is_header in proposal.cells:
            local = PixelBox(
                max(0, min(crop_width - 1, local.x0)),
                max(0, min(crop_height - 1, local.y0)),
                max(1, min(crop_width, local.x1)),
                max(1, min(crop_height, local.y1)),
            )
            absolute = PixelBox(
                region.bbox.x0 + local.x0,
                region.bbox.y0 + local.y0,
                region.bbox.x0 + local.x1,
                region.bbox.y0 + local.y1,
            )
            aligned_text, aligned_confidence = _text_for_words(
                _words_in_box(page_words, absolute)
            )
            resolved_text = aligned_text or text
            selected_source = "ocr" if aligned_text else "review" if text else "none"
            resolution_reason = (
                "page_ocr_aligned_to_table_cell" if aligned_text
                else "pp_tablemagic_cell_ocr" if text else "empty_cell"
            )
            cells.append(TableCell(
                id=f"{region.id}_pp_tablemagic_cell_r{row:03d}_c{column:03d}",
                row=row,
                column=column,
                row_span=row_span,
                column_span=column_span,
                bbox=_to_bbox(page, absolute),
                page_index=page.page_index,
                content=TextContent(
                    ocr_text=aligned_text or None,
                    review_text=text if text and text != aligned_text else None,
                    resolved_text=resolved_text or None,
                    resolution=Resolution(
                        selected_source=selected_source,
                        reason=resolution_reason,
                        confidence=(
                            aligned_confidence if aligned_text
                            else proposal.confidence if text else 1.0
                        ),
                    ),
                ),
                is_header=is_header,
            ))

        auxiliary_ids = set(region.auxiliary_word_ids)
        source_words = [
            word for word in _words_in_box(ocr_page.words, region.bbox)
            if word.id not in auxiliary_ids
        ]
        source_tokens = Counter(
            token.casefold()
            for word in source_words
            for token in re.findall(r"[A-Za-z0-9.]+", word.text)
        )
        cell_tokens = Counter(
            token.casefold()
            for cell in cells
            for token in re.findall(r"[A-Za-z0-9.]+", cell.content.resolved_text or "")
        )
        missing_tokens = source_tokens - cell_tokens
        issues: list[str] = []
        if proposal.confidence < self.settings.structure_auto_accept_confidence:
            issues.append("low_table_structure_confidence")
        if sum(missing_tokens.values()) > 0:
            issues.append("table_cell_text_omission")
        _postprocess_table_cells(cells)
        return ParsedTable(
            data=TableData(
                row_count=proposal.rows,
                column_count=proposal.columns,
                cells=cells,
                parser_backend="PP-TableMagic/TableRecognitionPipelineV2",
                html=self._to_html(proposal.rows, proposal.columns, cells),
            ),
            crop_ref=crop_ref,
            issues=issues,
            operation={
                "operation": "table_recognition_pipeline",
                "selected": "PP-TableMagic/TableRecognitionPipelineV2",
                "proposal_confidence": proposal.confidence,
                "missing_source_tokens": list(missing_tokens.elements()),
                "geometry_repairs": list(proposal.geometry_repairs),
                "fallback_reason": None,
            },
        )

    def _table_from_proposal(
        self,
        page: RenderedPage,
        region: LayoutRegion,
        ocr_page: OCRPage,
        crop_ref: Path,
        proposal: StructureProposal,
        *,
        selected: str,
        reason: str,
        fallback_reason: str | None,
        header_row: bool = True,
    ) -> ParsedTable:
        route_reason = reason
        cells: list[TableCell] = []
        ambiguous_cell_text = False
        words = _words_in_box(ocr_page.words, region.bbox)
        with Image.open(crop_ref) as crop:
            crop_width, crop_height = crop.size
        for row, column, row_span, column_span, local in proposal.cells:
            local = PixelBox(
                max(0, min(crop_width - 1, local.x0)),
                max(0, min(crop_height - 1, local.y0)),
                max(1, min(crop_width, local.x1)),
                max(1, min(crop_height, local.y1)),
            )
            if local.x1 <= local.x0 or local.y1 <= local.y0:
                continue
            absolute = PixelBox(
                region.bbox.x0 + local.x0, region.bbox.y0 + local.y0,
                region.bbox.x0 + local.x1, region.bbox.y0 + local.y1,
            )
            cell_words = _words_in_box(words, absolute)
            text, confidence = _text_for_words(cell_words)
            initial_text, initial_confidence = text, confidence
            reviewed_text: str | None = None
            reviewed_confidence = 0.0
            if not text or confidence < self.settings.cell_review_confidence:
                with Image.open(crop_ref) as crop:
                    cell_image = crop.crop((local.x0, local.y0, local.x1, local.y1)).convert("RGB")
                reviewed_text, reviewed_confidence = self.ocr_backend.recognize_crop(cell_image)
            normalized = lambda value: re.sub(r"\s+", "", value or "").casefold().replace(",", ".")
            critical_tokens = lambda value: re.findall(
                r"\d+(?:[.,]\d+)?%?|[<>≤≥=]|\b(?:mg|kg|g|ml|l|usd|eur|nok|not|shall|must|may|unless|except)\b|§",
                value or "", flags=re.IGNORECASE,
            )
            status = ResolutionStatus.RESOLVED
            selected_source = "ocr" if initial_text else "none"
            cell_resolution_reason = "table_cell_ocr" if initial_text else "empty_cell"
            resolved_text = initial_text or None
            confidence = initial_confidence
            if reviewed_text:
                if not initial_text:
                    selected_source, cell_resolution_reason = "review", "cell_only_ocr_review"
                    resolved_text, confidence = reviewed_text, reviewed_confidence
                elif normalized(initial_text) == normalized(reviewed_text):
                    selected_source, cell_resolution_reason = "both", "cell_ocr_review_agrees"
                    confidence = max(initial_confidence, reviewed_confidence)
                elif critical_tokens(initial_text) != critical_tokens(reviewed_text):
                    if reviewed_confidence >= self.settings.cell_auto_resolve_confidence:
                        selected_source, cell_resolution_reason = "review", "high_confidence_cell_review"
                        resolved_text, confidence = reviewed_text, reviewed_confidence
                    else:
                        selected_source, cell_resolution_reason = "none", "unresolved_cell_critical_conflict"
                        resolved_text, confidence = None, 0.0
                        status = ResolutionStatus.AMBIGUOUS
                        ambiguous_cell_text = True
                elif reviewed_confidence > initial_confidence:
                    selected_source, cell_resolution_reason = "review", "higher_confidence_cell_review"
                    resolved_text, confidence = reviewed_text, reviewed_confidence
            cells.append(TableCell(
                id=f"{region.id}_{selected.split('+')[0]}_cell_r{row:03d}_c{column:03d}",
                row=row, column=column, row_span=row_span, column_span=column_span,
                bbox=_to_bbox(page, absolute), page_index=page.page_index,
                content=TextContent(
                    ocr_text=initial_text or None, review_text=reviewed_text or None,
                    resolved_text=resolved_text,
                    resolution=Resolution(
                        selected_source=selected_source,
                        reason=cell_resolution_reason,
                        confidence=confidence,
                    ),
                    resolution_status=status,
                    requires_human_review=status == ResolutionStatus.AMBIGUOUS,
                ),
                is_header=header_row and row == 0,
            ))
        data = TableData(
            row_count=proposal.rows, column_count=proposal.columns, cells=cells,
            parser_backend=selected,
            html=self._to_html(proposal.rows, proposal.columns, cells),
        )
        auxiliary_ids = set(region.auxiliary_word_ids)
        source_words = [word for word in words if word.id not in auxiliary_ids]
        source_tokens = Counter(
            token.casefold()
            for word in source_words
            for token in re.findall(r"[A-Za-z0-9.]+", word.text)
        )
        cell_tokens = Counter(
            token.casefold()
            for cell in cells
            for token in re.findall(r"[A-Za-z0-9.]+", cell.content.resolved_text or "")
        )
        missing_tokens = source_tokens - cell_tokens
        issues: list[str] = []
        if proposal.confidence < self.settings.structure_auto_accept_confidence:
            issues.append("low_table_structure_confidence")
        if sum(missing_tokens.values()) > 0:
            issues.append("table_cell_text_omission")
        if ambiguous_cell_text:
            issues.append("table_cell_text_conflict")
        _postprocess_table_cells(cells)
        data.html = self._to_html(proposal.rows, proposal.columns, cells)
        return ParsedTable(
            data=data, crop_ref=crop_ref, issues=issues,
            operation={
                "operation": "table_fallback_route",
                "selected": selected.split("+")[0],
                "reason": route_reason,
                "proposal_confidence": proposal.confidence,
                "missing_source_tokens": list(missing_tokens.elements()),
                "cell_only_ocr_threshold": self.settings.cell_review_confidence,
                "cell_auto_resolve_confidence": self.settings.cell_auto_resolve_confidence,
                "fallback_reason": fallback_reason,
            },
        )

    def _fallback_word_grid(
        self,
        page: RenderedPage,
        region: LayoutRegion,
        ocr_page: OCRPage,
        crop_ref: Path,
        issues: list[str],
        proposal: StructureProposal | None = None,
        proposal_error: str | None = None,
    ) -> ParsedTable:
        if proposal and proposal.cells:
            return self._table_from_proposal(
                page, region, ocr_page, crop_ref, proposal,
                selected=f"PP-TableMagic/SLANet_plus+{ocr_page.backend}",
                reason="complex_or_borderless_table",
                fallback_reason=proposal_error or self.fallback_reason,
            )
        words = _words_in_box(ocr_page.words, region.bbox)
        grouped: dict[tuple[int, int, int], list[OCRWord]] = {}
        for word in words:
            grouped.setdefault((word.block_num, word.paragraph_num, word.line_num), []).append(word)
        rows = sorted(grouped.values(), key=lambda row: min(word.bbox.y0 for word in row))
        column_count = max((len(row) for row in rows), default=1)
        cells: list[TableCell] = []
        for row_index, row_words in enumerate(rows or [[]]):
            ordered = sorted(row_words, key=lambda word: word.bbox.x0)
            for column in range(column_count):
                if column < len(ordered):
                    word = ordered[column]
                    box = word.bbox
                    text = word.text
                    confidence = word.confidence
                else:
                    box = region.bbox
                    text = ""
                    confidence = 0.0
                cells.append(
                    TableCell(
                        id=f"{region.id}_cell_r{row_index:03d}_c{column:03d}",
                        row=row_index,
                        column=column,
                        bbox=_to_bbox(page, box),
                        page_index=page.page_index,
                        content=TextContent(
                            ocr_text=text or None,
                            resolved_text=text or None,
                            resolution=Resolution(
                                selected_source="ocr" if text else "none",
                                reason="word_grid_fallback" if text else "empty_cell",
                                confidence=confidence,
                            ),
                        ),
                        is_header=row_index == 0,
                    )
                )
        row_count = max(1, len(rows))
        return ParsedTable(
            data=TableData(
                row_count=row_count,
                column_count=column_count,
                cells=cells,
                parser_backend=f"{ocr_page.backend}-word-grid-fallback",
                html=self._to_html(row_count, column_count, cells),
            ),
            crop_ref=crop_ref,
            issues=issues,
            operation={
                "operation": "table_structure_resolution",
                "selected": "ocr_word_grid",
                "pp_tablemagic_proposal": (
                    {"rows": proposal.rows, "columns": proposal.columns, "confidence": proposal.confidence}
                    if proposal else None
                ),
                "proposal_matches_selected_grid": False,
                "fallback_reason": proposal_error or self.fallback_reason,
            },
            ancillary_text=None,
        )

    @staticmethod
    def _to_html(row_count: int, column_count: int, cells: list[TableCell]) -> str:
        lookup = {(cell.row, cell.column): cell for cell in cells}
        covered = {
            (row, column)
            for cell in cells
            for row in range(cell.row, cell.row + cell.row_span)
            for column in range(cell.column, cell.column + cell.column_span)
            if (row, column) != (cell.row, cell.column)
        }
        rows: list[str] = []
        for row in range(row_count):
            values: list[str] = []
            for column in range(column_count):
                if (row, column) in covered:
                    continue
                cell = lookup.get((row, column))
                if cell is None:
                    values.append("<td></td>")
                    continue
                tag = "th" if cell.is_header else "td"
                spans = ""
                if cell.row_span > 1:
                    spans += f' rowspan="{cell.row_span}"'
                if cell.column_span > 1:
                    spans += f' colspan="{cell.column_span}"'
                value = html.escape(cell.content.resolved_text or "")
                values.append(f"<{tag}{spans}>{value}</{tag}>")
            rows.append("<tr>" + "".join(values) + "</tr>")
        return "<table>" + "".join(rows) + "</table>"
