"""Application-level orchestration for the extraction workflow.

This package may coordinate modules, but domain parsing and verification rules
belong to their owning modules rather than the orchestrator.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .pipeline import ExtractionPipeline


def __getattr__(name: str) -> Any:
    if name == "ExtractionPipeline":
        from .pipeline import ExtractionPipeline

        return ExtractionPipeline
    raise AttributeError(name)

__all__ = ["ExtractionPipeline"]
