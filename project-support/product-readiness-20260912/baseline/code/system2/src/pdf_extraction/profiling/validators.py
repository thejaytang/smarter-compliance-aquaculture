from __future__ import annotations

import re

from ..models import Block, BlockType, Page, ReviewItem
from .models import DocumentProfile


def _block_text(block: Block) -> str:
    values: list[str] = []
    if block.content:
        values.append(
            block.content.resolved_text or block.content.native_text or block.content.ocr_text or ""
        )
    if block.table:
        values.extend(
            cell.content.resolved_text or cell.content.native_text or cell.content.ocr_text or ""
            for cell in block.table.cells
        )
    return " ".join(values)


def _requirement_structure_reviews(
    blocks: dict[str, Block], profile: DocumentProfile, page_indices: set[int]
) -> list[ReviewItem]:
    reviews: list[ReviewItem] = []
    blocks_by_page: dict[int, list[Block]] = {}
    for block in blocks.values():
        for segment in block.segments:
            blocks_by_page.setdefault(segment.page_index, []).append(block)
    for candidate in profile.requirement_candidates:
        if candidate.page_index not in page_indices:
            continue
        pattern = re.compile(rf"(?<!\d){re.escape(candidate.requirement_number)}(?!\d)")
        owners = [
            block for block in blocks_by_page.get(candidate.page_index, [])
            if pattern.search(_block_text(block))
        ]
        well_formed = False
        for block in owners:
            if block.type != BlockType.TABLE or not block.table or block.table.column_count != 2:
                continue
            for cell in block.table.cells:
                if cell.column != 0 or not pattern.match(
                    (cell.content.resolved_text or "").strip()
                ):
                    continue
                peer = next(
                    (
                        item for item in block.table.cells
                        if item.row == cell.row and item.column == 1
                        and (item.content.resolved_text or "").strip()
                    ),
                    None,
                )
                if peer is not None:
                    well_formed = True
                    break
            if well_formed:
                break
        if well_formed:
            continue
        reviews.append(ReviewItem(
            id=f"review_requirement_template_p{candidate.page_index:04d}_{candidate.requirement_number.replace('.', '_')}",
            target_id=f"page:{candidate.page_index}",
            reason="requirement_template_structure_mismatch",
            severity="critical",
            candidate_action="reparse_indicator_requirement_region",
            confidence=candidate.confidence,
            evidence_segment_ids=[
                segment.id for block in owners for segment in block.segments
            ],
        ))
    return reviews


def _cross_page_table_reviews(
    blocks: dict[str, Block], pages: dict[int, Page]
) -> list[ReviewItem]:
    tables = sorted(
        (block for block in blocks.values() if block.type == BlockType.TABLE and block.table and block.segments),
        key=lambda block: (block.segments[0].page_index, block.segments[0].bbox.y0),
    )
    reviews: list[ReviewItem] = []
    for left, right in zip(tables, tables[1:], strict=False):
        left_segment, right_segment = left.segments[-1], right.segments[0]
        if (
            right_segment.page_index != left_segment.page_index + 1
            or left_segment.page_index not in pages
            or right_segment.page_index not in pages
            or right.index
            or left.parent_id != right.parent_id
        ):
            continue
        left_page, right_page = pages[left_segment.page_index], pages[right_segment.page_index]
        left_width = left_segment.bbox.x1 - left_segment.bbox.x0
        right_width = right_segment.bbox.x1 - right_segment.bbox.x0
        same_band = min(left_width, right_width) / max(left_width, right_width) >= 0.88
        boundary_position = (
            left_segment.bbox.y1 >= left_page.height * 0.72
            and right_segment.bbox.y0 <= right_page.height * 0.28
        )
        if same_band and boundary_position and left.table.column_count != right.table.column_count:
            reviews.append(ReviewItem(
                id=f"review_cross_page_columns_{left.id}_{right.id}",
                target_id=left.id,
                reason="cross_page_table_column_mismatch",
                severity="critical",
                candidate_action=f"reparse_with:{right.id}",
                confidence=0.92,
                evidence_segment_ids=[left_segment.id, right_segment.id],
            ))
    return reviews


def _terminal_evidence_reviews(blocks: dict[str, Block]) -> list[ReviewItem]:
    reviews: list[ReviewItem] = []
    terminal = re.compile(r"[.!?:;]\s*$")
    for block in blocks.values():
        if block.type != BlockType.PARAGRAPH or not block.content or not block.segments:
            continue
        native = (block.content.native_text or "").strip()
        ocr = (block.content.ocr_text or "").strip()
        resolved = (block.content.resolved_text or "").strip()
        if len(resolved) < 40 or terminal.search(resolved):
            continue
        evidence_has_terminal = bool(terminal.search(native) or terminal.search(ocr))
        if not evidence_has_terminal:
            continue
        reviews.append(ReviewItem(
            id=f"review_terminal_evidence_{block.id}",
            target_id=block.id,
            reason="terminal_punctuation_missing_from_resolved_text",
            severity="warning",
            candidate_action="compare_native_and_ocr_terminal",
            confidence=0.90,
            evidence_segment_ids=[segment.id for segment in block.segments],
        ))
    return reviews


def validate_profile_consistency(
    blocks: dict[str, Block],
    pages: list[Page],
    profile: DocumentProfile,
    *,
    validate_requirement_sequence: bool = True,
    validate_cross_page_columns: bool = True,
    validate_terminal_evidence: bool = True,
) -> list[ReviewItem]:
    page_lookup = {page.page_index: page for page in pages}
    reviews: list[ReviewItem] = []
    if validate_requirement_sequence:
        reviews.extend(_requirement_structure_reviews(blocks, profile, set(page_lookup)))
    if validate_cross_page_columns:
        reviews.extend(_cross_page_table_reviews(blocks, page_lookup))
    if validate_terminal_evidence:
        reviews.extend(_terminal_evidence_reviews(blocks))
    return reviews
