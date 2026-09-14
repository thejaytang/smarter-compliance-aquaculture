from __future__ import annotations

import pytest

from pdf_extraction.domains.requirements.semantics import (
    RequirementSemanticAnalysis,
    analyze_requirement_semantics,
    assess_language,
)


def _assert_all_reported_spans_are_exact(analysis: RequirementSemanticAnalysis) -> None:
    payload = analysis.model_dump(mode="json")

    def walk(value: object) -> None:
        if isinstance(value, dict):
            if {"start", "end", "text"} <= value.keys():
                start = value["start"]
                end = value["end"]
                span_text = value["text"]
                assert isinstance(start, int)
                assert isinstance(end, int)
                assert analysis.source_text[start:end] == span_text
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(payload)


def test_english_semantics_preserve_exact_modal_and_context_spans() -> None:
    text = (
        "The operator shall not discharge more than 5 mg/L when temperature is "
        "below 10 °C, unless Section 4.2 applies."
    )

    result = analyze_requirement_semantics(text)

    assert result.language.language == "en"
    assert not result.language.ambiguous
    assert [(item.span.text, item.modality_type, item.negated) for item in result.modalities] == [
        ("shall not", "prohibition", True)
    ]
    assert [item.span.text for item in result.negations] == ["not"]
    assert [item.clause.text for item in result.conditions] == [
        "when temperature is below 10 °C"
    ]
    assert [item.clause.text for item in result.exceptions] == [
        "unless Section 4.2 applies"
    ]
    assert [item.span.text for item in result.thresholds] == [
        "more than 5 mg/L",
        "10 °C",
    ]
    assert result.thresholds[0].operator == "gt"
    assert result.thresholds[0].normalized_value == 5
    assert result.thresholds[0].unit == "mg/L"
    assert result.thresholds[1].operator == "unspecified"
    assert result.thresholds[1].ambiguous
    assert [item.span.text for item in result.cross_references] == ["Section 4.2"]
    _assert_all_reported_spans_are_exact(result)


def test_norwegian_semantics_cover_legal_cues_and_compound_section_reference() -> None:
    text = (
        "Virksomheten skal ikke slippe ut mer enn 5 prosent dersom vannet er "
        "kaldt, med mindre § 4-2 første ledd bokstav a gjelder. Se også kapittel 3."
    )

    result = analyze_requirement_semantics(text)

    assert result.language.language == "no"
    assert not result.language.ambiguous
    assert result.modalities[0].span.text == "skal ikke"
    assert result.modalities[0].modality_type == "prohibition"
    assert result.negations[0].span.text == "ikke"
    assert result.conditions[0].marker.text == "dersom"
    assert result.conditions[0].clause.text == "dersom vannet er kaldt"
    assert result.exceptions[0].marker.text == "med mindre"
    assert result.thresholds[0].span.text == "mer enn 5 prosent"
    assert result.thresholds[0].operator == "gt"
    assert result.thresholds[0].unit == "prosent"
    assert [item.span.text for item in result.cross_references] == [
        "§ 4-2 første ledd bokstav a",
        "kapittel 3",
    ]
    _assert_all_reported_spans_are_exact(result)


def test_appendix_reference_excludes_sentence_punctuation() -> None:
    result = analyze_requirement_semantics(
        "The farm shall report results according to Appendix VII.",
        language="en",
    )

    assert [item.span.text for item in result.cross_references] == ["Appendix VII"]


def test_norwegian_reference_range_and_standalone_legal_units_are_retained() -> None:
    text = "Kravene i §§ 3-2 til 3-4, annet ledd og bokstav b skal følges."

    result = analyze_requirement_semantics(text, language="no")

    assert [item.span.text for item in result.cross_references] == [
        "§§ 3-2 til 3-4",
        "annet ledd",
        "bokstav b",
    ]
    assert result.cross_references[0].reference_type == "section_range"
    assert result.cross_references[2].ambiguous
    assert result.language.method == "explicit"
    _assert_all_reported_spans_are_exact(result)


def test_all_requested_english_modalities_and_context_markers_are_detected() -> None:
    text = (
        "The owner shall register, must retain records, may disclose data, and "
        "should review them provided that consent exists, except paragraph (3)."
    )

    result = analyze_requirement_semantics(text, language="en")

    assert [item.span.text.lower() for item in result.modalities] == [
        "shall",
        "must",
        "may",
        "should",
    ]
    assert [item.modality_type for item in result.modalities] == [
        "obligation",
        "obligation",
        "permission",
        "recommendation",
    ]
    assert result.conditions[0].marker.text == "provided that"
    assert result.exceptions[0].marker.text == "except"
    assert result.cross_references[0].span.text == "paragraph (3)"
    _assert_all_reported_spans_are_exact(result)


def test_comparison_symbols_ranges_and_common_units_are_candidates() -> None:
    text = "The level must be ≥ 5% and between 10 and 20 kg, with temperature < 8 °C."

    result = analyze_requirement_semantics(text, language="en")

    assert [(item.span.text, item.operator) for item in result.thresholds] == [
        ("≥ 5%", "gte"),
        ("between 10 and 20 kg", "range"),
        ("< 8 °C", "lt"),
    ]
    assert result.thresholds[1].normalized_value == 10
    assert result.thresholds[1].normalized_end_value == 20
    assert result.thresholds[2].unit == "°C"


def test_unknown_comparative_unit_is_retained_but_flagged() -> None:
    text = "The operator shall appoint at least one manager."

    result = analyze_requirement_semantics(text, language="en")

    threshold = result.thresholds[0]
    assert threshold.span.text == "at least one manager"
    assert threshold.operator == "gte"
    assert threshold.normalized_value == 1
    assert threshold.unit == "manager"
    assert threshold.ambiguous
    assert "unit_requires_review" in threshold.flags
    assert any(flag.startswith("threshold_unit_requires_review:") for flag in result.flags)


def test_multiple_modal_scopes_stop_at_the_next_explicit_modal() -> None:
    text = "The owner shall register, must retain records, and may disclose data."

    result = analyze_requirement_semantics(text, language="en")

    assert [item.scope.text for item in result.modalities if item.scope] == [
        "register",
        "retain records",
        "disclose data",
    ]


def test_modality_scope_does_not_stop_at_numbered_items_or_eg_abbreviation() -> None:
    numbered = (
        "The farm shall publicly report the: 1. Weighted Number for each cycle "
        "2. Parasiticide load over the cycle 3. Residue levels."
    )
    abbreviated = (
        "The farm shall public present (e.g., via company website) the IPM "
        "measures that the company applies."
    )

    numbered_result = analyze_requirement_semantics(numbered, language="en")
    abbreviated_result = analyze_requirement_semantics(abbreviated, language="en")

    assert numbered_result.modalities[0].scope is not None
    assert numbered_result.modalities[0].scope.text == (
        "publicly report the: 1. Weighted Number for each cycle "
        "2. Parasiticide load over the cycle 3. Residue levels"
    )
    assert abbreviated_result.modalities[0].scope is not None
    assert abbreviated_result.modalities[0].scope.text == (
        "public present (e.g., via company website) the IPM measures that "
        "the company applies"
    )


def test_need_to_is_a_second_obligation_modality() -> None:
    text = (
        "The farm shall publish the measures which need to be approved by a "
        "veterinarian."
    )

    result = analyze_requirement_semantics(text, language="en")

    assert [(item.span.text, item.modality_type) for item in result.modalities] == [
        ("shall", "obligation"),
        ("need to", "obligation"),
    ]
    assert result.modalities[0].scope is not None
    assert result.modalities[0].scope.text == "publish the measures"
    assert result.modalities[1].scope is not None
    assert result.modalities[1].scope.text == "be approved by a veterinarian"


def test_qualitative_level_and_exact_rate_step_are_source_backed_thresholds() -> None:
    text = (
        "The farm shall reduce the Weighted Number of Medicinal Treatments, "
        "after achieving indicator 5.2.6, with 25% per 2 years until the WNMT "
        "is at or below the Global Level."
    )

    result = analyze_requirement_semantics(text, language="en")

    assert [
        (
            item.span.text,
            item.operator,
            item.normalized_value,
            item.unit,
            item.ambiguous,
        )
        for item in result.thresholds
    ] == [
        ("25%", "eq", 25.0, "%", False),
        ("at or below the Global Level", "lte", "Global Level", None, False),
    ]
    assert [item.marker.text for item in result.conditions] == ["after", "until"]
    assert [item.span.text for item in result.dates] == ["per 2 years"]


def test_numeric_applicability_phrase_is_condition_but_postnominal_after_is_not() -> None:
    applicable = (
        "Maximum unexplained mortality rate from each of the previous two "
        "production cycles, for farms with total mortality > 6%"
    )
    postnominal = "Compliance with all withholding periods after treatments"

    applicable_result = analyze_requirement_semantics(applicable, language="en")
    postnominal_result = analyze_requirement_semantics(postnominal, language="en")

    assert [item.clause.text for item in applicable_result.conditions] == [
        "for farms with total mortality > 6%"
    ]
    assert postnominal_result.conditions == []


def test_country_entry_level_is_a_qualitative_lte_threshold() -> None:
    text = (
        "The Weighted Number of Medicinal Treatments shall be at or below the "
        "country Entry Level."
    )

    result = analyze_requirement_semantics(text, language="en")

    assert [
        (item.span.text, item.operator, item.normalized_value, item.unit)
        for item in result.thresholds
    ] == [(
        "at or below the country Entry Level",
        "lte",
        "country Entry Level",
        None,
    )]


def test_ambiguous_comma_number_is_not_silently_normalized() -> None:
    text = "The operator shall retain at least 1,000 records."

    result = analyze_requirement_semantics(text, language="en")

    threshold = result.thresholds[0]
    assert threshold.value == "1,000"
    assert threshold.normalized_value is None
    assert threshold.ambiguous
    assert "ambiguous_numeric_separator" in threshold.flags


def test_ambiguous_language_and_where_are_explicitly_flagged() -> None:
    text = "Apply where relevant."

    result = analyze_requirement_semantics(text)

    assert result.language.language == "en"
    assert result.language.ambiguous
    assert "ambiguous_language" in result.flags
    assert result.conditions[0].ambiguous
    assert "where_may_be_locative_or_relative" in result.conditions[0].flags


def test_calendar_month_may_is_not_a_permission_modality() -> None:
    text = "The requirement enters into force in May 2025."

    result = analyze_requirement_semantics(text, language="en")

    assert result.modalities == []


def test_empty_source_fails_closed_without_inventing_semantics() -> None:
    result = analyze_requirement_semantics("")

    assert result.flags == ["empty_source_text", "ambiguous_language"]
    assert result.modalities == []
    assert result.negations == []
    assert result.conditions == []
    assert result.exceptions == []
    assert result.thresholds == []
    assert result.cross_references == []


def test_language_assessment_can_be_explicit_without_overwriting_source_scores() -> None:
    assessment = assess_language("The operator shall comply.", language="no")

    assert assessment.language == "no"
    assert assessment.method == "explicit"
    assert assessment.english_score > 0
    assert assessment.norwegian_score == 0


@pytest.mark.parametrize(
    ("text", "token", "candidate_type"),
    [
        ("Foretaket skal registrere data.", "skal", "modality"),
        ("Foretaket må registrere data.", "må", "modality"),
        ("Foretaket kan registrere data.", "kan", "modality"),
        ("Foretaket skal ikke registrere data.", "ikke", "negation"),
        ("Kravet gjelder dersom anlegget er åpent.", "dersom", "condition"),
        ("Kravet gjelder hvis anlegget er åpent.", "hvis", "condition"),
        ("Kravet gjelder når anlegget er åpent.", "når", "condition"),
        ("Kravet gjelder unntatt bokstav a.", "unntatt", "exception"),
        ("Kravet gjelder med mindre § 2 gjelder.", "med mindre", "exception"),
    ],
)
def test_requested_norwegian_legal_cues_are_covered(
    text: str,
    token: str,
    candidate_type: str,
) -> None:
    result = analyze_requirement_semantics(text, language="no")

    if candidate_type == "modality":
        actual = [item.span.text.lower() for item in result.modalities]
    elif candidate_type == "negation":
        actual = [item.span.text.lower() for item in result.negations]
    elif candidate_type == "condition":
        actual = [item.marker.text.lower() for item in result.conditions]
    else:
        actual = [item.marker.text.lower() for item in result.exceptions]
    assert token in actual


@pytest.mark.parametrize("marker", ["if", "when", "where", "provided that"])
def test_requested_english_condition_markers_are_covered(marker: str) -> None:
    text = f"The rule shall apply {marker} the permit is active."

    result = analyze_requirement_semantics(text, language="en")

    assert [item.marker.text.lower() for item in result.conditions] == [marker]


def test_embedded_english_basis_and_sequence_conditions_keep_exact_clauses() -> None:
    text = (
        "The operator shall, after the baseline is established, conduct monitoring "
        "based on the approved method."
    )

    result = analyze_requirement_semantics(text, language="en")

    assert [item.marker.text.lower() for item in result.conditions] == [
        "after",
        "based on",
    ]
    assert [item.clause.text for item in result.conditions] == [
        "after the baseline is established",
        "based on the approved method",
    ]
    _assert_all_reported_spans_are_exact(result)


def test_no_and_not_negations_have_bounded_source_scopes() -> None:
    text = (
        "The operator shall ensure there is no decline in status, and shall not "
        "discharge pesticides."
    )

    result = analyze_requirement_semantics(text, language="en")

    assert [
        (item.span.text, item.scope.text if item.scope else None)
        for item in result.negations
    ] == [
        ("no", "decline in status"),
        ("not", "discharge pesticides"),
    ]


def test_month_and_year_windows_are_dates_not_quantity_thresholds() -> None:
    text = (
        "The rate shall remain above 15% over the previous 24 months, and a bloom "
        "shall be recorded within the past 10 years."
    )

    result = analyze_requirement_semantics(text, language="en")

    assert [item.span.text for item in result.thresholds] == ["15%"]
    assert [item.span.text for item in result.dates] == [
        "over the previous 24 months",
        "within the past 10 years",
    ]
    _assert_all_reported_spans_are_exact(result)


def test_first_n_years_of_event_is_date_not_quantity_threshold() -> None:
    text = (
        "The declaration is not required for the first three years of the "
        "standard being effective."
    )

    result = analyze_requirement_semantics(text, language="en")

    assert [item.span.text for item in result.dates] == [
        "for the first three years of the standard being effective"
    ]
    assert result.thresholds == []
    _assert_all_reported_spans_are_exact(result)


def test_production_cycle_frequency_and_deadline_phrases_are_dates() -> None:
    text = (
        "Use each of the previous two production cycles and the most recent "
        "complete production cycle. Report for each production cycle, reduce "
        "25% per 2 years, set annual targets, monitor annually, and certify "
        "before prescribing medication."
    )

    result = analyze_requirement_semantics(text, language="en")

    assert [item.span.text for item in result.dates] == [
        "each of the previous two production cycles",
        "the most recent complete production cycle",
        "for each production cycle",
        "per 2 years",
        "annual targets",
        "annually",
        "before prescribing medication",
    ]
    assert all(item.span.text != "2 years" for item in result.thresholds)
    _assert_all_reported_spans_are_exact(result)


def test_requested_multiword_threshold_units_are_source_exact() -> None:
    text = (
        "Act at ≥5 index points, ≥1 adverse turnover event, or ≥1 harmful algal "
        "bloom."
    )

    result = analyze_requirement_semantics(text, language="en")

    assert [(item.span.text, item.unit) for item in result.thresholds] == [
        ("≥5 index points", "index points"),
        ("≥1 adverse turnover event", "adverse turnover event"),
        ("≥1 harmful algal bloom", "harmful algal bloom"),
    ]
    assert all(not item.ambiguous for item in result.thresholds)


def test_structural_at_least_one_is_not_misclassified_as_threshold() -> None:
    text = (
        "The operator shall act when at least one of the following is identified: "
        "loss or damage."
    )

    result = analyze_requirement_semantics(text, language="en")

    assert result.thresholds == []
    assert result.conditions[0].clause.text == (
        "when at least one of the following is identified"
    )


def test_norwegian_number_word_to_is_not_an_english_bare_quantity() -> None:
    text = "The standard is applicable to incidents involving listed species."

    result = analyze_requirement_semantics(text, language="en")

    assert result.thresholds == []


def test_source_field_labels_are_hard_threshold_and_scope_boundaries() -> None:
    text = (
        "Indicator: FishSource score "
        "Requirement: The farm shall act if the score is ≥ 6 "
        "Applicability: All sites"
    )

    result = analyze_requirement_semantics(text, language="en")

    assert [(item.span.text, item.unit) for item in result.thresholds] == [
        ("≥ 6", None)
    ]
    assert [item.scope.text for item in result.modalities if item.scope] == ["act"]
    assert [item.clause.text for item in result.conditions] == [
        "if the score is ≥ 6"
    ]
    assert all("Applicability" not in item.span.text for item in result.thresholds)
    assert all(
        item.scope is None or "Applicability" not in item.scope.text
        for item in result.modalities
    )
    _assert_all_reported_spans_are_exact(result)


def test_field_boundary_does_not_treat_unlabelled_words_as_labels() -> None:
    text = "The operator shall retain at least one applicability record."

    result = analyze_requirement_semantics(text, language="en")

    assert result.thresholds[0].span.text == "at least one applicability"
    assert result.thresholds[0].unit == "applicability"
    assert result.thresholds[0].ambiguous


def test_newline_label_cannot_become_a_threshold_unit() -> None:
    text = "Requirement: < 1.2\nApplicability: All"

    result = analyze_requirement_semantics(text, language="en")

    assert [(item.span.text, item.unit) for item in result.thresholds] == [
        ("< 1.2", None)
    ]
    assert not any(
        flag.endswith(":Applicability")
        for flag in result.flags
        if flag.startswith("threshold_unit_requires_review:")
    )


def test_comma_punctuation_does_not_hide_the_preceding_threshold() -> None:
    text = (
        "Requirement: All individual scores ≥ 6, and biomass score ≥ 6 "
        "Applicability: All"
    )

    result = analyze_requirement_semantics(text, language="en")

    assert [(item.span.text, item.unit) for item in result.thresholds] == [
        ("≥ 6", None),
        ("≥ 6", None),
    ]
    assert not any(flag.startswith("unparsed_threshold_comparator:") for flag in result.flags)
