from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


# These buckets are intentionally explicit.  A newly introduced schema role must
# be classified before it can be used as Requirement provenance.
DIRECT_REQUIREMENT_ROLES = frozenset(
    {
        "requirement_id",
        "indicator_text",
        "requirement_value",
        "normative_text",
        "applicability",
        "requirement_continuation",
        "footnote",
    }
)
CONTEXT_ROLES = frozenset(
    {
        "criterion_heading",
        "continuation_anchor",
        "rationale",
        "interpretation",
        "evidence_example",
        "auditor_guidance",
        "resource",
        "other",
    }
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_sample_history(
    manifest_file: Path,
    history_reference: Any,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Load the optional blind-sample registry with fail-closed validation."""
    if not isinstance(history_reference, str) or not history_reference:
        return {}, ["manifest sample_history must be a non-empty path"]
    history_path = (manifest_file.parent / history_reference).resolve()
    try:
        history = _read_json(history_path)
    except (OSError, json.JSONDecodeError) as exc:
        return {}, [f"cannot load sample_history {history_path}: {exc}"]
    if not isinstance(history, dict) or not isinstance(history.get("samples"), list):
        return {}, [f"sample_history {history_path} has no samples list"]

    registry: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for index, record in enumerate(history["samples"]):
        if not isinstance(record, dict):
            errors.append(f"sample_history record {index} is not an object")
            continue
        sample_id = record.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            errors.append(f"sample_history record {index} has no sample_id")
            continue
        if sample_id in registry:
            errors.append(f"sample_history has duplicate sample_id {sample_id}")
            continue
        first_scored_round = record.get("first_scored_round")
        if first_scored_round is not None and (
            not isinstance(first_scored_round, str) or not first_scored_round
        ):
            errors.append(
                f"sample_history {sample_id} first_scored_round must be string or null"
            )
        current_status = record.get("current_status")
        if not isinstance(current_status, str) or not current_status:
            errors.append(f"sample_history {sample_id} has no current_status")
        registry[sample_id] = record
    return registry, errors


def _gold_revision_integrity_errors(
    document: dict[str, Any],
    *,
    annotation_file: Path,
    schema_file: Path,
) -> list[str]:
    """Validate the immutable predecessor link used by Gold schema v3/v4.

    Schema v2 documents intentionally bypass this check so historical manifests
    remain reproducible.  A v3 revision must bind its predecessor by relative
    path and SHA256, keep the same sample window/source, and increment the
    revision number by exactly one.
    """

    if document.get("schema_version") not in {"3.0", "4.0"}:
        return []

    sample_id = document.get("sample_id", "<unknown>")
    revision = document.get("gold_revision")
    supersedes = document.get("supersedes")
    predecessor_digest = document.get("supersedes_sha256")
    if revision == 1:
        if supersedes is not None or predecessor_digest is not None:
            return [
                f"{sample_id}: Gold revision 1 cannot supersede another annotation"
            ]
        return []

    errors: list[str] = []
    if not isinstance(supersedes, str) or not supersedes:
        errors.append(f"{sample_id}: Gold revision {revision} has no predecessor")
        return errors
    if not isinstance(predecessor_digest, str) or not predecessor_digest:
        errors.append(
            f"{sample_id}: Gold revision {revision} has no predecessor SHA256"
        )
        return errors

    gold_root = schema_file.resolve().parent
    predecessor_path = (gold_root / supersedes).resolve()
    if not predecessor_path.is_relative_to(gold_root):
        errors.append(f"{sample_id}: supersedes escapes the Requirement Gold root")
        return errors
    if predecessor_path == annotation_file.resolve():
        errors.append(f"{sample_id}: Gold revision cannot supersede itself")
        return errors
    if not predecessor_path.is_file():
        errors.append(f"{sample_id}: superseded Gold does not exist: {supersedes}")
        return errors

    actual_digest = _sha256(predecessor_path)
    if actual_digest != predecessor_digest:
        errors.append(
            f"{sample_id}: superseded Gold SHA256 mismatch: actual "
            f"{actual_digest}, expected {predecessor_digest}"
        )
        return errors

    predecessor = _read_json(predecessor_path)
    predecessor_revision = predecessor.get("gold_revision", 1)
    if not isinstance(predecessor_revision, int) or revision != predecessor_revision + 1:
        errors.append(
            f"{sample_id}: Gold revision {revision} does not immediately follow "
            f"revision {predecessor_revision}"
        )
    if predecessor.get("sample_id") != document.get("sample_id"):
        errors.append(f"{sample_id}: superseded Gold sample_id mismatch")
    if predecessor.get("source") != document.get("source"):
        errors.append(f"{sample_id}: superseded Gold source identity changed")
    if predecessor.get("sample") != document.get("sample"):
        errors.append(f"{sample_id}: superseded Gold sample window changed")
    if document.get("schema_version") == "4.0":
        predecessor_supporting = set(predecessor.get("supporting_segment_ids", []))
        current_supporting = set(document.get("supporting_segment_ids", []))
        predecessor_segments = predecessor.get("segments", [])
        current_segments = document.get("segments", [])
        predecessor_by_id = {
            item["segment_id"]: item for item in predecessor_segments
        }
        current_by_id = {item["segment_id"]: item for item in current_segments}
        predecessor_direct = [
            item for item in predecessor_segments
            if item["segment_id"] not in predecessor_supporting
        ]
        current_direct = [
            item for item in current_segments
            if item["segment_id"] not in current_supporting
        ]
        if predecessor_direct != current_direct:
            errors.append(
                f"{sample_id}: v4 revision changed frozen direct source segments"
            )
        if not predecessor_supporting <= current_supporting:
            errors.append(
                f"{sample_id}: v4 revision removed supporting source segments"
            )
        if any(
            predecessor_by_id.get(segment_id) != current_by_id.get(segment_id)
            for segment_id in predecessor_supporting
        ):
            errors.append(
                f"{sample_id}: v4 revision changed supporting source segments"
            )
        if predecessor.get("excluded_regions") != document.get("excluded_regions"):
            errors.append(f"{sample_id}: v4 revision changed frozen excluded regions")
    return errors


def load_requirement_gold(
    annotation_path: str | Path,
    schema_path: str | Path,
) -> dict[str, Any]:
    """Load one frozen Requirement Gold sample and reject structural drift."""
    annotation_file = Path(annotation_path)
    schema_file = Path(schema_path)
    schema = _read_json(schema_file)
    Draft202012Validator.check_schema(schema)
    document = _read_json(annotation_file)
    Draft202012Validator(
        schema,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    ).validate(document)
    errors = requirement_gold_integrity_errors(document)
    errors.extend(
        _gold_revision_integrity_errors(
            document,
            annotation_file=annotation_file,
            schema_file=schema_file,
        )
    )
    if errors:
        raise ValueError("; ".join(errors))
    return document


def requirement_gold_integrity_errors(document: dict[str, Any]) -> list[str]:
    """Validate references and invariants that JSON Schema cannot express."""
    errors: list[str] = []
    sample_id = document.get("sample_id", "<unknown>")
    sample_pages = set(document.get("sample", {}).get("page_numbers", []))
    supporting_pages = set(document.get("supporting_page_numbers", []))
    supporting_segment_ids = set(document.get("supporting_segment_ids", []))
    segments = document.get("segments", [])
    segment_by_id: dict[str, dict[str, Any]] = {}

    for segment in segments:
        segment_id = segment["segment_id"]
        if segment_id in segment_by_id:
            errors.append(f"{sample_id}: duplicate segment_id {segment_id}")
            continue
        segment_by_id[segment_id] = segment
        page_number = segment["page_number"]
        if page_number not in sample_pages and not (
            segment_id in supporting_segment_ids
            and page_number in supporting_pages
        ):
            errors.append(f"{sample_id}: {segment_id} is outside selected pages")
        if segment["page_index"] != page_number - 1:
            errors.append(f"{sample_id}: {segment_id} page index is not zero-based")
        bbox = segment["bbox"]
        page_size = segment["page_size"]
        if not (0 <= bbox["x0"] < bbox["x1"] <= page_size["width"]):
            errors.append(f"{sample_id}: invalid horizontal bbox for {segment_id}")
        if not (0 <= bbox["y0"] < bbox["y1"] <= page_size["height"]):
            errors.append(f"{sample_id}: invalid vertical bbox for {segment_id}")

    def require_segment_refs(owner: str, values: list[str]) -> None:
        for segment_id in values:
            if segment_id not in segment_by_id:
                errors.append(f"{sample_id}: {owner} references missing segment {segment_id}")

    for segment_id in supporting_segment_ids:
        segment = segment_by_id.get(segment_id)
        if segment is None:
            errors.append(f"{sample_id}: missing supporting segment {segment_id}")
        elif segment["page_number"] not in supporting_pages:
            errors.append(
                f"{sample_id}: supporting segment {segment_id} is not on a supporting page"
            )

    def require_ref_roles(
        owner: str,
        values: list[str],
        allowed_roles: frozenset[str],
    ) -> None:
        for segment_id in values:
            segment = segment_by_id.get(segment_id)
            if segment is None:
                continue
            role = segment["role"]
            if role not in allowed_roles:
                errors.append(
                    f"{sample_id}: {owner} references {segment_id} with invalid role {role}"
                )

    def validate_anchor_container(owner: str, value: dict[str, Any]) -> None:
        previous_key: tuple[int, int, int] | None = None
        previous_end_by_segment: dict[str, int] = {}
        for anchor in value.get("anchors", []):
            segment_id = anchor["source_segment_id"]
            segment = segment_by_id.get(segment_id)
            if segment is None:
                errors.append(
                    f"{sample_id}: {owner} anchor references missing segment {segment_id}"
                )
                continue
            start = anchor["start_char"]
            end = anchor["end_char"]
            source_text = segment["source_text"]
            if not (0 <= start < end <= len(source_text)):
                errors.append(
                    f"{sample_id}: {owner} anchor is outside source text {segment_id}"
                )
                continue
            if source_text[start:end] != anchor["text"]:
                errors.append(
                    f"{sample_id}: {owner} anchor text mismatch {segment_id}"
                )
            key = (segment["page_number"], segment["segment_order"], start)
            if previous_key is not None and key < previous_key:
                errors.append(f"{sample_id}: {owner} anchors are out of source order")
            previous_key = key
            previous_end = previous_end_by_segment.get(segment_id)
            if previous_end is not None and start < previous_end:
                errors.append(
                    f"{sample_id}: {owner} anchors overlap in {segment_id}"
                )
            previous_end_by_segment[segment_id] = end

    def validate_scope_ref(owner: str, value: dict[str, Any]) -> None:
        scope_ref = value.get("scope_ref")
        if not isinstance(scope_ref, dict):
            return
        validate_anchor_container(f"{owner} scope_ref", scope_ref)
        kind = scope_ref.get("kind")
        target = str(scope_ref.get("target", ""))
        prefixes = {
            "field": ("indicator_text", "requirement_value", "applicability", "normative_text"),
            "clause": ("clause:",),
            "requirement": ("requirement:",),
            "action": ("client:", "auditor:"),
            "footnote": ("footnote:",),
        }
        allowed = prefixes.get(kind)
        if allowed is not None and not target.startswith(allowed):
            errors.append(
                f"{sample_id}: {owner} {kind} scope cannot target {target}"
            )

    for segment in segments:
        previous = segment.get("continues_segment_id")
        if previous is not None:
            require_segment_refs(segment["segment_id"], [previous])
            if previous in segment_by_id:
                prior = segment_by_id[previous]
                if prior["segment_order"] >= segment["segment_order"]:
                    errors.append(
                        f"{sample_id}: continuation order is reversed for {segment['segment_id']}"
                    )

    requirement_ids: set[str] = set()
    cross_page_count = 0
    client_action_count = 0
    auditor_action_count = 0
    for requirement in document.get("requirements", []):
        requirement_id = requirement["requirement_id"]
        if requirement_id in requirement_ids:
            errors.append(f"{sample_id}: duplicate requirement_id {requirement_id}")
        requirement_ids.add(requirement_id)
        require_segment_refs(
            f"Requirement {requirement_id}", requirement["source_segment_ids"]
        )
        if set(requirement["source_segment_ids"]) & supporting_segment_ids:
            errors.append(
                f"{sample_id}: Requirement {requirement_id} uses supporting evidence "
                "as direct provenance"
            )
        require_ref_roles(
            f"Requirement {requirement_id} direct source",
            requirement["source_segment_ids"],
            DIRECT_REQUIREMENT_ROLES,
        )
        require_segment_refs(
            f"Requirement {requirement_id} context", requirement["related_context_ids"]
        )
        require_ref_roles(
            f"Requirement {requirement_id} context",
            requirement["related_context_ids"],
            CONTEXT_ROLES,
        )
        source_pages = {
            segment_by_id[value]["page_number"]
            for value in requirement["source_segment_ids"]
            if value in segment_by_id
        }
        cross_page_count += len(source_pages) > 1

        for collection_name in (
            "footnote_refs",
            "associated_instructions",
            "client_actions",
            "auditor_actions",
        ):
            for item in requirement[collection_name]:
                require_segment_refs(
                    f"Requirement {requirement_id} {collection_name}",
                    item["source_segment_ids"],
                )
                if collection_name in {"client_actions", "auditor_actions"}:
                    expected_role = collection_name.removesuffix("s")
                    require_ref_roles(
                        f"Requirement {requirement_id} {collection_name}",
                        item["source_segment_ids"],
                        frozenset({expected_role}),
                    )
        for threshold in requirement["thresholds"]:
            require_segment_refs(
                f"Requirement {requirement_id} threshold",
                threshold["source_segment_ids"],
            )

        if document.get("schema_version") == "4.0":
            for collection_name in (
                "modalities",
                "negations",
                "conditions",
                "exceptions",
                "exemptions",
                "thresholds",
                "dates",
            ):
                for index, item in enumerate(requirement[collection_name]):
                    validate_scope_ref(
                        f"Requirement {requirement_id} {collection_name} {index}",
                        item,
                    )
            for evidence_name, display_name in (
                ("normative_subject_evidence", "normative_subjects"),
                ("applicability_evidence", "applicability"),
            ):
                evidence = requirement[evidence_name]
                if [item["text"] for item in evidence] != requirement[display_name]:
                    errors.append(
                        f"{sample_id}: Requirement {requirement_id} {evidence_name} "
                        f"does not match {display_name}"
                    )
                for index, item in enumerate(evidence):
                    owner = f"Requirement {requirement_id} {evidence_name} {index}"
                    require_segment_refs(owner, item["source_segment_ids"])
                    validate_anchor_container(owner, item)
                    if item["source_segment_ids"] != [
                        anchor["source_segment_id"] for anchor in item["anchors"]
                    ]:
                        errors.append(
                            f"{sample_id}: {owner} source_segment_ids do not match anchors"
                        )

        clause_ids = {clause["clause_id"] for clause in requirement["clauses"]}
        if len(clause_ids) != len(requirement["clauses"]):
            errors.append(f"{sample_id}: duplicate clause_id in {requirement_id}")
        for clause in requirement["clauses"]:
            parent = clause["parent_clause_id"]
            if parent is not None and parent not in clause_ids:
                errors.append(
                    f"{sample_id}: clause {clause['clause_id']} has missing parent {parent}"
                )

        client_action_count += len(requirement["client_actions"])
        auditor_action_count += len(requirement["auditor_actions"])

    for exclusion in document.get("excluded_regions", []):
        require_segment_refs("excluded region", exclusion["source_segment_ids"])

    summary = document.get("summary", {})
    expected_counts = {
        "requirement_count": len(requirement_ids),
        "cross_page_requirement_count": cross_page_count,
        "client_action_count": client_action_count,
        "auditor_action_count": auditor_action_count,
    }
    for key, expected in expected_counts.items():
        if summary.get(key) != expected:
            errors.append(
                f"{sample_id}: summary {key}={summary.get(key)} but expected {expected}"
            )
    return errors


def validate_requirement_manifest(
    manifest_path: str | Path,
    *,
    verify_source_files: bool = True,
) -> list[str]:
    """Validate frozen annotations, manifest identity and source PDF identity.

    Source-file verification is enabled by default so evaluation callers fail
    closed.  Tests which only exercise annotation contracts may disable the
    filesystem and digest checks explicitly.
    """
    manifest_file = Path(manifest_path)
    manifest = _read_json(manifest_file)
    manifest_round_id = manifest.get("round_id")
    errors: list[str] = []
    if not isinstance(manifest_round_id, str) or not manifest_round_id:
        errors.append("manifest has no round_id")
    sample_history: dict[str, dict[str, Any]] | None = None
    sample_history_reference = manifest.get("sample_history")
    if sample_history_reference is not None:
        sample_history, history_errors = _load_sample_history(
            manifest_file, sample_history_reference
        )
        errors.extend(history_errors)
    ids: set[str] = set()
    for item in manifest.get("documents", []):
        item_id = item["id"]
        if item_id in ids:
            errors.append(f"duplicate manifest id {item_id}")
            continue
        ids.add(item_id)
        gold_path = (manifest_file.parent / item["gold"]).resolve()
        if sample_history is not None:
            history_record = sample_history.get(item_id)
            if history_record is None:
                errors.append(f"{item_id}: sample is missing from sample_history")
            else:
                registered_annotation = history_record.get("annotation")
                if isinstance(registered_annotation, str) and registered_annotation:
                    history_path = (
                        manifest_file.parent / str(sample_history_reference)
                    ).resolve()
                    registered_references = [registered_annotation]
                    revisions = history_record.get("annotation_revisions", [])
                    if isinstance(revisions, list) and all(
                        isinstance(value, str) and value for value in revisions
                    ):
                        registered_references.extend(revisions)
                    elif revisions:
                        errors.append(
                            f"{item_id}: sample_history annotation_revisions "
                            "must be a list of non-empty paths"
                        )
                    registered_gold_paths = {
                        (history_path.parent / reference).resolve()
                        for reference in registered_references
                    }
                    if gold_path not in registered_gold_paths:
                        errors.append(
                            f"{item_id}: sample_history annotation mismatch"
                        )
                if item.get("split") == "holdout":
                    first_scored_round = history_record.get("first_scored_round")
                    if (
                        isinstance(first_scored_round, str)
                        and first_scored_round
                        and first_scored_round != manifest_round_id
                    ):
                        errors.append(
                            f"{item_id}: holdout was already scored in round "
                            f"{first_scored_round!r}"
                        )
                elif (
                    item.get("split") == "active"
                    and isinstance(history_record.get("current_status"), str)
                    and history_record["current_status"].startswith("untouched")
                ):
                    errors.append(
                        f"{item_id}: active sample is marked untouched_holdout "
                        "in sample_history"
                    )
        schema_path = (
            manifest_file.parent / item.get("schema", manifest["schema"])
        ).resolve()
        try:
            gold = load_requirement_gold(gold_path, schema_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{item_id}: {exc}")
            continue
        except Exception as exc:  # jsonschema exposes rich subclasses
            errors.append(f"{item_id}: {type(exc).__name__}: {exc}")
            continue
        if gold["sample_id"] != item_id:
            errors.append(f"{item_id}: sample_id mismatch")
        expected_gold_split = item.get("gold_split", item["split"])
        if gold["sample"]["split"] != expected_gold_split:
            errors.append(f"{item_id}: split mismatch")
        if gold["sample"]["page_numbers"] != item["pages"]:
            errors.append(f"{item_id}: page selection mismatch")
        expected_gold_round_id = item.get("gold_round_id", manifest_round_id)
        if gold["sample"]["round_id"] != expected_gold_round_id:
            errors.append(f"{item_id}: round_id mismatch")

        source_path = (manifest_file.parent / item["pdf"]).resolve()
        expected_source = gold["source"]
        if source_path.name != expected_source["file_name"]:
            errors.append(
                f"{item_id}: source file_name mismatch: manifest resolves to "
                f"{source_path.name!r}, Gold expects {expected_source['file_name']!r}"
            )
        if verify_source_files:
            if not source_path.is_file():
                errors.append(f"{item_id}: source PDF does not exist: {source_path}")
            else:
                try:
                    actual_sha256 = _sha256(source_path)
                except OSError as exc:
                    errors.append(f"{item_id}: cannot hash source PDF {source_path}: {exc}")
                else:
                    if actual_sha256 != expected_source["sha256"]:
                        errors.append(
                            f"{item_id}: source SHA256 mismatch: actual "
                            f"{actual_sha256}, Gold expects {expected_source['sha256']}"
                        )
        prediction_digest = item.get("prediction_sha256")
        if prediction_digest is not None:
            prediction_reference = item.get("prediction")
            if not isinstance(prediction_digest, str) or not prediction_digest:
                errors.append(
                    f"{item_id}: prediction_sha256 must be a non-empty string"
                )
            elif not isinstance(prediction_reference, str) or not prediction_reference:
                errors.append(
                    f"{item_id}: prediction_sha256 requires a prediction path"
                )
            else:
                prediction_path = (
                    manifest_file.parent / prediction_reference
                ).resolve()
                if not prediction_path.is_file():
                    errors.append(
                        f"{item_id}: prediction file does not exist: {prediction_path}"
                    )
                else:
                    try:
                        actual_prediction_digest = _sha256(prediction_path)
                    except OSError as exc:
                        errors.append(
                            f"{item_id}: cannot hash prediction {prediction_path}: {exc}"
                        )
                    else:
                        if actual_prediction_digest != prediction_digest:
                            errors.append(
                                f"{item_id}: prediction SHA256 mismatch: actual "
                                f"{actual_prediction_digest}, expected {prediction_digest}"
                            )
    evaluation_mode = manifest.get("evaluation_mode", "round")
    if evaluation_mode not in {"round", "active_diagnostic"}:
        errors.append(f"manifest has unsupported evaluation_mode {evaluation_mode!r}")
    if not any(item.get("split") == "active" for item in manifest.get("documents", [])):
        errors.append("manifest has no active sample")
    if (
        evaluation_mode == "round"
        and not any(
            item.get("split") == "holdout" for item in manifest.get("documents", [])
        )
    ):
        errors.append("manifest has no frozen holdout")
    if evaluation_mode == "active_diagnostic" and any(
        item.get("split") == "holdout" for item in manifest.get("documents", [])
    ):
        errors.append("active_diagnostic manifest cannot score a frozen holdout")
    return errors
