"""Stable contracts for the canonical document artifact.

Implementation modules may evolve, but cross-module communication should use
these exported models rather than importing parser internals.
"""

from ..models import (
    ArtifactReference,
    Block,
    BlockType,
    BoundingBox,
    Document,
    DocumentQuality,
    DocumentStatus,
    Page,
    ProcessingMetadata,
    ProcessingStatus,
    Requirement,
    ReviewItem,
    Segment,
)

__all__ = [
    "ArtifactReference",
    "Block",
    "BlockType",
    "BoundingBox",
    "Document",
    "DocumentQuality",
    "DocumentStatus",
    "Page",
    "ProcessingMetadata",
    "ProcessingStatus",
    "Requirement",
    "ReviewItem",
    "Segment",
]
