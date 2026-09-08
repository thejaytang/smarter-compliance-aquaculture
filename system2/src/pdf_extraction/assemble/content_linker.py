from __future__ import annotations

import re

from ..config import LinkSettings
from ..models import Block, BlockType, ContentLink, ReviewItem


EXPLICIT_RE = re.compile(
    r"\b(Table|Figure|Fig\.|Section|Clause|Annex|Appendix)\s+([A-Z0-9][\w.-]*)\b",
    re.IGNORECASE,
)
FOOTNOTE_RE = re.compile(r"\[\^(\d{1,2})\]|\[(\d{1,2})\]")
INFERRED_RE = re.compile(
    r"\b(?:the\s+)?(?:(table|figure)\s+(below|above)|following\s+(table|figure))\b",
    re.IGNORECASE,
)
VISUAL_INTRO_RE = re.compile(r"\b(?:examples?|illustrations?|diagrams?)\b.{0,40}\bbelow\b", re.I)


def _target_maps(blocks: dict[str, Block]) -> tuple[dict[tuple[str, str], str], dict[str, list[str]]]:
    explicit: dict[tuple[str, str], str] = {}
    by_type: dict[str, list[str]] = {
        "table": [], "figure": [], "section": [], "footnote": [],
    }
    for block in blocks.values():
        kind = "section" if block.type == BlockType.HEADING else block.type.value
        if kind not in by_type:
            continue
        by_type[kind].append(block.id)
        candidate = block.index or (
            block.content.resolved_text if block.content and block.content.resolved_text else ""
        )
        if candidate:
            if block.type == BlockType.TABLE:
                match = re.match(r"\s*(Table)\s+([A-Z0-9][\w.-]*)\b", candidate, re.I)
            elif block.type == BlockType.FIGURE:
                match = re.match(r"\s*(Figure|Fig\.)\s+([A-Z0-9][\w.-]*)\b", candidate, re.I)
            elif block.type == BlockType.HEADING:
                match = re.match(
                    r"\s*(Section|Clause|Annex|Appendix)\s+([A-Z0-9][\w.-]*)\b",
                    candidate,
                    re.I,
                )
            else:
                match = None
            if match:
                raw_kind = match.group(1).lower()
                kind = "table" if raw_kind == "table" else "figure" if raw_kind in {"figure", "fig."} else "section"
                explicit[(kind, match.group(2).lower())] = block.id
            if block.type == BlockType.FOOTNOTE:
                marker = re.match(r"^\s*\[?(\d+)\]?", candidate)
                if marker:
                    explicit[("footnote", marker.group(1))] = block.id
    return explicit, by_type


def _nearest_object(block: Block, kind: str, direction: str, blocks: dict[str, Block]) -> str | None:
    if not block.parent_id or block.parent_id not in blocks:
        return None
    siblings = blocks[block.parent_id].children
    try:
        index = siblings.index(block.id)
    except ValueError:
        return None
    candidates = siblings[index + 1:] if direction != "above" else list(reversed(siblings[:index]))
    return next((item for item in candidates if item in blocks and blocks[item].type.value == kind), None)


def enrich_content_links(
    blocks: dict[str, Block], settings: LinkSettings
) -> list[ReviewItem]:
    explicit, _ = _target_maps(blocks)
    reviews: list[ReviewItem] = []
    for block in list(blocks.values()):
        if block.type in {BlockType.HEADER, BlockType.FOOTER, BlockType.FOOTNOTE}:
            continue
        texts: list[str] = []
        if block.content and block.content.resolved_text:
            texts.append(block.content.resolved_text)
        if block.table:
            texts.extend(
                cell.content.resolved_text or ""
                for cell in sorted(block.table.cells, key=lambda item: (item.row, item.column))
            )
        text = "\n".join(value for value in texts if value)
        if not text:
            continue
        links = list(block.content_links)
        seen = {link.target_id for link in links}
        for match in EXPLICIT_RE.finditer(text):
            raw_kind = match.group(1).lower()
            kind = "table" if raw_kind == "table" else "figure" if raw_kind in {"figure", "fig."} else "section"
            target = explicit.get((kind, match.group(2).lower()))
            if target and target != block.id and target not in seen:
                links.append(ContentLink(
                    target_id=target, anchor_text=match.group(0), link_type="explicit",
                    confidence=1.0,
                    evidence_segment_ids=[segment.id for segment in block.segments],
                ))
                seen.add(target)
            elif kind == "section":
                block.operations.append({
                    "operation": "unresolved_cross_document_reference_candidate",
                    "anchor_text": match.group(0),
                    "target_kind": kind,
                })
        for match in FOOTNOTE_RE.finditer(text):
            marker = match.group(1) or match.group(2)
            target = explicit.get(("footnote", marker))
            if target and target != block.id and target not in seen:
                links.append(ContentLink(
                    target_id=target, anchor_text=match.group(0), link_type="explicit",
                    relation="footnote_reference", confidence=1.0,
                    evidence_segment_ids=[segment.id for segment in block.segments],
                ))
                seen.add(target)
        if VISUAL_INTRO_RE.search(text) and block.parent_id in blocks:
            siblings = blocks[block.parent_id].children
            try:
                start = siblings.index(block.id) + 1
            except ValueError:
                start = len(siblings)
            targets: list[str] = []
            for sibling_id in siblings[start:]:
                sibling = blocks.get(sibling_id)
                if not sibling:
                    continue
                if sibling.type == BlockType.HEADING:
                    break
                if sibling.type == BlockType.FIGURE:
                    targets.append(sibling_id)
                elif targets and sibling.type not in {BlockType.FOOTNOTE}:
                    break
            for target in targets:
                if target in seen:
                    continue
                links.append(ContentLink(
                    target_id=target,
                    anchor_text=VISUAL_INTRO_RE.search(text).group(0),
                    link_type="inferred",
                    relation="introduces_visual_examples",
                    confidence=settings.inferred_link_confidence,
                    evidence_segment_ids=[segment.id for segment in block.segments],
                ))
                seen.add(target)
        for match in INFERRED_RE.finditer(text):
            kind = (match.group(1) or match.group(3) or "").lower()
            direction = (match.group(2) or "below").lower()
            target = _nearest_object(block, kind, direction, blocks)
            if not target or target in seen:
                continue
            links.append(ContentLink(
                target_id=target, anchor_text=match.group(0), link_type="inferred",
                relation="deictic_reference", confidence=settings.inferred_link_confidence,
                evidence_segment_ids=[segment.id for segment in block.segments],
            ))
            seen.add(target)
            if settings.inferred_links_require_review:
                reviews.append(ReviewItem(
                    id=f"review_inferred_link_{block.id}_{target}", target_id=block.id,
                    reason="inferred_content_link", severity="warning",
                    candidate_action=f"confirm_link:{target}",
                    confidence=settings.inferred_link_confidence,
                    evidence_segment_ids=[segment.id for segment in block.segments],
                ))
        blocks[block.id] = block.model_copy(
            update={"content_links": links, "has_linked_content": bool(links)}
        )
    return reviews
