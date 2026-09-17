from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from pdf_extraction.models import (
    Block,
    BlockType,
    BoundingBox,
    Conflict,
    Document,
    DocumentQuality,
    DocumentStatus,
    Page,
    ProcessingMetadata,
    Resolution,
    Segment,
    SourceMetadata,
    TextContent,
)
from pdf_extraction.validate import structural_fingerprint, validate_document
from pdf_extraction.pipeline import _ensure_critical_conflicts_reviewable


def make_document() -> Document:
    root = Block(id="document", type=BlockType.DOCUMENT, children=["section"])
    section = Block(
        id="section",
        type=BlockType.SECTION,
        parent_id="document",
        children=["paragraph"],
    )
    paragraph = Block(
        id="paragraph",
        type=BlockType.PARAGRAPH,
        parent_id="section",
        segments=[
            Segment(
                id="segment-paragraph",
                page_index=0,
                bbox=BoundingBox(x0=10, y0=10, x1=100, y1=30),
                crop_ref="run-a/crops/paragraph.png",
            )
        ],
        content=TextContent(
            ocr_text="Hello",
            resolved_text="Hello",
            resolution=Resolution(selected_source="ocr", reason="native_empty", confidence=0.9),
        ),
    )
    return Document(
        document_id="sha256:test",
        source=SourceMetadata(
            file_name="test.pdf",
            file_hash="test",
            file_size=1,
            page_count=1,
            encrypted=False,
        ),
        processing=ProcessingMetadata(
            started_at="2026-01-01T00:00:00Z",
            completed_at="2026-01-01T00:00:01Z",
            pipeline_version="test",
            config_hash="config",
        ),
        pages=[
            Page(
                page_index=0,
                width=612,
                height=792,
                rotation=0,
                image_ref="run-a/pages/page-0001.png",
                native_text_coverage=0,
                image_coverage=1,
                page_kind="scanned",
                block_ids=["paragraph"],
            )
        ],
        root_block_ids=["document"],
        blocks={"document": root, "section": section, "paragraph": paragraph},
        quality=DocumentQuality(
            status=DocumentStatus.ACCEPTED,
            input_page_count=1,
            processed_page_count=1,
        ),
    )


def test_link_flag_must_match_links() -> None:
    with pytest.raises(ValidationError):
        Block(id="bad", type=BlockType.PARAGRAPH, has_linked_content=True)


def test_validator_accepts_valid_tree_and_rejects_bad_bbox() -> None:
    document = make_document()
    assert validate_document(document) == []
    document.blocks["paragraph"].segments[0].bbox = BoundingBox(
        x0=10, y0=10, x1=700, y1=30
    )
    assert "segment bbox out of page bounds" in "\n".join(validate_document(document))


def test_critical_conflict_cannot_be_silently_accepted() -> None:
    document = make_document()
    document.conflicts.append(
        Conflict(
            id="conflict-1",
            block_id="paragraph",
            native_value="5 mg",
            ocr_value="8 mg",
            conflict_type="critical_text_conflict",
            severity="critical",
            status="review_required",
            evidence_segment_ids=["segment-paragraph"],
        )
    )
    assert "critical conflict missing from review queue" in "\n".join(
        validate_document(document)
    )


def test_critical_conflict_is_routed_to_owning_block_review() -> None:
    document = make_document()
    document.conflicts.append(
        Conflict(
            id="conflict-1",
            block_id="paragraph",
            native_value="5 mg",
            ocr_value="8 mg",
            conflict_type="unit_conflict",
            severity="critical",
            status="review_required",
            evidence_segment_ids=["segment-paragraph"],
        )
    )

    _ensure_critical_conflicts_reviewable(
        document.blocks, document.conflicts, document.review_items
    )
    document.review_queue = [item.target_id for item in document.review_items]

    assert document.review_queue == ["paragraph"]
    assert document.blocks["paragraph"].quality.requires_review is True
    assert validate_document(document) == []


def test_structural_fingerprint_ignores_run_metadata_and_output_root() -> None:
    left = make_document()
    right = deepcopy(left)
    right.processing.started_at = "2030-01-01T00:00:00Z"
    right.processing.completed_at = "2030-01-01T00:00:05Z"
    right.pages[0].image_ref = "run-b/pages/page-0001.png"
    right.blocks["paragraph"].segments[0].crop_ref = "run-b/crops/paragraph.png"
    assert structural_fingerprint(left) == structural_fingerprint(right)
    right.blocks["paragraph"].content.resolved_text = "Changed"
    assert structural_fingerprint(left) != structural_fingerprint(right)
