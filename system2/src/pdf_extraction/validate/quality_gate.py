from __future__ import annotations

from collections import Counter

from ..models import Document
from .fingerprint import structural_fingerprint


def build_quality_report(document: Document) -> dict[str, object]:
    return {
        "document_id": document.document_id,
        "structural_fingerprint": structural_fingerprint(document),
        "status": document.quality.status.value,
        "input_page_count": document.quality.input_page_count,
        "processed_page_count": document.quality.processed_page_count,
        "page_kinds": dict(Counter(page.page_kind for page in document.pages)),
        "block_counts": document.quality.block_counts,
        "unknown_block_count": document.quality.unknown_block_count,
        "unassigned_native_object_count": document.quality.unassigned_native_object_count,
        "low_confidence_block_ids": document.quality.low_confidence_block_ids,
        "suspected_cross_page_fragments": document.quality.suspected_cross_page_fragments,
        "conflicts": [conflict.model_dump(mode="json") for conflict in document.conflicts],
        "conflict_counts": dict(Counter(conflict.conflict_type for conflict in document.conflicts)),
        "evidence_span_count": len(document.evidence_spans),
        "critical_span_counts": dict(Counter(
            span.criticality for span in document.evidence_spans.values()
        )),
        "review_queue": document.review_queue,
        "review_items": [item.model_dump(mode="json") for item in document.review_items],
        "page_completeness": [
            report.model_dump(mode="json") for report in document.page_completeness
        ],
        "accepted_result_precision": document.quality.accepted_result_precision,
        "automatic_coverage": document.quality.automatic_coverage,
        "provenance_anchor_coverage": document.quality.provenance_anchor_coverage,
        "human_review_rate": document.quality.human_review_rate,
        "validation_errors": document.quality.validation_errors,
        "warnings": document.quality.warnings,
        "models": [model.model_dump(mode="json") for model in document.processing.models],
        "processing": document.processing.model_dump(mode="json"),
        "audit_event_count": len(document.audit_events),
    }
