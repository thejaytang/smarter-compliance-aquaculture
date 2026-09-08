"""Verification policies and human-review routing.

Verification depth controls machine evidence requirements. Human review remains
available at every depth and is triggered per atomic assessment.
"""

from ..contracts.verification import (
    AtomicAssessment,
    EvidencePathRecord,
    ReviewDisposition,
    VerificationDepth,
    VerificationOutcome,
    VerificationReport,
)
from .review_router import route_atomic_assessment
from .conflict_review import ensure_critical_conflicts_reviewable
from .evidence_routing import (
    EvidenceRoutingResult,
    assessment_from_span,
    route_evidence_spans,
)

__all__ = [
    "AtomicAssessment",
    "EvidencePathRecord",
    "ReviewDisposition",
    "VerificationDepth",
    "VerificationOutcome",
    "VerificationReport",
    "EvidenceRoutingResult",
    "assessment_from_span",
    "ensure_critical_conflicts_reviewable",
    "route_evidence_spans",
    "route_atomic_assessment",
]
