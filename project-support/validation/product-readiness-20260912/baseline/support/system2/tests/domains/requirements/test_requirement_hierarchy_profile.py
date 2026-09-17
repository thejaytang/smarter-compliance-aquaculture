from __future__ import annotations

import json
from pathlib import Path

from pdf_extraction.domains.requirements import (
    NativeRequirementAssembler,
    TemplateFamily,
    bind_requirement_hierarchy,
    canonicalize_native_requirement,
    learn_requirement_hierarchy_profile,
)
from pdf_extraction.types import NativeObject, NativePage
from tests.support.paths import PROJECT_ROOT


ROOT = PROJECT_ROOT
ROUND1 = ROOT / "outputs" / "runs" / "goal04-round1"
ROUND3 = ROOT / "outputs" / "runs" / "goal04-round3"
ROUND4 = ROOT / "outputs" / "runs" / "goal04-round4"


def _native_page(path: Path) -> NativePage:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return NativePage(
        page_index=raw["page_index"],
        width_points=raw["width_points"],
        height_points=raw["height_points"],
        words=[NativeObject(**item) for item in raw["words"]],
        text_lines=[NativeObject(**item) for item in raw["text_lines"]],
    )


def _pages(raw_dir: Path) -> list[NativePage]:
    return [
        _native_page(path)
        for path in sorted(raw_dir.glob("native-page-*.json"))
    ]


def test_split_same_line_and_multiline_headings_are_source_reconstructed() -> None:
    farm = learn_requirement_hierarchy_profile(_pages(
        ROUND1 / "farm-standard-p028-p029" / "raw"
    ))
    salmon = learn_requirement_hierarchy_profile(_pages(
        ROUND1 / "salmon-cod-standard-p018" / "raw"
    ))

    assert [heading.text for heading in farm.headings] == [
        "Criterion 1.1 - Legal Compliance",
        "Criterion 1.2 - Management Systems",
    ]
    assert [heading.text for heading in salmon.headings] == [
        "PRINCIPLE 1: COMPLY WITH ALL APPLICABLE NATIONAL LAWS AND LOCAL REGULATIONS",
        "Criterion 1.1 Compliance with all applicable local and national legal requirements and regulations",
    ]
    assert all(heading.native_object_refs for heading in [*farm.headings, *salmon.headings])


def test_visual_superscript_is_not_promoted_into_heading_text() -> None:
    profile = learn_requirement_hierarchy_profile(_pages(
        ROUND3 / "salmon-cod-standard-p027-p028-holdout" / "raw"
    ))

    assert [heading.text for heading in profile.headings] == [
        "Criterion 2.5 Interaction with wildlife, including predators"
    ]
    # The superscript remains traceable through its native object reference and
    # the evidence bbox, even though it is not semantic heading text.
    heading = profile.headings[0]
    assert len(heading.native_object_refs) == 8
    assert heading.bbox.x1 > 480


def test_bold_inline_appendix_cross_references_are_not_headings() -> None:
    profile = learn_requirement_hierarchy_profile(_pages(
        ROUND4 / "interpretation-manual-p103-p106-active" / "raw"
    ))

    assert profile.headings == []


def test_legacy_requirement_is_bound_to_source_backed_principle_and_criterion() -> None:
    pages = _pages(ROUND1 / "salmon-cod-standard-p018" / "raw")
    profile = learn_requirement_hierarchy_profile(pages)
    native = NativeRequirementAssembler().assemble(
        pages,
        family=TemplateFamily.LEGACY_INDICATOR_VALUE,
    )
    canonical = [canonicalize_native_requirement(item) for item in native]

    bound = bind_requirement_hierarchy(canonical, profile)

    assert len(bound) == 4
    expected_path = ["Principle 1", "Criterion 1.1"]
    assert all(requirement.criterion_path == expected_path for requirement in bound)
    for requirement in bound:
        regions = [
            region for region in requirement.source_segments
            if region.role == "criterion_heading"
        ]
        assert [region.source_text for region in regions] == [
            "PRINCIPLE 1: COMPLY WITH ALL APPLICABLE NATIONAL LAWS AND LOCAL REGULATIONS",
            "Criterion 1.1 Compliance with all applicable local and national legal requirements and regulations",
        ]
        assert all(region.native_object_refs for region in regions)
        assert "hierarchy_profile:source_bound" in requirement.validation_flags


def test_audit_source_order_switches_paths_within_the_same_pages() -> None:
    pages = _pages(ROUND4 / "audit-manual-p011-p012-holdout" / "raw")
    profile = learn_requirement_hierarchy_profile(pages)
    native = NativeRequirementAssembler().assemble(
        pages,
        family=TemplateFamily.AUDIT_MATRIX,
    )
    canonical = [canonicalize_native_requirement(item) for item in native]

    bound = bind_requirement_hierarchy(canonical, profile)
    by_id = {item.requirement_id: item for item in bound}

    assert by_id["4.1.1"].criterion_path == ["Principle 4", "Criterion 4.1"]
    assert by_id["4.2.2"].criterion_path[-1] == "Criterion 4.2"
    assert by_id["4.3.3"].criterion_path[-1] == "Criterion 4.3"


def test_norwegian_labels_use_the_same_source_backed_binding_contract() -> None:
    page = NativePage(
        page_index=0,
        width_points=595,
        height_points=842,
        words=[
            NativeObject(
                id="no-principle",
                text="Prinsipp 2: Miljo",
                bbox_points=(50, 60, 220, 78),
                font_name="Example-Bold",
            ),
            NativeObject(
                id="no-criterion",
                text="Kriterium 2.3 Utslipp",
                bbox_points=(50, 100, 230, 116),
                font_name="Example-Bold",
            ),
        ],
    )

    profile = learn_requirement_hierarchy_profile([page])

    assert [(item.kind.value, item.number, item.text) for item in profile.headings] == [
        ("principle", "2", "Prinsipp 2: Miljo"),
        ("criterion", "2.3", "Kriterium 2.3 Utslipp"),
    ]
