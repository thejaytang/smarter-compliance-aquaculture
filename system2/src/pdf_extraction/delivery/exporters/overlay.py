from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

from ...models import Document


def export_overlays(document: Document, output_dir: str | Path) -> Path:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []
    for page in document.pages:
        with Image.open(page.image_ref) as source:
            image = source.convert("RGB")
        sx = image.width / page.width
        sy = image.height / page.height
        draw = ImageDraw.Draw(image)
        for block_id in page.block_ids:
            block = document.blocks[block_id]
            for segment in block.segments:
                if segment.page_index != page.page_index:
                    continue
                box = segment.bbox
                coords = (box.x0 * sx, box.y0 * sy, box.x1 * sx, box.y1 * sy)
                color = "#d62728" if block.quality.requires_review else "#1f77b4"
                draw.rectangle(coords, outline=color, width=3)
                draw.text((coords[0] + 2, coords[1] + 2), f"{block.type.value}:{block.id}", fill=color)
        output = target_dir / f"page-{page.page_index + 1:04d}.png"
        image.save(output)
        manifest.append({"page_index": page.page_index, "path": str(output)})
    manifest_path = target_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path
