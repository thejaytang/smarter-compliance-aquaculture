"""Versioned local snapshot and format-neutral artifact index contracts."""
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

class Snapshot(Strict):
    source_id: str = Field(pattern=r"^[A-Z]{2}\d{3}$")
    snapshot_id: str = Field(pattern=r"^[A-Z]{2}\d{3}-\d{3}$")
    relative_path: str
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    file_format: str
    operator_selection_decision: Literal["INCLUDE"]
    selection_status: Literal["INCLUDE"]
    snapshot_status: Literal["STORED"]
    source_status: Literal["CURRENT"]
    download_status: Literal["SUCCESS"]
    registry_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

class StructureNode(Strict):
    id: str
    kind: str
    parent_id: str | None = None
    locator: str
    data: dict[str, Any]
    confidence: float | None = Field(default=None, ge=0, le=1)
    review_policy: Literal["review_required"] = "review_required"
    reason: str = "uncalibrated_template_extraction"

class HtmlStructure(Strict):
    schema_version: Literal["html-structure/1"] = "html-structure/1"
    source: Snapshot
    parser_version: str
    config_hash: str
    encoding: str
    nodes: list[StructureNode]
    requirement_status: Literal["not_extracted"] = "not_extracted"
    review_policy: Literal["review_required"] = "review_required"
    issues: list[str] = Field(default_factory=list)

class ParseResult(Strict):
    schema_version: Literal["source-parse-result/1"] = "source-parse-result/1"
    source: Snapshot
    format: Literal["html", "pdf", "excel", "unknown"]
    status: Literal["review_required", "blocked", "failed", "not_implemented"]
    reason_codes: list[str] = Field(default_factory=list)
    canonical_path: str | None = None
    canonical_sha256: str | None = None
    canonical_schema_version: str | None = None
    verification_path: str | None = None
    verification_sha256: str | None = None
    # This is an index, never a second copy of Canonical facts.
    requirement_status: Literal["not_extracted", "native_pdf_pipeline"] = "not_extracted"
