from __future__ import annotations

import json
from pathlib import Path

from ..config import AppConfig
from ..models import BlockType, Document
from ..parsers import PARSER_ROUTES
from ..release_gate import evaluate_release


REQUIRED_ARTIFACTS = {
    "markdown", "html", "xml", "jsonl", "rag_chunks", "overlay_manifest",
    "regulatory_ir", "rdf", "shacl_report", "quality_report", "performance_report",
    "security_report", "verification_report",
}


def evaluate_full_system(
    document: Document,
    config: AppConfig,
    output_dir: str | Path,
    gold_report: dict[str, object] | None = None,
) -> dict[str, object]:
    output = Path(output_dir)
    ir_path = output / "regulatory-ir.json"
    ir = json.loads(ir_path.read_text(encoding="utf-8")) if ir_path.is_file() else {"statements": []}
    statements = ir.get("statements", [])
    ir_provenance = sum(
        bool(item.get("source_block_ids") and item.get("source_segment_ids") and item.get("source_page_indices"))
        for item in statements
    ) / max(1, len(statements))
    shacl_path = output / "ontology/shacl-report.json"
    shacl = json.loads(shacl_path.read_text(encoding="utf-8")) if shacl_path.is_file() else {"conforms": False}
    performance_path = output / "performance-report.json"
    performance = json.loads(performance_path.read_text(encoding="utf-8")) if performance_path.is_file() else None
    artifact_coverage = len(REQUIRED_ARTIFACTS & set(document.artifacts)) / len(REQUIRED_ARTIFACTS)
    content_blocks = [
        block for block in document.blocks.values()
        if block.type not in {BlockType.DOCUMENT, BlockType.SECTION}
    ]
    bbox_coverage = sum(bool(block.segments) for block in content_blocks) / max(1, len(content_blocks))
    metrics = {
        "page_completeness_rate": sum(report.status == "accepted" for report in document.page_completeness) / max(1, len(document.pages)),
        "parser_route_coverage": len(PARSER_ROUTES) / len(BlockType),
        "provenance_anchor_coverage": document.quality.provenance_anchor_coverage or bbox_coverage,
        "bbox_anchor_coverage": bbox_coverage,
        "regulatory_ir_provenance_coverage": ir_provenance,
        "shacl_conforms": bool(shacl.get("conforms")),
        "derived_artifact_coverage": artifact_coverage,
        "human_review_rate": document.quality.human_review_rate or 0,
        "seconds_per_page": performance.get("seconds_per_page") if performance else None,
        "peak_rss_mb": performance.get("peak_rss_mb") if performance else None,
    }
    release = evaluate_release(document, config, performance, gold_report)
    return {
        "schema_version": "1.0",
        "document_id": document.document_id,
        "metrics": metrics,
        "gold_aggregate": (gold_report or {}).get("aggregate"),
        "release_gate": release,
        "passed": release["passed"] and all((
            metrics["parser_route_coverage"] == 1,
            metrics["provenance_anchor_coverage"] >= config.release.min_provenance_anchor_coverage,
            metrics["regulatory_ir_provenance_coverage"] == 1,
            metrics["shacl_conforms"],
            metrics["derived_artifact_coverage"] == 1,
        )),
    }
