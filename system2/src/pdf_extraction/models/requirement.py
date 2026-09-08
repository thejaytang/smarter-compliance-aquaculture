from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import Field, model_validator

from .document import BoundingBox, ResolutionStatus, StrictModel


class RequirementStatus(str, Enum):
    ACCEPTED = "accepted"
    REVIEW_REQUIRED = "review_required"
    ABSTAIN = "abstain"


class RequirementSourceRegion(StrictModel):
    """Inline, source-preserving provenance for one part of a Requirement."""

    segment_id: str
    page_index: int = Field(ge=0)
    page_number: int | None = Field(default=None, ge=1)
    bbox: BoundingBox
    role: Literal[
        "criterion_heading",
        "continuation_anchor",
        "requirement_id",
        "indicator_text",
        "requirement_value",
        "normative_text",
        "applicability",
        "requirement_continuation",
        "client_action",
        "auditor_action",
        "instruction",
        "footnote",
        "other",
    ]
    source_text: str | None = None
    native_text: str | None = None
    ocr_text: str | None = None
    review_text: str | None = None
    resolved_text: str | None = None
    resolution_status: ResolutionStatus = ResolutionStatus.RESOLVED
    requires_human_review: bool = False
    native_object_refs: list[str] = Field(default_factory=list)
    ocr_word_ids: list[str] = Field(default_factory=list)


class RequirementTextAnchor(StrictModel):
    """Exact character range inside one Requirement source region."""

    source_segment_id: str = Field(min_length=1)
    start_char: int = Field(ge=0)
    end_char: int = Field(ge=1)
    text: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_character_range(self) -> "RequirementTextAnchor":
        if self.end_char <= self.start_char:
            raise ValueError("end_char must be greater than start_char")
        return self


class RequirementScopeRef(StrictModel):
    """Controlled semantic target backed by source-exact anchors."""

    kind: Literal[
        "source_span", "field", "clause", "requirement", "action", "footnote"
    ]
    target: str = Field(
        min_length=1,
        pattern=(
            r"^(indicator_text|requirement_value|applicability|normative_text|"
            r"clause:.+|requirement:.+|client:.+|auditor:.+|footnote:.+)$"
        ),
    )
    anchors: list[RequirementTextAnchor] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_kind_target_pair(self) -> "RequirementScopeRef":
        prefixes = {
            "field": ("indicator_text", "requirement_value", "applicability", "normative_text"),
            "clause": ("clause:",),
            "requirement": ("requirement:",),
            "action": ("client:", "auditor:"),
            "footnote": ("footnote:",),
        }
        allowed = prefixes.get(self.kind)
        if allowed is not None and not self.target.startswith(allowed):
            raise ValueError(f"{self.kind} scope cannot target {self.target}")
        return self


class RequirementTextEvidence(StrictModel):
    """Normalized display text with exact source evidence."""

    text: str = Field(min_length=1)
    basis: Literal["explicit", "inferred_from_source_structure"]
    source_segment_ids: list[str] = Field(min_length=1)
    anchors: list[RequirementTextAnchor] = Field(min_length=1)


class RequirementModality(StrictModel):
    token: str
    type: Literal[
        "obligation", "prohibition", "permission", "recommendation", "other"
    ]
    scope: str
    scope_ref: RequirementScopeRef | None = None


class RequirementScopedText(StrictModel):
    text: str
    applies_to: str
    scope_ref: RequirementScopeRef | None = None


class RequirementClause(StrictModel):
    clause_id: str
    parent_clause_id: str | None = None
    marker: str | None = None
    text: str
    joins_next: Literal["and", "or"] | None = None


class RequirementThreshold(StrictModel):
    raw_text: str
    operator: Literal["lt", "lte", "eq", "gte", "gt", "range", "other"] | None
    normalized_value: float | str | None
    unit: str | None
    applies_to: str
    basis: Literal["explicit", "inferred_from_source_structure"]
    source_segment_ids: list[str] = Field(default_factory=list)
    scope_ref: RequirementScopeRef | None = None


class RequirementCrossReference(StrictModel):
    text: str
    target: str
    type: Literal[
        "internal_exact", "internal_generic", "external_document", "defined_term"
    ]


class RequirementFootnoteReference(StrictModel):
    marker: str
    text: str
    link_type: Literal["direct", "inherited", "semantic", "anomalous"]
    source_segment_ids: list[str] = Field(default_factory=list)


class RequirementInstruction(StrictModel):
    marker: str | None = None
    text: str
    effect: Literal[
        "method", "condition", "exception", "exemption", "procedure", "other"
    ]
    source_segment_ids: list[str] = Field(default_factory=list)


class RequirementAction(StrictModel):
    marker: str | None = None
    text: str
    source_segment_ids: list[str] = Field(default_factory=list)


class RequirementSemanticFragment(StrictModel):
    """One source-backed, role-aware input fragment for semantic analysis."""

    role: Literal[
        "indicator_text",
        "requirement_value",
        "normative_text",
        "requirement_continuation",
        "applicability",
        "footnote",
    ]
    text: str = Field(min_length=1)
    source_segment_ids: list[str] = Field(min_length=1)


class RequirementSemanticInput(StrictModel):
    """Deterministic derived view; this is not additional source evidence."""

    generator_version: str = Field(min_length=1)
    core_fragments: list[RequirementSemanticFragment] = Field(default_factory=list)
    qualifier_fragments: list[RequirementSemanticFragment] = Field(default_factory=list)
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class Requirement(StrictModel):
    """Canonical Requirement model extended by Document schema v1.4."""

    requirement_id: str
    status: RequirementStatus = RequirementStatus.REVIEW_REQUIRED
    requirement_form: Literal[
        "normative_indicator",
        "indicator_plus_value",
        "requirement_table",
        "audit_matrix",
        "prose_clause",
        "appendix_procedure",
    ]
    source_document: str | None = None
    source_authority: str | None = None
    criterion_path: list[str] = Field(default_factory=list)
    language: Literal["en", "no"]
    indicator_text: str | None = None
    requirement_value: str | None = None
    normative_text: str
    normative_subjects: list[str] = Field(default_factory=list)
    applicability: list[str] = Field(default_factory=list)
    normative_subject_evidence: list[RequirementTextEvidence] = Field(
        default_factory=list
    )
    applicability_evidence: list[RequirementTextEvidence] = Field(
        default_factory=list
    )
    modalities: list[RequirementModality] = Field(default_factory=list)
    negations: list[RequirementScopedText] = Field(default_factory=list)
    clauses: list[RequirementClause] = Field(default_factory=list)
    conditions: list[RequirementScopedText] = Field(default_factory=list)
    exceptions: list[RequirementScopedText] = Field(default_factory=list)
    exemptions: list[RequirementScopedText] = Field(default_factory=list)
    thresholds: list[RequirementThreshold] = Field(default_factory=list)
    dates: list[RequirementScopedText] = Field(default_factory=list)
    cross_references: list[RequirementCrossReference] = Field(default_factory=list)
    footnote_refs: list[RequirementFootnoteReference] = Field(default_factory=list)
    associated_instructions: list[RequirementInstruction] = Field(default_factory=list)
    client_actions: list[RequirementAction] = Field(default_factory=list)
    auditor_actions: list[RequirementAction] = Field(default_factory=list)
    related_context_ids: list[str] = Field(default_factory=list)
    source_segments: list[RequirementSourceRegion] = Field(default_factory=list)
    semantic_input: RequirementSemanticInput | None = None
    source_anomalies: list[str] = Field(default_factory=list)
    validation_flags: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0, le=1)
