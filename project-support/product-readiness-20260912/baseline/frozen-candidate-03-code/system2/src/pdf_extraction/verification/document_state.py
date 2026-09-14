"""Conservative document status aggregation, independent of export formats."""
from ..models import Document, DocumentStatus, ProcessingStatus, ResolutionStatus, ReviewItem


def unresolved(content) -> bool:
    return bool(content and (
        content.requires_human_review
        or content.resolution_status in {ResolutionStatus.AMBIGUOUS, ResolutionStatus.UNREADABLE}
    ))


def refresh_document_state(document: Document) -> None:
    """Keep unresolved evidence visible; only a source decision can clear it."""
    def require(target: str, reason: str) -> None:
        if any(i.target_id == target and i.status == 'pending' for i in document.review_items):
            return
        review_id = f'review_fidelity_{target}'
        existing = next((i for i in document.review_items if i.id == review_id), None)
        if existing:
            existing.status = 'pending'
        else:
            document.review_items.append(ReviewItem(
                id=review_id, target_id=target, reason=reason, severity='critical',
                candidate_action='verify_source_or_reparse',
            ))

    for block in document.blocks.values():
        evidence_pending = (
            unresolved(block.content)
            or any(s.block_id == block.id and unresolved(s) for s in document.evidence_spans.values())
            or bool(block.table and any(unresolved(c.content) for c in block.table.cells))
        )
        if evidence_pending:
            block.quality.requires_review = True
            require(block.id, 'source_fidelity_unresolved')
        elif block.quality.requires_review:
            require(block.id, 'block_quality_requires_review')
    for page in document.page_completeness:
        if page.status != 'accepted':
            require(f'page:{page.page_index}', 'page_completeness_gate')
    for conflict in document.conflicts:
        if conflict.severity == 'critical' and conflict.resolution_status in {
            ResolutionStatus.AMBIGUOUS, ResolutionStatus.UNREADABLE,
        }:
            require(conflict.block_id, 'unresolved_critical_span')
    for requirement in document.requirements:
        if 'source_text_changed_after_extraction' in requirement.validation_flags:
            require(f'requirement:{requirement.requirement_id}', 'requirement_semantics_stale_after_review')
    document.review_queue = list(dict.fromkeys(
        item.target_id for item in document.review_items if item.status == 'pending'
    ))
    if (document.quality.status == DocumentStatus.FAILED
        or document.quality.validation_errors
        or any(p.status == 'failed' for p in document.page_completeness)):
        document.quality.status = DocumentStatus.FAILED
    else:
        document.quality.status = (
            DocumentStatus.REVIEW_REQUIRED if document.review_queue else DocumentStatus.ACCEPTED
        )
    if document.processing.status in {
        ProcessingStatus.ACCEPTED, ProcessingStatus.REVIEW_REQUIRED, ProcessingStatus.FAILED,
    }:
        document.processing.status = ProcessingStatus(document.quality.status.value)
