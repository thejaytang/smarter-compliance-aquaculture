from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from pdf_extraction.evaluation.requirement_gold import (
    load_requirement_gold,
    validate_requirement_manifest,
)
from tests.support.paths import PROJECT_ROOT


ROOT = PROJECT_ROOT
REQUIREMENT_GOLD = ROOT / "gold" / "requirements"
OLD_GOLD = REQUIREMENT_GOLD / "annotations" / "salmon-cod-standard-p018.json"
NEW_GOLD = REQUIREMENT_GOLD / "annotations" / "salmon-cod-standard-p018-v2.json"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_salmon_p18_v2_is_a_minimal_source_bound_revision() -> None:
    old = load_requirement_gold(OLD_GOLD, REQUIREMENT_GOLD / "schema-v2.json")
    new = load_requirement_gold(NEW_GOLD, REQUIREMENT_GOLD / "schema-v3.json")

    assert new["gold_revision"] == 2
    assert new["supersedes"] == "annotations/salmon-cod-standard-p018.json"
    assert new["revision_reason"]
    assert new["source"] == old["source"]
    assert new["sample"] == old["sample"]
    assert new["annotation"] == old["annotation"]
    assert new["segments"] == old["segments"]
    assert new["excluded_regions"] == old["excluded_regions"]
    assert new["summary"] == old["summary"]

    old_by_id = {item["requirement_id"]: item for item in old["requirements"]}
    for revised in new["requirements"]:
        original = old_by_id[revised["requirement_id"]]
        assert revised["normative_text"] == (
            f"{revised['indicator_text']}\n{revised['requirement_value']}"
        )
        unchanged = deepcopy(revised)
        unchanged["normative_text"] = original["normative_text"]
        assert unchanged == original


def test_schema_v2_historical_gold_and_manifest_remain_reproducible() -> None:
    old = load_requirement_gold(OLD_GOLD, REQUIREMENT_GOLD / "schema-v2.json")

    assert old["schema_version"] == "2.0"
    assert all(
        item["normative_text"] == item["indicator_text"]
        for item in old["requirements"]
    )
    assert validate_requirement_manifest(REQUIREMENT_GOLD / "manifest.json") == []


def test_v3_revision_rejects_a_changed_predecessor_digest(tmp_path: Path) -> None:
    revised = _read_json(NEW_GOLD)
    revised["supersedes_sha256"] = "0" * 64
    candidate = tmp_path / "salmon-cod-standard-p018-v2.json"
    candidate.write_text(json.dumps(revised), encoding="utf-8")

    with pytest.raises(ValueError, match="superseded Gold SHA256 mismatch"):
        load_requirement_gold(candidate, REQUIREMENT_GOLD / "schema-v3.json")


def test_manifest_can_mix_historical_v2_and_revised_v3_gold(
    tmp_path: Path,
) -> None:
    manifest = _read_json(REQUIREMENT_GOLD / "manifest.json")
    manifest["schema"] = str((REQUIREMENT_GOLD / "schema-v2.json").resolve())
    for item in manifest["documents"]:
        item["gold"] = str((REQUIREMENT_GOLD / item["gold"]).resolve())
        item["pdf"] = str((REQUIREMENT_GOLD / item["pdf"]).resolve())
        if item["id"] == "salmon-cod-standard-p018":
            item["gold"] = str(NEW_GOLD.resolve())
            item["schema"] = str(
                (REQUIREMENT_GOLD / "schema-v3.json").resolve()
            )
    manifest_path = tmp_path / "mixed-schema-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    assert validate_requirement_manifest(manifest_path) == []
