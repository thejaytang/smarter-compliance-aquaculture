from __future__ import annotations

from pathlib import Path

from PIL import Image

from pdf_extraction.assemble.content_linker import enrich_content_links
from pdf_extraction.config import LinkSettings
from pdf_extraction.delivery.exporters.rag import build_rag_chunks
from pdf_extraction.layout.aligner import native_text_for_region
from pdf_extraction.layout.marginals import detect_repeating_marginals
from pdf_extraction.models import (
    Block, BlockType, BoundingBox, Document, DocumentQuality, DocumentStatus,
    Page, ProcessingMetadata, ProcessingStatus, Resolution, Segment,
    Requirement, RequirementAction, RequirementSourceRegion, RequirementStatus,
    SourceMetadata, TableCell, TableData, TextContent,
)
from pdf_extraction.pipeline import _clean_owned_collision_copies, _clean_owned_output
from pdf_extraction.domains.regulatory import extract_regulatory_ir
from pdf_extraction.types import LayoutRegion, NativeObject, NativePage, PixelBox, RenderedPage


def _content(value: str) -> TextContent:
    return TextContent(
        native_text=value,
        resolved_text=value,
        resolution=Resolution(selected_source="native", reason="test", confidence=1),
    )


def _document(blocks: dict[str, Block]) -> Document:
    return Document(
        document_id="sha256:test",
        source=SourceMetadata(
            file_name="test.pdf", file_hash="test", file_size=1,
            page_count=1, encrypted=False,
        ),
        processing=ProcessingMetadata(
            pipeline_version="test", config_hash="test", status=ProcessingStatus.ACCEPTED,
        ),
        pages=[Page(
            page_index=0, width=600, height=800, rotation=0, image_ref="p.png",
            native_text_coverage=1, image_coverage=0, page_kind="born_digital",
        )],
        root_block_ids=["document"], blocks=blocks,
        quality=DocumentQuality(
            status=DocumentStatus.ACCEPTED, input_page_count=1, processed_page_count=1,
        ),
    )


def test_marginal_learning_keeps_distinct_top_templates_separate() -> None:
    pages = []
    for page_index in range(3):
        lines = [NativeObject(
            f"header-{page_index}", "Publisher", (450, 30, 540, 42), object_type="text_line"
        )]
        if page_index == 1:
            lines.append(NativeObject(
                "body", "The operator may sell products as non-certified.",
                (55, 65, 500, 82), object_type="text_line",
            ))
        pages.append(NativePage(page_index, 600, 800, text_lines=lines))
    annotations = detect_repeating_marginals(pages)
    assert [item.text for item in annotations[1]] == ["Publisher"]


def test_native_superscript_becomes_explicit_footnote_anchor(tmp_path: Path) -> None:
    image = tmp_path / "page.png"
    Image.new("RGB", (600, 800), "white").save(image)
    page = RenderedPage(0, image, 600, 800, 600, 800, 0)
    words = [
        NativeObject("w1", "many", (100, 100, 130, 112)),
        NativeObject("w2", "forms", (133, 100, 170, 112)),
        NativeObject("w3", "1", (171, 100, 174, 107)),
        NativeObject("w4", ".", (175, 100, 177, 112)),
    ]
    text, _ = native_text_for_region(
        LayoutRegion("r", "paragraph", PixelBox(90, 90, 190, 120), 1), page, words
    )
    assert text == "many forms[^1]."


def test_footnote_links_scan_table_cells_and_ignore_page_numbers() -> None:
    table = Block(
        id="table", type=BlockType.TABLE, parent_id="section",
        segments=[Segment(id="seg-table", page_index=0, bbox=BoundingBox(x0=1, y0=1, x1=500, y1=200))],
        table=TableData(row_count=1, column_count=1, parser_backend="test", cells=[
            TableCell(
                id="cell", row=0, column=0, bbox=BoundingBox(x0=1, y0=1, x1=500, y1=200),
                content=_content("The operator shall comply[^1]."),
            )
        ]),
    )
    footnote = Block(id="fn", type=BlockType.FOOTNOTE, content=_content("1 Definition."))
    header = Block(id="header", type=BlockType.HEADER, content=_content("Page 1 of 511"))
    blocks = {item.id: item for item in (table, footnote, header)}
    enrich_content_links(blocks, LinkSettings())
    assert [(link.target_id, link.relation) for link in blocks["table"].content_links] == [
        ("fn", "footnote_reference")
    ]
    assert not header.content_links


def test_figure_title_does_not_become_appendix_target() -> None:
    paragraph = Block(
        id="paragraph", type=BlockType.PARAGRAPH,
        content=_content("Conformance follows Appendix 14."),
    )
    figure = Block(
        id="figure", type=BlockType.FIGURE,
        index="Diagram text mentioning Appendix 14",
    )
    blocks = {item.id: item for item in (paragraph, figure)}
    enrich_content_links(blocks, LinkSettings())
    assert not blocks["paragraph"].content_links


def test_regulatory_ir_extracts_formal_requirement_table() -> None:
    cells = [
        TableCell(id="h1", row=0, column=0, bbox=BoundingBox(x0=1, y0=1, x1=100, y1=20), content=_content("Indicator:"), is_header=True),
        TableCell(id="h2", row=0, column=1, bbox=BoundingBox(x0=100, y0=1, x1=500, y1=20), content=_content("Requirement:"), is_header=True),
        TableCell(id="n", row=1, column=0, bbox=BoundingBox(x0=1, y0=20, x1=100, y1=80), content=_content("1.2.1")),
        TableCell(id="r", row=1, column=1, bbox=BoundingBox(x0=100, y0=20, x1=500, y1=80), content=_content("The UoC shall maintain records.")),
    ]
    root = Block(id="document", type=BlockType.DOCUMENT, children=["section"])
    section = Block(id="section", type=BlockType.SECTION, parent_id="document", children=["table"])
    table = Block(
        id="table", type=BlockType.TABLE, parent_id="section",
        segments=[Segment(id="seg", page_index=0, bbox=BoundingBox(x0=1, y0=1, x1=500, y1=80))],
        table=TableData(row_count=2, column_count=2, cells=cells, parser_backend="test"),
    )
    ir = extract_regulatory_ir(_document({item.id: item for item in (root, section, table)}))
    assert ir.formal_requirement_ids == ["1.2.1"]
    assert ir.missing_requirement_ids == []
    assert ir.statements[0].requirement_id == "1.2.1"
    assert ir.statements[0].source_block_ids == ["table"]


def test_regulatory_ir_accepts_indicator_side_label_after_number() -> None:
    cells = [
        TableCell(id="h1", row=0, column=0, bbox=BoundingBox(x0=1, y0=1, x1=100, y1=20), content=_content("Indicator:"), is_header=True),
        TableCell(id="h2", row=0, column=1, bbox=BoundingBox(x0=100, y0=1, x1=500, y1=20), content=_content("Requirement:"), is_header=True),
        TableCell(id="n", row=1, column=0, bbox=BoundingBox(x0=1, y0=20, x1=100, y1=80), content=_content("2.6.2\nReporting")),
        TableCell(id="r", row=1, column=1, bbox=BoundingBox(x0=100, y0=20, x1=500, y1=80), content=_content("The UoC shall report annually.")),
    ]
    root = Block(id="document", type=BlockType.DOCUMENT, children=["section"])
    section = Block(id="section", type=BlockType.SECTION, parent_id="document", children=["table"])
    table = Block(
        id="table", type=BlockType.TABLE, parent_id="section",
        segments=[Segment(id="seg", page_index=0, bbox=BoundingBox(x0=1, y0=1, x1=500, y1=80))],
        table=TableData(row_count=2, column_count=2, cells=cells, parser_backend="test"),
    )
    ir = extract_regulatory_ir(_document({item.id: item for item in (root, section, table)}))
    assert ir.formal_requirement_ids == ["2.6.2"]
    assert ir.missing_requirement_ids == []


def test_regulatory_ir_v2_uses_canonical_requirements_and_ignores_guidance_modal() -> None:
    guidance = Block(
        id="guidance",
        type=BlockType.PARAGRAPH,
        segments=[Segment(
            id="seg-guidance",
            page_index=0,
            bbox=BoundingBox(x0=20, y0=100, x1=500, y1=130),
        )],
        content=_content("Auditors shall inspect the evidence."),
    )
    document = _document({"guidance": guidance})
    document.requirements = [Requirement(
        requirement_id="1.2.1",
        status=RequirementStatus.ACCEPTED,
        requirement_form="normative_indicator",
        language="en",
        indicator_text="The UoC shall maintain records.",
        normative_text="The UoC shall maintain records.",
        client_actions=[RequirementAction(
            marker="a",
            text="The client shall retain a copy.",
            source_segment_ids=["req-client"],
        )],
        source_segments=[
            RequirementSourceRegion(
                segment_id="req-id",
                page_index=0,
                bbox=BoundingBox(x0=20, y0=20, x1=70, y1=35),
                role="requirement_id",
                source_text="1.2.1",
                native_text="1.2.1",
                resolved_text="1.2.1",
                native_object_refs=["native-id"],
            ),
            RequirementSourceRegion(
                segment_id="req-text",
                page_index=0,
                bbox=BoundingBox(x0=90, y0=20, x1=500, y1=50),
                role="normative_text",
                source_text="The UoC shall maintain records.",
                native_text="The UoC shall maintain records.",
                resolved_text="The UoC shall maintain records.",
                native_object_refs=["native-text"],
            ),
            RequirementSourceRegion(
                segment_id="req-client",
                page_index=0,
                bbox=BoundingBox(x0=90, y0=55, x1=500, y1=80),
                role="client_action",
                source_text="The client shall retain a copy.",
                native_text="The client shall retain a copy.",
                resolved_text="The client shall retain a copy.",
                native_object_refs=["native-client"],
            ),
        ],
        confidence=0.99,
    )]

    ir = extract_regulatory_ir(document)

    assert ir.schema_version == "2.0"
    assert [item.requirement_id for item in ir.requirements] == ["1.2.1"]
    assert ir.formal_requirement_ids == ["1.2.1"]
    assert len(ir.statements) == 1
    assert ir.statements[0].requirement_id == "1.2.1"
    assert ir.statements[0].source_block_ids == []
    assert ir.statements[0].source_segment_ids == ["req-id", "req-text"]


def test_rag_uses_tree_order_and_excludes_marginals_and_empty_figures() -> None:
    root = Block(id="document", type=BlockType.DOCUMENT, children=["section", "header"])
    section = Block(id="section", type=BlockType.SECTION, parent_id="document", children=["second", "first", "figure"])
    second = Block(id="second", type=BlockType.PARAGRAPH, parent_id="section", content=_content("Second in tree."))
    first = Block(id="first", type=BlockType.PARAGRAPH, parent_id="section", content=_content("First by local number."))
    figure = Block(id="figure", type=BlockType.FIGURE, parent_id="section")
    header = Block(id="header", type=BlockType.HEADER, parent_id="document", content=_content("Publisher"))
    chunks = build_rag_chunks(_document({item.id: item for item in (root, section, second, first, figure, header)}))
    assert chunks[0]["block_ids"] == ["second", "first"]
    assert "Publisher" not in chunks[0]["text"]
    assert all(chunk["text"] for chunk in chunks)


def test_output_cleanup_removes_only_parser_owned_artifacts(tmp_path: Path) -> None:
    (tmp_path / "canonical 2.json").write_text("old")
    (tmp_path / "crops 3").mkdir()
    (tmp_path / "keep-me.txt").write_text("user")
    _clean_owned_output(tmp_path)
    assert not (tmp_path / "canonical 2.json").exists()
    assert not (tmp_path / "crops 3").exists()
    assert (tmp_path / "keep-me.txt").read_text() == "user"

    (tmp_path / "canonical.json").write_text("current")
    (tmp_path / "canonical 4.json").write_text("copy")
    crops = tmp_path / "crops"
    crops.mkdir()
    (crops / "block.png").write_text("current")
    (crops / "block 2.png").write_text("copy")
    _clean_owned_collision_copies(tmp_path)
    assert (tmp_path / "canonical.json").read_text() == "current"
    assert not (tmp_path / "canonical 4.json").exists()
    assert (crops / "block.png").read_text() == "current"
    assert not (crops / "block 2.png").exists()
