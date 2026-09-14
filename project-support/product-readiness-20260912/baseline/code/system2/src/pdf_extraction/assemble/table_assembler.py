from __future__ import annotations

import html
import re

from ..config import AssemblySettings
from ..models import (
    Block, BlockType, BoundingBox, Page, ReviewItem, TableCell, TextContent,
)
from .paragraph_assembler import _remove_block


def _row_values(block: Block, row: int) -> list[str]:
    assert block.table
    cells = sorted((cell for cell in block.table.cells if cell.row == row), key=lambda cell: cell.column)
    return [re.sub(r"\s+", " ", cell.content.resolved_text or "").strip().casefold() for cell in cells]


def _column_centers(block: Block) -> list[float]:
    assert block.table
    centers: dict[int, list[float]] = {}
    for cell in block.table.cells:
        centers.setdefault(cell.column, []).append((cell.bbox.x0 + cell.bbox.x1) / 2)
    return [sum(centers[column]) / len(centers[column]) for column in sorted(centers)]


def _score(left: Block, right: Block, pages: dict[int, Page]) -> float:
    if not left.table or not right.table or left.parent_id != right.parent_id or right.index:
        return 0.0
    left_segment, right_segment = left.segments[-1], right.segments[0]
    if right_segment.page_index != left_segment.page_index + 1:
        return 0.0
    score = 0.0
    if left_segment.bbox.y1 >= pages[left_segment.page_index].height * 0.72:
        score += 0.2
    if right_segment.bbox.y0 <= pages[right_segment.page_index].height * 0.28:
        score += 0.2
    if left.table.column_count == right.table.column_count:
        score += 0.25
    left_width = left_segment.bbox.x1 - left_segment.bbox.x0
    right_width = right_segment.bbox.x1 - right_segment.bbox.x0
    if min(left_width, right_width) / max(left_width, right_width) >= 0.88:
        score += 0.15
    left_centers, right_centers = _column_centers(left), _column_centers(right)
    if len(left_centers) == len(right_centers) and left_centers:
        mean_delta = sum(abs(a - b) for a, b in zip(left_centers, right_centers, strict=True)) / len(left_centers)
        if mean_delta <= 18:
            score += 0.2
    repeated_header = _row_values(left, 0) == _row_values(right, 0) and bool(_row_values(left, 0))
    left_ids = [
        value for row in range(1, left.table.row_count)
        for value in _row_values(left, row)[:1]
        if re.fullmatch(r"\d+(?:\.\d+)+", value)
    ]
    right_ids = [
        value for row in range(1, right.table.row_count)
        for value in _row_values(right, row)[:1]
        if re.fullmatch(r"\d+(?:\.\d+)+", value)
    ]
    if repeated_header and left_ids and right_ids:
        left_parts = [int(value) for value in left_ids[-1].split(".")]
        right_parts = [int(value) for value in right_ids[0].split(".")]
        sequential = (
            len(left_parts) == len(right_parts)
            and left_parts[:-1] == right_parts[:-1]
            and right_parts[-1] == left_parts[-1] + 1
        )
        if sequential:
            score += 0.2
    return min(1.0, score)


def _render_html(row_count: int, column_count: int, cells: list[TableCell]) -> str:
    lookup = {(cell.row, cell.column): cell for cell in cells}
    rows: list[str] = []
    for row in range(row_count):
        values = []
        for column in range(column_count):
            cell = lookup.get((row, column))
            value = html.escape(cell.content.resolved_text or "").replace("\n", "<br>") if cell else ""
            tag = "th" if cell and cell.is_header else "td"
            values.append(f"<{tag}>{value}</{tag}>")
        rows.append("<tr>" + "".join(values) + "</tr>")
    return "<table>" + "".join(rows) + "</table>"


def _append_content(left: TextContent, right: TextContent, *, new_item: bool) -> None:
    separator = "\n" if new_item else " "
    for field in ("native_text", "ocr_text", "review_text", "resolved_text"):
        left_value = getattr(left, field)
        right_value = getattr(right, field)
        if right_value:
            setattr(
                left,
                field,
                f"{left_value.rstrip()}{separator}{right_value.lstrip()}" if left_value else right_value,
            )


def _union_bbox(blocks: list[Block]) -> BoundingBox:
    segments = [segment for block in blocks for segment in block.segments]
    return BoundingBox(
        x0=min(segment.bbox.x0 for segment in segments),
        y0=min(segment.bbox.y0 for segment in segments),
        x1=max(segment.bbox.x1 for segment in segments),
        y1=max(segment.bbox.y1 for segment in segments),
    )


def _recover_captioned_header_only_tables(
    blocks: dict[str, Block], pages: dict[int, Page], replacements: dict[str, str] | None,
) -> None:
    """Recover aligned body rows omitted below a captioned two-column header.

    The repair requires a ``Table N`` caption, a parsed two-cell header, at
    least two short labels aligned to the first column, and non-empty prose
    aligned to the second column.  Row bands are defined by label centres, so
    vertically centred labels remain associated with descriptions that start
    above them.  The body may continue onto exactly one following page.
    """
    for table_block in list(blocks.values()):
        if (
            table_block.type != BlockType.TABLE
            or not table_block.table
            or table_block.table.row_count != 1
            or table_block.table.column_count != 2
            or not table_block.index
            or not re.match(r"^Table\s+[A-Z0-9]", table_block.index.strip(), flags=re.I)
            or not table_block.segments
            or not table_block.parent_id
            or table_block.parent_id not in blocks
        ):
            continue
        headers = sorted(table_block.table.cells, key=lambda cell: cell.column)
        if len(headers) != 2 or any(not (cell.content.resolved_text or "").strip() for cell in headers):
            continue
        boundary = (headers[0].bbox.x1 + headers[1].bbox.x0) / 2
        parent = blocks[table_block.parent_id]
        if table_block.id not in parent.children:
            continue
        position = parent.children.index(table_block.id)
        start_page = table_block.segments[0].page_index
        candidates: list[Block] = []
        next_table: Block | None = None
        for sibling_id in parent.children[position + 1:]:
            sibling = blocks.get(sibling_id)
            if not sibling or not sibling.segments:
                continue
            page_index = sibling.segments[0].page_index
            if page_index > start_page + 1:
                break
            if sibling.type == BlockType.TABLE:
                next_table = sibling
                break
            if sibling.type == BlockType.HEADING:
                break
            if sibling.type in {BlockType.PARAGRAPH, BlockType.LIST}:
                candidates.append(sibling)
        labels = [
            block for block in candidates
            if block.segments[0].bbox.x0 < boundary - 20
            and block.segments[0].bbox.x1 <= boundary + 18
            and len((block.content.resolved_text or "").split()) <= 4
            and len(block.content.resolved_text or "") <= 48
        ]
        if len(labels) < 2:
            continue
        descriptions = [
            block for block in candidates
            if block not in labels and block.segments[0].bbox.x0 >= boundary - 12
        ]
        grouped_rows: list[tuple[Block, list[Block]]] = []
        for page_index in sorted({block.segments[0].page_index for block in labels}):
            page_labels = sorted(
                (block for block in labels if block.segments[0].page_index == page_index),
                key=lambda block: block.segments[0].bbox.y0,
            )
            centers = [
                (block.segments[0].bbox.y0 + block.segments[0].bbox.y1) / 2
                for block in page_labels
            ]
            lower = (
                table_block.segments[-1].bbox.y1 if page_index == start_page else 0.0
            )
            upper = (
                next_table.segments[0].bbox.y0
                if next_table and next_table.segments[0].page_index == page_index
                else pages[page_index].height
            )
            bounds = [lower]
            bounds.extend((left + right) / 2 for left, right in zip(centers, centers[1:], strict=False))
            bounds.append(upper)
            for index, label in enumerate(page_labels):
                row_descriptions = [
                    block for block in descriptions
                    if block.segments[0].page_index == page_index
                    and bounds[index] <= (
                        block.segments[0].bbox.y0 + block.segments[-1].bbox.y1
                    ) / 2 < bounds[index + 1]
                ]
                row_descriptions.sort(key=lambda block: block.segments[0].bbox.y0)
                if row_descriptions:
                    grouped_rows.append((label, row_descriptions))
        if len(grouped_rows) != len(labels):
            continue

        consumed: list[Block] = []
        new_cells = list(headers)
        for row, (label, row_descriptions) in enumerate(grouped_rows, start=1):
            description_content = row_descriptions[0].content.model_copy(deep=True)
            for continuation in row_descriptions[1:]:
                _append_content(description_content, continuation.content, new_item=False)
            new_cells.extend([
                TableCell(
                    id=f"{table_block.id}_recovered_r{row:03d}_c000",
                    row=row, column=0, page_index=label.segments[0].page_index,
                    bbox=_union_bbox([label]), content=label.content.model_copy(deep=True),
                ),
                TableCell(
                    id=f"{table_block.id}_recovered_r{row:03d}_c001",
                    row=row, column=1, page_index=label.segments[0].page_index,
                    bbox=_union_bbox(row_descriptions), content=description_content,
                ),
            ])
            consumed.extend([label, *row_descriptions])

        caption_continuation: Block | None = None
        prior_ids = parent.children[:position]
        if prior_ids:
            prior = blocks.get(prior_ids[-1])
            if (
                prior and prior.type == BlockType.PARAGRAPH and prior.content
                and prior.content.resolved_text and prior.segments
                and prior.segments[-1].page_index == start_page
                and 0 <= table_block.segments[0].bbox.y0 - prior.segments[-1].bbox.y1 <= 12
            ):
                caption_continuation = prior
                table_block.index = " ".join(
                    value.strip() for value in (
                        table_block.index, prior.content.resolved_text, table_block.note,
                    ) if value and value.strip()
                )
                table_block.note = None
                consumed.append(prior)

        table_block.table.cells = new_cells
        table_block.table.row_count = len(grouped_rows) + 1
        table_block.table.html = _render_html(
            table_block.table.row_count, table_block.table.column_count, new_cells
        )
        table_block.table.parser_backend += "+captioned-body-recovery"
        ordered_consumed = sorted(
            {block.id: block for block in consumed}.values(),
            key=lambda block: (block.segments[0].page_index, block.segments[0].bbox.y0),
        )
        table_block.segments.extend(
            segment for block in ordered_consumed for segment in block.segments
        )
        table_block.quality.structure_confidence = max(
            table_block.quality.structure_confidence or 0.0, 0.98
        )
        table_block.quality.requires_review = False
        table_block.quality.issues = [
            issue for issue in table_block.quality.issues if issue != "table_grid_incomplete"
        ]
        table_block.operations.append({
            "operation": "captioned_header_only_table_body_recovery",
            "source_fragment_ids": [table_block.id, *[block.id for block in ordered_consumed]],
            "decision": "auto_repair",
            "confidence": 0.98,
            "evidence": [
                "explicit_table_caption", "two_column_header_geometry",
                "multiple_aligned_row_labels", "non_empty_aligned_description_cells",
            ],
        })
        for block in ordered_consumed:
            if replacements is not None:
                replacements[block.id] = table_block.id
            _remove_block(blocks, pages, block.id, table_block.id)


def attach_profile_table_continuations(
    blocks: dict[str, Block], pages: list[Page], replacements: dict[str, str] | None = None,
) -> list[ReviewItem]:
    """Attach headerless next-page clauses to a learned Requirement table.

    This repair is deliberately narrow.  It requires both a learned two-column
    Requirement table ending near the page foot and a next-page top sequence
    beginning with the next alphabetic clause marker.  It therefore restores
    source text already present in the PDF without inferring missing content.
    """
    page_lookup = {page.page_index: page for page in pages}
    reviews: list[ReviewItem] = []
    profile_tables = [
        block for block in blocks.values()
        if block.type == BlockType.TABLE
        and block.table
        and block.segments
        and block.table.column_count == 2
        and block.table.parser_backend.startswith("document-profile+")
    ]
    for table_block in profile_tables:
        assert table_block.table
        last_segment = table_block.segments[-1]
        next_page_index = last_segment.page_index + 1
        if next_page_index not in page_lookup:
            continue
        if last_segment.bbox.y1 < page_lookup[last_segment.page_index].height * 0.72:
            continue
        body_row = table_block.table.row_count - 1
        target_cell = next(
            (
                cell for cell in table_block.table.cells
                if cell.row == body_row and cell.column == table_block.table.column_count - 1
            ),
            None,
        )
        if target_cell is None or not target_cell.content.resolved_text:
            continue
        prior_text = target_cell.content.resolved_text
        prior_markers = re.findall(r"(?:^|\n|\s)([a-z])\.\s+", prior_text, flags=re.I)
        if not prior_markers:
            continue
        expected = chr(ord(prior_markers[-1].casefold()) + 1)

        candidates = [
            block for block in blocks.values()
            if block.id != table_block.id
            and block.type in {BlockType.LIST, BlockType.PARAGRAPH}
            and block.content
            and block.content.resolved_text
            and block.segments
            and block.segments[0].page_index == next_page_index
            and block.segments[0].bbox.y0 <= page_lookup[next_page_index].height * 0.28
            and block.parent_id == table_block.parent_id
        ]
        candidates.sort(key=lambda block: (block.segments[0].bbox.y0, block.segments[0].bbox.x0))
        if not candidates:
            continue
        first_match = re.match(
            r"^([a-z])\.\s+", candidates[0].content.resolved_text.strip(), flags=re.I
        )
        if not first_match or first_match.group(1).casefold() != expected:
            continue
        if candidates[0].segments[0].bbox.x0 < target_cell.bbox.x0 - 28:
            continue

        attached: list[Block] = []
        expected_marker = expected
        for candidate in candidates:
            text = candidate.content.resolved_text.strip()
            marker = re.match(r"^([a-z])\.\s+", text, flags=re.I)
            if marker:
                if marker.group(1).casefold() != expected_marker:
                    break
                expected_marker = chr(ord(expected_marker) + 1)
                new_item = True
            else:
                # A narrow indented paragraph directly after a clause is its
                # physical line continuation, not a new Requirement row.
                if not attached or candidate.segments[0].bbox.x0 < target_cell.bbox.x0 - 8:
                    break
                new_item = False
            _append_content(target_cell.content, candidate.content, new_item=new_item)
            table_block.segments.extend(candidate.segments)
            attached.append(candidate)

        if not attached:
            continue
        table_block.table.html = _render_html(
            table_block.table.row_count, table_block.table.column_count, table_block.table.cells
        )
        table_block.operations.append({
            "operation": "profile_table_cross_page_continuation_attachment",
            "source_fragment_ids": [table_block.id, *[item.id for item in attached]],
            "starting_clause": expected,
            "confidence": 0.98,
            "decision": "auto_merge",
            "evidence": [
                "document_profile_two_column_requirement_table",
                "next_page_top_sequential_clause_markers",
            ],
        })
        for candidate in attached:
            if replacements is not None:
                replacements[candidate.id] = table_block.id
            _remove_block(blocks, page_lookup, candidate.id, table_block.id)
    return reviews


def _split_requirement_content(content: TextContent, group: int) -> TextContent:
    pattern = re.compile(r"^(\d+(?:\.\d+)+)\s+(.+)$", flags=re.S)

    def split(value: str | None) -> str | None:
        if not value:
            return None
        match = pattern.match(value.strip())
        return match.group(group).strip() if match else None

    return content.model_copy(update={
        "native_text": split(content.native_text),
        "ocr_text": split(content.ocr_text),
        "review_text": split(content.review_text),
        "resolved_text": split(content.resolved_text),
    })


def _attach_adjacent_labeled_rows(
    blocks: dict[str, Block], pages: dict[int, Page], replacements: dict[str, str] | None,
) -> None:
    """Attach a numbered body row below a detached two-column label header."""
    for table_block in list(blocks.values()):
        if (
            table_block.type != BlockType.TABLE
            or not table_block.table
            or table_block.table.row_count != 1
            or table_block.table.column_count != 2
            or not table_block.segments
            or not table_block.parent_id
            or table_block.parent_id not in blocks
        ):
            continue
        headers = sorted(table_block.table.cells, key=lambda cell: cell.column)
        if len(headers) != 2:
            continue
        header_values = [
            re.sub(r"\s+", " ", cell.content.resolved_text or "").strip()
            for cell in headers
        ]
        if not all(value.endswith(":") for value in header_values):
            continue
        parent = blocks[table_block.parent_id]
        if table_block.id not in parent.children:
            continue
        position = parent.children.index(table_block.id)
        if position + 1 >= len(parent.children):
            continue
        candidate = blocks.get(parent.children[position + 1])
        if (
            candidate is None
            or candidate.type not in {BlockType.LIST, BlockType.PARAGRAPH}
            or candidate.children
            or not candidate.content
            or not candidate.content.resolved_text
            or not candidate.segments
        ):
            continue
        match = re.match(
            r"^(\d+(?:\.\d+)+)\s+(.+)$", candidate.content.resolved_text.strip(), flags=re.S
        )
        if not match:
            continue
        header_segment = table_block.segments[-1]
        body_segment = candidate.segments[0]
        if body_segment.page_index != header_segment.page_index:
            continue
        gap = body_segment.bbox.y0 - header_segment.bbox.y1
        horizontal_overlap = max(
            0.0,
            min(header_segment.bbox.x1, body_segment.bbox.x1)
            - max(header_segment.bbox.x0, body_segment.bbox.x0),
        )
        if (
            not -2.0 <= gap <= 32.0
            or horizontal_overlap / max(1.0, body_segment.bbox.x1 - body_segment.bbox.x0) < 0.75
        ):
            continue

        boundary = (headers[0].bbox.x1 + headers[1].bbox.x0) / 2
        boundary = max(body_segment.bbox.x0 + 1, min(body_segment.bbox.x1 - 1, boundary))
        for cell in headers:
            cell.is_header = True
        body_cells = [
            TableCell(
                id=f"{table_block.id}_adjacent_body_r001_c000",
                row=1, column=0,
                bbox=BoundingBox(
                    x0=header_segment.bbox.x0, y0=body_segment.bbox.y0,
                    x1=boundary, y1=body_segment.bbox.y1,
                ),
                page_index=body_segment.page_index,
                content=_split_requirement_content(candidate.content, 1),
            ),
            TableCell(
                id=f"{table_block.id}_adjacent_body_r001_c001",
                row=1, column=1,
                bbox=BoundingBox(
                    x0=boundary, y0=body_segment.bbox.y0,
                    x1=header_segment.bbox.x1, y1=body_segment.bbox.y1,
                ),
                page_index=body_segment.page_index,
                content=_split_requirement_content(candidate.content, 2),
            ),
        ]
        table_block.table.cells.extend(body_cells)
        table_block.table.row_count = 2
        table_block.table.html = _render_html(2, 2, table_block.table.cells)
        table_block.table.parser_backend += "+adjacent-numbered-row"
        table_block.segments.extend(candidate.segments)
        table_block.operations.append({
            "operation": "adjacent_numbered_table_row_attachment",
            "source_fragment_ids": [table_block.id, candidate.id],
            "column_boundary": boundary,
            "header_values": header_values,
            "decision": "auto_merge",
        })
        if replacements is not None:
            replacements[candidate.id] = table_block.id
        _remove_block(blocks, pages, candidate.id, table_block.id)


def _merge(left: Block, right: Block, score: float) -> None:
    assert left.table and right.table
    repeated_header = _row_values(left, 0) == _row_values(right, 0) and bool(_row_values(left, 0))
    source_cells = [cell for cell in right.table.cells if not (repeated_header and cell.row == 0)]
    row_offset = left.table.row_count - (1 if repeated_header else 0)
    moved: list[TableCell] = []
    for cell in source_cells:
        moved.append(cell.model_copy(update={
            "row": cell.row + row_offset,
            "id": f"{left.id}_merged_{cell.id}",
        }))
    joined_rows: list[dict[str, object]] = []
    left_last = [cell for cell in left.table.cells if cell.row == left.table.row_count - 1]
    right_first_row = 1 if repeated_header else 0
    right_first = [cell for cell in moved if cell.row == right_first_row + row_offset]
    if left_last and right_first:
        left_empty = {cell.column for cell in left_last if not cell.content.resolved_text}
        right_empty = {cell.column for cell in right_first if not cell.content.resolved_text}
        if left_empty and right_empty and left_empty.isdisjoint(right_empty):
            for cell in right_first:
                prior = next((item for item in left_last if item.column == cell.column), None)
                if prior and not prior.content.resolved_text and cell.content.resolved_text:
                    prior.content = cell.content
            moved = [cell for cell in moved if cell not in right_first]
            moved = [cell.model_copy(update={"row": cell.row - 1}) for cell in moved]
            joined_rows.append({"left_row": left.table.row_count - 1, "right_row": right_first_row})
    left.table.cells.extend(moved)
    left.table.row_count = max((cell.row + cell.row_span for cell in left.table.cells), default=1)
    left.table.html = _render_html(left.table.row_count, left.table.column_count, left.table.cells)
    left.segments.extend(right.segments)
    left.operations.append({
        "operation": "table_cross_page_merge",
        "source_fragment_ids": [left.id, right.id],
        "removed_repeated_headers": [0] if repeated_header else [],
        "joined_rows": joined_rows,
        "confidence": score,
        "decision": "auto_merge",
    })


def assemble_tables(
    blocks: dict[str, Block], pages: list[Page], settings: AssemblySettings,
    replacements: dict[str, str] | None = None,
) -> list[ReviewItem]:
    page_lookup = {page.page_index: page for page in pages}
    tables = [block for block in blocks.values() if block.type == BlockType.TABLE and block.segments]
    tables.sort(key=lambda block: (block.segments[0].page_index, block.segments[0].bbox.y0))
    reviews: list[ReviewItem] = []
    consumed: set[str] = set()
    for left, right in zip(tables, tables[1:], strict=False):
        if left.id in consumed or right.id in consumed:
            continue
        intervening_heading = False
        if left.parent_id and left.parent_id in blocks:
            siblings = blocks[left.parent_id].children
            if left.id in siblings and right.id in siblings:
                start, end = sorted((siblings.index(left.id), siblings.index(right.id)))
                intervening_heading = any(
                    sibling in blocks and blocks[sibling].type == BlockType.HEADING
                    for sibling in siblings[start + 1:end]
                )
        score = 0.0 if intervening_heading else _score(left, right, page_lookup)
        if score >= settings.table_auto_merge_threshold:
            _merge(left, right, score)
            if replacements is not None:
                replacements[right.id] = left.id
            _remove_block(blocks, page_lookup, right.id, left.id)
            consumed.add(right.id)
        elif score >= settings.table_review_threshold:
            reviews.append(ReviewItem(
                id=f"review_table_merge_{left.id}_{right.id}", target_id=left.id,
                reason="cross_page_table_candidate", severity="warning",
                candidate_action=f"merge_with:{right.id}", confidence=score,
                evidence_segment_ids=[left.segments[-1].id, right.segments[0].id],
            ))
    _attach_adjacent_labeled_rows(blocks, page_lookup, replacements)
    _recover_captioned_header_only_tables(blocks, page_lookup, replacements)
    return reviews
