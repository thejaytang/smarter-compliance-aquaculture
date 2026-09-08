from __future__ import annotations

import json
import os
import platform
import re
import resource
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import version as package_version
from pathlib import Path
from typing import Callable, Iterable

from ..config import AppConfig
from ..assemble import assemble_document, enrich_content_links, populate_note_spans
from ..ingest import (
    NativeExtractor,
    PDFRenderer,
    extract_secondary_native,
    inspect_pdf_security,
    run_preflight,
)
from ..layout import (
    annotate_list_markers,
    apply_native_visual_regions,
    apply_repeating_marginals,
    create_layout_detector,
    detect_repeating_marginals,
    native_text_for_region,
)
from ..models import (
    Block,
    BlockQuality,
    BlockType,
    BoundingBox,
    Conflict,
    ContentLink,
    Document,
    DocumentQuality,
    DocumentStatus,
    DerivedContent,
    ModelRecord,
    ProcessingMetadata,
    ProcessingStatus,
    Resolution,
    ResolutionStatus,
    ReviewItem,
    Segment,
    TextContent,
)
from ..ocr import create_ocr_backend
from ..parsers import (
    EquationParser,
    TableParser,
    build_text_content,
    enrich_definition_formula_text,
    enrich_mixed_formula_text,
    parse_code,
    parse_figure,
    recover_visual_blank_text,
)
from ..profiling import (
    DocumentProfile,
    apply_profile_repairs,
    learn_document_profile,
    validate_profile_consistency,
)
from ..routing import TextLayerDecision, assess_text_layer, native_analysis_page
from ..types import LayoutRegion, OCRPage, RenderedPage
from ..reconcile import (
    PrecisionReviewer,
    apply_abstention_policy,
    build_evidence_spans,
    conflicts_from_spans,
)
from ..domains.requirements import (
    FamilyProfileStatus,
    NativeRequirementAssembler,
    bind_requirement_hierarchy,
    canonicalize_native_requirement,
    link_requirement_footnotes,
    learn_requirement_hierarchy_profile,
    learn_requirement_template_profile,
)
from ..validate import (
    apply_secondary_native_gate,
    build_page_completeness_report,
)
from ..extraction.regions import (
    figure_index_from_source_text as _figure_index_from_source_text,
    normalized_block_type as _block_type,
    region_bbox as _bbox,
    region_ocr_text as _ocr_text,
)
from ..verification.conflict_review import (
    ensure_critical_conflicts_reviewable as _ensure_critical_conflicts_reviewable,
)
from ..verification.evidence_routing import route_evidence_spans
from .context import RunContext
from .finalization import FinalizationInput, FinalizationStage
from .runtime import model_cache_hash as _model_cache_hash


PIPELINE_VERSION = "0.5.0"


def _load_cached_ocr(path: Path, page_index: int) -> OCRPage | None:
    if not path.is_file():
        return None
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
        from ..types import OCRWord, PixelBox

        words = [OCRWord(
            id=str(row["id"]), text=str(row["text"]),
            confidence=float(row.get("confidence", 0)),
            bbox=PixelBox(*map(int, row["bbox"])),
            block_num=int(row.get("block_num", 0)),
            paragraph_num=int(row.get("paragraph_num", 0)),
            line_num=int(row.get("line_num", 0)),
        ) for row in rows]
        return OCRPage(
            page_index=page_index, words=words, backend="cached-ocr",
            version=PIPELINE_VERSION, fallback_reason="resumed_from_page_cache", raw_ref=path,
        )
    except Exception:
        return None


class ExtractionPipeline:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._ocr_backend = None
        self._layout_detector = None
        self._table_parser = None
        self._equation_parser = None
        self._precision_reviewer = None

    @classmethod
    def from_config_file(cls, path: str | Path) -> "ExtractionPipeline":
        return cls(AppConfig.from_yaml(path))

    def run(
        self,
        pdf_path: str | Path,
        output_dir: str | Path,
        *,
        status_callback: Callable[[str, dict[str, object] | None], None] | None = None,
        resume: bool = False,
        page_indices: set[int] | None = None,
    ) -> Document:
        context = RunContext.create(
            pdf_path,
            output_dir,
            self.config,
            resume=resume,
            page_indices=page_indices,
            status_callback=status_callback,
        )
        cached = context.load_resumable_document()
        if cached is not None:
            return cached
        source_path = context.source_path
        pages_dir = context.paths.pages
        crops_dir = context.paths.crops
        figures_dir = context.paths.figures
        raw_dir = context.paths.raw
        status = context.status
        config_hash = context.config_hash

        started = datetime.now(timezone.utc).isoformat()
        timings = context.timings
        overall_started = time.perf_counter()
        status("preflight")
        phase_started = time.perf_counter()
        security_inspection = inspect_pdf_security(source_path, self.config.security)
        timings["security_preflight"] = (time.perf_counter() - phase_started) * 1000
        status("parsing")
        phase_started = time.perf_counter()
        native_result = NativeExtractor(self.config.native_extraction.backend).extract(source_path)
        if page_indices is None:
            selected_page_indices = set(range(len(native_result.pages)))
            partial_selection = False
        else:
            selected_page_indices = set(page_indices)
            partial_selection = True
            invalid = sorted(
                index for index in selected_page_indices
                if index < 0 or index >= len(native_result.pages)
            )
            if invalid:
                raise IndexError(f"page selection outside source document: {invalid}")
        selected_native_pages = [
            page for page in native_result.pages if page.page_index in selected_page_indices
        ]
        secondary_native_result = (
            extract_secondary_native(
                source_path,
                selected_page_indices,
                timeout_seconds=min(300, self.config.security.processing_timeout_seconds),
            )
            if self.config.secondary_native.enabled
            else None
        )
        text_route_decisions: dict[int, TextLayerDecision] = {}
        for native_page in selected_native_pages:
            if self.config.text_routing.enabled:
                decision = assess_text_layer(native_page, self.config.text_routing)
            else:
                decision = TextLayerDecision(
                    page_index=native_page.page_index,
                    route="ocr",
                    reason="native_text_routing_disabled",
                    word_count=len(native_page.words),
                    character_count=sum(len(word.text) for word in native_page.words),
                    suspicious_character_ratio=0.0,
                    valid_bbox_ratio=0.0,
                    bitmap_count=len(native_page.bitmap_resources),
                    confidence=1.0,
                )
            text_route_decisions[native_page.page_index] = decision
        routing_path = raw_dir / "text-routing.json"
        routing_path.write_text(
            json.dumps(
                [asdict(text_route_decisions[index]) for index in sorted(text_route_decisions)],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        marginal_annotations = detect_repeating_marginals(native_result.pages)
        document_profile = (
            learn_document_profile(
                native_result.pages,
                marginal_page_count=len(marginal_annotations),
            )
            if self.config.profiling.enabled
            else DocumentProfile(page_count=len(native_result.pages))
        )
        profile_path = raw_dir / "document-profile.json"
        profile_path.write_text(document_profile.model_dump_json(indent=2), encoding="utf-8")
        requirement_assembler = NativeRequirementAssembler()
        requirement_profile = (
            learn_requirement_template_profile(
                native_result.pages,
                assembler=requirement_assembler,
            )
            if self.config.profiling.enabled
            else None
        )
        requirement_hierarchy_profile = (
            learn_requirement_hierarchy_profile(native_result.pages)
            if self.config.profiling.enabled
            else None
        )
        requirement_profile_path = raw_dir / "requirement-template-profile.json"
        requirement_hierarchy_profile_path = (
            raw_dir / "requirement-hierarchy-profile.json"
        )
        if requirement_profile is not None:
            requirement_profile_path.write_text(
                requirement_profile.to_json(indent=2), encoding="utf-8"
            )
            family_hints = requirement_profile.family_hints(
                accepted_only=False,
            )
        else:
            family_hints = {}
        if requirement_hierarchy_profile is not None:
            requirement_hierarchy_profile_path.write_text(
                requirement_hierarchy_profile.to_json(indent=2),
                encoding="utf-8",
            )
        native_requirement_candidates = requirement_assembler.assemble(
            native_result.pages,
            selected_indices=selected_page_indices,
            family=(family_hints or None),
        )
        native_requirement_candidates = link_requirement_footnotes(
            native_requirement_candidates,
            native_result.pages,
        )
        renderer = PDFRenderer(self.config.pipeline.render_dpi)
        rendered_pages = renderer.render(
            source_path,
            pages_dir,
            reuse_existing=resume and self.config.runtime.cache_enabled,
            page_indices=selected_page_indices,
        )
        preflight = run_preflight(
            source_path,
            rendered_pages,
            selected_native_pages,
            security_inspection,
            expected_page_indices=(selected_page_indices if partial_selection else None),
        )
        timings["render_and_native_extraction"] = (time.perf_counter() - phase_started) * 1000
        native_page_refs: list[str] = []
        for native_page in selected_native_pages:
            native_ref = raw_dir / f"native-page-{native_page.page_index + 1:04d}.json"
            native_ref.write_text(
                json.dumps(asdict(native_page), ensure_ascii=False, indent=2), encoding="utf-8"
            )
            native_page_refs.append(str(native_ref))
        native_manifest_path = raw_dir / "native-manifest.json"
        native_manifest_path.write_text(
            json.dumps(
                {
                    "backend": native_result.backend,
                    "version": native_result.version,
                    "fallback_reason": native_result.fallback_reason,
                    "page_refs": native_page_refs,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        secondary_native_refs: list[str] = []
        if secondary_native_result:
            for secondary_page in secondary_native_result.pages:
                secondary_ref = raw_dir / f"secondary-native-page-{secondary_page.page_index + 1:04d}.json"
                secondary_ref.write_text(
                    json.dumps(asdict(secondary_page), ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                secondary_native_refs.append(str(secondary_ref))
            (raw_dir / "secondary-native-manifest.json").write_text(
                json.dumps({
                    "backend": secondary_native_result.backend,
                    "version": secondary_native_result.version,
                    "fallback_reason": secondary_native_result.fallback_reason,
                    "page_refs": secondary_native_refs,
                }, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        if self._ocr_backend is None:
            self._ocr_backend = create_ocr_backend(self.config.ocr)
        if self._layout_detector is None:
            self._layout_detector = create_layout_detector(self.config.layout, self.config.tables)
        if self._table_parser is None:
            self._table_parser = TableParser(self.config.tables, self._ocr_backend)
        if self._precision_reviewer is None:
            self._precision_reviewer = PrecisionReviewer(
                self.config.precision_review, self._ocr_backend
            )
        ocr_backend = self._ocr_backend
        layout_detector = self._layout_detector
        table_parser = self._table_parser
        precision_reviewer = self._precision_reviewer
        precision_reviewer.last_backend = self.config.precision_review.model_name
        precision_reviewer.last_fallback_reason = None

        processing = ProcessingMetadata(
            started_at=started,
            pipeline_version=PIPELINE_VERSION,
            config_hash=config_hash,
            status=ProcessingStatus.PARSING,
            pipeline_commit=context.source_tree_fingerprint,
            renderer_name="pypdfium2",
            renderer_version=package_version("pypdfium2"),
            render_dpi=self.config.pipeline.render_dpi,
            environment={
                "python": platform.python_version(),
                "platform": platform.platform(),
                "process_id": str(os.getpid()),
            },
            hardware={
                "machine": platform.machine(),
                "processor": platform.processor() or "unknown",
                "cpu_count": str(os.cpu_count() or 1),
            },
            random_seed=self.config.runtime.random_seed,
            deterministic=self.config.runtime.deterministic,
            processed_page_indices=sorted(selected_page_indices),
            data_routing={
                "external_models_enabled": self.config.security.external_models_enabled,
                "document_content_sent_externally": False,
                "document_text_in_logs": not self.config.security.redact_document_text_in_logs,
                "pdf_content_trust_level": "untrusted_data_only",
            },
            models=[
                ModelRecord(
                    role="native_extraction",
                    name=native_result.backend,
                    version=native_result.version,
                    backend=native_result.backend,
                    fallback_reason=native_result.fallback_reason,
                )
            ],
        )
        processing.models.append(ModelRecord(
            role="document_profile",
            name=document_profile.backend,
            version=document_profile.version,
            backend="native-feature-learning",
            fallback_reason=None,
        ))
        if requirement_profile is not None:
            processing.models.append(ModelRecord(
                role="requirement_template_profile",
                name=requirement_profile.backend,
                version=requirement_profile.version,
                backend="native-feature-learning",
                fallback_reason=None,
            ))
        if secondary_native_result:
            processing.models.append(ModelRecord(
                role="secondary_native_validation",
                name=secondary_native_result.backend,
                version=secondary_native_result.version,
                backend=secondary_native_result.backend,
                fallback_reason=secondary_native_result.fallback_reason,
            ))
        primary_table_backend = (
            table_parser.recognition_backend or table_parser.structure_backend
        )
        processing.models.append(
            ModelRecord(
                role="table_structure",
                name=(
                    primary_table_backend.name
                    if primary_table_backend else "opencv-grid"
                ),
                version=(
                    primary_table_backend.version
                    if primary_table_backend else None
                ),
                backend=(
                    self.config.tables.paddle_engine
                    if primary_table_backend else "opencv"
                ),
                fallback_reason=table_parser.fallback_reason,
                weights_hash=_model_cache_hash(
                    primary_table_backend.name if primary_table_backend else "opencv-grid"
                ),
            )
        )

        blocks: dict[str, Block] = {}
        conflicts: list[Conflict] = []
        review_queue: list[str] = []
        unassigned_native = 0
        document_root = Block(id="document_000", type=BlockType.DOCUMENT, order_in_parent=0)
        blocks[document_root.id] = document_root
        root_section = Block(
            id="section_000",
            type=BlockType.SECTION,
            parent_id=document_root.id,
            order_in_parent=0,
        )
        blocks[root_section.id] = root_section
        document_root.children.append(root_section.id)
        current_section_id = root_section.id
        section_number = 0
        page_ocr_results: list[OCRPage] = []
        page_completeness = []
        layout_regions_by_page: dict[int, list[LayoutRegion]] = {}
        layout_backend_recorded = False
        recorded_text_backends: set[str] = set()

        parallel_analysis: dict[int, tuple[OCRPage, object, object]] = {}
        if self.config.runtime.page_workers > 1 and len(rendered_pages) > 1:
            worker_state = threading.local()

            def analyze(item: tuple[RenderedPage, object, object]):
                rendered, native, page_model = item
                # Each worker owns one model pair and reuses it across pages. This
                # avoids per-page model reloads without sharing non-thread-safe models.
                if not hasattr(worker_state, "ocr"):
                    worker_state.ocr = create_ocr_backend(self.config.ocr)
                    worker_state.layout = create_layout_detector(
                        self.config.layout, self.config.tables
                    )
                worker_ocr = worker_state.ocr
                worker_layout = worker_state.layout
                cache_path = raw_dir / f"ocr-page-{rendered.page_index + 1:04d}.json"
                route = text_route_decisions[rendered.page_index]
                if route.route == "ocr":
                    ocr_result = (
                        _load_cached_ocr(cache_path, rendered.page_index)
                        if resume and self.config.runtime.cache_enabled else None
                    ) or worker_ocr.recognize_page(rendered, raw_dir)
                else:
                    ocr_result = native_analysis_page(native, rendered, raw_dir, route)
                layout_result = worker_layout.detect(rendered, ocr_result)
                layout_result.regions = apply_native_visual_regions(
                    layout_result.regions, rendered, native, ocr_result
                )
                layout_result.regions = apply_repeating_marginals(
                    layout_result.regions, rendered, ocr_result,
                    marginal_annotations.get(rendered.page_index, []),
                )
                layout_result.regions = annotate_list_markers(
                    layout_result.regions, rendered, native.words
                )
                layout_result.regions = apply_profile_repairs(
                    layout_result.regions,
                    rendered,
                    ocr_result,
                    native,
                    document_profile,
                    min_support=self.config.profiling.min_requirement_template_support,
                    min_confidence=self.config.profiling.template_repair_confidence,
                )
                completeness = build_page_completeness_report(
                    rendered, native, ocr_result, layout_result.regions, self.config.completeness
                )
                return rendered.page_index, ocr_result, layout_result, completeness

            with ThreadPoolExecutor(max_workers=self.config.runtime.page_workers) as executor:
                for page_index, ocr_result, layout_result, completeness in executor.map(
                    analyze, zip(rendered_pages, selected_native_pages, preflight.pages, strict=True)
                ):
                    parallel_analysis[page_index] = (ocr_result, layout_result, completeness)

        for page, native_page, page_model in zip(
            rendered_pages, selected_native_pages, preflight.pages, strict=True
        ):
            if time.perf_counter() - overall_started > self.config.security.processing_timeout_seconds:
                raise TimeoutError("processing exceeded configured timeout")
            peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            peak_mb = peak / (1024 * 1024) if platform.system() == "Darwin" else peak / 1024
            if peak_mb > self.config.security.max_memory_mb:
                raise MemoryError("processing exceeded configured memory limit")
            if page.page_index in parallel_analysis:
                ocr_page, layout_result, completeness_report = parallel_analysis[page.page_index]
            else:
                cache_path = raw_dir / f"ocr-page-{page.page_index + 1:04d}.json"
                route = text_route_decisions[page.page_index]
                if route.route == "ocr":
                    ocr_page = (
                        _load_cached_ocr(cache_path, page.page_index)
                        if resume and self.config.runtime.cache_enabled else None
                    ) or ocr_backend.recognize_page(page, raw_dir)
                else:
                    ocr_page = native_analysis_page(native_page, page, raw_dir, route)
                layout_result = layout_detector.detect(page, ocr_page)
                layout_result.regions = apply_native_visual_regions(
                    layout_result.regions, page, native_page, ocr_page
                )
                layout_result.regions = apply_repeating_marginals(
                    layout_result.regions, page, ocr_page,
                    marginal_annotations.get(page.page_index, []),
                )
                layout_result.regions = annotate_list_markers(
                    layout_result.regions, page, native_page.words
                )
                layout_result.regions = apply_profile_repairs(
                    layout_result.regions,
                    page,
                    ocr_page,
                    native_page,
                    document_profile,
                    min_support=self.config.profiling.min_requirement_template_support,
                    min_confidence=self.config.profiling.template_repair_confidence,
                )
                completeness_report = build_page_completeness_report(
                    page, native_page, ocr_page, layout_result.regions, self.config.completeness
                )
            page_ocr_results.append(ocr_page)
            layout_regions_by_page[page.page_index] = layout_result.regions
            page_completeness.append(completeness_report)
            if ocr_page.backend not in recorded_text_backends:
                is_native_route = ocr_page.backend == "native-text-layer"
                processing.models.append(
                    ModelRecord(
                        role="text_input" if is_native_route else "ocr",
                        name=ocr_page.backend,
                        version=ocr_page.version,
                        backend=ocr_page.backend,
                        fallback_reason=ocr_page.fallback_reason,
                        weights_hash=(
                            None if is_native_route
                            else _model_cache_hash(self.config.ocr.paddle_version)
                        ),
                    )
                )
                recorded_text_backends.add(ocr_page.backend)
            if not layout_backend_recorded:
                processing.models.append(
                    ModelRecord(
                        role="layout",
                        name=layout_result.backend,
                        version=layout_result.version,
                        backend=layout_result.backend,
                        fallback_reason=layout_result.fallback_reason,
                        weights_hash=_model_cache_hash(self.config.layout.paddle_model),
                    )
                )
                layout_backend_recorded = True

            assigned_native_ids: set[str] = set()
            for region_index, region in enumerate(layout_result.regions):
                block_type = _block_type(region.label)
                analysis_text, analysis_confidence = _ocr_text(region, ocr_page)
                native_text, native_refs = native_text_for_region(
                    region, page, native_page.words,
                    excluded_text_ids=set(region.native_object_ids) if region.list_marker else set(),
                    extra_ref_ids=region.native_object_ids,
                )
                assigned_native_ids.update(native_refs)
                native_confidence = (
                    sum(word.confidence for word in native_page.words if word.id in native_refs)
                    / len(native_refs)
                    if native_refs else 0.0
                )
                native_routed = ocr_page.backend == "native-text-layer"
                ocr_text = "" if native_routed else analysis_text
                ocr_confidence = 0.0 if native_routed else analysis_confidence
                region_text = native_text or analysis_text

                if block_type == BlockType.HEADING and re.match(
                    r"^Question\s+\d+\b", region_text or "", flags=re.IGNORECASE
                ):
                    section_number += 1
                    current_section_id = f"section_{section_number:03d}"
                    section = Block(
                        id=current_section_id,
                        type=BlockType.SECTION,
                        parent_id=document_root.id,
                        order_in_parent=len(document_root.children),
                    )
                    blocks[current_section_id] = section
                    document_root.children.append(current_section_id)

                block_id = f"p{page.page_index:04d}_{block_type.value}_{region_index:04d}"
                crop_ref = crops_dir / f"{block_id}.png"
                if not (resume and self.config.runtime.cache_enabled and crop_ref.is_file()):
                    PDFRenderer.crop(page, region.bbox, crop_ref)
                segment = Segment(
                    id=f"segment_{block_id}",
                    page_index=page.page_index,
                    bbox=_bbox(page, region),
                    crop_ref=str(crop_ref),
                    native_object_refs=native_refs,
                )
                parent_id = document_root.id if block_type in {BlockType.HEADER, BlockType.FOOTER} else current_section_id
                parent = blocks[parent_id]
                content: TextContent | None = None
                conflict_type: str | None = None
                critical = False
                if block_type in {BlockType.HEADER, BlockType.FOOTER}:
                    selected_text = native_text or ocr_text
                    content = TextContent(
                        native_text=native_text,
                        ocr_text=ocr_text,
                        resolved_text=selected_text,
                        resolution=Resolution(
                            selected_source="native" if native_text else "ocr" if ocr_text else "none",
                            reason="repeating_marginal_template",
                            confidence=max(native_confidence, ocr_confidence),
                        ),
                    )
                elif block_type != BlockType.TABLE and block_type != BlockType.FIGURE:
                    content, conflict_type, critical = build_text_content(
                        native_text, ocr_text, native_confidence, ocr_confidence
                    )
                compound_evidence: dict[str, object] = {"operation": "compound_text_binding"}
                if region.index_bbox is not None:
                    compound_evidence["index_bbox"] = list(page.pixel_to_points(region.index_bbox))
                if region.note_bbox is not None:
                    compound_evidence["note_bbox"] = list(page.pixel_to_points(region.note_bbox))
                block = Block(
                    id=block_id,
                    type=block_type,
                    parent_id=parent_id,
                    order_in_parent=len(parent.children),
                    heading_level=region.heading_level,
                    list_marker=region.list_marker,
                    list_level=region.list_level,
                    indent_points=region.indent_points,
                    segments=[segment],
                    content=content,
                    index=region.index_text,
                    note=region.note_text,
                    operations=([compound_evidence] if len(compound_evidence) > 1 else []),
                    quality=BlockQuality(
                        layout_confidence=region.confidence,
                        native_text_confidence=native_confidence,
                        ocr_confidence=ocr_confidence,
                        structure_confidence=region.confidence,
                        requires_review=critical,
                        issues=[conflict_type] if conflict_type else [],
                    ),
                )
                if region.profile_repair:
                    block.operations.append({
                        "operation": "document_profile_template_repair",
                        "template_id": region.profile_template_id,
                        "decision": "auto_repair",
                        "confidence": region.confidence,
                    })
                if region.visual_reclassification_reason:
                    block.operations.append({
                        "operation": "visual_region_reclassification",
                        "decision": f"{region.label}",
                        "reason": region.visual_reclassification_reason,
                        "confidence": region.confidence,
                    })
                if (
                    block_type in {
                        BlockType.HEADING, BlockType.PARAGRAPH,
                        BlockType.LIST, BlockType.FOOTNOTE,
                    }
                    and block.content
                ):
                    blank_text, blank_boxes = (
                        recover_visual_blank_text(page, region, ocr_page)
                        if not native_routed else ("", [])
                    )
                    if blank_text:
                        block.content.review_text = blank_text
                        block.content.resolved_text = blank_text
                        block.content.resolution = Resolution(
                            selected_source="review",
                            reason="visual_blank_recovery",
                            confidence=ocr_confidence,
                        )
                        block.operations.append({
                            "operation": "visual_blank_recovery",
                            "blank_boxes": [
                                list(page.pixel_to_points(blank_box))
                                for blank_box in blank_boxes
                            ],
                        })
                definition_prefix = re.split(r"(?:——|—|–)", region_text or "", maxsplit=1)[0]
                if (
                    block_type in {
                        BlockType.HEADING, BlockType.PARAGRAPH,
                        BlockType.LIST, BlockType.FOOTNOTE,
                    }
                    and region_text
                    and re.search(r"(?:——|—|–)", region_text)
                    and len(definition_prefix) <= 24
                    and re.search(r"(?:∑|γ|[NKt][^\s]{1,12})", definition_prefix)
                ):
                    if self._equation_parser is None:
                        self._equation_parser = EquationParser(self.config.equations)
                    candidate, _ = self._equation_parser.parse(
                        page,
                        region,
                        figures_dir,
                        f"{block_id}_definition_formula_review",
                        region_text,
                        segment_lines=False,
                    )
                    enriched = enrich_definition_formula_text(
                        region_text, candidate.latex or ""
                    )
                    if enriched and block.content:
                        block.content.review_text = enriched
                        block.content.resolved_text = enriched
                        block.content.resolution = Resolution(
                            selected_source="review",
                            reason="definition_formula_prefix_fusion",
                            confidence=ocr_confidence,
                        )
                        block.operations.append({
                            "operation": "definition_formula_prefix_fusion",
                            "formula_backend": candidate.backend,
                            "formula_image_ref": candidate.image_ref,
                        })
                if (
                    block_type in {
                        BlockType.HEADING, BlockType.PARAGRAPH,
                        BlockType.LIST, BlockType.FOOTNOTE,
                    }
                    and region_text
                    and len(region.word_ids) <= 3
                    and len(region_text) <= 100
                    and not re.search(r"(?:——|—|–)", region_text)
                    and any(marker in region_text for marker in ("∫", "∑", "√"))
                ):
                    if self._equation_parser is None:
                        self._equation_parser = EquationParser(self.config.equations)
                    candidate, _ = self._equation_parser.parse(
                        page,
                        region,
                        figures_dir,
                        f"{block_id}_mixed_formula_review",
                        region_text,
                        segment_lines=False,
                        crop_expand_px=max(24, self.config.equations.crop_padding_px * 4),
                    )
                    enriched = enrich_mixed_formula_text(
                        region_text, candidate.latex or ""
                    )
                    if enriched and block.content:
                        block.content.review_text = enriched
                        block.content.resolved_text = enriched
                        block.content.resolution = Resolution(
                            selected_source="review",
                            reason="mixed_text_formula_fusion",
                            confidence=ocr_confidence,
                        )
                        block.operations.append({
                            "operation": "mixed_text_formula_fusion",
                            "formula_backend": candidate.backend,
                            "formula_image_ref": candidate.image_ref,
                        })
                if block_type == BlockType.TABLE:
                    parsed = table_parser.parse(page, region, ocr_page, crops_dir, block_id)
                    if native_routed:
                        for cell in parsed.data.cells:
                            if cell.content.ocr_text and not cell.content.native_text:
                                cell.content.native_text = cell.content.ocr_text
                                cell.content.ocr_text = None
                                if cell.content.resolution.selected_source == "ocr":
                                    cell.content.resolution.selected_source = "native"
                                    cell.content.resolution.reason = (
                                        "table_cell_native_text_layer"
                                    )
                    block.table = parsed.data
                    block.operations.append(parsed.operation)
                    if parsed.ancillary_text:
                        block.note = "; ".join(
                            value for value in (block.note, parsed.ancillary_text) if value
                        )
                    block.quality.issues.extend(parsed.issues)
                    block.quality.requires_review = bool(parsed.issues)
                    block.quality.structure_confidence = 0.75 if not parsed.issues else 0.45
                elif block_type == BlockType.FIGURE:
                    block.figure = parse_figure(page, region, figures_dir, block_id)
                    if native_routed and native_text:
                        block.derived = DerivedContent(
                            embedded_text=native_text,
                            embedded_text_confidence=native_confidence,
                            backend="native-text-layer",
                        )
                    if (
                        self.config.figures.figure_ocr
                        and not (block.derived and block.derived.embedded_text)
                    ):
                        from PIL import Image

                        with Image.open(block.figure.image_ref) as figure_image:
                            embedded_text, embedded_confidence = ocr_backend.recognize_block(
                                figure_image.convert("RGB")
                            )
                        block.derived = DerivedContent(
                            embedded_text=embedded_text or None,
                            embedded_text_confidence=embedded_confidence,
                            backend=ocr_backend.name,
                        )
                    if not block.index and block.derived:
                        learned_index = _figure_index_from_source_text(
                            block.derived.embedded_text
                        )
                        if learned_index:
                            block.index = learned_index
                            block.operations.append({
                                "operation": "figure_index_from_embedded_source_text",
                                "decision": "source_text_title_candidate",
                                "confidence": block.derived.embedded_text_confidence,
                            })
                        elif block.derived.embedded_text:
                            block.operations.append({
                                "operation": "figure_embedded_text_semantic_abstention",
                                "decision": "preserve_as_evidence_but_exclude_from_semantic_exports",
                                "reason": "no_reliable_source_title_candidate",
                                "confidence": block.derived.embedded_text_confidence,
                            })
                    if self.config.figures.visual_understanding:
                        from ..parsers.figure import derive_visual_understanding

                        visual = derive_visual_understanding(
                            block.figure,
                            block.derived.embedded_text if block.derived else None,
                        )
                        block.derived = (block.derived or DerivedContent()).model_copy(
                            update=visual.model_dump(exclude_none=True)
                        )
                elif block_type == BlockType.CODE:
                    block.code, block.derived = parse_code(
                        native_text or ocr_text, self.config.code.infer_language
                    )
                    special = set("{}[]()<>=|&$\\`~^*")
                    native_symbols = [char for char in native_text or "" if char in special]
                    ocr_symbols = [char for char in ocr_text or "" if char in special]
                    symbols_agree = not (native_text and ocr_text) or native_symbols == ocr_symbols
                    block.operations.append({
                        "operation": "code_special_character_validation",
                        "native_symbols": native_symbols,
                        "ocr_symbols": ocr_symbols,
                        "passed": symbols_agree,
                    })
                    if self.config.code.special_character_review and not symbols_agree:
                        block.quality.requires_review = True
                        block.quality.issues.append("code_special_character_conflict")
                elif block_type == BlockType.EQUATION:
                    if self._equation_parser is None:
                        self._equation_parser = EquationParser(self.config.equations)
                    block.equation, block.derived = self._equation_parser.parse(
                        page,
                        region,
                        figures_dir,
                        block_id,
                        native_text or ocr_text,
                    )
                    if self._equation_parser.fallback_reason:
                        block.operations.append({
                            "operation": "equation_transcription_fallback",
                            "reason": self._equation_parser.fallback_reason,
                            "selected_backend": block.equation.backend,
                        })
                    source_equation = native_text or ocr_text or ""
                    risk_symbols = [char for char in source_equation if char in "<>≤≥=±"]
                    derived_equation = block.equation.latex or ""
                    validation_passed = all(
                        symbol not in "≤≥" or ("\\leq" in derived_equation if symbol == "≤" else "\\geq" in derived_equation)
                        for symbol in risk_symbols
                    )
                    block.operations.append({
                        "operation": "equation_high_risk_validation",
                        "risk_symbols": risk_symbols,
                        "passed": validation_passed,
                    })
                    if self.config.equations.high_risk_validation and not validation_passed:
                        block.quality.requires_review = True
                        block.quality.issues.append("equation_high_risk_symbol_conflict")
                if (
                    page_model.page_kind in {"scanned", "mixed"}
                    and block_type not in {BlockType.TABLE, BlockType.FIGURE}
                    and ocr_confidence < self.config.ocr.min_confidence
                ):
                    block.quality.requires_review = True
                    block.quality.issues.append("low_ocr_confidence_on_visual_page")
                blocks[block_id] = block
                parent.children.append(block_id)
                page_model.block_ids.append(block_id)
                if conflict_type and not critical:
                    conflict = Conflict(
                        id=f"conflict_{len(conflicts):05d}",
                        block_id=block_id,
                        native_value=native_text,
                        ocr_value=ocr_text,
                        conflict_type=conflict_type,
                        severity="warning",
                        status="open",
                        evidence_segment_ids=[segment.id],
                        resolution_status=ResolutionStatus.RESOLVED,
                    )
                    conflicts.append(conflict)
                if block.quality.requires_review and block_id not in review_queue:
                    review_queue.append(block_id)
            unassigned_native += len({word.id for word in native_page.words} - assigned_native_ids)

        timings["page_parsing"] = (time.perf_counter() - phase_started) * 1000
        status("assembling")
        processing.status = ProcessingStatus.ASSEMBLING
        phase_started = time.perf_counter()
        block_replacements: dict[str, str] = {}
        review_items: list[ReviewItem] = assemble_document(
            blocks, preflight.pages, self.config.assembly, block_replacements
        )
        for conflict in conflicts:
            seen: set[str] = set()
            while conflict.block_id in block_replacements and conflict.block_id not in seen:
                seen.add(conflict.block_id)
                conflict.block_id = block_replacements[conflict.block_id]
        populate_note_spans(blocks)
        if secondary_native_result and secondary_native_result.pages:
            review_items.extend(apply_secondary_native_gate(
                blocks,
                secondary_native_result.pages,
                auto_repair=self.config.secondary_native.auto_repair_exact_tokens,
                min_context_similarity=self.config.secondary_native.min_context_similarity,
            ))
        review_items.extend(enrich_content_links(blocks, self.config.links))
        review_items.extend(
            validate_profile_consistency(
                blocks,
                preflight.pages,
                document_profile,
                validate_requirement_sequence=(
                    self.config.profiling.validate_requirement_sequence
                ),
                validate_cross_page_columns=(
                    self.config.profiling.validate_cross_page_columns
                ),
                validate_terminal_evidence=(
                    self.config.profiling.validate_terminal_evidence
                ),
            )
        )
        timings["assembly"] = (time.perf_counter() - phase_started) * 1000

        status("reconciling")
        processing.status = ProcessingStatus.RECONCILING
        phase_started = time.perf_counter()
        rendered_lookup = {page.page_index: page for page in rendered_pages}
        native_lookup = {page.page_index: page.words for page in native_result.pages}
        ocr_lookup = {page.page_index: page for page in page_ocr_results}
        evidence_spans = {}
        precision_review_invoked = False
        for block in list(blocks.values()):
            if block.type in {BlockType.DOCUMENT, BlockType.SECTION, BlockType.HEADER, BlockType.FOOTER}:
                continue
            spans = build_evidence_spans(
                block, rendered_lookup, native_lookup, ocr_lookup
            )
            if self.config.precision_review.enabled:
                for span in spans:
                    if span.resolution_status == ResolutionStatus.AMBIGUOUS:
                        precision_review_invoked = True
                        precision_reviewer.resolve_span(span, rendered_lookup[span.page_index])
            for span in spans:
                evidence_spans[span.id] = span
            block_spans = list(spans)
            if apply_abstention_policy(block, block_spans):
                review_items.append(ReviewItem(
                    id=f"review_critical_span_{block.id}", target_id=block.id,
                    reason="unresolved_critical_span", severity="critical",
                    candidate_action="human_confirm_evidence_span",
                    evidence_segment_ids=[segment.id for segment in block.segments],
                ))
            elif block.content and block.content.resolution_status == ResolutionStatus.AMBIGUOUS:
                # Precision review resolved every critical token. Select the full evidence
                # stream that agrees with the resolved critical spans.
                native_agreement = sum(
                    span.resolved_text == span.native_text for span in block_spans if span.native_text
                )
                ocr_agreement = sum(
                    span.resolved_text == span.ocr_text for span in block_spans if span.ocr_text
                )
                selected = "native" if native_agreement >= ocr_agreement and block.content.native_text else "ocr"
                block.content.resolved_text = (
                    block.content.native_text if selected == "native" else block.content.ocr_text
                )
                block.content.resolution = Resolution(
                    selected_source=selected,
                    reason="precision_review_resolved_all_critical_spans",
                    confidence=min((span.confidence for span in block_spans), default=1.0),
                )
                block.content.resolution_status = ResolutionStatus.RESOLVED
                block.content.requires_human_review = False
                block.quality.requires_review = False
                block.quality.issues = [
                    issue for issue in block.quality.issues if issue != "critical_text_conflict"
                ]

        precision_enabled = self.config.precision_review.enabled
        processing.models.append(ModelRecord(
            role="precision_review",
            name=(
                precision_reviewer.last_backend if precision_review_invoked
                else self.config.precision_review.model_name if precision_enabled
                else "disabled"
            ),
            version=(
                "1.6"
                if precision_review_invoked and "PaddleOCR-VL" in precision_reviewer.last_backend
                else None
            ),
            backend=(
                precision_reviewer.last_backend if precision_review_invoked
                else "conflicts_only_deferred" if precision_enabled
                else "disabled"
            ),
            fallback_reason=precision_reviewer.last_fallback_reason,
            weights_hash=(
                _model_cache_hash(self.config.precision_review.model_name)
                if precision_enabled else None
            ),
        ))
        evidence_routing = route_evidence_spans(
            evidence_spans,
            blocks,
            self.config.verification,
        )
        review_items.extend(evidence_routing.review_items)
        conflicts.extend(conflicts_from_spans(
            list(evidence_spans.values()), processing.models, start_index=len(conflicts)
        ))
        _ensure_critical_conflicts_reviewable(blocks, conflicts, review_items)
        timings["reconciliation"] = (time.perf_counter() - phase_started) * 1000

        for report in page_completeness:
            if report.status == "review_required":
                review_items.append(ReviewItem(
                    id=f"review_page_completeness_{report.page_index:04d}",
                    target_id=f"page:{report.page_index}",
                    reason="page_completeness_gate", severity="critical",
                    candidate_action="inspect_unassigned_or_unexplained_content",
                ))
        for block in blocks.values():
            if block.quality.requires_review and not any(item.target_id == block.id for item in review_items):
                critical_issue = any(issue in {
                    "unresolved_critical_span", "table_cell_text_conflict",
                    "table_cell_text_omission", "missing_content_conflict",
                } for issue in block.quality.issues)
                review_items.append(ReviewItem(
                    id=f"review_block_quality_{block.id}", target_id=block.id,
                    reason=";".join(block.quality.issues) or "low_block_quality",
                    severity="critical" if critical_issue else "warning",
                    evidence_segment_ids=[segment.id for segment in block.segments],
                ))

        configured_language = self.config.ocr.language.casefold()
        requirement_language = (
            "no"
            if configured_language in {"no", "nor", "nob", "nno", "norwegian"}
            else "en"
        )
        canonical_requirements = []
        for candidate in native_requirement_candidates:
            family_trusted = (
                requirement_profile is not None
                and requirement_profile.families[candidate.family].status
                is FamilyProfileStatus.ACCEPTED
            )
            canonical_requirements.append(canonicalize_native_requirement(
                candidate,
                source_document=preflight.source.file_name,
                language=requirement_language,
                family_trusted=family_trusted,
            ))
        if requirement_hierarchy_profile is not None:
            canonical_requirements = bind_requirement_hierarchy(
                canonical_requirements,
                requirement_hierarchy_profile,
            )

        expected_requirement_ids: list[str] = []
        if requirement_profile is not None:
            for page_index in sorted(selected_page_indices):
                if page_index not in requirement_profile.page_family:
                    continue
                expected_requirement_ids.extend(
                    requirement_profile.page_candidate_requirement_ids.get(
                        page_index, []
                    )
                )
        expected_requirement_ids = list(dict.fromkeys(expected_requirement_ids))
        assembled_requirement_ids = list(dict.fromkeys(
            requirement.requirement_id for requirement in canonical_requirements
        ))
        missing_requirement_ids = [
            requirement_id for requirement_id in expected_requirement_ids
            if requirement_id not in set(assembled_requirement_ids)
        ]
        for requirement_id in missing_requirement_ids:
            safe_id = re.sub(r"[^A-Za-z0-9]+", "_", requirement_id).strip("_")
            review_items.append(ReviewItem(
                id=f"review_missing_requirement_inventory_{safe_id}",
                target_id=f"requirement:{requirement_id}",
                reason="document_profile_requirement_id_not_assembled",
                severity="critical",
                candidate_action=(
                    "inspect_native_requirement_template_boundary_and_row_assembly"
                ),
            ))
        requirement_assembly_path = raw_dir / "requirement-assembly.json"
        requirement_assembly_path.write_text(json.dumps({
            "backend": "native-template-guided-requirement-assembly",
            "selected_page_indices": sorted(selected_page_indices),
            "language": requirement_language,
            "profile_family_hints": {
                str(page_index): family.value
                for page_index, family in sorted(family_hints.items())
            },
            "profile_inventory_ids": expected_requirement_ids,
            "assembled_requirement_ids": assembled_requirement_ids,
            "missing_requirement_ids": missing_requirement_ids,
            "requirement_statuses": {
                requirement.requirement_id: requirement.status.value
                for requirement in canonical_requirements
            },
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        review_queue = list(dict.fromkeys(
            item.target_id for item in review_items if item.status == "pending"
        ))
        suspected_fragments = self._suspected_cross_page_tables(blocks)
        block_counts = dict(Counter(block.type.value for block in blocks.values()))
        low_confidence = [
            block.id for block in blocks.values()
            if block.type not in {BlockType.DOCUMENT, BlockType.SECTION}
            and (
                block.quality.layout_confidence < 0.35
                or (0 < block.quality.ocr_confidence < 0.25)
            )
        ]
        total_spans = len(evidence_spans)
        automatic_coverage = evidence_routing.automatic_coverage
        quality = DocumentQuality(
            status=DocumentStatus.REVIEW_REQUIRED if review_queue else DocumentStatus.ACCEPTED,
            input_page_count=preflight.source.page_count,
            processed_page_count=len(rendered_pages),
            block_counts=block_counts,
            unknown_block_count=block_counts.get(BlockType.UNKNOWN.value, 0),
            unassigned_native_object_count=sum(
                report.unassigned_native_object_count for report in page_completeness
            ),
            low_confidence_block_ids=low_confidence,
            suspected_cross_page_fragments=suspected_fragments,
            warnings=preflight.warnings,
            automatic_coverage=automatic_coverage,
            provenance_anchor_coverage=(
                sum(bool(block.segments) for block in blocks.values() if block.type not in {BlockType.DOCUMENT, BlockType.SECTION})
                / max(1, sum(block.type not in {BlockType.DOCUMENT, BlockType.SECTION} for block in blocks.values()))
            ),
            human_review_rate=(
                1.0 - automatic_coverage
                if total_spans
                else min(1.0, len(review_queue) / max(1, len(blocks)))
            ),
        )
        processing.completed_at = datetime.now(timezone.utc).isoformat()
        processing.step_timings_ms = timings
        document = Document(
            document_id=f"sha256:{preflight.source.file_hash}",
            source=preflight.source,
            processing=processing,
            pages=preflight.pages,
            root_block_ids=[document_root.id],
            blocks=blocks,
            conflicts=conflicts,
            review_queue=review_queue,
            review_items=review_items,
            evidence_spans=evidence_spans,
            page_completeness=page_completeness,
            quality=quality,
            requirements=canonical_requirements,
        )
        return FinalizationStage().run(
            context,
            FinalizationInput(
                document=document,
                page_ocr_results=page_ocr_results,
                native_manifest_path=native_manifest_path,
                profile_path=profile_path,
                routing_path=routing_path,
                requirement_assembly_path=requirement_assembly_path,
                requirement_profile_path=(
                    requirement_profile_path if requirement_profile is not None else None
                ),
                requirement_hierarchy_profile_path=(
                    requirement_hierarchy_profile_path
                    if requirement_hierarchy_profile is not None
                    else None
                ),
                evidence_routing=evidence_routing,
                overall_started=overall_started,
            ),
        )

    @staticmethod
    def _link_explicit_references(blocks: dict[str, Block]) -> None:
        targets: dict[tuple[str, str], str] = {}
        for block in blocks.values():
            if block.type == BlockType.TABLE and block.index:
                match = re.search(r"\bTable\s+(\d+)\b", block.index, flags=re.IGNORECASE)
                if match:
                    targets[("table", match.group(1))] = block.id
            if block.type == BlockType.FIGURE and block.index:
                match = re.search(r"\b(?:Figure|Fig\.)\s+(\d+)\b", block.index, flags=re.IGNORECASE)
                if match:
                    targets[("figure", match.group(1))] = block.id
        for block_id, block in list(blocks.items()):
            if not block.content or not block.content.resolved_text:
                continue
            links: list[ContentLink] = []
            for match in re.finditer(
                r"\b(Table|Figure|Fig\.)\s+(\d+)\b",
                block.content.resolved_text,
                flags=re.IGNORECASE,
            ):
                kind = "table" if match.group(1).lower() == "table" else "figure"
                target_id = targets.get((kind, match.group(2)))
                if target_id and target_id != block_id:
                    links.append(
                        ContentLink(
                            target_id=target_id,
                            anchor_text=match.group(0),
                            confidence=1.0,
                            evidence_segment_ids=[segment.id for segment in block.segments],
                        )
                    )
            if links:
                blocks[block_id] = block.model_copy(
                    update={"content_links": links, "has_linked_content": True}
                )

    @staticmethod
    def _suspected_cross_page_tables(blocks: dict[str, Block]) -> list[list[str]]:
        tables = [block for block in blocks.values() if block.type == BlockType.TABLE and block.segments]
        tables.sort(key=lambda block: (block.segments[0].page_index, block.segments[0].bbox.y0))
        suspects: list[list[str]] = []
        for left, right in zip(tables, tables[1:], strict=False):
            if right.segments[0].page_index == left.segments[0].page_index + 1:
                if left.segments[0].bbox.y1 > 700 and right.segments[0].bbox.y0 < 100:
                    suspects.append([left.id, right.id])
        return suspects
