from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from statistics import median
from typing import Iterable, Sequence

from pydantic import BaseModel, ConfigDict, Field

from ...models import (
    BoundingBox,
    Requirement,
    RequirementSourceRegion,
    RequirementStatus,
    ResolutionStatus,
)
from ...types import NativeObject, NativePage


class HierarchyKind(str, Enum):
    """Source-visible hierarchy labels supported by the native profiler."""

    PART = "part"
    CHAPTER = "chapter"
    PRINCIPLE = "principle"
    SECTION = "section"
    CRITERION = "criterion"
    APPENDIX = "appendix"


_LABELS: dict[str, HierarchyKind] = {
    "part": HierarchyKind.PART,
    "del": HierarchyKind.PART,
    "chapter": HierarchyKind.CHAPTER,
    "kapittel": HierarchyKind.CHAPTER,
    "principle": HierarchyKind.PRINCIPLE,
    "prinsipp": HierarchyKind.PRINCIPLE,
    "section": HierarchyKind.SECTION,
    "seksjon": HierarchyKind.SECTION,
    "avsnitt": HierarchyKind.SECTION,
    "criterion": HierarchyKind.CRITERION,
    "kriterium": HierarchyKind.CRITERION,
    "appendix": HierarchyKind.APPENDIX,
    "annex": HierarchyKind.APPENDIX,
    "vedlegg": HierarchyKind.APPENDIX,
}
_LABEL_PATTERN = "|".join(
    sorted((re.escape(value) for value in _LABELS), key=len, reverse=True)
)
_HEADING_RE = re.compile(
    rf"^(?P<label>{_LABEL_PATTERN})\s+"
    r"(?P<number>(?:\d+(?:\.\d+)*|[IVXLCDM]+(?:-\d+)?|[A-Z]))"
    r"(?=$|\s|[:\-\u2013\u2014])",
    re.IGNORECASE,
)
_ANY_HEADING_RE = re.compile(rf"^(?:{_LABEL_PATTERN})\b", re.IGNORECASE)
_NUMBER_PREFIX_RE = re.compile(r"^\d+(?:\.\d+)*$")
_SPACE_RE = re.compile(r"\s+")
_BODY_BOUNDARY_RE = re.compile(
    r"^(?:rationale|intent|applicability|"
    r"how\s+do\s+i\s+interpret|required\s+(?:client|cab)\s+actions|"
    r"note|instruction)\b",
    re.IGNORECASE,
)
_MODAL_SENTENCE_RE = re.compile(
    r"\b(?:shall|must|required\s+to|may\s+not|is\s+intended\s+to)\b",
    re.IGNORECASE,
)
_STRUCTURAL_FONT_RE = re.compile(
    r"(?:bold|semibold|demibold|extrabold|italic)", re.IGNORECASE
)
_RANK = {
    HierarchyKind.PART: 10,
    HierarchyKind.CHAPTER: 20,
    HierarchyKind.PRINCIPLE: 20,
    HierarchyKind.APPENDIX: 20,
    HierarchyKind.SECTION: 30,
    HierarchyKind.CRITERION: 40,
}


class RequirementHierarchyModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HierarchyHeading(RequirementHierarchyModel):
    heading_id: str
    kind: HierarchyKind
    number: str
    text: str = Field(min_length=1)
    page_index: int = Field(ge=0)
    page_number: int = Field(ge=1)
    bbox: BoundingBox
    native_object_refs: list[str] = Field(min_length=1)
    font_names: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    path: list[str] = Field(default_factory=list)


class RequirementHierarchyProfile(RequirementHierarchyModel):
    """Document-level source heading evidence used for Requirement binding."""

    version: str = "1.0"
    backend: str = "native-requirement-hierarchy-profile"
    page_count: int = Field(ge=0)
    headings: list[HierarchyHeading] = Field(default_factory=list)
    page_heading_ids: dict[int, list[str]] = Field(default_factory=dict)
    review_reasons: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return self.model_dump(mode="json")

    def to_json(self, *, indent: int | None = None) -> str:
        return self.model_dump_json(indent=indent)


@dataclass(frozen=True)
class _Row:
    text: str
    bbox: tuple[float, float, float, float]
    native_object_ids: tuple[str, ...]
    font_names: tuple[str, ...]

    @property
    def x0(self) -> float:
        return self.bbox[0]

    @property
    def y0(self) -> float:
        return self.bbox[1]

    @property
    def y1(self) -> float:
        return self.bbox[3]

    @property
    def height(self) -> float:
        return self.y1 - self.y0


@dataclass(frozen=True)
class _HeadingCandidate:
    kind: HierarchyKind
    number: str
    text: str
    page_index: int
    bbox: tuple[float, float, float, float]
    native_object_ids: tuple[str, ...]
    font_names: tuple[str, ...]
    confidence: float


def learn_requirement_hierarchy_profile(
    pages: Sequence[NativePage],
) -> RequirementHierarchyProfile:
    """Learn explicit English/Norwegian hierarchy headings from all native pages.

    The profiler never manufactures a heading from a Requirement ID.  A
    candidate must start with a supported source label and carry independent
    structural evidence from position plus font/line geometry.
    """

    ordered = sorted(pages, key=lambda page: page.page_index)
    seen_pages: set[int] = set()
    candidates: list[_HeadingCandidate] = []
    review_reasons: list[str] = []
    for page in ordered:
        if page.page_index in seen_pages:
            raise ValueError(f"duplicate NativePage page_index: {page.page_index}")
        seen_pages.add(page.page_index)
        rows = _rows(page)
        page_candidates = _page_heading_candidates(page, rows)
        if _is_contents_page(rows) and len(page_candidates) >= 3:
            # Contents entries are an index, not the source-order hierarchy
            # governing Requirement rows later in the document.
            review_reasons.append(f"contents_headings_excluded:p{page.page_index + 1}")
            continue
        candidates.extend(page_candidates)

    candidates.sort(key=lambda item: (item.page_index, item.bbox[1], item.bbox[0]))
    candidates = _deduplicate_candidates(candidates)
    headings = _headings_with_paths(candidates)
    page_heading_ids: dict[int, list[str]] = {}
    for heading in headings:
        page_heading_ids.setdefault(heading.page_index, []).append(heading.heading_id)
    return RequirementHierarchyProfile(
        page_count=len(ordered),
        headings=headings,
        page_heading_ids=page_heading_ids,
        review_reasons=review_reasons,
    )


def bind_requirement_hierarchy(
    requirements: Iterable[Requirement],
    profile: RequirementHierarchyProfile,
) -> list[Requirement]:
    """Bind each Requirement to the nearest source-visible compatible path.

    Compatibility is checked against explicit heading numbers.  The ID is
    used only to reject unrelated headings; it is never used to generate a
    missing title.  Source heading regions are embedded in each bound
    Requirement so ``criterion_path`` remains auditable without the profile.
    """

    result: list[Requirement] = []
    for requirement in requirements:
        updated = requirement.model_copy(deep=True)
        anchor = _requirement_anchor(updated)
        if anchor is None:
            _mark_unresolved(updated, "hierarchy_requirement_anchor_missing")
            result.append(updated)
            continue
        requirement_components = _numeric_components(updated.requirement_id)
        if requirement_components is None:
            _mark_unresolved(updated, "hierarchy_requirement_id_not_numeric")
            result.append(updated)
            continue

        eligible = [
            heading
            for heading in profile.headings
            if _precedes(heading, anchor)
        ]
        stack = _active_heading_stack(eligible)
        compatible = [
            heading
            for heading in stack
            if _heading_matches_requirement(heading, requirement_components)
        ]
        # A rank reset can remove a useful parent when the intervening explicit
        # heading is unrelated to this Requirement.  Recover only from prior,
        # number-compatible source headings and prefer that chain when it adds
        # source-backed ancestry to the same leaf.
        recovered_chain = _nearest_compatible_chain(
            eligible,
            requirement_components,
        )
        if len(recovered_chain) > len(compatible):
            compatible = recovered_chain
        if not compatible:
            if profile.headings:
                _mark_unresolved(updated, "criterion_hierarchy_unresolved")
            else:
                _append_unique(
                    updated.validation_flags,
                    "hierarchy_profile:no_explicit_headings",
                )
            result.append(updated)
            continue

        # ``criterion_path`` is a stable semantic path.  Keep the complete,
        # source-visible heading text in ``criterion_heading`` regions below
        # so titles, footnote markers and translations remain auditable
        # without making hierarchy equality depend on presentation wording.
        updated.criterion_path = [
            f"{heading.kind.value.title()} {heading.number}"
            for heading in compatible
        ]
        updated.source_segments = [
            region
            for region in updated.source_segments
            if region.role != "criterion_heading"
        ]
        updated.source_segments.extend(
            _heading_regions(updated.requirement_id, compatible)
        )
        _append_unique(updated.validation_flags, "hierarchy_profile:source_bound")
        _append_unique(
            updated.validation_flags,
            f"hierarchy_profile_version:{profile.version}",
        )
        result.append(updated)
    return result


def _page_heading_candidates(
    page: NativePage,
    rows: Sequence[_Row],
) -> list[_HeadingCandidate]:
    heights = [row.height for row in rows if row.height > 0 and row.text]
    body_height = median(heights) if heights else 0.0
    candidates: list[_HeadingCandidate] = []
    index = 0
    while index < len(rows):
        row = rows[index]
        match = _HEADING_RE.match(row.text)
        if match is None or not _is_structural_row(page, row, body_height):
            index += 1
            continue
        kind = _LABELS[match.group("label").casefold()]
        number = match.group("number").rstrip(".")
        combined_rows = [row]
        while len(combined_rows) < 3 and index + len(combined_rows) < len(rows):
            next_row = rows[index + len(combined_rows)]
            if not _is_heading_continuation(
                page,
                combined_rows[-1],
                next_row,
                heading_fonts=set(row.font_names),
            ):
                break
            combined_rows.append(next_row)
        text = _clean(" ".join(item.text for item in combined_rows))
        bbox = _union_boxes(item.bbox for item in combined_rows)
        refs = tuple(
            ref for item in combined_rows for ref in item.native_object_ids
        )
        fonts = tuple(dict.fromkeys(
            font for item in combined_rows for font in item.font_names if font
        ))
        confidence = 0.99 if len(combined_rows) == 1 else 0.96
        candidates.append(_HeadingCandidate(
            kind=kind,
            number=number,
            text=text,
            page_index=page.page_index,
            bbox=bbox,
            native_object_ids=refs,
            font_names=fonts,
            confidence=confidence,
        ))
        index += len(combined_rows)
    return candidates


def _rows(page: NativePage) -> list[_Row]:
    # Word geometry preserves superscript footnote markers that a native
    # text-line object may already have flattened into the heading string.
    source = page.words or page.text_lines
    units = [item for item in source if _clean(item.text) and _valid_bbox(item)]
    units.sort(key=lambda item: (item.bbox_points[1], item.bbox_points[0]))
    if not units:
        return []
    heights = [item.bbox_points[3] - item.bbox_points[1] for item in units]
    typical_height = median(height for height in heights if height > 0)
    tolerance = max(0.8, min(2.0, typical_height * 0.10))
    groups: list[list[NativeObject]] = []
    anchors: list[float] = []
    for unit in units:
        y0 = unit.bbox_points[1]
        if groups and abs(y0 - anchors[-1]) <= tolerance:
            groups[-1].append(unit)
            anchors[-1] = median(item.bbox_points[1] for item in groups[-1])
        else:
            groups.append([unit])
            anchors.append(y0)
    result: list[_Row] = []
    for group in groups:
        ordered = sorted(group, key=lambda item: item.bbox_points[0])
        result.append(_Row(
            text=_join_inline(item.text for item in _semantic_row_units(ordered)),
            bbox=_union_boxes(item.bbox_points for item in ordered),
            native_object_ids=tuple(item.id for item in ordered),
            font_names=tuple(dict.fromkeys(
                _normalized_font_name(item.font_name)
                for item in ordered
                if _normalized_font_name(item.font_name)
            )),
        ))
    return result


def _semantic_row_units(values: Sequence[NativeObject]) -> list[NativeObject]:
    """Exclude a visually superscripted naked footnote from heading text.

    The native object remains in ``native_object_ids`` and the union bbox, so
    this normalization cannot erase its source evidence.  Bracketed markers
    are ordinary text and remain part of the heading.
    """

    result = list(values)
    if len(result) < 2 or not re.fullmatch(r"\d{1,3}", _clean(result[-1].text)):
        return result
    heights = [item.bbox_points[3] - item.bbox_points[1] for item in result[:-1]]
    typical_height = median(height for height in heights if height > 0)
    final_height = result[-1].bbox_points[3] - result[-1].bbox_points[1]
    baseline_y0 = median(item.bbox_points[1] for item in result[:-1])
    if (
        typical_height > 0
        and final_height <= typical_height * 0.75
        and result[-1].bbox_points[1] > baseline_y0 + 0.35
    ):
        return result[:-1]
    return result


def _is_structural_row(page: NativePage, row: _Row, body_height: float) -> bool:
    if page.width_points <= 0 or page.height_points <= 0:
        return False
    if row.x0 > page.width_points * 0.35:
        return False
    if row.y0 < page.height_points * 0.025 or row.y1 > page.height_points * 0.96:
        return False
    if _MODAL_SENTENCE_RE.search(row.text):
        return False
    font_signal = any(_STRUCTURAL_FONT_RE.search(font) for font in row.font_names)
    height_signal = body_height > 0 and row.height >= body_height * 1.18
    return font_signal or height_signal


def _is_heading_continuation(
    page: NativePage,
    prior: _Row,
    candidate: _Row,
    *,
    heading_fonts: set[str],
) -> bool:
    text = _clean(candidate.text)
    if not text or _ANY_HEADING_RE.match(text) or _BODY_BOUNDARY_RE.match(text):
        return False
    if re.match(r"^\d+(?:\.\d+)*\b", text):
        return False
    if _MODAL_SENTENCE_RE.search(text):
        return False
    if prior.text.rstrip().endswith((".", "?", "!", ":")):
        return False
    gap = candidate.y0 - prior.y1
    if gap < -1.5 or gap > max(5.0, prior.height * 1.25):
        return False
    if candidate.x0 > page.width_points * 0.55:
        return False
    if heading_fonts and not heading_fonts.intersection(candidate.font_names):
        return False
    return True


def _is_contents_page(rows: Sequence[_Row]) -> bool:
    return any(
        _clean(row.text).casefold() in {
            "contents",
            "table of contents",
            "innhold",
            "innholdsfortegnelse",
        }
        for row in rows
    )


def _deduplicate_candidates(
    values: Sequence[_HeadingCandidate],
) -> list[_HeadingCandidate]:
    result: list[_HeadingCandidate] = []
    seen: set[tuple[int, HierarchyKind, str, str]] = set()
    for value in values:
        key = (
            value.page_index,
            value.kind,
            value.number.casefold(),
            value.text.casefold(),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _headings_with_paths(
    candidates: Sequence[_HeadingCandidate],
) -> list[HierarchyHeading]:
    result: list[HierarchyHeading] = []
    stack: list[HierarchyHeading] = []
    for index, candidate in enumerate(candidates, start=1):
        rank = _RANK[candidate.kind]
        while stack and _RANK[stack[-1].kind] >= rank:
            stack.pop()
        heading_id = f"hierarchy-p{candidate.page_index + 1:04d}-{candidate.kind.value}-{index:04d}"
        path = [item.text for item in stack] + [candidate.text]
        heading = HierarchyHeading(
            heading_id=heading_id,
            kind=candidate.kind,
            number=candidate.number,
            text=candidate.text,
            page_index=candidate.page_index,
            page_number=candidate.page_index + 1,
            bbox=BoundingBox(
                x0=candidate.bbox[0],
                y0=candidate.bbox[1],
                x1=candidate.bbox[2],
                y1=candidate.bbox[3],
            ),
            native_object_refs=list(candidate.native_object_ids),
            font_names=list(candidate.font_names),
            confidence=candidate.confidence,
            path=path,
        )
        result.append(heading)
        stack.append(heading)
    return result


def _requirement_anchor(
    requirement: Requirement,
) -> tuple[int, float] | None:
    id_regions = [
        region for region in requirement.source_segments
        if region.role == "requirement_id"
    ]
    regions = id_regions or requirement.source_segments
    if not regions:
        return None
    first = min(regions, key=lambda region: (region.page_index, region.bbox.y0))
    return first.page_index, first.bbox.y0


def _precedes(
    heading: HierarchyHeading,
    anchor: tuple[int, float],
) -> bool:
    page_index, y0 = anchor
    return heading.page_index < page_index or (
        heading.page_index == page_index and heading.bbox.y0 <= y0
    )


def _active_heading_stack(
    headings: Sequence[HierarchyHeading],
) -> list[HierarchyHeading]:
    stack: list[HierarchyHeading] = []
    for heading in headings:
        rank = _RANK[heading.kind]
        while stack and _RANK[stack[-1].kind] >= rank:
            stack.pop()
        stack.append(heading)
    return stack


def _nearest_compatible_chain(
    headings: Sequence[HierarchyHeading],
    requirement_components: tuple[int, ...],
) -> list[HierarchyHeading]:
    compatible = [
        heading for heading in headings
        if _heading_matches_requirement(heading, requirement_components)
    ]
    if not compatible:
        return []
    leaf = max(
        compatible,
        key=lambda heading: (
            len(_numeric_components(heading.number) or ()),
            heading.page_index,
            heading.bbox.y0,
        ),
    )
    prior = [
        heading for heading in compatible
        if _precedes(heading, (leaf.page_index, leaf.bbox.y0 + 0.001))
    ]
    stack = _active_heading_stack(prior)
    return [
        heading for heading in stack
        if _heading_matches_requirement(heading, requirement_components)
    ]


def _heading_matches_requirement(
    heading: HierarchyHeading,
    requirement_components: tuple[int, ...],
) -> bool:
    heading_components = _numeric_components(heading.number)
    if heading_components is None:
        return False
    if heading.kind is HierarchyKind.PRINCIPLE:
        return bool(heading_components) and (
            heading_components[0] == requirement_components[0]
        )
    return requirement_components[:len(heading_components)] == heading_components


def _heading_regions(
    requirement_id: str,
    headings: Sequence[HierarchyHeading],
) -> list[RequirementSourceRegion]:
    key = re.sub(r"[^a-z0-9]+", "-", requirement_id.casefold()).strip("-") or "unknown"
    result: list[RequirementSourceRegion] = []
    for index, heading in enumerate(headings, start=1):
        result.append(RequirementSourceRegion(
            segment_id=(
                f"req-{key}-p{heading.page_number:04d}-criterion_heading-{index:02d}"
            ),
            page_index=heading.page_index,
            page_number=heading.page_number,
            bbox=heading.bbox,
            role="criterion_heading",
            source_text=heading.text,
            native_text=heading.text,
            resolved_text=heading.text,
            resolution_status=ResolutionStatus.RESOLVED,
            requires_human_review=False,
            native_object_refs=list(heading.native_object_refs),
        ))
    return result


def _mark_unresolved(requirement: Requirement, reason: str) -> None:
    _append_unique(requirement.source_anomalies, reason)
    _append_unique(requirement.validation_flags, "hierarchy_profile:review_required")
    if requirement.status is RequirementStatus.ACCEPTED:
        requirement.status = RequirementStatus.REVIEW_REQUIRED
        requirement.confidence = min(requirement.confidence or 0.5, 0.5)
        _append_unique(
            requirement.validation_flags,
            "fail_closed:review_required",
        )


def _numeric_components(value: str) -> tuple[int, ...] | None:
    normalized = value.strip().rstrip(".")
    if not _NUMBER_PREFIX_RE.fullmatch(normalized):
        return None
    return tuple(int(part) for part in normalized.split("."))


def _join_inline(values: Iterable[str]) -> str:
    text = _clean(" ".join(_clean(value) for value in values if _clean(value)))
    text = re.sub(r"\s+([,.;:!?\]])", r"\1", text)
    text = re.sub(r"([\[])\s+", r"\1", text)
    return text


def _clean(value: str) -> str:
    return _SPACE_RE.sub(" ", value).strip()


def _normalized_font_name(value: str | None) -> str:
    if not value:
        return ""
    normalized = value.strip().lstrip("/")
    if "+" in normalized:
        prefix, suffix = normalized.split("+", 1)
        if len(prefix) == 6 and prefix.isalpha():
            normalized = suffix
    return normalized.casefold()


def _valid_bbox(item: NativeObject) -> bool:
    x0, y0, x1, y1 = item.bbox_points
    return x0 >= 0 and y0 >= 0 and x1 > x0 and y1 > y0


def _union_boxes(
    boxes: Iterable[tuple[float, float, float, float]],
) -> tuple[float, float, float, float]:
    materialized = list(boxes)
    if not materialized:
        raise ValueError("cannot union empty boxes")
    return (
        min(box[0] for box in materialized),
        min(box[1] for box in materialized),
        max(box[2] for box in materialized),
        max(box[3] for box in materialized),
    )


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)
