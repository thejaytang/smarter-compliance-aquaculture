from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from statistics import fmean
from typing import Any

from .metrics import error_rate, exact_match, f1, normalize_text, safe_ratio


def _text_for_block(block: dict[str, Any]) -> str:
    content = block.get("content") or {}
    return normalize_text(
        content.get("resolved_text") or content.get("ocr_text") or content.get("native_text")
    )


def _prediction_features(document: dict[str, Any]) -> dict[str, Any]:
    blocks = [
        block for block in document.get("blocks", {}).values()
        if block.get("type") not in {"document", "section", "header", "footer"}
    ]
    blocks.sort(key=lambda block: (
        (block.get("segments") or [{}])[0].get("page_index", 10**9),
        (block.get("segments") or [{"bbox": {}}])[0].get("bbox", {}).get("y0", 10**9),
        block.get("order_in_parent", 0),
    ))
    text_blocks = [block for block in blocks if block.get("type") not in {"table", "figure"}]
    critical_spans = [
        span for span in document.get("evidence_spans", {}).values()
        if span.get("criticality") != "general"
    ]
    tables = [block.get("table") for block in blocks if block.get("table")]
    cells = [
        normalize_text((cell.get("content") or {}).get("resolved_text"))
        for table in tables for cell in table.get("cells", [])
    ]
    spans = [
        f"{cell.get('row_span', 1)}x{cell.get('column_span', 1)}"
        for table in tables for cell in table.get("cells", [])
    ]
    return {
        "text": "\n".join(_text_for_block(block) for block in text_blocks if _text_for_block(block)),
        "block_types": [block.get("type") for block in blocks],
        "heading_levels": [str(block.get("heading_level")) for block in blocks if block.get("type") == "heading"],
        "cross_page_merges": sum(len(block.get("segments", [])) > 1 for block in blocks),
        "cells": cells,
        "cell_spans": spans,
        "critical_spans": [normalize_text(span.get("resolved_text")) for span in critical_spans],
        "critical_conflicts": [
            conflict.get("conflict_type") for conflict in document.get("conflicts", [])
            if conflict.get("severity") == "critical"
        ],
        "accepted_spans": [span for span in critical_spans if span.get("resolution_status") == "resolved"],
        "all_spans": critical_spans,
    }


def _score_entry(gold: dict[str, Any], prediction: dict[str, Any]) -> dict[str, float]:
    features = _prediction_features(prediction)
    expected_text = gold.get("text", "")
    expected_types = gold.get("block_types", [])
    expected_headings = [str(value) for value in gold.get("heading_levels", [])]
    expected_spans = [normalize_text(value) for value in gold.get("critical_spans", [])]
    expected_cells = [normalize_text(value) for value in gold.get("cells", [])]
    expected_cell_spans = gold.get("cell_spans", [])
    expected_conflicts = gold.get("critical_conflicts", [])
    accepted = features["accepted_spans"]
    correct_accepted = sum(
        normalize_text(span.get("resolved_text")) in expected_spans for span in accepted
    )
    expected_merge_count = int(gold.get("cross_page_merges", 0))
    actual_merge_count = int(features["cross_page_merges"])
    return {
        "cer": error_rate(expected_text, features["text"], words=False),
        "wer": error_rate(expected_text, features["text"], words=True),
        "critical_span_exact_match": exact_match(expected_spans, features["critical_spans"]),
        "block_omission_rate": max(0.0, len(expected_types) - len(features["block_types"])) / max(1, len(expected_types)),
        "block_type_f1": f1(expected_types, features["block_types"]),
        "heading_hierarchy_f1": f1(expected_headings, features["heading_levels"]),
        "cross_page_merge_precision": safe_ratio(min(expected_merge_count, actual_merge_count), actual_merge_count),
        "cross_page_merge_recall": safe_ratio(min(expected_merge_count, actual_merge_count), expected_merge_count),
        "cell_exact_match": exact_match(expected_cells, features["cells"]),
        "row_column_span_f1": f1(expected_cell_spans, features["cell_spans"]),
        "critical_conflict_recall": safe_ratio(
            sum(value in features["critical_conflicts"] for value in expected_conflicts),
            len(expected_conflicts),
        ),
        "accepted_result_precision": safe_ratio(correct_accepted, len(accepted)),
        "automatic_coverage": safe_ratio(len(accepted), len(features["all_spans"])),
    }


def evaluate_manifest(manifest_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    manifest_file = Path(manifest_path)
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    entries: list[dict[str, Any]] = []
    by_type: dict[str, list[dict[str, float]]] = defaultdict(list)
    by_error_type: dict[str, list[dict[str, float]]] = defaultdict(list)
    for item in manifest.get("documents", []):
        gold_path = (manifest_file.parent / item["gold"]).resolve()
        prediction_path = (manifest_file.parent / item["prediction"]).resolve()
        gold = json.loads(gold_path.read_text(encoding="utf-8"))
        prediction = json.loads(prediction_path.read_text(encoding="utf-8"))
        metrics = _score_entry(gold, prediction)
        document_type = item.get("document_type", "unknown")
        by_type[document_type].append(metrics)
        for error_type in item.get("error_types", []):
            by_error_type[error_type].append(metrics)
        entries.append({
            "id": item["id"], "document_type": document_type,
            "gold": str(gold_path), "prediction": str(prediction_path), "metrics": metrics,
        })
    metric_names = sorted({name for entry in entries for name in entry["metrics"]})
    aggregate = {
        name: fmean(entry["metrics"][name] for entry in entries)
        for name in metric_names
    } if entries else {}
    type_breakdown = {
        document_type: {
            name: fmean(metrics[name] for metrics in records) for name in metric_names
        }
        for document_type, records in sorted(by_type.items())
    }
    error_breakdown = {
        error_type: {
            name: fmean(metrics[name] for metrics in records) for name in metric_names
        }
        for error_type, records in sorted(by_error_type.items())
    }
    report = {
        "schema_version": "1.0", "document_count": len(entries),
        "aggregate": aggregate, "by_document_type": type_breakdown,
        "by_error_type": error_breakdown,
        "documents": entries,
    }
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def enforce_regression_thresholds(report: dict[str, Any], thresholds: dict[str, float]) -> list[str]:
    failures: list[str] = []
    aggregate = report.get("aggregate", {})
    for configured_metric, threshold in thresholds.items():
        is_maximum = configured_metric.startswith("max_")
        metric = configured_metric[4:] if is_maximum else configured_metric
        value = aggregate.get(metric)
        if value is None:
            failures.append(f"missing metric: {metric}")
        elif is_maximum and value > threshold:
            failures.append(f"{metric}={value:.6f} above {threshold:.6f}")
        elif not is_maximum and value < threshold:
            failures.append(f"{metric}={value:.6f} below {threshold:.6f}")
    return failures
