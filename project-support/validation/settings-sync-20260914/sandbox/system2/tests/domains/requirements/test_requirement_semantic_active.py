from __future__ import annotations

import json
from pathlib import Path

from pdf_extraction.domains.requirements import (
    NativeFootnoteLinkCandidate,
    NativeRequirement,
    RequirementSourceSpan,
    TemplateFamily,
    canonicalize_native_requirement,
)
from pdf_extraction.domains.requirements.semantics import analyze_requirement_semantics
from tests.support.paths import PROJECT_ROOT


ROOT = PROJECT_ROOT
ROUND4 = ROOT / "outputs" / "runs" / "goal04-round4"


def _requirements(relative_path: str) -> dict[str, dict[str, object]]:
    payload = json.loads((ROUND4 / relative_path / "regulatory-ir.json").read_text())
    return {item["requirement_id"]: item for item in payload["requirements"]}


def _canonical(requirement_id: str, text: str) -> object:
    native = NativeRequirement(
        requirement_id=requirement_id,
        family=TemplateFamily.SINGLE_COLUMN_INDICATORS,
        normative_text=text,
        source_segments=[
            RequirementSourceSpan(
                role="requirement_id",
                page_index=0,
                bbox=(10, 10, 50, 20),
                source_text=requirement_id,
                native_object_ids=(f"id-{requirement_id}",),
            ),
            RequirementSourceSpan(
                role="normative_text",
                page_index=0,
                bbox=(60, 10, 540, 40),
                source_text=text,
                native_object_ids=(f"body-{requirement_id}",),
            ),
        ],
    )
    return canonicalize_native_requirement(native, language="en")


def test_active_interpretation_conditions_negations_dates_and_units_regress() -> None:
    requirements = _requirements("interpretation-manual-p103-p106-active")

    analysis_10 = analyze_requirement_semantics(
        requirements["2.6.10"]["normative_text"], language="en"
    )
    assert [item.clause.text for item in analysis_10.conditions] == [
        "after the determination of the water quality baseline"
    ]

    analysis_11 = analyze_requirement_semantics(
        requirements["2.6.11"]["normative_text"], language="en"
    )
    assert [item.clause.text for item in analysis_11.conditions] == [
        "based on the monitoring of the water quality parameters"
    ]
    assert [
        (item.span.text, item.scope.text if item.scope else None)
        for item in analysis_11.negations
    ] == [
        ("no", "decline in trophic status compared to the water quality baseline determined"),
    ]

    analysis_12 = analyze_requirement_semantics(
        requirements["2.6.12"]["normative_text"], language="en"
    )
    assert [item.span.text for item in analysis_12.thresholds] == [">25%"]
    assert [item.span.text for item in analysis_12.dates] == [
        "over the previous 24 months"
    ]

    analysis_13 = analyze_requirement_semantics(
        requirements["2.6.13"]["normative_text"], language="en"
    )
    assert [(item.span.text, item.unit) for item in analysis_13.thresholds] == [
        ("≥5 index points", "index points"),
        ("≥15%", "%"),
        ("≥25%", "%"),
        ("≥15%", "%"),
        ("≥1 adverse turnover event", "adverse turnover event"),
        ("≥1 harmful algal bloom", "harmful algal bloom"),
    ]
    assert [item.span.text for item in analysis_13.dates] == [
        "over the past 24 months",
        "over the past 24 months",
        "over the past 24 months",
        "within the past 10 years",
    ]


def test_active_salmon_window_is_date_and_lethal_incident_unit_is_complete() -> None:
    requirements = _requirements("salmon-cod-standard-p027-p028-active")
    analysis = analyze_requirement_semantics(
        requirements["2.5.5"]["normative_text"], language="en"
    )

    assert [item.span.text for item in analysis.dates] == [
        "over the prior two years"
    ]
    assert [(item.span.text, item.unit) for item in analysis.thresholds] == [
        ("< 9 lethal incidents", "lethal incidents"),
        ("no more than two of the incidents", "incidents"),
    ]


def test_active_salmon_conditions_exclude_relative_and_nested_list_uses() -> None:
    requirements = _requirements("salmon-cod-standard-p027-p028-active")

    relative_when = analyze_requirement_semantics(
        requirements["2.5.1"]["normative_text"], language="en"
    )
    lethal_steps = analyze_requirement_semantics(
        requirements["2.5.3"]["normative_text"], language="en"
    )
    event_trigger = analyze_requirement_semantics(
        requirements["2.5.6"]["normative_text"], language="en"
    )

    assert relative_when.conditions == []
    assert [item.clause.text for item in lethal_steps.conditions] == [
        "prior to lethal action against a predator"
    ]
    assert [item.clause.text for item in event_trigger.conditions] == [
        "In the event of a lethal incident"
    ]


def test_active_interpretation_semantics_canonicalize_without_review_flags() -> None:
    requirements = _requirements("interpretation-manual-p103-p106-active")
    canonical = {
        requirement_id: _canonical(requirement_id, item["normative_text"])
        for requirement_id, item in requirements.items()
    }

    assert all(item.status.value == "accepted" for item in canonical.values())
    assert canonical["2.6.10"].conditions[0].applies_to.startswith(
        "conduct monitoring"
    )
    assert canonical["2.6.11"].negations[0].text.startswith("no decline")
    assert [item.raw_text for item in canonical["2.6.12"].thresholds] == [">25%"]
    assert [item.text for item in canonical["2.6.12"].dates] == [
        "over the previous 24 months"
    ]
    assert [item.unit for item in canonical["2.6.13"].thresholds] == [
        "index points",
        "%",
        "%",
        "%",
        "adverse turnover event",
        "harmful algal bloom",
    ]


def test_active_interpretation_linked_footnote_yields_bound_qualifiers() -> None:
    record = _requirements("interpretation-manual-p103-p106-active")["2.6.10"]
    text = record["normative_text"]
    reference = record["footnote_refs"][0]
    footnote_text = reference["text"]
    native = NativeRequirement(
        requirement_id="2.6.10",
        family=TemplateFamily.SINGLE_COLUMN_INDICATORS,
        normative_text=text,
        footnote_markers=[reference["marker"]],
        footnote_link_candidates=[NativeFootnoteLinkCandidate(
            marker=reference["marker"],
            link_type="direct",
            definition_page_index=102,
            definition_native_object_ids=("active-fn-13",),
        )],
        source_segments=[
            RequirementSourceSpan(
                role="requirement_id",
                page_index=102,
                bbox=(10, 10, 50, 20),
                source_text="2.6.10",
                native_object_ids=("active-id-2.6.10",),
            ),
            RequirementSourceSpan(
                role="normative_text",
                page_index=102,
                bbox=(60, 10, 540, 40),
                source_text=text,
                native_object_ids=("active-body-2.6.10",),
            ),
            RequirementSourceSpan(
                role="footnote",
                page_index=102,
                bbox=(60, 700, 540, 730),
                source_text=f"{reference['marker']} {footnote_text}",
                native_object_ids=("active-fn-13",),
            ),
        ],
    )

    canonical = canonicalize_native_requirement(native, language="en")
    footnote_segment_id = next(
        item.segment_id for item in canonical.source_segments if item.role == "footnote"
    )

    assert canonical.exemptions
    assert [item.text for item in canonical.dates] == [
        "over any rolling two-year period"
    ]
    assert canonical.thresholds[0].unit == "m"
    assert canonical.thresholds[0].source_segment_ids == [footnote_segment_id]


def test_active_farm_conditions_and_not_scope_regress() -> None:
    requirements = _requirements("farm-standard-p064-p065-active")

    feasible = analyze_requirement_semantics(
        requirements["2.11.1"]["normative_text"], language="en"
    )
    discharge = analyze_requirement_semantics(
        requirements["2.11.2"]["normative_text"], language="en"
    )
    only_if = analyze_requirement_semantics(
        requirements["2.11.8"]["normative_text"], language="en"
    )
    prohibition = analyze_requirement_semantics(
        requirements["2.11.9"]["normative_text"], language="en"
    )

    assert feasible.conditions[0].clause.text == "where feasible"
    assert not feasible.conditions[0].ambiguous
    assert discharge.conditions[0].clause.text == "prior to effluent discharge"
    assert only_if.conditions[0].clause.text == "only if the facility treats effluents"
    assert prohibition.negations[0].scope is not None
    assert prohibition.negations[0].scope.text == (
        "treat or clean aquaculture gear or infrastructure in situ"
    )


def test_active_salmon_page18_remains_semantically_quiet() -> None:
    requirements = _requirements("salmon-cod-standard-p018-active")

    for record in requirements.values():
        analysis = analyze_requirement_semantics(
            record["normative_text"], language="en"
        )
        assert analysis.conditions == []
        assert analysis.negations == []
        assert analysis.thresholds == []
        assert analysis.dates == []
