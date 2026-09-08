from __future__ import annotations

import json
from pathlib import Path

from ...models import Block, BlockType, Document


def _block_text(block: Block) -> str:
    if block.content and block.content.resolved_text:
        return block.content.resolved_text
    if block.code:
        return block.code.raw_text
    if block.equation and block.equation.latex:
        return block.equation.latex
    if block.table:
        return "\n".join(
            cell.content.resolved_text or ""
            for cell in sorted(block.table.cells, key=lambda cell: (cell.row, cell.column))
        )
    if block.type == BlockType.FIGURE:
        if block.index:
            return block.index
    return ""


def _canonical_blocks(document: Document) -> list[Block]:
    ordered: list[Block] = []
    seen: set[str] = set()

    def visit(block_id: str) -> None:
        if block_id in seen or block_id not in document.blocks:
            return
        seen.add(block_id)
        block = document.blocks[block_id]
        if block.type not in {
            BlockType.DOCUMENT, BlockType.SECTION,
            BlockType.HEADER, BlockType.FOOTER, BlockType.FOOTNOTE,
        }:
            ordered.append(block)
        for child_id in block.children:
            visit(child_id)

    for root_id in document.root_block_ids:
        visit(root_id)
    return ordered


def build_rag_chunks(document: Document, max_chars: int = 1800) -> list[dict[str, object]]:
    chunks: list[dict[str, object]] = []
    heading_path: list[str] = []
    buffer: list[Block] = []
    size = 0

    def flush() -> None:
        nonlocal buffer, size
        if not buffer:
            return
        segments = [segment for block in buffer for segment in block.segments]
        chunks.append({
            "id": f"chunk_{len(chunks):06d}",
            "document_id": document.document_id,
            "text": "\n\n".join(filter(None, (_block_text(block) for block in buffer))),
            "heading_path": list(heading_path),
            "block_ids": [block.id for block in buffer],
            "page_indices": sorted({segment.page_index for segment in segments}),
            "segments": [segment.model_dump(mode="json") for segment in segments],
            "content_links": [
                link.model_dump(mode="json") for block in buffer for link in block.content_links
            ],
        })
        buffer = []
        size = 0

    ordered = _canonical_blocks(document)
    atomic = {BlockType.TABLE, BlockType.FIGURE, BlockType.CODE, BlockType.EQUATION}
    for block in ordered:
        text = _block_text(block)
        if block.type == BlockType.HEADING:
            flush()
            level = block.heading_level or 1
            heading_path[:] = heading_path[: level - 1]
            heading_path.append(text)
        if block.type in atomic:
            flush()
            if text:
                buffer = [block]
                size = len(text)
                flush()
            continue
        if not text:
            continue
        if buffer and size + len(text) > max_chars:
            flush()
        buffer.append(block)
        size += len(text)
    flush()
    return chunks


def export_rag_chunks(document: Document, path: str | Path, max_chars: int = 1800) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(build_rag_chunks(document, max_chars=max_chars), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target
