from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

import pytest

from pdf_extraction.domains.requirements import (
    FamilyProfileStatus,
    NativeRequirementAssembler,
    TemplateFamily,
    learn_requirement_template_profile,
)
from pdf_extraction.types import NativeObject, NativePage
from tests.support.paths import PROJECT_ROOT


ROOT = PROJECT_ROOT
ROUND1 = ROOT / "outputs" / "runs" / "goal04-round1"
ROUND2 = ROOT / "outputs" / "runs" / "goal04-round2"
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


def _sample_pages(sample: str) -> list[NativePage]:
    return _pages_from(ROUND1 / sample / "raw")


def _pages_from(raw_dir: Path) -> list[NativePage]:
    return [
        _native_page(path)
        for path in sorted(raw_dir.glob("native-page-*.json"))
    ]


def _all_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {
            key for item in value.values() for key in _all_keys(item)
        }
    if isinstance(value, list):
        return {key for item in value for key in _all_keys(item)}
    return set()


@pytest.mark.parametrize(
    ("sample", "family", "support_rows", "support_pages"),
    [
        ("farm-standard-p028-p029", TemplateFamily.SINGLE_COLUMN_INDICATORS, 6, 2),
        ("audit-manual-p001-p003", TemplateFamily.AUDIT_MATRIX, 12, 3),
        (
            "interpretation-manual-p019-p021",
            TemplateFamily.ID_NORMATIVE_WITH_CONTEXT,
            3,
            3,
        ),
    ],
)
def test_full_document_profile_accepts_supported_families(
    sample: str,
    family: TemplateFamily,
    support_rows: int,
    support_pages: int,
) -> None:
    pages = _sample_pages(sample)
    profile = learn_requirement_template_profile(pages)
    learned = profile.families[family]

    assert profile.page_count == len(pages)
    assert learned.support_rows == support_rows
    assert learned.support_pages == support_pages
    assert learned.status is FamilyProfileStatus.ACCEPTED
    assert learned.confidence >= 0.80
    assert profile.family_hints() == {
        page.page_index: family for page in pages
    }
    assert learned.role_x_bands["requirement_id"].sample_count == support_rows


def test_one_page_family_is_review_only_and_not_an_automatic_hint() -> None:
    pages = _sample_pages("salmon-cod-standard-p018")
    profile = learn_requirement_template_profile(pages)
    learned = profile.families[TemplateFamily.LEGACY_INDICATOR_VALUE]

    assert learned.support_rows == 4
    assert learned.support_pages == 1
    assert learned.status is FamilyProfileStatus.REVIEW
    assert learned.confidence <= 0.69
    assert learned.review_reasons == ["insufficient_support_pages"]
    assert profile.family_hints() == {}
    assert profile.family_hints(accepted_only=False) == {
        pages[0].page_index: TemplateFamily.LEGACY_INDICATOR_VALUE
    }


def test_headerless_single_column_page_is_verified_as_continuation() -> None:
    pages = _pages_from(
        ROUND2 / "farm-standard-p064-p065-holdout" / "raw"
    )
    profile = learn_requirement_template_profile(pages)
    family = TemplateFamily.SINGLE_COLUMN_INDICATORS

    assert profile.page_family[pages[0].page_index] is family
    assert profile.page_family[pages[1].page_index] is family
    assert profile.page_family_source[pages[0].page_index] == "direct"
    assert profile.page_family_source[pages[1].page_index] == "continuation"
    assert profile.families[family].status is FamilyProfileStatus.ACCEPTED

    hints = profile.family_hints()
    recovered = NativeRequirementAssembler().assemble(pages, family=hints)
    expected_ids = [
        requirement_id
        for page in pages
        for requirement_id in profile.page_candidate_requirement_ids[page.page_index]
    ]
    assert [item.requirement_id for item in recovered] == expected_ids


def test_headerless_page_is_not_inherited_when_probe_misses_an_id() -> None:
    pages = _pages_from(
        ROUND2 / "farm-standard-p064-p065-holdout" / "raw"
    )
    pages = deepcopy(pages)
    continuation = pages[1]
    continuation.words.append(NativeObject(
        id="unassembled-candidate",
        text="9.9.9",
        bbox_points=(54.0, 720.0, 84.0, 735.0),
    ))

    profile = learn_requirement_template_profile(pages)

    assert continuation.page_index not in profile.page_family
    assert profile.page_candidate_requirement_ids[continuation.page_index][-1] == "9.9.9"


def test_context_cross_reference_is_not_promoted_as_headerless_requirement() -> None:
    pages = _pages_from(
        ROUND4 / "interpretation-manual-p103-p106-holdout" / "raw"
    )
    profile = learn_requirement_template_profile(pages)
    family = TemplateFamily.ID_NORMATIVE_WITH_CONTEXT

    # PDF page 106 starts with prose that mentions Indicator 2.6.13.  It is a
    # regular-font cross-reference, not a repeated bold ID in the table's left
    # column, so it must not make this page a Requirement-template continuation.
    reference_page = pages[-1]
    assert profile.page_candidate_requirement_ids[reference_page.page_index] == [
        "2.6.13"
    ]
    assert reference_page.page_index not in profile.page_family

    hints = profile.family_hints(accepted_only=False)
    recovered = NativeRequirementAssembler().assemble(pages, family=hints)
    assert [item.requirement_id for item in recovered] == [
        "2.6.10", "2.6.11", "2.6.12", "2.6.13"
    ]
    assert len({item.requirement_id for item in recovered}) == len(recovered)
    assert {item.family for item in recovered} == {family}


def test_headerless_normative_row_can_be_proven_without_font_metadata() -> None:
    pages = deepcopy(_pages_from(
        ROUND4 / "interpretation-manual-p103-p106-holdout" / "raw"
    ))
    continuation = pages[-1]
    continuation.words = [
        replace(
            word,
            bbox_points=(53.904, 130.1, 92.3034, 147.2),
            font_name=None,
            font_key=None,
        )
        if word.id == "native_p0105_w000053"
        else replace(
            word,
            bbox_points=(117.74, 130.1, 135.21, 147.2),
        )
        if word.id == "native_p0105_w000054"
        else word
        for word in continuation.words
    ]

    profile = learn_requirement_template_profile(pages)

    assert profile.page_family[continuation.page_index] is (
        TemplateFamily.ID_NORMATIVE_WITH_CONTEXT
    )
    assert profile.page_family_source[continuation.page_index] == "continuation"


def test_profile_has_all_families_and_serializes_without_extracted_text() -> None:
    profile = learn_requirement_template_profile(
        _sample_pages("farm-standard-p028-p029")
    )
    payload = profile.to_dict()
    serialized = profile.to_json()

    assert set(payload["families"]) == {family.value for family in TemplateFamily}
    assert json.loads(serialized) == payload
    assert {"source_text", "native_object_ids"}.isdisjoint(_all_keys(payload))
    assert profile.role_band(
        TemplateFamily.SINGLE_COLUMN_INDICATORS, "normative_text"
    ) is not None


def test_profile_keeps_page_level_candidate_id_inventory_without_prose() -> None:
    pages = _sample_pages("farm-standard-p028-p029")
    profile = learn_requirement_template_profile(pages)

    assert profile.page_candidate_requirement_ids == {
        pages[0].page_index: ["1.1.1", "1.1.2"],
        pages[1].page_index: ["1.2.1", "1.2.2", "1.2.3", "1.2.4"],
    }
    payload = profile.to_dict()["page_candidate_requirement_ids"]
    assert set(payload) == {str(page.page_index) for page in pages}


def test_selected_page_hints_are_directly_usable_by_assembler() -> None:
    pages = _sample_pages("farm-standard-p028-p029")
    profile = learn_requirement_template_profile(pages)
    selected = {pages[-1].page_index}
    hints = profile.family_hints(selected)

    requirements = NativeRequirementAssembler().assemble(
        pages,
        selected_indices=selected,
        family=hints,
    )
    assert [item.requirement_id for item in requirements] == [
        "1.2.1", "1.2.2", "1.2.3", "1.2.4"
    ]


def test_support_thresholds_cannot_be_weakened() -> None:
    pages = _sample_pages("farm-standard-p028-p029")
    with pytest.raises(ValueError, match="minimum_support_rows"):
        learn_requirement_template_profile(pages, minimum_support_rows=2)
    with pytest.raises(ValueError, match="minimum_support_pages"):
        learn_requirement_template_profile(pages, minimum_support_pages=1)


def test_duplicate_page_indices_fail_closed() -> None:
    page = _sample_pages("salmon-cod-standard-p018")[0]
    with pytest.raises(ValueError, match="duplicate NativePage page_index"):
        learn_requirement_template_profile([page, page])
