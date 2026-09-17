from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class PipelineSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    render_dpi: int = Field(default=200, ge=72, le=600)
    crop_dpi: int = Field(default=300, ge=72, le=600)
    page_index_origin: int = 0


class NativeSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backend: str = "auto"
    preserve_object_refs: bool = True


class SecondaryNativeSettings(BaseModel):
    """Independent, local PDF text evidence used for critical-span checks."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    backend: Literal["pdftotext"] = "pdftotext"
    auto_repair_exact_tokens: bool = True
    min_context_similarity: float = Field(default=0.90, ge=0, le=1)


class LayoutSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backend: str = "auto"
    paddle_model: str = "PP-DocLayoutV3"
    paddle_engine: str = "onnxruntime"
    min_confidence: float = Field(default=0.35, ge=0, le=1)


class OCRSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backend: str = "auto"
    paddle_version: str = "PP-OCRv6"
    paddle_engine: str = "onnxruntime"
    language: str = "eng"
    min_confidence: float = Field(default=0.25, ge=0, le=1)


class TextRoutingSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    min_word_count: int = Field(default=8, ge=1)
    min_character_count: int = Field(default=40, ge=1)
    max_suspicious_character_ratio: float = Field(default=0.02, ge=0, le=1)
    min_valid_bbox_ratio: float = Field(default=0.95, ge=0, le=1)


class TableSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backend: str = "auto"
    paddle_pipeline: str = "PP-TableMagic"
    paddle_engine: str = "onnxruntime"
    recognition_pipeline_enabled: bool = True
    min_width: int = 80
    min_height: int = 40
    img2table_enabled: bool = True
    gmft_enabled: bool = True
    cell_review_confidence: float = Field(default=0.80, ge=0, le=1)
    cell_auto_resolve_confidence: float = Field(default=0.96, ge=0, le=1)
    structure_auto_accept_confidence: float = Field(default=0.85, ge=0, le=1)


class FigureSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preserve_original_crop: bool = True
    figure_ocr: bool = False
    visual_understanding: bool = False


class CodeSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    infer_language: bool = True
    special_character_review: bool = True


class EquationSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transcription_enabled: bool = True
    backend: Literal["auto", "paddle", "native", "disabled"] = "auto"
    model_name: str = "PP-FormulaNet_plus-M"
    paddle_engine: Literal["paddle", "transformers"] = "paddle"
    crop_padding_px: int = Field(default=8, ge=0, le=64)
    high_risk_validation: bool = True


class ConflictSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    critical_patterns: bool = True


class CompletenessSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    min_visual_region_area: int = Field(default=180, ge=1)
    max_unexplained_regions: int = Field(default=0, ge=0)
    duplicate_iou_threshold: float = Field(default=0.85, ge=0, le=1)


class AssemblySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paragraph_auto_merge_threshold: float = Field(default=0.82, ge=0, le=1)
    paragraph_review_threshold: float = Field(default=0.62, ge=0, le=1)
    table_auto_merge_threshold: float = Field(default=0.88, ge=0, le=1)
    table_review_threshold: float = Field(default=0.68, ge=0, le=1)


class PrecisionReviewSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    mode: Literal["conflicts_only"] = "conflicts_only"
    backend: Literal["auto", "paddleocr_vl", "enhanced_ocr"] = "auto"
    model_name: str = "PaddleOCR-VL-1.6"
    auto_resolve_confidence: float = Field(default=0.96, ge=0, le=1)
    crop_scale: float = Field(default=3.0, ge=1, le=8)


class VerificationSettings(BaseModel):
    """Machine verification depth and orthogonal human-review routing policy."""

    model_config = ConfigDict(extra="forbid")

    depth: Literal["internal", "source", "independent", "strong"] = "source"
    default_review_threshold: float = Field(default=0.80, ge=0, le=1)
    criticality_thresholds: dict[str, float] = Field(default_factory=lambda: {
        "general": 0.80,
        "section_reference": 0.95,
        "modality": 0.99,
        "negation": 0.99,
        "numeric": 0.99,
        "unit": 0.99,
        "date": 0.99,
        "comparison_operator": 0.99,
    })
    require_confidence: bool = True
    force_review_on_disagreement: bool = True
    force_review_on_missing_provenance: bool = True


class LinkSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inferred_link_confidence: float = Field(default=0.72, ge=0, le=1)
    inferred_links_require_review: bool = True


class ProfilingSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    min_requirement_template_support: int = Field(default=3, ge=2)
    template_repair_confidence: float = Field(default=0.90, ge=0, le=1)
    validate_requirement_sequence: bool = True
    validate_cross_page_columns: bool = True
    validate_terminal_evidence: bool = True


class EvaluationSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gold_manifest: str = "gold/manifest.json"
    regression_thresholds: dict[str, float] = Field(default_factory=lambda: {
        "critical_span_exact_match": 0.98,
        "critical_conflict_recall": 1.0,
        "accepted_result_precision": 0.98,
        "block_type_f1": 0.98,
        "heading_hierarchy_f1": 0.98,
        "cross_page_merge_precision": 0.98,
        "cross_page_merge_recall": 0.98,
        "cell_exact_match": 0.85,
        "row_column_span_f1": 0.92,
        "max_cer": 0.02,
        "max_wer": 0.03,
        "max_block_omission_rate": 0.02,
    })


class OutputSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canonical_json: bool = True
    markdown: bool = True
    quality_report: bool = True
    html: bool = True
    xml: bool = True
    jsonl: bool = True
    rag_chunks: bool = True
    overlay: bool = True


class RegulatoryIRSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    require_provenance: bool = True


class OntologySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    namespace: str = "https://example.org/regulatory/"
    shacl_enabled: bool = True


class SecuritySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_file_size_mb: int = Field(default=250, ge=1)
    max_pages: int = Field(default=5000, ge=1)
    max_page_dimension_points: float = Field(default=20000, ge=100)
    reject_javascript: bool = True
    reject_embedded_files: bool = True
    external_models_enabled: bool = False
    redact_document_text_in_logs: bool = True
    processing_timeout_seconds: int = Field(default=3600, ge=1)
    max_memory_mb: int = Field(default=8192, ge=128)


class ReleaseSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_provenance_anchor_coverage: float = Field(default=0.99, ge=0, le=1)
    max_human_review_rate: float = Field(default=0.35, ge=0, le=1)
    max_seconds_per_page: float = Field(default=120.0, gt=0)
    max_peak_memory_mb: float = Field(default=8192.0, gt=0)


class RuntimeSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_workers: int = Field(default=1, ge=1, le=32)
    batch_size: int = Field(default=1, ge=1, le=64)
    cache_enabled: bool = True
    retry_limit: int = Field(default=2, ge=0, le=10)
    random_seed: int = 0
    deterministic: bool = True
    job_database: str = "runtime/jobs.sqlite3"


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pipeline: PipelineSettings = PipelineSettings()
    native_extraction: NativeSettings = NativeSettings()
    secondary_native: SecondaryNativeSettings = SecondaryNativeSettings()
    layout: LayoutSettings = LayoutSettings()
    ocr: OCRSettings = OCRSettings()
    text_routing: TextRoutingSettings = TextRoutingSettings()
    tables: TableSettings = TableSettings()
    figures: FigureSettings = FigureSettings()
    code: CodeSettings = CodeSettings()
    equations: EquationSettings = EquationSettings()
    conflicts: ConflictSettings = ConflictSettings()
    completeness: CompletenessSettings = CompletenessSettings()
    assembly: AssemblySettings = AssemblySettings()
    precision_review: PrecisionReviewSettings = PrecisionReviewSettings()
    verification: VerificationSettings = VerificationSettings()
    links: LinkSettings = LinkSettings()
    profiling: ProfilingSettings = ProfilingSettings()
    evaluation: EvaluationSettings = EvaluationSettings()
    outputs: OutputSettings = OutputSettings()
    regulatory_ir: RegulatoryIRSettings = RegulatoryIRSettings()
    ontology: OntologySettings = OntologySettings()
    security: SecuritySettings = SecuritySettings()
    runtime: RuntimeSettings = RuntimeSettings()
    release: ReleaseSettings = ReleaseSettings()

    @classmethod
    def from_yaml(cls, path: str | Path) -> "AppConfig":
        data: dict[str, Any] = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        return cls.model_validate(data)
