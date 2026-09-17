from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .config import AppConfig
from .export import (
    export_html,
    export_jsonl,
    export_markdown,
    export_overlays,
    export_rag_chunks,
    export_xml,
)
from .models import ArtifactReference, Document, DocumentStatus, ReviewItem
from .models import BlockType
from .regulatory_ir import export_regulatory_ir
from .validate import build_quality_report


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact(path: Path, media_type: str) -> ArtifactReference:
    return ArtifactReference(path=str(path), media_type=media_type, sha256=_sha256(path))


def write_derived_artifacts(document: Document, output_dir: str | Path, config: AppConfig) -> None:
    output = Path(output_dir)
    artifacts: dict[str, ArtifactReference] = {}
    if config.outputs.markdown:
        path = export_markdown(document, output / "document.md")
        artifacts["markdown"] = _artifact(path, "text/markdown")
    if config.outputs.html:
        path = export_html(document, output / "document.html")
        artifacts["html"] = _artifact(path, "text/html")
    if config.outputs.xml:
        path = export_xml(document, output / "document.xml")
        artifacts["xml"] = _artifact(path, "application/xml")
    if config.outputs.jsonl:
        path = export_jsonl(document, output / "blocks.jsonl")
        artifacts["jsonl"] = _artifact(path, "application/x-ndjson")
    if config.outputs.rag_chunks:
        path = export_rag_chunks(document, output / "rag-chunks.json")
        artifacts["rag_chunks"] = _artifact(path, "application/json")
    if config.outputs.overlay:
        path = export_overlays(document, output / "overlays")
        artifacts["overlay_manifest"] = _artifact(path, "application/json")
    if config.regulatory_ir.enabled:
        path, ir = export_regulatory_ir(document, output / "regulatory-ir.json")
        artifacts["regulatory_ir"] = _artifact(path, "application/json")
        for statement_id in ir.review_required:
            review_id = f"review_regulatory_ir_{statement_id}"
            if not any(item.id == review_id for item in document.review_items):
                document.review_items.append(ReviewItem(
                    id=review_id,
                    target_id=f"regulatory_ir:{statement_id}",
                    reason="regulatory_fact_depends_on_review_required_source",
                    severity="critical",
                    candidate_action="review_source_block_before_rdf_mapping",
                ))
        for requirement_id in ir.requirement_review_required:
            review_id = (
                "review_canonical_requirement_"
                f"{requirement_id.replace('.', '_')}"
            )
            if not any(item.id == review_id for item in document.review_items):
                document.review_items.append(ReviewItem(
                    id=review_id,
                    target_id=f"requirement:{requirement_id}",
                    reason="canonical_requirement_requires_review_or_abstained",
                    severity="critical",
                    candidate_action="inspect_requirement_source_regions_and_validation_flags",
                ))
        for requirement_id in ir.missing_requirement_ids:
            review_id = f"review_missing_regulatory_requirement_{requirement_id.replace('.', '_')}"
            if not any(item.id == review_id for item in document.review_items):
                document.review_items.append(ReviewItem(
                    id=review_id,
                    target_id=f"requirement:{requirement_id}",
                    reason="formal_requirement_missing_from_regulatory_ir",
                    severity="critical",
                    candidate_action="inspect_requirement_table_and_ir_extraction",
                ))
        if config.ontology.enabled:
            # Ontology dependencies are optional and comparatively heavy. Keep
            # them behind the delivery boundary so importing the extraction
            # orchestrator does not initialize pySHACL.
            from .ontology import export_ontology

            ttl, shapes, report, result = export_ontology(
                ir, output / "ontology", config.ontology.namespace
            )
            artifacts["rdf"] = _artifact(ttl, "text/turtle")
            artifacts["shacl_shapes"] = _artifact(shapes, "text/turtle")
            artifacts["shacl_report"] = _artifact(report, "application/json")
            if not result.conforms:
                for index, focus in enumerate(result.violating_focus_nodes or ["unknown"]):
                    review_id = f"review_shacl_{index:04d}"
                    if not any(item.id == review_id for item in document.review_items):
                        document.review_items.append(ReviewItem(
                            id=review_id,
                            target_id=f"ontology:{focus}",
                            reason="shacl_violation",
                            severity="critical",
                            candidate_action="repair_regulatory_ir_or_source_review",
                        ))
    footnote_ids = {
        block.id
        for block in document.blocks.values()
        if block.type == BlockType.FOOTNOTE
    }
    definition_markers = {
        match.group(1)
        for block in document.blocks.values()
        if block.type == BlockType.FOOTNOTE and block.content and block.content.resolved_text
        if (match := re.match(r"^\s*(\d{1,2})\s+", block.content.resolved_text))
    }
    referenced_markers: set[str] = set()
    for block in document.blocks.values():
        texts: list[str] = []
        if block.content and block.content.resolved_text:
            texts.append(block.content.resolved_text)
        if block.table:
            texts.extend(cell.content.resolved_text or "" for cell in block.table.cells)
        referenced_markers.update(
            marker
            for value in texts
            for marker in re.findall(r"\[\^(\d{1,2})\]", value)
        )
    for marker in sorted(referenced_markers - definition_markers, key=int):
        review_id = f"review_missing_footnote_definition_{marker}"
        if not any(item.id == review_id for item in document.review_items):
            document.review_items.append(ReviewItem(
                id=review_id,
                target_id=f"footnote:{marker}",
                reason="referenced_footnote_definition_missing",
                severity="critical",
                candidate_action="inspect_page_bottom_note_classification_and_assembly",
            ))
    footnote_link_counts = {target_id: 0 for target_id in footnote_ids}
    for block in document.blocks.values():
        for link in block.content_links:
            if link.relation == "footnote_reference" and link.target_id in footnote_link_counts:
                footnote_link_counts[link.target_id] += 1
    enforce_footnote_cardinality = any(footnote_link_counts.values())
    for target_id, count in footnote_link_counts.items():
        if not enforce_footnote_cardinality:
            break
        if count == 1:
            continue
        review_id = f"review_footnote_cardinality_{target_id}"
        if not any(item.id == review_id for item in document.review_items):
            document.review_items.append(ReviewItem(
                id=review_id,
                target_id=target_id,
                reason=f"footnote_reference_count:{count}",
                severity="critical",
                candidate_action="inspect_superscript_anchor_and_footnote_definition",
                evidence_segment_ids=[
                    segment.id for segment in document.blocks[target_id].segments
                ],
            ))
    for marginal_type in (BlockType.HEADER, BlockType.FOOTER):
        values = [
            (block.id, " ".join((block.content.resolved_text or "").split()))
            for block in document.blocks.values()
            if block.type == marginal_type and block.content and block.content.resolved_text
        ]
        normalized = [
            (block_id, re.sub(r"\b\d+\b", "{n}", value.casefold()))
            for block_id, value in values
        ]
        if not normalized:
            continue
        counts: dict[str, int] = {}
        for _, value in normalized:
            counts[value] = counts.get(value, 0) + 1
        dominant = max(counts, key=counts.get)
        for block_id, value in normalized:
            if value != dominant and dominant in value:
                review_id = f"review_marginal_contamination_{block_id}"
                if not any(item.id == review_id for item in document.review_items):
                    document.review_items.append(ReviewItem(
                        id=review_id,
                        target_id=block_id,
                        reason="repeating_marginal_contains_non_template_text",
                        severity="critical",
                        candidate_action="split_marginal_template_from_body_content",
                        evidence_segment_ids=[
                            segment.id for segment in document.blocks[block_id].segments
                        ],
                    ))
    document.review_queue = list(dict.fromkeys(
        item.target_id for item in document.review_items if item.status == "pending"
    ))
    document.quality.status = (
        DocumentStatus.REVIEW_REQUIRED if document.review_queue else DocumentStatus.ACCEPTED
    )
    report_path = output / "quality-report.json"
    report_path.write_text(
        json.dumps(build_quality_report(document), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    artifacts["quality_report"] = _artifact(report_path, "application/json")
    document.artifacts.update(artifacts)
