from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ProfileModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RequirementCandidate(ProfileModel):
    page_index: int = Field(ge=0)
    requirement_number: str
    bbox_points: tuple[float, float, float, float]
    column_boundary_points: float
    indicator_text: str
    requirement_text: str
    support_object_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class RequirementTemplate(ProfileModel):
    id: str = "indicator_requirement_v1"
    support_count: int = Field(ge=0)
    left_x_ratio: float = Field(ge=0, le=1)
    column_boundary_ratio: float = Field(ge=0, le=1)
    right_x_ratio: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)


class NumberingProfile(ProfileModel):
    observed: list[str] = Field(default_factory=list)
    possible_gaps: list[str] = Field(default_factory=list)


class TerminalProfile(ProfileModel):
    sample_count: int = Field(ge=0)
    terminal_counts: dict[str, int] = Field(default_factory=dict)
    punctuation_rate: float = Field(ge=0, le=1)


class DocumentProfile(ProfileModel):
    version: str = "1.0"
    page_count: int = Field(ge=1)
    backend: str = "robust-native-template-learning"
    requirement_template: RequirementTemplate | None = None
    requirement_candidates: list[RequirementCandidate] = Field(default_factory=list)
    numbering: NumberingProfile = Field(default_factory=NumberingProfile)
    terminals: TerminalProfile = Field(
        default_factory=lambda: TerminalProfile(
            sample_count=0, terminal_counts={}, punctuation_rate=0.0
        )
    )
    marginal_page_count: int = Field(default=0, ge=0)
