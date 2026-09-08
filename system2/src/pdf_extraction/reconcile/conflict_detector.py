from __future__ import annotations

from ..models import Conflict, EvidenceSpan, ModelRecord, ResolutionStatus


CONFLICT_TYPES = {
    "numeric": "critical_numeric_conflict",
    "unit": "unit_conflict",
    "date": "date_conflict",
    "section_reference": "section_reference_conflict",
    "negation": "negation_conflict",
    "modality": "modality_conflict",
    "comparison_operator": "comparison_operator_conflict",
    "general": "general_text_conflict",
}


def conflicts_from_spans(
    spans: list[EvidenceSpan], models: list[ModelRecord], start_index: int = 0
) -> list[Conflict]:
    versions = [
        f"{model.name}:{model.version or 'unknown'}" for model in models
        if model.role in {"native_extraction", "ocr", "precision_review"}
    ]
    output: list[Conflict] = []
    for span in spans:
        missing_one_side = bool(span.native_text) != bool(span.ocr_text)
        if missing_one_side and span.resolution_status == ResolutionStatus.AMBIGUOUS:
            conflict_type = "missing_content_conflict"
        elif not span.native_text or not span.ocr_text:
            continue
        else:
            normalized = lambda value: value.casefold().replace(",", ".")
            if normalized(span.native_text) == normalized(span.ocr_text):
                continue
            conflict_type = CONFLICT_TYPES[span.criticality]
        output.append(Conflict(
            id=f"conflict_{start_index + len(output):05d}", block_id=span.block_id,
            native_value=span.native_text, ocr_value=span.ocr_text,
            review_value=span.review_text, conflict_type=conflict_type,
            severity="critical",
            status=("review_required" if span.resolution_status == ResolutionStatus.AMBIGUOUS else "resolved"),
            evidence_segment_ids=[span.segment_id], evidence_span_ids=[span.id],
            bbox=span.bbox, trigger_rules=span.trigger_rules,
            model_versions=versions, resolution_status=span.resolution_status,
        ))
    return output
