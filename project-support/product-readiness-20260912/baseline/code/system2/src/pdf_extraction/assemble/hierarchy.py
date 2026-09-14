from __future__ import annotations

from ..models import Block, BlockType


def repair_sibling_orders(blocks: dict[str, Block]) -> None:
    """Make child arrays authoritative and repair local order fields after assembly."""
    for parent in blocks.values():
        for order, child_id in enumerate(parent.children):
            child = blocks.get(child_id)
            if child is not None:
                child.parent_id = parent.id
                child.order_in_parent = order


def repair_list_hierarchy(blocks: dict[str, Block]) -> None:
    """Nest consecutive list items using recovered marker indentation levels."""
    for parent in list(blocks.values()):
        original_children = list(parent.children)
        if not original_children:
            continue
        rebuilt: list[str] = []
        level_stack: dict[int, Block] = {}
        for child_id in original_children:
            child = blocks.get(child_id)
            if child is None:
                continue
            if child.type != BlockType.LIST or child.list_level is None:
                rebuilt.append(child_id)
                level_stack.clear()
                continue
            level = child.list_level
            for stale_level in [value for value in level_stack if value >= level]:
                level_stack.pop(stale_level, None)
            ancestor = next(
                (level_stack[candidate] for candidate in range(level - 1, -1, -1)
                 if candidate in level_stack),
                None,
            )
            if level > 0 and ancestor is not None:
                child.parent_id = ancestor.id
                ancestor.children.append(child.id)
            else:
                rebuilt.append(child_id)
                child.parent_id = parent.id
                # A list may begin at an indented level because the excerpt
                # starts mid-list. Keep its measured level but do not invent a parent.
            level_stack[level] = child
        parent.children = rebuilt


def repair_heading_hierarchy(blocks: dict[str, Block]) -> None:
    """Use explicit numbering as the anchor for heading levels.

    Layout models commonly promote a short heading at the top of a continuation
    page to document-title level. Once a numbered/criterion heading exists, an
    unnumbered peer cannot be level 1 solely because it starts a page.
    """
    import re

    headings = [
        block for block in blocks.values()
        if block.type == BlockType.HEADING and block.content and block.content.resolved_text
    ]
    has_explicit_root = False
    for block in headings:
        text = block.content.resolved_text.strip()
        criterion = re.match(r"^Criterion\s+(\d+(?:\.\d+)*)\b", text, flags=re.I)
        numbered = re.match(r"^(\d+(?:\.\d+)*)\s+\S", text)
        match = criterion or numbered
        if not match:
            continue
        depth = len(match.group(1).split("."))
        block.heading_level = max(1, min(6, depth - 1 if criterion else depth))
        has_explicit_root = has_explicit_root or block.heading_level == 1
    if has_explicit_root:
        for block in headings:
            text = block.content.resolved_text.strip()
            if not re.match(r"^(?:Criterion\s+)?\d+(?:\.\d+)*\b", text, flags=re.I):
                block.heading_level = max(2, block.heading_level or 2)
