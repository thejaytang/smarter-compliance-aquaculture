from __future__ import annotations

import os
import re
from pathlib import Path

from ...models import Block, BlockType, Document


def _markdown_cell_text(value: str) -> str:
    lines = value.splitlines() or [value]
    rendered: list[str] = []
    for line in lines:
        leading = len(line) - len(line.lstrip(" "))
        text = line.lstrip(" ").replace("|", "\\|")
        rendered.append("&nbsp;" * leading + text)
    return "<br>".join(rendered)


def _table_markdown(block: Block) -> list[str]:
    if not block.table:
        return []
    lookup = {(cell.row, cell.column): cell for cell in block.table.cells}
    rows: list[list[str]] = []
    for row in range(block.table.row_count):
        rows.append([
            _markdown_cell_text(lookup.get((row, column)).content.resolved_text or "")
            if lookup.get((row, column)) else ""
            for column in range(block.table.column_count)
        ])
    if not rows:
        return []
    lines = ["| " + " | ".join(rows[0]) + " |"]
    lines.append("| " + " | ".join("---" for _ in rows[0]) + " |")
    lines.extend("| " + " | ".join(row) + " |" for row in rows[1:])
    return lines


def _asset_ref(value: str, asset_base: Path) -> str:
    if "://" in value or value.startswith("data:"):
        return value
    return Path(os.path.relpath(Path(value).resolve(), start=asset_base.resolve())).as_posix()


def _render_block(
    document: Document,
    block: Block,
    depth: int,
    lines: list[str],
    asset_base: Path,
) -> None:
    if block.type in {BlockType.HEADER, BlockType.FOOTER, BlockType.FOOTNOTE}:
        return
    if block.content and block.content.requires_human_review and block.content.resolved_text is None:
        lines.extend([f"[REVIEW REQUIRED: {block.id}]", ""])
    if block.type == BlockType.HEADING and block.content and block.content.resolved_text:
        level = block.heading_level or max(1, min(6, depth + 1))
        lines.extend(["#" * level + " " + block.content.resolved_text, ""])
    elif block.type == BlockType.PARAGRAPH and block.content and block.content.resolved_text:
        lines.extend([block.content.resolved_text, ""])
    elif block.type in {BlockType.LIST, BlockType.LIST_ITEM} and block.content and block.content.resolved_text:
        marker = block.list_marker or "-"
        if marker in {"o", "○", "◦", "•", "●", "▪", "▫", "–", "—"}:
            marker = "-"
        indent = "  " * (block.list_level or 0)
        lines.extend([f"{indent}{marker} {block.content.resolved_text}", ""])
    elif block.type == BlockType.CODE and block.code:
        lines.extend([f"```{block.code.language or ''}", block.code.raw_text, "```", ""])
    elif block.type == BlockType.EQUATION and block.equation:
        if block.equation.latex:
            lines.extend(["$$", block.equation.latex, "$$", ""])
        else:
            lines.extend([f"![equation]({_asset_ref(block.equation.image_ref, asset_base)})", ""])
    elif block.type == BlockType.TABLE:
        if block.index:
            lines.extend([f"**{block.index}**", ""])
        lines.extend(_table_markdown(block))
        lines.append("")
        if block.note:
            lines.extend([block.note, ""])
    elif block.type == BlockType.FIGURE and block.figure:
        if block.index:
            lines.extend([f"**{block.index}**", ""])
        lines.extend([
            f"![{block.index or block.id}]({_asset_ref(block.figure.image_ref, asset_base)})",
            "",
        ])
        if block.note:
            lines.extend([block.note, ""])
    elif block.type == BlockType.UNKNOWN and block.content and block.content.resolved_text:
        lines.extend([block.content.resolved_text, ""])
    for child_id in block.children:
        _render_block(document, document.blocks[child_id], depth + 1, lines, asset_base)


def export_markdown(document: Document, path: str | Path) -> Path:
    target = Path(path)
    lines: list[str] = []
    for root_id in document.root_block_ids:
        _render_block(document, document.blocks[root_id], 0, lines, target.parent)
    footnotes = sorted(
        (
            block for block in document.blocks.values()
            if block.type == BlockType.FOOTNOTE
            and block.content and block.content.resolved_text
        ),
        key=lambda block: (
            block.segments[0].page_index if block.segments else 10**9,
            block.segments[0].bbox.y0 if block.segments else 10**9,
            block.id,
        ),
    )
    definitions: list[str] = []
    for block in footnotes:
        value = block.content.resolved_text or ""
        match = re.match(r"^\s*(\d+)\s+(.+)$", value, flags=re.S)
        if match:
            definitions.extend([f"[^{match.group(1)}]: {match.group(2).strip()}", ""])
    if definitions:
        lines.extend(definitions)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return target
