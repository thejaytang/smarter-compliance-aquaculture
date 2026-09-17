from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from enum import Enum
from statistics import median
import re
from typing import Iterable, Literal, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field

from ...types import NativeObject, NativePage
from .native_assembler import (
    NativeRequirement,
    NativeRequirementAssembler,
    TemplateFamily,
)


MINIMUM_SUPPORT_ROWS = 3
MINIMUM_SUPPORT_PAGES = 2
_CANDIDATE_REQUIREMENT_ID_RE = re.compile(
    r"^\s*(\d+(?:\.\d+){2,})(?=\s|$)"
)


@dataclass(frozen=True)
class _NormativeIdSignature:
    font_names: frozenset[str]
    x0_ratio: float
    x0_mad: float
    height_ratio: float
    height_mad: float
    normative_x0_ratio: float


class RequirementProfileModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FamilyProfileStatus(str, Enum):
    ACCEPTED = "accepted"
    REVIEW = "review"


class RoleXBand(RequirementProfileModel):
    """Robust horizontal geometry for one semantic role.

    Coordinates are ratios of page width so the learned band can be reused on
    selected pages rendered at a different resolution.  No extracted text is
    retained in the profile.
    """

    role: str
    sample_count: int = Field(ge=1)
    x0_ratio: float = Field(ge=0, le=1)
    x1_ratio: float = Field(ge=0, le=1)
    observed_x0_min_ratio: float = Field(ge=0, le=1)
    observed_x1_max_ratio: float = Field(ge=0, le=1)
    dispersion: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)


class RequirementFamilyProfile(RequirementProfileModel):
    family: TemplateFamily
    support_pages: int = Field(ge=0)
    support_rows: int = Field(ge=0)
    detected_page_indices: list[int] = Field(default_factory=list)
    support_page_indices: list[int] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    status: FamilyProfileStatus
    review_reasons: list[str] = Field(default_factory=list)
    role_x_bands: dict[str, RoleXBand] = Field(default_factory=dict)


class RequirementTemplateProfile(RequirementProfileModel):
    """Document-level, text-free Requirement template statistics."""

    version: str = "1.0"
    backend: str = "native-requirement-template-profile"
    page_count: int = Field(ge=0)
    minimum_support_rows: int = Field(default=MINIMUM_SUPPORT_ROWS, ge=MINIMUM_SUPPORT_ROWS)
    minimum_support_pages: int = Field(
        default=MINIMUM_SUPPORT_PAGES, ge=MINIMUM_SUPPORT_PAGES
    )
    families: dict[TemplateFamily, RequirementFamilyProfile]
    page_family: dict[int, TemplateFamily] = Field(default_factory=dict)
    page_family_source: dict[int, Literal["direct", "continuation"]] = Field(
        default_factory=dict
    )
    page_candidate_requirement_ids: dict[int, list[str]] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe payload suitable for a pipeline artifact."""

        return self.model_dump(mode="json")

    def to_json(self, *, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent)

    def family_hints(
        self,
        selected_indices: Iterable[int] | None = None,
        *,
        accepted_only: bool = True,
    ) -> dict[int, TemplateFamily]:
        """Return page-indexed hints accepted by ``NativeRequirementAssembler``.

        The default is fail-closed: a family with insufficient document-level
        support is not returned as an automatic hint.  Callers may request the
        review-only observations explicitly for diagnostics.
        """

        selected = set(selected_indices) if selected_indices is not None else None
        hints: dict[int, TemplateFamily] = {}
        for page_index, family in sorted(self.page_family.items()):
            if selected is not None and page_index not in selected:
                continue
            family_profile = self.families[family]
            if accepted_only and family_profile.status is not FamilyProfileStatus.ACCEPTED:
                continue
            hints[page_index] = family
        return hints

    def role_band(
        self, family: TemplateFamily | str, role: str
    ) -> tuple[float, float] | None:
        """Expose a learned normalized x-band for later selected-page parsing."""

        selected_family = (
            family if isinstance(family, TemplateFamily) else TemplateFamily(family)
        )
        band = self.families[selected_family].role_x_bands.get(role)
        return (band.x0_ratio, band.x1_ratio) if band is not None else None


def learn_requirement_template_profile(
    pages: Sequence[NativePage],
    *,
    assembler: NativeRequirementAssembler | None = None,
    minimum_support_rows: int = MINIMUM_SUPPORT_ROWS,
    minimum_support_pages: int = MINIMUM_SUPPORT_PAGES,
) -> RequirementTemplateProfile:
    """Learn reusable Requirement layout evidence from native PDF geometry.

    This is deliberately a profiling pass, not a document parse.  It uses the
    existing assembler to count structurally recoverable rows and measure their
    semantic x-bands, then discards all extracted text before returning.
    """

    if minimum_support_rows < MINIMUM_SUPPORT_ROWS:
        raise ValueError(
            f"minimum_support_rows cannot be below {MINIMUM_SUPPORT_ROWS}"
        )
    if minimum_support_pages < MINIMUM_SUPPORT_PAGES:
        raise ValueError(
            f"minimum_support_pages cannot be below {MINIMUM_SUPPORT_PAGES}"
        )

    ordered = sorted(pages, key=lambda page: page.page_index)
    page_lookup: dict[int, NativePage] = {}
    for page in ordered:
        if page.page_index in page_lookup:
            raise ValueError(f"duplicate NativePage page_index: {page.page_index}")
        page_lookup[page.page_index] = page

    worker = assembler or NativeRequirementAssembler()
    page_family, page_family_source = _detect_page_families(ordered, worker)

    requirements_by_family: dict[TemplateFamily, list[NativeRequirement]] = {}
    for family in TemplateFamily:
        selected = [
            page_index
            for page_index, selected_family in page_family.items()
            if selected_family is family
        ]
        requirements_by_family[family] = (
            worker.assemble(
                ordered,
                selected_indices=selected,
                family=family,
                include_preceding_context=False,
            )
            if selected
            else []
        )

    families = {
        family: _family_profile(
            family=family,
            requirements=requirements_by_family[family],
            detected_page_indices=[
                page_index
                for page_index, selected_family in page_family.items()
                if selected_family is family
            ],
            page_lookup=page_lookup,
            minimum_support_rows=minimum_support_rows,
            minimum_support_pages=minimum_support_pages,
        )
        for family in TemplateFamily
    }

    return RequirementTemplateProfile(
        page_count=len(ordered),
        minimum_support_rows=minimum_support_rows,
        minimum_support_pages=minimum_support_pages,
        families=families,
        page_family=page_family,
        page_family_source=page_family_source,
        page_candidate_requirement_ids={
            page.page_index: _candidate_requirement_ids(page) for page in ordered
        },
    )


def _detect_page_families(
    pages: Sequence[NativePage],
    assembler: NativeRequirementAssembler,
) -> tuple[
    dict[int, TemplateFamily],
    dict[int, Literal["direct", "continuation"]],
]:
    page_family: dict[int, TemplateFamily] = {}
    source: dict[int, Literal["direct", "continuation"]] = {}
    for page in pages:
        family = assembler.detect_family(page)
        if family is not None:
            page_family[page.page_index] = family
            source[page.page_index] = "direct"

    # Learn the visual style of a true ID from independently visible
    # Indicator/Requirement headers before attempting headerless inheritance.
    # This keeps a left-indented prose reference such as "Indicator 2.6.13"
    # from masquerading as a new table row on the following page.  The signal
    # is document-derived; no source name, page number or Requirement ID is
    # hard-coded.  If native font evidence is unavailable or lacks support,
    # continuation detection falls back to the existing geometry-only gate.
    normative_id_signature = _trusted_normative_id_signature(
        pages,
        page_family=page_family,
        page_family_source=source,
    )

    # A repeated template may omit its header on continuation pages.  Resolve
    # those pages one at a time: the immediately preceding page must already be
    # proven, and the same family must independently recover every left-band ID
    # candidate on the current page.  A proven continuation can support the
    # next page, but there is no unconditional family propagation.
    for position, (prior, current) in enumerate(zip(pages, pages[1:]), start=1):
        if current.page_index != prior.page_index + 1:
            continue
        if current.page_index in page_family:
            continue
        prior_family = page_family.get(prior.page_index)
        if prior_family is None:
            continue

        candidate_ids = _candidate_requirement_ids(
            current,
            anchor_signature=(
                normative_id_signature
                if prior_family is TemplateFamily.ID_NORMATIVE_WITH_CONTEXT
                else None
            ),
        )
        if candidate_ids:
            probe = assembler.assemble([current], family=prior_family)
            recovered_ids = _recovered_requirement_ids(probe, current.page_index)
            if recovered_ids != candidate_ids:
                continue
            page_family[current.page_index] = prior_family
            source[current.page_index] = "continuation"
            continue

        # ID + normative + context pages can carry the final Requirement prose
        # onto a page that has no new ID.  Preserve that special case, but make
        # the assembler prove an actual cross-page source span.  Include only
        # the already validated contiguous run so multi-page continuations are
        # checked incrementally rather than inherited blindly.
        if prior_family is not TemplateFamily.ID_NORMATIVE_WITH_CONTEXT:
            continue
        context = _contiguous_family_context(
            pages,
            end_position=position,
            page_family=page_family,
            family=prior_family,
        )
        probe = assembler.assemble(
            [*context, current],
            family=TemplateFamily.ID_NORMATIVE_WITH_CONTEXT,
        )
        crosses_to_current = any(
            span.page_index == current.page_index
            and span.role == "requirement_continuation"
            for requirement in probe
            for span in requirement.source_segments
        )
        if crosses_to_current:
            page_family[current.page_index] = prior_family
            source[current.page_index] = "continuation"

    return dict(sorted(page_family.items())), dict(sorted(source.items()))


def _recovered_requirement_ids(
    requirements: Sequence[NativeRequirement], page_index: int
) -> list[str]:
    return [
        requirement.requirement_id
        for requirement in requirements
        if any(
            span.role == "requirement_id" and span.page_index == page_index
            for span in requirement.source_segments
        )
    ]


def _contiguous_family_context(
    pages: Sequence[NativePage],
    *,
    end_position: int,
    page_family: Mapping[int, TemplateFamily],
    family: TemplateFamily,
) -> list[NativePage]:
    context: list[NativePage] = []
    cursor = end_position - 1
    expected_index: int | None = None
    while cursor >= 0:
        page = pages[cursor]
        if page_family.get(page.page_index) is not family:
            break
        if expected_index is not None and page.page_index != expected_index - 1:
            break
        context.append(page)
        expected_index = page.page_index
        cursor -= 1
    return list(reversed(context))


def _family_profile(
    *,
    family: TemplateFamily,
    requirements: Sequence[NativeRequirement],
    detected_page_indices: Sequence[int],
    page_lookup: Mapping[int, NativePage],
    minimum_support_rows: int,
    minimum_support_pages: int,
) -> RequirementFamilyProfile:
    support_page_indices = sorted({
        span.page_index
        for requirement in requirements
        for span in requirement.source_segments
        if span.page_index in page_lookup
    })
    support_rows = len(requirements)
    support_pages = len(support_page_indices)
    role_x_bands = _role_x_bands(requirements, page_lookup)
    geometry_confidence = (
        median(band.confidence for band in role_x_bands.values())
        if role_x_bands
        else 0.0
    )

    row_score = min(1.0, support_rows / max(minimum_support_rows * 2, 1))
    page_score = min(1.0, support_pages / max(minimum_support_pages * 2, 1))
    raw_confidence = 0.45 * row_score + 0.35 * page_score + 0.20 * geometry_confidence

    review_reasons: list[str] = []
    if support_rows < minimum_support_rows:
        review_reasons.append("insufficient_support_rows")
    if support_pages < minimum_support_pages:
        review_reasons.append("insufficient_support_pages")
    accepted = not review_reasons
    if accepted:
        confidence = min(0.995, max(0.80, raw_confidence))
        status = FamilyProfileStatus.ACCEPTED
    else:
        confidence = min(0.69, raw_confidence)
        status = FamilyProfileStatus.REVIEW

    return RequirementFamilyProfile(
        family=family,
        support_pages=support_pages,
        support_rows=support_rows,
        detected_page_indices=sorted(set(detected_page_indices)),
        support_page_indices=support_page_indices,
        confidence=round(confidence, 6),
        status=status,
        review_reasons=review_reasons,
        role_x_bands=role_x_bands,
    )


def _candidate_requirement_ids(
    page: NativePage,
    *,
    anchor_signature: _NormativeIdSignature | None = None,
) -> list[str]:
    """Inventory left-margin dotted IDs without retaining surrounding prose."""

    candidates: list[tuple[str, float, float]] = []
    native_objects = page.words if anchor_signature is not None else [*page.words, *page.text_lines]
    for native_object in native_objects:
        match = _CANDIDATE_REQUIREMENT_ID_RE.match(native_object.text)
        if match is None:
            continue
        x0, y0, _x1, _y1 = native_object.bbox_points
        if x0 >= page.width_points * 0.13 or y0 >= page.height_points * 0.90:
            continue
        if anchor_signature is not None and not _matches_normative_id_signature(
            page, native_object, anchor_signature
        ):
            continue
        candidates.append((match.group(1), x0, y0))

    result: list[str] = []
    prior_y: float | None = None
    prior_id: str | None = None
    for requirement_id, _x0, y0 in sorted(
        candidates, key=lambda item: (item[2], item[1])
    ):
        if requirement_id == prior_id and prior_y is not None and abs(y0 - prior_y) < 3:
            continue
        result.append(requirement_id)
        prior_id = requirement_id
        prior_y = y0
    return result


def _trusted_normative_id_signature(
    pages: Sequence[NativePage],
    *,
    page_family: Mapping[int, TemplateFamily],
    page_family_source: Mapping[int, Literal["direct", "continuation"]],
) -> _NormativeIdSignature | None:
    """Learn true left-column ID fonts from explicit two-column headers.

    Only the first dotted ID in each header-delimited formal band contributes
    evidence.  That makes inline cross-references inside the Requirement or
    interpretation prose ineligible training points.  At least two pages must
    agree before font evidence is allowed to constrain a continuation page.
    """

    observations: list[tuple[str, int, float, float, float]] = []
    for page in pages:
        if page_family.get(page.page_index) is not TemplateFamily.ID_NORMATIVE_WITH_CONTEXT:
            continue
        if page_family_source.get(page.page_index) != "direct":
            continue
        lines = sorted(
            page.text_lines,
            key=lambda item: (item.bbox_points[1], item.bbox_points[0]),
        )
        indicators = [
            line for line in lines
            if _profile_clean(line.text).casefold() in {"indicator", "indicator:"}
        ]
        requirements = [
            line for line in lines
            if _profile_clean(line.text).casefold() in {"requirement", "requirement:"}
        ]
        for indicator in indicators:
            header = min(
                (
                    requirement for requirement in requirements
                    if abs(_profile_center_y(requirement) - _profile_center_y(indicator)) <= 8
                    and requirement.bbox_points[0] > indicator.bbox_points[0]
                ),
                key=lambda item: abs(_profile_center_y(item) - _profile_center_y(indicator)),
                default=None,
            )
            if header is None:
                continue
            start_y = max(indicator.bbox_points[3], header.bbox_points[3])
            context_y = min(
                (
                    line.bbox_points[1] for line in lines
                    if line.bbox_points[1] > start_y
                    and _profile_clean(line.text).casefold().startswith(
                        "how do i interpret this requirement"
                    )
                ),
                default=page.height_points * 0.9,
            )
            anchors = [
                word for word in page.words
                if _CANDIDATE_REQUIREMENT_ID_RE.match(_profile_clean(word.text))
                and word.bbox_points[0] < page.width_points * 0.13
                and start_y - 3 <= word.bbox_points[1] < context_y
            ]
            if not anchors:
                continue
            first = min(anchors, key=lambda item: (item.bbox_points[1], item.bbox_points[0]))
            font_name = _normalized_font_name(first.font_name)
            x0, y0, _x1, y1 = first.bbox_points
            observations.append((
                font_name,
                page.page_index,
                _ratio(x0, page.width_points),
                _ratio(y1 - y0, page.height_points),
                _ratio(header.bbox_points[0], page.width_points),
            ))

    pages_by_font: dict[str, set[int]] = defaultdict(set)
    counts: Counter[str] = Counter()
    for font_name, page_index, _x0, _height, _normative_x0 in observations:
        if font_name:
            counts[font_name] += 1
            pages_by_font[font_name].add(page_index)
    trusted = {
        font_name for font_name, count in counts.items()
        if count >= 2 and len(pages_by_font[font_name]) >= 2
    }
    support_pages = {item[1] for item in observations}
    if len(observations) < 2 or len(support_pages) < 2:
        return None
    x0_values = [item[2] for item in observations]
    height_values = [item[3] for item in observations]
    normative_x0_values = [item[4] for item in observations]
    x0_center = median(x0_values)
    height_center = median(height_values)
    return _NormativeIdSignature(
        font_names=frozenset(trusted),
        x0_ratio=x0_center,
        x0_mad=median(abs(value - x0_center) for value in x0_values),
        height_ratio=height_center,
        height_mad=median(abs(value - height_center) for value in height_values),
        normative_x0_ratio=median(normative_x0_values),
    )


def _matches_normative_id_signature(
    page: NativePage,
    candidate: NativeObject,
    signature: _NormativeIdSignature,
) -> bool:
    x0, y0, x1, y1 = candidate.bbox_points
    x0_ratio = _ratio(x0, page.width_points)
    height_ratio = _ratio(y1 - y0, page.height_points)
    x_tolerance = max(0.012, signature.x0_mad * 4)
    height_tolerance = max(0.004, signature.height_mad * 4)
    geometry_matches = (
        abs(x0_ratio - signature.x0_ratio) <= x_tolerance
        and abs(height_ratio - signature.height_ratio) <= height_tolerance
    )
    if not geometry_matches:
        return False

    font_name = _normalized_font_name(candidate.font_name)
    style_matches = bool(font_name and font_name in signature.font_names)
    line_isolated = any(
        _CANDIDATE_REQUIREMENT_ID_RE.fullmatch(_profile_clean(line.text))
        and abs(_profile_center_y(line) - _profile_center_y(candidate))
        <= max(3.0, y1 - y0)
        for line in page.text_lines
    )

    same_row = [
        word for word in page.words
        if word.id != candidate.id
        and word.bbox_points[0] >= x1
        and abs(_profile_center_y(word) - _profile_center_y(candidate))
        <= max(3.0, (y1 - y0) * 0.65)
    ]
    first_right = min(same_row, key=lambda item: item.bbox_points[0], default=None)
    row_pair_matches = False
    if first_right is not None:
        right_x0 = _ratio(first_right.bbox_points[0], page.width_points)
        gutter = _ratio(first_right.bbox_points[0] - x1, page.width_points)
        row_pair_matches = (
            abs(right_x0 - signature.normative_x0_ratio) <= 0.025
            and gutter >= 0.015
        )

    # Two independent sources of evidence are required.  A valid row can be
    # accepted without font metadata when its learned geometry and right-column
    # pair agree; otherwise matching style must be backed by an isolated ID line.
    return row_pair_matches or (style_matches and line_isolated)


def _normalized_font_name(font_name: str | None) -> str:
    if not font_name:
        return ""
    normalized = font_name.strip().lstrip("/")
    if "+" in normalized:
        prefix, suffix = normalized.split("+", 1)
        if len(prefix) == 6 and prefix.isalpha():
            normalized = suffix
    return normalized.casefold()


def _profile_clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _profile_center_y(item: NativeObject) -> float:
    bbox = item.bbox_points
    return (bbox[1] + bbox[3]) / 2


def _role_x_bands(
    requirements: Sequence[NativeRequirement],
    page_lookup: Mapping[int, NativePage],
) -> dict[str, RoleXBand]:
    by_role: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for requirement in requirements:
        for span in requirement.source_segments:
            page = page_lookup.get(span.page_index)
            if page is None or page.width_points <= 0:
                continue
            x0, _y0, x1, _y1 = span.bbox
            if x1 <= x0:
                continue
            by_role[span.role].append((
                _ratio(x0, page.width_points),
                _ratio(x1, page.width_points),
            ))

    return {
        role: _role_x_band(role, observations)
        for role, observations in sorted(by_role.items())
        if observations
    }


def _role_x_band(role: str, observations: Sequence[tuple[float, float]]) -> RoleXBand:
    x0_values = [item[0] for item in observations]
    x1_values = [item[1] for item in observations]
    center_x0 = median(x0_values)
    center_x1 = median(x1_values)
    deviations = [
        abs(x0 - center_x0) + abs(x1 - center_x1)
        for x0, x1 in observations
    ]
    dispersion = min(1.0, median(deviations))
    sample_score = min(1.0, len(observations) / 3)
    consistency = max(0.0, 1.0 - min(1.0, dispersion / 0.12))
    confidence = min(0.995, 0.35 * sample_score + 0.65 * consistency)
    return RoleXBand(
        role=role,
        sample_count=len(observations),
        x0_ratio=round(center_x0, 6),
        x1_ratio=round(center_x1, 6),
        observed_x0_min_ratio=round(min(x0_values), 6),
        observed_x1_max_ratio=round(max(x1_values), 6),
        dispersion=round(dispersion, 6),
        confidence=round(confidence, 6),
    )


def _ratio(value: float, width: float) -> float:
    return max(0.0, min(1.0, value / width))
