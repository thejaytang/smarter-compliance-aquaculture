from __future__ import annotations

import re
from collections import Counter
from typing import Iterable


def normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def levenshtein(left: list[str], right: list[str]) -> int:
    prior = list(range(len(right) + 1))
    for row, left_item in enumerate(left, start=1):
        current = [row]
        for column, right_item in enumerate(right, start=1):
            current.append(min(
                current[-1] + 1,
                prior[column] + 1,
                prior[column - 1] + int(left_item != right_item),
            ))
        prior = current
    return prior[-1]


def error_rate(expected: str, actual: str, *, words: bool) -> float:
    expected_units = normalize_text(expected).split() if words else list(normalize_text(expected))
    actual_units = normalize_text(actual).split() if words else list(normalize_text(actual))
    if not expected_units:
        return 0.0 if not actual_units else 1.0
    return levenshtein(expected_units, actual_units) / len(expected_units)


def f1(expected: Iterable[str], actual: Iterable[str]) -> float:
    expected_counts, actual_counts = Counter(expected), Counter(actual)
    true_positive = sum((expected_counts & actual_counts).values())
    expected_total, actual_total = sum(expected_counts.values()), sum(actual_counts.values())
    if expected_total == actual_total == 0:
        return 1.0
    precision = true_positive / actual_total if actual_total else 0.0
    recall = true_positive / expected_total if expected_total else 0.0
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def exact_match(expected: Iterable[str], actual: Iterable[str]) -> float:
    expected_values = [normalize_text(value).casefold() for value in expected]
    actual_values = [normalize_text(value).casefold() for value in actual]
    if not expected_values:
        return 1.0 if not actual_values else 0.0
    return sum((Counter(expected_values) & Counter(actual_values)).values()) / len(expected_values)


def safe_ratio(numerator: int | float, denominator: int | float, empty: float = 1.0) -> float:
    return numerator / denominator if denominator else empty
