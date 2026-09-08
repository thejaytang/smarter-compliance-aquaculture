"""Stable evidence contracts shared by acquisition, extraction, and verification."""

from ..models import EvidenceSpan
from ..types import (
    LayoutRegion,
    NativeObject,
    NativePage,
    OCRPage,
    OCRWord,
    PixelBox,
    RenderedPage,
)

__all__ = [
    "EvidenceSpan",
    "LayoutRegion",
    "NativeObject",
    "NativePage",
    "OCRPage",
    "OCRWord",
    "PixelBox",
    "RenderedPage",
]
