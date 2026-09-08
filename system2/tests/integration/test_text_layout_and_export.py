from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from pdf_extraction.delivery import export_markdown
from pdf_extraction.assemble.document_assembler import assemble_document
from pdf_extraction.config import AssemblySettings
from pdf_extraction.layout import (
    annotate_list_markers,
    apply_native_visual_regions,
    apply_repeating_marginals,
    detect_repeating_marginals,
    native_text_for_region,
)
from pdf_extraction.layout.detector import _label_text_region
from pdf_extraction.layout.marginals import MarginalAnnotation
from pdf_extraction.models import (
    Block, BlockType, BoundingBox, FigureData, Page, Resolution,
    Segment, TableCell, TableData, TextContent,
)
from pdf_extraction.pipeline import ExtractionPipeline
from pdf_extraction.parsers.figure import parse_figure
from pdf_extraction.parsers.table import (
    RecognitionProposal,
    _RecognitionHTMLParser,
    _StructureParser,
    _grid_positions,
    _implicit_row_boundaries,
    _merged_cell_specs,
    _normalize_table_math_text,
    _repair_recognition_geometry,
    _recognition_geometry_consistent,
    _profile_requirement_table,
    _repair_profile_row_scope_leakage,
    _split_profile_requirement_spans,
)
from pdf_extraction.types import OCRWord, PixelBox
from pdf_extraction.parsers.text import build_text_content, recover_visual_blank_text
from pdf_extraction.types import (
    LayoutRegion,
    NativeObject,
    NativePage,
    OCRPage, OCRWord,
    PixelBox,
    RenderedPage,
    join_ocr_words,
    ocr_reading_order,
)

from tests.unit.test_models_and_validation import make_document


def test_critical_native_ocr_conflict_requires_review() -> None:
    content, conflict_type, critical = build_text_content(
        "The limit is 5 mg.", "The limit is 8 mg.", 0.99, 0.98
    )
    assert content.resolved_text is None
    assert content.requires_human_review is True
    assert conflict_type == "critical_text_conflict"
    assert critical is True


def test_ocr_order_uses_line_metadata_before_pixel_jitter() -> None:
    words = [
        OCRWord("b", "second", 1, PixelBox(80, 9, 120, 20), line_num=1),
        OCRWord("a", "first", 1, PixelBox(10, 11, 50, 20), line_num=1),
    ]
    assert [word.text for word in sorted(words, key=ocr_reading_order)] == ["first", "second"]


def test_numbered_criterion_with_title_is_a_heading(tmp_path: Path) -> None:
    page = RenderedPage(0, tmp_path / "page.png", 600, 800, 600, 800, 0)
    assert _label_text_region(
        "Criterion 1.1 - Legal Compliance", PixelBox(50, 60, 300, 85), page, 12
    ) == "heading"


def test_marginal_template_does_not_swallow_adjacent_body_text(tmp_path: Path) -> None:
    image_path = tmp_path / "page.png"
    Image.new("RGB", (600, 800), "white").save(image_path)
    page = RenderedPage(0, image_path, 600, 800, 600, 800, 0)
    words = [
        OCRWord("header", "Publisher", 1, PixelBox(450, 30, 540, 42), line_num=1),
        OCRWord("body1", "The UoC may decide to sell products", 1, PixelBox(55, 55, 360, 68), line_num=2),
        OCRWord("body2", "as non-certified.", 1, PixelBox(55, 72, 190, 85), line_num=3),
    ]
    regions = [LayoutRegion(
        "mixed", "paragraph", PixelBox(50, 28, 545, 88), 0.9,
        word_ids=[word.id for word in words],
    )]
    annotation = MarginalAnnotation(
        page_index=0, label="header", bbox_points=(450, 30, 540, 42),
        text="Publisher", native_object_ids=("native-header",),
    )
    output = apply_repeating_marginals(
        regions, page, OCRPage(0, words, "native-text-layer"), [annotation]
    )
    header = next(region for region in output if region.label == "header")
    body = next(region for region in output if region.label == "paragraph")
    assert header.word_ids == ["header"]
    assert body.word_ids == ["body1", "body2"]
    assert "The UoC" in body.text


def test_visual_line_end_hyphenation_is_repaired() -> None:
    words = [
        OCRWord("a", "quan-", 1, PixelBox(10, 10, 50, 20), line_num=1),
        OCRWord("b", "tities", 1, PixelBox(10, 30, 50, 40), line_num=2),
    ]
    assert join_ocr_words(words) == "quantities"


def test_visual_answer_blanks_are_recovered_in_x_order(tmp_path: Path) -> None:
    page_image = tmp_path / "worksheet.png"
    image = np.full((80, 700, 3), 255, dtype=np.uint8)
    for x0, x1 in ((10, 180), (290, 450), (520, 690)):
        cv2.line(image, (x0, 55), (x1, 55), (0, 0, 0), 3)
    cv2.imwrite(str(page_image), image)
    page = RenderedPage(0, page_image, 700, 80, 700, 80, 0)
    words = [
        OCRWord("is", "is", 0.99, PixelBox(205, 25, 240, 50), line_num=1),
        OCRWord("and", "and", 0.99, PixelBox(465, 25, 510, 50), line_num=1),
    ]
    region = LayoutRegion(
        "line", "paragraph", PixelBox(0, 0, 700, 70), 0.9,
        word_ids=["is", "and"],
    )

    recovered, boxes = recover_visual_blank_text(
        page, region, OCRPage(0, words, "test")
    )

    assert recovered == "____ is ____ and ____"
    assert len(boxes) == 3


def test_table_structure_parser_counts_spans() -> None:
    parser = _StructureParser()
    parser.feed(
        '<table><tr><td rowspan="2"></td><td colspan="2"></td></tr>'
        '<tr><td></td><td></td></tr></table>'
    )
    assert parser.rows == [[(2, 1), (1, 2)], [(1, 1), (1, 1)]]


def test_table_recognition_html_parser_preserves_text_spans_and_header() -> None:
    parser = _RecognitionHTMLParser()
    parser.feed(
        '<table><tr><th rowspan="2">Item</th><td colspan="2">Limit</td></tr>'
        '<tr><td>5 &lt; 8</td><td>A<br>B</td></tr></table>'
    )
    assert len(parser.rows) == 2
    assert parser.rows[0][0].is_header is True
    assert parser.rows[0][0].row_span == 2
    assert parser.rows[0][1].column_span == 2
    assert parser.rows[1][0].text == "5 < 8"
    assert parser.rows[1][1].text == "A B"


def test_implicit_row_boundaries_follow_ocr_baselines() -> None:
    region = PixelBox(100, 200, 400, 320)
    words = [
        OCRWord(
            id=f"w{index}", text=str(index), confidence=1.0,
            bbox=PixelBox(120, top, 160, top + 12),
            block_num=0, paragraph_num=0, line_num=index,
        )
        for index, top in enumerate((204, 224, 244, 264, 284, 304))
    ]
    boundaries = _implicit_row_boundaries(words, region, 120)
    assert len(boundaries) == 7
    assert boundaries[0] == 0
    assert boundaries[-1] == 120


def test_recognition_geometry_rejects_overlapping_model_columns() -> None:
    ordered = RecognitionProposal(
        rows=2,
        columns=2,
        confidence=0.99,
        cells=[
            (0, 0, 1, 1, PixelBox(0, 0, 50, 20), "a", False),
            (0, 1, 1, 1, PixelBox(50, 0, 100, 20), "b", False),
            (1, 0, 1, 1, PixelBox(0, 20, 50, 60), "c", False),
            (1, 1, 1, 1, PixelBox(50, 20, 100, 60), "d", False),
        ],
        html="<table></table>",
    )
    overlapping = RecognitionProposal(
        rows=1,
        columns=3,
        confidence=0.99,
        cells=[
            (0, 0, 1, 1, PixelBox(30, 0, 60, 20), "a", False),
            (0, 1, 1, 1, PixelBox(60, 0, 100, 20), "b", False),
            (0, 2, 1, 1, PixelBox(40, 0, 50, 20), "c", False),
        ],
        html="<table></table>",
    )

    assert _recognition_geometry_consistent(ordered) is True
    assert _recognition_geometry_consistent(overlapping) is False


def test_recognition_geometry_transposes_same_band_cells_into_columns() -> None:
    proposal = RecognitionProposal(
        rows=2, columns=1, confidence=0.99,
        cells=[
            (0, 0, 1, 1, PixelBox(0, 0, 100, 40), "Indicator:", False),
            (1, 0, 1, 1, PixelBox(92, 0, 500, 40), "Requirement:", False),
        ],
        html="<table><tr><td>Indicator:</td></tr><tr><td>Requirement:</td></tr></table>",
    )
    repaired = _repair_recognition_geometry(proposal)
    assert (repaired.rows, repaired.columns) == (1, 2)
    assert [(cell[0], cell[1]) for cell in repaired.cells] == [(0, 0), (0, 1)]
    assert all(cell[6] for cell in repaired.cells)
    assert repaired.geometry_repairs == ("same_band_cells_transposed_to_columns",)


def test_recognition_geometry_keeps_true_vertical_single_column() -> None:
    proposal = RecognitionProposal(
        rows=2, columns=1, confidence=0.99,
        cells=[
            (0, 0, 1, 1, PixelBox(0, 0, 100, 40), "A", False),
            (1, 0, 1, 1, PixelBox(0, 45, 100, 85), "B", False),
        ], html="<table></table>",
    )
    assert _repair_recognition_geometry(proposal) == proposal


def test_recognition_geometry_rejects_large_horizontal_overlap() -> None:
    proposal = RecognitionProposal(
        rows=2, columns=1, confidence=0.99,
        cells=[
            (0, 0, 1, 1, PixelBox(0, 0, 200, 40), "Indicator:", False),
            (1, 0, 1, 1, PixelBox(100, 0, 500, 40), "Requirement:", False),
        ], html="<table></table>",
    )
    assert _repair_recognition_geometry(proposal) == proposal


def test_table_math_normalization_uses_stable_inline_latex() -> None:
    assert _normalize_table_math_text("u3") == "$u_{3}$"
    assert (
        _normalize_table_math_text("ci = ∂f /∂x,")
        == "$c_{i}=\\partial f / \\partial x_{i}$"
    )
    assert (
        _normalize_table_math_text("|c1|×u(xi)")
        == "$\\left|c_{i}\\right| \\times u\\left(x_{i}\\right)$"
    )


def test_grid_restores_border_at_crop_edge() -> None:
    image = np.full((120, 160, 3), 255, dtype=np.uint8)
    for x in (5, 55, 105, 159):
        cv2.line(image, (x, 5), (x, 115), (0, 0, 0), 2)
    for y in (5, 60, 115):
        cv2.line(image, (5, y), (159, y), (0, 0, 0), 2)
    xs, ys = _grid_positions(image)
    assert xs[-1] >= 158
    assert len(xs) == 4
    assert len(ys) == 3


def test_missing_internal_rule_creates_column_span() -> None:
    image = np.full((120, 120, 3), 255, dtype=np.uint8)
    for x in (5, 115):
        cv2.line(image, (x, 5), (x, 115), (0, 0, 0), 2)
    cv2.line(image, (60, 60), (60, 115), (0, 0, 0), 2)
    for y in (5, 60, 115):
        cv2.line(image, (5, y), (115, y), (0, 0, 0), 2)
    xs, ys = _grid_positions(image)
    assert (0, 0, 1, 2) in _merged_cell_specs(image, xs, ys)


def test_requirement_template_restores_number_and_text_columns() -> None:
    specs = [(0, 0, 1, 1), (0, 1, 1, 1), (1, 0, 1, 2)]
    words = [
        OCRWord("n", "1.2.1", 1, PixelBox(10, 65, 45, 85)),
        OCRWord("b", "The UoC shall comply.", 1, PixelBox(70, 65, 190, 85)),
    ]
    repaired, changed = _split_profile_requirement_spans(
        specs,
        words,
        PixelBox(0, 0, 200, 100),
        [0, 60, 200],
        [0, 50, 100],
        profile_template_id="indicator_requirement_v1",
    )
    assert changed is True
    assert (1, 0, 1, 1) in repaired
    assert (1, 1, 1, 1) in repaired
    assert (1, 0, 1, 2) not in repaired


def test_figure_crop_is_preserved_as_independent_artifact(tmp_path: Path) -> None:
    page_image = tmp_path / "page.png"
    Image.new("RGB", (200, 100), "white").save(page_image)
    page = RenderedPage(0, page_image, 200, 100, 200, 100, 0)
    region = LayoutRegion("figure", "figure", PixelBox(20, 10, 120, 70), 1.0)
    figure = parse_figure(page, region, tmp_path / "figures", "figure-1")
    assert Path(figure.image_ref).is_file()
    assert (figure.width_px, figure.height_px) == (100, 60)


def test_explicit_figure_reference_creates_content_link() -> None:
    blocks = {
        "paragraph": Block(
            id="paragraph",
            type=BlockType.PARAGRAPH,
            content=TextContent(
                ocr_text="See Figure 2.",
                resolved_text="See Figure 2.",
                resolution=Resolution(selected_source="ocr", reason="test", confidence=1),
            ),
        ),
        "figure": Block(
            id="figure",
            type=BlockType.FIGURE,
            index="Figure 2: Result",
            figure=FigureData(image_ref="figure.png", width_px=10, height_px=10),
        ),
    }
    ExtractionPipeline._link_explicit_references(blocks)
    assert blocks["paragraph"].has_linked_content is True
    assert blocks["paragraph"].content_links[0].target_id == "figure"


def test_markdown_is_derived_from_canonical_model(tmp_path: Path) -> None:
    document = make_document()
    target = export_markdown(document, tmp_path / "document.md")
    assert target.read_text(encoding="utf-8") == "Hello\n"


def test_markdown_uses_output_relative_figure_path(tmp_path: Path) -> None:
    document = make_document()
    figure_path = tmp_path / "figures" / "figure.png"
    figure_path.parent.mkdir()
    figure_path.write_bytes(b"image")
    figure = Block(
        id="figure", type=BlockType.FIGURE, parent_id="section",
        figure=FigureData(image_ref=str(figure_path), width_px=10, height_px=10),
    )
    document.blocks["section"].children.append("figure")
    document.blocks["figure"] = figure
    target = export_markdown(document, tmp_path / "document.md")
    assert "![figure](figures/figure.png)" in target.read_text(encoding="utf-8")


def test_repeating_marginals_normalize_variable_page_numbers(tmp_path: Path) -> None:
    native_pages = []
    for index in range(3):
        native_pages.append(NativePage(
            page_index=index, width_points=600, height_points=800,
            text_lines=[
                NativeObject(f"h{index}", "Publisher", (430, 30, 540, 42), object_type="text_line"),
                NativeObject(
                    f"c{index}", f"Criterion 1.{index + 1} - Legal Compliance",
                    (50, 65, 300, 82), object_type="text_line",
                ),
                NativeObject(f"s{index}", "-", (128, 65, 134, 82), object_type="text_line"),
                NativeObject(
                    f"f{index}", f"Document ID X | Page {index + 7} of 511",
                    (50, 760, 550, 785), object_type="text_line",
                ),
                NativeObject(f"b{index}", "Body text", (50, 100, 200, 115), object_type="text_line"),
            ],
        ))
    annotations = detect_repeating_marginals(native_pages)
    assert {item.label for item in annotations[0]} == {"header", "footer"}
    assert all("Criterion" not in item.text for values in annotations.values() for item in values)

    image_path = tmp_path / "page.png"
    Image.new("RGB", (600, 800), "white").save(image_path)
    rendered = RenderedPage(0, image_path, 600, 800, 600, 800, 0)
    regions = [LayoutRegion("footer-as-text", "paragraph", PixelBox(50, 760, 550, 785), 0.9)]
    applied = apply_repeating_marginals(
        regions, rendered, OCRPage(0, [], "test"), annotations[0]
    )
    footers = [region for region in applied if region.label == "footer"]
    assert len(footers) == 1
    assert footers[0].bbox.y0 <= 760


def test_profile_requirement_table_uses_fixed_two_column_schema(tmp_path: Path) -> None:
    image_path = tmp_path / "page.png"
    Image.new("RGB", (600, 800), "white").save(image_path)
    page = RenderedPage(0, image_path, 600, 800, 600, 800, 0)
    region = LayoutRegion(
        "requirement", "table", PixelBox(50, 100, 540, 170), 0.995,
        profile_template_id="indicator_requirement_v1",
        profile_repair=True,
        profile_column_boundary_px=115,
    )
    words = [
        OCRWord("ih", "Indicator:", 1, PixelBox(54, 105, 105, 118), line_num=1),
        OCRWord("rh", "Requirement:", 1, PixelBox(118, 105, 195, 118), line_num=1),
        OCRWord("n", "1.1.1", 1, PixelBox(54, 145, 82, 162), line_num=2),
        OCRWord("b1", "The UoC shall hold", 1, PixelBox(118, 145, 250, 158), line_num=2),
        OCRWord("b2", "all permits.", 1, PixelBox(255, 145, 330, 158), line_num=2),
    ]
    parsed = _profile_requirement_table(
        page, region, OCRPage(0, words, "native-text-layer"),
        tmp_path / "crop.png", "table-1",
    )
    assert parsed is not None
    assert (parsed.data.row_count, parsed.data.column_count) == (2, 2)
    assert [cell.content.resolved_text for cell in parsed.data.cells] == [
        "Indicator:", "Requirement:", "1.1.1", "The UoC shall hold all permits."
    ]


def test_profile_requirement_table_supports_multiple_indicator_rows(tmp_path: Path) -> None:
    image_path = tmp_path / "page.png"
    Image.new("RGB", (600, 800), "white").save(image_path)
    page = RenderedPage(0, image_path, 600, 800, 600, 800, 0)
    region = LayoutRegion(
        "requirements", "table", PixelBox(50, 100, 540, 320), 0.995,
        profile_template_id="indicator_requirement_v1",
        profile_repair=True,
        profile_column_boundary_px=115,
    )
    words = [
        OCRWord("ih", "Indicator:", 1, PixelBox(54, 105, 105, 118), line_num=1),
        OCRWord("rh", "Requirement:", 1, PixelBox(118, 105, 195, 118), line_num=1),
        OCRWord("n1", "1.4.1", 1, PixelBox(54, 145, 82, 162), line_num=2),
        OCRWord("r1a", "The UoC shall identify risks", 1, PixelBox(118, 145, 320, 158), line_num=2),
        OCRWord("r1b", "at all sites.", 1, PixelBox(118, 168, 210, 181), line_num=3),
        OCRWord("n2", "1.4.2", 1, PixelBox(54, 220, 82, 237), line_num=4),
        OCRWord("r2a", "The UoC shall maintain traceability:", 1, PixelBox(118, 220, 365, 233), line_num=4),
        OCRWord("r2b", "a.", 1, PixelBox(118, 250, 130, 263), line_num=5),
        OCRWord("r2c", "only conforming product is used.", 1, PixelBox(140, 250, 360, 263), line_num=5),
        OCRWord("r2d", "o", 1, PixelBox(145, 280, 153, 293), line_num=6),
        OCRWord("r2e", "the source used ;", 1, PixelBox(165, 280, 270, 293), line_num=6),
    ]
    parsed = _profile_requirement_table(
        page, region, OCRPage(0, words, "native-text-layer"),
        tmp_path / "crop.png", "table-1",
    )
    assert parsed is not None
    assert (parsed.data.row_count, parsed.data.column_count) == (3, 2)
    assert [cell.content.resolved_text for cell in parsed.data.cells] == [
        "Indicator:", "Requirement:",
        "1.4.1", "The UoC shall identify risks at all sites.",
        "1.4.2", (
            "The UoC shall maintain traceability:\n"
            "a. only conforming product is used.\n"
            "• the source used;"
        ),
    ]
    assert "<br>a. only conforming product is used.<br>• the source used;" in parsed.data.html


def test_profile_requirement_table_preserves_indicator_side_label(tmp_path: Path) -> None:
    image_path = tmp_path / "page.png"
    Image.new("RGB", (600, 800), "white").save(image_path)
    page = RenderedPage(0, image_path, 600, 800, 600, 800, 0)
    region = LayoutRegion(
        "requirements", "table", PixelBox(50, 100, 540, 260), 0.995,
        profile_template_id="indicator_requirement_v1",
        profile_repair=True,
        profile_column_boundary_px=115,
    )
    words = [
        OCRWord("ih", "Indicator:", 1, PixelBox(54, 105, 105, 118), line_num=1),
        OCRWord("rh", "Requirement:", 1, PixelBox(118, 105, 195, 118), line_num=1),
        OCRWord("n1", "2.6.1", 1, PixelBox(54, 145, 82, 162), line_num=2),
        OCRWord("r1", "The UoC shall comply.", 1, PixelBox(118, 145, 300, 158), line_num=2),
        OCRWord("n2", "2.6.2", 1, PixelBox(54, 190, 82, 207), line_num=3),
        OCRWord("label", "Reporting", 1, PixelBox(54, 215, 105, 230), line_num=4),
        OCRWord("r2", "The UoC shall report annually.", 1, PixelBox(118, 190, 340, 205), line_num=3),
    ]
    parsed = _profile_requirement_table(
        page, region, OCRPage(0, words, "native-text-layer"),
        tmp_path / "crop.png", "table-1",
    )
    assert parsed is not None
    assert (parsed.data.row_count, parsed.data.column_count) == (3, 2)
    assert parsed.data.cells[4].content.resolved_text == "2.6.2\nReporting"


def test_profile_scope_leakage_moves_exact_duplicate_to_next_row() -> None:
    texts = {
        (1, 1): (
            "Indicator applicability: freshwater systems\n"
            "The UoC shall comply. Indicator applicability: freshwater systems"
        ),
        (2, 1): "The UoC shall report.",
    }
    repairs = _repair_profile_row_scope_leakage(texts, 2)
    assert repairs == [{
        "from_row": 1, "to_row": 2,
        "text": "Indicator applicability: freshwater systems",
    }]
    assert texts[(1, 1)] == "Indicator applicability: freshwater systems\nThe UoC shall comply."
    assert texts[(2, 1)] == "Indicator applicability: freshwater systems\nThe UoC shall report."


def test_bottom_footnote_cannot_absorb_next_page_body() -> None:
    section = Block(
        id="section", type=BlockType.SECTION,
        children=["note", "body"],
    )
    note = Block(
        id="note", type=BlockType.PARAGRAPH, parent_id="section",
        segments=[Segment(
            id="seg-note", page_index=0,
            bbox=BoundingBox(x0=50, y0=740, x1=500, y1=755),
        )],
        content=TextContent(
            native_text="17 Source reference.", resolved_text="17 Source reference.",
            resolution=Resolution(selected_source="native", reason="test", confidence=1),
        ),
    )
    body = Block(
        id="body", type=BlockType.PARAGRAPH, parent_id="section",
        segments=[Segment(
            id="seg-body", page_index=1,
            bbox=BoundingBox(x0=70, y0=70, x1=520, y1=90),
        )],
        content=TextContent(
            native_text="methodological requirements continue here.",
            resolved_text="methodological requirements continue here.",
            resolution=Resolution(selected_source="native", reason="test", confidence=1),
        ),
    )
    blocks = {block.id: block for block in (section, note, body)}
    pages = [
        Page(page_index=0, width=600, height=800, rotation=0, image_ref="p1.png",
             native_text_coverage=1, image_coverage=0, page_kind="born_digital", block_ids=["note"]),
        Page(page_index=1, width=600, height=800, rotation=0, image_ref="p2.png",
             native_text_coverage=1, image_coverage=0, page_kind="born_digital", block_ids=["body"]),
    ]
    assemble_document(blocks, pages, AssemblySettings())
    assert blocks["note"].type == BlockType.FOOTNOTE
    assert blocks["note"].content.resolved_text == "17 Source reference."
    assert blocks["body"].content.resolved_text == "methodological requirements continue here."


def test_footnote_band_is_effective_page_bottom_for_body_continuation() -> None:
    def content(value: str) -> TextContent:
        return TextContent(
            native_text=value, resolved_text=value,
            resolution=Resolution(selected_source="native", reason="test", confidence=1),
        )

    section = Block(
        id="section", type=BlockType.SECTION,
        children=["left", "note", "right"],
    )
    left = Block(
        id="left", type=BlockType.LIST, parent_id="section",
        segments=[Segment(
            id="seg-left", page_index=0,
            bbox=BoundingBox(x0=70, y0=500, x1=520, y1=520),
        )], content=content("Actions may also extend beyond the"),
    )
    note = Block(
        id="note", type=BlockType.FOOTNOTE, parent_id="section",
        segments=[Segment(
            id="seg-note", page_index=0,
            bbox=BoundingBox(x0=50, y0=700, x1=520, y1=720),
        )], content=content("19 Source."),
    )
    right = Block(
        id="right", type=BlockType.PARAGRAPH, parent_id="section",
        segments=[Segment(
            id="seg-right", page_index=1,
            bbox=BoundingBox(x0=70, y0=70, x1=520, y1=90),
        )], content=content("scope of the standard."),
    )
    blocks = {block.id: block for block in (section, left, note, right)}
    pages = [
        Page(page_index=0, width=600, height=800, rotation=0, image_ref="p1.png",
             native_text_coverage=1, image_coverage=0, page_kind="born_digital",
             block_ids=["left", "note"]),
        Page(page_index=1, width=600, height=800, rotation=0, image_ref="p2.png",
             native_text_coverage=1, image_coverage=0, page_kind="born_digital",
             block_ids=["right"]),
    ]
    reviews = assemble_document(blocks, pages, AssemblySettings())
    assert reviews == []
    assert blocks["left"].content.resolved_text == (
        "Actions may also extend beyond the scope of the standard."
    )
    assert "right" not in blocks
    assert blocks["note"].type == BlockType.FOOTNOTE


def test_captioned_header_only_table_recovers_aligned_body_rows() -> None:
    def content(value: str) -> TextContent:
        return TextContent(
            native_text=value, resolved_text=value,
            resolution=Resolution(selected_source="native", reason="test", confidence=1),
        )

    section = Block(
        id="section", type=BlockType.SECTION,
        children=["table", "d1", "l1", "d2", "l2"],
    )
    table = Block(
        id="table", type=BlockType.TABLE, parent_id="section", index="Table 1. Categories",
        segments=[Segment(
            id="seg-table", page_index=0,
            bbox=BoundingBox(x0=50, y0=400, x1=550, y1=450),
        )],
        table=TableData(row_count=1, column_count=2, parser_backend="test", cells=[
            TableCell(
                id="h1", row=0, column=0, page_index=0, is_header=True,
                bbox=BoundingBox(x0=50, y0=400, x1=150, y1=450), content=content("Category"),
            ),
            TableCell(
                id="h2", row=0, column=1, page_index=0, is_header=True,
                bbox=BoundingBox(x0=150, y0=400, x1=550, y1=450), content=content("Description"),
            ),
        ]),
    )
    def paragraph(block_id: str, value: str, x0: float, y0: float, x1: float) -> Block:
        return Block(
            id=block_id, type=BlockType.PARAGRAPH, parent_id="section",
            segments=[Segment(
                id=f"seg-{block_id}", page_index=0,
                bbox=BoundingBox(x0=x0, y0=y0, x1=x1, y1=y0 + 18),
            )],
            content=content(value),
        )
    blocks = {
        block.id: block for block in (
            section, table,
            paragraph("d1", "First description.", 160, 455, 520),
            paragraph("l1", "High", 55, 470, 110),
            paragraph("d2", "Second description.", 160, 520, 520),
            paragraph("l2", "Low", 55, 535, 110),
        )
    }
    pages = [Page(
        page_index=0, width=600, height=800, rotation=0, image_ref="p.png",
        native_text_coverage=1, image_coverage=0, page_kind="born_digital",
        block_ids=["table", "d1", "l1", "d2", "l2"],
    )]
    assemble_document(blocks, pages, AssemblySettings())
    assert blocks["table"].table.row_count == 3
    assert [cell.content.resolved_text for cell in blocks["table"].table.cells] == [
        "Category", "Description", "High", "First description.",
        "Low", "Second description.",
    ]
    assert all(block_id not in blocks for block_id in ("d1", "l1", "d2", "l2"))


def test_small_ungrounded_grid_on_full_page_bitmap_becomes_figure(tmp_path: Path) -> None:
    image_path = tmp_path / "page.png"
    Image.new("RGB", (600, 800), "white").save(image_path)
    page = RenderedPage(0, image_path, 600, 800, 600, 800, 0)
    native = NativePage(
        page_index=0, width_points=600, height_points=800,
        bitmap_resources=[{
            "rect": {
                "r_x0": 0, "r_y0": 0, "r_x1": 600, "r_y1": 0,
                "r_x2": 600, "r_y2": 800, "r_x3": 0, "r_y3": 800,
            }
        }],
    )
    regions = [LayoutRegion("icons", "table", PixelBox(450, 620, 530, 730), 0.8)]
    repaired = apply_native_visual_regions(
        regions, page, native, OCRPage(0, [], "native-text-layer")
    )
    assert repaired[0].label == "figure"
    assert repaired[0].visual_reclassification_reason == (
        "ungrounded_table_on_full_page_native_background"
    )

def test_native_marker_outside_layout_box_drives_list_level_and_clean_text(tmp_path: Path) -> None:
    image_path = tmp_path / "page.png"
    Image.new("RGB", (600, 800), "white").save(image_path)
    page = RenderedPage(0, image_path, 600, 800, 600, 800, 0)
    words = [
        NativeObject("outer-marker", "o", (54, 102, 60, 111)),
        NativeObject("outer-body", "Outer item", (72, 100, 150, 112)),
        NativeObject("inner-marker", "•", (75, 132, 80, 141)),
        NativeObject("inner-body", "Inner item", (93, 130, 170, 142)),
        NativeObject("deep-marker", "-", (96, 162, 101, 171)),
        NativeObject("deep-body", "Deep item", (114, 160, 190, 172)),
    ]
    regions = [
        LayoutRegion("outer", "paragraph", PixelBox(70, 98, 200, 115), 0.9),
        LayoutRegion("inner", "heading", PixelBox(91, 128, 210, 145), 0.9, heading_level=2),
        LayoutRegion("deep", "paragraph", PixelBox(112, 158, 220, 175), 0.9),
        LayoutRegion("outer-marker-only", "list", PixelBox(53, 101, 61, 112), 0.9, text="o"),
        LayoutRegion("inner-marker-only", "list", PixelBox(74, 131, 81, 142), 0.9, text="•"),
        LayoutRegion("deep-marker-only", "list", PixelBox(95, 161, 102, 172), 0.9, text="-"),
    ]
    regions = annotate_list_markers(regions, page, words)
    assert [region.list_level for region in regions] == [0, 1, 2]
    assert [region.label for region in regions] == ["list", "list", "list"]
    assert regions[1].heading_level is None
    text, refs = native_text_for_region(
        regions[0], page, words,
        excluded_text_ids=set(regions[0].native_object_ids),
        extra_ref_ids=regions[0].native_object_ids,
    )
    assert text == "Outer item"
    assert set(refs) == {"outer-marker", "outer-body"}


def test_native_bitmap_promotes_figure_and_consumes_internal_table(tmp_path: Path) -> None:
    image_path = tmp_path / "page.png"
    Image.new("RGB", (600, 800), "white").save(image_path)
    rendered = RenderedPage(0, image_path, 600, 800, 600, 800, 0)
    native = NativePage(
        page_index=0,
        width_points=600,
        height_points=800,
        bitmap_resources=[{
            "rect": {
                "r_x0": 50, "r_y0": 500, "r_x1": 550, "r_y1": 500,
                "r_x2": 550, "r_y2": 200, "r_x3": 50, "r_y3": 200,
            }
        }],
    )
    analysis = OCRPage(0, [
        OCRWord("diagram-text", "Final grow out", 1, PixelBox(350, 300, 470, 320))
    ], "native-text-layer")
    regions = [
        LayoutRegion("internal-box", "table", PixelBox(330, 250, 500, 360), 0.75),
        LayoutRegion("caption", "heading", PixelBox(50, 170, 300, 190), 0.95),
    ]
    output = apply_native_visual_regions(regions, rendered, native, analysis)
    assert [region.label for region in output] == ["heading", "figure"]
    assert output[1].word_ids == ["diagram-text"]


def test_list_hierarchy_and_conflict_replacement_survive_assembly(tmp_path: Path) -> None:
    document = make_document()
    section = document.blocks["section"]
    document.blocks.pop("paragraph")
    section.children = ["outer", "inner"]
    content = lambda value: TextContent(
        native_text=value, resolved_text=value,
        resolution=Resolution(selected_source="native", reason="test", confidence=1),
    )
    outer = Block(
        id="outer", type=BlockType.LIST, parent_id="section", list_marker="o", list_level=0,
        segments=[Segment(id="s-outer", page_index=0, bbox=BoundingBox(x0=54, y0=100, x1=300, y1=120))],
        content=content("Outer"),
    )
    inner = Block(
        id="inner", type=BlockType.LIST, parent_id="section", list_marker="•", list_level=1,
        segments=[Segment(id="s-inner", page_index=0, bbox=BoundingBox(x0=75, y0=130, x1=300, y1=150))],
        content=content("Inner"),
    )
    document.blocks.update({"outer": outer, "inner": inner})
    document.pages[0].block_ids = ["outer", "inner"]
    assemble_document(document.blocks, document.pages, AssemblySettings())
    assert section.children == ["outer"]
    assert outer.children == ["inner"]
    assert inner.parent_id == "outer"
    target = export_markdown(document, tmp_path / "nested.md")
    assert target.read_text(encoding="utf-8") == "- Outer\n\n  - Inner\n"


def test_numbered_heading_anchors_unnumbered_heading_below_level_one() -> None:
    document = make_document()
    section = document.blocks["section"]
    document.blocks.pop("paragraph")
    content = lambda value: TextContent(
        native_text=value, resolved_text=value,
        resolution=Resolution(selected_source="native", reason="test", confidence=1),
    )
    criterion = Block(
        id="criterion", type=BlockType.HEADING, parent_id="section", heading_level=1,
        content=content("Criterion 1.1 - Legal Compliance"),
    )
    continuation_heading = Block(
        id="continuation-heading", type=BlockType.HEADING, parent_id="section", heading_level=1,
        content=content("Auditors should confirm:"),
    )
    section.children = [criterion.id, continuation_heading.id]
    document.blocks.update({criterion.id: criterion, continuation_heading.id: continuation_heading})
    assemble_document(document.blocks, document.pages, AssemblySettings())
    assert criterion.heading_level == 1
    assert continuation_heading.heading_level == 2


def test_paragraph_assembly_records_replacement_for_conflict_remap() -> None:
    content = lambda value: TextContent(
        native_text=value, resolved_text=value,
        resolution=Resolution(selected_source="native", reason="test", confidence=1),
    )
    section = Block(id="section", type=BlockType.SECTION, children=["left", "right"])
    left = Block(
        id="left", type=BlockType.PARAGRAPH, parent_id="section",
        segments=[Segment(id="left-s", page_index=0, bbox=BoundingBox(x0=50, y0=700, x1=500, y1=780))],
        content=content("Contin-"),
    )
    right = Block(
        id="right", type=BlockType.PARAGRAPH, parent_id="section",
        segments=[Segment(id="right-s", page_index=1, bbox=BoundingBox(x0=50, y0=10, x1=500, y1=80))],
        content=content("uation"),
    )
    pages = [
        Page(page_index=index, width=600, height=800, rotation=0, image_ref="x.png",
             native_text_coverage=1, image_coverage=0, page_kind="born_digital",
             block_ids=["left" if index == 0 else "right"])
        for index in range(2)
    ]
    blocks = {item.id: item for item in (section, left, right)}
    replacements: dict[str, str] = {}
    assemble_document(blocks, pages, AssemblySettings(), replacements)
    assert replacements == {"right": "left"}
