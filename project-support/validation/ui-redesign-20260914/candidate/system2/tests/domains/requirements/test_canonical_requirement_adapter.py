from __future__ import annotations

from pdf_extraction.models import RequirementStatus, ResolutionStatus
from pdf_extraction.domains.requirements import (
    NativeRequirement,
    RequirementSourceSpan,
    TemplateFamily,
    apply_family_trust,
    canonicalize_native_requirement,
    canonicalize_native_requirements,
)


def _span(
    role: str,
    text: str,
    *,
    page_index: int = 4,
    bbox: tuple[float, float, float, float] = (20, 30, 500, 60),
    refs: tuple[str, ...] = ("native-1",),
) -> RequirementSourceSpan:
    return RequirementSourceSpan(
        role=role,
        page_index=page_index,
        bbox=bbox,
        source_text=text,
        native_object_ids=refs,
    )


def test_valid_candidate_becomes_accepted_with_deterministic_provenance() -> None:
    native = NativeRequirement(
        requirement_id="1.2.3",
        family=TemplateFamily.SINGLE_COLUMN_INDICATORS,
        normative_text="The UoC shall maintain records.",
        indicator_text="The UoC shall maintain records.",
        source_segments=[
            _span(
                "requirement_id",
                "1.2.3",
                bbox=(20, 30, 60, 45),
                refs=("id-1",),
            ),
            _span("normative_text", "The UoC shall maintain records."),
        ],
    )

    first = canonicalize_native_requirement(
        native,
        source_document="standard.pdf",
        source_authority="Standards body",
    )
    second = canonicalize_native_requirement(
        native,
        source_document="standard.pdf",
        source_authority="Standards body",
    )

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.status == RequirementStatus.ACCEPTED
    assert first.requirement_form == "normative_indicator"
    assert first.source_document == "standard.pdf"
    assert first.source_authority == "Standards body"
    assert [region.segment_id for region in first.source_segments] == [
        "req-1-2-3-p0005-requirement_id-01",
        "req-1-2-3-p0005-normative_text-01",
    ]
    assert first.source_segments[1].page_index == 4
    assert first.source_segments[1].page_number == 5
    assert first.source_segments[1].bbox.as_list() == [20.0, 30.0, 500.0, 60.0]
    assert first.source_segments[1].source_text == "The UoC shall maintain records."
    assert first.source_segments[1].native_object_refs == ["native-1"]
    assert first.source_segments[1].resolution_status == ResolutionStatus.RESOLVED
    assert [(item.token, item.type, item.scope) for item in first.modalities] == [
        ("shall", "obligation", "maintain records")
    ]
    modality_scope = first.modalities[0].scope_ref
    assert modality_scope is not None
    assert (modality_scope.kind, modality_scope.target) == (
        "source_span",
        "normative_text",
    )
    assert [
        (
            item.source_segment_id,
            item.start_char,
            item.end_char,
            item.text,
        )
        for item in modality_scope.anchors
    ] == [(
        "req-1-2-3-p0005-normative_text-01",
        14,
        30,
        "maintain records",
    )]
    assert first.semantic_input is not None
    assert [
        (item.role, item.text, item.source_segment_ids)
        for item in first.semantic_input.core_fragments
    ] == [(
        "normative_text",
        "The UoC shall maintain records.",
        ["req-1-2-3-p0005-normative_text-01"],
    )]
    assert len(first.semantic_input.fingerprint) == 64


def test_provenance_normalization_accepts_visual_list_and_split_percent_tokens() -> None:
    native = NativeRequirement(
        requirement_id="2.6.13",
        family=TemplateFamily.ID_NORMATIVE_WITH_CONTEXT,
        normative_text=(
            "The UoC shall act when the value is ≥15%: Total Nitrogen; and, "
            "Total Phosphorous."
        ),
        source_segments=[
            _span("requirement_id", "2.6.13", refs=("id-visual",)),
            _span(
                "normative_text",
                "The UoC shall act when the value is ≥1 5%: o Total Nitrogen; "
                "and, o Total Phosphorous.",
                refs=("formal-visual",),
            ),
        ],
    )

    requirement = canonicalize_native_requirement(native)

    assert "normative_text_provenance_mismatch" not in requirement.source_anomalies


def test_threshold_scope_stops_at_inline_source_field_label() -> None:
    text = "Requirement: < 1.2 Applicability: All"
    native = NativeRequirement(
        requirement_id="4.2.1",
        family=TemplateFamily.AUDIT_MATRIX,
        normative_text=text,
        source_segments=[
            _span("requirement_id", "4.2.1", refs=("id-field-boundary",)),
            _span("normative_text", text, refs=("formal-field-boundary",)),
        ],
    )

    requirement = canonicalize_native_requirement(native, language="en")

    assert len(requirement.thresholds) == 1
    assert requirement.thresholds[0].raw_text == "< 1.2"
    assert requirement.thresholds[0].unit is None
    assert requirement.thresholds[0].applies_to == "< 1.2"
    assert "Applicability" not in requirement.thresholds[0].applies_to


def test_repeated_threshold_values_keep_distinct_comma_bounded_scopes() -> None:
    text = (
        "Requirement: All individual scores ≥ 6, and biomass score ≥ 6 "
        "Applicability: All"
    )
    native = NativeRequirement(
        requirement_id="4.3.2",
        family=TemplateFamily.AUDIT_MATRIX,
        normative_text=text,
        source_segments=[
            _span("requirement_id", "4.3.2", refs=("id-threshold-scopes",)),
            _span("normative_text", text, refs=("formal-threshold-scopes",)),
        ],
    )

    requirement = canonicalize_native_requirement(native, language="en")

    assert [item.raw_text for item in requirement.thresholds] == ["≥ 6", "≥ 6"]
    assert [item.applies_to for item in requirement.thresholds] == [
        "All individual scores ≥ 6",
        "biomass score ≥ 6",
    ]


def test_clause_structure_uses_exact_root_when_source_has_no_explicit_list() -> None:
    text = "The operator shall keep complete inspection records."
    native = NativeRequirement(
        requirement_id="2.1.7",
        family=TemplateFamily.SINGLE_COLUMN_INDICATORS,
        normative_text=text,
        source_segments=[
            _span("requirement_id", "2.1.7", refs=("id-root",)),
            _span("normative_text", text, refs=("body-root",)),
        ],
    )

    requirement = canonicalize_native_requirement(native)

    assert len(requirement.clauses) == 1
    assert requirement.clauses[0].text == requirement.normative_text
    assert requirement.clauses[0].parent_clause_id is None
    assert requirement.clauses[0].marker is None
    assert requirement.clauses[0].joins_next is None


def test_clause_structure_preserves_explicit_bullets_and_source_connectors() -> None:
    normative = "The operator shall monitor: Nitrogen; and, Phosphorous."
    native = NativeRequirement(
        requirement_id="2.1.8",
        family=TemplateFamily.ID_NORMATIVE_WITH_CONTEXT,
        normative_text=normative,
        source_segments=[
            _span("requirement_id", "2.1.8", refs=("id-list",)),
            _span(
                "normative_text",
                "The operator shall monitor: o Nitrogen; and, o Phosphorous.",
                refs=("body-list",),
            ),
        ],
    )

    requirement = canonicalize_native_requirement(native)

    assert [(item.marker, item.text, item.joins_next) for item in requirement.clauses] == [
        (None, "The operator shall monitor:", None),
        ("o", "Nitrogen;", "and"),
        ("o", "Phosphorous.", None),
    ]
    assert all(
        item.parent_clause_id == requirement.clauses[0].clause_id
        for item in requirement.clauses[1:]
    )


def test_clause_structure_rolls_nested_connector_up_to_explicit_parent() -> None:
    text = (
        "The operator shall ensure: a. records include: o date; and, o place; "
        "and b. records are retained."
    )
    native = NativeRequirement(
        requirement_id="2.1.9",
        family=TemplateFamily.ID_NORMATIVE_WITH_CONTEXT,
        normative_text=text,
        source_segments=[
            _span("requirement_id", "2.1.9", refs=("id-nested",)),
            _span("normative_text", text, refs=("body-nested",)),
        ],
    )

    requirement = canonicalize_native_requirement(native)
    root, first, date, place, second = requirement.clauses

    assert first.parent_clause_id == root.clause_id
    assert date.parent_clause_id == first.clause_id
    assert place.parent_clause_id == first.clause_id
    assert second.parent_clause_id == root.clause_id
    assert date.joins_next == "and"
    assert place.joins_next is None
    assert first.joins_next == "and"


def test_clause_structure_fails_closed_when_same_marker_nesting_is_ambiguous() -> None:
    text = "The operator shall ensure: o records include: o date; o place."
    native = NativeRequirement(
        requirement_id="2.1.10",
        family=TemplateFamily.ID_NORMATIVE_WITH_CONTEXT,
        normative_text=text,
        source_segments=[
            _span("requirement_id", "2.1.10", refs=("id-ambiguous",)),
            _span("normative_text", text, refs=("body-ambiguous",)),
        ],
    )

    requirement = canonicalize_native_requirement(native)

    assert requirement.status == RequirementStatus.REVIEW_REQUIRED
    assert len(requirement.clauses) == 1
    assert requirement.clauses[0].text == requirement.normative_text
    assert "clause_structure_unresolved:same_marker_nested_list_ambiguous" in (
        requirement.source_anomalies
    )


def test_audit_actions_strip_markers_and_reference_their_own_role_region() -> None:
    native = NativeRequirement(
        requirement_id="2.1.1",
        family=TemplateFamily.AUDIT_MATRIX,
        normative_text="Indicator: Records are available.\nRequirement: Yes",
        indicator_text="Records are available.",
        requirement_value="Yes",
        applicability="All sites",
        client_actions=["a. Maintain records.", "b. Retain receipts."],
        auditor_actions=["A. Review records.", "B. Verify receipts."],
        source_segments=[
            _span("requirement_id", "2.1.1", refs=("id-2",)),
            _span(
                "normative_text",
                "Indicator: Records are available. Requirement: Yes Applicability: All sites",
                refs=("formal-2",),
            ),
            _span(
                "client_action",
                "a. Maintain records. b. Retain receipts.",
                refs=("client-2",),
            ),
            _span(
                "auditor_action",
                "A. Review records. B. Verify receipts.",
                refs=("auditor-2",),
            ),
        ],
    )

    requirement = canonicalize_native_requirement(native)
    regions = {region.role: region.segment_id for region in requirement.source_segments}

    assert requirement.status == RequirementStatus.ACCEPTED
    assert requirement.applicability == ["All sites"]
    assert [(item.marker, item.text) for item in requirement.client_actions] == [
        ("a", "Maintain records."),
        ("b", "Retain receipts."),
    ]
    assert [(item.marker, item.text) for item in requirement.auditor_actions] == [
        ("A", "Review records."),
        ("B", "Verify receipts."),
    ]
    assert all(
        action.source_segment_ids == [regions["client_action"]]
        for action in requirement.client_actions
    )
    assert all(
        action.source_segment_ids == [regions["auditor_action"]]
        for action in requirement.auditor_actions
    )
    assert requirement.semantic_input is not None
    assert [item.role for item in requirement.semantic_input.core_fragments] == [
        "indicator_text",
        "requirement_value",
    ]
    assert [item.text for item in requirement.semantic_input.qualifier_fragments] == [
        "All sites"
    ]
    assert all(
        item.source_segment_ids == [regions["normative_text"]]
        for item in [
            *requirement.semantic_input.core_fragments,
            *requirement.semantic_input.qualifier_fragments,
        ]
    )


def test_action_level_regions_are_bound_one_to_one() -> None:
    native = NativeRequirement(
        requirement_id="2.1.2",
        family=TemplateFamily.AUDIT_MATRIX,
        normative_text="Indicator: Records exist.\nRequirement: Yes\nApplicability: All",
        indicator_text="Records exist.",
        requirement_value="Yes",
        applicability="All",
        client_actions=["a. Keep records.", "b. Retain receipts."],
        source_segments=[
            _span("requirement_id", "2.1.2", refs=("id-action",)),
            _span(
                "normative_text",
                "Indicator: Records exist. Requirement: Yes Applicability: All",
                refs=("formal-action",),
            ),
            _span("client_action", "a. Keep records.", refs=("client-a",)),
            _span("client_action", "b. Retain receipts.", refs=("client-b",)),
        ],
    )

    requirement = canonicalize_native_requirement(native)

    client_regions = [
        region.segment_id for region in requirement.source_segments
        if region.role == "client_action"
    ]
    assert [action.source_segment_ids for action in requirement.client_actions] == [
        [client_regions[0]],
        [client_regions[1]],
    ]


def test_legacy_indicator_plus_value_has_role_aware_semantic_input() -> None:
    native = NativeRequirement(
        requirement_id="2.1.2",
        family=TemplateFamily.LEGACY_INDICATOR_VALUE,
        normative_text="The operator shall keep records.\nAt least 5 years",
        indicator_text="The operator shall keep records.",
        requirement_value="At least 5 years",
        source_segments=[
            _span("requirement_id", "2.1.2", refs=("legacy-id",)),
            _span(
                "indicator_text",
                "The operator shall keep records.",
                refs=("legacy-indicator",),
            ),
            _span(
                "requirement_value",
                "At least 5 years",
                refs=("legacy-value",),
            ),
        ],
    )

    requirement = canonicalize_native_requirement(native)

    assert requirement.semantic_input is not None
    assert [
        (item.role, item.text)
        for item in requirement.semantic_input.core_fragments
    ] == [
        ("indicator_text", "The operator shall keep records."),
        ("requirement_value", "At least 5 years"),
    ]
    assert all(item.source_segment_ids for item in requirement.semantic_input.core_fragments)
    assert requirement.modalities[0].scope == "keep records"
    assert requirement.thresholds[0].raw_text == "At least 5 years"


def test_audit_zero_count_uses_indicator_context_and_value_cell_provenance() -> None:
    indicator = (
        "Number of mortalities [25] of endangered or red-listed [26] "
        "marine mammals or birds on the farm"
    )
    value = "0 (zero)"
    normative = (
        f"Indicator: {indicator}\nRequirement: {value}\nApplicability: All"
    )
    native = NativeRequirement(
        requirement_id="2.5.2",
        family=TemplateFamily.AUDIT_MATRIX,
        normative_text=normative,
        indicator_text=indicator,
        requirement_value=value,
        applicability="All",
        source_segments=[
            _span("requirement_id", "2.5.2", refs=("zero-id",)),
            _span("indicator_text", indicator, refs=("zero-indicator",)),
            _span("requirement_value", value, refs=("zero-value",)),
            _span("normative_text", normative, refs=("zero-formal",)),
        ],
    )

    requirement = canonicalize_native_requirement(native)

    assert len(requirement.thresholds) == 1
    threshold = requirement.thresholds[0]
    assert threshold.raw_text == "0 (zero)"
    assert threshold.operator == "eq"
    assert threshold.normalized_value == 0
    assert threshold.unit == "mortalities"
    assert threshold.applies_to == (
        "number of mortalities of endangered or red-listed marine mammals "
        "or birds on the farm"
    )
    value_region = next(
        item for item in requirement.source_segments
        if item.role == "requirement_value"
    )
    assert threshold.source_segment_ids == [value_region.segment_id]
    assert "semantic_threshold_from_indicator_value_structure" in (
        requirement.validation_flags
    )


def test_bare_quantity_in_requirement_value_cell_is_an_exact_threshold() -> None:
    indicator = "Percentage of medication events prescribed by a veterinarian"
    value = "100%"
    normative = f"Indicator: {indicator}\nRequirement: {value}\nApplicability: All"
    native = NativeRequirement(
        requirement_id="5.2.3",
        family=TemplateFamily.AUDIT_MATRIX,
        normative_text=normative,
        indicator_text=indicator,
        requirement_value=value,
        applicability="All",
        source_segments=[
            _span("requirement_id", "5.2.3", refs=("exact-id",)),
            _span("indicator_text", indicator, refs=("exact-indicator",)),
            _span("requirement_value", value, refs=("exact-value",)),
            _span("normative_text", normative, refs=("exact-formal",)),
        ],
    )

    requirement = canonicalize_native_requirement(native)

    assert requirement.status == RequirementStatus.ACCEPTED
    assert len(requirement.thresholds) == 1
    threshold = requirement.thresholds[0]
    assert threshold.raw_text == "100%"
    assert threshold.operator == "eq"
    assert threshold.normalized_value == 100
    assert threshold.unit == "%"
    assert threshold.applies_to == indicator
    assert threshold.scope_ref is not None
    assert (threshold.scope_ref.kind, threshold.scope_ref.target) == (
        "field",
        "indicator_text",
    )
    assert [item.text for item in threshold.scope_ref.anchors] == [indicator]
    assert threshold.scope_ref.anchors[0].source_segment_id == next(
        item.segment_id
        for item in requirement.source_segments
        if item.role == "indicator_text"
    )
    assert "semantic_threshold_exact_from_requirement_value" in (
        requirement.validation_flags
    )
    assert [item.text for item in requirement.applicability_evidence] == ["All"]
    applicability_anchor = requirement.applicability_evidence[0].anchors[0]
    applicability_region = next(
        item for item in requirement.source_segments
        if item.segment_id == applicability_anchor.source_segment_id
    )
    assert applicability_region.source_text[
        applicability_anchor.start_char:applicability_anchor.end_char
    ] == applicability_anchor.text == "All"


def test_legacy_zero_day_count_derives_period_and_measured_activity() -> None:
    indicator = (
        "Number of days in the production cycle when acoustic deterrent devices "
        "(ADDs) or acoustic harassment devices (AHDs) were used"
    )
    native = NativeRequirement(
        requirement_id="2.5.1",
        family=TemplateFamily.LEGACY_INDICATOR_VALUE,
        normative_text=f"{indicator}\n0",
        indicator_text=indicator,
        requirement_value="0",
        source_segments=[
            _span("requirement_id", "2.5.1", refs=("legacy-zero-id",)),
            _span("indicator_text", indicator, refs=("legacy-zero-indicator",)),
            _span("requirement_value", "0", refs=("legacy-zero-value",)),
        ],
    )

    requirement = canonicalize_native_requirement(native)

    assert [
        (
            item.raw_text,
            item.operator,
            item.normalized_value,
            item.unit,
            item.applies_to,
        )
        for item in requirement.thresholds
    ] == [(
        "0",
        "eq",
        0,
        "days per production cycle",
        "use of acoustic deterrent devices or acoustic harassment devices",
    )]


def test_legacy_zero_mortality_count_uses_explicit_indicator_object() -> None:
    indicator = (
        "Number of mortalities of endangered or red-listed marine mammals or "
        "birds on the farm"
    )
    native = NativeRequirement(
        requirement_id="2.5.2",
        family=TemplateFamily.LEGACY_INDICATOR_VALUE,
        normative_text=f"{indicator}\n0",
        indicator_text=indicator,
        requirement_value="0",
        source_segments=[
            _span("requirement_id", "2.5.2", refs=("legacy-mortality-id",)),
            _span(
                "indicator_text",
                indicator,
                refs=("legacy-mortality-indicator",),
            ),
            _span("requirement_value", "0", refs=("legacy-mortality-value",)),
        ],
    )

    requirement = canonicalize_native_requirement(native)

    assert requirement.thresholds[0].unit == "mortalities"
    assert requirement.thresholds[0].applies_to == (
        "endangered or red-listed marine mammals or birds on the farm"
    )


def test_structured_zero_rule_does_not_generalize_to_arbitrary_bare_zero() -> None:
    cases = [
        (TemplateFamily.AUDIT_MATRIX, "Water temperature", "0"),
        (TemplateFamily.AUDIT_MATRIX, "Number of mortalities", "0.5"),
        (TemplateFamily.SINGLE_COLUMN_INDICATORS, "Number of days", "0"),
    ]
    for index, (family, indicator, value) in enumerate(cases, start=1):
        normative = f"Indicator: {indicator}\nRequirement: {value}"
        native = NativeRequirement(
            requirement_id=f"9.9.{index}",
            family=family,
            normative_text=normative,
            indicator_text=indicator,
            requirement_value=value,
            source_segments=[
                _span(
                    "requirement_id",
                    f"9.9.{index}",
                    refs=(f"zero-negative-id-{index}",),
                ),
                _span(
                    "indicator_text",
                    indicator,
                    refs=(f"zero-negative-indicator-{index}",),
                ),
                _span(
                    "requirement_value",
                    value,
                    refs=(f"zero-negative-value-{index}",),
                ),
                _span(
                    "normative_text",
                    normative,
                    refs=(f"zero-negative-formal-{index}",),
                ),
            ],
        )

        requirement = canonicalize_native_requirement(native)

        assert not any(
            item.operator == "eq" and item.normalized_value == 0
            for item in requirement.thresholds
        )


def test_audit_action_actor_is_not_promoted_to_normative_subject() -> None:
    indicator = "Number of days when deterrent devices were used"
    normative = f"Indicator: {indicator}\nRequirement: 0\nApplicability: All"
    native = NativeRequirement(
        requirement_id="2.5.1",
        family=TemplateFamily.AUDIT_MATRIX,
        normative_text=normative,
        indicator_text=indicator,
        requirement_value="0",
        applicability="All",
        client_actions=[
            "a. Compile evidence showing that no devices were used by the farm."
        ],
        source_segments=[
            _span("requirement_id", "2.5.1", refs=("subject-id",)),
            _span("indicator_text", indicator, refs=("subject-indicator",)),
            _span("requirement_value", "0", refs=("subject-value",)),
            _span("normative_text", normative, refs=("subject-formal",)),
            _span(
                "client_action",
                "a. Compile evidence showing that no devices were used by the farm.",
                refs=("subject-action",),
            ),
        ],
    )

    requirement = canonicalize_native_requirement(native)

    assert requirement.normative_subjects == []
    assert requirement.normative_subject_evidence == []


def test_audit_subject_can_use_linked_footnote_but_not_farm_staff_or_cab() -> None:
    base = "Indicator: Training records\nRequirement: Yes\nApplicability: All"
    explicit = NativeRequirement(
        requirement_id="3.4.4",
        family=TemplateFamily.AUDIT_MATRIX,
        normative_text=base,
        indicator_text="Training records",
        requirement_value="Yes",
        source_segments=[
            _span("requirement_id", "3.4.4", refs=("subject-footnote-id",)),
            _span("normative_text", base, refs=("subject-footnote-formal",)),
            _span(
                "footnote",
                "The farm shall retain the signed training record.",
                refs=("subject-footnote",),
            ),
        ],
    )
    non_actor = NativeRequirement(
        requirement_id="3.4.5",
        family=TemplateFamily.AUDIT_MATRIX,
        normative_text=base,
        indicator_text="Training records",
        requirement_value="Yes",
        source_segments=[
            _span("requirement_id", "3.4.5", refs=("subject-negative-id",)),
            _span("normative_text", base, refs=("subject-negative-formal",)),
            _span(
                "auditor_action",
                "A. Interview farm staff and ask the CAB to review records.",
                refs=("subject-negative-action",),
            ),
        ],
    )

    explicit_requirement = canonicalize_native_requirement(explicit)
    non_actor_requirement = canonicalize_native_requirement(non_actor)

    assert explicit_requirement.normative_subjects == ["The farm"]
    assert [
        item.text for item in explicit_requirement.normative_subject_evidence
    ] == ["The farm"]
    assert (
        explicit_requirement.normative_subject_evidence[0].anchors[0].text
        == "The farm"
    )
    assert explicit_requirement.normative_subject_evidence[0].basis == "explicit"
    assert non_actor_requirement.normative_subjects == []


def test_non_audit_family_does_not_promote_action_actor_to_normative_subject() -> None:
    text = "The records shall be available."
    native = NativeRequirement(
        requirement_id="3.4.6",
        family=TemplateFamily.LEGACY_INDICATOR_VALUE,
        normative_text=f"{text}\nYes",
        indicator_text=text,
        requirement_value="Yes",
        client_actions=["a. The farm shall retain records."],
        source_segments=[
            _span("requirement_id", "3.4.6", refs=("legacy-subject-id",)),
            _span("indicator_text", text, refs=("legacy-subject-indicator",)),
            _span("requirement_value", "Yes", refs=("legacy-subject-value",)),
            _span(
                "client_action",
                "a. The farm shall retain records.",
                refs=("legacy-subject-action",),
            ),
        ],
    )

    requirement = canonicalize_native_requirement(native)

    assert requirement.normative_subjects == []


def test_non_audit_explicit_uoc_subject_is_source_backed() -> None:
    text = "The UoC shall maintain complete records."
    native = NativeRequirement(
        requirement_id="2.5.1",
        family=TemplateFamily.ID_NORMATIVE_WITH_CONTEXT,
        normative_text=text,
        source_segments=[
            _span("requirement_id", "2.5.1", refs=("uoc-id",)),
            _span("normative_text", text, refs=("uoc-formal",)),
            _span(
                "other",
                "The operator should consider additional guidance.",
                refs=("uoc-context",),
            ),
        ],
    )

    requirement = canonicalize_native_requirement(native)

    assert requirement.normative_subjects == ["The UoC"]
    assert [item.text for item in requirement.normative_subject_evidence] == ["The UoC"]
    evidence = requirement.normative_subject_evidence[0]
    assert evidence.basis == "explicit"
    assert evidence.anchors[0].text == "The UoC"
    assert evidence.source_segment_ids == [evidence.anchors[0].source_segment_id]


def test_explicit_english_modalities_are_local_and_do_not_scan_actions() -> None:
    native = NativeRequirement(
        requirement_id="3.2.1",
        family=TemplateFamily.ID_NORMATIVE_WITH_CONTEXT,
        normative_text=(
            "The operator shall not discharge waste. "
            "The authority may grant an exemption; staff should retain evidence."
        ),
        client_actions=["a. The client must send a copy."],
        source_segments=[
            _span("requirement_id", "3.2.1", refs=("id-3",)),
            _span(
                "normative_text",
                "The operator shall not discharge waste. The authority may grant an exemption; staff should retain evidence.",
                refs=("formal-3",),
            ),
            _span(
                "client_action",
                "a. The client must send a copy.",
                refs=("client-3",),
            ),
        ],
    )

    requirement = canonicalize_native_requirement(native)

    assert [(item.token, item.type, item.scope) for item in requirement.modalities] == [
        ("shall not", "prohibition", "discharge waste"),
        ("may", "permission", "grant an exemption"),
        ("should", "recommendation", "retain evidence"),
    ]
    assert all(item.token != "must" for item in requirement.modalities)


def test_missing_identity_or_text_abstains_and_incomplete_provenance_reviews() -> None:
    missing_id = NativeRequirement(
        requirement_id="",
        family=TemplateFamily.SINGLE_COLUMN_INDICATORS,
        normative_text="The operator shall keep records.",
        source_segments=[_span("normative_text", "The operator shall keep records.")],
    )
    missing_text = NativeRequirement(
        requirement_id="1.1.1",
        family=TemplateFamily.SINGLE_COLUMN_INDICATORS,
        normative_text="",
        source_segments=[_span("requirement_id", "1.1.1")],
    )
    missing_formal_region = NativeRequirement(
        requirement_id="1.1.2",
        family=TemplateFamily.SINGLE_COLUMN_INDICATORS,
        normative_text="The operator shall keep records.",
        source_segments=[_span("requirement_id", "1.1.2")],
    )
    missing_native_refs = NativeRequirement(
        requirement_id="1.1.3",
        family=TemplateFamily.SINGLE_COLUMN_INDICATORS,
        normative_text="The operator shall keep records.",
        source_segments=[
            _span("requirement_id", "1.1.3", refs=("id-4",)),
            _span("normative_text", "The operator shall keep records.", refs=()),
        ],
    )

    converted = canonicalize_native_requirements(
        [missing_id, missing_text, missing_formal_region, missing_native_refs]
    )

    assert [item.status for item in converted] == [
        RequirementStatus.ABSTAIN,
        RequirementStatus.ABSTAIN,
        RequirementStatus.REVIEW_REQUIRED,
        RequirementStatus.REVIEW_REQUIRED,
    ]
    assert "missing_requirement_id" in converted[0].source_anomalies
    assert "missing_normative_text" in converted[1].source_anomalies
    assert "missing_formal_provenance" in converted[2].source_anomalies
    assert any(
        anomaly.startswith("missing_native_refs:")
        for anomaly in converted[3].source_anomalies
    )


def test_action_without_expected_marker_is_preserved_but_requires_review() -> None:
    native = NativeRequirement(
        requirement_id="4.1.1",
        family=TemplateFamily.AUDIT_MATRIX,
        normative_text="Indicator: Records are available. Requirement: Yes",
        client_actions=["Maintain records."],
        source_segments=[
            _span("requirement_id", "4.1.1", refs=("id-5",)),
            _span(
                "normative_text",
                "Indicator: Records are available. Requirement: Yes",
                refs=("formal-5",),
            ),
            _span("client_action", "Maintain records.", refs=("client-5",)),
        ],
    )

    requirement = canonicalize_native_requirement(native)

    assert requirement.status == RequirementStatus.REVIEW_REQUIRED
    assert requirement.client_actions[0].marker is None
    assert requirement.client_actions[0].text == "Maintain records."
    assert "client_action_marker_missing:1" in requirement.source_anomalies


def test_audit_lowercase_cab_marker_is_preserved_as_nonblocking_source_anomaly() -> None:
    native = NativeRequirement(
        requirement_id="4.1.2",
        family=TemplateFamily.AUDIT_MATRIX,
        normative_text="Indicator: Records are available. Requirement: Yes",
        indicator_text="Records are available.",
        requirement_value="Yes",
        auditor_actions=["a. Verify records."],
        source_segments=[
            _span("requirement_id", "4.1.2", refs=("id-lower-cab",)),
            _span(
                "normative_text",
                "Indicator: Records are available. Requirement: Yes",
                refs=("formal-lower-cab",),
            ),
            _span(
                "indicator_text",
                "Records are available.",
                refs=("indicator-lower-cab",),
            ),
            _span(
                "requirement_value",
                "Yes",
                refs=("value-lower-cab",),
            ),
            _span(
                "auditor_action",
                "a. Verify records.",
                refs=("auditor-lower-cab",),
            ),
        ],
    )

    requirement = canonicalize_native_requirement(native)

    assert requirement.status == RequirementStatus.ACCEPTED
    assert requirement.auditor_actions[0].marker == "a"
    assert "auditor_action_marker_case:1:a" in requirement.source_anomalies


def test_profile_trust_can_only_lower_acceptance_and_norwegian_is_explicit() -> None:
    native = NativeRequirement(
        requirement_id="5.1.1",
        family=TemplateFamily.SINGLE_COLUMN_INDICATORS,
        normative_text="Virksomheten skal føre journal.",
        source_segments=[
            _span("requirement_id", "5.1.1", refs=("id-6",)),
            _span(
                "normative_text",
                "Virksomheten skal føre journal.",
                refs=("formal-6",),
            ),
        ],
    )

    accepted = canonicalize_native_requirement(native, language="no", family_trusted=True)
    lowered = apply_family_trust(accepted, trusted=False)

    assert accepted.language == "no"
    assert [(item.token, item.type, item.scope) for item in accepted.modalities] == [
        ("skal", "obligation", "føre journal")
    ]
    assert accepted.status == RequirementStatus.ACCEPTED
    assert "document_profile_family_trusted" in accepted.validation_flags
    assert lowered.status == RequirementStatus.REVIEW_REQUIRED
    assert "document_profile_family_untrusted" in lowered.validation_flags
    assert accepted.status == RequirementStatus.ACCEPTED


def test_native_evidence_reused_across_action_and_formal_roles_requires_review() -> None:
    native = NativeRequirement(
        requirement_id="6.1.1",
        family=TemplateFamily.AUDIT_MATRIX,
        normative_text="Indicator: Records are available. Requirement: Yes",
        client_actions=["a. Maintain records."],
        source_segments=[
            _span("requirement_id", "6.1.1", refs=("id-7",)),
            _span(
                "normative_text",
                "Indicator: Records are available. Requirement: Yes",
                refs=("shared-7",),
            ),
            _span(
                "client_action",
                "a. Maintain records.",
                refs=("shared-7",),
            ),
        ],
    )

    requirement = canonicalize_native_requirement(native)

    assert requirement.status == RequirementStatus.REVIEW_REQUIRED
    assert any(
        anomaly.startswith("native_ref_reused_across_roles:shared-7:")
        for anomaly in requirement.source_anomalies
    )


def test_semantics_map_exact_english_source_and_threshold_provenance() -> None:
    text = (
        "The operator shall not discharge more than 5 mg/L when temperature is "
        "stable, unless Section 4.2 applies."
    )
    native = NativeRequirement(
        requirement_id="7.1.1",
        family=TemplateFamily.SINGLE_COLUMN_INDICATORS,
        normative_text=text,
        source_segments=[
            _span("requirement_id", "7.1.1", refs=("id-8",)),
            _span("normative_text", text, refs=("formal-8",)),
        ],
    )

    requirement = canonicalize_native_requirement(native, language="en")
    formal_region_id = next(
        region.segment_id
        for region in requirement.source_segments
        if region.role == "normative_text"
    )

    assert requirement.status == RequirementStatus.ACCEPTED
    assert [(item.token, item.type, item.scope) for item in requirement.modalities] == [
        ("shall not", "prohibition", "discharge more than 5 mg/L")
    ]
    assert [(item.text, item.applies_to) for item in requirement.negations] == [
        ("shall not discharge more than 5 mg/L", "discharge more than 5 mg/L")
    ]
    assert [(item.text, item.applies_to) for item in requirement.conditions] == [
        ("when temperature is stable", "discharge more than 5 mg/L")
    ]
    assert [(item.text, item.applies_to) for item in requirement.exceptions] == [
        ("unless Section 4.2 applies", "discharge more than 5 mg/L")
    ]
    assert len(requirement.thresholds) == 1
    threshold = requirement.thresholds[0]
    assert threshold.raw_text == "more than 5 mg/L"
    assert threshold.operator == "gt"
    assert threshold.normalized_value == 5
    assert threshold.unit == "mg/L"
    assert threshold.applies_to == "discharge more than 5 mg/L"
    assert threshold.source_segment_ids == [formal_region_id]
    assert [(item.text, item.target, item.type) for item in requirement.cross_references] == [
        ("Section 4.2", "Section 4.2", "internal_exact")
    ]


def test_semantics_map_explicit_norwegian_without_english_fallback() -> None:
    text = (
        "Virksomheten skal ikke slippe ut mer enn 5 prosent dersom vannet er "
        "kaldt, med mindre § 4-2 gjelder."
    )
    native = NativeRequirement(
        requirement_id="7.1.2",
        family=TemplateFamily.SINGLE_COLUMN_INDICATORS,
        normative_text=text,
        source_segments=[
            _span("requirement_id", "7.1.2", refs=("id-9",)),
            _span("normative_text", text, refs=("formal-9",)),
        ],
    )

    requirement = canonicalize_native_requirement(native, language="no")

    assert requirement.status == RequirementStatus.ACCEPTED
    assert [(item.token, item.type, item.scope) for item in requirement.modalities] == [
        ("skal ikke", "prohibition", "slippe ut mer enn 5 prosent")
    ]
    assert requirement.negations[0].text == "ikke"
    assert requirement.conditions[0].text == "dersom vannet er kaldt"
    assert requirement.exceptions[0].text == "med mindre § 4-2 gjelder"
    assert requirement.thresholds[0].raw_text == "mer enn 5 prosent"
    assert requirement.cross_references[0].text == "§ 4-2"


def test_ambiguous_semantic_candidate_is_retained_and_lowers_acceptance() -> None:
    text = "The operator shall appoint at least one manager."
    native = NativeRequirement(
        requirement_id="7.1.3",
        family=TemplateFamily.SINGLE_COLUMN_INDICATORS,
        normative_text=text,
        source_segments=[
            _span("requirement_id", "7.1.3", refs=("id-10",)),
            _span("normative_text", text, refs=("formal-10",)),
        ],
    )

    requirement = canonicalize_native_requirement(native, language="en")

    assert requirement.status == RequirementStatus.REVIEW_REQUIRED
    assert requirement.thresholds[0].raw_text == "at least one manager"
    assert requirement.thresholds[0].normalized_value == 1
    assert requirement.thresholds[0].unit == "manager"
    assert requirement.thresholds[0].source_segment_ids
    assert "semantic_review_required" in requirement.validation_flags
    assert any(
        anomaly.startswith("semantic_threshold:unit_requires_review:")
        or anomaly.startswith("semantic_threshold:ambiguous:")
        for anomaly in requirement.source_anomalies
    )


def test_threshold_source_binding_selects_covering_continuation_region() -> None:
    text = "The operator shall maintain records for at least 5 years."
    native = NativeRequirement(
        requirement_id="7.1.4",
        family=TemplateFamily.ID_NORMATIVE_WITH_CONTEXT,
        normative_text=text,
        source_segments=[
            _span("requirement_id", "7.1.4", refs=("id-11",)),
            _span(
                "normative_text",
                "The operator shall maintain records for",
                refs=("formal-11a",),
            ),
            _span(
                "requirement_continuation",
                "at least 5 years.",
                page_index=5,
                refs=("formal-11b",),
            ),
        ],
    )

    requirement = canonicalize_native_requirement(native, language="en")
    continuation_id = next(
        region.segment_id
        for region in requirement.source_segments
        if region.role == "requirement_continuation"
    )

    assert requirement.status == RequirementStatus.ACCEPTED
    assert requirement.thresholds[0].source_segment_ids == [continuation_id]
    assert requirement.semantic_input is not None
    assert [item.role for item in requirement.semantic_input.core_fragments] == [
        "normative_text",
        "requirement_continuation",
    ]
    assert len({
        (
            item.role,
            item.text,
            tuple(item.source_segment_ids),
        )
        for item in requirement.semantic_input.core_fragments
    }) == len(requirement.semantic_input.core_fragments)


def test_embedded_condition_targets_following_normative_action() -> None:
    text = (
        "The operator shall, based on verified monitoring data, implement the "
        "corrective plan."
    )
    native = NativeRequirement(
        requirement_id="7.2.1",
        family=TemplateFamily.SINGLE_COLUMN_INDICATORS,
        normative_text=text,
        source_segments=[
            _span("requirement_id", "7.2.1", refs=("id-condition",)),
            _span("normative_text", text, refs=("formal-condition",)),
        ],
    )

    requirement = canonicalize_native_requirement(native, language="en")

    assert requirement.conditions[0].text == "based on verified monitoring data"
    assert requirement.conditions[0].applies_to == "implement the corrective plan"
    assert requirement.modalities[0].scope == "implement the corrective plan"


def test_canonical_negations_preserve_full_no_and_modal_not_phrases() -> None:
    text = (
        "The operator shall ensure there is no decline in status, and shall not "
        "discharge pesticides."
    )
    native = NativeRequirement(
        requirement_id="7.2.2",
        family=TemplateFamily.SINGLE_COLUMN_INDICATORS,
        normative_text=text,
        source_segments=[
            _span("requirement_id", "7.2.2", refs=("id-negation",)),
            _span("normative_text", text, refs=("formal-negation",)),
        ],
    )

    requirement = canonicalize_native_requirement(native, language="en")

    assert [(item.text, item.applies_to) for item in requirement.negations] == [
        ("no decline in status", "decline in status"),
        ("shall not discharge pesticides", "discharge pesticides"),
    ]


def test_linked_footnote_qualifiers_bind_threshold_to_footnote_segment() -> None:
    from pdf_extraction.requirements import NativeFootnoteLinkCandidate

    text = "The operator shall monitor water quality."
    footnote = (
        "13 An exemption applies if the mean water depth calculated over any "
        "rolling two-year period remains ≥ 10m."
    )
    native = NativeRequirement(
        requirement_id="7.2.3",
        family=TemplateFamily.SINGLE_COLUMN_INDICATORS,
        normative_text=text,
        footnote_markers=["13"],
        footnote_link_candidates=[NativeFootnoteLinkCandidate(
            marker="13",
            link_type="direct",
            definition_page_index=4,
            definition_native_object_ids=("fn-13",),
        )],
        source_segments=[
            _span("requirement_id", "7.2.3", refs=("id-footnote",)),
            _span("normative_text", text, refs=("formal-footnote",)),
            _span("footnote", footnote, refs=("fn-13",)),
        ],
    )

    requirement = canonicalize_native_requirement(native, language="en")
    footnote_segment_id = next(
        region.segment_id
        for region in requirement.source_segments
        if region.role == "footnote"
    )

    assert [item.text for item in requirement.exemptions] == [
        "An exemption applies if the mean water depth calculated over any rolling "
        "two-year period remains ≥ 10m."
    ]
    assert [item.text for item in requirement.dates] == [
        "over any rolling two-year period"
    ]
    assert len(requirement.thresholds) == 1
    assert requirement.thresholds[0].raw_text == "≥ 10m"
    assert requirement.thresholds[0].unit == "m"
    assert requirement.thresholds[0].source_segment_ids == [footnote_segment_id]
    assert requirement.semantic_input is not None
    footnote_fragment = next(
        item
        for item in requirement.semantic_input.qualifier_fragments
        if item.role == "footnote"
    )
    assert footnote_fragment.source_segment_ids == [footnote_segment_id]


def test_attached_footnote_markers_are_removed_only_from_semantic_source() -> None:
    from pdf_extraction.requirements import NativeFootnoteLinkCandidate

    cases = [
        (
            "10",
            "The UoC shall10 determine benthic status.",
            "The UoC shall determine benthic status.",
            "determine benthic status",
        ),
        (
            "11",
            "The UoC shall demonstrate an 'Acceptable' status11, following the method.",
            "The UoC shall demonstrate an 'Acceptable' status, following the method.",
            "demonstrate an 'Acceptable' status, following the method",
        ),
    ]
    for index, (marker, raw_text, semantic_text, expected_scope) in enumerate(
        cases,
        start=1,
    ):
        native = NativeRequirement(
            requirement_id=f"7.2.{index}",
            family=TemplateFamily.SINGLE_COLUMN_INDICATORS,
            normative_text=semantic_text,
            footnote_markers=[marker],
            footnote_link_candidates=[NativeFootnoteLinkCandidate(
                marker=marker,
                link_type="direct",
                definition_page_index=4,
                definition_native_object_ids=(f"fn-{marker}",),
            )],
            source_segments=[
                _span("requirement_id", f"7.2.{index}", refs=(f"id-{marker}",)),
                _span("normative_text", raw_text, refs=(f"formal-{marker}",)),
                _span("footnote", f"{marker} Source note.", refs=(f"fn-{marker}",)),
            ],
        )

        requirement = canonicalize_native_requirement(native, language="en")
        formal_region = next(
            region
            for region in requirement.source_segments
            if region.role == "normative_text"
        )

        assert formal_region.source_text == semantic_text
        assert formal_region.resolved_text == semantic_text
        assert formal_region.native_text == raw_text
        assert requirement.modalities[0].scope == expected_scope
        assert requirement.modalities[0].scope_ref is not None
        assert requirement.modalities[0].scope_ref.anchors[0].text == expected_scope


def test_bracketed_footnote_reference_is_not_stripped_from_semantic_source() -> None:
    native = NativeRequirement(
        requirement_id="7.2.9",
        family=TemplateFamily.AUDIT_MATRIX,
        normative_text="Indicator: Protected area [22]\nRequirement: None [22]",
        indicator_text="Protected area [22]",
        requirement_value="None [22]",
        footnote_markers=["22"],
        source_segments=[
            _span("requirement_id", "7.2.9", refs=("id-22",)),
            _span("indicator_text", "Protected area [22]", refs=("indicator-22",)),
            _span("requirement_value", "None [22]", refs=("value-22",)),
            _span(
                "normative_text",
                "Indicator: Protected area [22]\nRequirement: None [22]",
                refs=("formal-22",),
            ),
        ],
    )

    requirement = canonicalize_native_requirement(native)

    assert next(
        region.source_text
        for region in requirement.source_segments
        if region.role == "indicator_text"
    ) == "Protected area [22]"
    assert next(
        region.source_text
        for region in requirement.source_segments
        if region.role == "normative_text"
    ) == "Indicator: Protected area [22]\nRequirement: None [22]"


def test_linked_footnote_within_deadline_is_threshold_and_condition() -> None:
    from pdf_extraction.requirements import NativeFootnoteLinkCandidate

    text = "The operator shall publish the incident report."
    footnote = "34 Shall be made available within 30 days of the incident."
    native = NativeRequirement(
        requirement_id="7.2.4",
        family=TemplateFamily.SINGLE_COLUMN_INDICATORS,
        normative_text=text,
        footnote_markers=["34"],
        footnote_link_candidates=[NativeFootnoteLinkCandidate(
            marker="34",
            link_type="direct",
            definition_page_index=4,
            definition_native_object_ids=("fn-34",),
        )],
        source_segments=[
            _span("requirement_id", "7.2.4", refs=("id-deadline",)),
            _span("normative_text", text, refs=("formal-deadline",)),
            _span("footnote", footnote, refs=("fn-34",)),
        ],
    )

    requirement = canonicalize_native_requirement(native, language="en")
    footnote_segment_id = next(
        region.segment_id
        for region in requirement.source_segments
        if region.role == "footnote"
    )

    assert requirement.conditions[-1].text == "within 30 days of the incident"
    assert requirement.thresholds[-1].raw_text == "within 30 days of the incident"
    assert requirement.thresholds[-1].unit == "days"
    assert requirement.thresholds[-1].source_segment_ids == [footnote_segment_id]


def test_linked_leading_exemption_preserves_full_scope_negation_and_date() -> None:
    from pdf_extraction.requirements import NativeFootnoteLinkCandidate

    text = "The UoC shall demonstrate an 'Acceptable' benthic status."
    footnote = (
        "11 An exemption applies to cage sites situated in lakes and reservoirs, "
        "where determination of benthic status is required (Indicator 2.5.1) "
        "but demonstration that the status is 'Acceptable' is not required for "
        "the first three years of the standard being effective."
    )
    definition = footnote.removeprefix("11 ")
    native = NativeRequirement(
        requirement_id="2.5.2",
        family=TemplateFamily.SINGLE_COLUMN_INDICATORS,
        normative_text=text,
        footnote_markers=["11"],
        footnote_link_candidates=[NativeFootnoteLinkCandidate(
            marker="11",
            link_type="direct",
            definition_page_index=4,
            definition_native_object_ids=("fn-11",),
        )],
        source_segments=[
            _span("requirement_id", "2.5.2", refs=("id-252",)),
            _span("normative_text", text, refs=("formal-252",)),
            _span("footnote", footnote, refs=("fn-11",)),
        ],
    )

    requirement = canonicalize_native_requirement(native, language="en")
    footnote_region = next(
        region for region in requirement.source_segments if region.role == "footnote"
    )

    assert footnote_region.source_text == definition
    assert footnote_region.resolved_text == definition
    assert footnote_region.native_text == footnote
    assert [(item.text, item.applies_to) for item in requirement.exemptions] == [
        (definition, "Requirement 2.5.2")
    ]
    assert requirement.exemptions[0].scope_ref is not None
    assert requirement.exemptions[0].scope_ref.kind == "requirement"
    assert [(item.text, item.applies_to) for item in requirement.negations] == [
        (
            "is not required",
            "demonstration that the status is 'Acceptable'",
        )
    ]
    assert requirement.negations[0].scope_ref is not None
    assert requirement.negations[0].scope_ref.kind == "footnote"
    assert requirement.thresholds == []
    assert [(item.text, item.applies_to) for item in requirement.dates] == [
        (
            "for the first three years of the standard being effective",
            "demonstration that the status is 'Acceptable' is not required",
        )
    ]
    assert requirement.dates[0].scope_ref is not None
    assert requirement.dates[0].scope_ref.kind == "footnote"
    assert requirement.conditions == []
    assert not any(
        "semantic_footnote_condition" in item
        or "semantic_footnote_threshold" in item
        for item in requirement.source_anomalies
    )


def test_linked_exception_footnote_promotes_only_source_backed_legal_qualifiers() -> None:
    from pdf_extraction.requirements import NativeFootnoteLinkCandidate

    indicator = "Allowance in a protected area [20]"
    value = "None [22]"
    text = (
        f"Indicator: {indicator}\nRequirement: {value}\n"
        "Applicability: All farms except as noted in [22]"
    )
    footnote = (
        "[22] The following exceptions shall be made for Standard 2.4.2: "
        "• For Category V or VI areas. "
        "• For HCVAs if the farm demonstrates compatible impacts. "
        "• For existing farms if designation occurred after operation and "
        "provided the farm demonstrates compatible impacts and it is in "
        "compliance with relevant conditions."
    )
    native = NativeRequirement(
        requirement_id="2.4.2",
        family=TemplateFamily.AUDIT_MATRIX,
        normative_text=text,
        indicator_text=indicator,
        requirement_value=value,
        applicability="All farms except as noted in [22]",
        footnote_markers=["22"],
        footnote_link_candidates=[NativeFootnoteLinkCandidate(
            marker="22",
            link_type="direct",
            definition_page_index=4,
            definition_native_object_ids=("fn-22",),
        )],
        source_segments=[
            _span("requirement_id", "2.4.2", refs=("id-22",)),
            _span("indicator_text", indicator, refs=("indicator-22",)),
            _span("requirement_value", value, refs=("value-22",)),
            _span("applicability", "All farms except as noted in [22]", refs=("app-22",)),
            _span("normative_text", text, refs=("formal-22",)),
            _span("footnote", footnote, refs=("fn-22",)),
        ],
    )

    requirement = canonicalize_native_requirement(native)

    assert requirement.status == RequirementStatus.ACCEPTED
    assert "normative_text_provenance_mismatch" not in requirement.source_anomalies
    assert [(item.token, item.type) for item in requirement.modalities] == [
        ("shall", "obligation")
    ]
    assert requirement.negations[0].text == "None"
    assert [item.marker for item in requirement.associated_instructions] == [
        "Exception #1", "Exception #2", "Exception #3"
    ]
    assert all(
        item.effect == "exception" and item.source_segment_ids
        for item in requirement.associated_instructions
    )
    assert len(requirement.exceptions) == 3
    assert [(item.text, item.applies_to) for item in requirement.conditions] == [
        ("if the farm demonstrates compatible impacts", "Exception #2"),
        ("if designation occurred after operation", "Exception #3"),
        ("provided the farm demonstrates compatible impacts", "Exception #3"),
        ("it is in compliance with relevant conditions", "Exception #3"),
    ]


def test_semantic_footnote_requires_explicit_owner_for_qualifier_promotion() -> None:
    from pdf_extraction.requirements import NativeFootnoteLinkCandidate

    definition = "35 Lethal incident: An incident causing deliberate death."
    unbound = "36 The operator shall publish a report."
    native = NativeRequirement(
        requirement_id="2.5.6",
        family=TemplateFamily.LEGACY_INDICATOR_VALUE,
        normative_text="In the event of a lethal incident, evidence is required\nYes",
        indicator_text="In the event of a lethal incident, evidence is required",
        requirement_value="Yes",
        footnote_link_candidates=[
            NativeFootnoteLinkCandidate(
                marker="35", link_type="semantic", definition_page_index=4,
                definition_native_object_ids=("fn-35",),
            ),
            NativeFootnoteLinkCandidate(
                marker="36", link_type="semantic", definition_page_index=4,
                definition_native_object_ids=("fn-36",),
            ),
        ],
        source_segments=[
            _span("requirement_id", "2.5.6", refs=("id-256",)),
            _span("indicator_text", "In the event of a lethal incident, evidence is required", refs=("ind-256",)),
            _span("requirement_value", "Yes", refs=("val-256",)),
            _span("footnote", definition, refs=("fn-35",)),
            _span("footnote", unbound, refs=("fn-36",)),
        ],
    )

    requirement = canonicalize_native_requirement(native)

    assert [(item.text, item.type) for item in requirement.cross_references] == [
        ("lethal incident", "defined_term")
    ]
    assert requirement.modalities == []
    assert requirement.associated_instructions == []


def test_anomalous_footnote_never_promotes_qualifiers_or_instructions() -> None:
    from pdf_extraction.requirements import NativeFootnoteLinkCandidate

    footnote = "[36] Standard 2.5.6 applicable to restricted cases."
    native = NativeRequirement(
        requirement_id="2.5.5",
        family=TemplateFamily.AUDIT_MATRIX,
        normative_text="Indicator: Incidents [36]\nRequirement: 0\nApplicability: All",
        indicator_text="Incidents [36]",
        requirement_value="0",
        applicability="All",
        footnote_link_candidates=[NativeFootnoteLinkCandidate(
            marker="36",
            link_type="direct",
            definition_page_index=4,
            definition_native_object_ids=("fn-36-mismatch",),
            issues=("footnote_direct_target_mismatch:36:explicit_targets=2.5.6",),
        )],
        source_segments=[
            _span("requirement_id", "2.5.5", refs=("id-255",)),
            _span("normative_text", "Indicator: Incidents [36]\nRequirement: 0\nApplicability: All", refs=("formal-255",)),
            _span("footnote", footnote, refs=("fn-36-mismatch",)),
        ],
    )

    requirement = canonicalize_native_requirement(native)

    assert requirement.footnote_refs[0].link_type == "anomalous"
    assert requirement.applicability == ["All"]
    assert requirement.modalities == []
    assert requirement.associated_instructions == []


def test_audit_fields_deduplicate_applicability_threshold_and_bind_exact_scopes() -> None:
    indicator = (
        "Maximum unexplained mortality rate from each of the previous two "
        "production cycles, for farms with total mortality > 6%"
    )
    value = "≤ 40% of total mortalities"
    applicability = (
        "All farms with > 6% total mortality in the most recent complete "
        "production cycle."
    )
    normative = (
        f"Indicator: {indicator}\nRequirement: {value}\n"
        f"Applicability: {applicability}"
    )
    native = NativeRequirement(
        requirement_id="5.1.6",
        family=TemplateFamily.AUDIT_MATRIX,
        normative_text=normative,
        indicator_text=indicator,
        requirement_value=value,
        applicability=applicability,
        source_segments=[
            _span("requirement_id", "5.1.6", refs=("id-516",)),
            _span("indicator_text", indicator, refs=("indicator-516",)),
            _span("requirement_value", value, refs=("value-516",)),
            _span("applicability", applicability, refs=("app-516",)),
            _span("normative_text", normative, refs=("formal-516",)),
        ],
    )

    requirement = canonicalize_native_requirement(native)

    assert [(item.text, item.applies_to) for item in requirement.conditions] == [
        (
            "for farms with total mortality > 6%",
            "Maximum unexplained mortality rate from each of the previous two production cycles",
        )
    ]
    assert [item.raw_text for item in requirement.thresholds] == [
        "≤ 40% of total mortalities",
        "> 6% total mortality",
    ]
    assert [item.applies_to for item in requirement.thresholds] == [
        "Maximum unexplained mortality rate",
        applicability,
    ]
    assert [item.scope_ref.target for item in requirement.thresholds] == [
        "indicator_text",
        "applicability",
    ]
    assert [(item.text, item.applies_to) for item in requirement.dates] == [
        (
            "each of the previous two production cycles",
            "Maximum unexplained mortality rate",
        ),
        (
            "the most recent complete production cycle",
            "All farms with > 6% total mortality",
        ),
    ]


def test_frequency_and_qualitative_thresholds_use_governing_action_or_subject() -> None:
    indicator = (
        "The farm shall reduce the Weighted Number of Medicinal Treatments "
        "after achieving indicator 5.2.6, with 25% per 2 years until the WNMT "
        "is at or below the Global Level (see Appendix VII)"
    )
    normative = f"Indicator: {indicator}\nRequirement: Yes"
    native = NativeRequirement(
        requirement_id="5.2.7",
        family=TemplateFamily.AUDIT_MATRIX,
        normative_text=normative,
        indicator_text=indicator,
        requirement_value="Yes",
        source_segments=[
            _span("requirement_id", "5.2.7", refs=("id-527",)),
            _span("indicator_text", indicator, refs=("indicator-527",)),
            _span("requirement_value", "Yes", refs=("value-527",)),
            _span("normative_text", normative, refs=("formal-527",)),
        ],
    )

    requirement = canonicalize_native_requirement(native)

    action = "reduce the Weighted Number of Medicinal Treatments"
    assert [(item.raw_text, item.applies_to) for item in requirement.thresholds] == [
        ("25%", action),
        ("at or below the Global Level", "the WNMT"),
    ]
    assert [(item.text, item.applies_to) for item in requirement.dates] == [
        ("per 2 years", action)
    ]


def test_linked_footnote_keeps_predicate_scope_and_footnote_anchor_kind() -> None:
    from pdf_extraction.requirements import NativeFootnoteLinkCandidate

    indicator = "Medication may only be prescribed by the veterinarian [88]"
    footnote = (
        "[88] The designated veterinarian must certify that a pathogen or "
        "disease is present before prescribing medication."
    )
    native = NativeRequirement(
        requirement_id="5.2.11",
        family=TemplateFamily.AUDIT_MATRIX,
        normative_text=f"Indicator: {indicator}\nRequirement: Yes",
        indicator_text=indicator,
        requirement_value="Yes",
        footnote_markers=["88"],
        footnote_link_candidates=[NativeFootnoteLinkCandidate(
            marker="88",
            link_type="direct",
            definition_page_index=4,
            definition_native_object_ids=("fn-88",),
        )],
        source_segments=[
            _span("requirement_id", "5.2.11", refs=("id-5211",)),
            _span("indicator_text", indicator, refs=("indicator-5211",)),
            _span("requirement_value", "Yes", refs=("value-5211",)),
            _span("footnote", footnote, refs=("fn-88",)),
        ],
    )

    requirement = canonicalize_native_requirement(native)
    promoted = next(item for item in requirement.modalities if item.token == "must")

    assert promoted.scope == (
        "certify that a pathogen or disease is present before prescribing medication"
    )
    assert promoted.scope_ref is not None
    assert (promoted.scope_ref.kind, promoted.scope_ref.target) == (
        "footnote",
        "footnote:88",
    )
    assert [(item.text, item.applies_to, item.scope_ref.kind) for item in requirement.dates] == [
        (
            "before prescribing medication",
            "certify that a pathogen or disease is present",
            "footnote",
        )
    ]
    assert requirement.associated_instructions == []


def test_source_instruction_stays_related_and_adds_only_explicit_references() -> None:
    note = (
        "Note Indicator 5.2.10: Guidance is pending. "
        "See QA 111: https://example.org/QA0111/"
    )
    native = NativeRequirement(
        requirement_id="5.2.10",
        family=TemplateFamily.AUDIT_MATRIX,
        normative_text="Indicator: Residue monitoring\nRequirement: Yes",
        indicator_text="Residue monitoring",
        requirement_value="Yes",
        source_segments=[
            _span("requirement_id", "5.2.10", refs=("id-5210",)),
            _span("indicator_text", "Residue monitoring", refs=("ind-5210",)),
            _span("requirement_value", "Yes", refs=("value-5210",)),
            _span("instruction", note, refs=("note-5210",)),
        ],
    )

    requirement = canonicalize_native_requirement(native)

    assert requirement.normative_text == "Indicator: Residue monitoring\nRequirement: Yes"
    assert [item.marker for item in requirement.associated_instructions] == [
        "Note Indicator 5.2.10"
    ]
    assert [(item.text, item.target, item.type) for item in requirement.cross_references] == [
        ("QA 111", "ASC interpretation platform QA0111", "external_document")
    ]


def test_explicit_indicator_dependency_is_not_treated_as_an_ordinary_number() -> None:
    indicator = (
        "The farm shall reduce treatments after achieving Indicator 5.2.6."
    )
    native = NativeRequirement(
        requirement_id="5.2.7",
        family=TemplateFamily.AUDIT_MATRIX,
        normative_text=f"Indicator: {indicator}\nRequirement: Yes",
        indicator_text=indicator,
        requirement_value="Yes",
        source_segments=[
            _span("requirement_id", "5.2.7", refs=("id-527",)),
            _span("indicator_text", indicator, refs=("ind-527",)),
            _span("requirement_value", "Yes", refs=("value-527",)),
        ],
    )

    requirement = canonicalize_native_requirement(native)

    assert [(item.text, item.target) for item in requirement.cross_references] == [
        ("5.2.6", "Indicator 5.2.6")
    ]


def test_audit_indicator_numbered_list_does_not_absorb_other_fields() -> None:
    indicator = (
        "The farm shall publicly report the: "
        "1. medicinal treatments for each production cycle "
        "2. parasiticide load over the production cycle "
        "3. benthic residue levels"
    )
    normative = f"Indicator: {indicator}\nRequirement: Yes\nApplicability: All"
    native = NativeRequirement(
        requirement_id="5.2.5",
        family=TemplateFamily.AUDIT_MATRIX,
        normative_text=normative,
        indicator_text=indicator,
        requirement_value="Yes",
        applicability="All",
        source_segments=[
            _span("requirement_id", "5.2.5", refs=("id-525",)),
            _span("indicator_text", indicator, refs=("indicator-525",)),
            _span("requirement_value", "Yes", refs=("value-525",)),
            _span("applicability", "All", refs=("app-525",)),
            _span("normative_text", normative, refs=("formal-525",)),
        ],
    )

    requirement = canonicalize_native_requirement(native)

    assert [(item.marker, item.text) for item in requirement.clauses] == [
        (None, "The farm shall publicly report the:"),
        ("1.", "medicinal treatments for each production cycle"),
        ("2.", "parasiticide load over the production cycle"),
        ("3.", "benthic residue levels"),
    ]
