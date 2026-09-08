from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import tempfile
from importlib.metadata import version
from pathlib import Path

from PIL import Image

from .config import OCRSettings
from .types import OCRPage, OCRWord, PixelBox, RenderedPage


def configure_paddle_runtime() -> Path:
    """Keep model, temporary, and provider caches inside the project workspace."""
    cache_root = (Path.cwd() / ".cache").resolve()
    paddle_cache = cache_root / "paddlex"
    paddle_cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(paddle_cache))
    os.environ.setdefault("PADDLE_PDX_MODEL_SOURCE", "bos")
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
    os.environ.setdefault("XDG_CACHE_HOME", str(cache_root))
    os.environ.setdefault("MPLCONFIGDIR", str(cache_root / "matplotlib"))
    os.environ.setdefault("HF_HOME", str(cache_root / "huggingface"))
    (cache_root / "matplotlib").mkdir(parents=True, exist_ok=True)
    (cache_root / "huggingface").mkdir(parents=True, exist_ok=True)
    return paddle_cache


class OCRBackend:
    name = "base"

    def recognize_page(self, page: RenderedPage, raw_dir: Path) -> OCRPage:
        raise NotImplementedError

    def recognize_crop(self, image: Image.Image, language: str = "eng") -> tuple[str, float]:
        raise NotImplementedError

    def recognize_block(self, image: Image.Image, language: str = "eng") -> tuple[str, float]:
        return self.recognize_crop(image, language)


class TesseractOCRBackend(OCRBackend):
    name = "tesseract"

    def __init__(self, language: str = "eng", fallback_reason: str | None = None) -> None:
        self.language = language
        self.fallback_reason = fallback_reason
        result = subprocess.run(
            ["tesseract", "--version"], capture_output=True, text=True, check=True
        )
        self.backend_version = result.stdout.splitlines()[0].replace("tesseract ", "")

    def recognize_page(self, page: RenderedPage, raw_dir: Path) -> OCRPage:
        import pytesseract
        from pytesseract import Output

        raw_dir.mkdir(parents=True, exist_ok=True)
        with Image.open(page.image_path) as image:
            data = pytesseract.image_to_data(
                image,
                lang=self.language,
                config="--oem 1 --psm 3",
                output_type=Output.DICT,
            )
        words: list[OCRWord] = []
        rows: list[dict[str, object]] = []
        for index, raw_text in enumerate(data["text"]):
            text = str(raw_text).strip()
            try:
                confidence = max(0.0, float(data["conf"][index]) / 100.0)
            except (TypeError, ValueError):
                confidence = 0.0
            if not text:
                continue
            left = int(data["left"][index])
            top = int(data["top"][index])
            width = int(data["width"][index])
            height = int(data["height"][index])
            word = OCRWord(
                id=f"ocr_p{page.page_index:04d}_w{len(words):06d}",
                text=text,
                confidence=confidence,
                bbox=PixelBox(left, top, left + width, top + height),
                block_num=int(data["block_num"][index]),
                paragraph_num=int(data["par_num"][index]),
                line_num=int(data["line_num"][index]),
            )
            words.append(word)
            rows.append(
                {
                    "id": word.id,
                    "text": word.text,
                    "confidence": word.confidence,
                    "bbox": [left, top, left + width, top + height],
                    "block_num": word.block_num,
                    "paragraph_num": word.paragraph_num,
                    "line_num": word.line_num,
                }
            )
        raw_ref = raw_dir / f"ocr-page-{page.page_index + 1:04d}.json"
        raw_ref.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        return OCRPage(
            page_index=page.page_index,
            words=words,
            backend=self.name,
            version=self.backend_version,
            fallback_reason=self.fallback_reason,
            raw_ref=raw_ref,
        )

    def recognize_crop(self, image: Image.Image, language: str = "eng") -> tuple[str, float]:
        return self._recognize_image(image, language, psm=7)

    def recognize_block(self, image: Image.Image, language: str = "eng") -> tuple[str, float]:
        return self._recognize_image(image, language, psm=6)

    @staticmethod
    def _recognize_image(
        image: Image.Image, language: str, *, psm: int
    ) -> tuple[str, float]:
        import pytesseract
        from pytesseract import Output

        data = pytesseract.image_to_data(
            image,
            lang=language,
            config=f"--oem 1 --psm {psm}",
            output_type=Output.DICT,
        )
        texts: list[str] = []
        scores: list[float] = []
        for text, raw_conf in zip(data["text"], data["conf"], strict=True):
            cleaned = re.sub(r"\s+", " ", str(text)).strip()
            if not cleaned:
                continue
            texts.append(cleaned)
            try:
                score = float(raw_conf)
            except (TypeError, ValueError):
                score = -1
            if score >= 0:
                scores.append(score / 100.0)
        confidence = sum(scores) / len(scores) if scores else 0.0
        return " ".join(texts), confidence


class PaddleOCRBackend(OCRBackend):
    name = "PP-OCRv6"

    def __init__(self, settings: OCRSettings) -> None:
        if importlib.util.find_spec("paddleocr") is None:
            raise RuntimeError("paddleocr package is not installed")
        configure_paddle_runtime()
        from paddleocr import PaddleOCR

        self.settings = settings
        self.model = PaddleOCR(
            ocr_version=settings.paddle_version,
            lang="en",
            engine=settings.paddle_engine,
            device="cpu",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
        self.backend_version = version("paddleocr")

    def recognize_page(self, page: RenderedPage, raw_dir: Path) -> OCRPage:
        output = list(self.model.predict(str(page.image_path)))
        words: list[OCRWord] = []
        serializable: list[dict[str, object]] = []
        for result in output:
            payload = result.json if hasattr(result, "json") else result
            if isinstance(payload, str):
                payload = json.loads(payload)
            data = payload.get("res", payload) if isinstance(payload, dict) else {}
            texts = data.get("rec_texts", [])
            scores = data.get("rec_scores", [])
            boxes = data.get("rec_boxes", data.get("dt_polys", []))
            for line_index, (text, score, box) in enumerate(
                zip(texts, scores, boxes, strict=False), start=1
            ):
                points = box.tolist() if hasattr(box, "tolist") else box
                if len(points) == 4 and not isinstance(points[0], (list, tuple)):
                    x0, y0, x1, y1 = map(int, points)
                else:
                    xs = [int(point[0]) for point in points]
                    ys = [int(point[1]) for point in points]
                    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
                word = OCRWord(
                    id=f"ocr_p{page.page_index:04d}_w{len(words):06d}",
                    text=str(text),
                    confidence=float(score),
                    bbox=PixelBox(x0, y0, x1, y1),
                    line_num=line_index,
                )
                words.append(word)
                serializable.append(
                    {"id": word.id, "text": word.text, "confidence": word.confidence,
                     "bbox": [x0, y0, x1, y1]}
                )
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_ref = raw_dir / f"ocr-page-{page.page_index + 1:04d}.json"
        raw_ref.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")
        return OCRPage(page.page_index, words, self.name, self.backend_version, raw_ref=raw_ref)

    def recognize_crop(self, image: Image.Image, language: str = "eng") -> tuple[str, float]:
        cache = configure_paddle_runtime() / "temp"
        cache.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(suffix=".png", dir=cache, delete=False) as stream:
            temp = Path(stream.name)
        image.save(temp)
        try:
            output = list(self.model.predict(str(temp)))
        finally:
            temp.unlink(missing_ok=True)
        texts: list[str] = []
        scores: list[float] = []
        for result in output:
            payload = result.json if hasattr(result, "json") else result
            if isinstance(payload, str):
                payload = json.loads(payload)
            data = payload.get("res", payload) if isinstance(payload, dict) else {}
            texts.extend(map(str, data.get("rec_texts", [])))
            scores.extend(map(float, data.get("rec_scores", [])))
        return " ".join(texts), sum(scores) / len(scores) if scores else 0.0


def create_ocr_backend(settings: OCRSettings) -> OCRBackend:
    if settings.backend in {"auto", "paddle"}:
        try:
            return PaddleOCRBackend(settings)
        except Exception as exc:
            if settings.backend == "paddle":
                raise
            return TesseractOCRBackend(settings.language, f"Paddle OCR unavailable: {exc}")
    if settings.backend == "tesseract":
        return TesseractOCRBackend(settings.language)
    raise ValueError(f"unsupported OCR backend: {settings.backend}")
