"""Backward-compatible access to the extraction orchestrator.

New code should import :class:`ExtractionPipeline` from
``pdf_extraction.orchestration``.  This module remains intentionally thin so
existing CLI, API, scripts, and downstream callers do not break during the
modular migration.
"""

from typing import TYPE_CHECKING, Any

from .orchestration.runtime import (
    clean_owned_collision_copies as _clean_owned_collision_copies,
    clean_owned_output as _clean_owned_output,
)
from .verification.conflict_review import (
    ensure_critical_conflicts_reviewable as _ensure_critical_conflicts_reviewable,
)

if TYPE_CHECKING:
    from .orchestration.pipeline import ExtractionPipeline

PIPELINE_VERSION = "0.5.0"


def __getattr__(name: str) -> Any:
    if name == "ExtractionPipeline":
        from .orchestration.pipeline import ExtractionPipeline

        return ExtractionPipeline
    raise AttributeError(name)

__all__ = ["ExtractionPipeline", "PIPELINE_VERSION"]
