from pdf_extraction.config import VerificationSettings
from pdf_extraction.models import (
    Block,
    BlockType,
    BoundingBox,
    EvidenceSpan,
    ResolutionStatus,
)
from pdf_extraction.verification import route_evidence_spans


def _span(*, confidence: float, span_id: str = "span_001") -> EvidenceSpan:
    return EvidenceSpan(
        id=span_id,
        block_id="block_001",
        segment_id="segment_001",
        page_index=0,
        bbox=BoundingBox(x0=1, y0=1, x1=10, y1=10),
        native_text="shall",
        resolved_text="shall",
        criticality="modality",
        resolution_status=ResolutionStatus.RESOLVED,
        confidence=confidence,
        native_object_refs=["native_001"],
    )


def test_low_confidence_resolved_span_still_routes_to_human() -> None:
    span = _span(confidence=0.98)
    block = Block(id="block_001", type=BlockType.PARAGRAPH)

    result = route_evidence_spans(
        {span.id: span},
        {block.id: block},
        VerificationSettings(depth="internal"),
    )

    assert result.automatic_coverage == 0
    assert span.resolution_status == ResolutionStatus.RESOLVED
    assert span.requires_human_review is True
    assert span.review_threshold == 0.99
    assert span.review_reason_codes == ["confidence_below_threshold"]
    assert result.review_items[0].target_id == span.id
    assert block.quality.requires_review is True


def test_high_confidence_span_is_automatic_at_source_depth() -> None:
    span = _span(confidence=0.995)
    block = Block(id="block_001", type=BlockType.PARAGRAPH)

    result = route_evidence_spans(
        {span.id: span},
        {block.id: block},
        VerificationSettings(depth="source"),
    )

    assert result.automatic_coverage == 1
    assert span.requires_human_review is False
    assert result.review_items == []


def test_strong_depth_does_not_auto_accept_without_independent_path() -> None:
    span = _span(confidence=0.995)
    block = Block(id="block_001", type=BlockType.PARAGRAPH)

    result = route_evidence_spans(
        {span.id: span},
        {block.id: block},
        VerificationSettings(depth="strong"),
    )

    assert result.automatic_coverage == 0
    assert span.requires_human_review is True
    assert span.review_reason_codes == [
        "independent_evidence_missing",
        "evidence_path_redundancy_missing",
    ]
