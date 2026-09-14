from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from pdf_extraction.evaluation.requirement_gold import (
    load_requirement_gold,
    requirement_gold_integrity_errors,
    validate_requirement_manifest,
)
from pdf_extraction.evaluation.requirement_evaluator import (
    _action_signature,
    _normalize_direct_provenance_text,
    _prediction_direct_segments,
    _strict_semantic_field_value,
    evaluate_requirement_manifest,
    evaluate_requirement_sample,
)
from tests.support.paths import PROJECT_ROOT


def test_relation_collections_are_order_independent_but_value_exact() -> None:
    left = {
        "cross_references": [
            {"text": "[84]", "target": "footnote 84", "type": "internal_exact"},
            {"text": "[83]", "target": "footnote 83", "type": "internal_exact"},
        ],
        "footnote_refs": [
            {"marker": "84", "text": "Second.", "link_type": "direct"},
            {"marker": "83", "text": "First.", "link_type": "semantic"},
        ],
    }
    right = {
        "cross_references": list(reversed(left["cross_references"])),
        "footnote_refs": list(reversed(left["footnote_refs"])),
    }

    for field in ("cross_references", "footnote_refs"):
        assert _strict_semantic_field_value(left, field) == (
            _strict_semantic_field_value(right, field)
        )


def test_sample_provenance_excludes_out_of_window_supporting_evidence() -> None:
    requirement = {
        "source_segments": [
            {"segment_id": "direct", "page_index": 16, "role": "normative_text"},
            {"segment_id": "support", "page_index": 15, "role": "footnote"},
        ]
    }

    segments = _prediction_direct_segments(
        {}, requirement, selected_page_indices={16}
    )

    assert [item["segment_id"] for item in segments] == ["direct"]


ROOT = PROJECT_ROOT
REQUIREMENT_GOLD = ROOT / "gold" / "requirements"


def test_action_signature_ignores_nested_list_glyph_but_not_text() -> None:
    marked = [{"marker": "a", "text": "Keep records: - date; - amount."}]
    flat = [{"marker": "a", "text": "Keep records: date; amount."}]
    changed = [{"marker": "a", "text": "Keep records: date."}]

    assert _action_signature(marked) == _action_signature(flat)
    assert _action_signature(marked) != _action_signature(changed)


def test_interpretation_requirement_gold_is_frozen_and_valid() -> None:
    gold = load_requirement_gold(
        REQUIREMENT_GOLD / "annotations" / "interpretation-manual-p019-p021.json",
        REQUIREMENT_GOLD / "schema-v2.json",
    )
    assert gold["annotation"]["status"] == "frozen"
    assert [item["requirement_id"] for item in gold["requirements"]] == [
        "1.4.1",
        "1.4.2",
        "1.4.3",
    ]
    cross_page = next(
        item for item in gold["requirements"] if item["requirement_id"] == "1.4.3"
    )
    assert cross_page["source_segment_ids"][-1] == "int-1.4.3-text-p21"


def test_requirement_manifest_has_no_schema_or_reference_errors() -> None:
    annotation_paths = [
        REQUIREMENT_GOLD / "annotations" / "farm-standard-p028-p029.json",
        REQUIREMENT_GOLD / "annotations" / "interpretation-manual-p019-p021.json",
        REQUIREMENT_GOLD / "annotations" / "audit-manual-p001-p003.json",
        REQUIREMENT_GOLD / "annotations" / "salmon-cod-standard-p018.json",
    ]
    assert all(path.exists() for path in annotation_paths)
    assert validate_requirement_manifest(REQUIREMENT_GOLD / "manifest.json") == []


def test_versioned_audit_gold_revision_preserves_immutable_predecessor() -> None:
    revised = load_requirement_gold(
        REQUIREMENT_GOLD / "annotations"
        / "audit-manual-p011-p012-round4-holdout-v2.json",
        REQUIREMENT_GOLD / "schema-v3.json",
    )
    assert revised["gold_revision"] == 2
    assert revised["supersedes"] == (
        "annotations/audit-manual-p011-p012-round4-holdout.json"
    )
    requirement = next(
        item for item in revised["requirements"]
        if item["requirement_id"] == "4.2.2"
    )
    assert requirement["auditor_actions"][-1]["text"].endswith("(Appendix VI)")
    assert not requirement["auditor_actions"][-1]["text"].endswith(".")
    assert validate_requirement_manifest(
        REQUIREMENT_GOLD / "manifest-round4.json"
    ) == []


def test_legacy_requirement_evaluation_exposes_modal_gate_and_silent_omission() -> None:
    gold = load_requirement_gold(
        REQUIREMENT_GOLD / "annotations" / "interpretation-manual-p019-p021.json",
        REQUIREMENT_GOLD / "schema-v2.json",
    )
    prediction = {
        "statements": [
            {
                "id": "reg-1",
                "requirement_id": "1.4.1",
                "modality": "shall",
                "threshold": None,
                "condition": None,
                "exception": None,
                "source_segment_ids": ["prediction-segment"],
                "source_page_indices": [18]
            }
        ],
        "formal_requirement_ids": ["1.4.1", "1.4.2"],
        "missing_requirement_ids": ["1.4.2"],
        "review_required": []
    }
    report = evaluate_requirement_sample(gold, prediction)
    assert report["matched_ids"] == ["1.4.1"]
    assert report["modal_gate_miss_ids"] == ["1.4.2"]
    assert report["silent_omission_ids"] == ["1.4.3"]


def test_empty_prediction_cannot_receive_vacuous_quality_scores() -> None:
    gold = load_requirement_gold(
        REQUIREMENT_GOLD / "annotations" / "farm-standard-p028-p029.json",
        REQUIREMENT_GOLD / "schema-v2.json",
    )
    report = evaluate_requirement_sample(gold, {"statements": []})
    metrics = report["metrics"]
    assert metrics["requirement_recall"] == 0.0
    assert metrics["requirement_precision"] is None
    assert metrics["critical_field_exact_match"] is None
    assert metrics["critical_field_recall"] == 0.0
    assert metrics["provenance_page_exact_match"] is None
    assert metrics["provenance_page_recall"] == 0.0
    assert metrics["action_separation_exact_match"] is None


def _prediction_requirement(
    gold: dict,
    requirement_id: str,
    *,
    status: str = "accepted",
) -> dict:
    requirement = deepcopy(next(
        item for item in gold["requirements"]
        if item["requirement_id"] == requirement_id
    ))
    segment_by_id = {item["segment_id"]: item for item in gold["segments"]}
    requirement["source_segments"] = [
        deepcopy(segment_by_id[segment_id])
        for segment_id in requirement["source_segment_ids"]
    ]
    requirement["status"] = status
    return requirement


def _v4_gold_sample() -> dict:
    indicator = "The farm shall record every medication event"
    segments = [
        ("g-id", "requirement_id", "1.1.1", 10, 10, 50, 20),
        ("g-ind", "indicator_text", indicator, 60, 10, 500, 30),
        ("g-value", "requirement_value", "100%", 60, 35, 120, 50),
        ("g-app", "applicability", "All", 60, 55, 120, 70),
    ]
    source_segments = [
        {
            "segment_id": segment_id,
            "page_number": 1,
            "page_index": 0,
            "page_size": {
                "width": 612,
                "height": 792,
                "unit": "pdf_point",
                "origin": "top_left",
            },
            "bbox": {"x0": x0, "y0": y0, "x1": x1, "y1": y1},
            "role": role,
            "object_kind": "table_cell",
            "segment_order": index,
            "source_text": text,
            "continues_segment_id": None,
        }
        for index, (segment_id, role, text, x0, y0, x1, y1) in enumerate(segments)
    ]
    subject_end = len("The farm")
    predicate_start = indicator.index("record")
    return {
        "schema_version": "4.0",
        "gold_revision": 1,
        "supersedes": None,
        "supersedes_sha256": None,
        "revision_reason": "Initial synthetic v4 contract fixture.",
        "sample_id": "synthetic-v4",
        "source": {
            "file_name": "synthetic.pdf",
            "sha256": "a" * 64,
            "language": "en",
            "document_family": "audit_manual",
            "page_count": 1,
        },
        "sample": {
            "round_id": "test-v4",
            "split": "active",
            "page_numbers": [1],
            "selection_rationale": "Exercise source-backed semantic scope.",
        },
        "annotation": {
            "status": "frozen",
            "frozen_at": "2026-08-28",
            "verification": ["visual_page", "native_text"],
            "notes": [],
        },
        "segments": source_segments,
        "requirements": [{
            "requirement_id": "1.1.1",
            "requirement_form": "audit_matrix",
            "criterion_path": [],
            "language": "en",
            "indicator_text": indicator,
            "requirement_value": "100%",
            "normative_text": f"Indicator: {indicator}\nRequirement: 100%\nApplicability: All",
            "normative_subjects": ["The farm"],
            "applicability": ["All"],
            "normative_subject_evidence": [{
                "text": "The farm",
                "basis": "explicit",
                "source_segment_ids": ["g-ind"],
                "anchors": [{
                    "source_segment_id": "g-ind",
                    "start_char": 0,
                    "end_char": subject_end,
                    "text": "The farm",
                }],
            }],
            "applicability_evidence": [{
                "text": "All",
                "basis": "explicit",
                "source_segment_ids": ["g-app"],
                "anchors": [{
                    "source_segment_id": "g-app",
                    "start_char": 0,
                    "end_char": 3,
                    "text": "All",
                }],
            }],
            "modalities": [{
                "token": "shall",
                "type": "obligation",
                "scope": "record every medication event",
                "scope_ref": {
                    "kind": "source_span",
                    "target": "indicator_text",
                    "anchors": [{
                        "source_segment_id": "g-ind",
                        "start_char": predicate_start,
                        "end_char": len(indicator),
                        "text": indicator[predicate_start:],
                    }],
                },
            }],
            "negations": [],
            "clauses": [{
                "clause_id": "1.1.1-c1",
                "parent_clause_id": None,
                "marker": None,
                "text": indicator,
                "joins_next": None,
            }],
            "conditions": [],
            "exceptions": [],
            "exemptions": [],
            "thresholds": [{
                "raw_text": "100%",
                "operator": "eq",
                "normalized_value": 100,
                "unit": "%",
                "applies_to": "medication event coverage",
                "basis": "explicit",
                "source_segment_ids": ["g-value"],
                "scope_ref": {
                    "kind": "field",
                    "target": "indicator_text",
                    "anchors": [{
                        "source_segment_id": "g-ind",
                        "start_char": 0,
                        "end_char": len(indicator),
                        "text": indicator,
                    }],
                },
            }],
            "dates": [],
            "cross_references": [],
            "footnote_refs": [],
            "associated_instructions": [],
            "client_actions": [],
            "auditor_actions": [],
            "related_context_ids": [],
            "source_segment_ids": ["g-id", "g-ind", "g-value", "g-app"],
            "source_anomalies": [],
            "gold_notes": [],
        }],
        "excluded_regions": [],
        "summary": {
            "requirement_count": 1,
            "cross_page_requirement_count": 0,
            "client_action_count": 0,
            "auditor_action_count": 0,
            "critical_gold_ambiguities": [],
        },
    }


def test_v4_schema_and_exact_anchor_integrity(tmp_path: Path) -> None:
    path = tmp_path / "synthetic-v4.json"
    path.write_text(json.dumps(_v4_gold_sample()), encoding="utf-8")

    loaded = load_requirement_gold(path, REQUIREMENT_GOLD / "schema-v4.json")

    assert loaded["schema_version"] == "4.0"
    broken = _v4_gold_sample()
    broken["requirements"][0]["thresholds"][0]["scope_ref"]["anchors"][0][
        "text"
    ] = "fabricated"
    path.write_text(json.dumps(broken), encoding="utf-8")
    with pytest.raises(ValueError, match="anchor text mismatch"):
        load_requirement_gold(path, REQUIREMENT_GOLD / "schema-v4.json")


def test_round7_v4_revision_preserves_frozen_source_evidence(tmp_path: Path) -> None:
    predecessor_path = (
        REQUIREMENT_GOLD
        / "annotations"
        / "audit-manual-p017-p018-round7-holdout.json"
    )
    revision_path = (
        REQUIREMENT_GOLD
        / "annotations"
        / "audit-manual-p017-p018-round7-holdout-v4.json"
    )
    predecessor = json.loads(predecessor_path.read_text(encoding="utf-8"))
    revision = load_requirement_gold(
        revision_path,
        REQUIREMENT_GOLD / "schema-v4.json",
    )

    assert revision["gold_revision"] == 2
    assert revision["segments"] == predecessor["segments"]
    assert revision["excluded_regions"] == predecessor["excluded_regions"]

    temporary_gold = tmp_path / "gold"
    annotations = temporary_gold / "annotations"
    annotations.mkdir(parents=True)
    (temporary_gold / "schema-v4.json").write_bytes(
        (REQUIREMENT_GOLD / "schema-v4.json").read_bytes()
    )
    (annotations / predecessor_path.name).write_bytes(predecessor_path.read_bytes())
    broken = deepcopy(revision)
    broken["segments"][0]["source_text"] += " fabricated"
    broken_path = annotations / revision_path.name
    broken_path.write_text(json.dumps(broken), encoding="utf-8")

    with pytest.raises(ValueError, match="changed frozen direct source segments"):
        load_requirement_gold(broken_path, temporary_gold / "schema-v4.json")


def test_round7_v5_adds_only_classified_supporting_evidence() -> None:
    revision = load_requirement_gold(
        REQUIREMENT_GOLD
        / "annotations"
        / "audit-manual-p017-p018-round7-holdout-v5.json",
        REQUIREMENT_GOLD / "schema-v4.json",
    )

    assert revision["sample"]["page_numbers"] == [17, 18]
    assert revision["supporting_page_numbers"] == [16]
    assert revision["supporting_segment_ids"] == ["p16-footnote-77-supporting"]
    requirement = next(
        item for item in revision["requirements"]
        if item["requirement_id"] == "5.1.6"
    )
    assert "p16-footnote-77-supporting" not in requirement["source_segment_ids"]
    assert requirement["footnote_refs"][0]["source_segment_ids"] == [
        "p16-footnote-77-supporting"
    ]

    broken = deepcopy(revision)
    broken_requirement = next(
        item for item in broken["requirements"]
        if item["requirement_id"] == "5.1.6"
    )
    broken_requirement["source_segment_ids"].append("p16-footnote-77-supporting")
    assert any(
        "uses supporting evidence as direct provenance" in error
        for error in requirement_gold_integrity_errors(broken)
    )


def test_v4_active_diagnostic_manifest_is_not_completion_gate_eligible(
    tmp_path: Path,
) -> None:
    manifest = REQUIREMENT_GOLD / "manifest-round7-v4.json"

    assert validate_requirement_manifest(manifest) == []
    report = evaluate_requirement_manifest(manifest, tmp_path / "report.json")

    assert report["evaluation_mode"] == "active_diagnostic"
    assert report["completion_gate_eligible"] is False
    assert "holdout" not in report["by_split"]


def test_v4_evaluator_uses_scope_ref_not_free_text_summary() -> None:
    gold = _v4_gold_sample()
    predicted = _prediction_requirement(gold, "1.1.1")

    predicted["thresholds"][0]["applies_to"] = "different display summary"
    report = evaluate_requirement_sample(gold, {"requirements": [predicted]})
    assert report["critical_field_rates"]["thresholds"] == 1.0
    assert report["metrics"]["accepted_result_precision"] == 1.0

    predicted["thresholds"][0]["scope_ref"]["target"] = "normative_text"
    report = evaluate_requirement_sample(gold, {"requirements": [predicted]})
    assert report["critical_field_rates"]["thresholds"] == 0.0
    assert report["metrics"]["accepted_result_precision"] == 0.0


def test_direct_provenance_typography_normalization_is_strict_and_limited() -> None:
    gold = (
        '“Policy” — controls:\n'
        '• score ≥ 6; and inter-\nnational reporting.'
    )
    prediction = (
        '"Policy" - controls: ◦ score ≥6; and international reporting.'
    )

    assert _normalize_direct_provenance_text(
        prediction
    ) == _normalize_direct_provenance_text(gold)
    assert _normalize_direct_provenance_text(
        prediction.replace("reporting", "records")
    ) != _normalize_direct_provenance_text(gold)
    assert _normalize_direct_provenance_text(
        prediction.replace("controls:", "controls;")
    ) != _normalize_direct_provenance_text(gold)


def test_bbox_coverage_is_independent_from_substantive_text_mismatch() -> None:
    gold = load_requirement_gold(
        REQUIREMENT_GOLD / "annotations" / "interpretation-manual-p019-p021.json",
        REQUIREMENT_GOLD / "schema-v2.json",
    )
    requirement = _prediction_requirement(gold, "1.4.1")
    requirement["source_segments"][1]["source_text"] = (
        "The UoC may ignore every applicable traceability risk."
    )

    report = evaluate_requirement_sample(gold, {"requirements": [requirement]})

    assert report["metrics"]["provenance_segment_coverage"] == 0.0
    assert report["metrics"]["provenance_bbox_coverage"] == 1.0
    assert report["metrics"]["accepted_result_precision"] == 0.0


def test_strict_result_accepts_only_typographic_source_text_variation() -> None:
    gold = load_requirement_gold(
        REQUIREMENT_GOLD / "annotations" / "interpretation-manual-p019-p021.json",
        REQUIREMENT_GOLD / "schema-v2.json",
    )
    requirement = _prediction_requirement(gold, "1.4.1")
    source = requirement["source_segments"][1]["source_text"]
    requirement["source_segments"][1]["source_text"] = source.replace(
        "products", "prod-\nucts"
    )

    report = evaluate_requirement_sample(gold, {"requirements": [requirement]})

    assert report["metrics"]["provenance_segment_coverage"] == 1.0
    assert report["metrics"]["provenance_bbox_coverage"] == 1.0
    assert report["metrics"]["accepted_result_precision"] == 1.0


def test_strict_result_requires_text_and_bbox_on_the_same_evidence_segment() -> None:
    gold = load_requirement_gold(
        REQUIREMENT_GOLD / "annotations" / "interpretation-manual-p019-p021.json",
        REQUIREMENT_GOLD / "schema-v2.json",
    )
    requirement = _prediction_requirement(gold, "1.4.1")
    exact = requirement["source_segments"][1]
    text_only = deepcopy(exact)
    text_only["segment_id"] = "text-only"
    text_only["bbox"] = {"x0": 1, "y0": 1, "x1": 10, "y1": 10}
    bbox_only = deepcopy(exact)
    bbox_only["segment_id"] = "bbox-only"
    bbox_only["source_text"] = "Substantively incorrect source text."
    requirement["source_segments"][1:] = [text_only, bbox_only]

    report = evaluate_requirement_sample(gold, {"requirements": [requirement]})

    assert report["metrics"]["provenance_segment_coverage"] == 1.0
    assert report["metrics"]["provenance_bbox_coverage"] == 1.0
    assert report["metrics"]["accepted_result_precision"] == 0.0


def test_critical_threshold_signature_checks_operator_value_unit_scope_and_basis() -> None:
    gold = load_requirement_gold(
        REQUIREMENT_GOLD / "annotations" / "audit-manual-p001-p003.json",
        REQUIREMENT_GOLD / "schema-v2.json",
    )
    requirement = _prediction_requirement(gold, "2.2.1")
    assert requirement["thresholds"]
    requirement["thresholds"][0].update({
        "operator": "lt",
        "normalized_value": 999,
        "unit": "kg",
        "applies_to": "wrong scope",
        "basis": "inferred_from_source_structure",
    })
    report = evaluate_requirement_sample(gold, {"requirements": [requirement]})
    assert report["critical_field_rates"]["thresholds"] == 0.0
    assert report["metrics"]["critical_nonempty_field_exact_match"] < 1.0


def test_provenance_requires_text_role_and_bbox_alignment_not_nonempty_placeholders() -> None:
    gold = load_requirement_gold(
        REQUIREMENT_GOLD / "annotations" / "interpretation-manual-p019-p021.json",
        REQUIREMENT_GOLD / "schema-v2.json",
    )
    requirement = _prediction_requirement(gold, "1.4.1")
    requirement["source_segments"] = [{
        "segment_id": "BOGUS",
        "page_index": 18,
        "role": "normative_text",
        "source_text": "fabricated evidence",
        "bbox": {},
    }]
    report = evaluate_requirement_sample(gold, {"requirements": [requirement]})
    assert report["metrics"]["provenance_segment_coverage"] == 0.0
    assert report["metrics"]["provenance_bbox_coverage"] == 0.0


def test_related_heading_page_does_not_widen_direct_requirement_provenance() -> None:
    gold = load_requirement_gold(
        REQUIREMENT_GOLD / "annotations" / "interpretation-manual-p019-p021.json",
        REQUIREMENT_GOLD / "schema-v2.json",
    )
    requirement = _prediction_requirement(gold, "1.4.1")
    requirement["source_segments"].append({
        "segment_id": "context-heading",
        "page_index": 0,
        "role": "criterion_heading",
        "source_text": "Criterion 1.4 - Traceability and Disclosure",
        "bbox": {"x0": 50, "y0": 50, "x1": 300, "y1": 65},
    })

    report = evaluate_requirement_sample(gold, {"requirements": [requirement]})

    assert report["metrics"]["provenance_page_exact_match"] == 1.0
    assert report["metrics"]["provenance_segment_coverage"] == 1.0
    assert report["metrics"]["provenance_bbox_coverage"] == 1.0
    assert report["metrics"]["accepted_result_precision"] == 1.0


def test_review_required_requirement_does_not_count_as_accepted_recall() -> None:
    gold = load_requirement_gold(
        REQUIREMENT_GOLD / "annotations" / "interpretation-manual-p019-p021.json",
        REQUIREMENT_GOLD / "schema-v2.json",
    )
    requirement = _prediction_requirement(
        gold, "1.4.1", status="review_required"
    )
    report = evaluate_requirement_sample(gold, {"requirements": [requirement]})
    assert report["metrics"]["requirement_recall"] == 1 / 3
    assert report["metrics"]["accepted_requirement_recall"] == 0.0


def test_accepted_result_precision_requires_full_requirement_correctness() -> None:
    gold = load_requirement_gold(
        REQUIREMENT_GOLD / "annotations" / "interpretation-manual-p019-p021.json",
        REQUIREMENT_GOLD / "schema-v2.json",
    )
    requirement = _prediction_requirement(gold, "1.4.1")
    requirement["normative_text"] = "Incorrect but still attached to the right ID."

    report = evaluate_requirement_sample(gold, {"requirements": [requirement]})

    assert report["metrics"]["accepted_id_precision"] == 1.0
    assert report["metrics"]["accepted_requirement_precision"] == 1.0
    assert report["metrics"]["accepted_result_precision"] == 0.0
    assert report["metrics"]["accepted_result_recall"] == 0.0
    assert report["accepted_correct_ids"] == []


def test_fully_exact_accepted_requirement_counts_as_correct_result() -> None:
    gold = load_requirement_gold(
        REQUIREMENT_GOLD / "annotations" / "interpretation-manual-p019-p021.json",
        REQUIREMENT_GOLD / "schema-v2.json",
    )
    requirement = _prediction_requirement(gold, "1.4.1")

    report = evaluate_requirement_sample(gold, {"requirements": [requirement]})

    assert report["metrics"]["accepted_result_precision"] == 1.0
    assert report["metrics"]["accepted_result_recall"] == 1 / 3
    assert report["accepted_correct_ids"] == ["1.4.1"]


def test_accepted_result_checks_cross_references_beyond_legacy_critical_fields() -> None:
    gold = load_requirement_gold(
        REQUIREMENT_GOLD / "annotations" / "interpretation-manual-p019-p021.json",
        REQUIREMENT_GOLD / "schema-v2.json",
    )
    requirement = _prediction_requirement(gold, "1.4.2")
    requirement["cross_references"] = []

    report = evaluate_requirement_sample(gold, {"requirements": [requirement]})

    assert report["metrics"]["accepted_id_precision"] == 1.0
    assert report["metrics"]["accepted_result_precision"] == 0.0


def test_client_and_auditor_action_swap_is_detected() -> None:
    gold = load_requirement_gold(
        REQUIREMENT_GOLD / "annotations" / "audit-manual-p001-p003.json",
        REQUIREMENT_GOLD / "schema-v2.json",
    )
    requirement = _prediction_requirement(gold, "1.1.1")
    requirement["client_actions"], requirement["auditor_actions"] = (
        requirement["auditor_actions"],
        requirement["client_actions"],
    )
    report = evaluate_requirement_sample(gold, {"requirements": [requirement]})
    assert report["client_auditor_confusion_ids"] == ["1.1.1"]
    assert report["metrics"]["action_separation_exact_match"] == 0.0
    assert report["metrics"]["action_bearing_recall"] == 0.0


def test_manifest_evaluation_rejects_prediction_from_another_document(
    tmp_path: Path,
) -> None:
    manifest_path = REQUIREMENT_GOLD / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["schema"] = str((REQUIREMENT_GOLD / manifest["schema"]).resolve())
    for item in manifest["documents"]:
        item["gold"] = str((REQUIREMENT_GOLD / item["gold"]).resolve())
        item["pdf"] = str((REQUIREMENT_GOLD / item["pdf"]).resolve())
        item["prediction"] = str((REQUIREMENT_GOLD / item["prediction"]).resolve())
    forged_prediction = json.loads(
        Path(manifest["documents"][0]["prediction"]).read_text(encoding="utf-8")
    )
    forged_prediction["document_id"] = "sha256:wrong-source"
    forged_path = tmp_path / "forged-prediction.json"
    forged_path.write_text(json.dumps(forged_prediction), encoding="utf-8")
    manifest["documents"][0]["prediction"] = str(forged_path)
    temporary_manifest = tmp_path / "manifest.json"
    temporary_manifest.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="prediction document_id"):
        evaluate_requirement_manifest(
            temporary_manifest, tmp_path / "report.json"
        )


def test_manifest_split_controls_report_grouping_not_frozen_gold_split(
    tmp_path: Path,
) -> None:
    manifest = json.loads(
        (REQUIREMENT_GOLD / "manifest.json").read_text(encoding="utf-8")
    )
    manifest["schema"] = str((REQUIREMENT_GOLD / manifest["schema"]).resolve())
    for item in manifest["documents"]:
        item["gold"] = str((REQUIREMENT_GOLD / item["gold"]).resolve())
        item["pdf"] = str((REQUIREMENT_GOLD / item["pdf"]).resolve())
        item["prediction"] = str(
            (REQUIREMENT_GOLD / item["prediction"]).resolve()
        )
        item["gold_split"] = item["split"]
    original_holdout = next(
        item for item in manifest["documents"] if item["split"] == "holdout"
    )
    replacement_holdout = next(
        item for item in manifest["documents"] if item["split"] == "active"
    )
    original_holdout["split"] = "active"
    replacement_holdout["split"] = "holdout"
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = evaluate_requirement_manifest(manifest_path, tmp_path / "report.json")
    by_id = {item["sample_id"]: item for item in report["documents"]}

    assert by_id[original_holdout["id"]]["split"] == "active"
    assert by_id[original_holdout["id"]]["gold_split"] == "holdout"
    assert by_id[replacement_holdout["id"]]["split"] == "holdout"
    assert by_id[replacement_holdout["id"]]["gold_split"] == "active"
