from __future__ import annotations

from difflib import SequenceMatcher
from collections import Counter
import re

from ..models import Block, BlockType, BoundingBox, Resolution, ResolutionStatus, ReviewItem
from ..types import NativeObject, NativePage


_CRITICAL_TOKEN = re.compile(
    r"(?:≤|≥|<|>|=|\b\d+(?:[.,]\d+)*(?:%|°[CF]|mg|kg|g|ml|l|days?|years?)?\b|"
    r"\b(?:shall|must|may|not|unless|except)\b)",
    flags=re.I,
)
_HYPHENATED_TOKEN = re.compile(r"\b[A-Za-z]{2,}-[A-Za-z]{2,}\b")


def _words_for_box(words: list[NativeObject], box: BoundingBox) -> list[NativeObject]:
    selected: list[NativeObject] = []
    for word in words:
        x0, y0, x1, y1 = word.bbox_points
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if box.x0 - 1 <= cx <= box.x1 + 1 and box.y0 - 1 <= cy <= box.y1 + 1:
            selected.append(word)
    return selected


def _text_for_box(words: list[NativeObject], box: BoundingBox) -> str:
    return " ".join(word.text.strip() for word in _words_for_box(words, box) if word.text.strip())


def _context_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.casefold())


def _critical_signature(text: str) -> list[str]:
    return [re.sub(r"\s+", "", value.casefold()) for value in _CRITICAL_TOKEN.findall(text)]


def _safe_repairs(primary: str, secondary: str) -> tuple[str, list[dict[str, str]]]:
    repaired = primary
    operations: list[dict[str, str]] = []
    for match in list(re.finditer(r"(?<!\d)([<>≤≥=]?\s*\d)\s+(\d+(?:[.,]\d+)?%)", repaired)):
        old = match.group(0)
        candidate = re.sub(r"\s+", "", old)
        if candidate in re.sub(r"\s+", "", secondary):
            repaired = repaired.replace(old, candidate, 1)
            operations.append({"kind": "split_numeric_token", "from": old, "to": candidate})

    secondary_compounds = list(_HYPHENATED_TOKEN.findall(secondary))
    secondary_compounds.extend(
        f"{match.group(1)}-{match.group(2)}"
        for match in re.finditer(r"\b([A-Za-z]{2,})-\s+([A-Za-z]{2,})\b", secondary)
    )
    for token in dict.fromkeys(secondary_compounds):
        left, right = token.split("-", 1)
        variants = (
            re.compile(rf"\b{re.escape(left)}{re.escape(right)}\b", flags=re.I),
            re.compile(rf"\b{re.escape(left)}\s*-\s+{re.escape(right)}\b", flags=re.I),
            re.compile(rf"\b{re.escape(left)}\s+-\s*{re.escape(right)}\b", flags=re.I),
        )
        for variant in variants:
            match = variant.search(repaired)
            if match:
                old = match.group(0)
                repaired = variant.sub(token, repaired, count=1)
                operations.append({"kind": "compound_hyphen", "from": old, "to": token})
                break
    return repaired, operations


def apply_secondary_native_gate(
    blocks: dict[str, Block],
    secondary_pages: list[NativePage],
    *,
    auto_repair: bool = True,
    min_context_similarity: float = 0.90,
) -> list[ReviewItem]:
    """Cross-check critical text with an independent local native extractor.

    Automatic changes require the exact replacement token in evidence from the
    same canonical geometry. Statistical/template evidence never creates text.
    """
    page_words = {page.page_index: page.words for page in secondary_pages}
    reviews: list[ReviewItem] = []

    def inspect_text(block: Block, content, secondary: str, target: str) -> None:
        primary = content.resolved_text or content.native_text or ""
        if not primary or not secondary:
            return
        repaired, repairs = _safe_repairs(primary, secondary) if auto_repair else (primary, [])
        if repairs and repaired != primary:
            content.resolved_text = repaired
            content.resolution = Resolution(
                selected_source="native",
                reason="secondary_native_exact_token_corroboration",
                confidence=1.0,
            )
            block.operations.append({
                "operation": "secondary_native_exact_token_repair",
                "target": target,
                "backend": "pdftotext",
                "repairs": repairs,
                "decision": "auto_repair",
                "evidence": ["same_bbox", "independent_native_token"],
            })
            primary = repaired

        left_key, right_key = _context_key(primary), _context_key(secondary)
        similarity = SequenceMatcher(None, left_key, right_key).ratio() if left_key and right_key else 0.0
        primary_signature = _critical_signature(primary)
        secondary_signature = _critical_signature(secondary)
        if (
            similarity >= min_context_similarity
            and primary_signature
            and secondary_signature
            and Counter(primary_signature) != Counter(secondary_signature)
        ):
            # Preserve both candidates in evidence, never expose an unresolved
            # critical value as the authoritative resolved text.
            content.resolved_text = None
            content.resolution_status = ResolutionStatus.AMBIGUOUS
            content.requires_human_review = True
            content.resolution = Resolution(
                selected_source='none', reason='secondary_native_critical_mismatch', confidence=0,
            )
            block.quality.requires_review = True
            if "secondary_native_critical_mismatch" not in block.quality.issues:
                block.quality.issues.append("secondary_native_critical_mismatch")
            block.operations.append({
                "operation": "secondary_native_critical_validation",
                "target": target,
                "backend": "pdftotext",
                "decision": "review_required",
                "context_similarity": round(similarity, 4),
                "primary_signature": primary_signature,
                "secondary_signature": secondary_signature,
                "primary_candidate": primary,
                "secondary_candidate": secondary,
            })
            if not any(item.target_id == block.id and item.reason == "secondary_native_critical_mismatch" for item in reviews):
                reviews.append(ReviewItem(
                    id=f"review_secondary_native_{block.id}",
                    target_id=block.id,
                    reason="secondary_native_critical_mismatch",
                    severity="critical",
                    candidate_action="inspect_independent_native_evidence",
                    evidence_segment_ids=[segment.id for segment in block.segments],
                ))

    for block in blocks.values():
        if block.type in {BlockType.DOCUMENT, BlockType.SECTION, BlockType.HEADER, BlockType.FOOTER}:
            continue
        if block.content and block.segments:
            secondary = " ".join(
                _text_for_box(page_words.get(segment.page_index, []), segment.bbox)
                for segment in block.segments
                if segment.page_index in page_words
            ).strip()
            inspect_text(block, block.content, secondary, "block")
        if block.table:
            for cell in block.table.cells:
                if cell.page_index is not None and cell.page_index in page_words:
                    secondary = _text_for_box(page_words[cell.page_index], cell.bbox)
                    inspect_text(block, cell.content, secondary, f"cell:{cell.id}")
    return reviews
