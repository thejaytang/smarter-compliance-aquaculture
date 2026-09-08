"""Source-evidence acquisition boundary."""

from ..ingest import (
    NativeExtractionResult,
    NativeExtractor,
    PDFRenderer,
    SecondaryNativeResult,
    extract_secondary_native,
    parse_pdftotext_bbox_xml,
)
from ..types import NativeObject, NativePage, OCRPage, OCRWord, RenderedPage

__all__ = [
    "NativeExtractionResult",
    "NativeExtractor",
    "NativeObject",
    "NativePage",
    "OCRPage",
    "OCRWord",
    "PDFRenderer",
    "RenderedPage",
    "SecondaryNativeResult",
    "extract_secondary_native",
    "parse_pdftotext_bbox_xml",
]
