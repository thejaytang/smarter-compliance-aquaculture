from __future__ import annotations

import re

from ..config import AssemblySettings
from ..models import Block, BlockType, Page, Resolution, ResolutionStatus, ReviewItem


def _join_text(left: str | None, right: str | None) -> str | None:
    if not left and not right:
        return None
    if not left:
        return right
    if not right:
        return left
    last_token = left.rsplit(maxsplit=1)[-1]
    preserve_compound_hyphen = (
        "http://" in last_token
        or "https://" in last_token
        or "www." in last_token
        or last_token.count("-") >= 2
        or "-" in right.split(maxsplit=1)[0]
    )
    if left.endswith("-") and re.match(r"^[a-z]", right):
        return left + right.lstrip() if preserve_compound_hyphen else left[:-1] + right.lstrip()
    return f"{left.rstrip()} {right.lstrip()}"


def _score(left: Block, right: Block, pages: dict[int, Page]) -> float:
    left_segment, right_segment = left.segments[-1], right.segments[0]
    left_page, right_page = pages[left_segment.page_index], pages[right_segment.page_index]
    compatible_types = left.type == right.type or (
        left.type == BlockType.LIST and right.type == BlockType.PARAGRAPH
    )
    if not compatible_types or left.parent_id != right.parent_id:
        return 0.0
    left_text = (
        left.content.resolved_text or left.content.native_text or left.content.ocr_text
        if left.content else None
    )
    right_text = (
        right.content.resolved_text or right.content.native_text or right.content.ocr_text
        if right.content else None
    )
    if left_text and left_text.strip().casefold() in {"n/a", "not applicable"}:
        return 0.0
    if right_segment.page_index == left_segment.page_index:
        gap = right_segment.bbox.y0 - left_segment.bbox.y1
        left_height = left_segment.bbox.y1 - left_segment.bbox.y0
        right_height = right_segment.bbox.y1 - right_segment.bbox.y0
        line_height = max(left_height, right_height)
        horizontal_overlap = max(
            0.0,
            min(left_segment.bbox.x1, right_segment.bbox.x1)
            - max(left_segment.bbox.x0, right_segment.bbox.x0),
        )
        narrow_width = max(
            1.0,
            min(
                left_segment.bbox.x1 - left_segment.bbox.x0,
                right_segment.bbox.x1 - right_segment.bbox.x0,
            ),
        )
        unmatched_parenthesis = (
            bool(left_text and right_text)
            and left_text.count("(") > left_text.count(")")
            and ")" in right_text
        )
        connector_fragment = bool(
            right_text
            and right_text.strip().casefold() in {"and", "or"}
            and left_text
            and not re.search(r"[.!?。！？]\s*$", left_text)
        )
        citation_suffix = bool(
            right_text
            and re.fullmatch(r"p{1,2}\.", right_text.strip(), flags=re.I)
            and left_text
        )
        if (
            (
                (left.type == BlockType.PARAGRAPH and right.type == BlockType.PARAGRAPH)
                or (left.type == BlockType.LIST and right.type == BlockType.PARAGRAPH)
                or (unmatched_parenthesis and left.type == right.type == BlockType.LIST)
                or ((connector_fragment or citation_suffix) and left.type == right.type == BlockType.LIST)
            )
            and -2 <= gap <= max(14.0, line_height * 1.2)
            and line_height <= 32
            and (
                abs(left_segment.bbox.x0 - right_segment.bbox.x0) <= 28
                or unmatched_parenthesis
                or connector_fragment
                or citation_suffix
            )
            and (horizontal_overlap / narrow_width >= 0.70 or connector_fragment or citation_suffix)
            and left_text
            and (
                unmatched_parenthesis
                or connector_fragment
                or citation_suffix
                or not re.search(r"[.!?:;。！？：；]\s*$", left_text)
            )
            and right_text
        ):
            return 0.95 if connector_fragment or citation_suffix else 0.90
        return 0.0
    if right_segment.page_index != left_segment.page_index + 1:
        return 0.0
    if left.type == right.type == BlockType.LIST and right.list_marker:
        return 0.0
    score = 0.15
    score += 0.2 if left_segment.bbox.y1 >= left_page.height * 0.78 else 0.0
    score += 0.2 if right_segment.bbox.y0 <= right_page.height * 0.22 else 0.0
    score += 0.1 if abs(left_segment.bbox.x0 - right_segment.bbox.x0) <= 28 else 0.0
    if left.type == BlockType.LIST and right_text and re.match(
        r"^(?:[A-Za-z]\)|[A-Za-z]\.|\d+[.)]|[•●▪])\s*", right_text
    ):
        return 0.0
    if left_text and not re.search(r"[.!?:;]\s*$", left_text):
        score += 0.2
    if left_text and left_text.endswith("-"):
        score += 0.1
    if right_text and re.match(r"^[a-z]", right_text):
        score += 0.1
    return min(1.0, score)


def _remove_block(blocks: dict[str, Block], pages: dict[int, Page], block_id: str, replacement: str) -> None:
    block = blocks[block_id]
    if block.parent_id and block.parent_id in blocks:
        parent = blocks[block.parent_id]
        parent.children = [child for child in parent.children if child != block_id]
    for page in pages.values():
        if block_id in page.block_ids:
            page.block_ids = list(dict.fromkeys(
                replacement if item == block_id else item for item in page.block_ids
            ))
    del blocks[block_id]


def assemble_paragraphs(
    blocks: dict[str, Block], pages: list[Page], settings: AssemblySettings,
    replacements: dict[str, str] | None = None,
) -> list[ReviewItem]:
    page_lookup = {page.page_index: page for page in pages}
    candidates = [
        block for block in blocks.values()
        if block.type in {BlockType.PARAGRAPH, BlockType.LIST} and block.segments and block.content
    ]
    candidates.sort(key=lambda block: (block.segments[0].page_index, block.segments[0].bbox.y0))
    reviews: list[ReviewItem] = []
    index = 0
    while index < len(candidates) - 1:
        left, right = candidates[index], candidates[index + 1]
        intervening_boundary = False
        intervening_footnote_band = False
        if left.parent_id and left.parent_id in blocks:
            siblings = blocks[left.parent_id].children
            if left.id in siblings and right.id in siblings:
                start, end = sorted((siblings.index(left.id), siblings.index(right.id)))
                intervening_boundary = any(
                    sibling in blocks and blocks[sibling].type in {
                        BlockType.HEADING, BlockType.TABLE, BlockType.FIGURE,
                    }
                    for sibling in siblings[start + 1:end]
                )
                intervening_footnote_band = any(
                    sibling in blocks
                    and blocks[sibling].type == BlockType.FOOTNOTE
                    and blocks[sibling].segments
                    and blocks[sibling].segments[0].page_index == left.segments[-1].page_index
                    for sibling in siblings[start + 1:end]
                )
        score = 0.0 if intervening_boundary else _score(left, right, page_lookup)
        left_text = left.content.resolved_text or "" if left.content else ""
        right_text = right.content.resolved_text or "" if right.content else ""
        if (
            intervening_footnote_band
            and right.segments[0].page_index == left.segments[-1].page_index + 1
            and score >= settings.paragraph_review_threshold
            and left_text and not re.search(r"[.!?:;]\s*$", left_text)
            and re.match(r"^[a-z]", right_text)
        ):
            score = min(1.0, score + 0.2)
        if score >= settings.paragraph_auto_merge_threshold:
            merge_kind = (
                "same_page_fragment"
                if left.segments[-1].page_index == right.segments[0].page_index
                else "cross_page_continuation"
            )
            left.segments.extend(right.segments)
            if left.content and right.content:
                left.content.native_text = _join_text(left.content.native_text, right.content.native_text)
                left.content.ocr_text = _join_text(left.content.ocr_text, right.content.ocr_text)
                left.content.review_text = _join_text(left.content.review_text, right.content.review_text)
                left.content.resolved_text = _join_text(left.content.resolved_text, right.content.resolved_text)
                if left.content.resolved_text is None:
                    left.content.resolution = Resolution(
                        selected_source="none", reason="merged_with_unresolved_fragment", confidence=0
                    )
                    left.content.resolution_status = ResolutionStatus.AMBIGUOUS
                    left.content.requires_human_review = True
            left.operations.append({
                "operation": "paragraph_fragment_merge",
                "merge_kind": merge_kind,
                "source_fragment_ids": [left.id, right.id],
                "confidence": score,
                "decision": "auto_merge",
            })
            if replacements is not None:
                replacements[right.id] = left.id
            _remove_block(blocks, page_lookup, right.id, left.id)
            candidates.pop(index + 1)
        elif score >= settings.paragraph_review_threshold:
            reviews.append(ReviewItem(
                id=f"review_paragraph_merge_{left.id}_{right.id}", target_id=left.id,
                reason="cross_page_paragraph_candidate", severity="warning",
                candidate_action=f"merge_with:{right.id}", confidence=score,
                evidence_segment_ids=[left.segments[-1].id, right.segments[0].id],
            ))
            index += 1
        else:
            index += 1
    return reviews
