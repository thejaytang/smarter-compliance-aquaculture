from __future__ import annotations

from reportlab.pdfgen import canvas
import pytest

from pdf_extraction.ingest.native_extractor import NativeExtractor


def _write_positioned_pdf(path) -> None:
    pdf = canvas.Canvas(str(path), pagesize=(612, 792))
    pdf.drawString(60, 665, "5.1.6")
    pdf.drawString(80, 645, "Indicator: Maximum unexplained mortality rate")
    pdf.drawString(80, 625, "Requirement: <= 40% of total mortalities")
    pdf.drawString(80, 605, "Applicability: All farms")
    pdf.drawString(194, 585, "a. Maintain supporting records.")
    pdf.drawString(376, 580, "A. Review supporting records.")
    pdf.save()


def test_pdfium_fallback_preserves_all_line_geometry(tmp_path) -> None:
    source = tmp_path / "positioned.pdf"
    _write_positioned_pdf(source)

    result = NativeExtractor("pdfium").extract(source)

    assert result.backend == "pypdfium2"
    assert len(result.pages) == 1
    page = result.pages[0]
    assert len(page.words) >= 6
    assert len(page.text_lines) == len(page.words)
    by_text = {item.text: item for item in page.words}
    assert by_text["5.1.6"].bbox_points[0] == pytest.approx(60, abs=1)
    assert by_text["Indicator: Maximum unexplained mortality rate"].bbox_points[0] == pytest.approx(80, abs=2)
    assert by_text["a. Maintain supporting records."].bbox_points[0] == pytest.approx(194, abs=2)
    assert by_text["A. Review supporting records."].bbox_points[0] == pytest.approx(376, abs=2)
    assert all(item.object_type != "page_text_fallback" for item in page.words)


def test_pypdf_last_resort_keeps_available_line_geometry(tmp_path) -> None:
    source = tmp_path / "positioned.pdf"
    _write_positioned_pdf(source)

    result = NativeExtractor("pypdf").extract(source)

    assert result.backend == "pypdf-positioned"
    by_text = {item.text: item for item in result.pages[0].words}
    assert by_text["5.1.6"].bbox_points[0] == 60
    assert by_text["Requirement: <= 40% of total mortalities"].bbox_points[0] == 80
    assert by_text["Applicability: All farms"].bbox_points[0] == 80
    assert all(
        item.object_type != "page_text_fallback" for item in result.pages[0].words
    )
