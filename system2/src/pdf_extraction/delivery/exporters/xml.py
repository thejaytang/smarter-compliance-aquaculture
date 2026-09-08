from __future__ import annotations

from pathlib import Path
from xml.etree.ElementTree import Element, ElementTree, SubElement, indent

from ...models import Document


def export_xml(document: Document, path: str | Path) -> Path:
    root = Element("document", id=document.document_id, schema_version=document.schema_version)
    for block in document.blocks.values():
        node = SubElement(root, "block", id=block.id, type=block.type.value)
        if block.parent_id:
            node.set("parent_id", block.parent_id)
        if block.content:
            content = SubElement(node, "content")
            for name in ("native_text", "ocr_text", "review_text", "resolved_text"):
                value = getattr(block.content, name)
                if value is not None:
                    SubElement(content, name).text = value
        for segment in block.segments:
            SubElement(
                node, "segment", id=segment.id, page_index=str(segment.page_index),
                bbox=",".join(map(str, segment.bbox.as_list())),
            )
    indent(root)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    ElementTree(root).write(target, encoding="utf-8", xml_declaration=True)
    return target
