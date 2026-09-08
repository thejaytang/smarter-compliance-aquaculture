"""Deterministic routing from machine confidence to targeted human review."""

from __future__ import annotations

from ..config import VerificationSettings
from ..contracts.verification import AtomicAssessment, ReviewDisposition


def route_atomic_assessment(
    assessment: AtomicAssessment,
    settings: VerificationSettings,
) -> AtomicAssessment:
    """Apply review policy without changing the underlying machine judgment."""

    threshold = settings.criticality_thresholds.get(
        assessment.criticality,
        settings.default_review_threshold,
    )
    reasons: list[str] = []
    if assessment.confidence is None:
        if settings.require_confidence:
            reasons.append("confidence_missing")
    elif assessment.confidence < threshold:
        reasons.append("confidence_below_threshold")
    if assessment.disagreement and settings.force_review_on_disagreement:
        reasons.append("evidence_disagreement")
    if (
        not assessment.provenance_complete
        and settings.force_review_on_missing_provenance
    ):
        reasons.append("provenance_incomplete")
    if settings.depth in {"source", "independent", "strong"}:
        if not assessment.evidence_paths:
            reasons.append("source_evidence_missing")
    if settings.depth in {"independent", "strong"}:
        if not any(
            path.independent_from_generation
            for path in assessment.evidence_paths
        ):
            reasons.append("independent_evidence_missing")
    if settings.depth == "strong" and len(assessment.evidence_paths) < 2:
        reasons.append("evidence_path_redundancy_missing")
    return assessment.model_copy(update={
        "review_threshold": threshold,
        "disposition": (
            ReviewDisposition.HUMAN_REVIEW
            if reasons
            else ReviewDisposition.AUTO_ACCEPT
        ),
        "reason_codes": list(dict.fromkeys([*assessment.reason_codes, *reasons])),
    })


__all__ = ["route_atomic_assessment"]
