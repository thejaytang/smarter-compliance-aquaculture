from __future__ import annotations

from types import SimpleNamespace

from PIL import Image, ImageDraw

from pdf_extraction.parsers.special import (
    _formula_from_payload,
    _segment_formula_lines,
    enrich_definition_formula_text,
    enrich_mixed_formula_text,
    normalize_formula_latex,
)


def test_formula_payload_is_unwrapped_from_paddle_result() -> None:
    result = SimpleNamespace(json={"res": {"rec_formula": "$$ x^2 + y^2 $$"}})

    assert _formula_from_payload(result) == "x^2 + y^2"


def test_formula_payload_accepts_list_and_display_brackets() -> None:
    payload = {"rec_formula": [r"\[\frac{q l}{2t_1}\leq f_1\]"]}

    assert _formula_from_payload(payload) == r"\frac{q l}{2t_1}\leq f_1"


def test_formula_normalization_unwraps_aligned_and_standardizes_operator() -> None:
    latex = (
        r"{\begin{aligned}x&=\operatorname*{l i m}_{n\to0}x_n\\"
        r"&=0\end{aligned}}"
    )

    assert normalize_formula_latex(latex) == (
        r"\begin{aligned}x&=\lim_{n\to0}x_n\\&=0\end{aligned}"
    )


def test_formula_line_segmentation_finds_separated_rows() -> None:
    image = Image.new("RGB", (160, 100), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 145, 28), fill="black")
    draw.rectangle((20, 65, 130, 85), fill="black")

    lines = _segment_formula_lines(image)

    assert len(lines) == 2


def test_formula_normalization_uses_brackets_for_bounded_evaluation_chain() -> None:
    latex = (
        r"\begin{aligned}&=\left(x^3\right)_{2}^{4}\\"
        r"&=\left(4^3\right)-\left(2^3\right)\end{aligned}"
    )

    assert normalize_formula_latex(latex) == (
        r"\begin{aligned}&=\Bigg[x^3\Bigg]_{2}^{4}\\"
        r"&=\Bigg[4^3\Bigg]-\Bigg[2^3\Bigg]\end{aligned}"
    )


def test_formula_normalization_preserves_limits_and_indexed_list_delimiters() -> None:
    assert normalize_formula_latex(r"\sup_{x\in X} f(x)") == (
        r"\mathop{\sup}\limits_{x\in X} f(x)"
    )
    assert normalize_formula_latex(r"f[x_0,x_1,\ldots,x_k]") == (
        r"f\left\lbrack x_0,x_1,\ldots,x_k \right\rbrack"
    )


def test_mixed_formula_text_fuses_ocr_prose_with_formula_bounds() -> None:
    fused = enrich_mixed_formula_text(
        "then AreaA=∫3x² dx 2",
        r"\tan\mathrm{Area}\;\mathrm{A}=\int_{2}^{4}3x^{2}dx",
    )

    assert fused == r"then Area A $= \int_{2}^{4}3x^{2}dx$"


def test_definition_formula_fusion_changes_only_variable_prefix() -> None:
    fused = enrich_definition_formula_text(
        "式中N(发)——到发线通过能力",
        r"式中 $\begin{array}{l}N_{ 到 ( 发 )}—— 到发线\end{array}$",
    )

    assert fused == r"式中 $N_{ 到 ( 发 )}$——到发线通过能力"
