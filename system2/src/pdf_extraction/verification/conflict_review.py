"""Fail-closed routing for unresolved critical extraction conflicts."""

from __future__ import annotations

from ..models import Block, Conflict, ResolutionStatus, ReviewItem


def ensure_critical_conflicts_reviewable(
    blocks: dict[str, Block],
    conflicts: list[Conflict],
    review_items: list[ReviewItem],
) -> None:
    """Route every unresolved critical conflict through its owning block."""
    critical_by_block: dict[str, list[Conflict]] = {}
    for conflict in conflicts:
        if (
            conflict.severity == "critical"
            and conflict.resolution_status == ResolutionStatus.AMBIGUOUS
            and conflict.block_id in blocks
        ):
            critical_by_block.setdefault(conflict.block_id, []).append(conflict)

    for block_id, owner_conflicts in critical_by_block.items():
        block = blocks[block_id]
        block.quality.requires_review = True
        if "critical_text_conflict" not in block.quality.issues:
            block.quality.issues.append("critical_text_conflict")
        if any(
            item.target_id == block_id and item.status == "pending"
            for item in review_items
        ):
            continue
        review_items.append(ReviewItem(
            id=f"review_critical_conflict_{block_id}",
            target_id=block_id,
            reason="critical_conflict:" + ",".join(
                sorted({conflict.conflict_type for conflict in owner_conflicts})
            ),
            severity="critical",
            candidate_action="human_confirm_conflict",
            evidence_segment_ids=list(dict.fromkeys(
                segment_id
                for conflict in owner_conflicts
                for segment_id in conflict.evidence_segment_ids
            )),
        ))


__all__ = ["ensure_critical_conflicts_reviewable"]
