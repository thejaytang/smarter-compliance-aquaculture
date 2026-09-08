from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..config import AppConfig
from ..delivery import write_derived_artifacts
from ..models import AuditEvent, Document, DocumentStatus, Resolution, ResolutionStatus
from ..validate import validate_document
from ..verification.document_state import refresh_document_state, unresolved


# Text decisions cannot resolve layout, completeness, or semantic ownership.
TEXT_REVIEW_REASONS = {
    'critical_text_conflict', 'unresolved_critical_span',
    'table_cell_text_conflict', 'table_cell_text_omission',
    'atomic_verification_review', 'source_fidelity_unresolved',
    'secondary_native_critical_mismatch',
    'low_ocr_confidence_on_visual_page',
}


def _text_review(reason: str, *, span: bool = False) -> bool:
    return (span and reason.startswith('atomic_verification:')) or (
        bool(reason) and all(token in TEXT_REVIEW_REASONS for token in reason.split(';'))
    )


class ReviewDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor: str = Field(min_length=1)
    action: Literal["accept", "modify", "reject", "unreadable"]
    target_type: Literal["block", "span", "cell"]
    target_id: str
    new_value: str | None = None
    reason: str | None = None

    @field_validator('actor')
    @classmethod
    def named_actor(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('actor must name a human')
        return value.strip()

    @model_validator(mode="after")
    def modification_has_value(self) -> "ReviewDecision":
        if self.action == "modify" and self.new_value is None:
            raise ValueError("modify requires new_value")
        return self


class PageLabelDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor: str = Field(min_length=1)
    page_index: int = Field(ge=0)
    label: str = Field(min_length=1)
    reason: str | None = None

    _named_actor = field_validator('actor')(ReviewDecision.named_actor.__func__)


def _hash(value: str | None) -> str | None:
    return hashlib.sha256(value.encode()).hexdigest() if value is not None else None


def _target(document: Document, decision: ReviewDecision):
    if decision.target_type == "block":
        block = document.blocks.get(decision.target_id)
        if block is None or block.content is None:
            raise KeyError(f"reviewable block not found: {decision.target_id}")
        return block.content
    if decision.target_type == "span":
        span = document.evidence_spans.get(decision.target_id)
        if span is None:
            raise KeyError(f"evidence span not found: {decision.target_id}")
        return span
    for block in document.blocks.values():
        if block.table:
            for cell in block.table.cells:
                if cell.id == decision.target_id:
                    return cell.content
    raise KeyError(f"table cell not found: {decision.target_id}")


def apply_review_decision(
    canonical_path: str | Path,
    decision: ReviewDecision,
    config: AppConfig,
) -> Document:
    path = Path(canonical_path)
    document = Document.model_validate_json(path.read_text(encoding="utf-8"))
    target = _target(document, decision)
    previous = target.resolved_text
    reviewed_block = document.blocks.get(decision.target_id) if decision.target_type == "block" else None
    if decision.target_type == "span":
        reviewed_block = document.blocks[document.evidence_spans[decision.target_id].block_id]
    elif decision.target_type == "cell":
        reviewed_block = next(
            block for block in document.blocks.values()
            if block.table and any(cell.id == decision.target_id for cell in block.table.cells)
        )

    def set_resolution(selected_source: str, reason: str, confidence: float) -> None:
        if hasattr(target, "resolution"):
            target.resolution = Resolution(
                selected_source=selected_source, reason=reason, confidence=confidence
            )
        else:
            target.confidence = confidence
    if decision.action == "modify":
        target.review_text = decision.new_value
        target.resolved_text = decision.new_value
        target.resolution_status = ResolutionStatus.HUMAN_CONFIRMED
        target.requires_human_review = False
        set_resolution("review", "human_modified", 1.0)
    elif decision.action == "accept":
        accepted = decision.new_value or target.resolved_text or target.review_text or target.native_text or target.ocr_text
        if accepted is None:
            raise ValueError("cannot accept target without an evidence value")
        target.review_text = accepted
        target.resolved_text = accepted
        target.resolution_status = ResolutionStatus.HUMAN_CONFIRMED
        target.requires_human_review = False
        set_resolution("review", "human_accepted", 1.0)
    else:
        target.resolved_text = None
        target.resolution_status = ResolutionStatus.UNREADABLE
        target.requires_human_review = True
        set_resolution("none", f"human_{decision.action}", 1.0)
    document.revision += 1
    if decision.target_type == "span" and reviewed_block and reviewed_block.content:
        owner_spans = [
            span for span in document.evidence_spans.values()
            if span.block_id == reviewed_block.id
        ]
        if all(
            not unresolved(span)
            for span in owner_spans
        ):
            rebuilt = reviewed_block.content.native_text or reviewed_block.content.ocr_text or ""
            edits = []
            for span in owner_spans:
                source_token = span.native_text or span.ocr_text
                matches = list(re.finditer(re.escape(source_token), rebuilt)) if source_token else []
                if len(matches) != 1 or span.resolved_text is None:
                    break
                edits.append((matches[0].start(), matches[0].end(), span.resolved_text))
            edits.sort()
            unique = len(edits) == len(owner_spans) and all(
                a[1] <= b[0] for a, b in zip(edits, edits[1:])
            )
            if unique:
                for start, end, text in reversed(edits):
                    rebuilt = rebuilt[:start] + text + rebuilt[end:]
                reviewed_block.content.review_text = rebuilt
                reviewed_block.content.resolved_text = rebuilt
                reviewed_block.content.resolution_status = ResolutionStatus.HUMAN_CONFIRMED
                reviewed_block.content.requires_human_review = False
                reviewed_block.content.resolution = Resolution(
                    selected_source="review", reason="human_resolved_all_evidence_spans",
                    confidence=1.0,
                )
            else:
                # Character offsets are not part of the span contract yet.
                # Repeated or overlapping tokens require a block-level decision.
                reviewed_block.content.resolved_text = None
                reviewed_block.content.resolution_status = ResolutionStatus.AMBIGUOUS
                reviewed_block.content.requires_human_review = True
    owner_resolved = False
    if reviewed_block is not None:
        unresolved_spans = any(
            span.block_id == reviewed_block.id
            and (
                unresolved(span)
            )
            for span in document.evidence_spans.values()
        )
        unresolved_cells = bool(reviewed_block.table and any(
            unresolved(cell.content)
            for cell in reviewed_block.table.cells
        ))
        unresolved_content = bool(
            reviewed_block.content
            and unresolved(reviewed_block.content)
        )
        owner_resolved = not (unresolved_spans or unresolved_cells or unresolved_content)
        if owner_resolved:
            reviewed_block.quality.issues = [
                issue for issue in reviewed_block.quality.issues
                if issue not in {
                    "critical_text_conflict", "unresolved_critical_span",
                    "table_cell_text_conflict", "table_cell_text_omission",
                    "atomic_verification_review",
                    "secondary_native_critical_mismatch",
                }
            ]
            reviewed_block.quality.requires_review = bool(reviewed_block.quality.issues)
            if decision.action in {'accept', 'modify'}:
                for conflict in document.conflicts:
                    if conflict.block_id != reviewed_block.id:
                        continue
                    span_confirmed = bool(conflict.evidence_span_ids) and all(
                        span_id in document.evidence_spans
                        and document.evidence_spans[span_id].resolution_status == ResolutionStatus.HUMAN_CONFIRMED
                        for span_id in conflict.evidence_span_ids
                    )
                    if span_confirmed or (decision.target_type == 'block' and not conflict.evidence_span_ids):
                        conflict.resolution_status = ResolutionStatus.HUMAN_CONFIRMED
                        conflict.status = 'resolved'
                        conflict.review_value = target.resolved_text
    event = AuditEvent(
        id=f"audit_{document.revision:08d}",
        timestamp=datetime.now(timezone.utc).isoformat(),
        actor=decision.actor,
        action=decision.action,
        target_type=decision.target_type,
        target_id=decision.target_id,
        previous_value_hash=_hash(previous),
        new_value=(target.resolved_text if decision.action in {"accept", "modify"} else None),
        reason=decision.reason,
        revision=document.revision,
    )
    document.audit_events.append(event)
    if previous != target.resolved_text or decision.action in {'reject', 'unreadable'}:
        # The existing Requirement source regions have no complete block-to-field
        # dependency map. Keep all domain results reviewable until recomputed.
        from ..models.requirement import RequirementStatus
        for requirement in document.requirements:
            requirement.status = RequirementStatus.REVIEW_REQUIRED
            requirement.confidence = None
            if 'source_text_changed_after_extraction' not in requirement.validation_flags:
                requirement.validation_flags.append('source_text_changed_after_extraction')
    for item in document.review_items:
        direct = (
            item.target_id == decision.target_id
            and _text_review(item.reason, span=decision.target_type == 'span')
            and (decision.target_type != 'block' or owner_resolved)
        )
        owner_evidence_review = (
            reviewed_block is not None and owner_resolved and item.target_id == reviewed_block.id
            and _text_review(item.reason)
        )
        if decision.action in {'accept', 'modify'} and (direct or owner_evidence_review):
            item.status = {
                "accept": "accepted", "modify": "modified",
                "reject": "rejected", "unreadable": "unreadable",
            }[decision.action]
    refresh_document_state(document)
    errors = validate_document(document)
    document.quality.validation_errors = errors
    if errors:
        document.quality.status = DocumentStatus.FAILED
        raise ValueError("review decision produced invalid document: " + "; ".join(errors))
    output_dir = path.parent
    write_derived_artifacts(document, output_dir, config)
    path.write_text(
        json.dumps(document.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    audit_path = output_dir / "audit-events.jsonl"
    with audit_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event.model_dump(mode="json"), ensure_ascii=False) + "\n")
    return document


def correct_page_label(
    canonical_path: str | Path,
    decision: PageLabelDecision,
    config: AppConfig,
) -> Document:
    path = Path(canonical_path)
    document = Document.model_validate_json(path.read_text(encoding="utf-8"))
    page = next(
        (item for item in document.pages if item.page_index == decision.page_index), None
    )
    if page is None:
        raise IndexError("page_index out of range")
    previous = page.page_label_correction or page.printed_page_label or page.pdf_page_label
    page.page_label_correction = decision.label
    page.page_label_source = "human"
    page.page_label_confidence = 1.0
    document.revision += 1
    event = AuditEvent(
        id=f"audit_{document.revision:08d}", actor=decision.actor, action="modify",
        target_type="page_label", target_id=f"page:{decision.page_index}",
        previous_value_hash=_hash(previous), new_value=decision.label,
        reason=decision.reason, revision=document.revision,
    )
    document.audit_events.append(event)
    errors = validate_document(document)
    if errors:
        raise ValueError("page-label correction produced invalid document: " + "; ".join(errors))
    write_derived_artifacts(document, path.parent, config)
    path.write_text(document.model_dump_json(indent=2), encoding="utf-8")
    with (path.parent / "audit-events.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event.model_dump(mode="json"), ensure_ascii=False) + "\n")
    return document
