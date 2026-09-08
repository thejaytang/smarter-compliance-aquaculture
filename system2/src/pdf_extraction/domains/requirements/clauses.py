from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal

from ...models import RequirementClause
from .native_assembler import NativeRequirement, TemplateFamily


_MARKER_RE = re.compile(
    r"(?<!\S)(?P<marker>"
    r"(?:\((?:[A-Za-z]|[1-9]\d*|[ivxlcdmIVXLCDM]{2,})\)|"
    r"[A-Za-z]\.|[1-9]\d*[.)]|"
    r"[ivxlcdmIVXLCDM]{2,}[.)]|"
    r"[o•●▪◦○\-–—]))(?=\s)"
)
_SPACE_RE = re.compile(r"\s+")
_TRAILING_JOIN_RE = re.compile(
    r"^(?P<body>.*?)(?:\s+(?P<join>and|or)\s*,?)\s*$",
    re.IGNORECASE | re.DOTALL,
)
_ROMAN_RE = re.compile(r"^[ivxlcdm]+$", re.IGNORECASE)


@dataclass(frozen=True)
class ClauseBuildResult:
    clauses: tuple[RequirementClause, ...]
    requires_review: bool = False
    anomalies: tuple[str, ...] = ()
    validation_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class _Marker:
    start: int
    end: int
    raw: str
    kind: Literal["alpha", "numeric", "roman", "bullet"]
    ordinal: int | None


@dataclass
class _Node:
    clause_id: str
    parent_clause_id: str
    marker: str
    text: str
    level: int
    ancestors: list[int]
    explicit_join: Literal["and", "or"] | None = None
    joins_next: Literal["and", "or"] | None = None


def build_requirement_clauses(
    native: NativeRequirement,
    normative_text: str,
) -> ClauseBuildResult:
    """Build only clause structure directly evidenced by source formatting.

    A Requirement without a visually explicit list receives one exact root
    clause.  A list is split only when a source marker run follows a visible
    colon and the marker order and parent transitions are deterministic.
    Anything more ambiguous keeps that exact root and lowers the Requirement
    to review instead of inventing logical structure.
    """

    exact_text = normative_text.strip()
    if not exact_text:
        return ClauseBuildResult(clauses=())

    root_id = f"{_safe_requirement_id(native.requirement_id)}-main"
    exact_root = RequirementClause(clause_id=root_id, text=exact_text)
    source = _structural_source(native)
    if not source:
        return _unresolved(exact_root, "formal_source_missing")

    source = _strip_attached_footnotes(source, native.footnote_markers)
    markers = _markers(source)
    if not markers:
        sentences = re.split(
            r'(?<=[.!?])\s+(?=(?:In\s+cases\s+where|If|When|Provided\s+that|Hvis|Dersom|Når)\b)',
            exact_text,
            flags=re.IGNORECASE,
        )
        if len(sentences) > 1 and all(
            re.search(r'\b(?:shall|must|skal|må)\b', part, re.IGNORECASE)
            for part in sentences
        ):
            return ClauseBuildResult(
                clauses=tuple(RequirementClause(
                    clause_id=f'{root_id}-{index + 1}', text=part,
                ) for index, part in enumerate(sentences)),
                validation_flags=('clause_structure:conditional_sentences_source_faithful',),
            )
        return ClauseBuildResult(
            clauses=(exact_root,),
            validation_flags=("clause_structure:single_root_source_faithful",),
        )

    first = markers[0]
    prefix = _clean_clause_text(source[: first.start])
    strong_run = _looks_like_marker_run(markers)
    if not prefix.endswith(":"):
        if strong_run:
            return _unresolved(exact_root, "list_root_not_explicit")
        return ClauseBuildResult(
            clauses=(exact_root,),
            validation_flags=("clause_structure:single_root_source_faithful",),
        )

    if not prefix or not _ordered_source_support(prefix, exact_text, start=0):
        return _unresolved(exact_root, "list_root_not_source_aligned")

    nodes_or_reason = _build_nodes(
        source,
        markers,
        requirement_id=_safe_requirement_id(native.requirement_id),
        root_id=root_id,
    )
    if isinstance(nodes_or_reason, str):
        return _unresolved(exact_root, nodes_or_reason)
    nodes = nodes_or_reason
    if not nodes:
        return _unresolved(exact_root, "list_items_missing")

    # Every emitted text fragment must appear in the canonical normative text
    # in the same order.  This is the source-faithfulness guard against a
    # marker-looking token inside ordinary prose.
    cursor = 0
    for fragment in [prefix, *(node.text for node in nodes)]:
        cursor = _ordered_source_support(fragment, exact_text, start=cursor)
        if cursor < 0:
            return _unresolved(exact_root, "list_item_not_source_aligned")

    clauses = [RequirementClause(clause_id=root_id, text=prefix)]
    clauses.extend(
        RequirementClause(
            clause_id=node.clause_id,
            parent_clause_id=node.parent_clause_id,
            marker=node.marker,
            text=node.text,
            joins_next=node.joins_next,
        )
        for node in nodes
    )
    return ClauseBuildResult(
        clauses=tuple(clauses),
        validation_flags=("clause_structure:explicit_list_source_faithful",),
    )


def _structural_source(native: NativeRequirement) -> str:
    if native.family in {
        TemplateFamily.LEGACY_INDICATOR_VALUE,
        TemplateFamily.AUDIT_MATRIX,
    }:
        roles = {"indicator_text"}
    else:
        roles = {"normative_text", "requirement_continuation"}
    material = [
        span.source_text.strip()
        for span in native.source_segments
        if span.role in roles and span.source_text.strip()
    ]
    if (
        native.family is TemplateFamily.AUDIT_MATRIX
        and not material
        and native.indicator_text
        and any(
            native.indicator_text in span.source_text
            for span in native.source_segments
            if span.role == "normative_text"
        )
    ):
        return native.indicator_text.strip()
    return " ".join(material).strip()


def _markers(source: str) -> list[_Marker]:
    raw_matches = [
        match
        for match in _MARKER_RE.finditer(source)
        if not _reference_roman_marker(source, match)
    ]
    if not raw_matches:
        return []
    raw_values = [match.group("marker") for match in raw_matches]
    roman_flags = _roman_marker_flags(raw_values)
    result: list[_Marker] = []
    for index, match in enumerate(raw_matches):
        raw = match.group("marker")
        core = raw.strip("().")
        if raw in {"o", "•", "●", "▪", "◦", "○", "-", "–", "—"}:
            kind: Literal["alpha", "numeric", "roman", "bullet"] = "bullet"
            ordinal = None
        elif core.isdigit():
            kind = "numeric"
            ordinal = int(core)
        elif roman_flags[index]:
            kind = "roman"
            ordinal = _roman_value(core)
        else:
            kind = "alpha"
            ordinal = ord(core.casefold()) - ord("a") + 1
        result.append(_Marker(
            start=match.start(),
            end=match.end(),
            raw=raw,
            kind=kind,
            ordinal=ordinal,
        ))
    return result


def _reference_roman_marker(source: str, match: re.Match[str]) -> bool:
    core = match.group("marker").strip("().")
    if not (len(core) > 1 and _ROMAN_RE.fullmatch(core)):
        return False
    prefix = source[max(0, match.start() - 40):match.start()]
    return bool(re.search(
        r"\b(?:Appendix|Annex|Chapter|Section|Table)\s+$",
        prefix,
        re.IGNORECASE,
    ))


def _roman_marker_flags(raw_values: list[str]) -> list[bool]:
    cores = [raw.strip("().") for raw in raw_values]
    flags = [bool(len(core) > 1 and _ROMAN_RE.fullmatch(core)) for core in cores]
    for index, core in enumerate(cores):
        if len(core) != 1 or not _ROMAN_RE.fullmatch(core):
            continue
        current = _roman_value(core)
        neighbours = []
        if index:
            neighbours.append(cores[index - 1])
        if index + 1 < len(cores):
            neighbours.append(cores[index + 1])
        flags[index] = any(
            len(neighbour) > 1
            and _ROMAN_RE.fullmatch(neighbour)
            and abs(_roman_value(neighbour) - current) == 1
            for neighbour in neighbours
        )
    return flags


def _looks_like_marker_run(markers: list[_Marker]) -> bool:
    if len(markers) < 2:
        return False
    first, second = markers[:2]
    if first.kind == second.kind == "bullet":
        return True
    return (
        first.kind == second.kind
        and first.ordinal is not None
        and second.ordinal == first.ordinal + 1
    )


def _build_nodes(
    source: str,
    markers: list[_Marker],
    *,
    requirement_id: str,
    root_id: str,
) -> list[_Node] | str:
    bodies: list[tuple[str, Literal["and", "or"] | None]] = []
    for index, marker in enumerate(markers):
        end = markers[index + 1].start if index + 1 < len(markers) else len(source)
        raw_body = _clean_clause_text(source[marker.end:end])
        body, explicit_join = _split_trailing_join(raw_body)
        if not body:
            return "list_item_text_missing"
        bodies.append((body, explicit_join))

    levels: list[dict[str, object]] = []
    nodes: list[_Node] = []
    for index, (marker, (body, explicit_join)) in enumerate(zip(markers, bodies)):
        existing_level = next(
            (position for position, level in enumerate(levels) if level["kind"] == marker.kind),
            None,
        )
        if existing_level is None:
            if not levels:
                level_index = 0
                parent_id = root_id
                ancestors: list[int] = []
            else:
                prior = nodes[-1]
                if not prior.text.endswith(":"):
                    return "marker_hierarchy_ambiguous"
                level_index = len(levels)
                parent_id = prior.clause_id
                ancestors = [*prior.ancestors, len(nodes) - 1]
            levels.append({
                "kind": marker.kind,
                "last_ordinal": None,
                "parent_id": parent_id,
                "ancestors": ancestors,
            })
        else:
            level_index = existing_level
            if (
                marker.kind == "bullet"
                and nodes
                and nodes[-1].level == level_index
                and nodes[-1].text.endswith(":")
            ):
                return "same_marker_nested_list_ambiguous"
            levels = levels[: level_index + 1]
            parent_id = str(levels[level_index]["parent_id"])
            ancestors = list(levels[level_index]["ancestors"])  # type: ignore[arg-type]

        level = levels[level_index]
        prior_ordinal = level["last_ordinal"]
        if marker.ordinal is not None:
            if prior_ordinal is not None and marker.ordinal != int(prior_ordinal) + 1:
                return "marker_sequence_non_contiguous"
            level["last_ordinal"] = marker.ordinal

        path = [*(ancestor + 1 for ancestor in ancestors), index + 1]
        clause_id = f"{requirement_id}-{_path_suffix(path)}"
        nodes.append(_Node(
            clause_id=clause_id,
            parent_clause_id=parent_id,
            marker=marker.raw,
            text=body,
            level=level_index,
            ancestors=ancestors,
            explicit_join=explicit_join,
        ))

    for index, node in enumerate(nodes):
        if node.explicit_join is None:
            continue
        if index + 1 >= len(nodes):
            return "dangling_explicit_join"
        next_level = nodes[index + 1].level
        target_index = index
        if next_level < node.level:
            if next_level >= len(node.ancestors):
                return "join_parent_unresolved"
            target_index = node.ancestors[next_level]
        target = nodes[target_index]
        if target.joins_next is not None and target.joins_next != node.explicit_join:
            return "join_conflict"
        target.joins_next = node.explicit_join
    return nodes


def _split_trailing_join(
    text: str,
) -> tuple[str, Literal["and", "or"] | None]:
    match = _TRAILING_JOIN_RE.match(text)
    if not match:
        return text, None
    body = match.group("body").strip()
    join = match.group("join").casefold()
    return body, "and" if join == "and" else "or"


def _strip_attached_footnotes(text: str, markers: list[str]) -> str:
    cleaned = text
    for marker in sorted(set(markers), key=len, reverse=True):
        if not marker.isdigit():
            continue
        cleaned = re.sub(
            rf"(?<=\S){re.escape(marker)}(?=$|\s|[.,;:)\]])",
            "",
            cleaned,
        )
    return cleaned


def _ordered_source_support(fragment: str, normative_text: str, *, start: int) -> int:
    haystack = _match_text(normative_text)
    needle = _match_text(fragment)
    if not needle:
        return -1
    position = haystack.find(needle, max(0, start))
    return -1 if position < 0 else position + len(needle)


def _match_text(text: str) -> str:
    # Marker punctuation is structural, not semantic content.  Removing it in
    # the comparison lets both marker-preserving and marker-free native
    # assemblers use the same source-faithfulness gate.
    text = _MARKER_RE.sub("", text)
    return _clean_clause_text(text).casefold()


def _clean_clause_text(text: str) -> str:
    cleaned = _SPACE_RE.sub(" ", text).strip()
    cleaned = re.sub(r"\s+([,.;:!?%\)\]\}])", r"\1", cleaned)
    cleaned = re.sub(r"([\(\[\{])\s+", r"\1", cleaned)
    cleaned = re.sub(r"([≤≥])\s+(?=\d)", r"\1", cleaned)
    cleaned = re.sub(r"([≤≥<>]=?\d+)\s+(\d+%)", r"\1\2", cleaned)
    return cleaned


def _safe_requirement_id(requirement_id: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", requirement_id.strip()).strip("-")
    return cleaned or "unresolved"


def _path_suffix(path: list[int]) -> str:
    def token(value: int) -> str:
        if 1 <= value <= 26:
            return chr(ord("a") + value - 1)
        return str(value)

    return "-".join(token(value) for value in path)


def _roman_value(value: str) -> int:
    numerals = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}
    total = 0
    prior = 0
    for character in reversed(value.casefold()):
        current = numerals[character]
        if current < prior:
            total -= current
        else:
            total += current
            prior = current
    return total


def _unresolved(root: RequirementClause, reason: str) -> ClauseBuildResult:
    return ClauseBuildResult(
        clauses=(root,),
        requires_review=True,
        anomalies=(f"clause_structure_unresolved:{reason}",),
        validation_flags=("clause_structure:fail_closed",),
    )
