from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
import hashlib
import json
import re
from typing import Iterable, Literal

from ...models import (
    BoundingBox,
    Requirement,
    RequirementAction,
    RequirementCrossReference,
    RequirementFootnoteReference,
    RequirementInstruction,
    RequirementModality,
    RequirementSemanticFragment,
    RequirementSemanticInput,
    RequirementScopeRef,
    RequirementScopedText,
    RequirementSourceRegion,
    RequirementStatus,
    RequirementTextAnchor,
    RequirementTextEvidence,
    RequirementThreshold,
    ResolutionStatus,
)
from .clauses import build_requirement_clauses
from .native_assembler import NativeRequirement, RequirementSourceSpan, TemplateFamily
from .semantics import (
    ContextCandidate,
    ModalityCandidate,
    NegationCandidate,
    RequirementSemanticAnalysis,
    SourceSpan,
    analyze_requirement_semantics,
    source_field_value_bounds,
)


Language = Literal["en", "no"]


_FAMILY_TO_FORM = {
    TemplateFamily.SINGLE_COLUMN_INDICATORS: "normative_indicator",
    TemplateFamily.LEGACY_INDICATOR_VALUE: "indicator_plus_value",
    TemplateFamily.AUDIT_MATRIX: "audit_matrix",
    TemplateFamily.ID_NORMATIVE_WITH_CONTEXT: "requirement_table",
}
_SOURCE_ROLES = {
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
}
_NORMATIVE_ROLES = {
    "indicator_text",
    "requirement_value",
    "normative_text",
    "requirement_continuation",
}
_SEMANTIC_SCOPE_ROLES = _NORMATIVE_ROLES | {"applicability"}
_ATTACHED_FOOTNOTE_CLEAN_ROLES = {
    "indicator_text",
    "normative_text",
    "requirement_continuation",
}
_SOURCE_FIELD_ROLE_RE = re.compile(
    r"(?im)^(?P<label>Indicator|Requirement|Applicability)\s*:\s*"
)
_ACTION_RE = re.compile(r"^([A-Za-z])\.\s*(.+)$", re.DOTALL)
_SPACE_RE = re.compile(r"\s+")
_SAFE_ID_RE = re.compile(r"[^a-z0-9]+")
_SEMANTIC_INPUT_VERSION = "role-aware-semantic-input-v1"
_EXPLICIT_ZERO_VALUE_RE = re.compile(r"^0(?:\s*\(\s*zero\s*\))?$", re.IGNORECASE)
_COUNT_INDICATOR_RE = re.compile(
    r"^Number\s+of\s+(?P<unit>[A-Za-z][A-Za-z-]*)\b(?P<scope>.*)$",
    re.IGNORECASE,
)
_BRACKET_MARKER_RE = re.compile(r"\s*\[\d+\]")
_PASSIVE_USE_SCOPE_RE = re.compile(
    r"\bwhen\s+(?P<object>.+?)\s+(?:was|were|is|are)\s+used\b",
    re.IGNORECASE,
)
_AUDIT_SUBJECT_ROLES = {
    "indicator_text",
    "normative_text",
    "footnote",
}
_FARM_MEMBER_RE = re.compile(
    r"\bfarm\s+(?:manager|staff|worker|workers|employee|employees)\b",
    re.IGNORECASE,
)
_EXPLICIT_MODAL_SUBJECT_RE = re.compile(
    r"(?:^|[.;]\s+)(?:\[\d+\]\s*)?(?:Indicator\s*:\s*)?"
    r"(?P<subject>[A-Z][^.;:\n]{1,140}?)\s+"
    r"(?:shall|must|should|may|can|will)\b",
    re.IGNORECASE,
)
_GENERAL_REGULATED_SUBJECT_RE = re.compile(
    r"\b(?P<subject>(?:the\s+)?(?:UoC|farm|operator))\s+"
    r"(?=shall|must|should|may|can|will)\b",
    re.IGNORECASE,
)
_ENGLISH_MODAL_TOKEN_RE = re.compile(
    r"\b(?:shall|must|should|may|need(?:s)?\s+to)\b",
    re.IGNORECASE,
)


def canonicalize_native_requirement(
    native: NativeRequirement,
    *,
    source_document: str | None = None,
    source_authority: str | None = None,
    language: Language = "en",
    family_trusted: bool | None = None,
) -> Requirement:
    """Convert one geometry-assembled candidate into a Canonical Requirement.

    Conversion is deliberately fail-closed.  A candidate is accepted only when
    both its formal content and its inline native provenance are complete.
    Missing identity/content produces ``abstain``; incomplete provenance or
    action structure produces ``review_required``.
    """

    requirement_id = native.requirement_id.strip()
    normative_text = native.normative_text.strip()
    anomalies: list[str] = []
    flags: list[str] = [f"template_family:{native.family.value}"]

    regions = _source_regions(native, anomalies)
    region_ids_by_role: dict[str, list[str]] = defaultdict(list)
    for region in regions:
        region_ids_by_role[region.role].append(region.segment_id)

    client_actions = _actions(
        native.client_actions,
        expected_case="lower",
        source_segment_ids=region_ids_by_role["client_action"],
        anomaly_prefix="client_action",
        anomalies=anomalies,
    )
    auditor_actions = _actions(
        native.auditor_actions,
        expected_case="upper",
        source_segment_ids=region_ids_by_role["auditor_action"],
        anomaly_prefix="auditor_action",
        anomalies=anomalies,
    )
    if region_ids_by_role["client_action"] and not client_actions:
        anomalies.append("client_action_evidence_without_actions")
    if region_ids_by_role["auditor_action"] and not auditor_actions:
        anomalies.append("auditor_action_evidence_without_actions")
    _check_native_ref_role_separation(regions, anomalies)

    for issue in native.footnote_link_issues:
        _append_unique(anomalies, issue)
    footnote_refs = _footnote_refs(native, regions, anomalies)
    semantic_input = _semantic_input(
        native,
        regions=regions,
        footnote_refs=footnote_refs,
        anomalies=anomalies,
    )
    clause_structure = build_requirement_clauses(native, normative_text)
    for anomaly in clause_structure.anomalies:
        _append_unique(anomalies, anomaly)
    for flag in clause_structure.validation_flags:
        _append_unique(flags, flag)

    provenance_status = _status(native, regions, anomalies)
    if provenance_status is RequirementStatus.ACCEPTED:
        flags.append("native_requirement_provenance_complete")
        if native.client_actions or native.auditor_actions:
            flags.append("client_auditor_separation_checked")
    semantics = _canonical_semantics(
        normative_text,
        language=language,
        regions=regions,
        anomalies=anomalies,
        flags=flags,
    )
    semantics = _with_structured_requirement_value_negation(
        semantics,
        native=native,
        regions=regions,
        flags=flags,
    )
    applicability = (
        [native.applicability.strip()]
        if native.applicability and native.applicability.strip()
        else []
    )
    footnote_qualifiers = _with_footnote_qualifiers(
        semantics,
        native=native,
        footnote_refs=footnote_refs,
        regions=regions,
        normative_text=normative_text,
        language=language,
        applicability=applicability,
        anomalies=anomalies,
        flags=flags,
    )
    semantics = footnote_qualifiers.semantics
    applicability = footnote_qualifiers.applicability
    source_instructions, instruction_references = _source_instructions(
        native,
        regions,
    )
    semantics = replace(
        semantics,
        cross_references=_deduplicate_cross_references([
            *_footnote_marker_cross_references(
                footnote_refs,
                requirement_id=native.requirement_id,
            ),
            *semantics.cross_references,
            *_direct_requirement_cross_references(
                normative_text,
                requirement_id=native.requirement_id,
            ),
            *instruction_references,
        ]),
    )
    semantics = _with_structured_zero_threshold(
        semantics,
        native=native,
        regions=regions,
        flags=flags,
    )
    normative_subjects = _normative_subjects(
        native,
        regions=regions,
        flags=flags,
    )
    normative_subject_evidence = _text_evidence_items(
        normative_subjects,
        regions,
        preferred_roles=(
            "indicator_text",
            "footnote",
            "normative_text",
            "client_action",
            "auditor_action",
        ),
    )
    applicability_evidence = _text_evidence_items(
        applicability,
        regions,
        preferred_roles=("applicability", "footnote", "normative_text"),
    )
    status = provenance_status
    if semantics.requires_review and status is RequirementStatus.ACCEPTED:
        status = RequirementStatus.REVIEW_REQUIRED
    if clause_structure.requires_review and status is RequirementStatus.ACCEPTED:
        status = RequirementStatus.REVIEW_REQUIRED
    if status is not RequirementStatus.ACCEPTED:
        fail_closed = f"fail_closed:{status.value}"
        if fail_closed not in flags:
            flags.append(fail_closed)

    confidence = {
        RequirementStatus.ACCEPTED: 0.95,
        RequirementStatus.REVIEW_REQUIRED: 0.50,
        RequirementStatus.ABSTAIN: 0.0,
    }[status]
    requirement = Requirement(
        requirement_id=requirement_id,
        status=status,
        requirement_form=_FAMILY_TO_FORM[native.family],
        source_document=source_document,
        source_authority=source_authority,
        language=language,
        indicator_text=_optional_text(native.indicator_text),
        requirement_value=_optional_text(native.requirement_value),
        normative_text=normative_text,
        normative_subjects=normative_subjects,
        applicability=applicability,
        normative_subject_evidence=normative_subject_evidence,
        applicability_evidence=applicability_evidence,
        modalities=semantics.modalities,
        negations=semantics.negations,
        clauses=list(clause_structure.clauses),
        conditions=semantics.conditions,
        exceptions=semantics.exceptions,
        exemptions=semantics.exemptions,
        thresholds=semantics.thresholds,
        dates=semantics.dates,
        cross_references=semantics.cross_references,
        footnote_refs=footnote_refs,
        associated_instructions=_deduplicate_instructions([
            *footnote_qualifiers.associated_instructions,
            *source_instructions,
        ]),
        client_actions=client_actions,
        auditor_actions=auditor_actions,
        source_segments=regions,
        semantic_input=semantic_input,
        source_anomalies=anomalies,
        validation_flags=flags,
        confidence=confidence,
    )
    return apply_family_trust(requirement, trusted=family_trusted)


def _footnote_refs(
    native: NativeRequirement,
    regions: list[RequirementSourceRegion],
    anomalies: list[str],
) -> list[RequirementFootnoteReference]:
    """Map exact native markers to source-backed canonical references."""

    if native.footnote_link_candidates:
        return _candidate_footnote_refs(native, regions, anomalies)
    return _marker_footnote_refs(native, regions, anomalies)


def _candidate_footnote_refs(
    native: NativeRequirement,
    regions: list[RequirementSourceRegion],
    anomalies: list[str],
) -> list[RequirementFootnoteReference]:
    result: list[RequirementFootnoteReference] = []
    footnote_regions = [region for region in regions if region.role == "footnote"]
    order: list[tuple[str, tuple[str, ...]]] = []
    link_types: dict[
        tuple[str, tuple[str, ...]],
        Literal["direct", "inherited", "semantic"],
    ] = {}
    issues_by_identity: dict[tuple[str, tuple[str, ...]], list[str]] = defaultdict(list)
    for candidate in native.footnote_link_candidates:
        marker = candidate.marker.strip()
        definition_ids = tuple(candidate.definition_native_object_ids)
        identity = (marker, definition_ids)
        if identity not in link_types:
            order.append(identity)
            link_types[identity] = candidate.link_type
        elif link_types[identity] != candidate.link_type:
            _append_unique(
                issues_by_identity[identity],
                "footnote_candidate_link_type_conflict:"
                f"{marker}:{link_types[identity]},{candidate.link_type}",
            )
        for issue in candidate.issues:
            _append_unique(issues_by_identity[identity], issue)

    for marker, definition_ids in order:
        identity = (marker, definition_ids)
        candidate_issues = issues_by_identity[identity]
        # Conventional page-bottom definitions start with a bare marker
        # (``50 text``), while audit-matrix definitions retain the visible
        # brackets (``[50] text``).  Candidate markers are canonicalized to
        # bare digits upstream, but both source-backed spellings must resolve
        # to the same definition region.
        escaped_marker = re.escape(marker)
        pattern = re.compile(
            rf"^\s*(?:{escaped_marker}|\[{escaped_marker}\])(?:\s+|(?=\D))"
        )
        matches = [
            region
            for region in footnote_regions
            if tuple(region.native_object_refs) == definition_ids
            and pattern.match(region.native_text or region.source_text or "")
        ]
        for issue in candidate_issues:
            _append_unique(anomalies, issue)
        if len(matches) != 1:
            issue = (
                f"footnote_candidate_definition_missing:{marker}"
                if not matches
                else f"footnote_candidate_definition_ambiguous:{marker}"
            )
            _append_unique(anomalies, issue)
            result.append(RequirementFootnoteReference(
                marker=marker,
                text="",
                link_type="anomalous",
                source_segment_ids=[region.segment_id for region in matches],
            ))
            continue
        region = matches[0]
        text = (region.source_text or "").strip()
        if pattern.match(text):
            text = pattern.sub("", text, count=1).strip()
        link_type: Literal["direct", "inherited", "semantic", "anomalous"] = (
            "anomalous" if candidate_issues else link_types[identity]
        )
        if not text:
            _append_unique(anomalies, f"footnote_definition_empty:{marker}")
            link_type = "anomalous"
        result.append(RequirementFootnoteReference(
            marker=marker,
            text=text,
            link_type=link_type,
            source_segment_ids=[region.segment_id],
        ))
    return _sort_footnote_refs(result)


def _semantic_input(
    native: NativeRequirement,
    *,
    regions: list[RequirementSourceRegion],
    footnote_refs: list[RequirementFootnoteReference],
    anomalies: list[str],
) -> RequirementSemanticInput:
    """Build a stable role-aware view entirely from existing source regions."""

    formal_by_role: dict[str, list[RequirementSourceRegion]] = defaultdict(list)
    for region in regions:
        formal_by_role[region.role].append(region)

    core: list[RequirementSemanticFragment] = []
    qualifiers: list[RequirementSemanticFragment] = []
    if native.family is TemplateFamily.LEGACY_INDICATOR_VALUE:
        _append_semantic_fragment(
            core,
            role="indicator_text",
            text=native.indicator_text,
            regions=formal_by_role["indicator_text"],
            anomalies=anomalies,
        )
        _append_semantic_fragment(
            core,
            role="requirement_value",
            text=native.requirement_value,
            regions=formal_by_role["requirement_value"],
            anomalies=anomalies,
        )
    elif native.family is TemplateFamily.AUDIT_MATRIX:
        metadata_regions = formal_by_role["normative_text"]
        _append_semantic_fragment(
            core,
            role="indicator_text",
            text=native.indicator_text,
            regions=formal_by_role["indicator_text"] or metadata_regions,
            anomalies=anomalies,
        )
        _append_semantic_fragment(
            core,
            role="requirement_value",
            text=native.requirement_value,
            regions=formal_by_role["requirement_value"] or metadata_regions,
            anomalies=anomalies,
        )
    elif native.family is TemplateFamily.SINGLE_COLUMN_INDICATORS:
        _append_semantic_fragment(
            core,
            role="normative_text",
            text=native.normative_text,
            regions=[
                region for region in regions
                if region.role in {"normative_text", "requirement_continuation"}
            ],
            anomalies=anomalies,
        )
    else:
        for region in regions:
            if region.role not in {"normative_text", "requirement_continuation"}:
                continue
            _append_semantic_fragment(
                core,
                role=region.role,
                text=region.source_text,
                regions=[region],
                anomalies=anomalies,
            )

    if native.applicability and native.applicability.strip():
        applicability_regions = formal_by_role["applicability"]
        if not applicability_regions and native.family is TemplateFamily.AUDIT_MATRIX:
            applicability_regions = formal_by_role["normative_text"]
        _append_semantic_fragment(
            qualifiers,
            role="applicability",
            text=native.applicability,
            regions=applicability_regions,
            anomalies=anomalies,
        )
    for reference in footnote_refs:
        reference_regions = [
            region
            for region in regions
            if region.segment_id in reference.source_segment_ids
        ]
        _append_semantic_fragment(
            qualifiers,
            role="footnote",
            text=reference.text,
            regions=reference_regions,
            anomalies=anomalies,
            required=False,
        )

    core = _deduplicate_semantic_fragments(core)
    qualifiers = _deduplicate_semantic_fragments(qualifiers)
    if native.normative_text.strip() and not core:
        _append_unique(anomalies, "semantic_input_core_missing")
    fingerprint_material = {
        "generator_version": _SEMANTIC_INPUT_VERSION,
        "core_fragments": [item.model_dump(mode="json") for item in core],
        "qualifier_fragments": [
            item.model_dump(mode="json") for item in qualifiers
        ],
    }
    fingerprint = hashlib.sha256(
        json.dumps(
            fingerprint_material,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return RequirementSemanticInput(
        generator_version=_SEMANTIC_INPUT_VERSION,
        core_fragments=core,
        qualifier_fragments=qualifiers,
        fingerprint=fingerprint,
    )


def _append_semantic_fragment(
    fragments: list[RequirementSemanticFragment],
    *,
    role: Literal[
        "indicator_text",
        "requirement_value",
        "normative_text",
        "requirement_continuation",
        "applicability",
        "footnote",
    ],
    text: str | None,
    regions: Iterable[RequirementSourceRegion],
    anomalies: list[str],
    required: bool = True,
) -> None:
    normalized_text = (text or "").strip()
    if not normalized_text:
        if required:
            _append_unique(anomalies, f"semantic_input_text_missing:{role}")
        return
    source_segment_ids = [region.segment_id for region in regions]
    if not source_segment_ids:
        _append_unique(anomalies, f"semantic_input_provenance_missing:{role}")
        return
    fragments.append(RequirementSemanticFragment(
        role=role,
        text=normalized_text,
        source_segment_ids=source_segment_ids,
    ))


def _deduplicate_semantic_fragments(
    fragments: Iterable[RequirementSemanticFragment],
) -> list[RequirementSemanticFragment]:
    result: list[RequirementSemanticFragment] = []
    seen: set[tuple[str, str, tuple[str, ...]]] = set()
    for fragment in fragments:
        identity = (
            fragment.role,
            fragment.text,
            tuple(fragment.source_segment_ids),
        )
        if identity in seen:
            continue
        seen.add(identity)
        result.append(fragment)
    return result


def _sort_footnote_refs(
    values: Iterable[RequirementFootnoteReference],
) -> list[RequirementFootnoteReference]:
    def key(value: RequirementFootnoteReference) -> tuple[int, int | str]:
        marker = value.marker.strip()
        return (0, int(marker)) if marker.isdigit() else (1, marker.casefold())

    return sorted(values, key=key)


def _marker_footnote_refs(
    native: NativeRequirement,
    regions: list[RequirementSourceRegion],
    anomalies: list[str],
) -> list[RequirementFootnoteReference]:
    """Compatibility fallback for pre-candidate native payloads."""

    result: list[RequirementFootnoteReference] = []
    requirement_pages = {
        region.page_index for region in regions if region.role != "footnote"
    }
    markers = list(dict.fromkeys(
        marker.strip() for marker in native.footnote_markers if marker.strip()
    ))
    footnote_regions = [region for region in regions if region.role == "footnote"]
    for marker in markers:
        pattern = re.compile(rf"^\s*{re.escape(marker)}(?:\s+|(?=\D))")
        matches = [
            region for region in footnote_regions
            if pattern.match(region.native_text or region.source_text or "")
        ]
        if len(matches) == 1:
            region = matches[0]
            text = (region.source_text or "").strip()
            if pattern.match(text):
                text = pattern.sub("", text, count=1).strip()
            if not text:
                _append_unique(anomalies, f"footnote_definition_empty:{marker}")
                result.append(RequirementFootnoteReference(
                    marker=marker,
                    text="",
                    link_type="anomalous",
                    source_segment_ids=[region.segment_id],
                ))
                continue
            result.append(RequirementFootnoteReference(
                marker=marker,
                text=text,
                link_type=(
                    "direct"
                    if region.page_index in requirement_pages
                    else "inherited"
                ),
                source_segment_ids=[region.segment_id],
            ))
            continue
        if not matches:
            _append_unique(anomalies, f"footnote_definition_missing:{marker}")
            result.append(RequirementFootnoteReference(
                marker=marker,
                text="",
                link_type="anomalous",
            ))
            continue
        _append_unique(anomalies, f"footnote_definition_ambiguous:{marker}")
        result.append(RequirementFootnoteReference(
            marker=marker,
            text="",
            link_type="anomalous",
            source_segment_ids=[region.segment_id for region in matches],
        ))
    return _sort_footnote_refs(result)


def canonicalize_native_requirements(
    requirements: Iterable[NativeRequirement],
    *,
    source_document: str | None = None,
    source_authority: str | None = None,
    language: Language = "en",
    family_trusted: bool | None = None,
) -> list[Requirement]:
    """Convert candidates in input order without document-specific rules."""

    return [
        canonicalize_native_requirement(
            requirement,
            source_document=source_document,
            source_authority=source_authority,
            language=language,
            family_trusted=family_trusted,
        )
        for requirement in requirements
    ]


def apply_family_trust(
    requirement: Requirement,
    *,
    trusted: bool | None,
) -> Requirement:
    """Apply an external document-profile trust decision without importing it.

    The helper allows the pipeline to keep template learning outside this
    adapter.  An untrusted family can only lower acceptance; it can never
    promote a review or abstention.
    """

    if trusted is None:
        return requirement
    updated = requirement.model_copy(deep=True)
    flag = (
        "document_profile_family_trusted"
        if trusted
        else "document_profile_family_untrusted"
    )
    if flag not in updated.validation_flags:
        updated.validation_flags.append(flag)
    if not trusted and updated.status is RequirementStatus.ACCEPTED:
        updated.status = RequirementStatus.REVIEW_REQUIRED
        updated.confidence = min(updated.confidence or 0.50, 0.50)
        if "untrusted_document_template_family" not in updated.source_anomalies:
            updated.source_anomalies.append("untrusted_document_template_family")
        fail_closed = "fail_closed:review_required"
        if fail_closed not in updated.validation_flags:
            updated.validation_flags.append(fail_closed)
    return updated


def parse_english_modalities(text: str) -> list[RequirementModality]:
    """Compatibility API backed by the source-faithful semantic analyzer."""

    analysis = analyze_requirement_semantics(text, language="en")
    return [
        RequirementModality(
            token=candidate.span.text.lower(),
            type=candidate.modality_type,
            scope=candidate.scope.text,
        )
        for candidate in analysis.modalities
        if candidate.scope is not None
    ]


@dataclass(frozen=True)
class _CanonicalSemantics:
    modalities: list[RequirementModality]
    negations: list[RequirementScopedText]
    conditions: list[RequirementScopedText]
    exceptions: list[RequirementScopedText]
    exemptions: list[RequirementScopedText]
    thresholds: list[RequirementThreshold]
    dates: list[RequirementScopedText]
    cross_references: list[RequirementCrossReference]
    requires_review: bool


def _canonical_semantics(
    text: str,
    *,
    language: Language,
    regions: list[RequirementSourceRegion],
    anomalies: list[str],
    flags: list[str],
) -> _CanonicalSemantics:
    analysis = analyze_requirement_semantics(text, language=language)
    review_reasons: list[str] = []
    for analysis_flag in analysis.flags:
        _append_unique(flags, f"semantic_analysis:{analysis_flag}")
        if not analysis_flag.startswith("calendar_month_not_modality:"):
            _semantic_issue(
                "analysis",
                analysis_flag,
                anomalies=anomalies,
                flags=flags,
                review_reasons=review_reasons,
            )

    modalities: list[RequirementModality] = []
    for candidate in analysis.modalities:
        _candidate_issues(
            "modality",
            candidate.span.start,
            candidate.ambiguous,
            candidate.flags,
            anomalies=anomalies,
            flags=flags,
            review_reasons=review_reasons,
        )
        if candidate.scope is None:
            _semantic_issue(
                "modality",
                f"missing_scope:{candidate.span.start}",
                anomalies=anomalies,
                flags=flags,
                review_reasons=review_reasons,
            )
            continue
        modalities.append(
            RequirementModality(
                token=candidate.span.text,
                type=candidate.modality_type,
                scope=candidate.scope.text,
                scope_ref=_scope_ref_for_span(
                    analysis.source_text,
                    candidate.scope,
                    regions,
                ),
            )
        )

    negations: list[RequirementScopedText] = []
    for candidate in analysis.negations:
        if candidate.ambiguous:
            _semantic_issue(
                "negation",
                f"ambiguous:{candidate.span.start}",
                anomalies=anomalies,
                flags=flags,
                review_reasons=review_reasons,
            )
        if candidate.scope is None:
            _semantic_issue(
                "negation",
                f"missing_scope:{candidate.span.start}",
                anomalies=anomalies,
                flags=flags,
                review_reasons=review_reasons,
            )
            continue
        negations.append(
            RequirementScopedText(
                text=_canonical_negation_text(analysis, candidate),
                applies_to=candidate.scope.text,
                scope_ref=_scope_ref_for_span(
                    analysis.source_text,
                    candidate.scope,
                    regions,
                ),
            )
        )

    conditions = _canonical_contexts(
        analysis,
        kind="condition",
        regions=regions,
        anomalies=anomalies,
        flags=flags,
        review_reasons=review_reasons,
    )
    exceptions = _canonical_contexts(
        analysis,
        kind="exception",
        regions=regions,
        anomalies=anomalies,
        flags=flags,
        review_reasons=review_reasons,
    )
    exemptions = _canonical_contexts(
        analysis,
        kind="exemption",
        regions=regions,
        anomalies=anomalies,
        flags=flags,
        review_reasons=review_reasons,
    )

    thresholds: list[RequirementThreshold] = []
    threshold_candidates = list(analysis.thresholds)
    for candidate in threshold_candidates:
        field_role = _source_field_role_at(
            analysis.source_text,
            candidate.span.start,
        )
        if field_role == "indicator_text" and any(
            _same_threshold_candidate(candidate, other)
            and _source_field_role_at(analysis.source_text, other.span.start)
            == "applicability"
            for other in threshold_candidates
            if other is not candidate
        ):
            # A repeated applicability threshold is one legal qualifier, not a
            # second threshold merely because the Indicator restates it.
            continue
        field_start, field_end = source_field_value_bounds(
            analysis.source_text,
            candidate.span.start,
        )
        field_text = analysis.source_text[field_start:field_end].strip()
        field_thresholds = [
            item
            for item in threshold_candidates
            if field_start <= item.span.start and item.span.end <= field_end
        ]
        structured_requirement_value = (
            field_role == "requirement_value"
            and len(field_thresholds) == 1
            and bool(field_text)
        )
        source_segment_ids = _covering_formal_region_ids(
            analysis.source_text,
            candidate.span,
            regions,
        )
        exact_value_regions = [
            region
            for region in regions
            if region.role == "requirement_value"
            and _SPACE_RE.sub(" ", region.source_text).strip()
            == _SPACE_RE.sub(" ", candidate.span.text).strip()
        ]
        exact_requirement_value = (
            candidate.operator == "unspecified"
            and bool(exact_value_regions)
        )
        if structured_requirement_value:
            source_segment_ids = [
                region.segment_id
                for region in regions
                if region.role == "requirement_value"
            ]
        if not (exact_requirement_value or structured_requirement_value):
            _candidate_issues(
                "threshold",
                candidate.span.start,
                candidate.ambiguous,
                candidate.flags,
                anomalies=anomalies,
                flags=flags,
                review_reasons=review_reasons,
            )
        else:
            _append_unique(
                flags,
                "semantic_threshold_exact_from_requirement_value",
            )
        if not source_segment_ids:
            _semantic_issue(
                "threshold",
                f"source_region_unresolved:{candidate.span.start}",
                anomalies=anomalies,
                flags=flags,
                review_reasons=review_reasons,
            )
        applies_to = (
            _indicator_measure_scope_from_regions(regions)
            if structured_requirement_value
            else _applicability_scope_from_regions(regions)
            if field_role == "applicability"
            else _semantic_applies_to(analysis, candidate.span)
        )
        if applies_to is None:
            applies_to = candidate.span.text
            _semantic_issue(
                "threshold",
                f"applies_to_unresolved:{candidate.span.start}",
                anomalies=anomalies,
                flags=flags,
                review_reasons=review_reasons,
            )
        if structured_requirement_value:
            scope_ref = _field_text_scope_ref(
                regions,
                role="indicator_text",
                target="indicator_text",
                text=applies_to,
            )
        elif field_role == "applicability":
            scope_ref = _field_scope_ref(
                regions,
                role="applicability",
                target="applicability",
            )
        else:
            applies_to_span = _nearest_exact_span(
                analysis.source_text,
                applies_to,
                pivot=candidate.span.start,
            )
            scope_ref = (
                _scope_ref_for_span(
                    analysis.source_text,
                    applies_to_span,
                    regions,
                )
                if applies_to_span is not None
                else None
            )
        normalized_value: float | str | None = candidate.normalized_value
        if candidate.operator == "range":
            # Canonical v1.4 has one normalized-value slot. Preserve the exact
            # range instead of silently dropping its second endpoint.
            normalized_value = candidate.span.text
            _append_unique(flags, "semantic_analysis:range_preserved_as_source_text")
        thresholds.append(
            RequirementThreshold(
                raw_text=(
                    field_text
                    if structured_requirement_value
                    else _expanded_threshold_text(
                        analysis.source_text,
                        candidate.span,
                        field_end=field_end,
                    )
                    if field_role == "applicability"
                    else candidate.span.text
                ),
                operator=(
                    "eq"
                    if exact_requirement_value
                    else "other" if candidate.operator == "unspecified"
                    else candidate.operator
                ),
                normalized_value=normalized_value,
                unit=candidate.unit,
                applies_to=applies_to,
                basis="explicit",
                source_segment_ids=source_segment_ids,
                scope_ref=scope_ref,
            )
        )

    cross_references: list[RequirementCrossReference] = []
    for candidate in analysis.cross_references:
        _candidate_issues(
            "cross_reference",
            candidate.span.start,
            candidate.ambiguous,
            candidate.flags,
            anomalies=anomalies,
            flags=flags,
            review_reasons=review_reasons,
        )
        cross_references.append(
            RequirementCrossReference(
                text=candidate.span.text,
                target=candidate.target,
                type=(
                    "internal_generic" if candidate.ambiguous else "internal_exact"
                ),
            )
        )

    dates = _canonical_dates(analysis, regions=regions)

    if review_reasons:
        _append_unique(flags, "semantic_review_required")
    else:
        _append_unique(flags, f"semantic_analysis_complete:{language}")
    return _CanonicalSemantics(
        modalities=modalities,
        negations=negations,
        conditions=conditions,
        exceptions=exceptions,
        exemptions=exemptions,
        thresholds=thresholds,
        dates=dates,
        cross_references=cross_references,
        requires_review=bool(review_reasons),
    )


def _indicator_scope_from_regions(
    regions: list[RequirementSourceRegion],
) -> str | None:
    indicator = next(
        (region.source_text for region in regions if region.role == "indicator_text"),
        None,
    )
    if indicator is None:
        return None
    return re.sub(r"^\s*Indicator\s*:\s*", "", indicator, flags=re.IGNORECASE).strip()


def _indicator_measure_scope_from_regions(
    regions: list[RequirementSourceRegion],
) -> str | None:
    """Return the measured Indicator phrase without temporal/applicability tails."""

    indicator = _indicator_scope_from_regions(regions)
    if indicator is None:
        return None
    value = indicator.split(",", 1)[0].strip()
    value = re.sub(
        r"\s+(?:from|during|over|for|within)\s+(?=(?:each|the|any|a)\b).*$",
        "",
        value,
        flags=re.IGNORECASE,
    ).strip()
    return value or indicator


def _applicability_scope_from_regions(
    regions: list[RequirementSourceRegion],
) -> str | None:
    return next(
        (
            region.source_text.strip()
            for region in regions
            if region.role == "applicability" and region.source_text.strip()
        ),
        None,
    )


def _scope_ref_for_span(
    source_text: str,
    span: SourceSpan,
    regions: list[RequirementSourceRegion],
) -> RequirementScopeRef | None:
    anchors = _source_anchors_for_span(source_text, span, regions)
    if not anchors:
        return None
    region_by_id = {region.segment_id: region for region in regions}
    roles = {
        region_by_id[anchor.source_segment_id].role
        for anchor in anchors
        if anchor.source_segment_id in region_by_id
    }
    target = (
        next(iter(roles))
        if len(roles) == 1
        and next(iter(roles)) in {
            "indicator_text",
            "requirement_value",
            "applicability",
            "normative_text",
        }
        else "normative_text"
    )
    return RequirementScopeRef(
        kind="source_span",
        target=target,
        anchors=anchors,
    )


def _field_scope_ref(
    regions: list[RequirementSourceRegion],
    *,
    role: str,
    target: str,
) -> RequirementScopeRef | None:
    anchors: list[RequirementTextAnchor] = []
    for region in regions:
        if region.role != role or not region.source_text:
            continue
        value = region.source_text
        if role == "indicator_text":
            value = re.sub(
                r"^\s*Indicator\s*:\s*",
                "",
                value,
                flags=re.IGNORECASE,
            ).strip()
        start = region.source_text.find(value)
        if value and start >= 0:
            anchors.append(RequirementTextAnchor(
                source_segment_id=region.segment_id,
                start_char=start,
                end_char=start + len(value),
                text=value,
            ))
    if not anchors:
        return None
    return RequirementScopeRef(kind="field", target=target, anchors=anchors)


def _field_text_scope_ref(
    regions: list[RequirementSourceRegion],
    *,
    role: str,
    target: str,
    text: str | None,
) -> RequirementScopeRef | None:
    if not text:
        return None
    anchors: list[RequirementTextAnchor] = []
    for region in regions:
        if region.role != role or not region.source_text:
            continue
        start = region.source_text.find(text)
        if start >= 0:
            anchors.append(RequirementTextAnchor(
                source_segment_id=region.segment_id,
                start_char=start,
                end_char=start + len(text),
                text=text,
            ))
    if not anchors:
        return None
    return RequirementScopeRef(kind="field", target=target, anchors=anchors)


def _text_evidence_items(
    values: list[str],
    regions: list[RequirementSourceRegion],
    *,
    preferred_roles: tuple[str, ...],
) -> list[RequirementTextEvidence]:
    """Bind normalized subject/applicability text to one exact source phrase."""

    result: list[RequirementTextEvidence] = []
    role_rank = {role: index for index, role in enumerate(preferred_roles)}
    ordered_regions = sorted(
        regions,
        key=lambda region: (
            role_rank.get(region.role, len(role_rank)),
            region.page_index,
            region.segment_id,
        ),
    )
    for value in values:
        matches: list[tuple[RequirementSourceRegion, re.Match[str]]] = []
        for region in ordered_regions:
            if region.role not in role_rank or not region.source_text:
                continue
            match = re.search(re.escape(value), region.source_text, re.IGNORECASE)
            if match is not None:
                matches.append((region, match))
        if not matches:
            continue
        best_rank = role_rank[matches[0][0].role]
        best = [item for item in matches if role_rank[item[0].role] == best_rank]
        if len(best) != 1:
            continue
        region, match = best[0]
        anchor = RequirementTextAnchor(
            source_segment_id=region.segment_id,
            start_char=match.start(),
            end_char=match.end(),
            text=region.source_text[match.start():match.end()],
        )
        result.append(RequirementTextEvidence(
            text=value,
            basis=(
                "inferred_from_source_structure"
                if region.role in {"client_action", "auditor_action"}
                else "explicit"
            ),
            source_segment_ids=[region.segment_id],
            anchors=[anchor],
        ))
    return result


def _nearest_exact_span(text: str, value: str, *, pivot: int) -> SourceSpan | None:
    starts = [match.start() for match in re.finditer(re.escape(value), text)]
    if not starts:
        return None
    start = min(
        starts,
        key=lambda candidate: (
            0 if candidate <= pivot <= candidate + len(value) else 1,
            abs(candidate - pivot),
        ),
    )
    return SourceSpan(start=start, end=start + len(value), text=value)


def _with_structured_zero_threshold(
    base: _CanonicalSemantics,
    *,
    native: NativeRequirement,
    regions: list[RequirementSourceRegion],
    flags: list[str],
) -> _CanonicalSemantics:
    """Recover an explicit zero count from a two-field Requirement row.

    A bare ``0`` is not meaningful without its table field.  This rule is
    intentionally restricted to the two families whose source structure pairs
    an Indicator with a Requirement value, and to Indicators that explicitly
    start with ``Number of ...``.  The value remains source-exact and its
    provenance points only to the Requirement-value cell.
    """

    if native.family not in {
        TemplateFamily.AUDIT_MATRIX,
        TemplateFamily.LEGACY_INDICATOR_VALUE,
    }:
        return base
    indicator = (native.indicator_text or "").strip()
    raw_value = (native.requirement_value or "").strip()
    if not _EXPLICIT_ZERO_VALUE_RE.fullmatch(raw_value):
        return base
    count_match = _COUNT_INDICATOR_RE.match(_indicator_without_markers(indicator))
    if count_match is None:
        return base

    value_region_ids = [
        region.segment_id
        for region in regions
        if region.role == "requirement_value"
    ]
    if not value_region_ids:
        # Do not create a semantic value without direct cell provenance.
        return base
    if any(
        threshold.operator == "eq" and threshold.normalized_value == 0
        for threshold in base.thresholds
    ):
        return base

    unit, applies_to = _zero_count_context(
        _indicator_without_markers(indicator),
        family=native.family,
        count_match=count_match,
    )
    threshold = RequirementThreshold(
        raw_text=raw_value,
        operator="eq",
        normalized_value=0,
        unit=unit,
        applies_to=applies_to,
        basis="explicit",
        source_segment_ids=value_region_ids,
        scope_ref=_field_scope_ref(
            regions,
            role="indicator_text",
            target="indicator_text",
        ),
    )
    _append_unique(flags, "semantic_threshold_from_indicator_value_structure")
    return _CanonicalSemantics(
        modalities=base.modalities,
        negations=base.negations,
        conditions=base.conditions,
        exceptions=base.exceptions,
        exemptions=base.exemptions,
        thresholds=[*base.thresholds, threshold],
        dates=base.dates,
        cross_references=base.cross_references,
        requires_review=base.requires_review,
    )


def _indicator_without_markers(text: str) -> str:
    return _SPACE_RE.sub(" ", _BRACKET_MARKER_RE.sub("", text)).strip()


def _zero_count_context(
    indicator: str,
    *,
    family: TemplateFamily,
    count_match: re.Match[str],
) -> tuple[str, str]:
    unit = count_match.group("unit").casefold()
    source_scope = _SPACE_RE.sub(" ", count_match.group("scope")).strip()
    whole_indicator = _lower_initial(indicator)
    if family is TemplateFamily.AUDIT_MATRIX:
        return unit, whole_indicator

    if unit == "days":
        period = re.search(
            r"\bin\s+(?:the\s+)?(?P<period>.+?)\s+when\b",
            source_scope,
            re.IGNORECASE,
        )
        if period is not None:
            unit = f"days per {_lower_initial(period.group('period').strip())}"
        passive_use = _PASSIVE_USE_SCOPE_RE.search(source_scope)
        if passive_use is not None:
            used_object = re.sub(
                r"\s*\([A-Z][A-Za-z0-9-]*\)",
                "",
                passive_use.group("object"),
            )
            used_object = _lower_initial(_SPACE_RE.sub(" ", used_object).strip())
            return unit, f"use of {used_object}"

    of_scope = re.match(r"^\s*of\s+(?P<object>.+)$", source_scope, re.IGNORECASE)
    if of_scope is not None:
        return unit, _lower_initial(of_scope.group("object").strip())
    return unit, whole_indicator


def _lower_initial(text: str) -> str:
    if not text:
        return text
    return text[0].lower() + text[1:]


def _audit_normative_subjects(
    native: NativeRequirement,
    *,
    regions: list[RequirementSourceRegion],
    flags: list[str],
) -> list[str]:
    """Return only explicitly named regulated actors in an Audit row.

    Audit Indicators often encode the obligation without a modal sentence, so
    the actor can occur in the Indicator or an explicitly linked footnote.
    This is a conservative surface extractor: it recognises domain actor names
    only when they are literally present and avoids treating ``farm staff`` or
    ``farm manager`` as the farm itself.
    """

    if native.family is not TemplateFamily.AUDIT_MATRIX:
        return []

    found: list[tuple[str, str]] = []
    for region in regions:
        if region.role not in _AUDIT_SUBJECT_ROLES:
            continue
        text = region.source_text or region.resolved_text or ""
        if not text:
            continue
        masked = _FARM_MEMBER_RE.sub(" ", text)
        if region.role in {"indicator_text", "footnote", "normative_text"}:
            for match in _EXPLICIT_MODAL_SUBJECT_RE.finditer(text):
                subject = _SPACE_RE.sub(" ", match.group("subject")).strip(" ,")
                if subject:
                    found.append((subject, region.role))
        if re.search(r"\bthe\s+farm\b", masked, re.IGNORECASE):
            match = re.search(r"\bthe\s+farm\b", masked, re.IGNORECASE)
            assert match is not None
            found.append((text[match.start():match.end()], region.role))
        elif re.search(
            r"(?:\b(?:by|on|at|for|from|of|to)\s+farm\b|"
            r"\bfarm\s+(?=shall|must|should|may|can|is|has|does|will\b))",
            masked,
            re.IGNORECASE,
        ):
            found.append(("farm", region.role))

        if re.search(r"\b(?:the\s+)?UoC\b", text, re.IGNORECASE):
            found.append(("the UoC", region.role))
        if re.search(
            r"\b(?:the\s+)?operator\s+"
            r"(?=shall|must|should|may|can|is|has|does|will\b)",
            text,
            re.IGNORECASE,
        ):
            found.append(("the operator", region.role))

    if any(subject == "the farm" for subject, _role in found):
        found = [item for item in found if item[0] != "farm"]

    subjects: list[str] = []
    seen: set[str] = set()
    for subject, role in found:
        identity = subject.casefold()
        if identity in seen:
            continue
        seen.add(identity)
        subjects.append(subject)
        _append_unique(
            flags,
            "normative_subject_source_backed:"
            f"{_SAFE_ID_RE.sub('_', identity).strip('_')}:{role}",
        )
    return subjects


def _normative_subjects(
    native: NativeRequirement,
    *,
    regions: list[RequirementSourceRegion],
    flags: list[str],
) -> list[str]:
    """Recover source-explicit regulated actors from formal evidence only."""

    if native.family is TemplateFamily.AUDIT_MATRIX:
        return _audit_normative_subjects(native, regions=regions, flags=flags)

    found: list[tuple[str, str]] = []
    for region in regions:
        if region.role not in {
            "indicator_text",
            "normative_text",
            "requirement_continuation",
        }:
            continue
        text = region.source_text or region.resolved_text or ""
        for match in _GENERAL_REGULATED_SUBJECT_RE.finditer(text):
            found.append((match.group("subject"), region.role))

    subjects: list[str] = []
    seen: set[str] = set()
    for subject, role in found:
        identity = subject.casefold()
        if identity in seen:
            continue
        seen.add(identity)
        subjects.append(subject)
        _append_unique(
            flags,
            "normative_subject_source_backed:"
            f"{_SAFE_ID_RE.sub('_', identity).strip('_')}:{role}",
        )
    return subjects


@dataclass(frozen=True)
class _FootnoteQualifierResult:
    semantics: _CanonicalSemantics
    applicability: list[str]
    associated_instructions: list[RequirementInstruction]


def _with_structured_requirement_value_negation(
    base: _CanonicalSemantics,
    *,
    native: NativeRequirement,
    regions: list[RequirementSourceRegion],
    flags: list[str],
) -> _CanonicalSemantics:
    """Interpret an explicit ``None`` value only with field-level evidence."""

    raw_value = (native.requirement_value or "").strip()
    value = _BRACKET_MARKER_RE.sub("", raw_value).strip()
    if value.casefold() not in {"none", "no"}:
        return base
    if not any(region.role == "requirement_value" for region in regions):
        return base
    applies_to = _lower_initial(
        _BRACKET_MARKER_RE.sub("", (native.indicator_text or "")).strip()
    ) or native.normative_text
    negation = RequirementScopedText(
        text=value,
        applies_to=applies_to,
        scope_ref=_field_scope_ref(
            regions,
            role="indicator_text",
            target="indicator_text",
        ),
    )
    _append_unique(flags, "semantic_negation_from_indicator_value_structure")
    return _CanonicalSemantics(
        modalities=base.modalities,
        negations=_deduplicate_scoped_text([*base.negations, negation]),
        conditions=base.conditions,
        exceptions=base.exceptions,
        exemptions=base.exemptions,
        thresholds=base.thresholds,
        dates=base.dates,
        cross_references=base.cross_references,
        requires_review=base.requires_review,
    )


def _with_footnote_qualifiers(
    base: _CanonicalSemantics,
    *,
    native: NativeRequirement,
    footnote_refs: list[RequirementFootnoteReference],
    regions: list[RequirementSourceRegion],
    normative_text: str,
    language: Language,
    applicability: list[str],
    anomalies: list[str],
    flags: list[str],
) -> _FootnoteQualifierResult:
    """Promote only proven, source-backed qualifiers from linked footnotes.

    A footnote definition is never a new Requirement.  ``anomalous`` links and
    definitions without a resolved source segment are retained as evidence but
    cannot affect semantics.  Semantic links may affect the owner only when the
    footnote explicitly names that Requirement; an exact leading ``Term:`` may
    still create a defined-term reference.
    """

    modalities = list(base.modalities)
    negations = list(base.negations)
    conditions = list(base.conditions)
    exceptions = list(base.exceptions)
    exemptions = list(base.exemptions)
    thresholds = list(base.thresholds)
    dates = list(base.dates)
    cross_references = list(base.cross_references)
    instructions: list[RequirementInstruction] = []
    promoted_applicability = list(applicability)
    requires_review = base.requires_review
    normative_analysis = analyze_requirement_semantics(normative_text, language=language)
    normative_target = next(
        (item.scope.text for item in normative_analysis.modalities if item.scope),
        normative_text,
    )

    for reference in footnote_refs:
        if reference.link_type == "anomalous" or not reference.text.strip():
            continue
        if not reference.source_segment_ids:
            requires_review = True
            _semantic_issue(
                "footnote_qualifier",
                f"source_region_unresolved:{reference.marker}",
                anomalies=anomalies,
                flags=flags,
                review_reasons=[],
            )
            continue

        text = reference.text.strip()
        analysis = analyze_requirement_semantics(text, language=language)
        added = False
        leading_exemption = _leading_footnote_exemption(text, analysis)
        qualifier_bound = (
            reference.link_type != "semantic"
            or _footnote_explicitly_targets(text, native.requirement_id)
        )

        defined_reference = _defined_term_reference(
            native=native,
            marker=reference.marker,
            definition=text,
        )
        if defined_reference is not None:
            cross_references.append(defined_reference)
            added = True
            if re.match(r"\s*[^:\n]{2,80}?\s*:\s+", text) and not _footnote_explicitly_targets(
                text, native.requirement_id
            ):
                _append_unique(
                    flags,
                    f"semantic_analysis:linked_footnote_qualifiers:{reference.marker}",
                )
                continue

        if not qualifier_bound:
            # Exact-term semantic links are useful definitions, but their prose
            # is not automatically a modality or condition of every use site.
            if added:
                _append_unique(
                    flags,
                    f"semantic_analysis:linked_footnote_qualifiers:{reference.marker}",
                )
            continue

        exception_parts = _explicit_exception_parts(text)
        if exception_parts:
            exceptions = [
                item for item in exceptions
                if not (
                    re.match(r"(?i)^except\s+as\s+noted\b", item.text)
                    and reference.marker in item.text
                )
            ]
            applies_to = (
                f"Requirement: {native.requirement_value.strip()}"
                if native.requirement_value and native.requirement_value.strip()
                else normative_target
            )
            for index, part in enumerate(exception_parts, start=1):
                marker = f"Exception #{index}"
                exceptions.append(RequirementScopedText(text=part, applies_to=applies_to))
                instructions.append(RequirementInstruction(
                    marker=marker,
                    text=part,
                    effect="exception",
                    source_segment_ids=list(reference.source_segment_ids),
                ))
                conditions.extend(_footnote_part_conditions(part, marker, language))
            added = True
        else:
            explicit_exception = _leading_exception_sentence(text)
            if explicit_exception:
                exceptions.append(RequirementScopedText(
                    text=explicit_exception,
                    applies_to=_exception_target(native, normative_target),
                ))
                added = True

        for candidate in analysis.modalities:
            if candidate.ambiguous or candidate.flags or candidate.scope is None:
                requires_review = True
                _semantic_issue(
                    "footnote_modality",
                    f"ambiguous:{reference.marker}:{candidate.span.start}",
                    anomalies=anomalies,
                    flags=flags,
                    review_reasons=[],
                )
                continue
            if re.match(
                r"(?i)should\s+this\s+be\s+required\s*,",
                text[candidate.span.start :],
            ):
                continue
            # ``may be made`` belongs to an already explicit exception rather
            # than creating a second top-level permission.
            if explicit_exception if not exception_parts else False:
                if candidate.modality_type == "permission" and candidate.span.start < len(explicit_exception):
                    continue
            modality_scope = _footnote_modality_scope(text, candidate, native)
            modalities.append(RequirementModality(
                token=candidate.span.text,
                type=candidate.modality_type,
                scope=modality_scope,
                scope_ref=_footnote_scope_ref(
                    reference_text=text,
                    scope_text=modality_scope,
                    anchor_text=candidate.scope.text,
                    marker=reference.marker,
                    source_segment_ids=reference.source_segment_ids,
                    regions=regions,
                ),
            ))
            added = True

        for candidate in ([] if exception_parts else analysis.negations):
            if candidate.ambiguous or candidate.scope is None:
                requires_review = True
                _semantic_issue(
                    "footnote_negation",
                    f"ambiguous:{reference.marker}:{candidate.span.start}",
                    anomalies=anomalies,
                    flags=flags,
                    review_reasons=[],
                )
                continue
            negation_text, negation_target = _footnote_negation_parts(
                analysis,
                candidate,
            )
            negations.append(RequirementScopedText(
                text=negation_text,
                applies_to=negation_target,
                scope_ref=_footnote_scope_ref(
                    reference_text=text,
                    scope_text=negation_target,
                    marker=reference.marker,
                    source_segment_ids=reference.source_segment_ids,
                    regions=regions,
                ),
            ))
            added = True

        if not exception_parts:
            for kind, candidates in (
                ("condition", analysis.conditions),
                ("exception", analysis.exceptions),
                ("exemption", analysis.exemptions),
            ):
                destination = {
                    "condition": conditions,
                    "exception": exceptions,
                    "exemption": exemptions,
                }[kind]
                for candidate in candidates:
                    if (
                        kind == "condition"
                        and leading_exemption is not None
                        and candidate.marker.start < leading_exemption.end
                    ):
                        # A ``where``/``if`` phrase inside an explicit leading
                        # exemption limits that exemption.  It is not a second
                        # standalone condition on the Requirement.
                        continue
                    if kind == "condition" and (
                        explicit_exception or _explicit_footnote_applicability(
                            text,
                            requirement_id=native.requirement_id,
                            link_type=reference.link_type,
                        )
                    ):
                        continue
                    if candidate.ambiguous or candidate.flags:
                        requires_review = True
                        _semantic_issue(
                            f"footnote_{kind}",
                            f"ambiguous:{reference.marker}:{candidate.marker.start}",
                            anomalies=anomalies,
                            flags=flags,
                            review_reasons=[],
                        )
                        continue
                    if kind == "exemption" and leading_exemption is not None:
                        exemption_text = leading_exemption.text
                        exemption_target = f"Requirement {native.requirement_id}"
                        scope_ref = _requirement_scope_ref(
                            native.requirement_id,
                            regions,
                        )
                    else:
                        exemption_text = candidate.clause.text
                        exemption_target = normative_target
                        scope_ref = None
                    destination.append(RequirementScopedText(
                        text=exemption_text,
                        applies_to=exemption_target,
                        scope_ref=scope_ref,
                    ))
                    added = True

        for candidate in analysis.thresholds:
            if candidate.ambiguous or candidate.flags:
                requires_review = True
                _semantic_issue(
                    "footnote_threshold",
                    f"ambiguous:{reference.marker}:{candidate.span.start}",
                    anomalies=anomalies,
                    flags=flags,
                    review_reasons=[],
                )
            applies_to = _semantic_applies_to(analysis, candidate.span)
            if applies_to is None:
                applies_to = _local_threshold_context(analysis.source_text, candidate.span)
            thresholds.append(RequirementThreshold(
                raw_text=candidate.span.text,
                operator="other" if candidate.operator == "unspecified" else candidate.operator,
                normalized_value=(candidate.span.text if candidate.operator == "range" else candidate.normalized_value),
                unit=candidate.unit,
                applies_to=applies_to or normative_target,
                basis="explicit",
                source_segment_ids=list(reference.source_segment_ids),
            ))
            if (
                candidate.operator == "lte"
                and candidate.span.text.lower().startswith("within ")
                and (candidate.unit or "").lower()
                in {"day", "days", "week", "weeks", "hour", "hours"}
            ):
                conditions.append(RequirementScopedText(
                    text=candidate.span.text,
                    applies_to=normative_target,
                ))
            added = True

        footnote_dates: list[RequirementScopedText] = []
        for item in _canonical_dates(analysis):
            date_target = _footnote_date_target(
                analysis,
                date_text=item.text,
            ) or item.applies_to
            footnote_dates.append(item.model_copy(update={
                "applies_to": date_target,
                "scope_ref": _footnote_scope_ref(
                    reference_text=text,
                    scope_text=date_target,
                    marker=reference.marker,
                    source_segment_ids=reference.source_segment_ids,
                    regions=regions,
                ),
            }))
        if footnote_dates:
            dates.extend(footnote_dates)
            added = True

        for scope in _explicit_footnote_applicability(
            text,
            requirement_id=native.requirement_id,
            link_type=reference.link_type,
        ):
            if scope not in promoted_applicability:
                promoted_applicability.append(scope)
            added = True

        cross_references.extend(_footnote_cross_references(
            analysis,
            text=text,
            requirement_id=native.requirement_id,
        ))
        effect = _footnote_instruction_effect(text, bool(exception_parts))
        if effect is not None and not exception_parts:
            instructions.append(RequirementInstruction(
                marker=reference.marker,
                text=text,
                effect=effect,
                source_segment_ids=list(reference.source_segment_ids),
            ))
            added = True
        if added:
            _append_unique(flags, f"semantic_analysis:linked_footnote_qualifiers:{reference.marker}")

    semantics = _CanonicalSemantics(
        modalities=_deduplicate_modalities(modalities),
        negations=_deduplicate_scoped_text(negations),
        conditions=_deduplicate_scoped_text(conditions),
        exceptions=_deduplicate_scoped_text(exceptions),
        exemptions=_deduplicate_scoped_text(exemptions),
        thresholds=_deduplicate_thresholds(thresholds),
        dates=_deduplicate_scoped_text(dates),
        cross_references=_deduplicate_cross_references(cross_references),
        requires_review=requires_review,
    )
    return _FootnoteQualifierResult(
        semantics=semantics,
        applicability=list(dict.fromkeys(promoted_applicability)),
        associated_instructions=_deduplicate_instructions(instructions),
    )


def _footnote_explicitly_targets(text: str, requirement_id: str) -> bool:
    identity = re.escape(requirement_id)
    return bool(re.search(
        rf"(?<![\d.]){identity}(?!\d|\.\d)",
        text,
    ))


def _explicit_exception_parts(text: str) -> list[str]:
    header = re.search(r"\bfollowing\s+exceptions?\b[^:]*:\s*", text, re.I)
    if header is None or "•" not in text[header.end() :]:
        return []
    return [
        part.strip()
        for part in text[header.end() :].split("•")
        if part.strip()
    ]


def _leading_exception_sentence(text: str) -> str | None:
    match = re.match(r"(?is)\s*(exception\b.*?(?:\.(?=\s|$)|$))", text)
    return match.group(1).strip() if match else None


def _exception_target(native: NativeRequirement, fallback: str) -> str:
    indicator = native.indicator_text or ""
    numbered = re.findall(r"(?:^|\s)(\d+)\.\s", indicator)
    if "prior to" in indicator.casefold() and len(numbered) == 3:
        return "the three pre-action conditions"
    return fallback


def _footnote_part_conditions(
    text: str,
    applies_to: str,
    language: Language,
) -> list[RequirementScopedText]:
    analysis = analyze_requirement_semantics(text, language=language)
    candidates = sorted(analysis.conditions, key=lambda item: item.marker.start)
    selected: list[ContextCandidate] = []
    for candidate in candidates:
        if candidate.ambiguous or candidate.flags:
            continue
        if any(
            prior.clause.start <= candidate.marker.start < prior.clause.end
            for prior in selected
        ):
            continue
        selected.append(candidate)
    values: list[str] = []
    for candidate in selected:
        values.extend(re.split(
            r"\s+and\s+(?=(?:provided(?:\s+that)?\b|it\s+is\s+in\s+compliance\b))",
            candidate.clause.text,
            flags=re.I,
        ))
    for match in re.finditer(r"\bas\s+long\s+as\b[^.]*", text, re.I):
        values.append(match.group(0))
    return _deduplicate_scoped_text([
        RequirementScopedText(
            text=value.strip().rstrip(" ."),
            applies_to=applies_to,
        )
        for value in values
        if value.strip().rstrip(" .")
    ])


def _footnote_modality_scope(
    text: str,
    candidate: ModalityCandidate,
    native: NativeRequirement,
) -> str:
    assert candidate.scope is not None
    # Keep the same predicate-only modality contract used for the Requirement
    # body. The grammatical subject remains available in normative_subjects;
    # prefixing it here makes linked-footnote modalities incomparable to body
    # modalities and broadens temporal scope.
    return candidate.scope.text


def _footnote_scope_ref(
    *,
    reference_text: str,
    scope_text: str,
    anchor_text: str | None = None,
    marker: str,
    source_segment_ids: list[str],
    regions: list[RequirementSourceRegion],
) -> RequirementScopeRef | None:
    """Anchor a promoted qualifier inside its explicitly linked footnote."""

    region_by_id = {region.segment_id: region for region in regions}
    exact_candidate = anchor_text or scope_text
    scope_match = re.search(
        re.escape(exact_candidate),
        reference_text,
        re.IGNORECASE,
    )
    if scope_match is None:
        return None
    source_exact_scope = reference_text[scope_match.start():scope_match.end()]
    matches: list[RequirementTextAnchor] = []
    for segment_id in source_segment_ids:
        region = region_by_id.get(segment_id)
        if region is None or not region.source_text:
            continue
        reference_start = region.source_text.find(reference_text)
        if reference_start < 0:
            continue
        start = reference_start + scope_match.start()
        end = reference_start + scope_match.end()
        if region.source_text[start:end] != source_exact_scope:
            continue
        matches.append(RequirementTextAnchor(
            source_segment_id=segment_id,
            start_char=start,
            end_char=end,
            text=source_exact_scope,
        ))
    if len(matches) != 1:
        return None
    return RequirementScopeRef(
        kind="footnote",
        target=f"footnote:{marker}",
        anchors=matches,
    )


def _footnote_negation_text(
    analysis: RequirementSemanticAnalysis,
    candidate: NegationCandidate,
) -> str:
    value = _canonical_negation_text(analysis, candidate)
    prefix = analysis.source_text[max(0, candidate.span.start - 8) : candidate.span.start]
    auxiliary = re.search(r"\b(?:do|does|did|is|are|was|were|can)\s*$", prefix, re.I)
    if auxiliary and not value.casefold().startswith(auxiliary.group(0).casefold()):
        return f"{auxiliary.group(0)} {value}"
    return value


def _footnote_negation_parts(
    analysis: RequirementSemanticAnalysis,
    candidate: NegationCandidate,
) -> tuple[str, str]:
    """Recover a source-exact passive negation and its grammatical subject."""

    if candidate.span.text.casefold() == "not":
        prefix = analysis.source_text[:candidate.span.start]
        match = re.search(
            r"(?:^|[.;]\s+|,\s+|\bbut\s+|\band\s+)"
            r"(?P<subject>[^,;:.]{2,180}?)\s+"
            r"(?P<aux>is|are|was|were)\s*$",
            prefix,
            re.IGNORECASE,
        )
        predicate = re.match(
            r"\s+(?P<predicate>[A-Za-z][A-Za-z-]*)",
            analysis.source_text[candidate.span.end:],
        )
        if match is not None and predicate is not None:
            subject = match.group("subject").strip()
            negation_end = candidate.span.end + predicate.end()
            negation_start = match.start("aux")
            return (
                analysis.source_text[negation_start:negation_end],
                subject,
            )
    return (
        _footnote_negation_text(analysis, candidate),
        candidate.scope.text if candidate.scope is not None else candidate.span.text,
    )


def _leading_footnote_exemption(
    text: str,
    analysis: RequirementSemanticAnalysis,
) -> SourceSpan | None:
    """Return the complete first sentence when it explicitly declares an exemption."""

    if not any(item.marker.start == 0 for item in analysis.exemptions):
        return None
    end = len(text)
    for index, character in enumerate(text):
        if character == "\n" or (
            character == "." and not _numeric_internal_dot(text, index)
        ):
            end = index + (character == '.')
            break
    while end > 0 and text[end - 1].isspace():
        end -= 1
    return SourceSpan(start=0, end=end, text=text[:end]) if end else None


def _footnote_date_target(
    analysis: RequirementSemanticAnalysis,
    *,
    date_text: str,
) -> str | None:
    """Bind a temporal window to the nearest complete passive negation."""

    date_start = analysis.source_text.find(date_text)
    if date_start < 0:
        return None
    candidates = [
        candidate
        for candidate in analysis.negations
        if candidate.span.start < date_start
    ]
    for candidate in reversed(candidates):
        negation_text, target = _footnote_negation_parts(analysis, candidate)
        phrase = f"{target} {negation_text}"
        if analysis.source_text.find(phrase) >= 0:
            return phrase
    return None


def _requirement_scope_ref(
    requirement_id: str,
    regions: list[RequirementSourceRegion],
) -> RequirementScopeRef | None:
    anchors: list[RequirementTextAnchor] = []
    for region in regions:
        if region.role != "requirement_id" or not region.source_text:
            continue
        start = region.source_text.find(requirement_id)
        if start < 0:
            continue
        anchors.append(RequirementTextAnchor(
            source_segment_id=region.segment_id,
            start_char=start,
            end_char=start + len(requirement_id),
            text=requirement_id,
        ))
    if len(anchors) != 1:
        return None
    return RequirementScopeRef(
        kind="requirement",
        target=f"requirement:{requirement_id}",
        anchors=anchors,
    )


def _defined_term_reference(
    *,
    native: NativeRequirement,
    marker: str,
    definition: str,
) -> RequirementCrossReference | None:
    heading = re.match(r"\s*([^:\n]{2,80}?)\s*:\s+", definition)
    if heading is None:
        return None
    term = _SPACE_RE.sub(" ", heading.group(1)).strip(" .")
    base_term = re.sub(r"\s*\([^)]*\)\s*$", "", term).strip()
    if len(base_term) < 3:
        return None
    fields = [
        value for value in (
            native.indicator_text,
            native.requirement_value,
            native.applicability,
            native.normative_text,
        ) if value
    ]
    for field in fields:
        match = re.search(rf"(?<!\w){re.escape(base_term)}(?!\w)", field, re.I)
        if match is None:
            continue
        anchor = field[match.start() : match.end()]
        bracket = re.match(
            rf"\s*\[{re.escape(marker)}\](?:\s*\([^)]*\))?",
            field[match.end() :],
        )
        if bracket:
            anchor += bracket.group(0)
        target = f"[{marker}] {term}" if bracket else f"Footnote {marker}"
        return RequirementCrossReference(
            text=_SPACE_RE.sub(" ", anchor).strip(),
            target=target,
            type="defined_term",
        )
    return None


def _explicit_footnote_applicability(
    text: str,
    *,
    requirement_id: str,
    link_type: str,
) -> list[str]:
    result: list[str] = []
    identity = re.escape(requirement_id)
    patterns = (
        rf"\bstandard\s+{identity}\s+(?:is\s+)?applicable\s+to\s+([^.]*)",
        rf"\bstandard\s+{identity}\b[^.]*?\bapplies\s+to\s+([^.]*)",
        r"\bthis\s+(?:standard|indicator|requirement)\b[^;\n]{0,160}?\bapplies\s+to\s+([^.]*)",
    )
    for index, pattern in enumerate(patterns):
        if index == 2 and link_type == "semantic":
            continue
        for match in re.finditer(pattern, text, re.I):
            scope = re.split(r"\s+and\s+not\s+to\s+", match.group(1), flags=re.I)[0]
            scope = _SPACE_RE.sub(" ", scope).strip(" ,;")
            if scope and scope not in result:
                result.append(scope)
    return result


def _footnote_cross_references(
    analysis: RequirementSemanticAnalysis,
    *,
    text: str,
    requirement_id: str,
) -> list[RequirementCrossReference]:
    result = [
        RequirementCrossReference(
            text=candidate.span.text,
            target=candidate.target,
            type="internal_generic" if candidate.ambiguous else "internal_exact",
        )
        for candidate in analysis.cross_references
    ]
    for match in re.finditer(
        r"\b(?:(Standard|Indicator|Requirement)\s+)?(\d+(?:\.\d+){1,4})\b",
        text,
        re.I,
    ):
        target = match.group(2)
        if target == requirement_id:
            continue
        prefix = text[max(0, match.start() - 35) : match.start()]
        if not match.group(1) and not re.search(
            r"(?:contradict|complement|pursuant|according|refer|see)\W*$",
            prefix,
            re.I,
        ):
            continue
        result.append(RequirementCrossReference(
            text=match.group(0),
            target=target,
            type="internal_exact",
        ))
    return _deduplicate_cross_references(result)


def _footnote_marker_cross_references(
    references: Iterable[RequirementFootnoteReference],
    *,
    requirement_id: str,
) -> list[RequirementCrossReference]:
    return [
        RequirementCrossReference(
            text=f"[{reference.marker}]",
            target=f"footnote {reference.marker}",
            type="internal_exact",
        )
        for reference in references
        if reference.link_type != "anomalous"
        and reference.text.strip()
        and (
            reference.link_type != "semantic"
            or _footnote_explicitly_targets(reference.text, requirement_id)
        )
    ]


def _direct_requirement_cross_references(
    text: str,
    *,
    requirement_id: str,
) -> list[RequirementCrossReference]:
    """Recover only source-explicit dependencies, not arbitrary numbers."""

    result: list[RequirementCrossReference] = []
    for match in re.finditer(
        r"\b(?:use\s+of|see(?:\s+also)?|according\s+to|pursuant\s+to|"
        r"under|after\s+achieving)\s+(?:Indicator\s+)?"
        r"(?P<id>\d+(?:\.\d+){2,})\b",
        text,
        re.IGNORECASE,
    ):
        target = match.group("id")
        if target == requirement_id:
            continue
        result.append(RequirementCrossReference(
            text=target,
            target=f"Indicator {target}",
            type="internal_exact",
        ))
    return _deduplicate_cross_references(result)


def _source_instructions(
    native: NativeRequirement,
    regions: Iterable[RequirementSourceRegion],
) -> tuple[list[RequirementInstruction], list[RequirementCrossReference]]:
    instructions: list[RequirementInstruction] = []
    references: list[RequirementCrossReference] = []
    for region in regions:
        if region.role != "instruction" or not (region.source_text or "").strip():
            continue
        text = (region.source_text or "").strip()
        note_indicator = re.match(
            r"(?i)^(Note\s+Indicator\s+\d+(?:\.\d+){2,})\s*:",
            text,
        )
        marker = (
            note_indicator.group(1)
            if note_indicator
            else "Note" if re.match(r"(?i)^Note\s*:", text) else None
        )
        instructions.append(RequirementInstruction(
            marker=marker,
            text=text,
            effect="method",
            source_segment_ids=[region.segment_id],
        ))
        for match in re.finditer(r"\((\d+(?:\.\d+){2,})\)", text):
            target = match.group(1)
            if target == native.requirement_id:
                continue
            references.append(RequirementCrossReference(
                text=target,
                target=f"Indicator {target}",
                type="internal_exact",
            ))
        for match in re.finditer(r"\bQA\s+(\d{1,4})\b", text, re.IGNORECASE):
            number = int(match.group(1))
            references.append(RequirementCrossReference(
                text=match.group(0),
                target=f"ASC interpretation platform QA{number:04d}",
                type="external_document",
            ))
    return (
        _deduplicate_instructions(instructions),
        _deduplicate_cross_references(references),
    )


def _footnote_instruction_effect(
    text: str,
    has_exception_parts: bool,
) -> Literal["method", "condition", "exception", "exemption", "procedure", "other"] | None:
    if has_exception_parts:
        return "exception"
    lowered = text.casefold()
    if lowered.startswith("exception") or re.search(r"\b(?:unless|except)\b", lowered):
        return "exception"
    if re.search(r"\b(?:exempt|excludes?|excluded)\b", lowered):
        return "exemption"
    if re.search(r"\b(?:applies|applicable)\s+to\b", lowered):
        return "condition"
    if re.search(r"\bshall\s+be\s+made\s+available\b", lowered):
        return "procedure"
    if re.search(r"\bsame\s+methodology\b", lowered):
        return "method"
    return None


def _deduplicate_modalities(
    values: Iterable[RequirementModality],
) -> list[RequirementModality]:
    result: list[RequirementModality] = []
    seen: set[tuple[str, str, str]] = set()
    for value in values:
        key = (value.token, value.type, value.scope)
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def _deduplicate_cross_references(
    values: Iterable[RequirementCrossReference],
) -> list[RequirementCrossReference]:
    result: list[RequirementCrossReference] = []
    seen: set[tuple[str, str, str]] = set()
    for value in values:
        key = (value.text, value.target, value.type)
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def _deduplicate_instructions(
    values: Iterable[RequirementInstruction],
) -> list[RequirementInstruction]:
    result: list[RequirementInstruction] = []
    seen: set[tuple[object, ...]] = set()
    for value in values:
        key = (value.marker, value.text, value.effect, tuple(value.source_segment_ids))
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def _deduplicate_thresholds(
    values: Iterable[RequirementThreshold],
) -> list[RequirementThreshold]:
    result: list[RequirementThreshold] = []
    seen: set[tuple[object, ...]] = set()
    for value in values:
        key = (
            value.raw_text,
            value.operator,
            value.normalized_value,
            value.unit,
            value.applies_to,
            tuple(value.source_segment_ids),
        )
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def _canonical_contexts(
    analysis: RequirementSemanticAnalysis,
    *,
    kind: Literal["condition", "exception", "exemption"],
    regions: list[RequirementSourceRegion],
    anomalies: list[str],
    flags: list[str],
    review_reasons: list[str],
) -> list[RequirementScopedText]:
    candidates = {
        "condition": analysis.conditions,
        "exception": analysis.exceptions,
        "exemption": analysis.exemptions,
    }[kind]
    result: list[RequirementScopedText] = []
    for candidate in candidates:
        _candidate_issues(
            kind,
            candidate.marker.start,
            candidate.ambiguous,
            candidate.flags,
            anomalies=anomalies,
            flags=flags,
            review_reasons=review_reasons,
        )
        applies_to = _context_applies_to(analysis, candidate)
        if applies_to is None:
            applies_to = candidate.clause.text
            _semantic_issue(
                kind,
                f"applies_to_unresolved:{candidate.marker.start}",
                anomalies=anomalies,
                flags=flags,
                review_reasons=review_reasons,
            )
        result.append(
            RequirementScopedText(
                text=candidate.clause.text,
                applies_to=applies_to,
                scope_ref=(
                    _scope_ref_for_span(
                        analysis.source_text,
                        applies_to_span,
                        regions,
                    )
                    if (
                        applies_to_span := _nearest_exact_span(
                            analysis.source_text,
                            applies_to,
                            pivot=candidate.marker.start,
                        )
                    ) is not None
                    else None
                ),
            )
        )
    return result


def _canonical_negation_text(
    analysis: RequirementSemanticAnalysis,
    candidate: NegationCandidate,
) -> str:
    """Preserve the complete English negated phrase without rewriting it."""

    if candidate.scope is None:
        return candidate.span.text
    cue = candidate.span.text.lower()
    if cue == "no":
        return analysis.source_text[candidate.span.start : candidate.scope.end]
    if cue != "not":
        return candidate.span.text
    containing_modalities = [
        modality
        for modality in analysis.modalities
        if modality.negated
        and modality.span.start <= candidate.span.start < modality.span.end
    ]
    start = (
        max(containing_modalities, key=lambda item: item.span.start).span.start
        if containing_modalities
        else candidate.span.start
    )
    return analysis.source_text[start : candidate.scope.end]


def _context_applies_to(
    analysis: RequirementSemanticAnalysis,
    candidate: ContextCandidate,
) -> str | None:
    if _context_leads_action(analysis, candidate):
        following_modalities = [
            item for item in analysis.modalities
            if item.span.start >= candidate.clause.end and item.scope is not None
            and not re.search(r'[.;\n]', analysis.source_text[candidate.clause.end:item.span.start])
        ]
        if following_modalities:
            return min(following_modalities, key=lambda item: item.span.start).scope.text
        following = _following_context_action(analysis.source_text, candidate.clause.end)
        if following is not None:
            return following.text
    preceding = _preceding_modality_scope(analysis, candidate.marker.start)
    if preceding is not None:
        return preceding
    if candidate.marker.start == 0:
        following = _following_context_action(analysis.source_text, candidate.clause.end)
        if following is not None:
            return following.text
    prefix_start = candidate.marker.start
    while prefix_start > 0 and analysis.source_text[prefix_start - 1] not in ";.\n":
        prefix_start -= 1
    field_start, _ = source_field_value_bounds(
        analysis.source_text,
        candidate.marker.start,
    )
    prefix_start = max(prefix_start, field_start)
    prefix = analysis.source_text[prefix_start : candidate.marker.start].strip(" ,:;-")
    if prefix:
        return prefix
    return None


def _context_leads_action(
    analysis: RequirementSemanticAnalysis,
    candidate: ContextCandidate,
) -> bool:
    if re.search(r'[.!?]\s*$', analysis.source_text[:candidate.marker.start]):
        return True
    preceding = [
        modality
        for modality in analysis.modalities
        if modality.span.end <= candidate.marker.start
    ]
    if not preceding:
        return candidate.marker.start == 0
    modality = max(preceding, key=lambda item: item.span.end)
    between = analysis.source_text[modality.span.end : candidate.marker.start]
    normalized = re.sub(r"[,\s]+", " ", between).strip().lower()
    return not normalized or bool(re.search(r"\b(?:and|or)$", normalized))


def _following_context_action(text: str, start: int) -> SourceSpan | None:
    cursor = start
    while cursor < len(text) and (text[cursor].isspace() or text[cursor] in ",:"):
        cursor += 1
    if cursor >= len(text):
        return None
    boundary = len(text)
    for index in range(cursor, len(text)):
        if text[index] in ";.\n":
            boundary = index
            break
    trailing_qualifier = re.search(
        r",\s+(?:following|subject\s+to|except|unless|provided\s+that)\b",
        text[cursor:boundary],
        re.IGNORECASE,
    )
    if trailing_qualifier is not None:
        boundary = cursor + trailing_qualifier.start()
    end = boundary
    while end > cursor and text[end - 1].isspace():
        end -= 1
    return SourceSpan(start=cursor, end=end, text=text[cursor:end]) if end > cursor else None


def _canonical_dates(
    analysis: RequirementSemanticAnalysis,
    *,
    regions: list[RequirementSourceRegion] | None = None,
) -> list[RequirementScopedText]:
    result: list[RequirementScopedText] = []
    for candidate in analysis.dates:
        applies_to = _date_applies_to(analysis, candidate.span)
        result.append(
            RequirementScopedText(
                text=candidate.span.text,
                applies_to=applies_to or candidate.span.text,
                scope_ref=(
                    _scope_ref_for_span(
                        analysis.source_text,
                        scope_span,
                        regions,
                    )
                    if regions is not None
                    and (
                        scope_span := _nearest_exact_span(
                            analysis.source_text,
                            applies_to or candidate.span.text,
                            pivot=candidate.span.start,
                        )
                    ) is not None
                    else None
                ),
            )
        )
    return _deduplicate_scoped_text(result)


def _date_applies_to(
    analysis: RequirementSemanticAnalysis,
    span: SourceSpan,
) -> str | None:
    candidate = next(
        (
            item
            for item in analysis.dates
            if item.span.start == span.start and item.span.end == span.end
        ),
        None,
    )
    if candidate is None or candidate.scope is None:
        return None
    before = analysis.source_text[candidate.scope.start : span.start]
    before = re.sub(r"^(?:or|and)\s*,?\s*", "", before.strip(), flags=re.IGNORECASE)
    before = before.rstrip(" ,:;-")
    after = analysis.source_text[span.end : candidate.scope.end].strip(" ,:;-")
    if span.text.casefold().startswith("annual target") and re.match(
        r"^for\s+", after, re.IGNORECASE
    ):
        return re.sub(r"^for\s+", "", after, flags=re.IGNORECASE).strip() or None
    preceding_scope = _preceding_modality_scope(analysis, span.start)
    if span.text.casefold().startswith("per ") and preceding_scope is not None:
        return preceding_scope
    if before:
        modal = list(_ENGLISH_MODAL_TOKEN_RE.finditer(before))
        if modal:
            before = before[modal[-1].end():].strip()
        before = re.sub(
            r"\s+\b(?:from|in|during|for|over|within)\b\s*$",
            "",
            before,
            flags=re.IGNORECASE,
        ).strip()
        if before.casefold().endswith(" used") and " all " in before.casefold():
            before = re.split(r"\ball\s+", before, flags=re.IGNORECASE)[-1].strip()
    if before:
        return before
    return after or None


def _deduplicate_scoped_text(
    values: Iterable[RequirementScopedText],
) -> list[RequirementScopedText]:
    result: list[RequirementScopedText] = []
    seen: set[tuple[str, str]] = set()
    for value in values:
        key = (value.text, value.applies_to)
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def _candidate_issues(
    kind: str,
    start: int,
    ambiguous: bool,
    candidate_flags: Iterable[str],
    *,
    anomalies: list[str],
    flags: list[str],
    review_reasons: list[str],
) -> None:
    if ambiguous:
        _semantic_issue(
            kind,
            f"ambiguous:{start}",
            anomalies=anomalies,
            flags=flags,
            review_reasons=review_reasons,
        )
    for candidate_flag in candidate_flags:
        _semantic_issue(
            kind,
            f"{candidate_flag}:{start}",
            anomalies=anomalies,
            flags=flags,
            review_reasons=review_reasons,
        )


def _semantic_issue(
    kind: str,
    detail: str,
    *,
    anomalies: list[str],
    flags: list[str],
    review_reasons: list[str],
) -> None:
    issue = f"semantic_{kind}:{detail}"
    _append_unique(anomalies, issue)
    _append_unique(flags, issue)
    _append_unique(review_reasons, issue)


def _semantic_applies_to(
    analysis: RequirementSemanticAnalysis,
    span: SourceSpan,
) -> str | None:
    prefix_start = max(
        analysis.source_text.rfind(";", 0, span.start),
        analysis.source_text.rfind(".", 0, span.start),
        analysis.source_text.rfind("\n", 0, span.start),
    ) + 1
    prefix = analysis.source_text[prefix_start:span.start]
    copular_subject = re.search(
        r"(?P<subject>(?:the|a|an)\s+[^,;:.]{1,100}?)\s+"
        r"(?:(?:shall|must|should|may)\s+)?(?:be|is|are)\s*$",
        prefix,
        re.IGNORECASE,
    )
    if copular_subject is not None:
        return copular_subject.group("subject").strip()
    if re.search(r"\bwith\s*$", prefix, re.IGNORECASE):
        preceding = _preceding_modality_scope(analysis, span.start)
        if preceding is not None:
            return preceding
    for modality in analysis.modalities:
        if (
            modality.scope is not None
            and modality.scope.start <= span.start
            and span.end <= modality.scope.end
        ):
            return modality.scope.text
    for context in [*analysis.conditions, *analysis.exceptions]:
        if context.clause.start <= span.start and span.end <= context.clause.end:
            return context.clause.text
    for negation in analysis.negations:
        if (
            negation.scope is not None
            and negation.scope.start <= span.start
            and span.end <= negation.scope.end
        ):
            return negation.scope.text
    return _local_threshold_context(analysis.source_text, span)


def _local_threshold_context(text: str, span: SourceSpan) -> str | None:
    field_start, field_end = source_field_value_bounds(text, span.start)
    start = span.start
    while start > field_start:
        character = text[start - 1]
        if character in ";:\n" or (
            character == "," and not _numeric_internal_comma(text, start - 1)
        ):
            break
        if character == "." and not _numeric_internal_dot(text, start - 1):
            break
        start -= 1
    end = span.end
    while end < field_end:
        character = text[end]
        if character in ";\n" or (
            character == "," and not _numeric_internal_comma(text, end)
        ):
            break
        if character == "." and not _numeric_internal_dot(text, end):
            break
        end += 1
    value = text[start:end].strip(" ,:;-")
    value = re.sub(r"^(?:or|and)\s*,?\s*", "", value, flags=re.IGNORECASE)
    return value or None


def _numeric_internal_dot(text: str, index: int) -> bool:
    return (
        0 < index < len(text) - 1
        and text[index - 1].isdigit()
        and text[index + 1].isdigit()
    )


def _numeric_internal_comma(text: str, index: int) -> bool:
    return (
        0 < index < len(text) - 1
        and text[index - 1].isdigit()
        and text[index + 1].isdigit()
    )


def _preceding_modality_scope(
    analysis: RequirementSemanticAnalysis,
    marker_start: int,
) -> str | None:
    candidates = [
        modality
        for modality in analysis.modalities
        if modality.scope is not None and modality.span.start < marker_start
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda item: item.span.start).scope.text  # type: ignore[union-attr]


def _source_field_role_at(source_text: str, position: int) -> str | None:
    role_by_label = {
        "indicator": "indicator_text",
        "requirement": "requirement_value",
        "applicability": "applicability",
    }
    role: str | None = None
    for match in _SOURCE_FIELD_ROLE_RE.finditer(source_text):
        if match.end() > position:
            break
        role = role_by_label[match.group("label").casefold()]
    return role


def _same_threshold_candidate(first: object, second: object) -> bool:
    return all(
        getattr(first, attribute) == getattr(second, attribute)
        for attribute in ("operator", "normalized_value", "unit")
    )


def _expanded_threshold_text(
    source_text: str,
    span: SourceSpan,
    *,
    field_end: int,
) -> str:
    tail = source_text[span.end:field_end]
    match = re.match(
        r"(?P<measure>(?:\s+[A-Za-z][A-Za-z-]*){1,5})"
        r"(?=\s+(?:in|during|for|over|within|per|after|before|until|if|when|where)\b|[.,;:]|$)",
        tail,
        re.IGNORECASE,
    )
    return span.text + (match.group("measure") if match is not None else "")


def _covering_formal_region_ids(
    source_text: str,
    span: SourceSpan,
    regions: list[RequirementSourceRegion],
) -> list[str]:
    formal = [region for region in regions if region.role in _SEMANTIC_SCOPE_ROLES]
    if not formal:
        return []

    expected_role = _source_field_role_at(source_text, span.start)
    if expected_role is not None:
        exact_role_matches = [
            region.segment_id
            for region in formal
            if region.role == expected_role
            and span.text in (region.source_text or "")
        ]
        if exact_role_matches:
            return exact_role_matches[:1]

    combined_parts: list[str] = []
    intervals: list[tuple[int, int, str]] = []
    cursor = 0
    for region in formal:
        if combined_parts:
            combined_parts.append(" ")
            cursor += 1
        region_text = region.source_text or ""
        start = cursor
        combined_parts.append(region_text)
        cursor += len(region_text)
        intervals.append((start, cursor, region.segment_id))
    combined = "".join(combined_parts)
    source_offset = combined.find(source_text)
    if source_offset >= 0:
        absolute_start = source_offset + span.start
        absolute_end = source_offset + span.end
        if combined[absolute_start:absolute_end] == span.text:
            return [
                segment_id
                for start, end, segment_id in intervals
                if start < absolute_end and absolute_start < end
            ]

    # Fallback for a formal region whose text contains extra metadata or when
    # the assembler normalized only the join between physical segments.
    exact = [
        region.segment_id
        for region in formal
        if span.text in (region.source_text or "")
    ]
    return exact[:1]


def _source_anchors_for_span(
    source_text: str,
    span: SourceSpan,
    regions: list[RequirementSourceRegion],
) -> list[RequirementTextAnchor]:
    """Map one semantic source span back to exact per-region offsets."""

    formal = [region for region in regions if region.role in _SEMANTIC_SCOPE_ROLES]
    expected_role = _source_field_role_at(source_text, span.start)
    direct_role_rank = {
        "indicator_text": 0,
        "requirement_value": 1,
        "applicability": 2,
        "requirement_continuation": 3,
        "normative_text": 4,
    }
    direct_matches: list[tuple[int, RequirementSourceRegion, int]] = []
    for region in formal:
        region_text = region.source_text or ""
        start = region_text.find(span.text)
        while start >= 0:
            direct_matches.append((
                direct_role_rank.get(region.role, 99),
                region,
                start,
            ))
            start = region_text.find(span.text, start + 1)
    if direct_matches:
        if expected_role is not None:
            expected_matches = [
                item for item in direct_matches if item[1].role == expected_role
            ]
            if expected_matches:
                direct_matches = expected_matches
        best_rank = min(item[0] for item in direct_matches)
        best = [item for item in direct_matches if item[0] == best_rank]
        if len(best) == 1:
            _, region, start = best[0]
            return [RequirementTextAnchor(
                source_segment_id=region.segment_id,
                start_char=start,
                end_char=start + len(span.text),
                text=span.text,
            )]

    combined_parts: list[str] = []
    intervals: list[tuple[int, int, RequirementSourceRegion]] = []
    cursor = 0
    for region in formal:
        if combined_parts:
            combined_parts.append(" ")
            cursor += 1
        region_text = region.source_text or ""
        start = cursor
        combined_parts.append(region_text)
        cursor += len(region_text)
        intervals.append((start, cursor, region))
    combined = "".join(combined_parts)
    source_offset = combined.find(source_text)
    if source_offset >= 0:
        absolute_start = source_offset + span.start
        absolute_end = source_offset + span.end
        if combined[absolute_start:absolute_end] == span.text:
            anchors: list[RequirementTextAnchor] = []
            for start, end, region in intervals:
                overlap_start = max(start, absolute_start)
                overlap_end = min(end, absolute_end)
                if overlap_start >= overlap_end:
                    continue
                local_start = overlap_start - start
                local_end = overlap_end - start
                region_text = region.source_text or ""
                anchors.append(RequirementTextAnchor(
                    source_segment_id=region.segment_id,
                    start_char=local_start,
                    end_char=local_end,
                    text=region_text[local_start:local_end],
                ))
            if anchors:
                return anchors

    matches = [(region, start) for _, region, start in direct_matches]
    if len(matches) != 1:
        return []
    region, start = matches[0]
    return [RequirementTextAnchor(
        source_segment_id=region.segment_id,
        start_char=start,
        end_char=start + len(span.text),
        text=span.text,
    )]


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _source_regions(
    native: NativeRequirement,
    anomalies: list[str],
) -> list[RequirementSourceRegion]:
    requirement_key = _requirement_key(native)
    role_counts: dict[tuple[int, str], int] = defaultdict(int)
    result: list[RequirementSourceRegion] = []
    linked_footnote_markers = [
        *native.footnote_markers,
        *(candidate.marker for candidate in native.footnote_link_candidates),
    ]
    for span in native.source_segments:
        role = span.role if span.role in _SOURCE_ROLES else "other"
        if role == "other" and span.role != "other":
            anomalies.append(f"unrecognized_source_role:{span.role}")
        if not _valid_span_coordinates(span):
            anomalies.append(
                f"invalid_source_bbox:p{span.page_index + 1}:{span.role}"
            )
            continue
        key = (span.page_index, role)
        role_counts[key] += 1
        segment_id = (
            f"req-{requirement_key}-p{span.page_index + 1:04d}-"
            f"{role}-{role_counts[key]:02d}"
        )
        native_text = span.source_text
        text = _semantic_source_text(
            native_text,
            role=role,
            footnote_markers=linked_footnote_markers,
        )
        resolved = bool(text.strip()) and bool(span.native_object_ids) and role != "other"
        if not text.strip():
            anomalies.append(f"empty_source_text:{segment_id}")
        if not span.native_object_ids:
            anomalies.append(f"missing_native_refs:{segment_id}")
        result.append(
            RequirementSourceRegion(
                segment_id=segment_id,
                page_index=span.page_index,
                page_number=span.page_number,
                bbox=BoundingBox(
                    x0=span.bbox[0],
                    y0=span.bbox[1],
                    x1=span.bbox[2],
                    y1=span.bbox[3],
                ),
                role=role,
                source_text=text,
                native_text=native_text if native_text.strip() else None,
                resolved_text=text if resolved else None,
                resolution_status=(
                    ResolutionStatus.RESOLVED
                    if resolved
                    else ResolutionStatus.AMBIGUOUS
                ),
                requires_human_review=not resolved,
                native_object_refs=list(span.native_object_ids),
            )
        )
    return result


def _semantic_source_text(
    text: str,
    *,
    role: str,
    footnote_markers: Iterable[str],
) -> str:
    """Separate linked superscript markers from the semantic text view.

    ``native_text`` remains byte-for-byte available on the source region.  We
    only remove digit markers that are attached to a preceding source token in
    formal normative roles.  A bare leading footnote label is also excluded
    from the definition view, while bracketed labels such as ``[22]`` remain
    explicit source syntax.
    """

    markers = {
        marker.strip()
        for marker in footnote_markers
        if marker.strip().isdigit()
    }
    if role == "footnote":
        cleaned = text
        for marker in sorted(markers, key=len, reverse=True):
            cleaned = re.sub(
                rf"^\s*{re.escape(marker)}(?:\s+|(?=\D))",
                "",
                cleaned,
                count=1,
            )
        return cleaned
    if role not in _ATTACHED_FOOTNOTE_CLEAN_ROLES:
        return text
    cleaned = text
    for marker in sorted(markers, key=len, reverse=True):
        cleaned = re.sub(
            rf"(?<=[^\s\[]){re.escape(marker)}(?=$|\s|[.,;:)\]])",
            "",
            cleaned,
        )
    return cleaned


def _actions(
    values: Iterable[str],
    *,
    expected_case: Literal["lower", "upper"],
    source_segment_ids: list[str],
    anomaly_prefix: str,
    anomalies: list[str],
) -> list[RequirementAction]:
    materialized = list(values)
    result: list[RequirementAction] = []
    one_to_one_provenance = len(materialized) == len(source_segment_ids)
    for index, raw_value in enumerate(materialized, start=1):
        value = raw_value.strip()
        match = _ACTION_RE.match(value)
        if match:
            marker, text = match.group(1), match.group(2).strip()
            correct_case = (
                marker.islower() if expected_case == "lower" else marker.isupper()
            )
            if not correct_case:
                anomalies.append(f"{anomaly_prefix}_marker_case:{index}:{marker}")
        else:
            marker, text = None, value
            anomalies.append(f"{anomaly_prefix}_marker_missing:{index}")
        if not text:
            anomalies.append(f"{anomaly_prefix}_text_missing:{index}")
        result.append(
            RequirementAction(
                marker=marker,
                text=text,
                source_segment_ids=(
                    [source_segment_ids[index - 1]]
                    if one_to_one_provenance
                    else list(source_segment_ids)
                ),
            )
        )
    if result and not source_segment_ids:
        anomalies.append(f"{anomaly_prefix}_provenance_missing")
    return result


def _status(
    native: NativeRequirement,
    regions: list[RequirementSourceRegion],
    anomalies: list[str],
) -> RequirementStatus:
    requirement_id = native.requirement_id.strip()
    normative_text = native.normative_text.strip()
    if not requirement_id:
        anomalies.append("missing_requirement_id")
    if not normative_text:
        anomalies.append("missing_normative_text")
    if not requirement_id or not normative_text:
        return RequirementStatus.ABSTAIN

    direct_id_regions = [
        region for region in regions if region.role == "requirement_id"
    ]
    continuation_anchors = [
        region for region in regions if region.role == "continuation_anchor"
    ]
    id_regions = [*direct_id_regions, *continuation_anchors]
    formal_regions = [region for region in regions if region.role in _NORMATIVE_ROLES]
    if not id_regions:
        anomalies.append("missing_requirement_id_provenance")
    elif not any(
        _clean(region.source_text or "") == _clean(requirement_id)
        for region in id_regions
    ):
        anomalies.append("requirement_id_provenance_mismatch")
    if continuation_anchors and not direct_id_regions:
        anomalies.append("requirement_identity_from_preceding_page")
    if not formal_regions:
        anomalies.append("missing_formal_provenance")
    elif not _formal_text_supports(
        normative_text,
        formal_regions,
        ignored_attached_markers=native.footnote_markers,
    ):
        anomalies.append("normative_text_provenance_mismatch")

    unresolved = any(
        region.requires_human_review
        or region.resolution_status != ResolutionStatus.RESOLVED
        for region in regions
    )
    blocking_anomalies = [
        anomaly
        for anomaly in anomalies
        if not (
            native.family is TemplateFamily.AUDIT_MATRIX
            and anomaly.startswith("auditor_action_marker_case:")
        )
    ]
    if (
        blocking_anomalies
        or unresolved
        or not id_regions
        or not formal_regions
    ):
        return RequirementStatus.REVIEW_REQUIRED
    return RequirementStatus.ACCEPTED


def _check_native_ref_role_separation(
    regions: Iterable[RequirementSourceRegion],
    anomalies: list[str],
) -> None:
    buckets_by_ref: dict[str, set[str]] = defaultdict(set)
    for region in regions:
        bucket = (
            "formal"
            if region.role in _NORMATIVE_ROLES | {"requirement_id", "applicability"}
            else "client"
            if region.role == "client_action"
            else "auditor"
            if region.role == "auditor_action"
            else "context"
        )
        for native_ref in region.native_object_refs:
            buckets_by_ref[native_ref].add(bucket)
    for native_ref, buckets in sorted(buckets_by_ref.items()):
        if len(buckets) > 1:
            anomalies.append(
                f"native_ref_reused_across_roles:{native_ref}:{','.join(sorted(buckets))}"
            )


def _formal_text_supports(
    normative_text: str,
    regions: Iterable[RequirementSourceRegion],
    *,
    ignored_attached_markers: Iterable[str] = (),
) -> bool:
    evidence = _clean(" ".join(region.source_text or "" for region in regions))
    normative = _clean(normative_text)
    if evidence and normative and (normative in evidence or evidence in normative):
        return True

    # Some PDF text layers attach an unbracketed footnote number directly to
    # the preceding token even though the assembled semantic text omits it.
    # Apply that repair only as a fallback: removing a marker before checking
    # the exact source form caused valid bracketed references such as ``[84]``
    # to fail provenance despite an exact normative_text region being present.
    for marker in dict.fromkeys(ignored_attached_markers):
        cleaned_marker = marker.strip()
        if not cleaned_marker or not cleaned_marker.isdigit():
            continue
        evidence = re.sub(
            rf"(?<=\S){re.escape(cleaned_marker)}(?=\s|[.,;:)\]])",
            "",
            evidence,
        )
    return bool(evidence and normative) and (
        normative in evidence or evidence in normative
    )


def _valid_span_coordinates(span: RequirementSourceSpan) -> bool:
    x0, y0, x1, y1 = span.bbox
    return span.page_index >= 0 and x0 >= 0 and y0 >= 0 and x1 > x0 and y1 > y0


def _requirement_key(native: NativeRequirement) -> str:
    normalized = _SAFE_ID_RE.sub("-", native.requirement_id.casefold()).strip("-")
    if normalized:
        return normalized
    material = "|".join(
        [native.family.value, native.normative_text]
        + [
            f"{span.page_index}:{span.role}:{span.bbox}:{span.source_text}"
            for span in native.source_segments
        ]
    )
    return f"unresolved-{hashlib.sha256(material.encode('utf-8')).hexdigest()[:12]}"


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _clean(value: str) -> str:
    cleaned = _SPACE_RE.sub(" ", value).strip()
    cleaned = re.sub(r"([≤≥])\s+(?=\d)", r"\1", cleaned)
    cleaned = re.sub(r"([≤≥<>]=?\d+)\s+(\d+%)", r"\1\2", cleaned)
    # Visual list bullets are retained in source evidence but intentionally
    # omitted from semantic text.  Normalize only marker-shaped tokens after a
    # list-introducing delimiter so ordinary prose remains untouched.
    cleaned = re.sub(
        r"(^|[;:,])\s+(?:o|[•●▪◦○])\s+(?=[A-Z0-9≤≥])",
        r"\1 ",
        cleaned,
    )
    return cleaned
