from __future__ import annotations

import html
import re
from pathlib import Path

from ...models import Block, BlockType, Document


def _text(block: Block) -> str:
    return block.content.resolved_text if block.content and block.content.resolved_text else ""


def _inline(value: str) -> str:
    escaped = html.escape(value).replace("\n", "<br>")
    return re.sub(
        r"\[\^(\d{1,2})\]",
        r'<sup><a href="#fn-\1" id="fnref-\1">\1</a></sup>',
        escaped,
    )


def _render(block: Block, document: Document) -> str:
    if block.type in {BlockType.HEADER, BlockType.FOOTER, BlockType.FOOTNOTE}:
        return ""
    body = ""
    value = _inline(_text(block))
    if block.type == BlockType.HEADING and value:
        level = block.heading_level or 2
        body += f"<h{level} data-block-id=\"{block.id}\">{value}</h{level}>"
    elif block.type == BlockType.PARAGRAPH and value:
        body += f"<p data-block-id=\"{block.id}\">{value}</p>"
    elif block.type in {BlockType.LIST, BlockType.LIST_ITEM} and value:
        children = "".join(_render(document.blocks[item], document) for item in block.children)
        return f"<ul data-block-id=\"{block.id}\"><li>{value}{children}</li></ul>"
    elif block.type == BlockType.CODE and block.code:
        body += f"<pre data-block-id=\"{block.id}\"><code>{html.escape(block.code.raw_text)}</code></pre>"
    elif block.type == BlockType.EQUATION and block.equation:
        body += f"<figure data-block-id=\"{block.id}\"><code>{html.escape(block.equation.latex or value)}</code></figure>"
    elif block.type == BlockType.TABLE and block.table:
        cells = {(cell.row, cell.column): cell for cell in block.table.cells}
        rows = []
        for row in range(block.table.row_count):
            values = []
            for column in range(block.table.column_count):
                cell = cells.get((row, column))
                content = cell.content.resolved_text if cell and cell.content.resolved_text else ""
                tag = "th" if cell and cell.is_header else "td"
                span = ""
                if cell:
                    span = f' rowspan="{cell.row_span}" colspan="{cell.column_span}"'
                values.append(f"<{tag}{span}>{_inline(content)}</{tag}>")
            rows.append("<tr>" + "".join(values) + "</tr>")
        body += f"<table data-block-id=\"{block.id}\">{''.join(rows)}</table>"
    elif block.type == BlockType.FIGURE and block.figure:
        body += (
            f'<figure data-block-id="{block.id}"><img src="{html.escape(block.figure.image_ref)}" '
            f'alt="{html.escape(block.index or block.id)}"></figure>'
        )
    for child_id in block.children:
        body += _render(document.blocks[child_id], document)
    return body


def export_html(document: Document, path: str | Path) -> Path:
    content = "".join(_render(document.blocks[root], document) for root in document.root_block_ids)
    definitions: list[str] = []
    for block in sorted(
        (item for item in document.blocks.values() if item.type == BlockType.FOOTNOTE),
        key=lambda item: (
            item.segments[0].page_index if item.segments else 10**9,
            item.segments[0].bbox.y0 if item.segments else 10**9,
            item.id,
        ),
    ):
        match = re.match(r"^\s*(\d+)\s+(.+)$", _text(block), flags=re.S)
        if match:
            definitions.append(
                f'<li id="fn-{match.group(1)}" data-block-id="{block.id}">'
                f'{_inline(match.group(2).strip())} '
                f'<a href="#fnref-{match.group(1)}">↩</a></li>'
            )
    if definitions:
        content += '<section class="footnotes"><ol>' + "".join(definitions) + "</ol></section>"
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "<!doctype html><html><head><meta charset=\"utf-8\"><title>"
        + html.escape(document.source.file_name)
        + "</title></head><body>" + content + "</body></html>\n",
        encoding="utf-8",
    )
    return target
