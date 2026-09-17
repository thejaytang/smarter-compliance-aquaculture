from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageStat
from pypdf import PdfReader

from ..config import SecuritySettings
from ..models import Page, SourceMetadata
from ..types import NativePage, RenderedPage


@dataclass
class PreflightResult:
    source: SourceMetadata
    pages: list[Page]
    warnings: list[str]


class UnsafePDFError(ValueError):
    """Raised when an input violates an enforced local processing policy."""


@dataclass(frozen=True)
class SecurityInspection:
    page_count: int
    has_javascript: bool
    embedded_file_count: int
    external_link_count: int
    warnings: list[str]


def inspect_pdf_security(pdf_path: str | Path, settings: SecuritySettings) -> SecurityInspection:
    path = Path(pdf_path)
    if path.stat().st_size > settings.max_file_size_mb * 1024 * 1024:
        raise UnsafePDFError("PDF exceeds configured file-size limit")
    try:
        reader = PdfReader(path, strict=False)
    except Exception as exc:
        raise UnsafePDFError(f"malformed PDF: {type(exc).__name__}") from exc
    if reader.is_encrypted:
        raise UnsafePDFError("encrypted PDF requires an explicit decryption workflow")
    if len(reader.pages) > settings.max_pages:
        raise UnsafePDFError("PDF exceeds configured page-count limit")
    for page in reader.pages:
        if (
            float(page.mediabox.width) > settings.max_page_dimension_points
            or float(page.mediabox.height) > settings.max_page_dimension_points
        ):
            raise UnsafePDFError("PDF page exceeds configured dimension limit")
    root = reader.trailer.get("/Root", {})
    root = root.get_object() if hasattr(root, "get_object") else root
    names = root.get("/Names", {}) if hasattr(root, "get") else {}
    names = names.get_object() if hasattr(names, "get_object") else names
    open_action = root.get("/OpenAction", {}) if hasattr(root, "get") else {}
    open_action = open_action.get_object() if hasattr(open_action, "get_object") else open_action
    has_javascript = bool(names.get("/JavaScript")) if hasattr(names, "get") else False
    has_javascript = has_javascript or (
        hasattr(open_action, "get") and str(open_action.get("/S")) == "/JavaScript"
    )
    embedded = names.get("/EmbeddedFiles") if hasattr(names, "get") else None
    embedded_count = 0
    if embedded:
        try:
            embedded_count = len(embedded.get_object().get("/Names", [])) // 2
        except Exception:
            embedded_count = 1
    external_links = 0
    for page in reader.pages:
        additional_actions = page.get("/AA", {})
        additional_actions = additional_actions.get_object() if hasattr(additional_actions, "get_object") else additional_actions
        if additional_actions:
            has_javascript = has_javascript or "JavaScript" in str(additional_actions)
        for annotation in page.get("/Annots", []) or []:
            try:
                action = annotation.get_object().get("/A", {})
                if action.get("/URI"):
                    external_links += 1
            except Exception:
                continue
    if has_javascript and settings.reject_javascript:
        raise UnsafePDFError("PDF JavaScript is prohibited by policy")
    if embedded_count and settings.reject_embedded_files:
        raise UnsafePDFError("embedded files are prohibited by policy")
    warnings = [f"external_links_present:{external_links}"] if external_links else []
    return SecurityInspection(
        page_count=len(reader.pages),
        has_javascript=has_javascript,
        embedded_file_count=embedded_count,
        external_link_count=external_links,
        warnings=warnings,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _blank_score(image_path: Path) -> float:
    with Image.open(image_path) as image:
        gray = image.convert("L").resize((128, 128))
        stat = ImageStat.Stat(gray)
        return float(stat.mean[0]) / 255.0


def run_preflight(
    pdf_path: str | Path,
    rendered_pages: list[RenderedPage],
    native_pages: list[NativePage],
    security: SecurityInspection | None = None,
    expected_page_indices: set[int] | None = None,
) -> PreflightResult:
    path = Path(pdf_path)
    reader = PdfReader(path)
    try:
        labels = list(reader.page_labels)
    except Exception:
        labels = []
    inspection = security or SecurityInspection(
        page_count=len(reader.pages), has_javascript=False,
        embedded_file_count=0, external_link_count=0, warnings=[],
    )
    source = SourceMetadata(
        file_name=path.name,
        file_hash=_sha256(path),
        file_size=path.stat().st_size,
        pdf_version=getattr(reader, "pdf_header", None),
        page_count=len(reader.pages),
        encrypted=bool(reader.is_encrypted),
        has_javascript=inspection.has_javascript,
        embedded_file_count=inspection.embedded_file_count,
        external_link_count=inspection.external_link_count,
        security_warnings=inspection.warnings,
    )
    warnings: list[str] = []
    pages: list[Page] = []
    for rendered, native in zip(rendered_pages, native_pages, strict=True):
        page_area = rendered.width_points * rendered.height_points
        native_area = sum(
            max(0.0, x1 - x0) * max(0.0, y1 - y0)
            for x0, y0, x1, y1 in (word.bbox_points for word in native.words)
        )
        bitmap_area = sum(
            max(0.0, x1 - x0) * max(0.0, y1 - y0)
            for x0, y0, x1, y1 in native.bitmap_boxes_points
        )
        native_coverage = min(1.0, native_area / page_area) if page_area else 0.0
        image_coverage = min(1.0, bitmap_area / page_area) if page_area else 0.0
        blank_score = _blank_score(rendered.image_path)
        if blank_score > 0.995 and not native.words:
            kind = "blank"
        elif native_coverage > 0.01 and image_coverage > 0.2:
            kind = "mixed"
        elif native_coverage > 0.01:
            kind = "born_digital"
        else:
            kind = "scanned"
        bottom_words = [
            word.text.strip() for word in native.words
            if word.text.strip() and word.bbox_points[1] >= rendered.height_points * 0.88
        ]
        printed_candidates = [
            value for value in bottom_words
            if re.fullmatch(r"(?:\d+|[ivxlcdm]+)", value, flags=re.I)
        ]
        pdf_label = labels[rendered.page_index] if rendered.page_index < len(labels) else None
        printed_label = printed_candidates[-1] if printed_candidates else None
        pages.append(
            Page(
                page_index=rendered.page_index,
                width=rendered.width_points,
                height=rendered.height_points,
                rotation=rendered.rotation,
                image_ref=str(rendered.image_path),
                native_text_coverage=native_coverage,
                image_coverage=image_coverage,
                page_kind=kind,
                pdf_page_label=pdf_label,
                printed_page_label=printed_label,
                page_label_confidence=(0.98 if pdf_label else 0.8 if printed_label else None),
                page_label_source=("pdf" if pdf_label else "printed" if printed_label else "none"),
            )
        )
    if expected_page_indices is None:
        if len(rendered_pages) != source.page_count:
            warnings.append("rendered page count does not match input page count")
        if len(native_pages) != source.page_count:
            warnings.append("native extraction page count does not match input page count")
    else:
        rendered_indices = {page.page_index for page in rendered_pages}
        native_indices = {page.page_index for page in native_pages}
        if rendered_indices != expected_page_indices:
            warnings.append("rendered pages do not match requested page selection")
        if native_indices != expected_page_indices:
            warnings.append("native pages do not match requested page selection")
        one_based = sorted(index + 1 for index in expected_page_indices)
        warnings.append(f"partial_page_selection:{one_based[0]}-{one_based[-1]}")
    warnings.extend(inspection.warnings)
    return PreflightResult(source=source, pages=pages, warnings=warnings)
