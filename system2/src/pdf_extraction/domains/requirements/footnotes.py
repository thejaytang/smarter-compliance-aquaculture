from __future__ import annotations

from dataclasses import dataclass, replace
import re
from statistics import median
from typing import Iterable, Sequence

from ...types import NativeObject, NativePage
from .native_assembler import (
    NativeFootnoteLinkCandidate,
    NativeRequirement,
    RequirementSourceSpan,
)


_MARKER_RE = re.compile(r"^\d{1,3}$")
_BRACKETED_MARKER_RE = re.compile(r"^\[(\d{1,3})\]\s*")
_FORMAL_ROW_LABEL_RE = re.compile(
    r"^(?:indicator|requirement|applicability|indikator|krav|anvendelse)\s*:?$",
    re.IGNORECASE,
)
_FORMAL_HEADING_RE = re.compile(
    r"^(?:criterion|principle|section|chapter|part|appendix|annex|"
    r"kriterium|prinsipp|seksjon|avsnitt|kapittel|del|vedlegg)\s+"
    r"\d+(?:\.\d+)*\b",
    re.IGNORECASE,
)
_FORMAL_ID_RE = re.compile(r"^\d+(?:\.\d+)+\s*$")
_ANCESTOR_HEADING_RE = re.compile(
    r"^(?:criterion|principle|section|chapter|part|appendix|annex|"
    r"kriterium|prinsipp|seksjon|avsnitt|kapittel|del|vedlegg)\s+"
    r"(?P<number>\d+(?:\.\d+)*)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class FootnoteDefinition:
    """A source-backed footnote definition detected in the page-bottom band."""

    marker: str
    page_index: int
    bbox: tuple[float, float, float, float]
    source_text: str
    native_object_ids: tuple[str, ...]


@dataclass(frozen=True)
class _Word:
    id: str
    text: str
    bbox: tuple[float, float, float, float]
    font_name: str | None

    @property
    def x0(self) -> float:
        return self.bbox[0]

    @property
    def y0(self) -> float:
        return self.bbox[1]

    @property
    def x1(self) -> float:
        return self.bbox[2]

    @property
    def y1(self) -> float:
        return self.bbox[3]

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2

    @property
    def height(self) -> float:
        return self.y1 - self.y0


def link_requirement_footnotes(
    requirements: Sequence[NativeRequirement],
    pages: Sequence[NativePage],
) -> list[NativeRequirement]:
    """Link superscript anchors to exact page-bottom footnote definitions.

    The linker does not infer missing prose. It accepts a definition only when
    the marker is present in the Requirement's native evidence, and exactly one
    conventional page-bottom or explicitly labelled table definition with the
    same marker exists on that page or, when absent there, on exactly one
    immediately adjacent page. Ambiguous or missing evidence is carried
    forward as a fail-closed issue for the canonical adapter.
    """

    pages_by_index = {page.page_index: page for page in pages}
    definitions_by_page = {
        page.page_index: _unique_definitions([
            *detect_page_footnote_definitions(page),
            *detect_table_footnote_definitions(page),
        ])
        for page in pages
    }
    requirement_ids = {item.requirement_id for item in requirements}
    direct_definition_markers_by_family: dict[object, set[str]] = {}
    linked: list[NativeRequirement] = []
    for requirement in requirements:
        # The template assembler sees physical rows, not semantic ownership.
        # A row can contain the next Criterion's footnote before its first
        # Requirement anchor.  Rebuild footnote spans only from an owned
        # direct marker or an explicit semantic/scope target below; otherwise
        # a physically nearby but unrelated definition would silently widen
        # the Requirement evidence.
        base_segments = [
            span for span in requirement.source_segments if span.role != "footnote"
        ]
        issues = list(requirement.footnote_link_issues)
        footnote_spans: list[RequirementSourceSpan] = []
        link_candidates: list[NativeFootnoteLinkCandidate] = []
        for marker in _unique_markers(requirement.footnote_markers):
            anchor_pages = _anchor_pages(requirement, marker, pages_by_index)
            if len(anchor_pages) != 1:
                issue = (
                    f"footnote_anchor_missing:{marker}"
                    if not anchor_pages
                    else f"footnote_anchor_ambiguous:{marker}"
                )
                _append_unique(issues, issue)
                continue
            anchor_page = anchor_pages[0]
            same_page = [
                item for item in definitions_by_page.get(anchor_page, [])
                if item.marker == marker
            ]
            if len(same_page) > 1:
                _append_unique(issues, f"footnote_definition_ambiguous:{marker}")
                continue
            candidates = same_page
            if not candidates:
                # A continued table can repeat an anchor after its definition
                # appeared on the immediately preceding page, while other
                # layouts put definitions on the immediately following page.
                # Admit either adjacent page only when the marker resolves to
                # one unique definition across both directions.
                candidates = [
                    item
                    for adjacent_page in (anchor_page - 1, anchor_page + 1)
                    if adjacent_page in pages_by_index
                    for item in definitions_by_page.get(adjacent_page, [])
                    if item.marker == marker
                ]
            if len(candidates) != 1:
                issue = (
                    f"footnote_definition_missing:{marker}"
                    if not candidates
                    else f"footnote_definition_ambiguous:{marker}"
                )
                _append_unique(issues, issue)
                continue
            definition = candidates[0]
            explicit_targets = _exclusive_requirement_targets(
                definition.source_text, requirement_ids
            )
            candidate_issues: list[str] = []
            if (
                explicit_targets
                and requirement.requirement_id not in explicit_targets
                and not _definition_names_anchor_host(definition.source_text, marker)
            ):
                mismatch = (
                    f"footnote_direct_target_mismatch:{marker}:"
                    f"explicit_targets={','.join(explicit_targets)}"
                )
                _append_unique(issues, mismatch)
                candidate_issues.append(mismatch)
            _append_definition_span(footnote_spans, definition)
            link_candidates.append(NativeFootnoteLinkCandidate(
                marker=marker,
                link_type=(
                    "direct" if definition.page_index == anchor_page else "inherited"
                ),
                definition_page_index=definition.page_index,
                definition_native_object_ids=definition.native_object_ids,
                issues=tuple(candidate_issues),
            ))
            direct_definition_markers_by_family.setdefault(
                requirement.family, set()
            ).add(marker)
        linked.append(replace(
            requirement,
            source_segments=[*base_segments, *footnote_spans],
            footnote_link_issues=issues,
            footnote_link_candidates=link_candidates,
        ))

    # A definition can govern a Requirement without an inline superscript.
    # Only two source-explicit cases are admitted: an exact Requirement ID in
    # the definition, or a leading ``Term:`` whose exact term occurs in a
    # direct Requirement field and whose definition marker is directly
    # anchored within the same template family.  Both remain page-local or
    # immediately adjacent and ambiguous markers fail closed.
    enriched: list[NativeRequirement] = []
    for requirement in linked:
        spans = list(requirement.source_segments)
        issues = list(requirement.footnote_link_issues)
        candidates = list(requirement.footnote_link_candidates)
        direct_markers = {
            item.marker for item in candidates
            if item.link_type in {"direct", "inherited"}
        }
        requirement_pages = {
            span.page_index for span in requirement.source_segments
            if span.role != "footnote"
        }
        nearby = [
            definition
            for page_definitions in definitions_by_page.values()
            for definition in page_definitions
            if any(
                abs(definition.page_index - page_index) <= 1
                for page_index in requirement_pages
            )
        ]
        semantic_by_marker: dict[str, list[FootnoteDefinition]] = {}
        direct_family_markers = direct_definition_markers_by_family.get(
            requirement.family, set()
        )
        direct_text = _requirement_direct_text(requirement)
        for definition in nearby:
            if definition.marker in direct_markers:
                continue
            explicit_targets = _explicit_requirement_ids(
                definition.source_text, requirement_ids
            )
            exact_id_match = requirement.requirement_id in explicit_targets
            term = _definition_term(definition.source_text)
            exact_term_match = bool(
                term
                and definition.marker in direct_family_markers
                and _contains_exact_term(direct_text, term)
            )
            if exact_id_match or exact_term_match:
                semantic_by_marker.setdefault(definition.marker, []).append(definition)

        for marker, definitions in semantic_by_marker.items():
            unique = _unique_definitions(definitions)
            if len(unique) != 1:
                _append_unique(issues, f"footnote_semantic_ambiguous:{marker}")
                continue
            definition = unique[0]
            _append_definition_span(spans, definition)
            candidates.append(NativeFootnoteLinkCandidate(
                marker=marker,
                # An explicit Requirement ID is semantic ownership even when
                # the marker is printed on an ancestor heading. ``inherited``
                # is reserved for a physical adjacent-page continuation.
                link_type="semantic",
                definition_page_index=definition.page_index,
                definition_native_object_ids=definition.native_object_ids,
            ))
        enriched.append(replace(
            requirement,
            source_segments=spans,
            footnote_link_issues=issues,
            footnote_link_candidates=candidates,
        ))
    return enriched


def detect_page_footnote_definitions(page: NativePage) -> list[FootnoteDefinition]:
    """Detect numbered definitions using marker, geometry, size and spacing.

    The first definition is not required to cross a fixed page-height ratio.
    Instead, small left-margin marker rows form a coherent bottom cluster; the
    cluster's first row must be separated from preceding body material or be
    supported by multiple consistent definition starts.
    """

    words = [
        _Word(
            id=item.id,
            text=item.text.strip(),
            bbox=item.bbox_points,
            font_name=item.font_name,
        )
        for item in page.words
        if item.text.strip() and _valid_native_object(item)
    ]
    upper = page.height_points * 0.93
    rows = _word_rows([word for word in words if word.cy < upper])
    starts: list[tuple[int, _Word]] = []
    for row_index, row in enumerate(rows):
        ordered = sorted(row, key=lambda item: item.x0)
        if len(ordered) < 2:
            continue
        marker = ordered[0]
        body = [word for word in ordered[1:] if word.x0 > marker.x1]
        if (
            not _MARKER_RE.fullmatch(marker.text)
            or marker.x0 > page.width_points * 0.18
            or not body
        ):
            continue
        body_height = median(word.height for word in body)
        if body_height <= 0 or marker.height > body_height * 0.82:
            continue
        starts.append((row_index, marker))

    starts = _select_definition_cluster(starts, rows, page.height_points)

    definitions: list[FootnoteDefinition] = []
    for position, (row_index, marker) in enumerate(starts):
        next_start = starts[position + 1][0] if position + 1 < len(starts) else len(rows)
        materialized = list(rows[row_index])
        prior_y1 = max(word.y1 for word in materialized)
        base_height = median(word.height for word in materialized[1:])
        for following in rows[row_index + 1:next_start]:
            gap = min(word.y0 for word in following) - prior_y1
            if gap > max(4.0, base_height * 1.25):
                break
            materialized.extend(following)
            prior_y1 = max(word.y1 for word in following)
        ordered_rows = _word_rows(materialized)
        text = " ".join(
            " ".join(word.text for word in sorted(row, key=lambda item: item.x0))
            for row in ordered_rows
        ).strip()
        if not text:
            continue
        definitions.append(FootnoteDefinition(
            marker=marker.text,
            page_index=page.page_index,
            bbox=_union_boxes(word.bbox for word in materialized),
            source_text=text,
            native_object_ids=tuple(word.id for word in materialized),
        ))
    return definitions


def detect_table_footnote_definitions(page: NativePage) -> list[FootnoteDefinition]:
    """Detect bracketed definitions in explicitly labelled table footnote rows.

    Audit manuals and some standards place definitions inside the table body,
    so neither a page-bottom band nor superscript typography is available.
    A definition is accepted only when a left-side ``Footnote`` cell vertically
    overlaps a bracketed ``[N]`` body cell.  This row-label evidence prevents
    inline anchors such as ``score [55]`` from being mistaken for definitions.
    """

    lines = sorted(
        (
            item for item in page.text_lines
            if item.text.strip() and _valid_native_object(item)
        ),
        key=lambda item: (item.bbox_points[1], item.bbox_points[0]),
    )
    labels = [
        item for item in lines if item.text.strip().casefold() == "footnote"
    ]
    starts = [
        item for item in lines
        if _BRACKETED_MARKER_RE.match(item.text.strip())
        and item.bbox_points[0] <= page.width_points * 0.25
    ]
    definitions: list[FootnoteDefinition] = []
    for start in starts:
        start_text = start.text.strip()
        marker_match = _BRACKETED_MARKER_RE.match(start_text)
        assert marker_match is not None
        materialized = [start]
        prior_y1 = start.bbox_points[3]
        base_height = start.bbox_points[3] - start.bbox_points[1]
        for following in lines:
            if following.id == start.id or following.bbox_points[1] <= start.bbox_points[1]:
                continue
            gap = following.bbox_points[1] - prior_y1
            if gap > max(4.0, base_height * 1.5):
                break
            if _BRACKETED_MARKER_RE.match(following.text.strip()):
                break
            if _is_formal_table_boundary(following, page.width_points):
                break
            if abs(following.bbox_points[0] - start.bbox_points[0]) > 4.0:
                continue
            materialized.append(following)
            prior_y1 = following.bbox_points[3]

        bbox = _union_boxes(item.bbox_points for item in materialized)
        vertically_labelled = any(
            label.bbox_points[0] < start.bbox_points[0]
            and bbox[1] - 1.5
            <= (label.bbox_points[1] + label.bbox_points[3]) / 2
            <= bbox[3] + 1.5
            for label in labels
        )
        if not vertically_labelled:
            continue
        source_text = " ".join(
            item.text.strip()
            for item in sorted(
                materialized,
                key=lambda item: (item.bbox_points[1], item.bbox_points[0]),
            )
        ).strip()
        definitions.append(FootnoteDefinition(
            marker=marker_match.group(1),
            page_index=page.page_index,
            bbox=bbox,
            source_text=source_text,
            native_object_ids=tuple(item.id for item in materialized),
        ))
    return definitions


def _select_definition_cluster(
    starts: Sequence[tuple[int, _Word]],
    rows: Sequence[Sequence[_Word]],
    page_height: float,
) -> list[tuple[int, _Word]]:
    """Select the bottom coherent marker cluster without a fixed band start."""

    if not starts:
        return []
    ordered = sorted(starts, key=lambda item: item[1].cy)
    clusters: list[list[tuple[int, _Word]]] = []
    for start in ordered:
        if not clusters:
            clusters.append([start])
            continue
        prior = clusters[-1][-1][1]
        body_heights = [
            word.height
            for row_index, _ in (clusters[-1][-1], start)
            for word in rows[row_index]
            if word.text and not _MARKER_RE.fullmatch(word.text)
        ]
        scale = median(body_heights) if body_heights else max(prior.height, start[1].height)
        if start[1].cy - prior.cy <= max(48.0, scale * 4.5):
            clusters[-1].append(start)
        else:
            clusters.append([start])

    # The last definition start anchors the cluster in the lower document
    # region.  Earlier starts may sit above 70% when a long footnote band is
    # present, as in the Salmon/Cod page containing markers 32-36.
    eligible = [
        cluster for cluster in clusters
        if cluster[-1][1].cy >= page_height * 0.55
    ]
    if not eligible:
        return []
    cluster = eligible[-1]
    if len(cluster) > 1:
        return cluster

    row_index, marker = cluster[0]
    if row_index == 0:
        return cluster if marker.cy >= page_height * 0.60 else []
    prior_y1 = max(word.y1 for word in rows[row_index - 1])
    row_body = [
        word for word in rows[row_index]
        if not _MARKER_RE.fullmatch(word.text)
    ]
    body_height = median(word.height for word in row_body) if row_body else marker.height
    gap = min(word.y0 for word in rows[row_index]) - prior_y1
    return cluster if gap > max(8.0, body_height * 1.5) else []


def _anchor_pages(
    requirement: NativeRequirement,
    marker: str,
    pages_by_index: dict[int, NativePage],
) -> list[int]:
    pages: list[int] = []
    for span in requirement.source_segments:
        if span.role == "footnote":
            continue
        page = pages_by_index.get(span.page_index)
        if page is None:
            continue
        refs = set(span.native_object_ids)
        if any(
            item.id in refs and _contains_marker(item.text, marker)
            for item in [*page.words, *page.text_lines]
        ):
            if span.page_index not in pages:
                pages.append(span.page_index)
    return pages


def _append_definition_span(
    spans: list[RequirementSourceSpan],
    definition: FootnoteDefinition,
) -> None:
    identity = (definition.page_index, definition.native_object_ids)
    if any(
        span.role == "footnote"
        and (span.page_index, span.native_object_ids) == identity
        for span in spans
    ):
        return
    spans.append(RequirementSourceSpan(
        role="footnote",
        page_index=definition.page_index,
        bbox=definition.bbox,
        source_text=definition.source_text,
        native_object_ids=definition.native_object_ids,
    ))


def _explicit_requirement_ids(
    source_text: str,
    requirement_ids: set[str],
) -> list[str]:
    """Return source-explicit targets, excluding ordinary cross-references.

    A bare ``see 2.1.4`` is a cross-reference inside the footnote, not proof
    that the definition governs Requirement 2.1.4.  Targeting needs an
    applicability cue (``Standard 2.1.4 applies``) or an explicit plural
    declaration such as ``requirements 1.2.3 and 1.2.4``.
    """

    matches: list[str] = []
    declares_requirements = bool(
        re.search(r"\brequirements?\b", source_text, re.IGNORECASE)
    )
    for requirement_id in sorted(requirement_ids, key=lambda item: (-len(item), item)):
        identity = re.escape(requirement_id)
        occurrence = re.compile(
            rf"(?<![\d.]){re.escape(requirement_id)}(?!\d|\.\d)"
        )
        if not occurrence.search(source_text):
            continue
        targeted = declares_requirements or any(
            re.search(pattern, source_text, re.IGNORECASE)
            for pattern in (
                rf"\b(?:standard|indicator|requirement)\s+{identity}"
                rf"\b[^.\n]{{0,40}}\b(?:applies|applicable|governs)\b",
                rf"(?<![\d.]){identity}(?!\d|\.\d)"
                rf"[^.\n]{{0,40}}\b(?:applies|applicable|governs)\b",
                rf"\b(?:applies|applicable|governs)\b[^.\n]{{0,40}}"
                rf"(?<![\d.]){identity}(?!\d|\.\d)",
            )
        )
        if targeted and requirement_id not in matches:
            matches.append(requirement_id)
    return sorted(matches)


def _exclusive_requirement_targets(
    source_text: str,
    requirement_ids: set[str],
) -> list[str]:
    """Return only IDs carrying an explicit applicability/governance cue.

    This narrower view is used for direct-anchor conflict detection.  A
    definition may contain auxiliary references such as ``requirements on
    transparency for 2.1.1`` without invalidating a visible anchor on another
    row, so those references must not be treated as exclusive targets.
    """

    matches: list[str] = []
    for requirement_id in sorted(requirement_ids, key=lambda item: (-len(item), item)):
        identity = re.escape(requirement_id)
        targeted = any(
            re.search(pattern, source_text, re.IGNORECASE)
            for pattern in (
                rf"\b(?:standard|indicator|requirement)\s+{identity}"
                rf"\b[^.\n]{{0,40}}\b(?:applies|applicable|governs)\b",
                rf"(?<![\d.]){identity}(?!\d|\.\d)"
                rf"[^.\n]{{0,40}}\b(?:applies|applicable|governs)\b",
                rf"\b(?:applies|applicable|governs)\b[^.\n]{{0,40}}"
                rf"(?<![\d.]){identity}(?!\d|\.\d)",
            )
        )
        if targeted:
            matches.append(requirement_id)
    return sorted(matches)


def _definition_term(source_text: str) -> str | None:
    match = re.match(r"^\s*\d{1,3}\s+([^:\n]{2,80}?)\s*:\s+", source_text)
    if not match:
        return None
    term = " ".join(match.group(1).split()).strip(" .")
    return term if len(term) >= 3 else None


def _definition_names_anchor_host(source_text: str, marker: str) -> bool:
    """Return whether a direct definition explicitly includes its host row.

    ``This standard and standard 4.3.2 applies ...`` includes both the row
    carrying the marker and the named additional target.  A later sentence
    containing ``this standard`` does not prove that, so only a leading
    deictic subject after the marker is admitted.
    """

    body = re.sub(
        rf"^\s*(?:{re.escape(marker)}|\[{re.escape(marker)}\])\s*",
        "",
        source_text,
        count=1,
    )
    return bool(re.match(
        r"^this\s+(?:standard|indicator|requirement)\b",
        body,
        re.IGNORECASE,
    ))


def _has_ancestor_scope_anchor(
    requirement: NativeRequirement,
    marker: str,
    pages_by_index: dict[int, NativePage],
) -> bool:
    """Prove inheritance from a visible numbered ancestor heading.

    A definition merely naming a Requirement is semantic.  It becomes
    inherited only when the same marker is visibly attached to a formal
    heading whose number is a strict prefix of the Requirement ID, e.g.
    ``Criterion 2.5 ... [23]`` governing Requirement ``2.5.2``.
    """

    requirement_parts = requirement.requirement_id.split(".")
    if not all(part.isdigit() for part in requirement_parts):
        return False
    relevant_pages = {
        span.page_index
        for span in requirement.source_segments
        if span.role != "footnote"
    }
    relevant_pages.update({page - 1 for page in relevant_pages})
    for page_index in sorted(relevant_pages):
        page = pages_by_index.get(page_index)
        if page is None:
            continue
        for item in page.text_lines:
            text = " ".join(item.text.split()).strip()
            heading = _ANCESTOR_HEADING_RE.match(text)
            if not heading or not _contains_marker(text, marker):
                continue
            heading_parts = heading.group("number").split(".")
            if (
                len(heading_parts) < len(requirement_parts)
                and requirement_parts[:len(heading_parts)] == heading_parts
            ):
                return True
    return False


def _is_formal_table_boundary(item: NativeObject, width: float) -> bool:
    """Stop a bracketed definition at the next formal row/heading boundary."""

    if item.bbox_points[0] > width * 0.31:
        return False
    text = " ".join(item.text.split()).strip()
    return bool(
        _FORMAL_ROW_LABEL_RE.fullmatch(text)
        or _FORMAL_HEADING_RE.match(text)
        or _FORMAL_ID_RE.fullmatch(text)
        or re.match(r"^instruction\s+to\s+clients?\b", text, re.IGNORECASE)
    )


def _requirement_direct_text(requirement: NativeRequirement) -> str:
    values: list[str] = [requirement.normative_text]
    for value in (
        requirement.indicator_text,
        requirement.requirement_value,
        requirement.applicability,
    ):
        if value:
            values.append(value)
    values.extend(requirement.client_actions)
    values.extend(requirement.auditor_actions)
    return "\n".join(values)


def _contains_exact_term(source_text: str, term: str) -> bool:
    pattern = re.compile(
        rf"(?<!\w){re.escape(term)}(?!\w)",
        re.IGNORECASE,
    )
    return bool(pattern.search(source_text))


def _unique_definitions(
    definitions: Sequence[FootnoteDefinition],
) -> list[FootnoteDefinition]:
    result: list[FootnoteDefinition] = []
    seen: set[tuple[int, tuple[str, ...]]] = set()
    for definition in definitions:
        identity = (definition.page_index, definition.native_object_ids)
        if identity not in seen:
            seen.add(identity)
            result.append(definition)
    return result


def _word_rows(words: Sequence[_Word]) -> list[list[_Word]]:
    if not words:
        return []
    tolerance = max(1.5, median(word.height for word in words) * 0.60)
    rows: list[list[_Word]] = []
    for word in sorted(words, key=lambda item: (item.cy, item.x0)):
        if not rows or abs(median(item.cy for item in rows[-1]) - word.cy) > tolerance:
            rows.append([word])
        else:
            rows[-1].append(word)
    return rows


def _valid_native_object(item: NativeObject) -> bool:
    x0, y0, x1, y1 = item.bbox_points
    return x0 >= 0 and y0 >= 0 and x1 > x0 and y1 > y0


def _unique_markers(markers: Iterable[str]) -> list[str]:
    result: list[str] = []
    for marker in markers:
        cleaned = marker.strip()
        bracketed = _BRACKETED_MARKER_RE.fullmatch(cleaned)
        normalized = bracketed.group(1) if bracketed else cleaned
        if _MARKER_RE.fullmatch(normalized) and normalized not in result:
            result.append(normalized)
    return result


def _contains_marker(value: str, marker: str) -> bool:
    cleaned = value.strip()
    if cleaned == marker:
        return True
    return bool(re.search(rf"\[{re.escape(marker)}\]", cleaned))


def _union_boxes(
    boxes: Iterable[tuple[float, float, float, float]],
) -> tuple[float, float, float, float]:
    values = list(boxes)
    return (
        min(box[0] for box in values),
        min(box[1] for box in values),
        max(box[2] for box in values),
        max(box[3] for box in values),
    )


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)
