from __future__ import annotations

from ..models import BlockType


PARSER_ROUTES: dict[BlockType, str] = {
    BlockType.DOCUMENT: "structural",
    BlockType.SECTION: "structural",
    BlockType.HEADING: "text",
    BlockType.PARAGRAPH: "text",
    BlockType.LIST: "text",
    BlockType.LIST_ITEM: "text",
    BlockType.TABLE: "table",
    BlockType.FIGURE: "figure",
    BlockType.CODE: "code",
    BlockType.EQUATION: "equation",
    BlockType.FOOTNOTE: "text-and-cross-reference",
    BlockType.HEADER: "text",
    BlockType.FOOTER: "text-and-page-label",
    BlockType.UNKNOWN: "evidence-preserving-unknown",
}


def parser_route(block_type: BlockType) -> str:
    return PARSER_ROUTES[block_type]
