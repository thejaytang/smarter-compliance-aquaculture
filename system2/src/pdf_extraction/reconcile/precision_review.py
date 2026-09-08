from __future__ import annotations

import importlib.util
import json
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from ..config import PrecisionReviewSettings
from ..models import BoundingBox, EvidenceSpan, ResolutionStatus
from ..ocr import OCRBackend, configure_paddle_runtime
from ..types import PixelBox, RenderedPage


@dataclass(frozen=True)
class ReviewResult:
    value: str | None
    confidence: float
    backend: str
    fallback_reason: str | None = None


class PrecisionReviewer:
    def __init__(self, settings: PrecisionReviewSettings, ocr_backend: OCRBackend) -> None:
        self.settings = settings
        self.ocr_backend = ocr_backend
        self._vl_model = None
        self.last_backend = settings.model_name
        self.last_fallback_reason: str | None = None

    @staticmethod
    def _span_crop(page: RenderedPage, bbox: BoundingBox, scale: float) -> Image.Image:
        sx, sy = page.width_px / page.width_points, page.height_px / page.height_points
        margin = 8
        box = PixelBox(
            max(0, int(bbox.x0 * sx) - margin), max(0, int(bbox.y0 * sy) - margin),
            min(page.width_px, int(bbox.x1 * sx) + margin),
            min(page.height_px, int(bbox.y1 * sy) + margin),
        )
        with Image.open(page.image_path) as image:
            crop = image.crop((box.x0, box.y0, box.x1, box.y1)).convert("RGB")
        return crop.resize(
            (max(1, int(crop.width * scale)), max(1, int(crop.height * scale))),
            Image.Resampling.LANCZOS,
        )

    def _vl_review(self, crop: Image.Image) -> ReviewResult:
        if importlib.util.find_spec("paddleocr") is None:
            raise RuntimeError("paddleocr package is not installed")
        configure_paddle_runtime()
        from paddleocr import PaddleOCRVL

        if self._vl_model is None:
            self._vl_model = PaddleOCRVL(
                pipeline_version="v1.6",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_layout_detection=False,
                format_block_content=False,
            )
        temp_dir = configure_paddle_runtime() / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(suffix=".png", dir=temp_dir, delete=False) as stream:
            path = Path(stream.name)
        crop.save(path)
        try:
            output = self._vl_model.predict(
                str(path), use_layout_detection=False, prompt_label="ocr",
                temperature=0.0, max_new_tokens=64,
            )
        finally:
            path.unlink(missing_ok=True)
        texts: list[str] = []
        for result in output:
            payload = result.json if hasattr(result, "json") else result
            if isinstance(payload, str):
                payload = json.loads(payload)
            data = payload.get("res", payload) if isinstance(payload, dict) else {}
            for block in data.get("parsing_res_list", []):
                value = str(block.get("block_content", "")).strip()
                if value:
                    texts.append(value)
        return ReviewResult(" ".join(texts) or None, 0.0, "PaddleOCR-VL-1.6")

    def _enhanced_ocr_review(self, crop: Image.Image, reason: str | None = None) -> ReviewResult:
        value, confidence = self.ocr_backend.recognize_crop(crop)
        return ReviewResult(
            value.strip() or None, confidence,
            f"{self.ocr_backend.name}-span-review", reason,
        )

    def review(self, span: EvidenceSpan, page: RenderedPage) -> ReviewResult:
        crop = self._span_crop(page, span.bbox, self.settings.crop_scale)
        if self.settings.backend in {"auto", "paddleocr_vl"}:
            try:
                result = self._vl_review(crop)
                self.last_backend = result.backend
                return result
            except Exception as exc:
                if self.settings.backend == "paddleocr_vl":
                    raise
                reason = f"PaddleOCR-VL-1.6 unavailable: {exc}"
                self.last_fallback_reason = reason
                result = self._enhanced_ocr_review(crop, reason)
                self.last_backend = result.backend
                return result
        result = self._enhanced_ocr_review(crop)
        self.last_backend = result.backend
        return result

    def resolve_span(self, span: EvidenceSpan, page: RenderedPage) -> ReviewResult:
        result = self.review(span, page)
        span.review_text = result.value
        normalized = lambda value: re.sub(r"\s+", "", value or "").casefold().replace(",", ".")
        candidates = [value for value in (span.native_text, span.ocr_text) if value]
        match = next((value for value in candidates if normalized(value) == normalized(result.value)), None)
        if match and result.confidence >= self.settings.auto_resolve_confidence:
            span.resolved_text = match
            span.resolution_status = ResolutionStatus.RESOLVED
            span.confidence = result.confidence
            span.requires_human_review = False
            span.trigger_rules.append("precision_review_agrees_with_existing_evidence")
        else:
            span.resolution_status = ResolutionStatus.AMBIGUOUS
            span.requires_human_review = True
            span.trigger_rules.append("precision_review_insufficient_for_auto_resolution")
        return result
