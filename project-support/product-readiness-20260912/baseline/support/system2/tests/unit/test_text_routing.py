from pathlib import Path

from pdf_extraction.config import TextRoutingSettings
from pdf_extraction.routing import assess_text_layer, native_analysis_page
from pdf_extraction.types import NativeObject, NativePage, RenderedPage


def _native_page(words: list[NativeObject], *, bitmaps: list[dict] | None = None) -> NativePage:
    return NativePage(
        page_index=2,
        width_points=100,
        height_points=100,
        words=words,
        text_lines=[NativeObject(
            id="line", text="This is a sufficiently complete native text layer.",
            bbox_points=(10, 10, 90, 20), object_type="text_line",
        )],
        bitmap_resources=bitmaps or [],
    )


def test_routes_usable_native_text_without_ocr() -> None:
    words = [
        NativeObject(
            id=f"word-{index}", text=text,
            bbox_points=(10 + index * 8, 10, 17 + index * 8, 20),
        )
        for index, text in enumerate(
            ["This", "is", "a", "sufficiently", "complete", "native", "text", "layer"]
        )
    ]
    decision = assess_text_layer(_native_page(words), TextRoutingSettings())
    assert decision.route == "native"
    assert decision.confidence == 0.99


def test_routes_empty_text_layer_to_ocr() -> None:
    decision = assess_text_layer(_native_page([]), TextRoutingSettings())
    assert decision.route == "ocr"


def test_native_analysis_page_preserves_native_provenance(tmp_path: Path) -> None:
    words = [
        NativeObject(
            id=f"word-{index}", text=text,
            bbox_points=(10 + index * 8, 10, 17 + index * 8, 20),
        )
        for index, text in enumerate(
            ["This", "is", "a", "sufficiently", "complete", "native", "text", "layer"]
        )
    ]
    page = _native_page(words)
    decision = assess_text_layer(page, TextRoutingSettings())
    rendered = RenderedPage(2, tmp_path / "page.png", 100, 100, 200, 200, 0)
    analysis = native_analysis_page(page, rendered, tmp_path, decision)
    assert analysis.backend == "native-text-layer"
    assert analysis.words[0].bbox.x0 == 20
    assert analysis.words[0].paragraph_num == analysis.words[0].line_num
    assert analysis.raw_ref and analysis.raw_ref.name == "analysis-text-page-0003.json"


def test_native_analysis_merges_adjacent_same_baseline_fragments(tmp_path: Path) -> None:
    words = [
        NativeObject("criterion", "Criterion", (10, 10, 45, 20)),
        NativeObject("number", "1.1", (47, 10, 60, 20)),
        NativeObject("dash", "-", (62, 10, 65, 20)),
        NativeObject("label", "Legal Compliance", (67, 10, 95, 20)),
    ]
    page = NativePage(
        page_index=0, width_points=100, height_points=100, words=words,
        text_lines=[
            NativeObject("l1", "Criterion 1.1", (10, 10, 60, 20), object_type="text_line"),
            NativeObject("l2", "-", (62, 10, 65, 20), object_type="text_line"),
            NativeObject("l3", "Legal Compliance", (67, 10, 95, 20), object_type="text_line"),
        ],
    )
    rendered = RenderedPage(0, tmp_path / "page.png", 100, 100, 200, 200, 0)
    decision = assess_text_layer(page, TextRoutingSettings(
        min_word_count=1, min_character_count=1
    ))
    analysis = native_analysis_page(page, rendered, tmp_path, decision)
    assert len({word.line_num for word in analysis.words}) == 1
