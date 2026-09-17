from __future__ import annotations

import json
from pathlib import Path

from pdf_extraction.models import RequirementStatus
from pdf_extraction.domains.requirements import (
    NativeRequirement,
    NativeRequirementAssembler,
    RequirementSourceSpan,
    TemplateFamily,
    canonicalize_native_requirement,
    detect_page_footnote_definitions,
    detect_table_footnote_definitions,
    link_requirement_footnotes,
)
from pdf_extraction.types import NativeObject, NativePage
from tests.support.paths import PROJECT_ROOT


ROOT = PROJECT_ROOT
ROUND1 = ROOT / "outputs" / "runs" / "goal04-round1"
ROUND3_FARM = (
    ROOT / "outputs" / "runs" / "goal04-round3"
    / "farm-standard-p064-p065-active" / "raw"
)
ROUND4_SALMON = (
    ROOT / "outputs" / "runs" / "goal04-round4"
    / "salmon-cod-standard-p027-p028-active" / "raw"
)
ROUND5_AUDIT = (
    ROOT / "outputs" / "runs" / "goal04-round5"
    / "audit-manual-p011-p012-active" / "raw"
)
ROUND5_AUDIT_P5 = (
    ROOT / "outputs" / "runs" / "goal04-round5"
    / "audit-manual-p005-holdout" / "raw"
)


def _word(
    object_id: str,
    text: str,
    bbox: tuple[float, float, float, float],
    font: str = "Body",
) -> NativeObject:
    return NativeObject(
        id=object_id,
        text=text,
        bbox_points=bbox,
        font_name=font,
    )


def _page(page_index: int, words: list[NativeObject]) -> NativePage:
    return NativePage(
        page_index=page_index,
        width_points=600,
        height_points=800,
        words=words,
    )


def _requirement(
    marker: str,
    *,
    page_index: int = 0,
    requirement_id: str = "1.2.3",
    normative_text: str = "The operator shall retain records.",
) -> NativeRequirement:
    return NativeRequirement(
        requirement_id=requirement_id,
        family=TemplateFamily.SINGLE_COLUMN_INDICATORS,
        normative_text=normative_text,
        indicator_text=normative_text,
        footnote_markers=[marker],
        source_segments=[
            RequirementSourceSpan(
                role="requirement_id",
                page_index=page_index,
                bbox=(20, 90, 60, 105),
                source_text=requirement_id,
                native_object_ids=("id",),
            ),
            RequirementSourceSpan(
                role="normative_text",
                page_index=page_index,
                bbox=(80, 90, 360, 110),
                source_text=f"The operator shall retain records{marker}.",
                native_object_ids=("body", "anchor"),
            ),
        ],
    )


def _plain_requirement(
    requirement_id: str,
    normative_text: str,
    *,
    page_index: int = 0,
) -> NativeRequirement:
    return NativeRequirement(
        requirement_id=requirement_id,
        family=TemplateFamily.SINGLE_COLUMN_INDICATORS,
        normative_text=normative_text,
        indicator_text=normative_text,
        source_segments=[RequirementSourceSpan(
            role="normative_text",
            page_index=page_index,
            bbox=(80, 90, 360, 110),
            source_text=normative_text,
            native_object_ids=(f"body-{requirement_id}",),
        )],
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


def _pages(path: Path) -> list[NativePage]:
    return [_native_page(item) for item in sorted(path.glob("native-page-*.json"))]


def test_exact_bottom_definition_links_and_canonicalizes() -> None:
    page = _page(0, [
        _word("id", "1.2.3", (20, 90, 60, 105)),
        _word("body", "records", (150, 95, 200, 105)),
        _word("anchor", "7", (201, 91, 206, 97), "Superscript"),
        _word("fn-marker", "7", (40, 700, 46, 706), "Footnote"),
        _word("fn-text-1", "Definition", (52, 698, 105, 708)),
        _word("fn-text-2", "text.", (110, 698, 140, 708)),
    ])

    linked = link_requirement_footnotes([_requirement("7")], [page])[0]
    footnote = next(span for span in linked.source_segments if span.role == "footnote")
    assert footnote.source_text == "7 Definition text."
    assert footnote.native_object_ids == ("fn-marker", "fn-text-1", "fn-text-2")

    canonical = canonicalize_native_requirement(linked)
    assert canonical.status == RequirementStatus.ACCEPTED
    assert [item.model_dump() for item in canonical.footnote_refs] == [{
        "marker": "7",
        "text": "Definition text.",
        "link_type": "direct",
        "source_segment_ids": ["req-1-2-3-p0001-footnote-01"],
    }]


def test_bracketed_candidate_marker_and_definition_canonicalize() -> None:
    page = _page(0, [
        _word("id", "1.2.3", (20, 90, 60, 105)),
        _word("body", "records", (150, 95, 200, 105)),
        _word("anchor", "[7]", (201, 91, 215, 99), "Body"),
        _word("fn-marker", "7", (40, 700, 46, 706), "Footnote"),
        _word("fn-text", "Definition.", (52, 698, 115, 708)),
    ])

    linked = link_requirement_footnotes([_requirement("[7]")], [page])[0]
    canonical = canonicalize_native_requirement(linked)
    assert [(item.marker, item.text, item.link_type) for item in canonical.footnote_refs] == [
        ("7", "Definition.", "direct")
    ]


def test_immediately_following_page_definition_is_inherited() -> None:
    first = _page(0, [
        _word("id", "1.2.3", (20, 90, 60, 105)),
        _word("body", "records", (150, 95, 200, 105)),
        _word("anchor", "7", (201, 91, 206, 97), "Superscript"),
    ])
    second = _page(1, [
        _word("fn-marker", "7", (40, 700, 46, 706), "Footnote"),
        _word("fn-text", "Definition.", (52, 698, 115, 708)),
    ])

    linked = link_requirement_footnotes([_requirement("7")], [first, second])[0]
    canonical = canonicalize_native_requirement(linked)
    assert canonical.status == RequirementStatus.ACCEPTED
    assert canonical.footnote_refs[0].link_type == "inherited"
    assert canonical.footnote_refs[0].text == "Definition."


def test_missing_or_ambiguous_definition_fails_closed_and_preserves_marker() -> None:
    base = [
        _word("id", "1.2.3", (20, 90, 60, 105)),
        _word("body", "records", (150, 95, 200, 105)),
        _word("anchor", "7", (201, 91, 206, 97), "Superscript"),
    ]
    missing = link_requirement_footnotes([_requirement("7")], [_page(0, base)])[0]
    missing_canonical = canonicalize_native_requirement(missing)
    assert missing_canonical.status == RequirementStatus.REVIEW_REQUIRED
    assert missing_canonical.footnote_refs[0].marker == "7"
    assert missing_canonical.footnote_refs[0].link_type == "anomalous"
    assert "footnote_definition_missing:7" in missing_canonical.source_anomalies

    ambiguous_page = _page(0, [
        *base,
        _word("fn-marker-1", "7", (40, 680, 46, 686), "Footnote"),
        _word("fn-text-1", "First.", (52, 678, 90, 688)),
        _word("fn-marker-2", "7", (40, 720, 46, 726), "Footnote"),
        _word("fn-text-2", "Second.", (52, 718, 100, 728)),
    ])
    ambiguous = link_requirement_footnotes(
        [_requirement("7")], [ambiguous_page]
    )[0]
    ambiguous_canonical = canonicalize_native_requirement(ambiguous)
    assert ambiguous_canonical.status == RequirementStatus.REVIEW_REQUIRED
    assert ambiguous_canonical.footnote_refs[0].marker == "7"
    assert "footnote_definition_ambiguous:7" in ambiguous_canonical.source_anomalies


def test_body_number_and_page_number_are_not_footnote_definitions() -> None:
    page = _page(0, [
        _word("body-number", "7", (40, 690, 46, 700)),
        _word("body-text", "days", (52, 690, 80, 700)),
        _word("page-number", "7", (520, 760, 526, 766), "Footer"),
        _word("page-label", "Page", (485, 758, 515, 768), "Footer"),
    ])
    assert detect_page_footnote_definitions(page) == []


def test_dynamic_bottom_cluster_recovers_definition_above_old_70_percent_cutoff() -> None:
    page = _page(0, [
        _word("body", "Body", (80, 480, 110, 492)),
        _word("marker-32", "32", (40, 540, 46, 546), "Footnote"),
        _word("text-32", "Lethal action: Definition.", (52, 538, 190, 548)),
        _word("marker-33", "33", (40, 565, 46, 571), "Footnote"),
        _word("text-33", "Exception text.", (52, 563, 140, 573)),
        _word("marker-34", "34", (40, 600, 46, 606), "Footnote"),
        _word("text-34", "Publication text.", (52, 598, 155, 608)),
    ])

    definitions = detect_page_footnote_definitions(page)
    assert [item.marker for item in definitions] == ["32", "33", "34"]
    assert definitions[0].bbox[1] < page.height_points * 0.70


def test_explicit_exact_requirement_ids_create_semantic_links_only() -> None:
    page = _page(0, [
        _word("body-a", "First", (80, 90, 110, 100)),
        _word("body-b", "Second", (80, 120, 120, 130)),
        _word("fn-marker", "29", (40, 650, 46, 656), "Footnote"),
        _word(
            "fn-text", "See requirements 1.2.3 and 1.2.4.",
            (52, 648, 250, 658), "Footnote",
        ),
    ])
    requirements = [
        _plain_requirement("1.2.3", "The operator shall retain records."),
        _plain_requirement("1.2.4", "The operator shall publish results."),
        _plain_requirement("1.2.5", "The operator shall inspect records."),
    ]

    linked = {
        item.requirement_id: item
        for item in link_requirement_footnotes(requirements, [page])
    }
    assert [
        (item.marker, item.link_type)
        for item in linked["1.2.3"].footnote_link_candidates
    ] == [("29", "semantic")]
    assert [
        (item.marker, item.link_type)
        for item in linked["1.2.4"].footnote_link_candidates
    ] == [("29", "semantic")]
    assert linked["1.2.5"].footnote_link_candidates == []


def test_term_definition_requires_exact_term_and_direct_family_context() -> None:
    page = _page(0, [
        _word("id", "1.2.3", (20, 90, 60, 105)),
        _word("body", "Mortalities", (150, 95, 200, 105)),
        _word("anchor", "35", (201, 91, 208, 97), "Superscript"),
        _word("fn-marker", "35", (40, 650, 46, 656), "Footnote"),
        _word(
            "fn-text", "Mortalities: Includes accidental deaths.",
            (52, 648, 260, 658), "Footnote",
        ),
    ])
    direct = _requirement(
        "35", requirement_id="1.2.3",
        normative_text="Mortalities shall be recorded.",
    )
    semantic = _plain_requirement(
        "1.2.4", "All mortalities shall be reported.", page_index=1
    )
    no_term = _plain_requirement(
        "1.2.5", "All deaths shall be reported.", page_index=1
    )

    linked = {
        item.requirement_id: item
        for item in link_requirement_footnotes([direct, semantic, no_term], [page])
    }
    assert [
        (item.marker, item.link_type)
        for item in linked["1.2.3"].footnote_link_candidates
    ] == [("35", "direct")]
    assert [
        (item.marker, item.link_type)
        for item in linked["1.2.4"].footnote_link_candidates
    ] == [("35", "semantic")]
    assert linked["1.2.5"].footnote_link_candidates == []


def test_direct_anchor_target_mismatch_stays_direct_and_adds_semantic_target() -> None:
    page = _page(0, [
        _word("id", "1.2.3", (20, 90, 60, 105)),
        _word("body", "records", (150, 95, 200, 105)),
        _word("anchor", "36", (201, 91, 208, 97), "Superscript"),
        _word("fn-marker", "36", (40, 650, 46, 656), "Footnote"),
        _word(
            "fn-text", "Standard 1.2.4 applies to these cases.",
            (52, 648, 250, 658), "Footnote",
        ),
    ])
    anchored = _requirement("36", requirement_id="1.2.3")
    target = _plain_requirement("1.2.4", "The operator shall report cases.")

    linked = {
        item.requirement_id: item
        for item in link_requirement_footnotes([anchored, target], [page])
    }
    direct = linked["1.2.3"].footnote_link_candidates[0]
    assert direct.link_type == "direct"
    assert direct.issues == (
        "footnote_direct_target_mismatch:36:explicit_targets=1.2.4",
    )
    assert direct.issues[0] in linked["1.2.3"].footnote_link_issues
    assert [
        (item.marker, item.link_type)
        for item in linked["1.2.4"].footnote_link_candidates
    ] == [("36", "semantic")]

    anchored_canonical = canonicalize_native_requirement(linked["1.2.3"])
    target_canonical = canonicalize_native_requirement(linked["1.2.4"])
    assert anchored_canonical.footnote_refs[0].link_type == "anomalous"
    assert direct.issues[0] in anchored_canonical.source_anomalies
    assert target_canonical.footnote_refs[0].link_type == "semantic"
    assert anchored_canonical.footnote_refs[0].text == target_canonical.footnote_refs[0].text
    anchored_region = next(
        item for item in anchored_canonical.source_segments
        if item.segment_id == anchored_canonical.footnote_refs[0].source_segment_ids[0]
    )
    target_region = next(
        item for item in target_canonical.source_segments
        if item.segment_id == target_canonical.footnote_refs[0].source_segment_ids[0]
    )
    assert anchored_region.native_object_refs == target_region.native_object_refs
    assert anchored_canonical.semantic_input is not None
    assert anchored_canonical.semantic_input.qualifier_fragments[0].role == "footnote"


def test_real_farm_p64_p65_links_45_to_48_without_semantic_invention() -> None:
    pages = _pages(ROUND3_FARM)
    assembled = NativeRequirementAssembler().assemble(pages)
    linked = {
        item.requirement_id: item
        for item in link_requirement_footnotes(assembled, pages)
    }
    expected = {
        "2.11.3": ["45"],
        "2.11.4": ["46", "47", "48"],
    }
    for requirement_id, markers in expected.items():
        requirement = linked[requirement_id]
        spans = [span for span in requirement.source_segments if span.role == "footnote"]
        assert len(spans) == len(markers)
        assert [span.source_text.split(maxsplit=1)[0] for span in spans] == markers
        assert requirement.footnote_link_issues == []
        assert [
            (item.marker, item.link_type)
            for item in requirement.footnote_link_candidates
        ] == [(marker, "direct") for marker in markers]
        canonical = canonicalize_native_requirement(requirement)
        assert [item.marker for item in canonical.footnote_refs] == markers
        assert all(item.text for item in canonical.footnote_refs)
        assert not any(
            anomaly.startswith("footnote_definition_")
            for anomaly in canonical.source_anomalies
        )


def test_real_salmon_p27_p28_links_29_to_36_with_explicit_context() -> None:
    pages = _pages(ROUND4_SALMON)
    family = {
        page.page_index: TemplateFamily.LEGACY_INDICATOR_VALUE for page in pages
    }
    assembled = NativeRequirementAssembler().assemble(pages, family=family)
    linked = {
        item.requirement_id: item
        for item in link_requirement_footnotes(assembled, pages)
    }

    assert [item.marker for item in detect_page_footnote_definitions(pages[1])] == [
        "32", "33", "34", "35", "36",
    ]
    matrix = {
        requirement_id: [
            (item.marker, item.link_type, bool(item.issues))
            for item in requirement.footnote_link_candidates
        ]
        for requirement_id, requirement in linked.items()
    }
    assert matrix == {
        "2.5.1": [],
        "2.5.2": [
            ("30", "direct", False),
            ("31", "direct", False),
            ("29", "semantic", False),
        ],
        "2.5.3": [
            ("32", "direct", False),
            ("33", "direct", False),
        ],
        "2.5.4": [("34", "direct", False)],
        "2.5.5": [
            ("35", "direct", False),
            ("36", "direct", True),
            ("29", "semantic", False),
        ],
        "2.5.6": [
            ("35", "semantic", False),
            ("36", "semantic", False),
        ],
    }
    assert linked["2.5.5"].footnote_link_issues == [
        "footnote_direct_target_mismatch:36:explicit_targets=2.5.6"
    ]


def test_real_audit_table_footnotes_are_detected_and_preserved() -> None:
    pages = _pages(ROUND5_AUDIT)
    definitions = detect_table_footnote_definitions(pages[1])
    assert [item.marker for item in definitions] == ["51", "52", "53", "54", "55"]
    assert definitions[3].source_text == (
        "[54] Meets ISEAL guidelines as demonstrated through full membership in "
        "the ISEAL Alliance, or equivalent as determined by  ASC."
    )

    assembled = NativeRequirementAssembler().assemble(pages)
    linked = {
        item.requirement_id: item
        for item in link_requirement_footnotes(assembled, pages)
    }
    requirement = linked["4.3.2"]
    assert [
        (item.marker, item.link_type)
        for item in requirement.footnote_link_candidates
    ] == [("55", "direct"), ("53", "semantic")]
    footnote_texts = [
        span.source_text
        for span in requirement.source_segments
        if span.role == "footnote"
    ]
    assert sum(text.startswith("[55]") for text in footnote_texts) == 1
    assert sum(text.startswith("[53]") for text in footnote_texts) == 1

    matrix = {
        item.requirement_id: [
            (candidate.marker, candidate.link_type, candidate.issues)
            for candidate in item.footnote_link_candidates
        ]
        for item in linked.values()
    }
    assert matrix["4.1.1"] == [("50", "direct", ())]
    assert matrix["4.2.1"] == [("51", "semantic", ())]
    assert matrix["4.2.2"] == [
        ("52", "direct", ()),
        ("51", "semantic", ()),
    ]
    assert matrix["4.3.1"] == [
        ("53", "direct", ()),
        ("54", "direct", ()),
    ]
    for requirement_id in ("4.1.1", "4.2.1", "4.2.2", "4.3.1", "4.3.2"):
        canonical = canonicalize_native_requirement(linked[requirement_id])
        assert all(item.text for item in canonical.footnote_refs)
        assert not any(
            anomaly.startswith("footnote_candidate_definition_")
            for anomaly in canonical.source_anomalies
        )


def test_real_audit_p5_owns_only_direct_or_ancestor_scoped_footnotes() -> None:
    pages = _pages(ROUND5_AUDIT_P5)
    definitions = detect_table_footnote_definitions(pages[0])
    by_marker = {item.marker: item for item in definitions}
    assert sorted(by_marker) == ["20", "21", "22", "23", "25", "26"]
    assert by_marker["23"].source_text == (
        "[23] See Appendix VI for transparency requirements for 2.5.2, 2.5.5 "
        "and 2.5.6."
    )

    assembled = NativeRequirementAssembler().assemble(pages)
    linked = {
        item.requirement_id: item
        for item in link_requirement_footnotes(assembled, pages)
    }
    matrix = {
        requirement_id: [
            (candidate.marker, candidate.link_type, candidate.issues)
            for candidate in requirement.footnote_link_candidates
        ]
        for requirement_id, requirement in linked.items()
    }
    assert matrix == {
        "2.4.2": [
            ("20", "direct", ()),
            ("21", "direct", ()),
            ("22", "direct", ()),
        ],
        "2.5.1": [],
        "2.5.2": [
            ("25", "direct", ()),
            ("26", "direct", ()),
            ("23", "semantic", ()),
        ],
    }
    spans_by_requirement = {
        requirement_id: [
            span.source_text.split(maxsplit=1)[0]
            for span in requirement.source_segments
            if span.role == "footnote"
        ]
        for requirement_id, requirement in linked.items()
    }
    assert spans_by_requirement == {
        "2.4.2": ["[20]", "[21]", "[22]"],
        "2.5.1": [],
        "2.5.2": ["[25]", "[26]", "[23]"],
    }
    for requirement in linked.values():
        canonical = canonicalize_native_requirement(requirement)
        assert all(item.text for item in canonical.footnote_refs)
        assert not any(
            anomaly.startswith("footnote_candidate_definition_")
            for anomaly in canonical.source_anomalies
        )


def test_unowned_upstream_footnote_span_is_removed_fail_closed() -> None:
    page = NativePage(
        page_index=0,
        width_points=600,
        height_points=800,
        words=[
            _word("id", "1.2.3", (20, 90, 60, 105)),
            _word("body", "records", (150, 95, 200, 105)),
            _word("anchor", "[7]", (201, 91, 215, 99)),
        ],
        text_lines=[
            _word("label-7", "Footnote", (40, 680, 75, 690)),
            _word("definition-7", "[7] Owned definition.", (80, 680, 190, 690)),
            _word("label-8", "Footnote", (40, 710, 75, 720)),
            _word("definition-8", "[8] Unrelated definition.", (80, 710, 210, 720)),
        ],
    )
    requirement = _requirement("7")
    requirement.source_segments.append(RequirementSourceSpan(
        role="footnote",
        page_index=0,
        bbox=(80, 710, 210, 720),
        source_text="[8] Unrelated definition.",
        native_object_ids=("definition-8",),
    ))

    linked = link_requirement_footnotes([requirement], [page])[0]
    footnotes = [
        span.source_text for span in linked.source_segments if span.role == "footnote"
    ]
    assert footnotes == ["[7] Owned definition."]
    assert [(item.marker, item.link_type) for item in linked.footnote_link_candidates] == [
        ("7", "direct")
    ]


def test_round1_active_samples_gain_no_false_footnote_links() -> None:
    assembler = NativeRequirementAssembler()
    for sample in (
        "farm-standard-p028-p029",
        "salmon-cod-standard-p018",
        "interpretation-manual-p019-p021",
    ):
        pages = _pages(ROUND1 / sample / "raw")
        linked = link_requirement_footnotes(assembler.assemble(pages), pages)
        assert all(not item.footnote_markers for item in linked)
        assert all(
            span.role != "footnote"
            for item in linked for span in item.source_segments
        )

    audit_pages = _pages(ROUND1 / "audit-manual-p001-p003" / "raw")
    audit = link_requirement_footnotes(assembler.assemble(audit_pages), audit_pages)
    assert any(item.footnote_markers for item in audit)
    assert all(not item.footnote_link_issues for item in audit)
    for requirement in audit:
        linked_markers = {
            item.marker for item in requirement.footnote_link_candidates
        }
        assert set(requirement.footnote_markers) <= linked_markers
