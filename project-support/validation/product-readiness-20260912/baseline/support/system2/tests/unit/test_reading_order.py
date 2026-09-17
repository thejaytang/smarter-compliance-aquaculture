from __future__ import annotations

from pdf_extraction.layout.reading_order import (
    merge_recovered_regions,
    repair_fragmented_column_runs,
    repair_local_model_inversions,
)
from pdf_extraction.layout.detector import (
    promote_spaced_lead_paragraphs,
    split_sparse_text_regions,
)
from pdf_extraction.types import LayoutRegion, OCRPage, OCRWord, PixelBox


def _region(name: str, x0: int, y0: int, x1: int, y1: int) -> LayoutRegion:
    return LayoutRegion(
        id=name,
        label="paragraph",
        bbox=PixelBox(x0, y0, x1, y1),
        confidence=1.0,
    )


def test_model_column_order_is_not_replaced_by_coordinate_order() -> None:
    # The model has resolved the page as left column followed by right column.
    model_order = [
        _region("left-top", 0, 0, 90, 30),
        _region("left-bottom", 0, 100, 90, 130),
        _region("right-top", 110, 0, 200, 30),
        _region("right-bottom", 110, 100, 200, 130),
    ]

    merged = merge_recovered_regions(model_order, [])

    assert [region.id for region in merged] == [
        "left-top", "left-bottom", "right-top", "right-bottom"
    ]


def test_recovered_line_is_inserted_in_its_column_without_reordering_model_regions() -> None:
    model_order = [
        _region("left-top", 0, 0, 90, 30),
        _region("left-bottom", 0, 100, 90, 130),
        _region("right-top", 110, 0, 200, 30),
        _region("right-bottom", 110, 100, 200, 130),
    ]
    recovered = [_region("left-middle", 0, 50, 90, 70)]

    merged = merge_recovered_regions(model_order, recovered)

    assert [region.id for region in merged] == [
        "left-top", "left-middle", "left-bottom", "right-top", "right-bottom"
    ]


def test_short_same_lane_model_inversion_is_repaired() -> None:
    model_order = [
        _region("left-before", 0, 20, 90, 40),
        _region("left-after", 10, 57, 80, 63),
        _region("left-missed-line", 20, 50, 60, 56),
        _region("right-top", 110, 5, 200, 30),
    ]

    repaired = repair_local_model_inversions(model_order)

    assert [region.id for region in repaired] == [
        "left-before", "left-missed-line", "left-after", "right-top"
    ]


def test_local_repair_does_not_interleave_columns() -> None:
    model_order = [
        _region("left-top", 0, 0, 90, 30),
        _region("left-bottom", 0, 100, 90, 130),
        _region("right-top", 110, 95, 200, 115),
        _region("right-bottom", 110, 120, 200, 140),
    ]

    repaired = repair_local_model_inversions(model_order)

    assert [region.id for region in repaired] == [
        "left-top", "left-bottom", "right-top", "right-bottom"
    ]


def test_sparse_text_region_is_split_on_large_vertical_gap() -> None:
    words = [
        OCRWord("a", "first line", 0.99, PixelBox(10, 10, 180, 30), line_num=1),
        OCRWord("b", "second statement", 0.99, PixelBox(10, 70, 210, 92), line_num=2),
    ]
    region = LayoutRegion(
        "r", "heading", PixelBox(5, 5, 220, 100), 0.9,
        word_ids=["a", "b"], heading_level=1,
    )

    split = split_sparse_text_regions([region], OCRPage(0, words, "test"))

    assert [item.text for item in split] == ["first line", "second statement"]
    assert [item.label for item in split] == ["heading", "paragraph"]


def test_wrapped_paragraph_is_not_split_on_normal_line_spacing() -> None:
    words = [
        OCRWord("a", "first line", 0.99, PixelBox(10, 10, 180, 30), line_num=1),
        OCRWord("b", "continues here", 0.99, PixelBox(10, 36, 190, 56), line_num=2),
    ]
    region = LayoutRegion(
        "r", "paragraph", PixelBox(5, 5, 200, 60), 0.9,
        word_ids=["a", "b"],
    )

    split = split_sparse_text_regions([region], OCRPage(0, words, "test"))

    assert [item.id for item in split] == ["r"]


def test_fragmented_dense_columns_are_reassembled_by_lane() -> None:
    left = [_region(f"l{i}", 0, i * 20, 80, i * 20 + 10) for i in range(8)]
    right = [_region(f"r{i}", 120, i * 20, 200, i * 20 + 10) for i in range(8)]
    fragmented = left[:4] + right[:2] + left[4:6] + right[2:4] + left[6:] + right[4:]

    repaired = repair_fragmented_column_runs(fragmented, 200)

    assert [item.id for item in repaired] == [
        *(f"l{i}" for i in range(8)), *(f"r{i}" for i in range(8))
    ]


def test_two_panel_transitions_are_preserved() -> None:
    left = [_region(f"l{i}", 0, i * 20, 80, i * 20 + 10) for i in range(8)]
    right = [_region(f"r{i}", 120, i * 20, 200, i * 20 + 10) for i in range(8)]
    panels = left[:4] + right[:4] + left[4:] + right[4:]

    repaired = repair_fragmented_column_runs(panels, 200)

    assert [item.id for item in repaired] == [item.id for item in panels]


def test_short_lead_line_with_top_spacing_is_promoted() -> None:
    regions = [
        LayoutRegion("prior", "paragraph", PixelBox(10, 10, 180, 30), 0.9, text="prior"),
        LayoutRegion("lead", "paragraph", PixelBox(10, 50, 180, 70), 0.9, text="New topic"),
        LayoutRegion("body", "paragraph", PixelBox(10, 72, 180, 92), 0.9, text="body sentence."),
    ]

    promoted = promote_spaced_lead_paragraphs(regions)

    assert promoted[1].label == "heading"
    assert promoted[1].heading_level == 2
