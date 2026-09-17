from __future__ import annotations

import json
from pathlib import Path

from ...models import Document


def export_jsonl(document: Document, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as stream:
        for block in sorted(document.blocks.values(), key=lambda item: item.id):
            stream.write(json.dumps({
                "document_id": document.document_id,
                "schema_version": document.schema_version,
                "block": block.model_dump(mode="json"),
            }, ensure_ascii=False) + "\n")
    return target
