"""Contracts for fidelity verification and human-review routing."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class VerificationDepth(str, Enum):
    """Machine evidence depth. Human review is orthogonal to this scale."""

    INTERNAL = "internal"
    SOURCE = "source"
    INDEPENDENT = "independent"
    STRONG = "strong"


class VerificationOutcome(str, Enum):
    PASS = "pass"
    REVIEW = "review"
    FAIL = "fail"


class ReviewDisposition(str, Enum):
    AUTO_ACCEPT = "auto_accept"
    HUMAN_REVIEW = "human_review"


class EvidencePathRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path_id: str
    kind: str
    source_refs: list[str] = Field(default_factory=list)
    independent_from_generation: bool = False


class AtomicAssessment(BaseModel):
    """One machine judgment that can be accepted or routed to a human."""

    model_config = ConfigDict(extra="forbid")

    assessment_id: str
    target_id: str
    field_name: str
    criticality: str = "general"
    confidence: float | None = Field(default=None, ge=0, le=1)
    review_threshold: float | None = Field(default=None, ge=0, le=1)
    evidence_paths: list[EvidencePathRecord] = Field(default_factory=list)
    provenance_complete: bool = True
    disagreement: bool = False
    disposition: ReviewDisposition = ReviewDisposition.HUMAN_REVIEW
    reason_codes: list[str] = Field(default_factory=list)


class VerificationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    depth: VerificationDepth
    outcome: VerificationOutcome
    assessments: list[AtomicAssessment] = Field(default_factory=list)
    automatic_coverage: float = Field(ge=0, le=1)
    human_review_count: int = Field(ge=0)


__all__ = [
    "AtomicAssessment",
    "EvidencePathRecord",
    "ReviewDisposition",
    "VerificationDepth",
    "VerificationOutcome",
    "VerificationReport",
]
