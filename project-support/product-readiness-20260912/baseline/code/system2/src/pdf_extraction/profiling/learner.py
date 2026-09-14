from __future__ import annotations

from collections import Counter, defaultdict
from statistics import median
import re

from ..types import NativeObject, NativePage
from .models import (
    DocumentProfile,
    NumberingProfile,
    RequirementCandidate,
    RequirementTemplate,
    TerminalProfile,
)


NUMBER_RE = re.compile(r"^(\d+(?:\.\d+)+)\b")
TERMINALS = {".": "period", ":": "colon", ";": "semicolon", "?": "question", "!": "exclamation"}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _center_y(item: NativeObject) -> float:
    return (item.bbox_points[1] + item.bbox_points[3]) / 2


def _candidates_for_page(page: NativePage) -> list[RequirementCandidate]:
    lines = sorted(
        (line for line in page.text_lines if _clean(line.text)),
        key=lambda line: (line.bbox_points[1], line.bbox_points[0]),
    )
    indicators = [line for line in lines if _clean(line.text).casefold() == "indicator:"]
    requirements = [line for line in lines if _clean(line.text).casefold() == "requirement:"]
    candidates: list[RequirementCandidate] = []
    for indicator_index, indicator in enumerate(indicators):
        header = min(
            (
                requirement for requirement in requirements
                if abs(_center_y(requirement) - _center_y(indicator)) <= 8
                and requirement.bbox_points[0] > indicator.bbox_points[0]
            ),
            key=lambda item: abs(_center_y(item) - _center_y(indicator)),
            default=None,
        )
        if header is None:
            continue
        next_indicator_y = (
            indicators[indicator_index + 1].bbox_points[1]
            if indicator_index + 1 < len(indicators)
            else page.height_points
        )
        numbered = [
            line for line in lines
            if NUMBER_RE.match(_clean(line.text))
            and 5 <= line.bbox_points[1] - indicator.bbox_points[3] <= 100
            and line.bbox_points[1] < next_indicator_y
            and abs(line.bbox_points[0] - indicator.bbox_points[0]) <= 36
        ]
        if not numbered:
            continue
        number_line = min(numbered, key=lambda item: item.bbox_points[1])
        next_heading_y = min(
            (
                line.bbox_points[1] for line in lines
                if line.bbox_points[1] > number_line.bbox_points[1]
                and _clean(line.text).casefold().startswith("how do i interpret this requirement")
            ),
            default=min(
                next_indicator_y,
                page.height_points * 0.92,
                number_line.bbox_points[1] + 150,
            ),
        )
        next_heading_y = min(next_heading_y, next_indicator_y)
        body = [
            line for line in lines
            if number_line.bbox_points[1] - 4 <= line.bbox_points[1] < next_heading_y - 2
            and line.bbox_points[0] >= header.bbox_points[0] - 12
            and line.id != number_line.id
        ]
        if not body:
            continue
        number = NUMBER_RE.match(_clean(number_line.text))
        assert number is not None
        x0 = min(indicator.bbox_points[0], number_line.bbox_points[0])
        x1 = max(header.bbox_points[2], *(line.bbox_points[2] for line in body))
        y0 = min(indicator.bbox_points[1], header.bbox_points[1])
        y1 = max(number_line.bbox_points[3], *(line.bbox_points[3] for line in body))
        boundary = (indicator.bbox_points[2] + header.bbox_points[0]) / 2
        candidates.append(RequirementCandidate(
            page_index=page.page_index,
            requirement_number=number.group(1),
            bbox_points=(x0, y0, x1, y1),
            column_boundary_points=boundary,
            indicator_text=_clean(indicator.text),
            requirement_text=_clean(header.text),
            support_object_ids=[indicator.id, header.id, number_line.id] + [line.id for line in body],
            confidence=0.90,
        ))
    return candidates


def _possible_numbering_gaps(values: list[str]) -> list[str]:
    by_parent: dict[tuple[int, ...], set[int]] = defaultdict(set)
    for value in values:
        parts = tuple(int(part) for part in value.split("."))
        if len(parts) >= 2:
            by_parent[parts[:-1]].add(parts[-1])
    gaps: list[str] = []
    for parent, children in by_parent.items():
        if len(children) < 2:
            continue
        for missing in range(min(children), max(children) + 1):
            if missing not in children:
                gaps.append(".".join(map(str, (*parent, missing))))
    return sorted(gaps, key=lambda value: tuple(map(int, value.split("."))))


def learn_document_profile(
    pages: list[NativePage], *, marginal_page_count: int = 0
) -> DocumentProfile:
    raw_candidates = [
        candidate for page in pages for candidate in _candidates_for_page(page)
    ]
    template: RequirementTemplate | None = None
    candidates: list[RequirementCandidate] = []
    if raw_candidates:
        by_page = {page.page_index: page for page in pages}
        left = median(
            candidate.bbox_points[0] / by_page[candidate.page_index].width_points
            for candidate in raw_candidates
        )
        boundary = median(
            candidate.column_boundary_points / by_page[candidate.page_index].width_points
            for candidate in raw_candidates
        )
        right = median(
            candidate.bbox_points[2] / by_page[candidate.page_index].width_points
            for candidate in raw_candidates
        )
        for candidate in raw_candidates:
            page = by_page[candidate.page_index]
            deviations = (
                abs(candidate.bbox_points[0] / page.width_points - left),
                abs(candidate.column_boundary_points / page.width_points - boundary),
            )
            # Requirement prose naturally has different line lengths. The left
            # edge and semantic column boundary define this template; treating
            # the final glyph x-position as a template boundary drops short but
            # valid rows such as 1.1.1. Normalize the crop to the learned table
            # width only after the semantic anchors agree.
            has_requirement_width = (
                candidate.bbox_points[2] - candidate.column_boundary_points
                >= page.width_points * 0.20
            )
            if max(deviations) <= 0.07 and has_requirement_width:
                confidence = min(0.995, 0.92 + min(len(raw_candidates), 30) * 0.0025)
                x0, y0, _x1, y1 = candidate.bbox_points
                candidates.append(candidate.model_copy(update={
                    "bbox_points": (
                        min(x0, left * page.width_points),
                        y0,
                        right * page.width_points,
                        y1,
                    ),
                    "column_boundary_points": boundary * page.width_points,
                    "confidence": confidence,
                }))
        support = len(candidates)
        template = RequirementTemplate(
            support_count=support,
            left_x_ratio=left,
            column_boundary_ratio=boundary,
            right_x_ratio=right,
            confidence=min(0.995, 0.90 + min(support, 19) * 0.005),
        )

    numbering = sorted(
        {candidate.requirement_number for candidate in candidates},
        key=lambda value: tuple(map(int, value.split("."))),
    )
    terminal_counts: Counter[str] = Counter()
    samples = 0
    for page in pages:
        for line in page.text_lines:
            text = _clean(line.text)
            if len(text) < 35 or text.casefold() in {"indicator:", "requirement:"}:
                continue
            samples += 1
            terminal_counts[TERMINALS.get(text[-1], "none")] += 1
    punctuated = samples - terminal_counts.get("none", 0)
    return DocumentProfile(
        page_count=len(pages),
        requirement_template=template,
        requirement_candidates=candidates,
        numbering=NumberingProfile(
            observed=numbering,
            possible_gaps=_possible_numbering_gaps(numbering),
        ),
        terminals=TerminalProfile(
            sample_count=samples,
            terminal_counts=dict(terminal_counts),
            punctuation_rate=punctuated / samples if samples else 0.0,
        ),
        marginal_page_count=marginal_page_count,
    )
