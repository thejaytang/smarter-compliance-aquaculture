"""Evidence-preserving PDF extraction."""

from pathlib import Path
from typing import TYPE_CHECKING, Any

from .config import AppConfig

if TYPE_CHECKING:
    from .orchestration import ExtractionPipeline

__version__ = "0.4.0"


def extract_pdf(
    pdf_path: str | Path,
    output_dir: str | Path,
    config: AppConfig | str | Path = Path("config/default.yaml"),
    *,
    page_indices: set[int] | None = None,
):
    """Run the same canonical pipeline used by the CLI, API and worker."""
    from .orchestration import ExtractionPipeline

    settings = config if isinstance(config, AppConfig) else AppConfig.from_yaml(config)
    return ExtractionPipeline(settings).run(
        pdf_path, output_dir, page_indices=page_indices
    )


def __getattr__(name: str) -> Any:
    """Load the heavy orchestrator only when the caller actually requests it."""
    if name == "ExtractionPipeline":
        from .orchestration import ExtractionPipeline

        return ExtractionPipeline
    raise AttributeError(name)


__all__ = ["AppConfig", "ExtractionPipeline", "extract_pdf", "__version__"]
