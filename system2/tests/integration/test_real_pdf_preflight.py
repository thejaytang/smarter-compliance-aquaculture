from __future__ import annotations

from pathlib import Path

import pytest

from pdf_extraction.ingest import NativeExtractor, PDFRenderer, run_preflight
from tests.support.paths import PROJECT_ROOT


def test_supplied_pdf_is_fully_preflighted(tmp_path: Path) -> None:
    source = PROJECT_ROOT / "_PS3_副本.pdf"
    if not source.is_file():
        pytest.skip("user-supplied _PS3_副本.pdf is not present in the project root")
    rendered = PDFRenderer(100).render(source, tmp_path / "pages")
    native = NativeExtractor("auto").extract(source)
    result = run_preflight(source, rendered, native.pages)
    assert result.source.page_count == 3
    assert len(result.pages) == 3
    assert all(page.page_kind == "scanned" for page in result.pages)
    assert all(Path(page.image_ref).is_file() for page in result.pages)
