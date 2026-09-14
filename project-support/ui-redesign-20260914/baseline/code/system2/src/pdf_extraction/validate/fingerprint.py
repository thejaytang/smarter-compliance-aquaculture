from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..models import Document


def structural_fingerprint(document: Document) -> str:
    """Hash semantic structure while ignoring run times and output-root locations."""
    data = document.model_dump(mode="json")
    data["processing"].pop("started_at", None)
    data["processing"].pop("completed_at", None)
    data["processing"].pop("step_timings_ms", None)
    data["processing"].pop("retry_count", None)
    data["processing"].pop("resumed_from", None)
    data["processing"].get("environment", {}).pop("process_id", None)
    for artifact in data.get("artifacts", {}).values():
        artifact["path"] = Path(artifact["path"]).name
        artifact["sha256"] = None
    for page in data.get("pages", []):
        page["image_ref"] = Path(page["image_ref"]).name
    for block in data.get("blocks", {}).values():
        for segment in block.get("segments", []):
            if segment.get("crop_ref"):
                segment["crop_ref"] = Path(segment["crop_ref"]).name
        figure = block.get("figure")
        if figure and figure.get("image_ref"):
            figure["image_ref"] = Path(figure["image_ref"]).name
        equation = block.get("equation")
        if equation and equation.get("image_ref"):
            equation["image_ref"] = Path(equation["image_ref"]).name
    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()
