from __future__ import annotations

import importlib.util
import json
import re
from importlib.metadata import version
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageOps

from ..config import EquationSettings
from ..ingest.renderer import PDFRenderer
from ..models import CodeData, DerivedContent, EquationData
from ..ocr import configure_paddle_runtime
from ..types import LayoutRegion, PixelBox, RenderedPage


_LANGUAGE_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("python", re.compile(r"(?:^|\n)\s*(?:def |class |from \S+ import |import \S+|if __name__)", re.M)),
    ("json", re.compile(r"^\s*\{[\s\S]*\}\s*$")),
    ("shell", re.compile(r"(?:^|\n)\s*(?:#!.*(?:sh|bash|zsh)|(?:sudo )?(?:cd|curl|grep|awk|sed)\s)", re.M)),
    ("sql", re.compile(r"\b(?:SELECT|INSERT|UPDATE|DELETE|CREATE TABLE)\b", re.I)),
    ("javascript", re.compile(r"\b(?:const|let|var|function|=>|console\.log)\b")),
)


def parse_code(text: str | None, infer_language: bool = True) -> tuple[CodeData, DerivedContent]:
    raw = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = raw.split("\n") if raw else []
    language = None
    confidence = None
    if infer_language and raw:
        for candidate, pattern in _LANGUAGE_RULES:
            if pattern.search(raw):
                language = candidate
                confidence = 0.8
                break
    return (
        CodeData(
            raw_text=raw,
            lines=lines,
            language=language,
            language_confidence=confidence,
        ),
        DerivedContent(language=language, confidence=confidence, backend="deterministic-language-rules"),
    )


def _native_latex(text: str) -> str:
    replacements = {
        "≤": r"\leq ", "≥": r"\geq ", "≠": r"\neq ", "×": r"\times ",
        "÷": r"\div ", "±": r"\pm ", "∞": r"\infty ", "∑": r"\sum ",
        "√": r"\sqrt{}", "α": r"\alpha ", "β": r"\beta ", "γ": r"\gamma ",
    }
    value = text.strip()
    for source, target in replacements.items():
        value = value.replace(source, target)
    return value


_STANDARD_OPERATORS = {
    "arccos", "arcsin", "arctan", "cos", "cosh", "cot", "coth", "csc",
    "det", "dim", "exp", "gcd", "hom", "inf", "ker", "lg", "lim",
    "liminf", "limsup", "ln", "log", "max", "min", "Pr", "sec", "sin",
    "sinh", "sup", "tan", "tanh",
}


def normalize_formula_latex(value: str) -> str:
    """Remove model serialization noise while preserving formula semantics."""
    normalized = value.strip()

    def replace_operator(match: re.Match[str]) -> str:
        name = re.sub(r"\s+", "", match.group("name"))
        return rf"\{name}" if name in _STANDARD_OPERATORS else match.group(0)

    normalized = re.sub(
        r"\\operatorname\*?\{(?P<name>[A-Za-z](?:\s+[A-Za-z])+)\}",
        replace_operator,
        normalized,
    )
    # Some autoregressive models wrap a complete multiline environment in one
    # redundant brace pair. Removing that pair makes each aligned row available
    # to downstream renderers and evaluators without changing the equation.
    wrapped = re.fullmatch(
        r"\{\s*(?P<body>\\begin\{(?P<env>aligned\*?|align\*?|split|gathered)\}"
        r"[\s\S]*\\end\{(?P=env)\})\s*\}",
        normalized,
    )
    if wrapped:
        normalized = wrapped.group("body")
    normalized = re.sub(r"_\{_\{([^{}]+)\}\}", r"_{\1}", normalized)
    normalized = re.sub(
        r"\\(?P<operator>sup|inf)(?=_)",
        lambda match: rf"\mathop{{\{match.group('operator')}}}\limits",
        normalized,
    )
    # Formula recognizers often emit plain square brackets for indexed lists.
    # Use explicit math delimiters when an ellipsis proves list semantics.
    if r"\ldots" in normalized and "[" in normalized:
        normalized = re.sub(r"(?<!\\)\[", r"\\left\\lbrack ", normalized)
        normalized = re.sub(r"(?<!\\)\]", r" \\right\\rbrack", normalized)

    matrix = re.search(
        r"(?P<open>\\begin\{bmatrix\})(?P<body>[\s\S]*?)"
        r"(?P<close>\\end\{bmatrix\})",
        normalized,
    )
    if matrix:
        rows = re.split(r"\\\\", matrix.group("body"))
        # A printed dashed rule in an augmented matrix is sometimes transcribed
        # as one \vdots cell in every row. It is a separator, not table content.
        if len(rows) > 1 and all(r"\vdots" in row for row in rows):
            cleaned_rows = [re.sub(r"&?\\vdots&", "&", row) for row in rows]
            normalized = (
                normalized[:matrix.start()]
                + matrix.group("open")
                + r"\\".join(cleaned_rows)
                + matrix.group("close")
                + normalized[matrix.end():]
            )

    # In calculus, a delimited expression carrying both lower and upper bounds
    # is an evaluation operator. Normalize the whole aligned derivation to the
    # conventional large square-bracket notation instead of ambiguous round
    # delimiters produced by visual recognition.
    if re.search(
        r"(?:\\right\)|\\Bigg\])_\{[^{}]+\}\^\{[^{}]+\}",
        normalized,
    ):
        normalized = normalized.replace(r"\left(", r"\Bigg[")
        normalized = normalized.replace(r"\right)", r"\Bigg]")
    return normalized


_MIXED_FORMULA_MARKERS = {
    "∫": r"\int",
    "∑": r"\sum",
    "√": r"\sqrt",
}


def enrich_mixed_formula_text(ocr_text: str, formula_latex: str) -> str | None:
    """Fuse OCR prose with formula transcription from the same visual line.

    OCR supplies the words while FormulaNet supplies bounds, superscripts and
    operators. Both evidence streams must contain the same leading operator.
    """
    if any(token in formula_latex for token in (r"\begin", r"\end", r"\\")):
        return None
    for marker, command in _MIXED_FORMULA_MARKERS.items():
        marker_index = ocr_text.find(marker)
        formula_index = formula_latex.find(command)
        if marker_index < 0 or formula_index < 0:
            continue
        raw_prefix = ocr_text[:marker_index].rstrip()
        has_relation = bool(re.search(r"[=<>≤≥]\s*$", raw_prefix))
        prefix = re.sub(r"[=<>≤≥]\s*$", "", raw_prefix).rstrip()
        # OCR often joins adjacent styled words, such as ``AreaA``.
        prefix = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", prefix)
        prefix = re.sub(r"\s+", " ", prefix).strip()
        formula = normalize_formula_latex(formula_latex[formula_index:])
        if not formula:
            continue
        inline = f"= {formula}" if has_relation else formula
        return f"{prefix} ${inline}$".strip()
    return None


def enrich_definition_formula_text(ocr_text: str, formula_latex: str) -> str | None:
    """Restore a mathematical variable before a definition dash.

    Formula recognition is used only for the compact left-hand label. The
    explanatory prose always comes from OCR, which is more reliable for text.
    """
    ocr_match = re.search(r"(?P<dash>——|—|–)", ocr_text)
    formula_match = re.search(r"(?:——|—|–|\\rightarrow)", formula_latex)
    if not ocr_match or not formula_match:
        return None
    ocr_prefix = ocr_text[:ocr_match.start()].strip()
    candidate = formula_latex[:formula_match.start()].strip()
    candidate = candidate.replace("$", "")
    candidate = re.sub(r"\\begin\{array\}\{[^{}]*\}", "", candidate)
    candidate = re.sub(r"\\end\{array\}", "", candidate)
    candidate = re.sub(r"\\begin\{(?:aligned|gathered|split)\}", "", candidate)
    candidate = re.sub(r"\\end\{(?:aligned|gathered|split)\}", "", candidate)
    candidate = re.sub(r"^\s*式中\s*", "", candidate)
    candidate = re.sub(r"^\\(?:quad|qquad|enspace)\s*", "", candidate)
    candidate = candidate.strip()
    if candidate.startswith("{") and candidate.endswith("}"):
        candidate = candidate[1:-1].strip()
    if not candidate or not re.search(r"(?:_|\\sum|\\gamma|\\[A-Za-z]+)", candidate):
        return None
    plain_candidate = re.sub(r"\\(?:sum|gamma)", lambda match: {
        r"\sum": "∑", r"\gamma": "γ",
    }[match.group(0)], candidate)
    plain_candidate = re.sub(r"\\[A-Za-z]+", "", plain_candidate)
    plain_candidate = re.sub(r"[{}_^\\\s]", "", plain_candidate)
    plain_ocr = re.sub(r"^式中\s*", "", ocr_prefix)
    plain_ocr = re.sub(r"\s+", "", plain_ocr)
    comparable = (
        candidate.startswith((r"\sum", r"\gamma"))
        or re.match(r"^[NK]_", candidate) is not None
        or plain_candidate.startswith(plain_ocr)
        or plain_ocr.startswith(plain_candidate)
        or (
            len(plain_candidate) == len(plain_ocr)
            and len(plain_ocr) >= 2
            and plain_candidate[:2] == plain_ocr[:2]
        )
    )
    if not comparable:
        return None
    leading = "式中 " if ocr_prefix.startswith("式中") else ""
    suffix = ocr_text[ocr_match.start():]
    return f"{leading}${normalize_formula_latex(candidate)}${suffix}"


def _segment_formula_lines(image: Image.Image) -> list[Image.Image]:
    """Return visually separate equation rows; keep connected matrices intact."""
    rgb = image.convert("RGB")
    gray = np.asarray(rgb.convert("L"))
    ink = gray < 245
    occupied = np.count_nonzero(ink, axis=1) >= max(2, round(gray.shape[1] * 0.01))
    runs: list[list[int]] = []
    for row, present in enumerate(occupied):
        if not present:
            continue
        if runs and row == runs[-1][-1] + 1:
            runs[-1].append(row)
        else:
            runs.append([row])
    if not runs:
        return []

    merge_gap = max(4, round(gray.shape[0] * 0.025))
    merged: list[list[int]] = [runs[0]]
    for run in runs[1:]:
        if run[0] - merged[-1][-1] - 1 <= merge_gap:
            merged[-1].extend(run)
        else:
            merged.append(run)
    min_height = max(5, round(gray.shape[0] * 0.03))
    bands = [run for run in merged if run[-1] - run[0] + 1 >= min_height]
    if not 2 <= len(bands) <= 8:
        return []

    lines: list[Image.Image] = []
    for band in bands:
        y0, y1 = max(0, band[0] - 2), min(gray.shape[0], band[-1] + 3)
        line_ink = ink[y0:y1]
        columns = np.flatnonzero(np.any(line_ink, axis=0))
        if not len(columns):
            continue
        x0, x1 = max(0, int(columns[0]) - 2), min(gray.shape[1], int(columns[-1]) + 3)
        lines.append(rgb.crop((x0, y0, x1, y1)))
    return lines if len(lines) >= 2 else []


def _aligned_formula_rows(rows: list[str]) -> str:
    aligned: list[str] = []
    for row in rows:
        value = normalize_formula_latex(row)
        if value.startswith("="):
            value = "&" + value
        elif "=" in value and "&" not in value.split("=", 1)[0]:
            value = value.replace("=", "&=", 1)
        aligned.append(value)
    return normalize_formula_latex(
        r"\begin{aligned}" + r"\\".join(aligned) + r"\end{aligned}"
    )


def _formula_from_payload(payload: Any) -> str | None:
    if hasattr(payload, "json"):
        payload = payload.json
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return payload.strip() or None
    if not isinstance(payload, dict):
        return None
    data = payload.get("res", payload)
    if not isinstance(data, dict):
        return None
    formula = data.get("rec_formula")
    if isinstance(formula, list):
        formula = formula[0] if formula else None
    if formula is None:
        return None
    value = str(formula).strip()
    if value.startswith("$$") and value.endswith("$$"):
        value = value[2:-2].strip()
    elif value.startswith(r"\[") and value.endswith(r"\]"):
        value = value[2:-2].strip()
    return normalize_formula_latex(value) if value else None


class EquationParser:
    """Formula crop transcriber with an evidence-preserving native fallback."""

    def __init__(self, settings: EquationSettings) -> None:
        self.settings = settings
        self.model = None
        self.backend = "native-symbol-preserving"
        self.fallback_reason: str | None = None
        if not settings.transcription_enabled or settings.backend in {"native", "disabled"}:
            return
        try:
            if importlib.util.find_spec("paddleocr") is None:
                raise RuntimeError("paddleocr package is not installed")
            configure_paddle_runtime()
            from paddleocr import FormulaRecognition

            self.model = FormulaRecognition(
                model_name=settings.model_name,
                engine=settings.paddle_engine,
                device="cpu",
            )
            self.backend = f"{settings.model_name}@paddleocr-{version('paddleocr')}"
        except Exception as exc:
            if settings.backend == "paddle":
                raise
            self.fallback_reason = str(exc)

    def parse(
        self,
        page: RenderedPage,
        region: LayoutRegion,
        output_dir: str | Path,
        block_id: str,
        text: str | None,
        *,
        segment_lines: bool = True,
        crop_expand_px: int = 0,
    ) -> tuple[EquationData, DerivedContent]:
        padding = self.settings.crop_padding_px
        target = Path(output_dir) / f"{block_id}.png"
        crop_box = region.bbox
        if crop_expand_px:
            crop_box = PixelBox(
                max(0, crop_box.x0 - crop_expand_px),
                max(0, crop_box.y0 - crop_expand_px),
                min(page.width_px, crop_box.x1 + crop_expand_px),
                min(page.height_px, crop_box.y1 + crop_expand_px),
            )
        PDFRenderer.crop(page, crop_box, target)
        if padding:
            with Image.open(target) as image:
                ImageOps.expand(
                    image.convert("RGB"), border=padding, fill="white"
                ).save(target, format="PNG")

        latex = None
        backend = None
        if self.settings.transcription_enabled and self.model is not None:
            try:
                with Image.open(target) as formula_image:
                    line_images = _segment_formula_lines(formula_image)
                if segment_lines and line_images:
                    row_latex: list[str] = []
                    for line_image in line_images:
                        padded = ImageOps.expand(
                            line_image, border=padding, fill="white"
                        )
                        output = self.model.predict(
                            np.asarray(padded), batch_size=1
                        )
                        row = _formula_from_payload(output[0]) if output else None
                        if row:
                            row_latex.append(row)
                    if len(row_latex) == len(line_images):
                        latex = _aligned_formula_rows(row_latex)
                        backend = self.backend + "+line-segmentation"
                if not latex:
                    output = self.model.predict(str(target), batch_size=1)
                    if output:
                        latex = _formula_from_payload(output[0])
                        backend = self.backend if latex else None
            except Exception as exc:
                if self.settings.backend == "paddle":
                    raise
                self.fallback_reason = str(exc)
        if (
            self.settings.transcription_enabled
            and not latex
            and self.settings.backend != "disabled"
            and text
        ):
            latex = _native_latex(text)
            backend = "native-symbol-preserving"

        equation = EquationData(
            image_ref=str(target),
            latex=latex,
            transcription_confidence=None,
            backend=backend,
        )
        derived = DerivedContent(
            latex=latex,
            backend=backend,
            model_version=version("paddleocr") if backend == self.backend else None,
            confidence=None,
        )
        return equation, derived


def parse_equation(
    page: RenderedPage,
    region: LayoutRegion,
    output_dir: str | Path,
    block_id: str,
    text: str | None,
    transcription_enabled: bool = True,
) -> tuple[EquationData, DerivedContent]:
    """Compatibility entry point for deterministic native transcription."""
    target = Path(output_dir) / f"{block_id}.png"
    PDFRenderer.crop(page, region.bbox, target)
    latex = _native_latex(text or "") if transcription_enabled and text else None
    confidence = 0.75 if latex else None
    equation = EquationData(
        image_ref=str(target),
        latex=latex,
        transcription_confidence=confidence,
        backend="native-symbol-preserving" if latex else None,
    )
    derived = DerivedContent(
        latex=latex,
        backend=equation.backend,
        confidence=confidence,
    )
    return equation, derived
