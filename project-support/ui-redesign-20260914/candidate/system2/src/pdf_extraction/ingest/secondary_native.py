from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

from ..types import NativeObject, NativePage


@dataclass(frozen=True)
class SecondaryNativeResult:
    pages: list[NativePage]
    backend: str = "pdftotext"
    version: str | None = None
    fallback_reason: str | None = None


def parse_pdftotext_bbox_xml(
    xml_text: str, *, first_page_index: int = 0,
) -> list[NativePage]:
    """Parse Poppler ``pdftotext -bbox-layout`` output.

    Poppler coordinates are PDF points with a top-left origin, matching the
    canonical segment coordinate system used by this project.
    """
    root = ET.fromstring(xml_text)
    pages: list[NativePage] = []
    page_nodes = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "page"]
    for offset, page_node in enumerate(page_nodes):
        page_index = first_page_index + offset
        words: list[NativeObject] = []
        for word_index, node in enumerate(page_node.iter()):
            if node.tag.rsplit("}", 1)[-1] != "word":
                continue
            text = "".join(node.itertext()).strip()
            if not text:
                continue
            try:
                bbox = tuple(float(node.attrib[key]) for key in ("xMin", "yMin", "xMax", "yMax"))
            except (KeyError, ValueError):
                continue
            words.append(NativeObject(
                id=f"secondary_p{page_index:04d}_w{word_index:06d}",
                text=text,
                bbox_points=bbox,
                confidence=1.0,
                object_type="word",
            ))
        pages.append(NativePage(
            page_index=page_index,
            width_points=float(page_node.attrib.get("width", 1.0)),
            height_points=float(page_node.attrib.get("height", 1.0)),
            words=words,
            backend="pdftotext",
        ))
    return pages


def extract_secondary_native(
    pdf_path: str | Path, page_indices: set[int], *, timeout_seconds: int = 300,
) -> SecondaryNativeResult:
    executable = shutil.which("pdftotext")
    if not executable:
        return SecondaryNativeResult(pages=[], fallback_reason="pdftotext_not_installed")
    if not page_indices:
        return SecondaryNativeResult(pages=[])
    first = min(page_indices)
    last = max(page_indices)
    try:
        completed = subprocess.run(
            [
                executable, "-f", str(first + 1), "-l", str(last + 1),
                "-bbox-layout", str(Path(pdf_path)), "-",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        pages = [
            page for page in parse_pdftotext_bbox_xml(
                completed.stdout, first_page_index=first
            )
            if page.page_index in page_indices
        ]
        version_output = subprocess.run(
            [executable, "-v"], capture_output=True, text=True, timeout=10
        )
        version_line = (version_output.stderr or version_output.stdout).splitlines()
        return SecondaryNativeResult(
            pages=pages,
            version=version_line[0].strip() if version_line else None,
        )
    except (OSError, subprocess.SubprocessError, ET.ParseError) as exc:
        return SecondaryNativeResult(
            pages=[], fallback_reason=f"{type(exc).__name__}:{exc}"
        )
