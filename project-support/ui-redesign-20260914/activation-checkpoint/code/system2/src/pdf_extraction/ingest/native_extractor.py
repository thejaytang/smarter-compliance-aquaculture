from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from pypdf import PdfReader

from ..types import NativeObject, NativePage


@dataclass
class NativeExtractionResult:
    pages: list[NativePage]
    backend: str
    version: str | None
    fallback_reason: str | None = None


class NativeExtractor:
    """Extract programmatic PDF objects, preferring docling-parse."""

    def __init__(self, backend: str = "auto") -> None:
        self.backend = backend

    def extract(self, pdf_path: str | Path) -> NativeExtractionResult:
        if self.backend in {"auto", "docling-parse"}:
            try:
                return self._extract_docling(Path(pdf_path))
            except Exception as exc:
                if self.backend == "docling-parse":
                    raise
                docling_reason = f"docling-parse unavailable: {exc}"
                try:
                    return self._extract_pdfium_positioned(
                        Path(pdf_path), docling_reason
                    )
                except Exception as pdfium_exc:
                    return self._extract_pypdf_positioned(
                        Path(pdf_path),
                        f"{docling_reason}; pypdfium2 unavailable: {pdfium_exc}",
                    )
        if self.backend == "pdfium":
            return self._extract_pdfium_positioned(Path(pdf_path), None)
        return self._extract_pypdf_positioned(Path(pdf_path), None)

    def _extract_docling(self, path: Path) -> NativeExtractionResult:
        from importlib.metadata import version

        from docling_parse.pdf_parser import DoclingPdfParser

        document = DoclingPdfParser(loglevel="fatal").load(path)
        pages: list[NativePage] = []
        try:
            for page_index in range(document.number_of_pages()):
                page = document.get_page(page_index + 1)
                width = float(page.dimension.crop_bbox.r - page.dimension.crop_bbox.l)
                height = float(page.dimension.crop_bbox.t - page.dimension.crop_bbox.b)
                def convert_cells(cells: list, object_type: str) -> list[NativeObject]:
                    converted: list[NativeObject] = []
                    for position, cell in enumerate(cells):
                        rect = cell.rect.to_top_left_origin(height).to_bounding_box()
                        x0, x1 = sorted((float(rect.l), float(rect.r)))
                        y0, y1 = sorted((float(rect.t), float(rect.b)))
                        converted.append(
                            NativeObject(
                                id=f"native_p{page_index:04d}_{object_type[0]}{position:06d}",
                                text=cell.text,
                                bbox_points=(x0, y0, x1, y1),
                                confidence=float(cell.confidence),
                                object_type=object_type,
                                font_name=getattr(cell, "font_name", None),
                                font_key=getattr(cell, "font_key", None),
                                from_ocr=getattr(cell, "from_ocr", None),
                            )
                        )
                    return converted

                words = convert_cells(page.word_cells, "word")
                characters = convert_cells(page.char_cells, "character")
                text_lines = convert_cells(page.textline_cells, "text_line")
                bitmap_resources: list[dict[str, object]] = []
                bitmap_boxes: list[tuple[float, float, float, float]] = []
                for bitmap in page.bitmap_resources:
                    if bitmap is None:
                        bitmap_resources.append({"type": "bitmap_resource", "detail": "unavailable"})
                        continue
                    converted = bitmap.to_top_left_origin(height)
                    if converted is None:
                        bitmap_resources.append(
                            bitmap.model_dump(mode="json")
                            if hasattr(bitmap, "model_dump") else {"type": "bitmap_resource"}
                        )
                        continue
                    rect_value = getattr(converted, "rect", None)
                    if rect_value is not None:
                        rect = rect_value.to_bounding_box()
                        x0, x1 = sorted((float(rect.l), float(rect.r)))
                        y0, y1 = sorted((float(rect.t), float(rect.b)))
                        bitmap_boxes.append((x0, y0, x1, y1))
                    bitmap_resources.append(
                        converted.model_dump(mode="json")
                        if hasattr(converted, "model_dump") else {"type": "bitmap_resource"}
                    )
                shapes: list[dict[str, object]] = []
                for shape in page.shapes:
                    if shape is None:
                        continue
                    converted_shape = shape.to_top_left_origin(height)
                    if converted_shape is not None and hasattr(converted_shape, "model_dump"):
                        shapes.append(converted_shape.model_dump(mode="json"))
                pages.append(
                    NativePage(
                        page_index=page_index,
                        width_points=width,
                        height_points=height,
                        words=words,
                        bitmap_boxes_points=bitmap_boxes,
                        characters=characters,
                        text_lines=text_lines,
                        shapes=shapes,
                        bitmap_resources=bitmap_resources,
                    )
                )
        finally:
            document.unload()
        return NativeExtractionResult(
            pages=pages,
            backend="docling-parse",
            version=version("docling-parse"),
        )

    def _extract_pypdf_positioned(
        self, path: Path, reason: str | None
    ) -> NativeExtractionResult:
        """Recover line-level native geometry before using the flat fallback.

        ``pypdf`` exposes the text and current transformation matrices through
        ``visitor_text``.  The fragments are not as fine-grained as Docling's
        word cells, but they preserve the row and semantic-column coordinates
        needed by Requirement template profiling.  A dependency failure must
        therefore not collapse a structured page into one full-page object.
        """
        from importlib.metadata import version

        reader = PdfReader(path)
        pages: list[NativePage] = []
        positioned_page_count = 0
        for page_index, page in enumerate(reader.pages):
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            positioned: list[tuple[str, tuple[float, float, float, float], str | None]] = []

            def visitor_text(
                text: str,
                current_matrix: list[float],
                text_matrix: list[float],
                font: dict | None,
                font_size: float,
            ) -> None:
                normalized = re.sub(r"\s+", " ", text).strip()
                if not normalized:
                    return
                matrix = _multiply_pdf_matrices(text_matrix, current_matrix)
                x = float(matrix[4])
                baseline_y = float(matrix[5])
                # Some malformed content streams return a synthetic (0, 0)
                # fragment.  Keeping it would invent geometry, so retain that
                # text only in the page-level fallback evidence when necessary.
                if x == 0.0 and baseline_y == 0.0:
                    return
                size = max(abs(float(font_size)), 1.0)
                x0 = min(max(x, 0.0), width)
                y0 = min(max(height - baseline_y - 0.75 * size, 0.0), height)
                x1 = min(width, x0 + max(size * 0.45 * len(normalized), size * 0.8))
                y1 = min(height, y0 + size)
                if x1 <= x0 or y1 <= y0:
                    return
                font_name = None
                if font is not None:
                    raw_name = font.get("/BaseFont")
                    if raw_name is not None:
                        font_name = str(raw_name)
                positioned.append((normalized, (x0, y0, x1, y1), font_name))

            try:
                text = page.extract_text(visitor_text=visitor_text) or ""
            except Exception:
                text = page.extract_text() or ""
                positioned = []

            if positioned:
                positioned_page_count += 1
                words = [
                    NativeObject(
                        id=f"native_p{page_index:04d}_pw{position:06d}",
                        text=text,
                        bbox_points=bbox,
                        confidence=0.8,
                        object_type="word",
                        font_name=font_name,
                    )
                    for position, (text, bbox, font_name) in enumerate(positioned)
                ]
                text_lines = [
                    NativeObject(
                        id=f"native_p{page_index:04d}_pt{position:06d}",
                        text=text,
                        bbox_points=bbox,
                        confidence=0.8,
                        object_type="text_line",
                        font_name=font_name,
                    )
                    for position, (text, bbox, font_name) in enumerate(positioned)
                ]
                page_backend = "pypdf-positioned"
            else:
                words = [
                    NativeObject(
                        id=f"native_p{page_index:04d}_fallback_000000",
                        text=text,
                        bbox_points=(0.0, 0.0, width, height),
                        confidence=0.5,
                        object_type="page_text_fallback",
                    )
                ] if text.strip() else []
                text_lines = []
                page_backend = "pypdf"
            bitmap_resources: list[dict[str, object]] = []
            try:
                bitmap_resources = [
                    {
                        "name": getattr(image, "name", f"image_{index}"),
                        "source": "pypdf_page_images",
                    }
                    for index, image in enumerate(page.images)
                ]
            except Exception:
                # Image enumeration is evidence enrichment; text extraction must
                # remain available even for malformed image XObjects.
                bitmap_resources = []
            pages.append(
                NativePage(
                    page_index=page_index,
                    width_points=width,
                    height_points=height,
                    words=words,
                    bitmap_boxes_points=[(0.0, 0.0, width, height)] * len(bitmap_resources),
                    text_lines=text_lines,
                    bitmap_resources=bitmap_resources,
                    backend=page_backend,
                    fallback_reason=reason,
                )
            )
        backend = (
            "pypdf-positioned"
            if positioned_page_count == len(pages)
            else "pypdf-positioned-mixed"
            if positioned_page_count
            else "pypdf"
        )
        return NativeExtractionResult(
            pages=pages,
            backend=backend,
            version=version("pypdf"),
            fallback_reason=reason,
        )

    def _extract_pdfium_positioned(
        self, path: Path, reason: str | None
    ) -> NativeExtractionResult:
        """Extract source-faithful text lines from PDFium character boxes.

        PDFium is already the project's renderer dependency and supplies real
        per-character PDF coordinates without external font-metric files.  It
        is therefore the first geometry-bearing fallback when Docling cannot
        initialize.  Lines, rather than guessed words, are sufficient for the
        Requirement assembler because IDs, labels and action markers retain
        their true x bands and reading order.
        """
        from importlib.metadata import version

        import pypdfium2 as pdfium

        document = pdfium.PdfDocument(path)
        pages: list[NativePage] = []
        try:
            for page_index in range(len(document)):
                page = document[page_index]
                width, height = (float(value) for value in page.get_size())
                text_page = page.get_textpage()
                line_payloads: list[
                    tuple[str, tuple[float, float, float, float]]
                ] = []
                current_chars: list[str] = []
                current_boxes: list[tuple[float, float, float, float]] = []

                def flush_line() -> None:
                    raw_text = "".join(current_chars)
                    text = re.sub(r"[ \t]+", " ", raw_text).strip()
                    if text and current_boxes:
                        left = min(box[0] for box in current_boxes)
                        bottom = min(box[1] for box in current_boxes)
                        right = max(box[2] for box in current_boxes)
                        top = max(box[3] for box in current_boxes)
                        bbox = (
                            max(0.0, min(left, width)),
                            max(0.0, min(height - top, height)),
                            max(0.0, min(right, width)),
                            max(0.0, min(height - bottom, height)),
                        )
                        if bbox[2] > bbox[0] and bbox[3] > bbox[1]:
                            line_payloads.append((text, bbox))
                    current_chars.clear()
                    current_boxes.clear()

                try:
                    for char_index in range(text_page.count_chars()):
                        character = text_page.get_text_range(char_index, 1)
                        if "\r" in character or "\n" in character:
                            flush_line()
                            continue
                        try:
                            char_box = tuple(
                                float(value) for value in text_page.get_charbox(char_index)
                            )
                        except Exception:
                            # Missing geometry for one glyph must not discard the
                            # remaining source-backed line.
                            current_chars.append(character)
                            continue
                        if current_boxes:
                            prior_box = current_boxes[-1]
                            # Glyph descenders can move an individual character
                            # box by roughly 2–3 points within the same line.
                            vertical_shift = abs(char_box[1] - prior_box[1]) > 6.0
                            horizontal_reset = char_box[0] + 1.0 < prior_box[0]
                            column_gap = char_box[0] - prior_box[2] > 8.0
                            if vertical_shift or horizontal_reset or column_gap:
                                flush_line()
                        current_chars.append(character)
                        current_boxes.append(char_box)
                    flush_line()
                finally:
                    text_page.close()
                    page.close()

                words = [
                    NativeObject(
                        id=f"native_p{page_index:04d}_fw{position:06d}",
                        text=text,
                        bbox_points=bbox,
                        confidence=0.95,
                        object_type="word",
                    )
                    for position, (text, bbox) in enumerate(line_payloads)
                ]
                text_lines = [
                    NativeObject(
                        id=f"native_p{page_index:04d}_ft{position:06d}",
                        text=text,
                        bbox_points=bbox,
                        confidence=0.95,
                        object_type="text_line",
                    )
                    for position, (text, bbox) in enumerate(line_payloads)
                ]
                pages.append(
                    NativePage(
                        page_index=page_index,
                        width_points=width,
                        height_points=height,
                        words=words,
                        text_lines=text_lines,
                        backend="pypdfium2",
                        fallback_reason=reason,
                    )
                )
        finally:
            document.close()
        return NativeExtractionResult(
            pages=pages,
            backend="pypdfium2",
            version=version("pypdfium2"),
            fallback_reason=reason,
        )

    def _extract_pypdf(self, path: Path, reason: str | None) -> NativeExtractionResult:
        """Compatibility alias for the geometry-bearing pypdf fallback."""

        return self._extract_pypdf_positioned(path, reason)


def _multiply_pdf_matrices(
    left: list[float], right: list[float]
) -> tuple[float, float, float, float, float, float]:
    """Multiply two PDF affine matrices without importing pypdf internals."""

    return (
        left[0] * right[0] + left[1] * right[2],
        left[0] * right[1] + left[1] * right[3],
        left[2] * right[0] + left[3] * right[2],
        left[2] * right[1] + left[3] * right[3],
        left[4] * right[0] + left[5] * right[2] + right[4],
        left[4] * right[1] + left[5] * right[3] + right[5],
    )
