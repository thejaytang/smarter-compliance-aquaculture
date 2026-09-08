from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from enum import Enum
import re
from statistics import median
from typing import Iterable, Literal, Mapping, Sequence

from ...types import NativePage


class TemplateFamily(str, Enum):
    """Born-digital layouts supported by the first Requirement assembler."""

    SINGLE_COLUMN_INDICATORS = "SINGLE_COLUMN_INDICATORS"
    LEGACY_INDICATOR_VALUE = "LEGACY_INDICATOR_VALUE"
    AUDIT_MATRIX = "AUDIT_MATRIX"
    ID_NORMATIVE_WITH_CONTEXT = "ID_NORMATIVE_WITH_CONTEXT"


@dataclass(frozen=True)
class RequirementSourceSpan:
    role: str
    page_index: int
    bbox: tuple[float, float, float, float]
    source_text: str
    native_object_ids: tuple[str, ...] = ()

    @property
    def page_number(self) -> int:
        return self.page_index + 1

    def to_dict(self) -> dict[str, object]:
        return {
            "role": self.role,
            "page_index": self.page_index,
            "page_number": self.page_number,
            "bbox": {
                "x0": self.bbox[0],
                "y0": self.bbox[1],
                "x1": self.bbox[2],
                "y1": self.bbox[3],
            },
            "source_text": self.source_text,
            "native_object_ids": list(self.native_object_ids),
        }


@dataclass(frozen=True)
class NativeFootnoteLinkCandidate:
    """Source-backed relationship between a Requirement and one footnote.

    ``link_type`` records how the relationship was evidenced.  A direct
    anchor can remain direct while ``issues`` marks a target mismatch; this
    lets the canonical adapter fail closed without erasing the source
    relationship that exposed the anomaly.
    """

    marker: str
    link_type: Literal["direct", "inherited", "semantic"]
    definition_page_index: int
    definition_native_object_ids: tuple[str, ...]
    issues: tuple[str, ...] = ()


@dataclass
class NativeRequirement:
    requirement_id: str
    family: TemplateFamily
    normative_text: str
    source_segments: list[RequirementSourceSpan]
    indicator_text: str | None = None
    requirement_value: str | None = None
    applicability: str | None = None
    client_actions: list[str] = field(default_factory=list)
    auditor_actions: list[str] = field(default_factory=list)
    footnote_markers: list[str] = field(default_factory=list)
    footnote_link_issues: list[str] = field(default_factory=list)
    footnote_link_candidates: list[NativeFootnoteLinkCandidate] = field(
        default_factory=list
    )

    @property
    def page_index(self) -> int:
        return self.source_segments[0].page_index

    @property
    def page_number(self) -> int:
        return self.page_index + 1

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        return _union_boxes(span.bbox for span in self.source_segments)

    @property
    def source_text(self) -> str:
        return "\n".join(span.source_text for span in self.source_segments).strip()

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-ready record without coupling to canonical models."""
        result = asdict(self)
        result["family"] = self.family.value
        result["page_index"] = self.page_index
        result["page_number"] = self.page_number
        result["bbox"] = {
            "x0": self.bbox[0],
            "y0": self.bbox[1],
            "x1": self.bbox[2],
            "y1": self.bbox[3],
        }
        result["source_text"] = self.source_text
        result["source_segments"] = [span.to_dict() for span in self.source_segments]
        return result


@dataclass(frozen=True)
class _Unit:
    id: str
    text: str
    bbox: tuple[float, float, float, float]
    font_name: str | None = None

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


_ID_RE = re.compile(r"^\d+(?:\.\d+){2,}$")
_CLIENT_MARKER_RE = re.compile(r"^[a-z]\.\s+")
_AUDITOR_MARKER_RE = re.compile(r"^[A-Z]\.\s+")
_AUDITOR_GEOMETRIC_MARKER_RE = re.compile(r"^[A-Za-z]\.\s+")
_ACTION_SECTION_HEADER_RE = re.compile(
    r"\brequired\s+(?:client|cab)\s+actions\b", re.IGNORECASE
)
_ACTION_CONTEXT_BOUNDARY_RE = re.compile(
    r"^(?:note(?:\s+indicator\b[^:]*)?\s*:|instruction\s+to\s+clients?\b)",
    re.IGNORECASE,
)
_INSTRUCTION_BLOCK_END_RE = re.compile(
    r"^(?:indicator|requirement|applicability)(?:\s*:\s*.*)?$|"
    r"^(?:criterion|principle|section|chapter|part|appendix|annex)\b|"
    r"^(?:footnote\s*)$|^[A-Za-z]\.\s+|^\d+(?:\.\d+){2,}$",
    re.IGNORECASE,
)
_EXPLICIT_INSTRUCTION_OWNER_RE = re.compile(
    r"\bIndicator\s+(?P<id>\d+(?:\.\d+){2,})\b",
    re.IGNORECASE,
)
_ACTION_LIST_MARKER_RE = re.compile(r"^[\-\u2013\u2014]\s+")
_AUDIT_FOOTNOTE_BODY_RE = re.compile(r"^\[(\d{1,3})\](?:\s+|$)")
_BRACKET_FOOTNOTE_ANCHOR_RE = re.compile(r"\[(\d{1,3})\]")
_FORMAL_MODAL_RE = re.compile(r"\b(?:shall|must|required\s+to|may\s+not)\b", re.IGNORECASE)
_FOOTNOTE_MARKER_RE = re.compile(r"^\d{1,3}$")
_SPACE_RE = re.compile(r"\s+")


class NativeRequirementAssembler:
    """Assemble formal Requirement rows from native word/line geometry.

    Template selection is based on visible header and column geometry.  Page
    indices only select input pages; neither page numbers nor source filenames
    take part in family detection or row assembly.
    """

    def assemble(
        self,
        pages: Sequence[NativePage],
        selected_indices: Iterable[int] | None = None,
        family: TemplateFamily | str | Mapping[int, TemplateFamily | str] | None = None,
        *,
        include_preceding_context: bool = True,
    ) -> list[NativeRequirement]:
        selected = set(selected_indices) if selected_indices is not None else None
        all_ordered = sorted(pages, key=lambda page: page.page_index)
        ordered = (
            _pages_with_preceding_context(all_ordered, selected)
            if selected is not None and include_preceding_context
            else [
                page
                for page in all_ordered
                if selected is None or page.page_index in selected
            ]
        )
        if not ordered:
            return []

        families = self._resolve_families(ordered, family)
        requirements: list[NativeRequirement] = []
        for page in ordered:
            page_family = families.get(page.page_index)
            if page_family is None:
                continue
            if page_family is TemplateFamily.SINGLE_COLUMN_INDICATORS:
                page_requirements = self._assemble_single_column(page)
                self._append_single_column_page_top_continuation(
                    page,
                    page_requirements,
                    requirements,
                )
                requirements.extend(page_requirements)
            elif page_family is TemplateFamily.LEGACY_INDICATOR_VALUE:
                requirements.extend(self._assemble_legacy(page))
            elif page_family is TemplateFamily.AUDIT_MATRIX:
                requirements.extend(self._assemble_audit(page))
            elif page_family is TemplateFamily.ID_NORMATIVE_WITH_CONTEXT:
                self._assemble_normative_with_context(page, requirements)
        if selected is not None:
            requirements = _project_requirements_to_selected_pages(
                requirements,
                selected,
            )
        requirements = _link_audit_instruction_blocks(requirements, ordered)
        return sorted(requirements, key=lambda item: (item.page_index, item.bbox[1]))

    def assemble_dicts(
        self,
        pages: Sequence[NativePage],
        selected_indices: Iterable[int] | None = None,
        family: TemplateFamily | str | Mapping[int, TemplateFamily | str] | None = None,
        *,
        include_preceding_context: bool = True,
    ) -> list[dict[str, object]]:
        return [
            item.to_dict()
            for item in self.assemble(
                pages,
                selected_indices,
                family,
                include_preceding_context=include_preceding_context,
            )
        ]

    def detect_family(self, page: NativePage) -> TemplateFamily | None:
        units = _line_units(page)
        texts = [_clean(unit.text).casefold() for unit in units]
        joined = "\n".join(texts)
        has_audit_columns = (
            any(
                _CLIENT_MARKER_RE.match(unit.text)
                and page.width_points * 0.31 <= unit.x0 < page.width_points * 0.61
                for unit in units
            )
            and any(
                _AUDITOR_MARKER_RE.match(unit.text)
                and unit.x0 >= page.width_points * 0.61
                for unit in units
            )
            and any(text.startswith("applicability:") for text in texts)
        )
        if (
            "required client actions" in joined and "required cab actions" in joined
        ) or has_audit_columns:
            return TemplateFamily.AUDIT_MATRIX
        if any(text == "indicator" for text in texts) and any(
            text == "requirement" for text in texts
        ):
            return TemplateFamily.LEGACY_INDICATOR_VALUE
        if "how do i interpret this requirement?" in joined or (
            any(text.startswith("requirement:") for text in texts)
            and any(text.startswith("indicator:") for text in texts)
        ):
            return TemplateFamily.ID_NORMATIVE_WITH_CONTEXT
        if any(text.startswith("indicators:") for text in texts):
            return TemplateFamily.SINGLE_COLUMN_INDICATORS
        return None

    def _resolve_families(
        self,
        pages: Sequence[NativePage],
        requested: TemplateFamily | str | Mapping[int, TemplateFamily | str] | None,
    ) -> dict[int, TemplateFamily | None]:
        mapping_is_authoritative = isinstance(requested, Mapping)
        if isinstance(requested, Mapping):
            resolved = {
                page.page_index: _coerce_family(requested.get(page.page_index))
                for page in pages
            }
        elif requested is not None:
            resolved = {page.page_index: _coerce_family(requested) for page in pages}
        else:
            resolved = {page.page_index: self.detect_family(page) for page in pages}

        # A continuation page can lack all table headers.  Only inherit across
        # consecutive selected PDF pages, and only for pages with no new family.
        prior_family: TemplateFamily | None = None
        prior_index: int | None = None
        for page in pages:
            current = resolved[page.page_index]
            if (
                not mapping_is_authoritative
                and current is None
                and prior_index is not None
                and page.page_index == prior_index + 1
                and (
                    prior_family is TemplateFamily.ID_NORMATIVE_WITH_CONTEXT
                    or (
                        prior_family is TemplateFamily.SINGLE_COLUMN_INDICATORS
                        and bool(_id_anchors(page))
                    )
                )
            ):
                current = prior_family
                resolved[page.page_index] = current
            if current is not None:
                prior_family = current
            prior_index = page.page_index
        return resolved

    def _assemble_single_column(self, page: NativePage) -> list[NativeRequirement]:
        anchors = _id_anchors(page)
        words = _word_units(page)
        lines = _line_units(page)
        result: list[NativeRequirement] = []
        for position, anchor in enumerate(anchors):
            end = (
                anchors[position + 1].y0 - 1
                if position + 1 < len(anchors)
                else _formal_section_end(page, lines, anchor.y0)
            )
            content = [
                word for word in words
                if word.x0 >= page.width_points * 0.15
                and word.cy >= anchor.y0 - 2
                and word.cy < end
            ]
            applicability_words = _single_column_applicability_words(content, lines)
            applicability_source = _words_source_text(applicability_words, set())
            applicability = (
                _strip_label(applicability_source, "Indicator applicability")
                if applicability_source else None
            )
            applicability_ids = {word.id for word in applicability_words}
            normative_words = [word for word in content if word.id not in applicability_ids]
            list_markers, footnote_markers = _semantic_marker_candidates(normative_words)
            semantic_marker_ids = {
                word.id for word in [*list_markers, *footnote_markers]
            }
            semantic_words = [
                word for word in normative_words if word.id not in semantic_marker_ids
            ]
            text, _, _ = _words_text_bbox(semantic_words)
            source_text = _words_source_text(
                normative_words, {word.id for word in footnote_markers}
            )
            if not text or not source_text:
                continue
            id_span = _span("requirement_id", page, [anchor], anchor.text)
            spans = [id_span]
            if applicability_words and applicability:
                spans.append(RequirementSourceSpan(
                    "applicability",
                    page.page_index,
                    _union_boxes(word.bbox for word in applicability_words),
                    applicability_source,
                    tuple(word.id for word in applicability_words),
                ))
            spans.append(RequirementSourceSpan(
                "normative_text",
                page.page_index,
                _union_boxes(word.bbox for word in normative_words),
                source_text,
                tuple(word.id for word in normative_words),
            ))
            result.append(NativeRequirement(
                requirement_id=anchor.text,
                family=TemplateFamily.SINGLE_COLUMN_INDICATORS,
                normative_text=text,
                indicator_text=text,
                applicability=applicability,
                footnote_markers=[word.text for word in footnote_markers],
                source_segments=spans,
            ))
        return result

    def _append_single_column_page_top_continuation(
        self,
        page: NativePage,
        page_requirements: Sequence[NativeRequirement],
        accumulated: list[NativeRequirement],
    ) -> None:
        """Attach a proven page-top list continuation to the preceding row.

        Adjacency alone is insufficient.  The previous row must reach the page
        bottom, the first ID on this page must be its numeric successor, and
        the page-top alphabetic marker must continue the prior marker sequence.
        These independent identity, geometry and list signals prevent ordinary
        page-top prose from being promoted into a Requirement.
        """

        if not accumulated or not page_requirements:
            return
        prior = accumulated[-1]
        first = page_requirements[0]
        if prior.family is not TemplateFamily.SINGLE_COLUMN_INDICATORS:
            return
        if prior.source_segments[-1].page_index != page.page_index - 1:
            return
        if prior.source_segments[-1].bbox[3] < page.height_points * 0.78:
            return
        if not _is_next_requirement_id(prior.requirement_id, first.requirement_id):
            return

        spans = _single_column_page_top_continuation_spans(page)
        if not spans:
            return
        prior_markers = _alphabetic_clause_markers(prior.normative_text)
        current_markers = [
            marker
            for span in spans
            if (marker := _leading_alphabetic_clause_marker(span.source_text))
        ]
        if not prior_markers or not current_markers:
            return
        if ord(current_markers[0]) != ord(prior_markers[-1]) + 1:
            return
        if any(
            ord(current) != ord(previous) + 1
            for previous, current in zip(current_markers, current_markers[1:])
        ):
            return

        prior.normative_text = "\n".join(
            [prior.normative_text, *(span.source_text for span in spans)]
        )
        prior.source_segments.extend(spans)

    def _assemble_legacy(self, page: NativePage) -> list[NativeRequirement]:
        anchors = _id_anchors(page)
        words = _word_units(page)
        lines = _line_units(page)
        superscript_hosts = _legacy_superscript_hosts(words)
        result: list[NativeRequirement] = []
        indicator_left = page.width_points * 0.14
        value_left = page.width_points * 0.61
        for position, anchor in enumerate(anchors):
            end = (
                anchors[position + 1].y0 - 1
                if position + 1 < len(anchors)
                else _formal_section_end(page, lines, anchor.y0)
            )
            indicator = [
                word for word in words
                if indicator_left
                <= superscript_hosts.get(word.id, word).x0
                < value_left
                and anchor.y0 - 2
                <= superscript_hosts.get(word.id, word).cy
                < end
            ]
            value = [
                word for word in words
                if superscript_hosts.get(word.id, word).x0 >= value_left
                and anchor.y0 - 2
                <= superscript_hosts.get(word.id, word).cy
                < end
            ]
            indicator_markers = [
                word for word in indicator if word.id in superscript_hosts
            ]
            value_markers = [word for word in value if word.id in superscript_hosts]
            indicator_marker_ids = {word.id for word in indicator_markers}
            value_marker_ids = {word.id for word in value_markers}
            indicator_semantic = [
                word for word in indicator if word.id not in indicator_marker_ids
            ]
            value_semantic = [
                word for word in value if word.id not in value_marker_ids
            ]
            indicator_text, _, _ = _words_text_bbox(indicator_semantic)
            value_text, _, _ = _words_text_bbox(value_semantic)
            if not indicator_text or not value_text:
                continue
            indicator_source = _words_source_text(indicator, indicator_marker_ids)
            value_source = _words_source_text(value, value_marker_ids)
            spans = [
                _span("requirement_id", page, [anchor], anchor.text),
                RequirementSourceSpan(
                    "indicator_text", page.page_index,
                    _union_boxes(word.bbox for word in indicator),
                    indicator_source, tuple(word.id for word in indicator),
                ),
                RequirementSourceSpan(
                    "requirement_value", page.page_index,
                    _union_boxes(word.bbox for word in value),
                    value_source, tuple(word.id for word in value),
                ),
            ]
            result.append(NativeRequirement(
                requirement_id=anchor.text,
                family=TemplateFamily.LEGACY_INDICATOR_VALUE,
                normative_text=f"{indicator_text}\n{value_text}",
                indicator_text=indicator_text,
                requirement_value=value_text,
                footnote_markers=[
                    word.text for word in [*indicator_markers, *value_markers]
                ],
                source_segments=spans,
            ))
        return result

    def _assemble_audit(self, page: NativePage) -> list[NativeRequirement]:
        anchors = _id_anchors(page)
        lines = _line_units(page)
        row_starts = _audit_row_starts(anchors, lines, page.width_points)
        result: list[NativeRequirement] = []
        for position, anchor in enumerate(anchors):
            start = row_starts[position]
            end = (
                row_starts[position + 1]
                if position + 1 < len(anchors) else _body_end(page, lines)
            )
            row_lines = [line for line in lines if start <= line.cy < end]
            footnote_groups = _audit_footnote_groups(row_lines, page.width_points)
            labels = _audit_label_positions(row_lines, page.width_points)
            if not all(name in labels for name in ("indicator", "requirement", "applicability")):
                continue

            indicator_units = _audit_field_units(
                row_lines, labels["indicator"], labels["requirement"], page.width_points
            )
            requirement_units = _audit_field_units(
                row_lines, labels["requirement"], labels["applicability"], page.width_points
            )
            footnote_start = min(
                (unit.y0 for group in footnote_groups for unit in group),
                default=end,
            )
            applicability_units = _audit_field_units(
                row_lines,
                labels["applicability"],
                min(end, labels["applicability"] + 10.0, footnote_start),
                page.width_points,
            )
            indicator_text = _strip_label(_join_units(indicator_units), "Indicator")
            requirement_value = _strip_label(_join_units(requirement_units), "Requirement")
            applicability = _strip_label(_join_units(applicability_units), "Applicability")
            if not indicator_text or not requirement_value:
                continue

            client_units = [
                line for line in row_lines
                if page.width_points * 0.31 <= line.x0 < page.width_points * 0.61
            ]
            auditor_units = [
                line for line in row_lines if line.x0 >= page.width_points * 0.61
            ]
            note_start = min(
                (
                    line.y0
                    for line in row_lines
                    if _ACTION_CONTEXT_BOUNDARY_RE.match(_clean(line.text))
                ),
                default=end,
            )
            client_units = [line for line in client_units if line.cy < note_start]
            auditor_units = [line for line in auditor_units if line.cy < note_start]
            client_units = _trim_action_units(client_units, _CLIENT_MARKER_RE)
            auditor_units = _trim_action_units(
                auditor_units, _AUDITOR_GEOMETRIC_MARKER_RE
            )
            client_groups = _split_action_groups(client_units, _CLIENT_MARKER_RE)
            auditor_groups = _split_action_groups(
                auditor_units, _AUDITOR_GEOMETRIC_MARKER_RE
            )
            client_actions = [text for text, _units in client_groups]
            auditor_actions = [text for text, _units in auditor_groups]

            metadata_units = indicator_units + requirement_units + applicability_units
            metadata_text = (
                f"Indicator: {indicator_text}\nRequirement: {requirement_value}"
                + (f"\nApplicability: {applicability}" if applicability else "")
            )
            spans = [
                _span("requirement_id", page, [anchor], anchor.text),
                _span("indicator_text", page, indicator_units, indicator_text),
                _span(
                    "requirement_value",
                    page,
                    requirement_units,
                    requirement_value,
                ),
                _span("applicability", page, applicability_units, applicability),
                _span("normative_text", page, metadata_units, metadata_text),
            ]
            spans.extend(
                _span("client_action", page, units, _join_units(units))
                for text, units in client_groups
            )
            spans.extend(
                _span("auditor_action", page, units, _join_units(units))
                for text, units in auditor_groups
            )
            spans.extend(
                _span("footnote", page, units, _join_units(units))
                for units in footnote_groups
            )
            result.append(NativeRequirement(
                requirement_id=anchor.text,
                family=TemplateFamily.AUDIT_MATRIX,
                normative_text=metadata_text,
                indicator_text=indicator_text,
                requirement_value=requirement_value,
                applicability=applicability or None,
                client_actions=client_actions,
                auditor_actions=auditor_actions,
                footnote_markers=_bracket_footnote_markers(
                    indicator_text,
                    requirement_value,
                    applicability,
                ),
                source_segments=spans,
            ))
        return result

    def _assemble_normative_with_context(
        self,
        page: NativePage,
        accumulated: list[NativeRequirement],
    ) -> None:
        anchors = _id_anchors(page)
        lines = _line_units(page)
        words = _word_units(page)
        context_y = min(
            (
                line.y0 for line in lines
                if _clean(line.text).casefold().startswith("how do i interpret this requirement?")
            ),
            default=_body_end(page, lines),
        )

        if not anchors:
            self._append_context_continuation(page, words, lines, context_y, accumulated)
            return

        for position, anchor in enumerate(anchors):
            next_y = anchors[position + 1].y0 - 1 if position + 1 < len(anchors) else _body_end(page, lines)
            end = min(next_y, context_y)
            content = [
                word for word in words
                if word.x0 >= page.width_points * 0.18
                and anchor.y0 - 2 <= word.cy < end
            ]
            applicability_words = [
                word for word in content
                if _word_line_starts_with(word, lines, "indicator applicability:")
            ]
            if applicability_words:
                app_line_y = min(word.y0 for word in applicability_words)
                app_line_end = max(word.y1 for word in applicability_words)
                app_words = [word for word in content if app_line_y - 1 <= word.cy <= app_line_end + 1]
                content = [word for word in content if word not in app_words]
                app_text, app_bbox, app_ids = _words_text_bbox(app_words)
                applicability = _strip_label(app_text, "Indicator applicability")
            else:
                app_bbox, app_ids, applicability = (0.0, 0.0, 0.0, 0.0), (), None

            list_markers, footnote_markers = _semantic_marker_candidates(content)
            semantic_marker_ids = {
                word.id for word in [*list_markers, *footnote_markers]
            }
            semantic_words = [
                word for word in content if word.id not in semantic_marker_ids
            ]
            text, _semantic_bbox, _semantic_ids = _words_text_bbox(semantic_words)
            if not text:
                continue
            source_text = _words_source_text(
                content, {word.id for word in footnote_markers}
            )
            bbox = _union_boxes(word.bbox for word in content)
            ids = tuple(word.id for word in content)
            spans = [
                _span("requirement_id", page, [anchor], anchor.text),
            ]
            if applicability:
                spans.append(RequirementSourceSpan(
                    "applicability", page.page_index, app_bbox, applicability, app_ids
                ))
            spans.append(RequirementSourceSpan(
                "normative_text", page.page_index, bbox, source_text, ids
            ))
            accumulated.append(NativeRequirement(
                requirement_id=anchor.text,
                family=TemplateFamily.ID_NORMATIVE_WITH_CONTEXT,
                normative_text=text,
                applicability=applicability,
                footnote_markers=[word.text for word in footnote_markers],
                source_segments=spans,
            ))

    def _append_context_continuation(
        self,
        page: NativePage,
        words: list[_Unit],
        lines: list[_Unit],
        context_y: float,
        accumulated: list[NativeRequirement],
    ) -> None:
        if not accumulated:
            return
        prior = accumulated[-1]
        if prior.family is not TemplateFamily.ID_NORMATIVE_WITH_CONTEXT:
            return
        # Only a prior formal segment that reaches the previous page body end
        # can own an unlabelled continuation on the next page.
        if prior.source_segments[-1].bbox[3] < 0.78 * page.height_points:
            return
        content = [
            word for word in words
            if word.x0 >= page.width_points * 0.18
            and word.cy >= page.height_points * 0.06
            and word.cy < context_y
            and word.cy < _body_end(page, lines)
        ]
        text, bbox, ids = _words_text_bbox(content)
        if not text:
            return
        prior.normative_text = _clean(f"{prior.normative_text} {text}")
        prior.source_segments.append(RequirementSourceSpan(
            "requirement_continuation", page.page_index, bbox, text, ids
        ))


def assemble_native_requirements(
    pages: Sequence[NativePage],
    selected_indices: Iterable[int] | None = None,
    family: TemplateFamily | str | Mapping[int, TemplateFamily | str] | None = None,
    *,
    include_preceding_context: bool = True,
) -> list[NativeRequirement]:
    return NativeRequirementAssembler().assemble(
        pages,
        selected_indices,
        family,
        include_preceding_context=include_preceding_context,
    )


def _pages_with_preceding_context(
    pages: Sequence[NativePage],
    selected: set[int],
) -> list[NativePage]:
    """Return selected pages plus one real, consecutive predecessor per run."""

    by_index = {page.page_index: page for page in pages}
    included = set(selected)
    for page_index in selected:
        if page_index - 1 not in selected and page_index - 1 in by_index:
            included.add(page_index - 1)
    return [page for page in pages if page.page_index in included]


def _link_audit_instruction_blocks(
    requirements: Sequence[NativeRequirement],
    pages: Sequence[NativePage],
) -> list[NativeRequirement]:
    """Attach source-visible Note/Instruction blocks to their proven owner.

    Explicit ``Indicator N.N.N`` ownership wins.  A plain ``Note:`` may bind
    only to the immediately following audit row on the same page and within a
    small vertical gap.  This keeps guidance outside ``normative_text`` and
    action columns while preserving it as related, auditable evidence.
    """

    by_id = {
        item.requirement_id: item
        for item in requirements
        if item.family is TemplateFamily.AUDIT_MATRIX
    }
    if not by_id:
        return list(requirements)

    additions: dict[str, list[RequirementSourceSpan]] = {}
    for page in pages:
        lines = _line_units(page)
        for index, line in enumerate(lines):
            if not _ACTION_CONTEXT_BOUNDARY_RE.match(_clean(line.text)):
                continue
            units = [line]
            previous = line
            for candidate in lines[index + 1 :]:
                if candidate.y0 <= previous.y0:
                    continue
                if _ACTION_CONTEXT_BOUNDARY_RE.match(_clean(candidate.text)):
                    break
                if _INSTRUCTION_BLOCK_END_RE.match(_clean(candidate.text)):
                    break
                if candidate.y0 - previous.y1 > 9.0:
                    break
                units.append(candidate)
                previous = candidate

            source_text = "\n".join(unit.text for unit in units).strip()
            owner_match = _EXPLICIT_INSTRUCTION_OWNER_RE.search(source_text)
            owner_id = owner_match.group("id") if owner_match else None
            if owner_id not in by_id:
                owner_id = _nearest_following_audit_requirement(
                    by_id.values(), page.page_index, max(unit.y1 for unit in units)
                )
            if owner_id is None:
                continue
            span = _span("instruction", page, units, source_text)
            additions.setdefault(owner_id, []).append(span)

    result: list[NativeRequirement] = []
    for requirement in requirements:
        spans = additions.get(requirement.requirement_id, [])
        if not spans:
            result.append(requirement)
            continue
        identities = {
            (span.page_index, span.native_object_ids)
            for span in requirement.source_segments
        }
        unique = [
            span for span in spans
            if (span.page_index, span.native_object_ids) not in identities
        ]
        result.append(replace(
            requirement,
            source_segments=[*requirement.source_segments, *unique],
        ))
    return result


def _nearest_following_audit_requirement(
    requirements: Iterable[NativeRequirement],
    page_index: int,
    block_bottom: float,
) -> str | None:
    candidates = [
        (min(span.bbox[1] for span in item.source_segments), item.requirement_id)
        for item in requirements
        if any(span.page_index == page_index for span in item.source_segments)
        and min(span.bbox[1] for span in item.source_segments) >= block_bottom
    ]
    if not candidates:
        return None
    top, requirement_id = min(candidates)
    return requirement_id if top - block_bottom <= 24.0 else None


def _project_requirements_to_selected_pages(
    requirements: Sequence[NativeRequirement],
    selected: set[int],
) -> list[NativeRequirement]:
    """Keep direct evidence inside the requested window without losing identity.

    A Requirement that starts immediately before the window is represented by
    selected-page continuation spans plus one supporting ``continuation_anchor``
    copied from the real preceding-page ID object.  The anchor is context, not
    direct Requirement provenance, and no off-window normative text is copied.
    """

    result: list[NativeRequirement] = []
    for requirement in requirements:
        visible = [
            span for span in requirement.source_segments
            if span.page_index in selected
        ]
        if not visible:
            continue
        if len(visible) == len(requirement.source_segments):
            result.append(requirement)
            continue

        visible_formal = [
            span for span in visible
            if span.role in {
                "indicator_text",
                "requirement_value",
                "normative_text",
                "requirement_continuation",
            }
        ]
        if not visible_formal:
            continue
        visible_id = next(
            (span for span in visible if span.role == "requirement_id"),
            None,
        )
        source_segments = list(visible)
        if visible_id is None:
            prior_id = next(
                (
                    span for span in requirement.source_segments
                    if span.role == "requirement_id"
                    and span.page_index < min(selected)
                ),
                None,
            )
            if prior_id is None:
                continue
            source_segments.insert(
                0,
                replace(prior_id, role="continuation_anchor"),
            )

        normative_text = "\n".join(
            span.source_text for span in visible_formal if span.source_text.strip()
        )
        applicability_span = next(
            (span for span in visible if span.role == "applicability"),
            None,
        )
        result.append(replace(
            requirement,
            normative_text=normative_text,
            indicator_text=(
                requirement.requirement_id
                if requirement.family is TemplateFamily.SINGLE_COLUMN_INDICATORS
                and visible_id is None
                else requirement.indicator_text
            ),
            applicability=(
                _strip_label(
                    applicability_span.source_text,
                    "Indicator applicability",
                )
                if applicability_span is not None
                else None
            ),
            source_segments=source_segments,
        ))
    return result


def _single_column_page_top_continuation_spans(
    page: NativePage,
) -> list[RequirementSourceSpan]:
    anchors = _id_anchors(page)
    if not anchors:
        return []
    first_anchor_y = anchors[0].y0
    words = [
        word for word in _word_units(page)
        if word.x0 >= page.width_points * 0.15
        and page.height_points * 0.06 <= word.cy < first_anchor_y - 2
    ]
    markers = sorted(
        (
            word for word in words
            if re.fullmatch(r"[a-z]\.", word.text)
            and word.x0 < page.width_points * 0.30
        ),
        key=lambda word: (word.y0, word.x0),
    )
    if not markers:
        return []

    spans: list[RequirementSourceSpan] = []
    for position, marker in enumerate(markers):
        end = (
            markers[position + 1].y0 - 1
            if position + 1 < len(markers)
            else first_anchor_y - 2
        )
        group = [
            word for word in words
            if marker.y0 - 2 <= word.cy < end
        ]
        source_text = _words_source_text(group, set())
        if not source_text:
            return []
        spans.append(RequirementSourceSpan(
            role="requirement_continuation",
            page_index=page.page_index,
            bbox=_union_boxes(word.bbox for word in group),
            source_text=source_text,
            native_object_ids=tuple(word.id for word in group),
        ))
    return spans


def _leading_alphabetic_clause_marker(text: str) -> str | None:
    match = re.match(r"^([a-z])\.\s+", _clean(text))
    return match.group(1) if match else None


def _alphabetic_clause_markers(text: str) -> list[str]:
    return re.findall(r"(?:^|\s)([a-z])\.\s+", _clean(text))


def _is_next_requirement_id(previous: str, current: str) -> bool:
    try:
        prior_parts = [int(value) for value in previous.split(".")]
        current_parts = [int(value) for value in current.split(".")]
    except ValueError:
        return False
    return (
        len(prior_parts) == len(current_parts)
        and prior_parts[:-1] == current_parts[:-1]
        and current_parts[-1] == prior_parts[-1] + 1
    )


def _coerce_family(value: TemplateFamily | str | None) -> TemplateFamily | None:
    if value is None or isinstance(value, TemplateFamily):
        return value
    return TemplateFamily(value)


def _clean(text: str) -> str:
    cleaned = _SPACE_RE.sub(" ", text).strip()
    cleaned = re.sub(r"\s+([,.;:!?%\)\]\}])", r"\1", cleaned)
    cleaned = re.sub(r"([\(\[\{])\s+", r"\1", cleaned)
    # Comparator spacing is source evidence.  Do not rewrite ``≥ 6`` to
    # ``≥6`` here, and never fuse adjacent numeric tokens such as ``≥ 6 15%``.
    # Consumers that need a normalized comparator/value pair do that in the
    # semantics layer while retaining the exact native span.
    cleaned = re.sub(r"(?<=\w)-\s+(?=\w)", "-", cleaned)
    cleaned = re.sub(r"([μµ])\s+(?=[A-Za-z])", r"\1", cleaned)
    # A straight apostrophe can be a quote delimiter or part of a word.
    # Normalize only balanced quoted spans so the surrounding word boundary
    # remains visible: ``an ' Acceptable ' status`` becomes
    # ``an 'Acceptable' status`` rather than ``an'Acceptable'status``.
    cleaned = re.sub(
        r"(?<!\w)'\s*([^'\n]+?)\s*'(?!\w)",
        lambda match: f"'{match.group(1).strip()}'",
        cleaned,
    )
    cleaned = re.sub(r"([‘“])\s+", r"\1", cleaned)
    return re.sub(r"\s+([’”])", r"\1", cleaned)


def _word_units(page: NativePage) -> list[_Unit]:
    return [
        _Unit(word.id, _clean(word.text), word.bbox_points, word.font_name)
        for word in page.words if _clean(word.text)
    ]


def _line_units(page: NativePage) -> list[_Unit]:
    native = [
        _Unit(line.id, _clean(line.text), line.bbox_points, line.font_name)
        for line in page.text_lines if _clean(line.text)
    ]
    if native:
        return sorted(native, key=lambda item: (item.y0, item.x0))
    words = _word_units(page)
    if not words:
        return []
    tolerance = max(1.5, median(word.y1 - word.y0 for word in words) * 0.55)
    rows: list[list[_Unit]] = []
    for word in sorted(words, key=lambda item: (item.cy, item.x0)):
        if not rows or abs(median(item.cy for item in rows[-1]) - word.cy) > tolerance:
            rows.append([word])
        else:
            rows[-1].append(word)
    return [
        _Unit(
            f"derived-line-{index}",
            _join_units(row),
            _union_boxes(item.bbox for item in row),
        )
        for index, row in enumerate(rows)
    ]


def _id_anchors(page: NativePage) -> list[_Unit]:
    anchors = [
        word for word in _word_units(page)
        if _ID_RE.fullmatch(word.text)
        and word.x0 < page.width_points * 0.13
        and word.y0 < page.height_points * 0.9
    ]
    result: list[_Unit] = []
    for anchor in sorted(anchors, key=lambda item: (item.y0, item.x0)):
        if result and anchor.text == result[-1].text and abs(anchor.y0 - result[-1].y0) < 2:
            continue
        result.append(anchor)
    return result


def _body_end(page: NativePage, lines: list[_Unit]) -> float:
    footer_starts = [
        line.y0 for line in lines
        if line.y0 > page.height_points * 0.78
        and (
            _clean(line.text).casefold().startswith("document name")
            or re.match(r"^page \d+ of \d+$", _clean(line.text), re.IGNORECASE)
            or "copyright" in _clean(line.text).casefold()
        )
    ]
    return min([page.height_points * 0.9, *footer_starts])


def _formal_section_end(page: NativePage, lines: list[_Unit], after_y: float) -> float:
    section_starts = [
        line.y0 for line in lines
        if line.y0 > after_y + 2
        and re.match(
            r"^(rationale|criterion\b|principle\b|intent\b|how do i interpret)",
            _clean(line.text),
            re.IGNORECASE,
        )
    ]
    end = min(section_starts, default=_body_end(page, lines))
    candidate_lines = sorted(
        (
            line for line in lines
            if after_y - 2 <= line.y0 < end and line.x1 >= page.width_points * 0.15
        ),
        key=lambda line: line.y0,
    )
    for prior, current in zip(candidate_lines, candidate_lines[1:]):
        if current.y0 - prior.y1 > 45:
            end = min(end, current.y0)
            break
    return end


def _words_text_bbox(
    words: Sequence[_Unit],
) -> tuple[str, tuple[float, float, float, float], tuple[str, ...]]:
    if not words:
        return "", (0.0, 0.0, 0.0, 0.0), ()
    rows = _word_rows(words)
    row_texts = [_word_row_text(row) for row in rows]
    text = _clean(" ".join(row_texts))
    return text, _union_boxes(word.bbox for word in words), tuple(word.id for word in words)


def _word_rows(words: Sequence[_Unit]) -> list[list[_Unit]]:
    if not words:
        return []
    heights = [word.y1 - word.y0 for word in words]
    tolerance = max(1.5, median(heights) * 0.6)
    rows: list[list[_Unit]] = []
    for word in sorted(words, key=lambda item: (item.cy, item.x0)):
        if not rows or abs(median(item.cy for item in rows[-1]) - word.cy) > tolerance:
            rows.append([word])
        else:
            rows[-1].append(word)
    return rows


def _single_column_applicability_words(
    words: Sequence[_Unit],
    lines: Sequence[_Unit],
) -> list[_Unit]:
    if not words:
        return []
    y0 = min(word.y0 for word in words)
    y1 = max(word.y1 for word in words)
    relevant_lines = [line for line in lines if y0 - 2 <= line.cy <= y1 + 2]
    starts = [
        line for line in relevant_lines
        if _clean(line.text).casefold().startswith("indicator applicability:")
    ]
    if not starts:
        return []
    start = min(starts, key=lambda line: line.y0)
    modal_lines = [
        line for line in relevant_lines
        if line.y0 > start.y0 and _FORMAL_MODAL_RE.search(_clean(line.text))
    ]
    if not modal_lines:
        return []
    modal_start = min(line.y0 for line in modal_lines)
    return [word for word in words if start.y0 - 2 <= word.cy < modal_start]


def _legacy_superscript_hosts(words: Sequence[_Unit]) -> dict[str, _Unit]:
    """Bind small numeric footnote markers to their visual host word.

    Legacy table rows can begin below a superscript's own centre point.  Row
    ownership must therefore follow the normal-size host word rather than the
    marker's ``cy``.  Bounding-box height is the native extractor's reliable
    proxy for font size; tight horizontal adjacency and top/baseline geometry
    keep ordinary body numbers out of this mapping.
    """
    result: dict[str, _Unit] = {}
    for marker in words:
        if not _FOOTNOTE_MARKER_RE.fullmatch(marker.text):
            continue
        marker_height = marker.y1 - marker.y0
        candidates: list[tuple[float, float, _Unit]] = []
        for host in words:
            if host.id == marker.id:
                continue
            host_height = host.y1 - host.y0
            if host_height <= 0 or marker_height > host_height * 0.78:
                continue
            gap = marker.x0 - host.x1
            if not (-max(1.5, host_height * 0.12) <= gap <= max(3.0, host_height * 0.35)):
                continue
            if marker.y0 < host.y0 - max(1.0, host_height * 0.1):
                continue
            if marker.y1 > host.y1 + max(1.0, host_height * 0.1):
                continue
            top_offset = abs(marker.y0 - host.y0)
            if top_offset > max(1.5, host_height * 0.35):
                continue
            candidates.append((abs(gap), top_offset, host))
        if candidates:
            result[marker.id] = min(candidates, key=lambda item: item[:2])[2]
    return result


def _semantic_marker_candidates(
    words: Sequence[_Unit],
) -> tuple[list[_Unit], list[_Unit]]:
    list_markers: list[_Unit] = []
    footnote_markers: list[_Unit] = []
    for row in _word_rows(words):
        ordinary = [word for word in row if not _is_list_marker_glyph(word, row)]
        ordinary_heights = [word.y1 - word.y0 for word in ordinary]
        base_height = median(ordinary_heights) if ordinary_heights else 0.0
        for word in row:
            if _is_list_marker_glyph(word, row):
                list_markers.append(word)
                continue
            height = word.y1 - word.y0
            has_left_neighbor = any(other.x1 <= word.x0 + 1 for other in row if other is not word)
            if (
                _FOOTNOTE_MARKER_RE.fullmatch(word.text)
                and base_height > 0
                and height <= base_height * 0.78
                and has_left_neighbor
            ):
                footnote_markers.append(word)
    return list_markers, footnote_markers


def _is_list_marker_glyph(word: _Unit, row: Sequence[_Unit]) -> bool:
    glyphs = {"o", "•", "●", "▪", "◦", "○"}
    if word.text not in glyphs:
        return False
    font = (word.font_name or "").casefold()
    is_symbolic_font = "courier" in font or "symbol" in font or "wingdings" in font
    is_nonalpha_glyph = not word.text.isalpha()
    has_right_neighbor = any(other.x0 > word.x1 for other in row if other is not word)
    return has_right_neighbor and (is_symbolic_font or is_nonalpha_glyph)


def _words_source_text(words: Sequence[_Unit], attached_ids: set[str]) -> str:
    row_texts: list[str] = []
    for row in _word_rows(words):
        text = _word_row_text(row, attached_ids=attached_ids)
        if text:
            row_texts.append(text)
    return _clean(" ".join(row_texts))


def _word_row_text(
    row: Sequence[_Unit],
    *,
    attached_ids: set[str] | None = None,
) -> str:
    """Reconstruct one visual row without generic numeric token fusion.

    A few native PDFs split one printed token into adjacent text objects, for
    example ``≥1`` and ``5%`` whose boxes are only 0.06 pt apart.  Join only
    when both the near-zero physical gap and the complete token morphology
    agree.  Ordinary numeric objects keep their source-visible space.
    """

    attached = attached_ids or set()
    ordered = sorted(row, key=lambda item: item.x0)
    if not ordered:
        return ""
    result = ordered[0].text
    prior = ordered[0]
    for current in ordered[1:]:
        join = current.id in attached or _touching_percentage_token(prior, current)
        result += ("" if join else " ") + current.text
        prior = current
    return result


def _touching_percentage_token(left: _Unit, right: _Unit) -> bool:
    gap = right.x0 - left.x1
    height = max(1.0, min(left.y1 - left.y0, right.y1 - right.y0))
    if not (-0.25 <= gap <= min(0.65, height * 0.06)):
        return False
    return bool(re.fullmatch(
        r"(?:[≤≥<>]=?)?\d+(?:[.,]\d+)?%",
        f"{left.text}{right.text}",
    ))


def _union_boxes(
    boxes: Iterable[tuple[float, float, float, float]],
) -> tuple[float, float, float, float]:
    materialized = list(boxes)
    if not materialized:
        return (0.0, 0.0, 0.0, 0.0)
    return (
        min(box[0] for box in materialized),
        min(box[1] for box in materialized),
        max(box[2] for box in materialized),
        max(box[3] for box in materialized),
    )


def _span(
    role: str,
    page: NativePage,
    units: Sequence[_Unit],
    source_text: str,
) -> RequirementSourceSpan:
    return RequirementSourceSpan(
        role=role,
        page_index=page.page_index,
        bbox=_union_boxes(unit.bbox for unit in units),
        source_text=source_text,
        native_object_ids=tuple(unit.id for unit in units),
    )


def _join_units(units: Sequence[_Unit]) -> str:
    return _clean(" ".join(unit.text for unit in sorted(units, key=lambda item: (item.y0, item.x0))))


def _strip_label(text: str, label: str) -> str:
    return re.sub(rf"^{re.escape(label)}\s*:\s*", "", text, flags=re.IGNORECASE).strip()


def _audit_label_positions(lines: Sequence[_Unit], width: float) -> dict[str, float]:
    result: dict[str, float] = {}
    for line in lines:
        if line.x0 >= width * 0.31:
            continue
        normalized = _clean(line.text).casefold()
        for label in ("indicator", "requirement", "applicability"):
            if normalized == label or normalized.startswith(f"{label}:"):
                result.setdefault(label, line.y0)
    return result


def _audit_row_starts(
    anchors: Sequence[_Unit],
    lines: Sequence[_Unit],
    width: float,
) -> list[float]:
    starts: list[float] = []
    for position, anchor in enumerate(anchors):
        floor = anchors[position - 1].cy if position else 0.0
        indicator_candidates = [
            line.y0 for line in lines
            if floor < line.cy <= anchor.cy + 5
            and line.x0 < width * 0.31
            and (
                _clean(line.text).casefold() in {"indicator", "indicator:"}
                or _clean(line.text).casefold().startswith("indicator:")
            )
        ]
        indicator_y = max(indicator_candidates, default=anchor.y0)
        action_floor = max(floor + 1, indicator_y - width * 0.20)
        client_candidates = [
            line.y0 for line in lines
            if action_floor <= line.cy <= anchor.cy + 50
            and _CLIENT_MARKER_RE.match(line.text)
            and line.text.startswith("a.")
            and width * 0.31 <= line.x0 < width * 0.61
        ]
        auditor_candidates = [
            line.y0 for line in lines
            if action_floor <= line.cy <= anchor.cy + 50
            and _AUDITOR_GEOMETRIC_MARKER_RE.match(line.text)
            and line.text[:2].casefold() == "a."
            and line.x0 >= width * 0.61
        ]
        nearest_client = min(
            client_candidates, key=lambda y: abs(y - indicator_y), default=indicator_y
        )
        nearest_auditor = min(
            auditor_candidates, key=lambda y: abs(y - indicator_y), default=indicator_y
        )
        starts.append(min(indicator_y, nearest_client, nearest_auditor))
    return starts


def _audit_field_units(
    lines: Sequence[_Unit],
    start: float,
    end: float,
    width: float,
) -> list[_Unit]:
    return [
        line for line in lines
        if line.x0 < width * 0.31
        and not _ID_RE.fullmatch(_clean(line.text))
        and _clean(line.text).casefold() != "footnote"
        and start - 1 <= line.cy < end
    ]


def _audit_footnote_groups(
    lines: Sequence[_Unit], width: float
) -> list[list[_Unit]]:
    """Recover table-internal footnote rows without treating anchors as fields.

    Legacy audit matrices place a literal ``Footnote`` cell beside one or
    more ``[NN] ...`` body lines.  The label can be vertically centred across
    a multi-line body, so the first body line may precede the label.  A bracket
    marker is therefore accepted only when a visible ``Footnote`` label is
    nearby.  This prevents inline anchors such as ``[55] for the fishery``
    inside an Indicator cell from being promoted to definitions.
    """

    ordered = sorted(lines, key=lambda item: (item.y0, item.x0))
    labels = [
        line for line in ordered
        if line.x0 < width * 0.13
        and _clean(line.text).casefold() == "footnote"
    ]
    starts = [
        line for line in ordered
        if width * 0.125 <= line.x0 < width * 0.31
        and _AUDIT_FOOTNOTE_BODY_RE.match(_clean(line.text))
        and any(abs(line.cy - label.cy) <= 12.0 for label in labels)
    ]
    if not starts:
        return []

    groups: list[list[_Unit]] = []
    for position, start in enumerate(starts):
        next_start_y = (
            starts[position + 1].y0 if position + 1 < len(starts) else float("inf")
        )
        group: list[_Unit] = []
        prior_y1 = start.y1
        for line in ordered:
            if line.y0 < start.y0 - 1 or line.y0 >= next_start_y - 1:
                continue
            text = _clean(line.text)
            normalized = text.casefold()
            if normalized == "footnote":
                continue
            if line is not start and (
                normalized.startswith(("indicator", "requirement", "applicability"))
                or normalized.startswith(("criterion ", "principle "))
                or _CLIENT_MARKER_RE.match(text)
                or _AUDITOR_MARKER_RE.match(text)
            ):
                break
            if line is not start and line.y0 - prior_y1 > 8.0:
                break
            if line.x0 >= width * 0.125:
                group.append(line)
                prior_y1 = max(prior_y1, line.y1)
        if group:
            groups.append(group)
    return groups


def _bracket_footnote_markers(*texts: str) -> list[str]:
    result: list[str] = []
    for text in texts:
        for match in _BRACKET_FOOTNOTE_ANCHOR_RE.finditer(text):
            marker = match.group(1)
            if marker not in result:
                result.append(marker)
    return result


def _split_actions(units: Sequence[_Unit], marker: re.Pattern[str]) -> list[str]:
    return [text for text, _units in _split_action_groups(units, marker)]


def _split_action_groups(
    units: Sequence[_Unit], marker: re.Pattern[str]
) -> list[tuple[str, list[_Unit]]]:
    actions: list[tuple[str, list[_Unit]]] = []
    current: list[_Unit] = []
    in_context = False
    for unit in sorted(units, key=lambda item: (item.y0, item.x0)):
        text = _clean(unit.text)
        if current and _ACTION_SECTION_HEADER_RE.search(text):
            break
        if _ACTION_CONTEXT_BOUNDARY_RE.match(text):
            if current:
                actions.append((_semantic_action_text(current), current))
            current = []
            in_context = True
            continue
        if text in {"-", "–", "—"}:
            continue
        if marker.match(text):
            if current:
                actions.append((
                    _semantic_action_text(current),
                    current,
                ))
            current = [unit]
            in_context = False
        elif current and not in_context:
            current.append(unit)
    if current:
        actions.append((
            _semantic_action_text(current),
            current,
        ))
    return actions


def _semantic_action_text(units: Sequence[_Unit]) -> str:
    parts: list[str] = []
    for position, unit in enumerate(units):
        text = _clean(unit.text)
        if position > 0:
            text = _ACTION_LIST_MARKER_RE.sub("", text, count=1)
        if text:
            parts.append(text)
    return _clean(" ".join(parts))


def _trim_action_units(
    units: Sequence[_Unit], marker: re.Pattern[str]
) -> list[_Unit]:
    ordered = sorted(units, key=lambda item: (item.y0, item.x0))
    first = next((index for index, unit in enumerate(ordered) if marker.match(unit.text)), None)
    return ordered[first:] if first is not None else []


def _word_line_starts_with(word: _Unit, lines: Sequence[_Unit], prefix: str) -> bool:
    return any(
        line.y0 - 1 <= word.cy <= line.y1 + 1
        and _clean(line.text).casefold().startswith(prefix)
        for line in lines
    )
