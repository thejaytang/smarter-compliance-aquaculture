from __future__ import annotations

import json
import re
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from pdf_extraction.assemble.content_linker import enrich_content_links
from pdf_extraction.assemble.note_parser import populate_note_spans
from pdf_extraction.assemble.paragraph_assembler import assemble_paragraphs
from pdf_extraction.assemble.table_assembler import (
    assemble_tables,
    attach_profile_table_continuations,
)
from pdf_extraction.config import (
    AssemblySettings, CompletenessSettings, LinkSettings, PrecisionReviewSettings,
)
from pdf_extraction.evaluation import evaluate_manifest, enforce_regression_thresholds
from pdf_extraction.models import (
    Block, BlockType, BoundingBox, EvidenceSpan, FigureData, Page, Resolution,
    ResolutionStatus, Segment, TableCell, TableData, TextContent,
)
from pdf_extraction.parsers.table import Img2TableStructureBackend
from pdf_extraction.reconcile.conflict_detector import conflicts_from_spans
from pdf_extraction.reconcile.resolver import apply_abstention_policy
from pdf_extraction.reconcile.precision_review import PrecisionReviewer
from pdf_extraction.reconcile.span_aligner import build_evidence_spans
from pdf_extraction.types import LayoutRegion, NativeObject, OCRPage, OCRWord, PixelBox, RenderedPage
from pdf_extraction.validate.completeness_gate import build_page_completeness_report

from tests.unit.test_models_and_validation import make_document


def _content(value: str | None) -> TextContent:
    return TextContent(
        ocr_text=value, resolved_text=value,
        resolution=Resolution(
            selected_source="ocr" if value else "none", reason="test", confidence=1 if value else 0
        ),
    )


def _page(index: int) -> Page:
    return Page(
        page_index=index, width=612, height=792, rotation=0,
        image_ref=f"page-{index}.png", native_text_coverage=0,
        image_coverage=1, page_kind="scanned",
    )


def _cell(block_id: str, row: int, column: int, value: str | None, page: int) -> TableCell:
    return TableCell(
        id=f"{block_id}-{row}-{column}", row=row, column=column,
        bbox=BoundingBox(x0=10 + column * 100, y0=10 + row * 20, x1=100 + column * 100, y1=30 + row * 20),
        page_index=page, content=_content(value), is_header=row == 0,
    )


def test_profile_requirement_table_absorbs_headerless_next_page_clauses() -> None:
    section = Block(
        id="section", type=BlockType.SECTION,
        children=["table", "clause-c", "clause-d", "continuation", "clause-e"],
    )
    table = Block(
        id="table", type=BlockType.TABLE, parent_id="section",
        segments=[Segment(
            id="table-segment", page_index=0,
            bbox=BoundingBox(x0=50, y0=620, x1=550, y1=780),
        )],
        table=TableData(
            row_count=2, column_count=2,
            parser_backend="document-profile+native-text-layer",
            cells=[
                _cell("table", 0, 0, "Indicator:", 0),
                _cell("table", 0, 1, "Requirement:", 0),
                _cell("table", 1, 0, "1.4.3", 0),
                _cell(
                    "table", 1, 1,
                    "The UoC shall provide: a. first; and\nb. second; and", 0,
                ),
            ],
        ),
    )

    def clause(block_id: str, text: str, y0: float, x0: float = 120) -> Block:
        block_type = BlockType.LIST if re.match(r"^[a-z]\. ", text) else BlockType.PARAGRAPH
        return Block(
            id=block_id, type=block_type, parent_id="section",
            segments=[Segment(
                id=f"segment-{block_id}", page_index=1,
                bbox=BoundingBox(x0=x0, y0=y0, x1=530, y1=y0 + 14),
            )],
            content=_content(text),
        )

    fragments = [
        clause("clause-c", "c. third; and", 40),
        clause("clause-d", "d. fourth (i.e.", 65),
        clause("continuation", "Mass Balance); and", 84, 138),
        clause("clause-e", "e. fifth.", 108),
    ]
    pages = [_page(0), _page(1)]
    pages[0].block_ids = ["table"]
    pages[1].block_ids = [item.id for item in fragments]
    blocks = {item.id: item for item in [section, table, *fragments]}
    replacements: dict[str, str] = {}

    assert attach_profile_table_continuations(blocks, pages, replacements) == []
    assert set(blocks) == {"section", "table"}
    assert replacements == {item.id: "table" for item in fragments}
    value = next(
        cell.content.resolved_text
        for cell in table.table.cells
        if cell.row == 1 and cell.column == 1
    )
    assert value.endswith(
        "\nc. third; and\nd. fourth (i.e. Mass Balance); and\ne. fifth."
    )


def test_completeness_counts_bound_auxiliary_evidence(tmp_path: Path) -> None:
    image_path = tmp_path / "page.png"
    Image.new("RGB", (200, 100), "white").save(image_path)
    page = RenderedPage(0, image_path, 200, 100, 200, 100, 0)
    word = OCRWord("caption", "Table 1", 1, PixelBox(20, 10, 70, 25))
    region = LayoutRegion(
        "table", "table", PixelBox(20, 35, 180, 90), 1,
        word_ids=[word.id], index_text="Table 1",
    )
    report = build_page_completeness_report(
        page,
        native_page=type("Native", (), {
            "width_points": 200, "height_points": 100,
            "characters": [], "words": [], "bitmap_resources": [{"image": 1}], "shapes": []
        })(),
        ocr_page=OCRPage(0, [word], "test"), regions=[region],
        settings=CompletenessSettings(),
    )
    assert report.assigned_ocr_word_count == 1
    assert report.status == "accepted"


def test_completeness_ignores_unassigned_whitespace_characters(tmp_path: Path) -> None:
    image_path = tmp_path / "page.png"
    Image.new("RGB", (200, 100), "white").save(image_path)
    page = RenderedPage(0, image_path, 200, 100, 200, 100, 0)
    region = LayoutRegion("body", "paragraph", PixelBox(20, 10, 180, 40), 1)
    native_page = type("Native", (), {
        "width_points": 200, "height_points": 100,
        "characters": [
            NativeObject("visible", "A", (30, 15, 35, 25), object_type="character"),
            NativeObject("space", " ", (190, 90, 195, 95), object_type="character"),
        ],
        "words": [], "bitmap_resources": [], "shapes": [],
    })()
    report = build_page_completeness_report(
        page, native_page=native_page, ocr_page=OCRPage(0, [], "test"),
        regions=[region], settings=CompletenessSettings(),
    )
    assert report.native_object_count == 1
    assert report.unassigned_native_object_count == 0
    assert report.status == "accepted"


def test_span_conflict_abstains_instead_of_guessing(tmp_path: Path) -> None:
    image_path = tmp_path / "page.png"
    Image.new("RGB", (200, 100), "white").save(image_path)
    page = RenderedPage(0, image_path, 200, 100, 200, 100, 0)
    block = Block(
        id="paragraph", type=BlockType.PARAGRAPH,
        segments=[Segment(id="segment", page_index=0, bbox=BoundingBox(x0=0, y0=0, x1=200, y1=100))],
        content=_content("The limit is 8 mg."),
    )
    native = NativeObject("native", "The limit is 5 mg.", (10, 10, 150, 30))
    ocr = OCRWord("ocr", "The limit is 8 mg.", 0.99, PixelBox(10, 10, 150, 30))
    spans = build_evidence_spans(
        block, {0: page}, {0: [native]}, {0: OCRPage(0, [ocr], "test")}
    )
    assert any(span.criticality == "numeric" and span.resolution_status == ResolutionStatus.AMBIGUOUS for span in spans)
    assert apply_abstention_policy(block, spans)
    assert block.content.resolved_text is None
    conflicts = conflicts_from_spans(spans, [])
    assert conflicts[0].conflict_type == "critical_numeric_conflict"
    assert conflicts[0].status == "review_required"


def test_missing_critical_token_and_precision_review_are_auditable(tmp_path: Path) -> None:
    image_path = tmp_path / "page.png"
    Image.new("RGB", (200, 100), "white").save(image_path)
    page = RenderedPage(0, image_path, 200, 100, 200, 100, 0)
    block = Block(
        id="paragraph", type=BlockType.PARAGRAPH,
        segments=[Segment(id="segment", page_index=0, bbox=BoundingBox(x0=0, y0=0, x1=200, y1=100))],
        content=_content("The limit applies."),
    )
    spans = build_evidence_spans(
        block, {0: page},
        {0: [NativeObject("native", "The limit is 5 mg.", (10, 10, 150, 30))]},
        {0: OCRPage(0, [OCRWord("ocr", "The limit applies.", 0.99, PixelBox(10, 10, 150, 30))], "test")},
    )
    assert any(span.resolution_status == ResolutionStatus.AMBIGUOUS for span in spans)
    assert any(conflict.conflict_type == "missing_content_conflict" for conflict in conflicts_from_spans(spans, []))

    class FixedOCR:
        name = "fixed-ocr"

        def recognize_crop(self, image: Image.Image, language: str = "eng") -> tuple[str, float]:
            return "5", 0.99

    numeric = next(span for span in spans if span.criticality == "numeric")
    reviewer = PrecisionReviewer(
        PrecisionReviewSettings(backend="enhanced_ocr", auto_resolve_confidence=0.96),
        FixedOCR(),
    )
    reviewer.resolve_span(numeric, page)
    assert numeric.review_text == "5"
    assert numeric.resolution_status == ResolutionStatus.RESOLVED


def test_cross_page_paragraph_auto_merge_is_reversible() -> None:
    section = Block(id="section", type=BlockType.SECTION, children=["left", "right"])
    left = Block(
        id="left", type=BlockType.PARAGRAPH, parent_id="section",
        segments=[Segment(id="s-left", page_index=0, bbox=BoundingBox(x0=50, y0=700, x1=500, y1=780))],
        content=_content("A hy-"),
    )
    right = Block(
        id="right", type=BlockType.PARAGRAPH, parent_id="section",
        segments=[Segment(id="s-right", page_index=1, bbox=BoundingBox(x0=50, y0=10, x1=500, y1=80))],
        content=_content("phenated continuation"),
    )
    pages = [_page(0), _page(1)]
    pages[0].block_ids = ["left"]
    pages[1].block_ids = ["right"]
    blocks = {item.id: item for item in (section, left, right)}
    reviews = assemble_paragraphs(blocks, pages, AssemblySettings())
    assert reviews == []
    assert "right" not in blocks
    assert blocks["left"].content.resolved_text == "A hyphenated continuation"
    assert blocks["left"].operations[0]["source_fragment_ids"] == ["left", "right"]


def test_same_page_line_fragment_joins_existing_cross_page_continuation() -> None:
    section = Block(id="section", type=BlockType.SECTION, children=["left", "right"])
    left = Block(
        id="left", type=BlockType.PARAGRAPH, parent_id="section",
        segments=[Segment(
            id="s-left", page_index=0,
            bbox=BoundingBox(x0=52, y0=592, x1=221, y1=604),
        )],
        content=_content("This paragraph deliberately continues"),
    )
    right = Block(
        id="right", type=BlockType.PARAGRAPH, parent_id="section",
        segments=[
            Segment(
                id="s-right-0", page_index=0,
                bbox=BoundingBox(x0=52, y0=612, x1=215, y1=625),
            ),
            Segment(
                id="s-right-1", page_index=1,
                bbox=BoundingBox(x0=52, y0=43, x1=245, y1=56),
            ),
        ],
        content=_content("across the page boundary and ends on the next page."),
    )
    pages = [_page(0), _page(1)]
    pages[0].block_ids = ["left", "right"]
    pages[1].block_ids = ["right"]
    blocks = {item.id: item for item in (section, left, right)}

    assert assemble_paragraphs(blocks, pages, AssemblySettings()) == []
    assert "right" not in blocks
    assert len(blocks["left"].segments) == 3
    assert pages[0].block_ids == ["left"]
    assert pages[1].block_ids == ["left"]
    assert blocks["left"].operations[0]["merge_kind"] == "same_page_fragment"


def test_list_item_absorbs_same_page_paragraph_continuation() -> None:
    section = Block(id="section", type=BlockType.SECTION, children=["item", "continuation"])
    item = Block(
        id="item", type=BlockType.LIST, parent_id="section", list_marker="•", list_level=1,
        segments=[Segment(
            id="s-item", page_index=0,
            bbox=BoundingBox(x0=75, y0=100, x1=540, y1=114),
        )],
        content=_content("The requirement applies to the"),
    )
    continuation = Block(
        id="continuation", type=BlockType.PARAGRAPH, parent_id="section",
        segments=[Segment(
            id="s-continuation", page_index=0,
            bbox=BoundingBox(x0=93, y0=118, x1=400, y1=132),
        )],
        content=_content("local context."),
    )
    pages = [_page(0)]
    pages[0].block_ids = ["item", "continuation"]
    blocks = {item.id: item for item in (section, item, continuation)}
    replacements: dict[str, str] = {}
    assert assemble_paragraphs(blocks, pages, AssemblySettings(), replacements) == []
    assert blocks["item"].content.resolved_text == "The requirement applies to the local context."
    assert replacements == {"continuation": "item"}


def test_adjacent_list_items_are_not_merged_even_without_terminal_period() -> None:
    section = Block(id="section", type=BlockType.SECTION, children=["left", "right"])
    left = Block(
        id="left", type=BlockType.LIST, parent_id="section", list_marker="-", list_level=2,
        segments=[Segment(
            id="s-left", page_index=0,
            bbox=BoundingBox(x0=96, y0=100, x1=300, y1=114),
        )], content=_content("first item,"),
    )
    right = Block(
        id="right", type=BlockType.LIST, parent_id="section", list_marker="-", list_level=2,
        segments=[Segment(
            id="s-right", page_index=0,
            bbox=BoundingBox(x0=96, y0=118, x1=300, y1=132),
        )], content=_content("second item,"),
    )
    pages = [_page(0)]
    pages[0].block_ids = ["left", "right"]
    blocks = {item.id: item for item in (section, left, right)}
    assert assemble_paragraphs(blocks, pages, AssemblySettings()) == []
    assert set(blocks) == {"section", "left", "right"}


def test_paragraph_fragments_merge_as_a_same_page_cross_page_chain() -> None:
    section = Block(
        id="section", type=BlockType.SECTION,
        children=["left", "middle", "tail"],
    )
    left = Block(
        id="left", type=BlockType.PARAGRAPH, parent_id="section",
        segments=[Segment(
            id="s-left", page_index=0,
            bbox=BoundingBox(x0=52, y0=592, x1=221, y1=604),
        )],
        content=_content("This paragraph deliberately continues"),
    )
    middle = Block(
        id="middle", type=BlockType.PARAGRAPH, parent_id="section",
        segments=[Segment(
            id="s-middle", page_index=0,
            bbox=BoundingBox(x0=52, y0=612, x1=215, y1=625),
        )],
        content=_content("across the page boundary with a hy-"),
    )
    tail = Block(
        id="tail", type=BlockType.PARAGRAPH, parent_id="section",
        segments=[Segment(
            id="s-tail", page_index=1,
            bbox=BoundingBox(x0=52, y0=43, x1=245, y1=56),
        )],
        content=_content("phenated word and ends on the next page."),
    )
    pages = [_page(0), _page(1)]
    pages[0].block_ids = ["left", "middle"]
    pages[1].block_ids = ["tail"]
    blocks = {item.id: item for item in (section, left, middle, tail)}

    assert assemble_paragraphs(blocks, pages, AssemblySettings()) == []
    assert set(blocks) == {"section", "left"}
    assert len(blocks["left"].segments) == 3
    assert blocks["left"].content.resolved_text == (
        "This paragraph deliberately continues across the page boundary "
        "with a hyphenated word and ends on the next page."
    )
    assert [item["merge_kind"] for item in blocks["left"].operations] == [
        "same_page_fragment", "cross_page_continuation",
    ]


def test_cross_page_table_removes_header_and_joins_partial_row_without_gap() -> None:
    section = Block(id="section", type=BlockType.SECTION, children=["left", "right"])
    left_cells = [
        _cell("left", 0, 0, "Item", 0), _cell("left", 0, 1, "Value", 0),
        _cell("left", 1, 0, "A", 0), _cell("left", 1, 1, None, 0),
    ]
    right_cells = [
        _cell("right", 0, 0, "Item", 1), _cell("right", 0, 1, "Value", 1),
        _cell("right", 1, 0, None, 1), _cell("right", 1, 1, "5", 1),
        _cell("right", 2, 0, "B", 1), _cell("right", 2, 1, "7", 1),
    ]
    left = Block(
        id="left", type=BlockType.TABLE, parent_id="section",
        segments=[Segment(id="s-left", page_index=0, bbox=BoundingBox(x0=10, y0=600, x1=210, y1=780))],
        table=TableData(row_count=2, column_count=2, cells=left_cells, parser_backend="test"),
    )
    right = Block(
        id="right", type=BlockType.TABLE, parent_id="section",
        segments=[Segment(id="s-right", page_index=1, bbox=BoundingBox(x0=10, y0=10, x1=210, y1=180))],
        table=TableData(row_count=3, column_count=2, cells=right_cells, parser_backend="test"),
    )
    pages = [_page(0), _page(1)]
    pages[0].block_ids, pages[1].block_ids = ["left"], ["right"]
    blocks = {item.id: item for item in (section, left, right)}
    assert assemble_tables(blocks, pages, AssemblySettings()) == []
    table = blocks["left"].table
    assert table.row_count == 3
    assert sorted({cell.row for cell in table.cells}) == [0, 1, 2]
    assert next(cell for cell in table.cells if cell.row == 1 and cell.column == 1).content.resolved_text == "5"
    operation = blocks["left"].operations[-1]
    assert operation["removed_repeated_headers"] == [0]
    assert operation["joined_rows"]


def test_detached_numbered_row_attaches_to_two_column_label_header() -> None:
    section = Block(id="section", type=BlockType.SECTION, children=["table", "body"])
    headers = [
        TableCell(
            id="h0", row=0, column=0,
            bbox=BoundingBox(x0=50, y0=100, x1=115, y1=135), page_index=0,
            content=_content("Indicator:"),
        ),
        TableCell(
            id="h1", row=0, column=1,
            bbox=BoundingBox(x0=115, y0=100, x1=545, y1=135), page_index=0,
            content=_content("Requirement:"),
        ),
    ]
    table = Block(
        id="table", type=BlockType.TABLE, parent_id="section",
        segments=[Segment(
            id="table-segment", page_index=0,
            bbox=BoundingBox(x0=50, y0=95, x1=545, y1=135),
        )],
        table=TableData(
            row_count=1, column_count=2, cells=headers, parser_backend="test",
        ),
    )
    body = Block(
        id="body", type=BlockType.LIST, parent_id="section",
        segments=[Segment(
            id="body-segment", page_index=0,
            bbox=BoundingBox(x0=54, y0=145, x1=405, y1=165),
        )],
        content=_content("1.1.1 The UoC shall hold all permits."),
    )
    pages = [_page(0)]
    pages[0].block_ids = ["table", "body"]
    blocks = {item.id: item for item in (section, table, body)}
    replacements: dict[str, str] = {}
    assert assemble_tables(blocks, pages, AssemblySettings(), replacements) == []
    assert "body" not in blocks
    assert replacements == {"body": "table"}
    assert (table.table.row_count, table.table.column_count) == (2, 2)
    values = {
        (cell.row, cell.column): cell.content.resolved_text for cell in table.table.cells
    }
    assert values[(1, 0)] == "1.1.1"
    assert values[(1, 1)] == "The UoC shall hold all permits."
    assert table.table.html == (
        "<table><tr><th>Indicator:</th><th>Requirement:</th></tr>"
        "<tr><td>1.1.1</td><td>The UoC shall hold all permits.</td></tr></table>"
    )
    assert pages[0].block_ids == ["table"]


def test_links_notes_and_real_img2table_route(tmp_path: Path) -> None:
    section = Block(id="section", type=BlockType.SECTION, children=["paragraph", "table"])
    paragraph = Block(
        id="paragraph", type=BlockType.PARAGRAPH, parent_id="section",
        segments=[Segment(id="s", page_index=0, bbox=BoundingBox(x0=1, y0=1, x1=10, y1=10))],
        content=_content("Use the following table."),
    )
    table = Block(id="table", type=BlockType.TABLE, parent_id="section", index="Table 2", note="Source: test; Warning: inspect")
    blocks = {item.id: item for item in (section, paragraph, table)}
    reviews = enrich_content_links(blocks, LinkSettings())
    populate_note_spans(blocks)
    assert blocks["paragraph"].content_links[0].target_id == "table"
    assert reviews[0].reason == "inferred_content_link"
    assert [span.role for span in blocks["table"].note_spans] == ["source", "warning"]

    image_path = tmp_path / "grid.png"
    image = np.full((400, 600, 3), 255, dtype=np.uint8)
    for x in (20, 300, 580):
        cv2.line(image, (x, 20), (x, 380), (0, 0, 0), 4)
    for y in (20, 140, 260, 380):
        cv2.line(image, (20, y), (580, y), (0, 0, 0), 4)
    for row, values in enumerate((("Item", "Value"), ("A", "5"), ("B", "7"))):
        for column, value in enumerate(values):
            cv2.putText(
                image, value, (45 + column * 280, 90 + row * 120),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2, cv2.LINE_AA,
            )
    cv2.imwrite(str(image_path), image)
    proposal = Img2TableStructureBackend().analyze(image_path)
    assert (proposal.rows, proposal.columns) == (3, 2)
    assert len(proposal.cells) == 6


def test_gold_evaluator_and_regression_gate(tmp_path: Path) -> None:
    prediction = make_document().model_dump(mode="json")
    prediction_path = tmp_path / "prediction.json"
    gold_path = tmp_path / "gold.json"
    manifest_path = tmp_path / "manifest.json"
    prediction_path.write_text(json.dumps(prediction), encoding="utf-8")
    gold_path.write_text(json.dumps({
        "text": "Hello", "block_types": ["paragraph"], "heading_levels": [],
        "cross_page_merges": 0, "cells": [], "cell_spans": [],
        "critical_spans": [], "critical_conflicts": [],
    }), encoding="utf-8")
    manifest_path.write_text(json.dumps({"documents": [{
        "id": "perfect", "document_type": "unit", "gold": "gold.json",
        "prediction": "prediction.json",
    }]}), encoding="utf-8")
    report = evaluate_manifest(manifest_path, tmp_path / "report.json")
    assert report["aggregate"]["cer"] == 0
    assert report["aggregate"]["block_type_f1"] == 1
    assert enforce_regression_thresholds(report, {"block_type_f1": 1.0}) == []
