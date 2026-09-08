from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

if TYPE_CHECKING:
    from .requirement import Requirement


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class BlockType(str, Enum):
    DOCUMENT = "document"
    SECTION = "section"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    LIST_ITEM = "list_item"
    TABLE = "table"
    FIGURE = "figure"
    CODE = "code"
    EQUATION = "equation"
    FOOTNOTE = "footnote"
    HEADER = "header"
    FOOTER = "footer"
    UNKNOWN = "unknown"


class DocumentStatus(str, Enum):
    ACCEPTED = "accepted"
    REVIEW_REQUIRED = "review_required"
    FAILED = "failed"


class ProcessingStatus(str, Enum):
    QUEUED = "queued"
    PREFLIGHT = "preflight"
    PARSING = "parsing"
    ASSEMBLING = "assembling"
    RECONCILING = "reconciling"
    VALIDATING = "validating"
    REVIEW_REQUIRED = "review_required"
    ACCEPTED = "accepted"
    FAILED = "failed"


class ResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    UNREADABLE = "unreadable"
    HUMAN_CONFIRMED = "human_confirmed"


class BoundingBox(StrictModel):
    x0: float = Field(ge=0)
    y0: float = Field(ge=0)
    x1: float = Field(gt=0)
    y1: float = Field(gt=0)

    @model_validator(mode="after")
    def ordered(self) -> "BoundingBox":
        if self.x1 <= self.x0 or self.y1 <= self.y0:
            raise ValueError("bbox must have positive width and height")
        return self

    def as_list(self) -> list[float]:
        return [self.x0, self.y0, self.x1, self.y1]


class ArtifactReference(StrictModel):
    path: str
    media_type: str
    sha256: str | None = None


class Segment(StrictModel):
    id: str
    page_index: int = Field(ge=0)
    bbox: BoundingBox
    coord_origin: Literal["top_left"] = "top_left"
    crop_ref: str | None = None
    native_object_refs: list[str] = Field(default_factory=list)


class Resolution(StrictModel):
    selected_source: Literal["native", "ocr", "review", "both", "none"]
    reason: str
    confidence: float = Field(ge=0, le=1)


class TextContent(StrictModel):
    native_text: str | None = None
    ocr_text: str | None = None
    review_text: str | None = None
    resolved_text: str | None = None
    resolution: Resolution
    resolution_status: ResolutionStatus = ResolutionStatus.RESOLVED
    requires_human_review: bool = False


class ContentLink(StrictModel):
    target_id: str
    anchor_text: str | None = None
    link_type: Literal["explicit", "inferred"] = "explicit"
    relation: str = "references"
    confidence: float = Field(ge=0, le=1)
    evidence_segment_ids: list[str] = Field(default_factory=list)


class TableCell(StrictModel):
    id: str
    row: int = Field(ge=0)
    column: int = Field(ge=0)
    row_span: int = Field(default=1, ge=1)
    column_span: int = Field(default=1, ge=1)
    bbox: BoundingBox
    page_index: int | None = Field(default=None, ge=0)
    content: TextContent
    is_header: bool = False


class TableData(StrictModel):
    row_count: int = Field(ge=1)
    column_count: int = Field(ge=1)
    cells: list[TableCell]
    parser_backend: str
    html: str | None = None


class FigureData(StrictModel):
    image_ref: str
    width_px: int = Field(gt=0)
    height_px: int = Field(gt=0)


class CodeData(StrictModel):
    raw_text: str
    lines: list[str] = Field(default_factory=list)
    language: str | None = None
    language_confidence: float | None = Field(default=None, ge=0, le=1)


class EquationData(StrictModel):
    image_ref: str
    latex: str | None = None
    structured_expression: dict[str, Any] | None = None
    transcription_confidence: float | None = Field(default=None, ge=0, le=1)
    backend: str | None = None


class DerivedContent(StrictModel):
    embedded_text: str | None = None
    embedded_text_confidence: float | None = Field(default=None, ge=0, le=1)
    backend: str | None = None
    visual_description: str | None = None
    entities: list[dict[str, Any]] = Field(default_factory=list)
    relations: list[dict[str, Any]] = Field(default_factory=list)
    latex: str | None = None
    structured_expression: dict[str, Any] | None = None
    language: str | None = None
    model_version: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class NoteSpan(StrictModel):
    text: str
    role: Literal["note", "source", "warning", "unknown"] = "unknown"
    bbox: BoundingBox | None = None
    confidence: float = Field(default=1.0, ge=0, le=1)


class EvidenceSpan(StrictModel):
    id: str
    block_id: str
    segment_id: str
    page_index: int = Field(ge=0)
    bbox: BoundingBox
    native_text: str | None = None
    ocr_text: str | None = None
    review_text: str | None = None
    resolved_text: str | None = None
    criticality: Literal[
        "numeric", "unit", "date", "section_reference", "negation",
        "modality", "comparison_operator", "general"
    ]
    resolution_status: ResolutionStatus
    confidence: float = Field(ge=0, le=1)
    requires_human_review: bool = False
    review_threshold: float | None = Field(default=None, ge=0, le=1)
    review_reason_codes: list[str] = Field(default_factory=list)
    evidence_path_ids: list[str] = Field(default_factory=list)
    native_object_refs: list[str] = Field(default_factory=list)
    ocr_word_ids: list[str] = Field(default_factory=list)
    trigger_rules: list[str] = Field(default_factory=list)


class PageCompletenessReport(StrictModel):
    page_index: int = Field(ge=0)
    native_object_count: int = Field(ge=0)
    assigned_native_object_count: int = Field(ge=0)
    unassigned_native_object_count: int = Field(ge=0)
    detected_block_count: int = Field(ge=0)
    ocr_word_count: int = Field(ge=0)
    assigned_ocr_word_count: int = Field(ge=0)
    unexplained_visual_regions: list[BoundingBox] = Field(default_factory=list)
    duplicate_regions: list[list[str]] = Field(default_factory=list)
    status: Literal["accepted", "review_required", "failed"]


class ReviewItem(StrictModel):
    id: str
    target_id: str
    reason: str
    severity: Literal["warning", "critical"]
    status: Literal[
        "pending", "resolved", "human_confirmed", "accepted", "modified",
        "rejected", "unreadable"
    ] = "pending"
    candidate_action: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_segment_ids: list[str] = Field(default_factory=list)


class BlockQuality(StrictModel):
    layout_confidence: float = Field(default=0, ge=0, le=1)
    native_text_confidence: float = Field(default=0, ge=0, le=1)
    ocr_confidence: float = Field(default=0, ge=0, le=1)
    structure_confidence: float = Field(default=0, ge=0, le=1)
    requires_review: bool = False
    issues: list[str] = Field(default_factory=list)


class Block(StrictModel):
    id: str
    type: BlockType
    parent_id: str | None = None
    children: list[str] = Field(default_factory=list)
    order_in_parent: int = Field(default=0, ge=0)
    heading_level: int | None = Field(default=None, ge=1, le=6)
    list_marker: str | None = None
    list_level: int | None = Field(default=None, ge=0)
    indent_points: float | None = Field(default=None, ge=0)
    segments: list[Segment] = Field(default_factory=list)
    content: TextContent | None = None
    index: str | None = None
    note: str | None = None
    note_spans: list[NoteSpan] = Field(default_factory=list)
    derived: DerivedContent | None = None
    table: TableData | None = None
    figure: FigureData | None = None
    code: CodeData | None = None
    equation: EquationData | None = None
    has_linked_content: bool = False
    content_links: list[ContentLink] = Field(default_factory=list)
    quality: BlockQuality = Field(default_factory=BlockQuality)
    operations: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def linked_content_consistent(self) -> "Block":
        if self.has_linked_content != bool(self.content_links):
            raise ValueError("has_linked_content must equal bool(content_links)")
        return self


class Page(StrictModel):
    page_index: int = Field(ge=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    rotation: int
    image_ref: str
    native_text_coverage: float = Field(ge=0, le=1)
    image_coverage: float = Field(ge=0, le=1)
    page_kind: Literal["born_digital", "scanned", "mixed", "blank"]
    block_ids: list[str] = Field(default_factory=list)
    pdf_page_label: str | None = None
    printed_page_label: str | None = None
    page_label_confidence: float | None = Field(default=None, ge=0, le=1)
    page_label_source: Literal["pdf", "printed", "human", "none"] = "none"
    page_label_correction: str | None = None


class Conflict(StrictModel):
    id: str
    block_id: str
    native_value: str | None
    ocr_value: str | None
    conflict_type: str
    severity: Literal["info", "warning", "critical"]
    status: Literal["open", "review_required", "resolved"]
    evidence_segment_ids: list[str] = Field(default_factory=list)
    evidence_span_ids: list[str] = Field(default_factory=list)
    bbox: BoundingBox | None = None
    review_value: str | None = None
    trigger_rules: list[str] = Field(default_factory=list)
    model_versions: list[str] = Field(default_factory=list)
    resolution_status: ResolutionStatus = ResolutionStatus.AMBIGUOUS


class ModelRecord(StrictModel):
    role: str
    name: str
    version: str | None = None
    backend: str
    fallback_reason: str | None = None
    weights_hash: str | None = None


class SourceMetadata(StrictModel):
    file_name: str
    file_hash: str
    file_size: int = Field(ge=0)
    pdf_version: str | None = None
    page_count: int = Field(ge=1)
    encrypted: bool
    parser_page_index_origin: int = 0
    has_javascript: bool = False
    embedded_file_count: int = Field(default=0, ge=0)
    external_link_count: int = Field(default=0, ge=0)
    security_warnings: list[str] = Field(default_factory=list)


class ProcessingMetadata(StrictModel):
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str | None = None
    pipeline_version: str
    config_hash: str
    models: list[ModelRecord] = Field(default_factory=list)
    status: ProcessingStatus = ProcessingStatus.PREFLIGHT
    pipeline_commit: str | None = None
    renderer_name: str | None = None
    renderer_version: str | None = None
    render_dpi: int | None = None
    environment: dict[str, str] = Field(default_factory=dict)
    hardware: dict[str, str] = Field(default_factory=dict)
    random_seed: int = 0
    deterministic: bool = True
    step_timings_ms: dict[str, float] = Field(default_factory=dict)
    retry_count: int = Field(default=0, ge=0)
    resumed_from: str | None = None
    processed_page_indices: list[int] = Field(default_factory=list)
    data_routing: dict[str, Any] = Field(default_factory=dict)


class AuditEvent(StrictModel):
    id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    actor: str
    action: Literal["accept", "modify", "reject", "unreadable"]
    target_type: Literal["block", "span", "cell", "page_label"]
    target_id: str
    previous_value_hash: str | None = None
    new_value: str | None = None
    reason: str | None = None
    revision: int = Field(ge=1)


class DocumentQuality(StrictModel):
    status: DocumentStatus
    input_page_count: int = Field(ge=1)
    processed_page_count: int = Field(ge=0)
    block_counts: dict[str, int] = Field(default_factory=dict)
    unknown_block_count: int = Field(default=0, ge=0)
    unassigned_native_object_count: int = Field(default=0, ge=0)
    low_confidence_block_ids: list[str] = Field(default_factory=list)
    suspected_cross_page_fragments: list[list[str]] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    accepted_result_precision: float | None = Field(default=None, ge=0, le=1)
    automatic_coverage: float | None = Field(default=None, ge=0, le=1)
    provenance_anchor_coverage: float | None = Field(default=None, ge=0, le=1)
    human_review_rate: float | None = Field(default=None, ge=0, le=1)


class Document(StrictModel):
    schema_version: str = "1.5"
    document_id: str
    source: SourceMetadata
    processing: ProcessingMetadata
    pages: list[Page]
    root_block_ids: list[str]
    blocks: dict[str, Block]
    conflicts: list[Conflict] = Field(default_factory=list)
    review_queue: list[str] = Field(default_factory=list)
    review_items: list[ReviewItem] = Field(default_factory=list)
    evidence_spans: dict[str, EvidenceSpan] = Field(default_factory=dict)
    page_completeness: list[PageCompletenessReport] = Field(default_factory=list)
    quality: DocumentQuality
    artifacts: dict[str, ArtifactReference] = Field(default_factory=dict)
    audit_events: list[AuditEvent] = Field(default_factory=list)
    requirements: list[Requirement] = Field(default_factory=list)
    revision: int = Field(default=0, ge=0)
