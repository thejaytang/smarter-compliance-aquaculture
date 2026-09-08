"""Production routing for atomic evidence-span judgments."""

from __future__ import annotations

from dataclasses import dataclass

from ..config import VerificationSettings
from ..contracts.verification import (
    AtomicAssessment,
    EvidencePathRecord,
    ReviewDisposition,
)
from ..models import Block, EvidenceSpan, ResolutionStatus, ReviewItem
from .review_router import route_atomic_assessment


@dataclass(frozen=True)
class EvidenceRoutingResult:
    assessments: list[AtomicAssessment]
    review_items: list[ReviewItem]

    @property
    def automatic_coverage(self) -> float:
        if not self.assessments:
            return 1.0
        accepted = sum(
            item.disposition == ReviewDisposition.AUTO_ACCEPT
            for item in self.assessments
        )
        return accepted / len(self.assessments)


def _evidence_paths(span: EvidenceSpan) -> list[EvidencePathRecord]:
    paths: list[EvidencePathRecord] = []
    if span.native_object_refs:
        paths.append(EvidencePathRecord(
            path_id=f"native:{span.id}",
            kind="native_object",
            source_refs=span.native_object_refs,
        ))
    if span.ocr_word_ids:
        paths.append(EvidencePathRecord(
            path_id=f"ocr:{span.id}",
            kind="raster_ocr",
            source_refs=span.ocr_word_ids,
        ))
    return paths


def assessment_from_span(
    span: EvidenceSpan,
    settings: VerificationSettings,
) -> AtomicAssessment:
    paths = _evidence_paths(span)
    disagreement = (
        span.resolution_status == ResolutionStatus.AMBIGUOUS
        or (
            span.native_text is not None
            and span.ocr_text is not None
            and span.native_text.casefold().replace(",", ".")
            != span.ocr_text.casefold().replace(",", ".")
        )
    )
    assessment = AtomicAssessment(
        assessment_id=f"assessment:{span.id}",
        target_id=span.id,
        field_name=span.criticality,
        criticality=span.criticality,
        confidence=span.confidence,
        evidence_paths=paths,
        provenance_complete=bool(span.segment_id and paths),
        disagreement=disagreement,
    )
    return route_atomic_assessment(assessment, settings)


def route_evidence_spans(
    spans: dict[str, EvidenceSpan],
    blocks: dict[str, Block],
    settings: VerificationSettings,
) -> EvidenceRoutingResult:
    assessments: list[AtomicAssessment] = []
    review_items: list[ReviewItem] = []
    for span in spans.values():
        assessment = assessment_from_span(span, settings)
        assessments.append(assessment)
        span.review_threshold = assessment.review_threshold
        span.review_reason_codes = assessment.reason_codes
        span.evidence_path_ids = [path.path_id for path in assessment.evidence_paths]
        span.requires_human_review = (
            assessment.disposition == ReviewDisposition.HUMAN_REVIEW
        )
        if not span.requires_human_review:
            continue
        block = blocks.get(span.block_id)
        if block is not None:
            block.quality.requires_review = True
            if "atomic_verification_review" not in block.quality.issues:
                block.quality.issues.append("atomic_verification_review")
        review_items.append(ReviewItem(
            id=f"review_atomic_{span.id}",
            target_id=span.id,
            reason="atomic_verification:" + ",".join(assessment.reason_codes),
            severity="critical",
            candidate_action="human_confirm_evidence_span",
            confidence=span.confidence,
            evidence_segment_ids=[span.segment_id],
        ))
    return EvidenceRoutingResult(
        assessments=assessments,
        review_items=review_items,
    )


__all__ = [
    "EvidenceRoutingResult",
    "assessment_from_span",
    "route_evidence_spans",
]
