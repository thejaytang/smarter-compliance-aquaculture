from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from ...models import Block, BlockType, Document, Requirement, RequirementStatus
from .models import RegulatoryIRDocument, RegulatoryStatement


_MODAL = re.compile(r"\b(shall not|must not|may not|shall|must|should|may|required to|prohibited from)\b", re.I)
_THRESHOLD = re.compile(
    r"(?:[<>≤≥]=?\s*)?\d+(?:[.,]\d+)?\s*(?:%|mg|kg|g|ml|l|°c|kpa|mpa|bar|days?|hours?|years?)\b",
    re.I,
)
_DATE = re.compile(
    r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b",
    re.I,
)
_REFERENCE = re.compile(r"\b(?:section|clause|annex|appendix|table|figure|fig\.)\s+[A-Z0-9][\w.-]*", re.I)
_CONDITION = re.compile(r"\b(?:if|when|where|provided that)\b(.+?)(?=[.;]|$)", re.I)
_EXCEPTION = re.compile(r"\b(?:unless|except(?: where| when| for)?)\b(.+?)(?=[.;]|$)", re.I)
_FORMAL_SOURCE_ROLES = {
    "requirement_id",
    "indicator_text",
    "requirement_value",
    "normative_text",
    "applicability",
    "requirement_continuation",
    "footnote",
}


def _text(block: Block) -> str:
    if block.content and block.content.resolved_text:
        return block.content.resolved_text
    return ""


def _statement(
    block: Block,
    text: str,
    modal_match: re.Match[str],
    requirement_id: str | None = None,
) -> RegulatoryStatement:
    before = text[: modal_match.start()].strip(" ,:;\n")
    after = text[modal_match.end():].strip(" ,:;\n")
    entity = before.split(".")[-1].strip() or None
    action_match = re.match(r"(?:be\s+)?([A-Za-z][\w-]*)\b", after)
    action = action_match.group(1) if action_match else None
    object_value = after[action_match.end():].strip(" ,:;") if action_match else after
    condition_match = _CONDITION.search(text)
    exception_match = _EXCEPTION.search(text)
    threshold_match = _THRESHOLD.search(text)
    date_match = _DATE.search(text)
    segment_ids = [segment.id for segment in block.segments]
    page_indices = sorted({segment.page_index for segment in block.segments})
    digest = hashlib.sha256(
        f"{block.id}:{requirement_id or ''}:{modal_match.start()}:{text}".encode()
    ).hexdigest()[:16]
    return RegulatoryStatement(
        id=f"reg_{digest}",
        requirement_id=requirement_id,
        regulated_entity=entity,
        modality=modal_match.group(1).lower(),
        action=action,
        object=object_value or None,
        condition=condition_match.group(1).strip() if condition_match else None,
        exception=exception_match.group(1).strip() if exception_match else None,
        threshold=threshold_match.group(0) if threshold_match else None,
        effective_date=date_match.group(0) if date_match else None,
        cross_references=[match.group(0) for match in _REFERENCE.finditer(text)],
        source_block_ids=[block.id],
        source_segment_ids=segment_ids,
        source_page_indices=page_indices,
        confidence=0.9 if block.quality.requires_review is False else 0.65,
    )


def _statement_from_requirement(
    requirement: Requirement,
    text: str,
    modal_match: re.Match[str],
) -> RegulatoryStatement:
    before = text[: modal_match.start()].strip(" ,:;\n")
    after = text[modal_match.end():].strip(" ,:;\n")
    entity = before.split(".")[-1].strip() or None
    action_match = re.match(r"(?:be\s+)?([A-Za-z][\w-]*)\b", after)
    action = action_match.group(1) if action_match else None
    object_value = after[action_match.end():].strip(" ,:;") if action_match else after
    condition_match = _CONDITION.search(text)
    exception_match = _EXCEPTION.search(text)
    threshold_match = _THRESHOLD.search(text)
    date_match = _DATE.search(text)
    source_segments = [
        segment for segment in requirement.source_segments
        if segment.role in _FORMAL_SOURCE_ROLES
    ]
    digest = hashlib.sha256(
        f"{requirement.requirement_id}:{modal_match.start()}:{text}".encode()
    ).hexdigest()[:16]
    return RegulatoryStatement(
        id=f"reg_{digest}",
        requirement_id=requirement.requirement_id,
        regulated_entity=entity,
        modality=modal_match.group(1).lower(),
        action=action,
        object=object_value or None,
        condition=condition_match.group(1).strip() if condition_match else None,
        exception=exception_match.group(1).strip() if exception_match else None,
        threshold=threshold_match.group(0) if threshold_match else None,
        effective_date=date_match.group(0) if date_match else None,
        cross_references=[match.group(0) for match in _REFERENCE.finditer(text)],
        source_block_ids=[],
        source_segment_ids=[segment.segment_id for segment in source_segments],
        source_page_indices=sorted({segment.page_index for segment in source_segments}),
        confidence=(
            requirement.confidence
            if requirement.confidence is not None
            else 0.95 if requirement.status == RequirementStatus.ACCEPTED else 0.60
        ),
    )


def _extract_from_canonical_requirements(document: Document) -> RegulatoryIRDocument:
    statements: list[RegulatoryStatement] = []
    review_required: list[str] = []
    requirement_review_required: list[str] = []
    for requirement in document.requirements:
        if requirement.status != RequirementStatus.ACCEPTED:
            requirement_review_required.append(requirement.requirement_id)
        if not any(
            segment.role in _FORMAL_SOURCE_ROLES
            for segment in requirement.source_segments
        ):
            continue
        for modal in _MODAL.finditer(requirement.normative_text):
            statement = _statement_from_requirement(
                requirement, requirement.normative_text, modal
            )
            statements.append(statement)
            if requirement.status != RequirementStatus.ACCEPTED:
                review_required.append(statement.id)
    return RegulatoryIRDocument(
        document_id=document.document_id,
        requirements=document.requirements,
        statements=statements,
        review_required=list(dict.fromkeys(review_required)),
        requirement_review_required=list(
            dict.fromkeys(requirement_review_required)
        ),
        formal_requirement_ids=list(dict.fromkeys(
            requirement.requirement_id for requirement in document.requirements
        )),
        missing_requirement_ids=[],
    )


def extract_regulatory_ir(document: Document) -> RegulatoryIRDocument:
    if document.requirements:
        return _extract_from_canonical_requirements(document)
    statements: list[RegulatoryStatement] = []
    review_required: list[str] = []
    formal_requirement_ids: list[str] = []
    extracted_formal_ids: set[str] = set()
    for block in document.blocks.values():
        if block.type != BlockType.TABLE or not block.table or block.table.column_count < 2:
            continue
        cells = {(cell.row, cell.column): cell for cell in block.table.cells}
        header_left = (cells.get((0, 0)).content.resolved_text if cells.get((0, 0)) else "") or ""
        header_right = (cells.get((0, 1)).content.resolved_text if cells.get((0, 1)) else "") or ""
        if "indicator" not in header_left.casefold() or "requirement" not in header_right.casefold():
            continue
        for row in range(1, block.table.row_count):
            left = cells.get((row, 0))
            right = cells.get((row, 1))
            left_text = (left.content.resolved_text if left else "") or ""
            id_match = re.match(r"^(\d+(?:\.\d+)+)(?:[.:]|\s|$)", left_text.strip())
            if not id_match:
                continue
            requirement_id = id_match.group(1)
            formal_requirement_ids.append(requirement_id)
            text = (right.content.resolved_text if right else "") or ""
            modal = _MODAL.search(text)
            if not modal:
                continue
            statement = _statement(block, text, modal, requirement_id=requirement_id)
            statements.append(statement)
            extracted_formal_ids.add(requirement_id)
            if block.quality.requires_review:
                review_required.append(statement.id)
    eligible = {
        BlockType.PARAGRAPH, BlockType.LIST, BlockType.LIST_ITEM,
        BlockType.FOOTNOTE,
    }
    for block in document.blocks.values():
        if block.type not in eligible:
            continue
        text = _text(block)
        if not text:
            continue
        for modal in _MODAL.finditer(text):
            statement = _statement(block, text, modal)
            if not statement.source_segment_ids:
                review_required.append(statement.id)
                continue
            if block.quality.requires_review:
                review_required.append(statement.id)
            statements.append(statement)
    return RegulatoryIRDocument(
        document_id=document.document_id,
        statements=statements,
        review_required=list(dict.fromkeys(review_required)),
        formal_requirement_ids=list(dict.fromkeys(formal_requirement_ids)),
        missing_requirement_ids=[
            value for value in dict.fromkeys(formal_requirement_ids)
            if value not in extracted_formal_ids
        ],
    )


def export_regulatory_ir(document: Document, path: str | Path) -> tuple[Path, RegulatoryIRDocument]:
    ir = extract_regulatory_ir(document)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(ir.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
    return target, ir
