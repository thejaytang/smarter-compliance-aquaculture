from __future__ import annotations

from pathlib import Path

from PIL import Image

import re

from ..models import DerivedContent, FigureData
from ..types import LayoutRegion, RenderedPage
from ..ingest.renderer import PDFRenderer


def parse_figure(
    page: RenderedPage,
    region: LayoutRegion,
    figure_dir: str | Path,
    block_id: str,
) -> FigureData:
    target = Path(figure_dir) / f"{block_id}.png"
    PDFRenderer.crop(page, region.bbox, target)
    with Image.open(target) as image:
        width, height = image.size
    return FigureData(image_ref=str(target), width_px=width, height_px=height)


def derive_visual_understanding(
    figure: FigureData, embedded_text: str | None
) -> DerivedContent:
    text = embedded_text or ""
    entities = [
        {"text": match.group(0), "type": "numeric_or_unit", "confidence": 0.9}
        for match in re.finditer(r"\b\d+(?:[.,]\d+)?\s*(?:%|mg|kg|g|ml|l)?\b", text, re.I)
    ]
    orientation = "landscape" if figure.width_px >= figure.height_px else "portrait"
    description = (
        f"{orientation.capitalize()} figure with embedded text: {text}"
        if text else f"{orientation.capitalize()} figure without reliably detected embedded text"
    )
    return DerivedContent(
        embedded_text=embedded_text,
        visual_description=description,
        entities=entities,
        relations=[],
        backend="local-visual-evidence-summary",
        model_version="1.0",
        confidence=0.85 if text else 0.55,
    )
