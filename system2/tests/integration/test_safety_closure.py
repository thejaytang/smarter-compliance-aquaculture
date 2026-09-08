from __future__ import annotations

from pathlib import Path

from pdf_extraction.assemble.document_assembler import assemble_document
from pdf_extraction.assemble.paragraph_assembler import assemble_paragraphs
from pdf_extraction.config import AppConfig, AssemblySettings
from pdf_extraction.ingest.secondary_native import parse_pdftotext_bbox_xml
from pdf_extraction.models import (
    Block, BlockType, BoundingBox, Page, Resolution, Segment, TableCell, TableData,
    TextContent, FigureData,
)
from pdf_extraction.release_gate import evaluate_release
from pdf_extraction.types import NativeObject, NativePage
from pdf_extraction.validate.secondary_native_gate import apply_secondary_native_gate

from .test_scheme3 import _document


def _content(value: str) -> TextContent:
    return TextContent(
        native_text=value,
        resolved_text=value,
        resolution=Resolution(selected_source="native", reason="test", confidence=1),
    )


def _page() -> Page:
    return Page(
        page_index=0, width=612, height=792, rotation=0, image_ref="p.png",
        native_text_coverage=1, image_coverage=0, page_kind="born_digital",
    )


def test_pdftotext_bbox_xml_is_parsed_as_independent_native_evidence() -> None:
    xml = """<?xml version="1.0"?>
    <html xmlns="http://www.w3.org/1999/xhtml"><body><doc>
      <page width="612" height="792"><flow><block><line>
        <word xMin="50" yMin="100" xMax="80" yMax="112">≥15%</word>
      </line></block></flow></page>
    </doc></body></html>"""
    pages = parse_pdftotext_bbox_xml(xml, first_page_index=104)
    assert pages[0].page_index == 104
    assert pages[0].words[0].text == "≥15%"
    assert pages[0].words[0].bbox_points == (50.0, 100.0, 80.0, 112.0)


def test_secondary_native_exact_token_repairs_split_percentage_without_overwriting_native() -> None:
    block = Block(
        id="requirement", type=BlockType.PARAGRAPH,
        segments=[Segment(
            id="segment", page_index=0,
            bbox=BoundingBox(x0=40, y0=90, x1=300, y1=130),
        )],
        content=_content("The annual samples shall be ≥1 5% of the total."),
    )
    secondary = NativePage(
        page_index=0, width_points=612, height_points=792,
        words=[NativeObject(
            id="w1", text="The annual samples shall be ≥15% of the total.",
            bbox_points=(45, 95, 295, 120),
        )],
    )
    reviews = apply_secondary_native_gate({block.id: block}, [secondary])
    assert reviews == []
    assert block.content.native_text.endswith("≥1 5% of the total.")
    assert block.content.resolved_text.endswith("≥15% of the total.")
    assert block.operations[-1]["operation"] == "secondary_native_exact_token_repair"


def test_secondary_native_unresolved_critical_mismatch_fails_closed() -> None:
    block = Block(
        id="requirement", type=BlockType.PARAGRAPH,
        segments=[Segment(
            id="segment", page_index=0,
            bbox=BoundingBox(x0=40, y0=90, x1=300, y1=130),
        )],
        content=_content("The UoC shall not exceed 15%."),
    )
    secondary = NativePage(
        page_index=0, width_points=612, height_points=792,
        words=[NativeObject(
            id="w1", text="The UoC shall not exceed 16%.",
            bbox_points=(45, 95, 295, 120),
        )],
    )
    reviews = apply_secondary_native_gate({block.id: block}, [secondary])
    assert reviews and reviews[0].severity == "critical"
    assert block.quality.requires_review
    assert block.content.requires_human_review
    assert block.content.resolved_text is None
    assert block.content.native_text == 'The UoC shall not exceed 15%.'
    assert block.operations[-1]['primary_candidate'].endswith('15%.')
    assert block.operations[-1]['secondary_candidate'].endswith('16%.')


def test_secondary_native_critical_values_with_different_extraction_order_agree() -> None:
    block = Block(
        id="footnote", type=BlockType.FOOTNOTE,
        segments=[Segment(
            id="segment", page_index=0,
            bbox=BoundingBox(x0=40, y0=700, x1=500, y1=730),
        )], content=_content("28 https://example.test/tabid/2509/Default.aspx"),
    )
    secondary = NativePage(
        page_index=0, width_points=612, height_points=792,
        words=[
            NativeObject(id="url", text="https://example.test/tabid/2509/Default.aspx", bbox_points=(50, 705, 450, 718)),
            NativeObject(id="marker", text="28", bbox_points=(40, 705, 48, 718)),
        ],
    )
    assert apply_secondary_native_gate({block.id: block}, [secondary]) == []
    assert not block.quality.requires_review


def test_tiny_right_edge_duplicate_inside_table_is_suppressed() -> None:
    page = _page()
    section = Block(id="section", type=BlockType.SECTION, children=["table", "fragment"])
    table = Block(
        id="table", type=BlockType.TABLE, parent_id="section",
        segments=[Segment(
            id="table-segment", page_index=0,
            bbox=BoundingBox(x0=50, y0=100, x1=552, y1=220),
        )],
        table=TableData(
            row_count=1, column_count=1, parser_backend="test",
            cells=[TableCell(
                id="cell", row=0, column=0, page_index=0,
                bbox=BoundingBox(x0=50, y0=100, x1=552, y1=220),
                content=_content("The UoC shall apply condition a."),
            )],
        ),
    )
    fragment = Block(
        id="fragment", type=BlockType.PARAGRAPH, parent_id="section",
        segments=[Segment(
            id="fragment-segment", page_index=0,
            bbox=BoundingBox(x0=540, y0=150, x1=543, y1=162),
        )],
        content=_content("a"),
    )
    page.block_ids = ["table", "fragment"]
    blocks = {item.id: item for item in (section, table, fragment)}
    replacements: dict[str, str] = {}
    assemble_document(blocks, [page], AssemblySettings(), replacements)
    assert "fragment" not in blocks
    assert replacements["fragment"] == "table"
    assert table.operations[0]["operation"] == "table_edge_duplicate_fragment_suppression"


def test_connector_and_citation_suffix_fragments_merge_on_same_page() -> None:
    for suffix in ("and", "p."):
        page = _page()
        section = Block(id="section", type=BlockType.SECTION, children=["left", "right"])
        left = Block(
            id="left", type=BlockType.LIST, parent_id="section",
            segments=[Segment(
                id="left-segment", page_index=0,
                bbox=BoundingBox(x0=80, y0=100, x1=500, y1=114),
            )], content=_content("Supporting citation"),
        )
        right = Block(
            id="right", type=BlockType.LIST, parent_id="section",
            segments=[Segment(
                id="right-segment", page_index=0,
                bbox=BoundingBox(x0=520, y0=116, x1=545, y1=130),
            )], content=_content(suffix),
        )
        page.block_ids = ["left", "right"]
        blocks = {item.id: item for item in (section, left, right)}
        assemble_paragraphs(blocks, [page], AssemblySettings())
        assert "right" not in blocks
        assert blocks["left"].content.resolved_text.endswith(suffix)


def test_local_list_label_is_promoted_and_explicit_figure_caption_is_attached() -> None:
    page = _page()
    section = Block(
        id="section", type=BlockType.SECTION,
        children=["label", "item", "figure", "caption"],
    )
    label = Block(
        id="label", type=BlockType.PARAGRAPH, parent_id="section",
        segments=[Segment(id="label-segment", page_index=0, bbox=BoundingBox(x0=50, y0=50, x1=200, y1=65))],
        content=_content("Sampling Timing"),
    )
    item = Block(
        id="item", type=BlockType.LIST, parent_id="section",
        segments=[Segment(id="item-segment", page_index=0, bbox=BoundingBox(x0=65, y0=75, x1=450, y1=90))],
        content=_content("Collect samples in summer."),
    )
    figure = Block(
        id="figure", type=BlockType.FIGURE, parent_id="section",
        segments=[Segment(id="figure-segment", page_index=0, bbox=BoundingBox(x0=100, y0=120, x1=500, y1=300))],
        figure=FigureData(image_ref="figure.png", width_px=400, height_px=180),
    )
    caption = Block(
        id="caption", type=BlockType.PARAGRAPH, parent_id="section",
        segments=[Segment(id="caption-segment", page_index=0, bbox=BoundingBox(x0=100, y0=310, x1=500, y1=330))],
        content=_content("Figure 1. Sampling locations."),
    )
    page.block_ids = ["label", "item", "figure", "caption"]
    blocks = {item.id: item for item in (section, label, item, figure, caption)}
    replacements: dict[str, str] = {}
    assemble_document(blocks, [page], AssemblySettings(), replacements)
    assert blocks["label"].type == BlockType.HEADING
    assert blocks["label"].heading_level == 4
    assert blocks["figure"].index == "Figure 1. Sampling locations."
    assert "caption" not in blocks


def test_release_gate_does_not_invent_precision_when_no_evaluation_exists(tmp_path: Path) -> None:
    document = _document(tmp_path)
    report = evaluate_release(document, AppConfig(), performance={"within_budget": True})
    assert not report["checks"]["accepted_result_precision"]
    assert "accepted_result_precision" in report["failures"]
