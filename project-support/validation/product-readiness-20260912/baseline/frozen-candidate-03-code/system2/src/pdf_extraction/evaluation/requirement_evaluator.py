from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from statistics import fmean
from typing import Any

from .metrics import normalize_text, safe_ratio
from .requirement_gold import (
    DIRECT_REQUIREMENT_ROLES,
    load_requirement_gold,
    validate_requirement_manifest,
)


CRITICAL_FIELDS = (
    "modalities",
    "negations",
    "thresholds",
    "applicability",
    "conditions",
    "exceptions",
    "exemptions",
    "dates",
    "logical_structure",
)

STRICT_SEMANTIC_FIELDS = CRITICAL_FIELDS + (
    "criterion_path",
    "normative_subjects",
    "cross_references",
    "footnote_refs",
    "associated_instructions",
)


def _ratio_or_none(
    numerator: int | float,
    denominator: int | float,
) -> float | None:
    """Return N/A for an undefined metric instead of a vacuous perfect score."""
    return numerator / denominator if denominator else None


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _gold_source_pages(requirement: dict[str, Any], gold: dict[str, Any]) -> set[int]:
    segment_by_id = {item["segment_id"]: item for item in gold["segments"]}
    return {
        segment_by_id[segment_id]["page_index"]
        for segment_id in requirement["source_segment_ids"]
    }


def _bbox_values(value: Any) -> tuple[float, float, float, float] | None:
    if isinstance(value, dict):
        values = tuple(value.get(key) for key in ("x0", "y0", "x1", "y1"))
    elif isinstance(value, (list, tuple)) and len(value) == 4:
        values = tuple(value)
    else:
        return None
    if not all(isinstance(item, (int, float)) for item in values):
        return None
    x0, y0, x1, y1 = (float(item) for item in values)
    if x1 <= x0 or y1 <= y0:
        return None
    return x0, y0, x1, y1


def _bbox_iou(left: Any, right: Any) -> float:
    left_box = _bbox_values(left)
    right_box = _bbox_values(right)
    if left_box is None or right_box is None:
        return 0.0
    lx0, ly0, lx1, ly1 = left_box
    rx0, ry0, rx1, ry1 = right_box
    intersection = max(0.0, min(lx1, rx1) - max(lx0, rx0)) * max(
        0.0, min(ly1, ry1) - max(ly0, ry0)
    )
    if not intersection:
        return 0.0
    left_area = (lx1 - lx0) * (ly1 - ly0)
    right_area = (rx1 - rx0) * (ry1 - ry0)
    return intersection / (left_area + right_area - intersection)


def _prediction_source_segments(
    prediction: dict[str, Any],
    requirement: dict[str, Any],
) -> list[dict[str, Any]]:
    inline = requirement.get("source_segments")
    if isinstance(inline, list) and all(isinstance(item, dict) for item in inline):
        return inline
    segment_by_id = {
        str(item.get("segment_id", item.get("id"))): item
        for item in prediction.get("segments", [])
        if isinstance(item, dict) and (item.get("segment_id") or item.get("id"))
    }
    return [
        segment_by_id[str(segment_id)]
        for segment_id in requirement.get("source_segment_ids", [])
        if str(segment_id) in segment_by_id
    ]


def _prediction_direct_segments(
    prediction: dict[str, Any],
    requirement: dict[str, Any],
    *,
    selected_page_indices: set[int] | None = None,
) -> list[dict[str, Any]]:
    """Return only evidence roles that constitute the Requirement itself.

    Criterion headings, guidance and client/auditor actions are related
    evidence, but their pages must not widen the direct Requirement provenance
    set used for exact page/segment acceptance.
    """

    return [
        segment
        for segment in _prediction_source_segments(prediction, requirement)
        if segment.get("role") in DIRECT_REQUIREMENT_ROLES
        and (
            selected_page_indices is None
            or _segment_page_index(segment) in selected_page_indices
        )
    ]


def _segment_page_index(segment: dict[str, Any]) -> int | None:
    page_index = segment.get("page_index")
    if isinstance(page_index, int):
        return page_index
    page_number = segment.get("page_number")
    return page_number - 1 if isinstance(page_number, int) else None


_BULLET_GLYPHS = frozenset("•◦▪▫‣⁃●○")
_QUOTE_GLYPHS = frozenset("'\"‘’‚‛“”„‟")
_LINE_BREAK_HYPHEN_RE = re.compile(
    r"(?<=[^\W\d_])(?:-|\u00ad)[ \t]*(?:\r\n|\r|\n)[ \t]*(?=[^\W\d_])"
)


def _normalize_direct_provenance_text(value: Any) -> str:
    """Normalize only source-rendering typography for direct provenance.

    The evaluator deliberately preserves every letter, digit and substantive
    punctuation mark.  It only canonicalizes rendering differences that can
    be introduced by PDF text objects: bullet shape/spacing, quotation glyph
    style, en/em dash glyphs, comparison-operator spacing and a word split by
    a line-break hyphen.
    """

    text = "" if value is None else str(value)
    text = _LINE_BREAK_HYPHEN_RE.sub("", text)
    text = text.translate(str.maketrans({"–": "-", "—": "-"}))

    # Preserve the presence and position of quote punctuation while treating
    # smart/straight and single/double source-rendering variants alike.  An
    # apostrophe embedded between alphanumeric characters remains an
    # apostrophe, so contractions and possessives are not erased.
    characters: list[str] = []
    for index, character in enumerate(text):
        if character in _BULLET_GLYPHS:
            characters.append("•")
            continue
        if character not in _QUOTE_GLYPHS:
            characters.append(character)
            continue
        previous = text[index - 1] if index else ""
        following = text[index + 1] if index + 1 < len(text) else ""
        if character in "'‘’‚‛" and previous.isalnum() and following.isalnum():
            characters.append("'")
        else:
            characters.append('"')
    text = "".join(characters)

    # Canonical spacing rules retain the operator/punctuation itself.  They do
    # not make missing or changed punctuation compare equal.
    text = re.sub(r"\s*(<=|>=|[<>≤≥])\s*", r"\1", text)
    text = re.sub(r"\s*•\s*", "•", text)
    text = re.sub(r"\s*:\s*", ":", text)
    text = re.sub(r"\s*\"\s*", '"', text)
    text = re.sub(r"(?<=[^\W\d_])-\s+(?=[^\W\d_])", "-", text)
    return normalize_text(text)


def _gold_direct_segments(
    requirement: dict[str, Any], gold: dict[str, Any]
) -> list[dict[str, Any]]:
    segment_by_id = {item["segment_id"]: item for item in gold["segments"]}
    return [
        segment_by_id[segment_id]
        for segment_id in requirement["source_segment_ids"]
        if segment_id in segment_by_id
    ]


def _maximum_direct_segment_coverage(
    gold_segments: list[dict[str, Any]],
    predicted_segments: list[dict[str, Any]],
    *,
    require_text: bool,
    require_bbox: bool,
) -> bool:
    """Return full one-to-one coverage under the requested evidence contract."""

    if not gold_segments or not predicted_segments:
        return False

    candidates_by_gold: list[list[int]] = []
    for gold_segment in gold_segments:
        candidates = []
        for index, predicted_segment in enumerate(predicted_segments):
            if (
                _segment_page_index(predicted_segment) != gold_segment["page_index"]
                or predicted_segment.get("role") != gold_segment["role"]
            ):
                continue
            if require_text and (
                _normalize_direct_provenance_text(
                    predicted_segment.get("source_text", predicted_segment.get("text"))
                )
                != _normalize_direct_provenance_text(gold_segment["source_text"])
            ):
                continue
            iou = _bbox_iou(predicted_segment.get("bbox"), gold_segment["bbox"])
            if require_bbox and iou < 0.50:
                continue
            candidates.append((index, iou))
        candidates.sort(key=lambda item: (-item[1], item[0]))
        candidates_by_gold.append([index for index, _ in candidates])

    predicted_to_gold: dict[int, int] = {}

    def assign(gold_index: int, visited: set[int]) -> bool:
        for predicted_index in candidates_by_gold[gold_index]:
            if predicted_index in visited:
                continue
            visited.add(predicted_index)
            current_gold = predicted_to_gold.get(predicted_index)
            if current_gold is None or assign(current_gold, visited):
                predicted_to_gold[predicted_index] = gold_index
                return True
        return False

    matched = 0
    for gold_index in sorted(
        range(len(gold_segments)), key=lambda index: len(candidates_by_gold[index])
    ):
        matched += assign(gold_index, set())
    return matched == len(gold_segments)


def _direct_provenance_matches(
    gold_segments: list[dict[str, Any]],
    predicted_segments: list[dict[str, Any]],
) -> tuple[bool, bool]:
    """Score text/role and bbox coverage independently, never by private IDs."""

    return (
        _maximum_direct_segment_coverage(
            gold_segments,
            predicted_segments,
            require_text=True,
            require_bbox=False,
        ),
        _maximum_direct_segment_coverage(
            gold_segments,
            predicted_segments,
            require_text=False,
            require_bbox=True,
        ),
    )


def _strict_direct_provenance_matches(
    gold_segments: list[dict[str, Any]],
    predicted_segments: list[dict[str, Any]],
) -> bool:
    """Require text/role and bbox to agree on the same one-to-one evidence."""

    return _maximum_direct_segment_coverage(
        gold_segments,
        predicted_segments,
        require_text=True,
        require_bbox=True,
    )


def _action_signature(actions: list[dict[str, Any]]) -> list[tuple[str, str]]:
    return [
        (
            normalize_text(action.get("marker")),
            _normalize_action_text(action.get("text")),
        )
        for action in actions
    ]


def _normalize_action_text(value: Any) -> str:
    """Compare action meaning independently from source list typography.

    Nested dash or bullet glyphs remain in the source segment and native
    object references.  The action model is currently flat, so those visual
    delimiters must not make otherwise identical action text unequal.
    """

    text = "" if value is None else str(value)
    text = re.sub(r"(?:(?<=\s)|^)[\-–—•◦▪▫‣⁃●○]\s+", "", text)
    return normalize_text(text)


def _logic_signature(requirement: dict[str, Any]) -> list[tuple[Any, ...]]:
    clauses = requirement.get("clauses", [])
    clause_index = {
        clause.get("clause_id"): index
        for index, clause in enumerate(clauses)
        if clause.get("clause_id") is not None
    }
    return [
        (
            clause_index.get(clause.get("parent_clause_id")),
            _normalized_clause_marker(clause.get("marker")),
            normalize_text(clause.get("text")),
            clause.get("joins_next"),
        )
        for clause in clauses
    ]


def _normalized_clause_marker(value: Any) -> str | None:
    if value is None:
        return None
    marker = normalize_text(value).strip()
    marker = marker.strip("().")
    return marker or None


def _normalized(value: Any) -> Any:
    if isinstance(value, str):
        return normalize_text(value)
    if isinstance(value, list):
        return [_normalized(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalized(value[key]) for key in sorted(value)}
    return value


def _legacy_field_value(statement: dict[str, Any], field: str) -> Any:
    if field == "modalities":
        modal = statement.get("modality")
        return [] if not modal else [
            (normalize_text(modal), None, None)
        ]
    if field == "negations":
        modal = normalize_text(statement.get("modality"))
        return [] if " not" not in f" {modal}" else [(modal, None)]
    if field == "thresholds":
        threshold = statement.get("threshold")
        return [] if not threshold else [
            (normalize_text(threshold), None, None, None, None, None)
        ]
    if field == "conditions":
        condition = statement.get("condition")
        return [] if not condition else [(normalize_text(condition), None)]
    if field == "exceptions":
        exception = statement.get("exception")
        return [] if not exception else [(normalize_text(exception), None)]
    if field in {"applicability", "exemptions", "dates", "logical_structure"}:
        return []
    raise KeyError(field)


def _anchor_signature(
    anchor: dict[str, Any],
    segment_by_id: dict[str, dict[str, Any]],
) -> tuple[Any, ...]:
    segment = segment_by_id.get(str(anchor.get("source_segment_id")), {})
    return (
        segment.get("role"),
        _segment_page_index(segment),
        anchor.get("start_char"),
        anchor.get("end_char"),
        anchor.get("text"),
    )


def _scope_ref_signature(
    item: dict[str, Any],
    segment_by_id: dict[str, dict[str, Any]],
) -> tuple[Any, ...] | None:
    scope_ref = item.get("scope_ref")
    if not isinstance(scope_ref, dict):
        return None
    return (
        scope_ref.get("kind"),
        scope_ref.get("target"),
        tuple(
            _anchor_signature(anchor, segment_by_id)
            for anchor in scope_ref.get("anchors", [])
        ),
    )


def _text_evidence_signature(
    values: list[dict[str, Any]],
    segment_by_id: dict[str, dict[str, Any]],
) -> list[tuple[Any, ...]]:
    return [
        (
            normalize_text(item.get("text")),
            item.get("basis"),
            tuple(
                _anchor_signature(anchor, segment_by_id)
                for anchor in item.get("anchors", [])
            ),
        )
        for item in values
    ]


def _gold_field_value(
    requirement: dict[str, Any],
    field: str,
    *,
    scope_v4: bool = False,
    segment_by_id: dict[str, dict[str, Any]] | None = None,
) -> Any:
    segments = segment_by_id or {}
    if field == "modalities":
        return [
            (
                normalize_text(item["token"]),
                item["type"],
                (
                    _scope_ref_signature(item, segments)
                    if scope_v4
                    else normalize_text(item["scope"])
                ),
            )
            for item in requirement["modalities"]
        ]
    if field == "negations":
        return [
            (
                normalize_text(item["text"]),
                _scope_ref_signature(item, segments)
                if scope_v4 else normalize_text(item["applies_to"]),
            )
            for item in requirement["negations"]
        ]
    if field == "thresholds":
        return [
            (
                normalize_text(item["raw_text"]),
                item["operator"],
                _normalized(item["normalized_value"]),
                normalize_text(item["unit"]),
                _scope_ref_signature(item, segments)
                if scope_v4 else normalize_text(item["applies_to"]),
                item["basis"],
            )
            for item in requirement["thresholds"]
        ]
    if field in {"conditions", "exceptions", "exemptions", "dates"}:
        return [
            (
                normalize_text(item["text"]),
                _scope_ref_signature(item, segments)
                if scope_v4 else normalize_text(item["applies_to"]),
            )
            for item in requirement[field]
        ]
    if field == "applicability":
        if scope_v4:
            return _text_evidence_signature(
                requirement.get("applicability_evidence", []),
                segments,
            )
        return [normalize_text(item) for item in requirement[field]]
    if field == "logical_structure":
        return _logic_signature(requirement)
    raise KeyError(field)


def _prediction_entries(prediction: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    if isinstance(prediction.get("requirements"), list):
        return "requirement-v2", prediction["requirements"]
    return "legacy-regulatory-ir", prediction.get("statements", [])


def _prediction_field_value(
    prediction_kind: str,
    requirement: dict[str, Any],
    field: str,
    *,
    scope_v4: bool = False,
    segment_by_id: dict[str, dict[str, Any]] | None = None,
) -> Any:
    if prediction_kind == "legacy-regulatory-ir":
        return _legacy_field_value(requirement, field)
    if field == "logical_structure":
        return _logic_signature(requirement)
    segments = segment_by_id or {}
    value = requirement.get(field, [])
    if field == "modalities":
        return [
            (
                normalize_text(item.get("token")),
                item.get("type"),
                _scope_ref_signature(item, segments)
                if scope_v4 else normalize_text(item.get("scope")),
            )
            for item in value
        ]
    if field == "negations":
        return [
            (
                normalize_text(item.get("text")),
                _scope_ref_signature(item, segments)
                if scope_v4 else normalize_text(item.get("applies_to")),
            )
            for item in value
        ]
    if field == "thresholds":
        return [
            (
                normalize_text(item.get("raw_text")),
                item.get("operator"),
                _normalized(item.get("normalized_value")),
                normalize_text(item.get("unit")),
                _scope_ref_signature(item, segments)
                if scope_v4 else normalize_text(item.get("applies_to")),
                item.get("basis"),
            )
            for item in value
        ]
    if field in {"conditions", "exceptions", "exemptions", "dates"}:
        return [
            (
                normalize_text(item.get("text")),
                _scope_ref_signature(item, segments)
                if scope_v4 else normalize_text(item.get("applies_to")),
            )
            for item in value
        ]
    if field == "applicability":
        if scope_v4:
            return _text_evidence_signature(
                requirement.get("applicability_evidence", []),
                segments,
            )
        return [normalize_text(item) for item in value]
    return _normalized(value)


def _strict_semantic_field_value(
    requirement: dict[str, Any],
    field: str,
    *,
    prediction_kind: str | None = None,
    scope_v4: bool = False,
    segment_by_id: dict[str, dict[str, Any]] | None = None,
) -> Any:
    if field in CRITICAL_FIELDS:
        if prediction_kind is None:
            return _gold_field_value(
                requirement,
                field,
                scope_v4=scope_v4,
                segment_by_id=segment_by_id,
            )
        return _prediction_field_value(
            prediction_kind,
            requirement,
            field,
            scope_v4=scope_v4,
            segment_by_id=segment_by_id,
        )
    if field in {"criterion_path", "normative_subjects"}:
        if field == "normative_subjects" and scope_v4:
            return _text_evidence_signature(
                requirement.get("normative_subject_evidence", []),
                segment_by_id or {},
            )
        return [normalize_text(item) for item in requirement.get(field, [])]
    if field == "cross_references":
        return sorted(
            (
                normalize_text(item.get("text")),
                normalize_text(item.get("target")),
                item.get("type"),
            )
            for item in requirement.get(field, [])
        )
    if field == "footnote_refs":
        return sorted(
            (
                normalize_text(item.get("marker")),
                normalize_text(item.get("text")),
                item.get("link_type"),
            )
            for item in requirement.get(field, [])
        )
    if field == "associated_instructions":
        return [
            (
                normalize_text(item.get("marker")),
                normalize_text(item.get("text")),
                item.get("effect"),
            )
            for item in requirement.get(field, [])
        ]
    raise KeyError(field)


def _accepted_result_is_correct(
    *,
    prediction_kind: str,
    predicted: dict[str, Any],
    gold_requirement: dict[str, Any],
    gold: dict[str, Any],
    prediction: dict[str, Any],
    identity_is_unique: bool,
) -> bool:
    """Return whether one accepted Requirement satisfies the full contract.

    This is deliberately stricter than ID matching. A result is correct only
    when its unique Requirement identity, direct text, every critical semantic
    field, actions and direct provenance all pass their exact-match checks.
    Legacy Regulatory IR cannot prove this contract.
    """
    if prediction_kind != "requirement-v2" or not identity_is_unique:
        return False
    scope_v4 = gold.get("schema_version") == "4.0"
    gold_segments = {item["segment_id"]: item for item in gold.get("segments", [])}
    predicted_segments_all = _prediction_source_segments(prediction, predicted)
    predicted_segment_by_id = {
        str(item.get("segment_id", item.get("id"))): item
        for item in predicted_segments_all
        if item.get("segment_id") or item.get("id")
    }
    if str(predicted.get("requirement_id")) != gold_requirement["requirement_id"]:
        return False
    if (
        predicted.get("requirement_form") != gold_requirement.get("requirement_form")
        or predicted.get("language") != gold_requirement.get("language")
    ):
        return False
    if any(
        normalize_text(predicted.get(field))
        != normalize_text(gold_requirement.get(field))
        for field in ("normative_text", "indicator_text", "requirement_value")
    ):
        return False
    if any(
        _strict_semantic_field_value(
            predicted,
            field,
            prediction_kind=prediction_kind,
            scope_v4=scope_v4,
            segment_by_id=predicted_segment_by_id,
        )
        != _strict_semantic_field_value(
            gold_requirement,
            field,
            scope_v4=scope_v4,
            segment_by_id=gold_segments,
        )
        for field in STRICT_SEMANTIC_FIELDS
    ):
        return False
    if (
        _action_signature(predicted.get("client_actions", []))
        != _action_signature(gold_requirement["client_actions"])
        or _action_signature(predicted.get("auditor_actions", []))
        != _action_signature(gold_requirement["auditor_actions"])
    ):
        return False
    selected_page_indices = {
        page_number - 1 for page_number in gold["sample"]["page_numbers"]
    }
    predicted_segments = _prediction_direct_segments(
        prediction,
        predicted,
        selected_page_indices=selected_page_indices,
    )
    predicted_pages = {
        page_index
        for segment in predicted_segments
        if (page_index := _segment_page_index(segment)) is not None
    }
    if not predicted_pages:
        predicted_pages = set(predicted.get("source_page_indices", []))
    if predicted_pages != _gold_source_pages(gold_requirement, gold):
        return False
    return _strict_direct_provenance_matches(
        _gold_direct_segments(gold_requirement, gold), predicted_segments
    )


def evaluate_requirement_sample(
    gold: dict[str, Any],
    prediction: dict[str, Any],
) -> dict[str, Any]:
    prediction_kind, entries = _prediction_entries(prediction)
    scope_v4 = gold.get("schema_version") == "4.0"
    gold_segment_by_id = {
        item["segment_id"]: item for item in gold.get("segments", [])
    }
    gold_by_id = {item["requirement_id"]: item for item in gold["requirements"]}
    sample_page_indices = {page - 1 for page in gold["sample"]["page_numbers"]}
    if prediction_kind == "legacy-regulatory-ir":
        sample_entries = [
            entry
            for entry in entries
            if sample_page_indices.intersection(entry.get("source_page_indices", []))
        ]
    else:
        sample_entries = entries
    prediction_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in sample_entries:
        requirement_id = entry.get("requirement_id")
        if requirement_id:
            prediction_by_id[str(requirement_id)].append(entry)

    gold_ids = set(gold_by_id)
    predicted_ids = set(prediction_by_id)
    matched_ids = sorted(gold_ids & predicted_ids)
    missing_ids = sorted(gold_ids - predicted_ids)
    extra_ids = sorted(predicted_ids - gold_ids)
    duplicate_ids = sorted(
        requirement_id
        for requirement_id, values in prediction_by_id.items()
        if len(values) > 1
    )

    formal_inventory = set(prediction.get("formal_requirement_ids", []))
    if prediction_kind == "requirement-v2" and not formal_inventory:
        formal_inventory = predicted_ids
    explicitly_missing = set(prediction.get("missing_requirement_ids", []))
    silent_omissions = sorted(
        requirement_id
        for requirement_id in missing_ids
        if requirement_id not in explicitly_missing
    )
    modal_gate_misses = sorted(gold_ids & explicitly_missing)
    unscoped_entries = [
        entry
        for entry in sample_entries
        if not entry.get("requirement_id")
        and sample_page_indices.intersection(entry.get("source_page_indices", []))
    ]

    provenance_page_matches = 0
    provenance_segment_covered = 0
    provenance_bbox_covered = 0
    normative_text_results: list[bool] = []
    indicator_text_results: list[bool] = []
    requirement_value_results: list[bool] = []
    critical_field_results: dict[str, list[bool]] = {
        field: [] for field in CRITICAL_FIELDS
    }
    action_separation_results: list[bool] = []
    action_bearing_results: list[bool] = []
    action_hallucination_count = 0
    matched_gold_empty_action_count = 0
    client_auditor_confusion_ids: list[str] = []
    for requirement_id in matched_ids:
        gold_requirement = gold_by_id[requirement_id]
        predicted = prediction_by_id[requirement_id][0]
        predicted_segment_by_id = {
            str(item.get("segment_id", item.get("id"))): item
            for item in _prediction_source_segments(prediction, predicted)
            if item.get("segment_id") or item.get("id")
        }
        predicted_segments = _prediction_direct_segments(
            prediction,
            predicted,
            selected_page_indices=sample_page_indices,
        )
        predicted_pages = {
            page_index
            for segment in predicted_segments
            if (page_index := _segment_page_index(segment)) is not None
        }
        if not predicted_pages:
            predicted_pages = set(predicted.get("source_page_indices", []))
        provenance_page_matches += predicted_pages == _gold_source_pages(
            gold_requirement, gold
        )
        segment_match, bbox_match = _direct_provenance_matches(
            _gold_direct_segments(gold_requirement, gold), predicted_segments
        )
        provenance_segment_covered += segment_match
        provenance_bbox_covered += bbox_match
        if prediction_kind == "requirement-v2":
            normative_text_results.append(
                normalize_text(predicted.get("normative_text"))
                == normalize_text(gold_requirement["normative_text"])
            )
            indicator_text_results.append(
                normalize_text(predicted.get("indicator_text"))
                == normalize_text(gold_requirement["indicator_text"])
            )
            requirement_value_results.append(
                normalize_text(predicted.get("requirement_value"))
                == normalize_text(gold_requirement["requirement_value"])
            )
        else:
            # Regulatory IR 1.0 decomposes text and drops the source-level
            # indicator/value distinction, so exact recovery cannot be proven.
            normative_text_results.append(False)
            indicator_text_results.append(gold_requirement["indicator_text"] is None)
            requirement_value_results.append(gold_requirement["requirement_value"] is None)
        for field in CRITICAL_FIELDS:
            critical_field_results[field].append(
                _gold_field_value(
                    gold_requirement,
                    field,
                    scope_v4=scope_v4,
                    segment_by_id=gold_segment_by_id,
                )
                == _prediction_field_value(
                    prediction_kind,
                    predicted,
                    field,
                    scope_v4=scope_v4,
                    segment_by_id=predicted_segment_by_id,
                )
            )
        gold_client = _action_signature(gold_requirement["client_actions"])
        gold_auditor = _action_signature(gold_requirement["auditor_actions"])
        predicted_client = _action_signature(predicted.get("client_actions", []))
        predicted_auditor = _action_signature(predicted.get("auditor_actions", []))
        action_match = (
            prediction_kind == "requirement-v2"
            and predicted_client == gold_client
            and predicted_auditor == gold_auditor
        )
        action_separation_results.append(action_match)
        if gold_client or gold_auditor:
            action_bearing_results.append(action_match)
            if (
                prediction_kind == "requirement-v2"
                and predicted_client == gold_auditor
                and predicted_auditor == gold_client
                and (gold_client != gold_auditor)
            ):
                client_auditor_confusion_ids.append(requirement_id)
        else:
            matched_gold_empty_action_count += 1
            action_hallucination_count += bool(predicted_client or predicted_auditor)

    accepted_entries: list[dict[str, Any]] = []
    if prediction_kind == "legacy-regulatory-ir":
        review_ids = set(prediction.get("review_required", []))
        accepted_entries = [
            entry for entry in sample_entries if entry.get("id") not in review_ids
        ]
    else:
        accepted_entries = [
            entry
            for entry in sample_entries
            if entry.get("status", "accepted") == "accepted"
        ]

    accepted_matched_ids = {
        str(entry.get("requirement_id"))
        for entry in accepted_entries
        if entry.get("requirement_id") is not None
        and str(entry.get("requirement_id")) in gold_ids
    }
    accepted_correct_ids = sorted(
        str(entry["requirement_id"])
        for entry in accepted_entries
        if entry.get("requirement_id") is not None
        and str(entry["requirement_id"]) in gold_by_id
        and _accepted_result_is_correct(
            prediction_kind=prediction_kind,
            predicted=entry,
            gold_requirement=gold_by_id[str(entry["requirement_id"])],
            gold=gold,
            prediction=prediction,
            identity_is_unique=(
                len(prediction_by_id[str(entry["requirement_id"])]) == 1
            ),
        )
    )

    field_rates = {
        field: _ratio_or_none(sum(values), len(values))
        for field, values in critical_field_results.items()
    }
    field_recall_rates = {
        field: safe_ratio(sum(values), len(gold_ids), empty=0.0)
        for field, values in critical_field_results.items()
    }
    all_field_values = [
        result for values in critical_field_results.values() for result in values
    ]
    nonempty_field_values = [
        result
        for requirement_id in matched_ids
        for field in CRITICAL_FIELDS
        if _gold_field_value(
            gold_by_id[requirement_id],
            field,
            scope_v4=scope_v4,
            segment_by_id=gold_segment_by_id,
        )
        for result in [critical_field_results[field][matched_ids.index(requirement_id)]]
    ]
    gold_nonempty_field_count = sum(
        bool(_gold_field_value(
            requirement,
            field,
            scope_v4=scope_v4,
            segment_by_id=gold_segment_by_id,
        ))
        for requirement in gold_by_id.values()
        for field in CRITICAL_FIELDS
    )
    gold_action_requirement_count = sum(
        bool(requirement["client_actions"] or requirement["auditor_actions"])
        for requirement in gold_by_id.values()
    )
    counts = {
        "gold_requirements": len(gold_ids),
        "predicted_statements": len(sample_entries),
        "matched_requirements": len(matched_ids),
        "accepted_statements": len(accepted_entries),
        "accepted_matched_requirements": len(accepted_matched_ids),
        "accepted_result_correct": len(accepted_correct_ids),
        "formal_inventory_matches": len(gold_ids & formal_inventory),
        "critical_field_correct": sum(all_field_values),
        "critical_field_matched_total": len(all_field_values),
        "critical_field_gold_total": len(gold_ids) * len(CRITICAL_FIELDS),
        "critical_nonempty_field_correct": sum(nonempty_field_values),
        "critical_nonempty_field_matched_total": len(nonempty_field_values),
        "critical_nonempty_field_gold_total": gold_nonempty_field_count,
        "normative_text_correct": sum(normative_text_results),
        "indicator_text_correct": sum(indicator_text_results),
        "requirement_value_correct": sum(requirement_value_results),
        "provenance_page_correct": provenance_page_matches,
        "provenance_segment_covered": provenance_segment_covered,
        "provenance_bbox_covered": provenance_bbox_covered,
        "action_separation_correct": sum(action_separation_results),
        "action_requirement_matched_total": len(action_separation_results),
        "action_requirement_gold_total": gold_action_requirement_count,
        "action_bearing_correct": sum(action_bearing_results),
        "action_bearing_matched_total": len(action_bearing_results),
        "action_hallucinations": action_hallucination_count,
        "matched_gold_empty_actions": matched_gold_empty_action_count,
    }
    metrics = {
        "requirement_recall": safe_ratio(len(matched_ids), len(gold_ids)),
        "requirement_precision": _ratio_or_none(
            len(matched_ids), len(sample_entries)
        ),
        "accepted_id_precision": _ratio_or_none(
            len(accepted_matched_ids),
            len(accepted_entries),
        ),
        "accepted_id_coverage": safe_ratio(
            len(accepted_matched_ids), len(gold_ids), empty=0.0
        ),
        "accepted_id_recall": safe_ratio(
            len(accepted_matched_ids), len(gold_ids), empty=0.0
        ),
        # Compatibility aliases. These measure only identity matching and must
        # not be interpreted as correctness of the accepted result.
        "accepted_requirement_precision": _ratio_or_none(
            len(accepted_matched_ids), len(accepted_entries)
        ),
        "accepted_requirement_coverage": safe_ratio(
            len(accepted_matched_ids), len(gold_ids), empty=0.0
        ),
        "accepted_requirement_recall": safe_ratio(
            len(accepted_matched_ids), len(gold_ids), empty=0.0
        ),
        "accepted_result_precision": _ratio_or_none(
            len(accepted_correct_ids), len(accepted_entries)
        ),
        "accepted_result_coverage": safe_ratio(
            len(accepted_correct_ids), len(gold_ids), empty=0.0
        ),
        "accepted_result_recall": safe_ratio(
            len(accepted_correct_ids), len(gold_ids), empty=0.0
        ),
        "formal_inventory_recall": safe_ratio(
            len(gold_ids & formal_inventory), len(gold_ids)
        ),
        "critical_field_exact_match": _ratio_or_none(
            sum(all_field_values), len(all_field_values)
        ),
        "critical_field_recall": safe_ratio(
            sum(all_field_values), len(gold_ids) * len(CRITICAL_FIELDS), empty=0.0
        ),
        "critical_nonempty_field_exact_match": _ratio_or_none(
            sum(nonempty_field_values), len(nonempty_field_values)
        ),
        "critical_nonempty_field_recall": safe_ratio(
            sum(nonempty_field_values), gold_nonempty_field_count, empty=1.0
        ),
        "normative_text_exact_match": _ratio_or_none(
            sum(normative_text_results), len(normative_text_results)
        ),
        "normative_text_recall": safe_ratio(
            sum(normative_text_results), len(gold_ids), empty=0.0
        ),
        "indicator_text_exact_match": _ratio_or_none(
            sum(indicator_text_results), len(indicator_text_results)
        ),
        "indicator_text_recall": safe_ratio(
            sum(indicator_text_results), len(gold_ids), empty=0.0
        ),
        "requirement_value_exact_match": _ratio_or_none(
            sum(requirement_value_results), len(requirement_value_results)
        ),
        "requirement_value_recall": safe_ratio(
            sum(requirement_value_results), len(gold_ids), empty=0.0
        ),
        "provenance_page_exact_match": _ratio_or_none(
            provenance_page_matches, len(matched_ids)
        ),
        "provenance_page_recall": safe_ratio(
            provenance_page_matches, len(gold_ids), empty=0.0
        ),
        "provenance_segment_coverage": _ratio_or_none(
            provenance_segment_covered, len(matched_ids)
        ),
        "provenance_segment_recall": safe_ratio(
            provenance_segment_covered, len(gold_ids), empty=0.0
        ),
        "provenance_bbox_coverage": _ratio_or_none(
            provenance_bbox_covered, len(matched_ids)
        ),
        "provenance_bbox_recall": safe_ratio(
            provenance_bbox_covered, len(gold_ids), empty=0.0
        ),
        "action_separation_exact_match": _ratio_or_none(
            sum(action_separation_results), len(action_separation_results)
        ),
        "action_separation_recall": safe_ratio(
            sum(action_separation_results), len(gold_ids), empty=0.0
        ),
        "action_bearing_recall": _ratio_or_none(
            sum(action_bearing_results), gold_action_requirement_count
        ),
        "action_hallucination_rate": _ratio_or_none(
            action_hallucination_count, matched_gold_empty_action_count
        ),
    }
    return {
        "sample_id": gold["sample_id"],
        "split": gold["sample"]["split"],
        "prediction_kind": prediction_kind,
        "gold_requirement_count": len(gold_ids),
        "predicted_requirement_id_count": len(predicted_ids),
        "predicted_statement_count": len(sample_entries),
        "matched_ids": matched_ids,
        "missing_ids": missing_ids,
        "extra_ids": extra_ids,
        "duplicate_ids": duplicate_ids,
        "accepted_correct_ids": accepted_correct_ids,
        "silent_omission_ids": silent_omissions,
        "modal_gate_miss_ids": modal_gate_misses,
        "unscoped_modal_statement_count": len(unscoped_entries),
        "client_auditor_confusion_ids": client_auditor_confusion_ids,
        "critical_field_rates": field_rates,
        "critical_field_recall_rates": field_recall_rates,
        "counts": counts,
        "metrics": metrics,
    }


def _aggregate_requirement_reports(
    reports: list[dict[str, Any]],
) -> dict[str, float | None]:
    if not reports:
        return {}
    counts = {
        key: sum(report["counts"][key] for report in reports)
        for key in reports[0]["counts"]
    }
    matched = counts["matched_requirements"]
    gold = counts["gold_requirements"]
    action_matched = counts["action_requirement_matched_total"]
    action_gold = counts["action_requirement_gold_total"]
    return {
        "requirement_recall": safe_ratio(
            counts["matched_requirements"], gold, empty=0.0
        ),
        "requirement_precision": _ratio_or_none(
            counts["matched_requirements"], counts["predicted_statements"]
        ),
        "accepted_id_precision": _ratio_or_none(
            counts["accepted_matched_requirements"], counts["accepted_statements"]
        ),
        "accepted_id_coverage": safe_ratio(
            counts["accepted_matched_requirements"], gold, empty=0.0
        ),
        "accepted_id_recall": safe_ratio(
            counts["accepted_matched_requirements"], gold, empty=0.0
        ),
        # Compatibility aliases for the former ID-only metric names.
        "accepted_requirement_precision": _ratio_or_none(
            counts["accepted_matched_requirements"], counts["accepted_statements"]
        ),
        "accepted_requirement_coverage": safe_ratio(
            counts["accepted_matched_requirements"], gold, empty=0.0
        ),
        "accepted_requirement_recall": safe_ratio(
            counts["accepted_matched_requirements"], gold, empty=0.0
        ),
        "accepted_result_precision": _ratio_or_none(
            counts["accepted_result_correct"], counts["accepted_statements"]
        ),
        "accepted_result_coverage": safe_ratio(
            counts["accepted_result_correct"], gold, empty=0.0
        ),
        "accepted_result_recall": safe_ratio(
            counts["accepted_result_correct"], gold, empty=0.0
        ),
        "formal_inventory_recall": safe_ratio(
            counts["formal_inventory_matches"], gold, empty=0.0
        ),
        "critical_field_exact_match": _ratio_or_none(
            counts["critical_field_correct"], counts["critical_field_matched_total"]
        ),
        "critical_field_recall": safe_ratio(
            counts["critical_field_correct"], counts["critical_field_gold_total"], empty=0.0
        ),
        "critical_nonempty_field_exact_match": _ratio_or_none(
            counts["critical_nonempty_field_correct"],
            counts["critical_nonempty_field_matched_total"],
        ),
        "critical_nonempty_field_recall": safe_ratio(
            counts["critical_nonempty_field_correct"],
            counts["critical_nonempty_field_gold_total"],
            empty=1.0,
        ),
        "normative_text_exact_match": _ratio_or_none(
            counts["normative_text_correct"], matched
        ),
        "normative_text_recall": safe_ratio(
            counts["normative_text_correct"], gold, empty=0.0
        ),
        "indicator_text_exact_match": _ratio_or_none(
            counts["indicator_text_correct"], matched
        ),
        "indicator_text_recall": safe_ratio(
            counts["indicator_text_correct"], gold, empty=0.0
        ),
        "requirement_value_exact_match": _ratio_or_none(
            counts["requirement_value_correct"], matched
        ),
        "requirement_value_recall": safe_ratio(
            counts["requirement_value_correct"], gold, empty=0.0
        ),
        "provenance_page_exact_match": _ratio_or_none(
            counts["provenance_page_correct"], matched
        ),
        "provenance_page_recall": safe_ratio(
            counts["provenance_page_correct"], gold, empty=0.0
        ),
        "provenance_segment_coverage": _ratio_or_none(
            counts["provenance_segment_covered"], matched
        ),
        "provenance_segment_recall": safe_ratio(
            counts["provenance_segment_covered"], gold, empty=0.0
        ),
        "provenance_bbox_coverage": _ratio_or_none(
            counts["provenance_bbox_covered"], matched
        ),
        "provenance_bbox_recall": safe_ratio(
            counts["provenance_bbox_covered"], gold, empty=0.0
        ),
        "action_separation_exact_match": _ratio_or_none(
            counts["action_separation_correct"], action_matched
        ),
        "action_separation_recall": _ratio_or_none(
            counts["action_separation_correct"], gold
        ),
        "action_bearing_recall": _ratio_or_none(
            counts["action_bearing_correct"], action_gold
        ),
        "action_hallucination_rate": _ratio_or_none(
            counts["action_hallucinations"], counts["matched_gold_empty_actions"]
        ),
    }


def evaluate_requirement_manifest(
    manifest_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    manifest_file = Path(manifest_path)
    manifest_errors = validate_requirement_manifest(manifest_file)
    if manifest_errors:
        raise ValueError("; ".join(manifest_errors))
    manifest = _read_json(manifest_file)
    reports: list[dict[str, Any]] = []
    for item in manifest.get("documents", []):
        gold_path = (manifest_file.parent / item["gold"]).resolve()
        prediction_path = (manifest_file.parent / item["prediction"]).resolve()
        schema_path = (
            manifest_file.parent / item.get("schema", manifest["schema"])
        ).resolve()
        gold = load_requirement_gold(gold_path, schema_path)
        prediction = _read_json(prediction_path)
        expected_document_id = f"sha256:{gold['source']['sha256']}"
        if prediction.get("document_id") != expected_document_id:
            raise ValueError(
                f"{item['id']}: prediction document_id={prediction.get('document_id')!r} "
                f"but expected {expected_document_id!r}"
            )
        report = evaluate_requirement_sample(gold, prediction)
        # The manifest controls how a frozen sample is used in this evaluation
        # round. ``gold_split`` exists only to validate the immutable Gold
        # annotation's original split and must not control report grouping.
        report["gold_split"] = gold["sample"]["split"]
        report["split"] = item["split"]
        report["prediction"] = str(prediction_path)
        reports.append(report)

    metric_names = sorted({name for report in reports for name in report["metrics"]})
    aggregate = _aggregate_requirement_reports(reports)
    macro_average = {
        name: (
            fmean(values)
            if (values := [
                report["metrics"][name]
                for report in reports
                if report["metrics"][name] is not None
            ])
            else None
        )
        for name in metric_names
    }
    by_split = {}
    for split in ("active", "holdout"):
        split_reports = [report for report in reports if report["split"] == split]
        if split_reports:
            by_split[split] = _aggregate_requirement_reports(split_reports)
    result = {
        "schema_version": "2.1-baseline",
        "round_id": manifest["round_id"],
        "evaluation_mode": manifest.get("evaluation_mode", "round"),
        "completion_gate_eligible": (
            manifest.get("evaluation_mode", "round") == "round"
        ),
        "document_count": len(reports),
        "metric_semantics": {
            "accepted_result_precision": (
                "fully correct accepted Requirements / all accepted predictions"
            ),
            "accepted_id_precision": (
                "accepted predictions with a Gold Requirement ID / all accepted predictions"
            ),
            "accepted_requirement_precision": (
                "deprecated compatibility alias of accepted_id_precision"
            ),
        },
        "aggregate": aggregate,
        "macro_average": macro_average,
        "by_split": by_split,
        "documents": reports,
    }
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
