from __future__ import annotations

from pdf_extraction.cli import parse_page_selection
from pdf_extraction.models import (
    Block,
    BlockType,
    BoundingBox,
    Page,
    Resolution,
    Segment,
    TextContent,
    TableCell,
    TableData,
)
from pdf_extraction.profiling import (
    apply_profile_repairs,
    learn_document_profile,
    validate_profile_consistency,
)
from pdf_extraction.types import (
    LayoutRegion,
    NativeObject,
    NativePage,
    OCRPage,
    OCRWord,
    PixelBox,
    RenderedPage,
)


def _native_page(index: int, number: str) -> NativePage:
    lines = [
        NativeObject(f"i{index}", "Indicator:", (54, 120, 107, 135), object_type="text_line"),
        NativeObject(f"r{index}", "Requirement:", (118, 120, 193, 135), object_type="text_line"),
        NativeObject(f"n{index}", number, (54, 160, 84, 180), object_type="text_line"),
        NativeObject(
            f"b{index}", "The UoC shall maintain the required evidence.",
            (118, 160, 520, 180), object_type="text_line",
        ),
        NativeObject(
            f"h{index}", "How do I interpret this requirement?",
            (54, 220, 300, 235), object_type="text_line",
        ),
    ]
    words = [
        NativeObject(f"w{index}_{position}", line.text, line.bbox_points)
        for position, line in enumerate(lines)
    ]
    return NativePage(
        page_index=index, width_points=600, height_points=800,
        words=words, text_lines=lines,
    )


def _page(index: int) -> Page:
    return Page(
        page_index=index, width=600, height=800, rotation=0,
        image_ref=f"page-{index}.png", native_text_coverage=0.1,
        image_coverage=0, page_kind="born_digital",
    )


def _content(value: str) -> TextContent:
    return TextContent(
        native_text=value, resolved_text=value,
        resolution=Resolution(selected_source="native", reason="test", confidence=1),
    )


def test_page_selection_is_one_based_at_cli_boundary() -> None:
    assert parse_page_selection("6-8,10") == {5, 6, 7, 9}


def test_full_document_profile_learns_repeated_requirement_geometry() -> None:
    profile = learn_document_profile([
        _native_page(index, f"1.2.{index + 1}") for index in range(5)
    ])
    assert profile.requirement_template is not None
    assert profile.requirement_template.support_count == 5
    assert len(profile.requirement_candidates) == 5
    assert profile.numbering.observed == ["1.2.1", "1.2.2", "1.2.3", "1.2.4", "1.2.5"]


def test_short_requirement_text_is_not_rejected_by_right_edge() -> None:
    pages = [_native_page(index, f"1.2.{index + 1}") for index in range(4)]
    short = pages[0]
    short.text_lines[3] = NativeObject(
        "b0", "The UoC shall comply.", (118, 160, 300, 180), object_type="text_line"
    )
    profile = learn_document_profile(pages)
    candidate = next(
        item for item in profile.requirement_candidates if item.requirement_number == "1.2.1"
    )
    assert candidate.bbox_points[2] > 500


def test_profile_learns_multiple_requirement_tables_on_same_page() -> None:
    page = _native_page(0, "1.4.6")
    page.text_lines.extend([
        NativeObject("i2", "Indicator:", (54, 320, 107, 335), object_type="text_line"),
        NativeObject("r2", "Requirement:", (118, 320, 193, 335), object_type="text_line"),
        NativeObject("n2", "1.4.7", (54, 360, 84, 380), object_type="text_line"),
        NativeObject(
            "b2", "The UoC shall report the required data.",
            (118, 360, 510, 380), object_type="text_line",
        ),
    ])
    profile = learn_document_profile([
        page,
        _native_page(1, "1.4.8"),
        _native_page(2, "1.4.9"),
    ])
    assert [
        item.requirement_number for item in profile.requirement_candidates
        if item.page_index == 0
    ] == ["1.4.6", "1.4.7"]


def test_profile_promotes_fragmented_requirement_regions_to_table(tmp_path) -> None:
    native = _native_page(0, "1.2.1")
    profile = learn_document_profile([
        _native_page(index, f"1.2.{index + 1}") for index in range(3)
    ])
    image_path = tmp_path / "page.png"
    from PIL import Image

    Image.new("RGB", (600, 800), "white").save(image_path)
    rendered = RenderedPage(0, image_path, 600, 800, 600, 800, 0)
    words = [
        OCRWord("i", "Indicator:", 1, PixelBox(54, 120, 107, 135)),
        OCRWord("r", "Requirement:", 1, PixelBox(118, 120, 193, 135)),
        OCRWord("n", "1.2.1", 1, PixelBox(54, 160, 84, 180)),
        OCRWord("b", "The UoC shall maintain the required evidence.", 1, PixelBox(118, 160, 520, 180)),
    ]
    regions = [
        LayoutRegion("indicator", "paragraph", PixelBox(54, 120, 107, 135), 0.9, word_ids=["i"]),
        LayoutRegion("requirement", "paragraph", PixelBox(118, 120, 193, 135), 0.9, word_ids=["r"]),
        LayoutRegion("body", "list", PixelBox(54, 160, 520, 180), 0.9, word_ids=["n", "b"]),
    ]
    repaired = apply_profile_repairs(
        regions, rendered, OCRPage(0, words, "test"), native, profile
    )
    tables = [region for region in repaired if region.label == "table"]
    assert len(tables) == 1
    assert tables[0].profile_repair is True
    assert tables[0].profile_column_boundary_px is not None
    assert set(tables[0].word_ids) == {"i", "r", "n", "b"}


def test_profile_existing_table_consumes_duplicate_text_regions(tmp_path) -> None:
    native = _native_page(0, "1.2.1")
    profile = learn_document_profile([
        _native_page(index, f"1.2.{index + 1}") for index in range(3)
    ])
    image_path = tmp_path / "page.png"
    from PIL import Image

    Image.new("RGB", (600, 800), "white").save(image_path)
    rendered = RenderedPage(0, image_path, 600, 800, 600, 800, 0)
    words = [
        OCRWord("i", "Indicator:", 1, PixelBox(54, 120, 107, 135)),
        OCRWord("r", "Requirement:", 1, PixelBox(118, 120, 193, 135)),
        OCRWord("n", "1.2.1", 1, PixelBox(54, 160, 84, 180)),
        OCRWord("b", "The UoC shall maintain the required evidence.", 1, PixelBox(118, 160, 520, 180)),
    ]
    regions = [
        LayoutRegion("grid", "table", PixelBox(50, 115, 525, 185), 0.75),
        LayoutRegion("number", "list", PixelBox(54, 160, 84, 180), 0.9, word_ids=["n"]),
        LayoutRegion("body", "paragraph", PixelBox(118, 160, 520, 180), 0.9, word_ids=["b"]),
    ]
    repaired = apply_profile_repairs(
        regions, rendered, OCRPage(0, words, "test"), native, profile
    )
    tables = [region for region in repaired if region.label == "table"]
    assert len(tables) == 1
    assert tables[0].profile_repair is True
    assert set(tables[0].word_ids) == {"i", "r", "n", "b"}


def test_requirement_number_outside_table_is_a_structural_review() -> None:
    profile = learn_document_profile([
        _native_page(index, f"1.2.{index + 1}") for index in range(3)
    ])
    block = Block(
        id="body", type=BlockType.LIST, parent_id="section",
        segments=[Segment(
            id="segment-body", page_index=0,
            bbox=BoundingBox(x0=54, y0=160, x1=520, y1=180),
        )],
        content=_content("1.2.1 The UoC shall maintain the required evidence."),
    )
    reviews = validate_profile_consistency(
        {"body": block}, [_page(0)], profile
    )
    assert any(item.reason == "requirement_template_structure_mismatch" for item in reviews)


def test_malformed_table_does_not_satisfy_requirement_structure_gate() -> None:
    profile = learn_document_profile([
        _native_page(index, f"1.2.{index + 1}") for index in range(3)
    ])
    block = Block(
        id="bad-table", type=BlockType.TABLE, parent_id="section",
        segments=[Segment(
            id="segment-bad-table", page_index=0,
            bbox=BoundingBox(x0=54, y0=120, x1=520, y1=180),
        )],
        table=TableData(
            row_count=1, column_count=7, parser_backend="bad-grid",
            cells=[TableCell(
                id="bad-cell", row=0, column=0, page_index=0,
                bbox=BoundingBox(x0=54, y0=120, x1=84, y1=180),
                content=_content("1.2.1"),
            )],
        ),
    )
    reviews = validate_profile_consistency({"bad-table": block}, [_page(0)], profile)
    assert any(item.reason == "requirement_template_structure_mismatch" for item in reviews)
