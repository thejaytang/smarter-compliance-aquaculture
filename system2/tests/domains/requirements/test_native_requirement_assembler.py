from __future__ import annotations

import json
from pathlib import Path

from pdf_extraction.domains.requirements import (
    NativeRequirementAssembler,
    TemplateFamily,
    canonicalize_native_requirement,
)
from pdf_extraction.domains.requirements.native_assembler import _clean
from pdf_extraction.types import NativeObject, NativePage
from tests.support.paths import PROJECT_ROOT


ROOT = PROJECT_ROOT
ROUND1 = ROOT / "outputs" / "runs" / "goal04-round1"
ROUND3_FARM = (
    ROOT / "outputs" / "runs" / "goal04-round3"
    / "farm-standard-p064-p065-active" / "raw"
)
ROUND3_SALMON = (
    ROOT / "outputs" / "runs" / "goal04-round3"
    / "salmon-cod-standard-p027-p028-holdout" / "raw"
)
ROUND4_INTERPRETATION = (
    ROOT / "outputs" / "runs" / "goal04-round4"
    / "interpretation-manual-p103-p106-active" / "raw"
)
ROUND4_AUDIT = (
    ROOT / "outputs" / "runs" / "goal04-round4"
    / "audit-manual-p011-p012-holdout" / "raw"
)


def _native_page(path: Path) -> NativePage:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return NativePage(
        page_index=raw["page_index"],
        width_points=raw["width_points"],
        height_points=raw["height_points"],
        words=[NativeObject(**item) for item in raw["words"]],
        text_lines=[NativeObject(**item) for item in raw["text_lines"]],
    )


def _sample_pages(sample: str) -> list[NativePage]:
    return [
        _native_page(path)
        for path in sorted((ROUND1 / sample / "raw").glob("native-page-*.json"))
    ]


def _round3_farm_pages() -> list[NativePage]:
    return [
        _native_page(path)
        for path in sorted(ROUND3_FARM.glob("native-page-*.json"))
    ]


def _round3_salmon_pages() -> list[NativePage]:
    return [
        _native_page(path)
        for path in sorted(ROUND3_SALMON.glob("native-page-*.json"))
    ]


def _round4_interpretation_pages() -> list[NativePage]:
    return [
        _native_page(path)
        for path in sorted(ROUND4_INTERPRETATION.glob("native-page-*.json"))
    ]


def _round4_audit_pages() -> list[NativePage]:
    return [
        _native_page(path)
        for path in sorted(ROUND4_AUDIT.glob("native-page-*.json"))
    ]


def test_round1_native_templates_recover_all_25_requirement_ids() -> None:
    expected = {
        "farm-standard-p028-p029": (
            TemplateFamily.SINGLE_COLUMN_INDICATORS,
            ["1.1.1", "1.1.2", "1.2.1", "1.2.2", "1.2.3", "1.2.4"],
        ),
        "salmon-cod-standard-p018": (
            TemplateFamily.LEGACY_INDICATOR_VALUE,
            ["1.1.1", "1.1.2", "1.1.3", "1.1.4"],
        ),
        "audit-manual-p001-p003": (
            TemplateFamily.AUDIT_MATRIX,
            [
                "1.1.1", "1.1.2", "1.1.3", "1.1.4",
                "2.1.1", "2.1.2", "2.1.3", "2.1.4",
                "2.2.1", "2.2.2", "2.2.3", "2.2.4",
            ],
        ),
        "interpretation-manual-p019-p021": (
            TemplateFamily.ID_NORMATIVE_WITH_CONTEXT,
            ["1.4.1", "1.4.2", "1.4.3"],
        ),
    }
    assembler = NativeRequirementAssembler()
    recovered = 0
    for sample, (family, ids) in expected.items():
        requirements = assembler.assemble(_sample_pages(sample))
        assert [item.requirement_id for item in requirements] == ids
        assert {item.family for item in requirements} == {family}
        recovered += len(requirements)
    assert recovered == 25


def test_every_requirement_keeps_role_page_bbox_and_source_text() -> None:
    assembler = NativeRequirementAssembler()
    requirements = []
    for sample in (
        "farm-standard-p028-p029",
        "salmon-cod-standard-p018",
        "audit-manual-p001-p003",
        "interpretation-manual-p019-p021",
    ):
        requirements.extend(assembler.assemble(_sample_pages(sample)))

    for requirement in requirements:
        record = requirement.to_dict()
        assert record["source_text"]
        assert record["page_number"] == record["page_index"] + 1
        assert record["bbox"]["x1"] > record["bbox"]["x0"]
        assert record["bbox"]["y1"] > record["bbox"]["y0"]
        assert {span["role"] for span in record["source_segments"]} >= {
            "requirement_id"
        }
        for span in record["source_segments"]:
            assert span["source_text"]
            assert span["page_number"] == span["page_index"] + 1
            assert span["bbox"]["x1"] > span["bbox"]["x0"]
            assert span["bbox"]["y1"] > span["bbox"]["y0"]


def test_short_non_modal_values_are_retained() -> None:
    assembler = NativeRequirementAssembler()
    legacy = assembler.assemble(_sample_pages("salmon-cod-standard-p018"))
    assert [item.requirement_value for item in legacy] == ["Yes"] * 4
    assert all(
        item.normative_text == f"{item.indicator_text}\n{item.requirement_value}"
        for item in legacy
    )

    audit = {
        item.requirement_id: item
        for item in assembler.assemble(_sample_pages("audit-manual-p001-p003"))
    }
    assert audit["2.2.2"].requirement_value == "5%"
    assert audit["2.1.4"].requirement_value == "Yes"


def test_audit_matrix_keeps_client_and_auditor_columns_separate() -> None:
    audit = {
        item.requirement_id: item
        for item in NativeRequirementAssembler().assemble(
            _sample_pages("audit-manual-p001-p003")
        )
    }
    assert len(audit["2.1.2"].client_actions) == 9
    assert len(audit["2.1.2"].auditor_actions) == 9
    assert all(action[0].islower() for action in audit["2.1.2"].client_actions)
    assert all(action[0].isupper() for action in audit["2.1.2"].auditor_actions)
    assert audit["1.1.1"].client_actions[0].startswith("a. Maintain")
    assert audit["1.1.1"].auditor_actions[0].startswith("A. Review")


def test_audit_actions_stop_at_next_section_header_and_repair_token_spacing() -> None:
    audit = {
        item.requirement_id: item
        for item in NativeRequirementAssembler().assemble(
            _sample_pages("audit-manual-p001-p003")
        )
    }

    assert "Required Client Actions" not in audit["1.1.4"].client_actions[-1]
    assert "Required CAB Actions" not in audit["1.1.4"].auditor_actions[-1]
    assert "site-specific" in audit["2.1.4"].auditor_actions[1]
    assert "ortho-P" in audit["2.2.4"].client_actions[0]


def test_context_guidance_is_not_promoted_and_cross_page_text_is_joined() -> None:
    requirements = {
        item.requirement_id: item
        for item in NativeRequirementAssembler().assemble(
            _sample_pages("interpretation-manual-p019-p021")
        )
    }
    cross_page = requirements["1.4.3"]
    assert {span.page_number for span in cross_page.source_segments} == {20, 21}
    assert "documentation accompanying the feed identifies" in cross_page.normative_text
    assert "How do I interpret this requirement?" not in cross_page.normative_text
    assert "Auditors should confirm" not in cross_page.normative_text
    assert "Aquaculture Stewardship Council" not in cross_page.normative_text


def test_selected_indices_only_assemble_requested_pages() -> None:
    pages = _sample_pages("farm-standard-p028-p029")
    requirements = NativeRequirementAssembler().assemble(
        pages,
        selected_indices=[pages[1].page_index],
    )
    assert [item.requirement_id for item in requirements] == [
        "1.2.1", "1.2.2", "1.2.3", "1.2.4"
    ]


def test_selected_window_recovers_proven_page_top_single_column_continuation() -> None:
    previous_words = [
        NativeObject("p53-id", "2.6.13", (54.0, 620.0, 92.0, 635.0)),
        NativeObject("p53-root", "The UoC shall act when one applies:", (118.0, 620.0, 360.0, 635.0)),
        NativeObject("p53-a", "a.", (136.0, 642.0, 147.0, 654.0)),
        NativeObject("p53-a-text", "first condition; or", (154.0, 642.0, 280.0, 654.0)),
        NativeObject("p53-b", "b.", (136.0, 670.0, 147.0, 682.0)),
        NativeObject("p53-b-text", "second condition; or", (154.0, 670.0, 290.0, 682.0)),
    ]
    current_words = [
        NativeObject("p54-c", "c.", (136.0, 72.0, 147.0, 84.0)),
        NativeObject("p54-c-text", "third condition; or", (154.0, 72.0, 282.0, 84.0)),
        NativeObject("p54-d", "d.", (136.0, 102.0, 147.0, 114.0)),
        NativeObject("p54-d-text", "fourth condition; or", (154.0, 102.0, 288.0, 114.0)),
        NativeObject("p54-e", "e.", (136.0, 132.0, 147.0, 144.0)),
        NativeObject("p54-e-text", "fifth condition.", (154.0, 132.0, 260.0, 144.0)),
        NativeObject("p54-next-id", "2.6.14", (54.0, 180.0, 92.0, 195.0)),
        NativeObject("p54-next-text", "The UoC shall report annually.", (118.0, 180.0, 330.0, 195.0)),
    ]
    pages = [
        NativePage(53, 595.0, 842.0, words=previous_words),
        NativePage(54, 595.0, 842.0, words=current_words),
    ]
    families = {
        53: TemplateFamily.SINGLE_COLUMN_INDICATORS,
        54: TemplateFamily.SINGLE_COLUMN_INDICATORS,
    }

    requirements = NativeRequirementAssembler().assemble(
        pages,
        selected_indices=[54],
        family=families,
    )

    assert [item.requirement_id for item in requirements] == ["2.6.13", "2.6.14"]
    continuation = requirements[0]
    assert continuation.normative_text == (
        "c. third condition; or\n"
        "d. fourth condition; or\n"
        "e. fifth condition."
    )
    assert continuation.indicator_text == "2.6.13"
    assert [span.role for span in continuation.source_segments] == [
        "continuation_anchor",
        "requirement_continuation",
        "requirement_continuation",
        "requirement_continuation",
    ]
    assert continuation.source_segments[0].page_index == 53
    assert {span.page_index for span in continuation.source_segments[1:]} == {54}

    canonical = canonicalize_native_requirement(continuation)
    assert canonical.status.value == "review_required"
    assert "requirement_identity_from_preceding_page" in canonical.source_anomalies


def test_page_top_list_is_not_attached_without_successor_identity() -> None:
    previous = NativePage(
        53,
        595.0,
        842.0,
        words=[
            NativeObject("id", "2.6.13", (54.0, 660.0, 92.0, 675.0)),
            NativeObject("root", "The UoC shall act.", (118.0, 660.0, 260.0, 675.0)),
            NativeObject("b", "b.", (136.0, 680.0, 147.0, 692.0)),
            NativeObject("b-text", "second condition; or", (154.0, 680.0, 290.0, 692.0)),
        ],
    )
    current = NativePage(
        54,
        595.0,
        842.0,
        words=[
            NativeObject("c", "c.", (136.0, 72.0, 147.0, 84.0)),
            NativeObject("c-text", "unrelated list text", (154.0, 72.0, 280.0, 84.0)),
            NativeObject("next", "2.6.15", (54.0, 180.0, 92.0, 195.0)),
            NativeObject("next-text", "The UoC shall report.", (118.0, 180.0, 300.0, 195.0)),
        ],
    )

    requirements = NativeRequirementAssembler().assemble(
        [previous, current],
        selected_indices=[54],
        family={
            53: TemplateFamily.SINGLE_COLUMN_INDICATORS,
            54: TemplateFamily.SINGLE_COLUMN_INDICATORS,
        },
    )

    assert [item.requirement_id for item in requirements] == ["2.6.15"]


def test_single_column_continuation_recovers_all_ten_p64_p65_rows() -> None:
    requirements = NativeRequirementAssembler().assemble(_round3_farm_pages())
    assert [item.requirement_id for item in requirements] == [
        "2.11.1", "2.11.2", "2.11.3", "2.11.4", "2.11.5",
        "2.11.6", "2.11.7", "2.11.8", "2.11.9", "2.11.10",
    ]
    assert {item.family for item in requirements} == {
        TemplateFamily.SINGLE_COLUMN_INDICATORS
    }


def test_single_column_applicability_uses_modal_boundary_and_own_span() -> None:
    requirements = {
        item.requirement_id: item
        for item in NativeRequirementAssembler().assemble(_round3_farm_pages())
    }
    expected = {
        "2.11.2": "point-source discharge",
        "2.11.8": (
            "cage culture and suspended culture not using copper-treated "
            "gear or infrastructure"
        ),
        "2.11.9": (
            "cage culture and suspended culture using copper-treated "
            "gear or infrastructure"
        ),
        "2.11.10": (
            "cage culture and suspended culture using copper-treated "
            "gear or infrastructure"
        ),
    }
    assert {
        key: item.applicability
        for key, item in requirements.items() if item.applicability
    } == expected
    for requirement_id, applicability in expected.items():
        requirement = requirements[requirement_id]
        spans = [
            span for span in requirement.source_segments
            if span.role == "applicability"
        ]
        assert len(spans) == 1
        assert spans[0].source_text == f"Indicator applicability: {applicability}"
        assert "Indicator applicability:" not in requirement.normative_text
        assert requirement.normative_text.startswith("The UoC shall")


def test_superscript_45_is_evidence_not_semantic_normative_text() -> None:
    requirement = next(
        item for item in NativeRequirementAssembler().assemble(_round3_farm_pages())
        if item.requirement_id == "2.11.3"
    )
    assert requirement.normative_text == "The UoC shall dispose of waste responsibly."
    assert requirement.footnote_markers == ["45"]
    source = next(
        span.source_text for span in requirement.source_segments
        if span.role == "normative_text"
    )
    assert "waste45 responsibly" in source


def test_list_glyphs_and_superscripts_stay_in_evidence_but_not_semantics() -> None:
    requirement = next(
        item for item in NativeRequirementAssembler().assemble(_round3_farm_pages())
        if item.requirement_id == "2.11.4"
    )
    assert requirement.footnote_markers == ["46", "47", "48"]
    assert " o " not in f" {requirement.normative_text} "
    assert not any(marker in requirement.normative_text for marker in ("46", "47", "48"))
    assert "The Rotterdam Convention" in requirement.normative_text
    assert "The Stockholm Convention" in requirement.normative_text
    assert "The World Health Organisation" in requirement.normative_text

    source = next(
        span.source_text for span in requirement.source_segments
        if span.role == "normative_text"
    )
    assert "o The Rotterdam" in source
    assert "(PIC)46" in source
    assert "(POPs)47" in source
    assert "(classes Ia and Ib).48" in source

    ordinary_number = next(
        item for item in NativeRequirementAssembler().assemble(_round3_farm_pages())
        if item.requirement_id == "2.11.6"
    )
    assert "at least 48 hours" in ordinary_number.normative_text
    assert ordinary_number.footnote_markers == []


def test_legacy_superscripts_follow_host_row_and_leave_semantic_fields() -> None:
    requirements = {
        item.requirement_id: item
        for item in NativeRequirementAssembler().assemble(
            _round3_salmon_pages(), family=TemplateFamily.LEGACY_INDICATOR_VALUE
        )
    }

    assert requirements["2.5.2"].footnote_markers == ["30", "31"]
    assert requirements["2.5.3"].footnote_markers == ["32", "33"]
    assert requirements["2.5.4"].footnote_markers == ["34"]
    assert requirements["2.5.5"].footnote_markers == ["35", "36"]
    assert requirements["2.5.6"].footnote_markers == []

    for requirement_id, markers in {
        "2.5.2": ("30", "31"),
        "2.5.3": ("32", "33"),
        "2.5.4": ("34",),
        "2.5.5": ("35", "36"),
    }.items():
        requirement = requirements[requirement_id]
        assert not any(marker in requirement.indicator_text for marker in markers)
        assert not any(marker in requirement.normative_text for marker in markers)
        assert not any(marker in requirement.requirement_value for marker in markers)

    indicator_source = next(
        span.source_text for span in requirements["2.5.2"].source_segments
        if span.role == "indicator_text"
    )
    value_source = next(
        span.source_text for span in requirements["2.5.5"].source_segments
        if span.role == "requirement_value"
    )
    assert "mortalities30" in indicator_source
    assert "listed31" in indicator_source
    assert "incidents,36" in value_source


def test_legacy_ordinary_numbers_and_numbered_steps_are_not_footnotes() -> None:
    requirements = {
        item.requirement_id: item
        for item in NativeRequirementAssembler().assemble(
            _round3_salmon_pages(), family=TemplateFamily.LEGACY_INDICATOR_VALUE
        )
    }

    assert requirements["2.5.1"].requirement_value == "0"
    assert requirements["2.5.1"].footnote_markers == []
    assert "1. All other avenues" in requirements["2.5.3"].indicator_text
    assert "2. Approval was given" in requirements["2.5.3"].indicator_text
    assert "3. Explicit permission" in requirements["2.5.3"].indicator_text
    assert requirements["2.5.5"].requirement_value.startswith(
        "< 9 lethal incidents,"
    )
    assert "9" not in requirements["2.5.5"].footnote_markers


def test_normative_context_rows_keep_list_and_footnote_marks_out_of_semantics() -> None:
    requirements = {
        item.requirement_id: item
        for item in NativeRequirementAssembler().assemble(
            _round4_interpretation_pages(),
            family={
                page.page_index: TemplateFamily.ID_NORMATIVE_WITH_CONTEXT
                for page in _round4_interpretation_pages()
                if page.page_index in {102, 104}
            },
        )
    }

    assert list(requirements) == ["2.6.10", "2.6.11", "2.6.12", "2.6.13"]
    assert requirements["2.6.10"].footnote_markers == ["13"]
    assert "(8.8) 13" not in requirements["2.6.10"].normative_text
    assert " o " not in f" {requirements['2.6.10'].normative_text} "
    assert " o " not in f" {requirements['2.6.13'].normative_text} "
    assert "≥15%" in requirements["2.6.13"].normative_text
    assert "≥1 5%" not in requirements["2.6.13"].normative_text

    source = next(
        span.source_text for span in requirements["2.6.10"].source_segments
        if span.role == "normative_text"
    )
    assert "(8.8)13" in source
    assert "o Total Nitrogen" in source


def test_revealed_active_sources_generate_source_faithful_clause_structure() -> None:
    interpretation_native = {
        item.requirement_id: item
        for item in NativeRequirementAssembler().assemble(
            _round4_interpretation_pages(),
            family={
                page.page_index: TemplateFamily.ID_NORMATIVE_WITH_CONTEXT
                for page in _round4_interpretation_pages()
                if page.page_index in {102, 104}
            },
        )
    }
    interpretation = {
        key: canonicalize_native_requirement(value)
        for key, value in interpretation_native.items()
    }
    assert [item.marker for item in interpretation["2.6.10"].clauses] == [
        None, "o", "o", "o", "o", "o"
    ]
    assert [item.joins_next for item in interpretation["2.6.13"].clauses[1:]] == [
        "or", "or", "or", "or", None
    ]
    assert interpretation["2.6.11"].clauses[0].text == (
        interpretation["2.6.11"].normative_text
    )

    farm_native = {
        item.requirement_id: item
        for item in NativeRequirementAssembler().assemble(_round3_farm_pages())
    }
    farm = {
        key: canonicalize_native_requirement(value)
        for key, value in farm_native.items()
    }
    assert farm["2.11.3"].clauses[0].text == farm["2.11.3"].normative_text
    assert [item.marker for item in farm["2.11.4"].clauses] == [None, "o", "o", "o"]
    assert all(item.joins_next is None for item in farm["2.11.4"].clauses)

    salmon_native = {
        item.requirement_id: item
        for item in NativeRequirementAssembler().assemble(
            _round3_salmon_pages(), family=TemplateFamily.LEGACY_INDICATOR_VALUE
        )
    }
    salmon = canonicalize_native_requirement(salmon_native["2.5.3"])
    assert [item.marker for item in salmon.clauses] == [None, "1.", "2.", "3."]
    assert all(item.parent_clause_id == salmon.clauses[0].clause_id for item in salmon.clauses[1:])

    audit = [
        canonicalize_native_requirement(item)
        for item in NativeRequirementAssembler().assemble(_round4_audit_pages())
    ]
    assert audit
    assert all(len(item.clauses) == 1 for item in audit)
    assert all(item.clauses[0].text == item.normative_text for item in audit)


def test_audit_row_with_inline_indicator_label_is_not_lost_at_sample_boundary() -> None:
    requirements = NativeRequirementAssembler().assemble(_round4_audit_pages())

    assert [item.requirement_id for item in requirements] == [
        "3.4.4", "4.1.1", "4.2.1", "4.2.2", "4.3.1", "4.3.2", "4.3.3"
    ]
    first = requirements[0]
    assert first.indicator_text.startswith("Evidence of escape prevention planning")
    assert first.requirement_value == "Yes"
    assert first.applicability == "All"
    assert len(first.client_actions) == 5
    assert len(first.auditor_actions) == 6


def test_audit_normative_text_includes_applicability_and_drops_placeholder_dash() -> None:
    requirements = {
        item.requirement_id: item
        for item in NativeRequirementAssembler().assemble(_round4_audit_pages())
    }

    assert requirements["4.1.1"].normative_text.endswith("Applicability: All")
    assert requirements["4.3.1"].normative_text.endswith("Applicability: N/A")
    assert not requirements["4.1.1"].client_actions[-1].endswith(" -")
    client_spans = [
        span for span in requirements["4.1.1"].source_segments
        if span.role == "client_action"
    ]
    auditor_spans = [
        span for span in requirements["4.1.1"].source_segments
        if span.role == "auditor_action"
    ]
    assert len(client_spans) == len(requirements["4.1.1"].client_actions) == 5
    assert len(auditor_spans) == len(requirements["4.1.1"].auditor_actions) == 6
    assert all(span.source_text[:2].endswith(".") for span in client_spans)
    assert all(span.source_text[:2].endswith(".") for span in auditor_spans)


def test_audit_metadata_has_direct_field_level_provenance() -> None:
    requirements = NativeRequirementAssembler().assemble(_round4_audit_pages())

    for requirement in requirements:
        by_role = {
            role: [
                span for span in requirement.source_segments if span.role == role
            ]
            for role in ("indicator_text", "requirement_value", "applicability")
        }
        assert all(len(spans) == 1 for spans in by_role.values())
        assert by_role["indicator_text"][0].source_text == requirement.indicator_text
        assert by_role["requirement_value"][0].source_text == requirement.requirement_value
        assert by_role["applicability"][0].source_text == requirement.applicability
        assert all(
            span.native_object_ids
            and span.bbox[2] > span.bbox[0]
            and span.bbox[3] > span.bbox[1]
            for spans in by_role.values()
            for span in spans
        )

    fishsource = next(
        item for item in requirements if item.requirement_id == "4.3.2"
    )
    assert tuple(round(value, 1) for value in next(
        span.bbox for span in fishsource.source_segments
        if span.role == "applicability"
    )) == (79.9, 605.5, 113.2, 610.3)


def test_audit_action_list_markers_stay_in_native_evidence_not_semantics() -> None:
    pages = _round4_audit_pages()
    requirements = {
        item.requirement_id: item
        for item in NativeRequirementAssembler().assemble(pages)
    }
    lines_by_id = {
        line.id: line.text
        for page in pages
        for line in page.text_lines
    }

    open_system = requirements["3.4.4"].client_actions[1]
    assert "areas: net strength testing;" in open_system
    assert "- net strength testing" not in open_system
    open_system_span = [
        span for span in requirements["3.4.4"].source_segments
        if span.role == "client_action"
    ][1]
    assert "- net strength testing" in open_system_span.source_text
    assert any(
        lines_by_id[native_id].strip().startswith("- net strength testing")
        for native_id in open_system_span.native_object_ids
    )

    inventory = requirements["4.2.1"].client_actions[0]
    assert "including: Quantities used" in inventory
    assert "- Quantities used" not in inventory


def test_audit_note_is_not_appended_to_prior_action_and_periods_are_source_faithful() -> None:
    requirements = {
        item.requirement_id: item
        for item in NativeRequirementAssembler().assemble(_round4_audit_pages())
    }

    assert requirements["4.2.1"].client_actions[-1] == (
        "e. Submit FFDRm to ASC as per Appendix VI for each production cycle."
    )
    assert not any(
        "Note: Under Indicator 4.2.2" in action
        for action in requirements["4.2.1"].client_actions
    )
    assert requirements["4.2.2"].client_actions[-1].endswith(".")
    assert requirements["4.2.2"].auditor_actions[-2].endswith(".")
    # The visible CAB F cell itself has no final period; do not invent one.
    assert requirements["4.2.2"].auditor_actions[-1].endswith("(Appendix VI)")


def test_audit_geometry_preserves_lowercase_cab_marker_and_excludes_note_row() -> None:
    def obj(identifier: str, text: str, x0: float, y0: float, x1: float) -> NativeObject:
        return NativeObject(identifier, text, (x0, y0, x1, y0 + 8.0))

    lines = [
        obj("indicator", "Indicator: Public IPM plan", 80, 376, 190),
        obj("cab-a", "a. Check the public plan.", 376, 383, 520),
        obj("client-a", "a. Publish the plan.", 194, 386, 330),
        obj("value", "Requirement: Yes", 80, 407, 150),
        obj("client-b", "b. Obtain veterinarian approval.", 194, 415, 350),
        obj("cab-b", "B. Verify veterinarian approval.", 376, 415, 530),
        obj("scope", "Applicability: All", 80, 420, 150),
        obj("note", "Note Indicator 5.2.10: Guidance is pending.", 186, 435, 500),
        obj("note-url", "example.org/guidance", 228, 443, 360),
        obj("next-indicator", "Indicator: Next requirement", 80, 460, 190),
        obj("next-value", "Requirement: Yes", 80, 480, 150),
        obj("next-scope", "Applicability: All", 80, 492, 150),
    ]
    page = NativePage(
        page_index=17,
        width_points=612,
        height_points=792,
        words=[
            obj("id-529", "5.2.9", 60, 398, 70),
            obj("id-5210", "5.2.10", 60, 480, 75),
        ],
        text_lines=lines,
    )

    requirements = {
        item.requirement_id: item
        for item in NativeRequirementAssembler().assemble(
            [page], family=TemplateFamily.AUDIT_MATRIX
        )
    }

    assert requirements["5.2.9"].auditor_actions == [
        "a. Check the public plan.",
        "B. Verify veterinarian approval.",
    ]
    assert requirements["5.2.9"].client_actions == [
        "a. Publish the plan.",
        "b. Obtain veterinarian approval.",
    ]
    assert not any(
        "guidance" in action.casefold() or "example.org" in action
        for action in [
            *requirements["5.2.9"].client_actions,
            *requirements["5.2.9"].auditor_actions,
        ]
    )
    assert not any(
        span.role == "instruction"
        for span in requirements["5.2.9"].source_segments
    )
    instructions = [
        span for span in requirements["5.2.10"].source_segments
        if span.role == "instruction"
    ]
    assert len(instructions) == 1
    assert instructions[0].source_text == (
        "Note Indicator 5.2.10: Guidance is pending.\n"
        "example.org/guidance"
    )


def test_audit_table_footnote_does_not_pollute_applicability_but_keeps_evidence() -> None:
    requirements = {
        item.requirement_id: item
        for item in NativeRequirementAssembler().assemble(_round4_audit_pages())
    }
    requirement = requirements["4.3.2"]

    assert requirement.applicability == "All"
    assert requirement.normative_text.endswith("Applicability: All")
    assert "FishSource scoring" not in requirement.normative_text
    assert requirements["4.2.2"].footnote_markers == ["52"]
    assert requirements["4.3.1"].footnote_markers == ["53", "54"]
    assert requirement.footnote_markers == ["55"]
    footnotes = [
        span for span in requirement.source_segments if span.role == "footnote"
    ]
    assert len(footnotes) == 1
    assert footnotes[0].source_text == (
        "[55] Or equivalent score using the same methodology. See Appendix "
        "IV-3 for explanation of FishSource scoring."
    )
    assert footnotes[0].native_object_ids


def test_native_clean_preserves_comparator_spacing_and_never_fuses_numbers() -> None:
    source = "Limits are ≥ 6, ≤ 10, < 1.2, and > 0.5."

    assert _clean(source) == source
    assert _clean("Scores ≥ 6 15%") == "Scores ≥ 6 15%"
    assert _clean("Indicator 4.3.2") == "Indicator 4.3.2"


def test_native_clean_repairs_balanced_straight_quote_spacing() -> None:
    assert _clean("an ' Acceptable ' benthic status") == "an 'Acceptable' benthic status"
    assert _clean("an 'Acceptable' benthic status") == "an 'Acceptable' benthic status"
    assert _clean("the farm's records") == "the farm's records"


def test_active_audit_fishsource_threshold_spacing_is_source_faithful() -> None:
    requirements = {
        item.requirement_id: item
        for item in NativeRequirementAssembler().assemble(_round4_audit_pages())
    }

    assert requirements["4.2.1"].requirement_value == "< 1.2"
    assert requirements["4.3.2"].requirement_value == (
        "All individual scores ≥ 6, and biomass score ≥ 6"
    )
