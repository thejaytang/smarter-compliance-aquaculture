from __future__ import annotations

from ..models import Block, EvidenceSpan, Resolution, ResolutionStatus


def apply_abstention_policy(block: Block, spans: list[EvidenceSpan]) -> bool:
    ambiguous = [span for span in spans if span.resolution_status == ResolutionStatus.AMBIGUOUS]
    if not ambiguous or block.content is None:
        return False
    block.content.resolved_text = None
    block.content.resolution = Resolution(
        selected_source="none", reason="unresolved_critical_span", confidence=0.0
    )
    block.content.resolution_status = ResolutionStatus.AMBIGUOUS
    block.content.requires_human_review = True
    block.quality.requires_review = True
    if "unresolved_critical_span" not in block.quality.issues:
        block.quality.issues.append("unresolved_critical_span")
    return True
