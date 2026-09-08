from __future__ import annotations

import json
from pathlib import Path

from ..models import BlockType, Document, RequirementStatus, ResolutionStatus


# Requirement source regions have two different locality contracts.  Direct
# evidence must be present in the processed page window so the extracted
# Requirement can be verified from the emitted partial document.  A hierarchy
# heading is supporting evidence learned from the full source PDF and may
# legitimately precede that window.  Keep this allow-list deliberately narrow:
# adding a new role requires an explicit provenance decision.
_OUT_OF_WINDOW_SUPPORTING_REQUIREMENT_ROLES = frozenset(
    {"criterion_heading", "continuation_anchor", "footnote"}
)


def write_schema(path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(Document.model_json_schema(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


def validate_document(document: Document) -> list[str]:
    # Keep jsonschema behind the canonical-validation call. Some consumers only
    # need models or orchestration metadata and should not initialize this
    # optional validation dependency during import.
    from jsonschema import Draft202012Validator

    errors: list[str] = []
    schema = Document.model_json_schema()
    validator = Draft202012Validator(schema)
    for error in sorted(validator.iter_errors(document.model_dump(mode="json")), key=str):
        path = ".".join(map(str, error.absolute_path))
        errors.append(f"json_schema:{path}:{error.message}")

    block_ids = set(document.blocks)
    all_ids: set[str] = set()

    def register(identifier: str, kind: str) -> None:
        if identifier in all_ids:
            errors.append(f"duplicate ID {identifier} ({kind})")
        all_ids.add(identifier)

    for conflict in document.conflicts:
        register(conflict.id, "conflict")
    for span_id, span in document.evidence_spans.items():
        register(span.id, "evidence_span")
        if span_id != span.id:
            errors.append(f"evidence span map key mismatch: {span_id}")
    for review in document.review_items:
        register(review.id, "review_item")
    for event in document.audit_events:
        register(event.id, "audit_event")
    page_lookup = {page.page_index: page for page in document.pages}
    selected = set(document.processing.processed_page_indices)
    partial_page_window = (
        bool(selected)
        and set(page_lookup) == selected
        and len(selected) < document.source.page_count
    )
    if selected:
        if set(page_lookup) != selected:
            errors.append("page records do not match processed_page_indices")
        if any(index >= document.source.page_count for index in selected):
            errors.append("processed page index exceeds source page count")
    elif len(document.pages) != document.source.page_count:
        errors.append("page count does not match source metadata")
    if document.quality.processed_page_count != len(document.pages):
        errors.append("processed page count does not match page records")
    if len({page.page_index for page in document.pages}) != len(document.pages):
        errors.append("duplicate page_index")
    for root_id in document.root_block_ids:
        if root_id not in block_ids:
            errors.append(f"missing root block: {root_id}")
    for block_id, block in document.blocks.items():
        register(block.id, "block")
        if block.id != block_id:
            errors.append(f"block map key mismatch: {block_id}")
        if block.parent_id is not None and block.parent_id not in block_ids:
            errors.append(f"missing parent {block.parent_id} for {block_id}")
        for child_id in block.children:
            if child_id not in block_ids:
                errors.append(f"missing child {child_id} for {block_id}")
            elif document.blocks[child_id].parent_id != block_id:
                errors.append(f"parent-child mismatch: {block_id}->{child_id}")
        for link in block.content_links:
            if link.target_id not in block_ids:
                errors.append(f"missing content link target {link.target_id} for {block_id}")
        if block.type not in {BlockType.DOCUMENT, BlockType.SECTION} and not block.segments:
            errors.append(f"content block has no segment: {block_id}")
        for segment in block.segments:
            register(segment.id, "segment")
            if segment.page_index not in page_lookup:
                errors.append(f"segment page_index out of range: {segment.id}")
                continue
            page = page_lookup[segment.page_index]
            if segment.bbox.x1 > page.width + 0.5 or segment.bbox.y1 > page.height + 0.5:
                errors.append(f"segment bbox out of page bounds: {segment.id}")
        if block.content and block.content.resolved_text and block.content.resolution.selected_source == "none":
            errors.append(f"resolved text has no selected source: {block_id}")
        if block.content and block.content.resolution_status in {
            ResolutionStatus.AMBIGUOUS, ResolutionStatus.UNREADABLE
        } and block.content.resolved_text is not None:
            errors.append(f"unresolved content has resolved_text: {block_id}")
        if block.table:
            for cell in block.table.cells:
                register(cell.id, "table_cell")
                if cell.row + cell.row_span > block.table.row_count:
                    errors.append(f"table row span out of range: {cell.id}")
                if cell.column + cell.column_span > block.table.column_count:
                    errors.append(f"table column span out of range: {cell.id}")
                if cell.page_index is not None and cell.page_index not in page_lookup:
                    errors.append(f"table cell page_index out of range: {cell.id}")
                if cell.content.resolution_status in {
                    ResolutionStatus.AMBIGUOUS, ResolutionStatus.UNREADABLE
                }:
                    if cell.content.resolved_text is not None:
                        errors.append(f"unresolved table cell has resolved_text: {cell.id}")
                    if block_id not in document.review_queue:
                        errors.append(f"unresolved table cell missing from review queue: {cell.id}")
        if block.type == BlockType.CODE and block.code is None:
            errors.append(f"code block missing code payload: {block_id}")
        if block.type == BlockType.EQUATION and block.equation is None:
            errors.append(f"equation block missing equation payload: {block_id}")
        if block.code and block.type != BlockType.CODE:
            errors.append(f"non-code block has code payload: {block_id}")
        if block.equation and block.type != BlockType.EQUATION:
            errors.append(f"non-equation block has equation payload: {block_id}")
    for page in document.pages:
        for block_id in page.block_ids:
            if block_id not in block_ids:
                errors.append(f"page references missing block: {block_id}")
            elif not any(segment.page_index == page.page_index for segment in document.blocks[block_id].segments):
                errors.append(f"page-block segment mismatch: page {page.page_index}->{block_id}")

    for conflict in document.conflicts:
        if conflict.block_id not in block_ids:
            errors.append(f"conflict references missing block: {conflict.id}")
        if (
            conflict.severity == "critical"
            and conflict.resolution_status == ResolutionStatus.AMBIGUOUS
            and conflict.block_id not in document.review_queue
        ):
            errors.append(f"critical conflict missing from review queue: {conflict.id}")
        for span_id in conflict.evidence_span_ids:
            if span_id not in document.evidence_spans:
                errors.append(f"conflict references missing evidence span: {conflict.id}->{span_id}")

    requirement_ids: set[str] = set()
    requirement_region_ids: set[str] = set()
    formal_roles = {
        "requirement_id",
        "indicator_text",
        "requirement_value",
        "normative_text",
        "applicability",
        "requirement_continuation",
    }
    for requirement in document.requirements:
        if requirement.requirement_id in requirement_ids:
            errors.append(f"duplicate Requirement ID: {requirement.requirement_id}")
        requirement_ids.add(requirement.requirement_id)
        if not requirement.normative_text.strip():
            errors.append(f"Requirement has empty normative_text: {requirement.requirement_id}")
        if requirement.status == RequirementStatus.ACCEPTED:
            if not requirement.source_segments:
                errors.append(
                    f"accepted Requirement has no source segments: {requirement.requirement_id}"
                )
            roles = {segment.role for segment in requirement.source_segments}
            if "requirement_id" not in roles or not roles.intersection(
                formal_roles - {"requirement_id"}
            ):
                errors.append(
                    f"accepted Requirement lacks ID/formal provenance roles: "
                    f"{requirement.requirement_id}"
                )
            if any(
                segment.requires_human_review
                or segment.resolution_status != ResolutionStatus.RESOLVED
                for segment in requirement.source_segments
            ):
                errors.append(
                    f"accepted Requirement contains unresolved provenance: "
                    f"{requirement.requirement_id}"
                )

        region_by_id = {
            segment.segment_id: segment for segment in requirement.source_segments
        }
        if len(region_by_id) != len(requirement.source_segments):
            errors.append(
                f"duplicate source region in Requirement: {requirement.requirement_id}"
            )
        for segment in requirement.source_segments:
            if segment.segment_id in requirement_region_ids:
                errors.append(f"duplicate Requirement source region: {segment.segment_id}")
            requirement_region_ids.add(segment.segment_id)
            source_page_exists = segment.page_index < document.source.page_count
            supporting_out_of_window = (
                partial_page_window
                and source_page_exists
                and segment.role in _OUT_OF_WINDOW_SUPPORTING_REQUIREMENT_ROLES
            )
            if not source_page_exists:
                errors.append(
                    f"Requirement source page is outside source document: "
                    f"{segment.segment_id}"
                )
            elif segment.page_index not in page_lookup and not supporting_out_of_window:
                errors.append(
                    f"Requirement source page is outside processed pages: {segment.segment_id}"
                )
            page = page_lookup.get(segment.page_index)
            if segment.page_number is not None and segment.page_number != segment.page_index + 1:
                errors.append(
                    f"Requirement source page_number mismatch: {segment.segment_id}"
                )
            if page is not None and (
                segment.bbox.x1 > page.width + 0.5
                or segment.bbox.y1 > page.height + 0.5
            ):
                errors.append(f"Requirement source bbox out of bounds: {segment.segment_id}")
            if not (segment.source_text or segment.resolved_text or "").strip():
                errors.append(f"Requirement source region has no text: {segment.segment_id}")

        def validate_role_refs(
            owner: str, values: list[str], expected_role: str | None = None
        ) -> None:
            for segment_id in values:
                segment = region_by_id.get(segment_id)
                if segment is None:
                    errors.append(
                        f"{owner} references missing Requirement source region: {segment_id}"
                    )
                elif expected_role is not None and segment.role != expected_role:
                    errors.append(
                        f"{owner} references {segment_id} with role {segment.role}, "
                        f"expected {expected_role}"
                    )

        def validate_scope_ref(owner: str, scope_ref: object | None) -> None:
            if scope_ref is None:
                return
            previous_by_segment: dict[str, int] = {}
            for anchor in scope_ref.anchors:
                segment = region_by_id.get(anchor.source_segment_id)
                if segment is None:
                    errors.append(
                        f"{owner} scope anchor references missing Requirement source "
                        f"region: {anchor.source_segment_id}"
                    )
                    continue
                source_text = segment.source_text or ""
                if anchor.end_char > len(source_text):
                    errors.append(
                        f"{owner} scope anchor is outside source text: "
                        f"{anchor.source_segment_id}"
                    )
                    continue
                if source_text[anchor.start_char:anchor.end_char] != anchor.text:
                    errors.append(
                        f"{owner} scope anchor text mismatch: {anchor.source_segment_id}"
                    )
                previous_end = previous_by_segment.get(anchor.source_segment_id)
                if previous_end is not None and anchor.start_char < previous_end:
                    errors.append(
                        f"{owner} scope anchors overlap or are out of order: "
                        f"{anchor.source_segment_id}"
                    )
                previous_by_segment[anchor.source_segment_id] = anchor.end_char

        for index, modality in enumerate(requirement.modalities):
            validate_scope_ref(
                f"Requirement {requirement.requirement_id} modality {index}",
                modality.scope_ref,
            )
        for field_name in ("negations", "conditions", "exceptions", "exemptions", "dates"):
            for index, item in enumerate(getattr(requirement, field_name)):
                validate_scope_ref(
                    f"Requirement {requirement.requirement_id} {field_name} {index}",
                    item.scope_ref,
                )
        for field_name in (
            "normative_subject_evidence",
            "applicability_evidence",
        ):
            for index, item in enumerate(getattr(requirement, field_name)):
                owner = f"Requirement {requirement.requirement_id} {field_name} {index}"
                validate_role_refs(owner, item.source_segment_ids)
                validate_scope_ref(owner, item)
                anchor_ids = [anchor.source_segment_id for anchor in item.anchors]
                if anchor_ids != item.source_segment_ids:
                    errors.append(
                        f"{owner} source_segment_ids do not match anchor order"
                    )

        for threshold in requirement.thresholds:
            validate_role_refs(
                f"Requirement {requirement.requirement_id} threshold",
                threshold.source_segment_ids,
            )
            validate_scope_ref(
                f"Requirement {requirement.requirement_id} threshold",
                threshold.scope_ref,
            )
        for action in requirement.client_actions:
            validate_role_refs(
                f"Requirement {requirement.requirement_id} client action",
                action.source_segment_ids,
                "client_action",
            )
        for action in requirement.auditor_actions:
            validate_role_refs(
                f"Requirement {requirement.requirement_id} auditor action",
                action.source_segment_ids,
                "auditor_action",
            )

        native_ref_roles: dict[str, set[str]] = {}
        for segment in requirement.source_segments:
            bucket = (
                "formal" if segment.role in formal_roles
                else "client" if segment.role == "client_action"
                else "auditor" if segment.role == "auditor_action"
                else "context"
            )
            for native_ref in segment.native_object_refs:
                native_ref_roles.setdefault(native_ref, set()).add(bucket)
        for native_ref, buckets in native_ref_roles.items():
            if len(buckets) > 1:
                errors.append(
                    f"Requirement native evidence reused across roles: "
                    f"{requirement.requirement_id}->{native_ref}:{sorted(buckets)}"
                )

    segment_ids = {
        segment.id for block in document.blocks.values() for segment in block.segments
    }
    for span in document.evidence_spans.values():
        if span.block_id not in block_ids:
            errors.append(f"evidence span references missing block: {span.id}")
        if span.segment_id not in segment_ids:
            errors.append(f"evidence span references missing segment: {span.id}")
        if span.page_index not in page_lookup:
            errors.append(f"evidence span page_index out of range: {span.id}")
        elif span.bbox.x1 > page_lookup[span.page_index].width + 0.5 or span.bbox.y1 > page_lookup[span.page_index].height + 0.5:
            errors.append(f"evidence span bbox out of page bounds: {span.id}")
        if span.resolution_status == ResolutionStatus.AMBIGUOUS and not span.requires_human_review:
            errors.append(f"ambiguous evidence span not marked for review: {span.id}")

    if document.page_completeness:
        if {report.page_index for report in document.page_completeness} != {
            page.page_index for page in document.pages
        }:
            errors.append("page completeness reports do not match document pages")
        for report in document.page_completeness:
            if report.assigned_native_object_count + report.unassigned_native_object_count != report.native_object_count:
                errors.append(f"native completeness count mismatch: page {report.page_index}")

    if document.audit_events:
        revisions = [event.revision for event in document.audit_events]
        if revisions != list(range(1, len(revisions) + 1)):
            errors.append("audit event revisions are not contiguous and append-only")
        if document.revision != revisions[-1]:
            errors.append("document revision does not match audit log")
    elif document.revision != 0:
        errors.append("document revision is nonzero without audit events")

    pending_targets = list(dict.fromkeys(
        item.target_id for item in document.review_items if item.status == "pending"
    ))
    if document.review_queue != pending_targets:
        errors.append("review_queue does not match pending review_items")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(block_id: str) -> None:
        if block_id in visiting:
            errors.append(f"cycle detected at {block_id}")
            return
        if block_id in visited or block_id not in document.blocks:
            return
        visiting.add(block_id)
        for child_id in document.blocks[block_id].children:
            visit(child_id)
        visiting.remove(block_id)
        visited.add(block_id)

    for root_id in document.root_block_ids:
        visit(root_id)
    if visited != block_ids:
        errors.append(f"unreachable blocks: {sorted(block_ids - visited)}")
    return errors
