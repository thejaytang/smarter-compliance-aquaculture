from __future__ import annotations

from ..config import AssemblySettings
import re

from ..models import Block, BlockType, Page, ReviewItem
from .hierarchy import repair_heading_hierarchy, repair_list_hierarchy, repair_sibling_orders
from .paragraph_assembler import _join_text, _remove_block, assemble_paragraphs
from .table_assembler import assemble_tables, attach_profile_table_continuations


def _suppress_table_edge_duplicate_fragments(
    blocks: dict[str, Block], pages: list[Page], replacements: dict[str, str] | None = None,
) -> None:
    """Remove tiny right-edge fragments already present in a table cell.

    Born-digital PDFs sometimes expose a clipped glyph twice: once inside the
    recovered table and once as a separate layout object. The raw native object
    remains in evidence; only the duplicate semantic block is suppressed.
    """
    page_lookup = {page.page_index: page for page in pages}
    tables_by_page: dict[int, list[Block]] = {}
    for table in blocks.values():
        if table.type != BlockType.TABLE or not table.table:
            continue
        for segment in table.segments:
            tables_by_page.setdefault(segment.page_index, []).append(table)

    for block in list(blocks.values()):
        if (
            block.type not in {BlockType.HEADING, BlockType.PARAGRAPH, BlockType.LIST}
            or not block.content
            or not block.content.resolved_text
            or len(block.segments) != 1
        ):
            continue
        text = block.content.resolved_text.strip()
        segment = block.segments[0]
        page = page_lookup.get(segment.page_index)
        if (
            not page
            or len(text) > 2
            or segment.bbox.x1 - segment.bbox.x0 > 10
            or segment.bbox.x0 < page.width * 0.85
        ):
            continue
        for table in tables_by_page.get(segment.page_index, []):
            table_segment = next(
                (item for item in table.segments if item.page_index == segment.page_index), None
            )
            if not table_segment:
                continue
            center_x = (segment.bbox.x0 + segment.bbox.x1) / 2
            center_y = (segment.bbox.y0 + segment.bbox.y1) / 2
            inside_table = (
                table_segment.bbox.x0 - 2 <= center_x <= table_segment.bbox.x1 + 8
                and table_segment.bbox.y0 <= center_y <= table_segment.bbox.y1
            )
            table_text = " ".join(
                cell.content.resolved_text or "" for cell in table.table.cells
                if cell.page_index in {None, segment.page_index}
            )
            punctuation_fragment = text in {",", ".", ";", ":"}
            duplicate = bool(re.search(rf"\b{re.escape(text)}\b", table_text, flags=re.I))
            if not inside_table or not (duplicate or punctuation_fragment):
                continue
            table.operations.append({
                "operation": "table_edge_duplicate_fragment_suppression",
                "source_block_id": block.id,
                "text": text,
                "decision": "auto_suppress",
                "evidence": (
                    ["inside_table_geometry", "punctuation_only_tiny_fragment"]
                    if punctuation_fragment
                    else ["inside_table_geometry", "text_already_in_table_cell"]
                ),
            })
            if replacements is not None:
                replacements[block.id] = table.id
            _remove_block(blocks, page_lookup, block.id, table.id)
            break


def _promote_local_subheadings(blocks: dict[str, Block]) -> None:
    """Promote short noun-phrase labels that introduce a local list.

    The rule is deliberately structural: a short, untterminated paragraph on
    the same page must be followed immediately by a list with a small vertical
    gap. It captures repeated legal/standards subheads without a document-
    specific vocabulary.
    """
    for parent in blocks.values():
        children = list(parent.children)
        for current_id, next_id in zip(children, children[1:], strict=False):
            current, following = blocks.get(current_id), blocks.get(next_id)
            if (
                not current or not following
                or current.type != BlockType.PARAGRAPH
                or following.type not in {BlockType.LIST, BlockType.LIST_ITEM}
                or not current.content or not current.content.resolved_text
                or not current.segments or not following.segments
            ):
                continue
            text = current.content.resolved_text.strip()
            words = text.split()
            left, right = current.segments[-1], following.segments[0]
            gap = right.bbox.y0 - left.bbox.y1
            if (
                not 1 <= len(words) <= 7
                or len(text) > 80
                or not text[:1].isupper()
                or re.search(r"[.!?:;]\s*$", text)
                or left.page_index != right.page_index
                or not -2 <= gap <= 30
                or re.search(r"\b(?:shall|must|may|should|is|are|was|were)\b", text, re.I)
            ):
                continue
            current.type = BlockType.HEADING
            current.heading_level = 4
            current.operations.append({
                "operation": "local_list_subheading_promotion",
                "decision": "auto_reclassify",
                "evidence": ["short_unterminated_noun_phrase", "immediate_same_page_list"],
            })


def _attach_figure_captions(
    blocks: dict[str, Block], pages: list[Page], replacements: dict[str, str] | None = None,
) -> None:
    page_lookup = {page.page_index: page for page in pages}
    for parent in list(blocks.values()):
        children = list(parent.children)
        for figure_id, caption_id in zip(children, children[1:], strict=False):
            figure, caption = blocks.get(figure_id), blocks.get(caption_id)
            if (
                not figure or not caption
                or figure.type != BlockType.FIGURE
                or figure.index
                or caption.type not in {BlockType.PARAGRAPH, BlockType.HEADING}
                or not caption.content or not caption.content.resolved_text
                or not figure.segments or not caption.segments
            ):
                continue
            text = caption.content.resolved_text.strip()
            figure_segment, caption_segment = figure.segments[-1], caption.segments[0]
            gap = caption_segment.bbox.y0 - figure_segment.bbox.y1
            if (
                not re.match(r"^(?:Figure|Fig\.)\s+[A-Z0-9][\w.-]*\b", text, re.I)
                or figure_segment.page_index != caption_segment.page_index
                or not -5 <= gap <= 70
            ):
                continue
            figure.index = text
            figure.operations.append({
                "operation": "figure_caption_attachment",
                "source_block_id": caption.id,
                "decision": "auto_attach",
                "evidence": ["explicit_figure_label", "same_page_adjacent_geometry"],
            })
            if replacements is not None:
                replacements[caption.id] = figure.id
            _remove_block(blocks, page_lookup, caption.id, figure.id)


def _replace_exact_text(block: Block, old: str, new: str) -> None:
    if not block.content:
        return
    for field in ("native_text", "ocr_text", "review_text", "resolved_text"):
        value = getattr(block.content, field)
        if value and value.strip() == old:
            setattr(block.content, field, new)


def _repair_inline_na_sections(blocks: dict[str, Block], pages: list[Page]) -> None:
    """Split the recurring inline ``Useful Resources N/A`` schema."""
    page_lookup = {page.page_index: page for page in pages}
    for block in list(blocks.values()):
        if not block.content or (block.content.resolved_text or "").strip() != "Useful Resources N/A":
            continue
        block.type = BlockType.HEADING
        block.heading_level = 3
        _replace_exact_text(block, "Useful Resources N/A", "Useful Resources")
        block.operations.append({
            "operation": "inline_heading_value_split",
            "schema": "useful_resources_na",
            "decision": "auto_repair",
            "evidence": ["recurring_useful_resources_heading", "explicit_na_value"],
        })
        na_id = f"{block.id}_na"
        na_block = block.model_copy(deep=True, update={
            "id": na_id,
            "type": BlockType.PARAGRAPH,
            "heading_level": None,
            "children": [],
            "operations": [{
                "operation": "inline_heading_value_split",
                "source_block_id": block.id,
                "semantic_role": "section_value",
            }],
        })
        _replace_exact_text(na_block, "Useful Resources", "N/A")
        na_block.segments = [
            segment.model_copy(update={"id": f"{segment.id}_na"})
            for segment in na_block.segments
        ]
        blocks[na_id] = na_block
        if block.parent_id and block.parent_id in blocks:
            siblings = blocks[block.parent_id].children
            position = siblings.index(block.id)
            siblings.insert(position + 1, na_id)
        for segment in block.segments:
            page = page_lookup.get(segment.page_index)
            if page and block.id in page.block_ids and na_id not in page.block_ids:
                position = page.block_ids.index(block.id)
                page.block_ids.insert(position + 1, na_id)

    # Layout backends occasionally promote the value alone to a heading.  It is
    # a paragraph when it directly follows the recurring section heading.
    for parent in blocks.values():
        for prior_id, current_id in zip(parent.children, parent.children[1:], strict=False):
            prior, current = blocks.get(prior_id), blocks.get(current_id)
            if not prior or not current or not prior.content or not current.content:
                continue
            if (
                prior.type == BlockType.HEADING
                and (prior.content.resolved_text or "").strip().casefold() == "useful resources"
                and current.type == BlockType.HEADING
                and (current.content.resolved_text or "").strip() == "N/A"
            ):
                current.type = BlockType.PARAGRAPH
                current.heading_level = None
                current.operations.append({
                    "operation": "heading_value_reclassification",
                    "schema": "useful_resources_na",
                    "decision": "auto_repair",
                })


def _promote_bottom_footnotes(
    blocks: dict[str, Block], pages: list[Page], replacements: dict[str, str] | None = None,
) -> None:
    """Classify and assemble numbered page-bottom notes before prose merging.

    Promotion happens before the general paragraph assembler so a footnote can
    never absorb the first body paragraph on the next page.  A note is accepted
    either by strong bottom-margin geometry or by an increasing run of at least
    two numbered notes in the lower part of the page.
    """
    page_lookup = {page.page_index: page for page in pages}
    numbered_by_page: dict[int, list[tuple[int, Block]]] = {}
    for block in blocks.values():
        if (
            block.type not in {BlockType.PARAGRAPH, BlockType.LIST}
            or not block.content
            or not block.content.resolved_text
            or not block.segments
        ):
            continue
        match = re.match(r"^([1-9]\d*)\s+\S", block.content.resolved_text.strip())
        first = block.segments[0]
        page = page_lookup.get(first.page_index)
        if match and page and first.bbox.y0 >= page.height * 0.69:
            numbered_by_page.setdefault(first.page_index, []).append((int(match.group(1)), block))

    promoted: set[str] = set()
    for page_index, values in numbered_by_page.items():
        values.sort(key=lambda item: item[1].segments[0].bbox.y0)
        markers = [marker for marker, _ in values]
        increasing_run = len(markers) >= 2 and all(
            right > left for left, right in zip(markers, markers[1:], strict=False)
        )
        page = page_lookup[page_index]
        for _, block in values:
            strong_bottom = block.segments[0].bbox.y0 >= page.height * 0.84
            if not strong_bottom and not increasing_run:
                continue
            block.type = BlockType.FOOTNOTE
            promoted.add(block.id)
            block.operations.append({
                "operation": "bottom_margin_footnote_promotion",
                "decision": "auto_repair",
                "evidence": (
                    ["numbered_note_prefix", "bottom_margin_geometry"]
                    if strong_bottom
                    else ["numbered_note_prefix", "increasing_bottom_note_sequence"]
                ),
            })

    # Attach wrapped physical lines on the same page.  A new numbered note is a
    # hard boundary; cross-page attachment is intentionally forbidden.
    for page_index, page in page_lookup.items():
        candidates = [
            block for block in blocks.values()
            if block.type in {BlockType.PARAGRAPH, BlockType.LIST, BlockType.FOOTNOTE}
            and block.content and block.content.resolved_text and block.segments
            and block.segments[0].page_index == page_index
            and block.segments[0].bbox.y0 >= page.height * 0.69
        ]
        candidates.sort(key=lambda block: (block.segments[0].bbox.y0, block.segments[0].bbox.x0))
        index = 0
        while index < len(candidates) - 1:
            left, right = candidates[index], candidates[index + 1]
            if left.type != BlockType.FOOTNOTE or right.type == BlockType.FOOTNOTE:
                index += 1
                continue
            left_segment, right_segment = left.segments[-1], right.segments[0]
            gap = right_segment.bbox.y0 - left_segment.bbox.y1
            right_text = right.content.resolved_text.strip()
            if (
                not -2.0 <= gap <= 14.0
                or abs(left_segment.bbox.x0 - right_segment.bbox.x0) > 32.0
                or re.match(r"^[1-9]\d*\s+\S", right_text)
            ):
                index += 1
                continue
            left_text = left.content.resolved_text or ""
            url_note = bool(re.match(r"^\d+\s+https?://", left_text.strip(), flags=re.I))
            for field in ("native_text", "ocr_text", "review_text", "resolved_text"):
                left_value = getattr(left.content, field)
                right_value = getattr(right.content, field)
                if not right_value:
                    continue
                if url_note and left_value:
                    setattr(left.content, field, left_value.rstrip() + re.sub(r"\s+", "", right_value))
                else:
                    setattr(left.content, field, _join_text(left_value, right_value))
            left.segments.extend(right.segments)
            left.operations.append({
                "operation": "footnote_line_attachment",
                "source_fragment_ids": [left.id, right.id],
                "decision": "auto_merge",
                "evidence": ["same_page_bottom_geometry", "no_new_note_marker"],
            })
            if replacements is not None:
                replacements[right.id] = left.id
            _remove_block(blocks, page_lookup, right.id, left.id)
            candidates.pop(index + 1)


def assemble_document(
    blocks: dict[str, Block], pages: list[Page], settings: AssemblySettings,
    replacements: dict[str, str] | None = None,
) -> list[ReviewItem]:
    _suppress_table_edge_duplicate_fragments(blocks, pages, replacements)
    _promote_bottom_footnotes(blocks, pages, replacements)
    reviews = attach_profile_table_continuations(blocks, pages, replacements)
    reviews.extend(assemble_paragraphs(blocks, pages, settings, replacements))
    reviews.extend(assemble_tables(blocks, pages, settings, replacements))
    _repair_inline_na_sections(blocks, pages)
    _promote_local_subheadings(blocks)
    _attach_figure_captions(blocks, pages, replacements)
    repair_list_hierarchy(blocks)
    repair_heading_hierarchy(blocks)
    repair_sibling_orders(blocks)
    for page in pages:
        page.block_ids = list(dict.fromkeys(page.block_ids))
    return [
        item for item in reviews
        if item.target_id in blocks or item.target_id.startswith("page:")
    ]
