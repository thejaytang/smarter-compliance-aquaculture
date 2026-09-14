from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import AppConfig
from .models import Document, ResolutionStatus
from .validate import validate_document


def evaluate_release(
    document: Document,
    config: AppConfig,
    performance: dict[str, object] | None = None,
    evaluation: dict[str, object] | None = None,
) -> dict[str, object]:
    checks: dict[str, bool] = {}
    checks["no_silent_missing_pages"] = (
        document.quality.processed_page_count == document.quality.input_page_count
        and all(report.status != "failed" for report in document.page_completeness)
    )
    checks["schema_and_references_valid"] = not validate_document(document)
    checks["critical_conflicts_gated"] = all(
        conflict.severity != "critical"
        or conflict.resolution_status != ResolutionStatus.AMBIGUOUS
        or conflict.block_id in document.review_queue
        for conflict in document.conflicts
    )
    precision = (
        document.quality.accepted_result_precision
        if document.quality.accepted_result_precision is not None
        else (evaluation or {}).get("aggregate", {}).get("accepted_result_precision")
    )
    checks["accepted_result_precision"] = (
        precision is not None
        and float(precision) >= config.evaluation.regression_thresholds["accepted_result_precision"]
    )
    checks["provenance_anchor_coverage"] = (
        (document.quality.provenance_anchor_coverage or 0)
        >= config.release.min_provenance_anchor_coverage
    )
    checks["human_review_rate"] = (
        (document.quality.human_review_rate or 0) <= config.release.max_human_review_rate
    )
    if evaluation:
        failures = evaluation.get("failures", [])
        checks["gold_regression"] = not failures
    else:
        checks["gold_regression"] = True
    if performance:
        checks["performance_budget"] = bool(performance.get("within_budget"))
    else:
        checks["performance_budget"] = False
    rdf = document.artifacts.get("rdf")
    shacl = document.artifacts.get("shacl_report")
    checks["ontology_artifacts"] = bool(rdf and shacl and Path(rdf.path).is_file() and Path(shacl.path).is_file())
    security_artifact = document.artifacts.get("security_report")
    security_report = (
        json.loads(Path(security_artifact.path).read_text(encoding="utf-8"))
        if security_artifact and Path(security_artifact.path).is_file() else {}
    )
    checks["security_policy"] = bool(
        security_report.get("passed")
        and security_report.get("policy", {}).get("document_content_sent_externally") is False
    )
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "failures": [name for name, passed in checks.items() if not passed],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scheme-three release gate")
    parser.add_argument("canonical", type=Path)
    parser.add_argument("--config", type=Path, default=Path("config/default.yaml"))
    parser.add_argument("--evaluation", type=Path)
    parser.add_argument("--output", type=Path, default=Path("release-gate-report.json"))
    args = parser.parse_args(argv)
    document = Document.model_validate_json(args.canonical.read_text(encoding="utf-8"))
    performance_path = args.canonical.parent / "performance-report.json"
    performance = json.loads(performance_path.read_text()) if performance_path.is_file() else None
    evaluation = json.loads(args.evaluation.read_text()) if args.evaluation and args.evaluation.is_file() else None
    report = evaluate_release(document, AppConfig.from_yaml(args.config), performance, evaluation)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
