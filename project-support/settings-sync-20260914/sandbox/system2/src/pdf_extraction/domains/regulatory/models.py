from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ...models import Requirement


class RegulatoryStatement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    requirement_id: str | None = None
    regulated_entity: str | None = None
    modality: str
    action: str | None = None
    object: str | None = None
    condition: str | None = None
    exception: str | None = None
    threshold: str | None = None
    jurisdiction: str | None = None
    effective_date: str | None = None
    cross_references: list[str] = Field(default_factory=list)
    source_block_ids: list[str] = Field(default_factory=list)
    source_segment_ids: list[str] = Field(min_length=1)
    source_page_indices: list[int] = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)


class RegulatoryIRDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "2.0"
    document_id: str
    requirements: list[Requirement] = Field(default_factory=list)
    statements: list[RegulatoryStatement] = Field(default_factory=list)
    extraction_backend: str = "canonical-requirement-derived-rules"
    review_required: list[str] = Field(default_factory=list)
    requirement_review_required: list[str] = Field(default_factory=list)
    formal_requirement_ids: list[str] = Field(default_factory=list)
    missing_requirement_ids: list[str] = Field(default_factory=list)
