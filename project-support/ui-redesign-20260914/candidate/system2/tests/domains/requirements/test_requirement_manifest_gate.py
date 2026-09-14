from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pdf_extraction.evaluation.requirement_gold import (
    load_requirement_gold,
    requirement_gold_integrity_errors,
    validate_requirement_manifest,
)
from tests.support.paths import PROJECT_ROOT


ROOT = PROJECT_ROOT
REQUIREMENT_GOLD = ROOT / "gold" / "requirements"
MANIFEST_PATH = REQUIREMENT_GOLD / "manifest.json"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def _manifest_copy(tmp_path: Path) -> tuple[Path, dict]:
    manifest = _read_json(MANIFEST_PATH)
    manifest["schema"] = str((REQUIREMENT_GOLD / "schema-v2.json").resolve())
    for item in manifest["documents"]:
        item["gold"] = str((REQUIREMENT_GOLD / item["gold"]).resolve())
        item["pdf"] = str((REQUIREMENT_GOLD / item["pdf"]).resolve())
    path = tmp_path / "manifest.json"
    _write_json(path, manifest)
    return path, manifest


def _gold(name: str) -> dict:
    return load_requirement_gold(
        REQUIREMENT_GOLD / "annotations" / name,
        REQUIREMENT_GOLD / "schema-v2.json",
    )


def _attach_sample_history(tmp_path: Path, manifest: dict) -> dict:
    history = {
        "schema_version": "1.0",
        "samples": [
            {
                "sample_id": item["id"],
                "current_status": (
                    "untouched_holdout"
                    if item["split"] == "holdout"
                    else "active_regression"
                ),
                "first_scored_round": (
                    None if item["split"] == "holdout" else manifest["round_id"]
                ),
            }
            for item in manifest["documents"]
        ],
    }
    history_path = tmp_path / "sample-history.json"
    _write_json(history_path, history)
    manifest["sample_history"] = history_path.name
    return history


def test_current_requirement_manifest_passes_fail_closed_source_gate() -> None:
    assert validate_requirement_manifest(MANIFEST_PATH) == []


def test_manifest_round_id_must_match_every_gold_sample(tmp_path: Path) -> None:
    manifest_path, manifest = _manifest_copy(tmp_path)
    manifest["round_id"] = "different-round"
    _write_json(manifest_path, manifest)

    errors = validate_requirement_manifest(manifest_path, verify_source_files=False)

    assert sum("round_id mismatch" in error for error in errors) == 4


def test_manifest_can_reuse_frozen_gold_from_an_explicit_prior_round(
    tmp_path: Path,
) -> None:
    manifest_path, manifest = _manifest_copy(tmp_path)
    manifest["round_id"] = "new-evaluation-round"
    for item in manifest["documents"]:
        item["gold_round_id"] = "goal04-round1"
    _write_json(manifest_path, manifest)

    errors = validate_requirement_manifest(
        manifest_path, verify_source_files=False
    )

    assert not any("round_id mismatch" in error for error in errors)


def test_manifest_can_reclassify_a_used_holdout_as_active_without_mutating_gold(
    tmp_path: Path,
) -> None:
    manifest_path, manifest = _manifest_copy(tmp_path)
    holdout = next(
        item for item in manifest["documents"] if item["split"] == "holdout"
    )
    holdout["split"] = "active"
    holdout["gold_split"] = "holdout"
    other = next(
        item for item in manifest["documents"] if item["id"] != holdout["id"]
    )
    other["split"] = "holdout"
    other["gold_split"] = "active"
    _write_json(manifest_path, manifest)

    errors = validate_requirement_manifest(
        manifest_path, verify_source_files=False
    )

    assert not any("split mismatch" in error for error in errors)


def test_sample_history_requires_every_manifest_sample(tmp_path: Path) -> None:
    manifest_path, manifest = _manifest_copy(tmp_path)
    history = _attach_sample_history(tmp_path, manifest)
    missing = history["samples"].pop()
    _write_json(tmp_path / "sample-history.json", history)
    _write_json(manifest_path, manifest)

    errors = validate_requirement_manifest(manifest_path, verify_source_files=False)

    assert any(
        missing["sample_id"] in error and "missing from sample_history" in error
        for error in errors
    )


def test_prior_scored_sample_cannot_be_reused_as_holdout(tmp_path: Path) -> None:
    manifest_path, manifest = _manifest_copy(tmp_path)
    history = _attach_sample_history(tmp_path, manifest)
    holdout = next(
        item for item in manifest["documents"] if item["split"] == "holdout"
    )
    record = next(
        item for item in history["samples"] if item["sample_id"] == holdout["id"]
    )
    record["first_scored_round"] = "an-earlier-round"
    record["current_status"] = "active_regression"
    _write_json(tmp_path / "sample-history.json", history)
    _write_json(manifest_path, manifest)

    errors = validate_requirement_manifest(manifest_path, verify_source_files=False)

    assert any(
        holdout["id"] in error and "already scored" in error for error in errors
    )


@pytest.mark.parametrize("first_scored_round", [None, "goal04-round1"])
def test_holdout_may_be_unscored_or_first_scored_in_current_round(
    tmp_path: Path,
    first_scored_round: str | None,
) -> None:
    manifest_path, manifest = _manifest_copy(tmp_path)
    history = _attach_sample_history(tmp_path, manifest)
    holdout = next(
        item for item in manifest["documents"] if item["split"] == "holdout"
    )
    record = next(
        item for item in history["samples"] if item["sample_id"] == holdout["id"]
    )
    record["first_scored_round"] = first_scored_round
    _write_json(tmp_path / "sample-history.json", history)
    _write_json(manifest_path, manifest)

    errors = validate_requirement_manifest(manifest_path, verify_source_files=False)

    assert not any("sample_history" in error or "already scored" in error for error in errors)


def test_active_sample_cannot_be_marked_untouched_holdout(tmp_path: Path) -> None:
    manifest_path, manifest = _manifest_copy(tmp_path)
    history = _attach_sample_history(tmp_path, manifest)
    active = next(
        item for item in manifest["documents"] if item["split"] == "active"
    )
    record = next(
        item for item in history["samples"] if item["sample_id"] == active["id"]
    )
    record["current_status"] = "untouched_holdout"
    _write_json(tmp_path / "sample-history.json", history)
    _write_json(manifest_path, manifest)

    errors = validate_requirement_manifest(manifest_path, verify_source_files=False)

    assert any(
        active["id"] in error and "marked untouched_holdout" in error
        for error in errors
    )


def test_prediction_sha256_detects_overwritten_blind_output(tmp_path: Path) -> None:
    manifest_path, manifest = _manifest_copy(tmp_path)
    prediction = tmp_path / "blind-prediction.json"
    prediction.write_bytes(b'{"frozen": true}')
    item = manifest["documents"][0]
    item["prediction"] = prediction.name
    item["prediction_sha256"] = hashlib.sha256(prediction.read_bytes()).hexdigest()
    _write_json(manifest_path, manifest)

    assert not any(
        "prediction SHA256" in error
        for error in validate_requirement_manifest(
            manifest_path, verify_source_files=False
        )
    )

    prediction.write_bytes(b'{"frozen": false}')
    errors = validate_requirement_manifest(manifest_path, verify_source_files=False)

    assert any("prediction SHA256 mismatch" in error for error in errors)


def test_manifest_requires_existing_source_pdf(tmp_path: Path) -> None:
    manifest_path, manifest = _manifest_copy(tmp_path)
    manifest["documents"][0]["pdf"] = str(
        tmp_path / "ASC-STD-001-ASC-Farm-Standard-V1.0.1-Aug-2025.pdf"
    )
    _write_json(manifest_path, manifest)

    errors = validate_requirement_manifest(manifest_path)

    assert any("source PDF does not exist" in error for error in errors)


def test_manifest_source_file_name_must_match_gold(tmp_path: Path) -> None:
    manifest_path, manifest = _manifest_copy(tmp_path)
    manifest["documents"][0]["pdf"] = str(tmp_path / "renamed.pdf")
    _write_json(manifest_path, manifest)

    errors = validate_requirement_manifest(manifest_path, verify_source_files=False)

    assert any("source file_name mismatch" in error for error in errors)


def test_manifest_source_sha256_must_match_gold(tmp_path: Path) -> None:
    manifest_path, manifest = _manifest_copy(tmp_path)
    source_name = "ASC-STD-001-ASC-Farm-Standard-V1.0.1-Aug-2025.pdf"
    forged_source = tmp_path / source_name
    forged_source.write_bytes(b"not the frozen source")
    manifest["documents"][0]["pdf"] = str(forged_source)
    _write_json(manifest_path, manifest)

    errors = validate_requirement_manifest(manifest_path)

    actual_hash = hashlib.sha256(forged_source.read_bytes()).hexdigest()
    assert any(
        "source SHA256 mismatch" in error and actual_hash in error
        for error in errors
    )


@pytest.mark.parametrize(
    "invalid_role",
    [
        "criterion_heading",
        "header",
        "footer",
        "rationale",
        "auditor_guidance",
        "client_action",
        "auditor_action",
    ],
)
def test_direct_requirement_source_rejects_non_direct_roles(invalid_role: str) -> None:
    gold = _gold("farm-standard-p028-p029.json")
    requirement = gold["requirements"][0]
    segment_id = requirement["source_segment_ids"][0]
    segment = next(item for item in gold["segments"] if item["segment_id"] == segment_id)
    segment["role"] = invalid_role

    errors = requirement_gold_integrity_errors(gold)

    assert any(
        "direct source" in error and f"invalid role {invalid_role}" in error
        for error in errors
    )


def test_related_context_must_reference_context_role() -> None:
    gold = _gold("farm-standard-p028-p029.json")
    requirement = gold["requirements"][0]
    requirement["related_context_ids"] = [requirement["source_segment_ids"][0]]

    errors = requirement_gold_integrity_errors(gold)

    assert any(
        "context" in error and "invalid role requirement_id" in error
        for error in errors
    )


@pytest.mark.parametrize(
    ("collection_name", "wrong_role"),
    [("client_actions", "auditor_action"), ("auditor_actions", "client_action")],
)
def test_action_references_require_matching_action_role(
    collection_name: str,
    wrong_role: str,
) -> None:
    gold = _gold("audit-manual-p001-p003.json")
    requirement = next(item for item in gold["requirements"] if item[collection_name])
    action = requirement[collection_name][0]
    segment = next(
        item
        for item in gold["segments"]
        if item["segment_id"] == action["source_segment_ids"][0]
    )
    segment["role"] = wrong_role

    errors = requirement_gold_integrity_errors(gold)

    assert any(
        collection_name in error and f"invalid role {wrong_role}" in error
        for error in errors
    )
