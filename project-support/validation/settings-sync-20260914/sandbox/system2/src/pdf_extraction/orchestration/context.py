"""Explicit runtime context shared by orchestration stages."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from ..config import AppConfig
from ..delivery import write_derived_artifacts
from ..models import Document
from .runtime import (
    clean_owned_collision_copies,
    clean_owned_output,
    sha256_bytes,
    sha256_file,
    source_tree_hash,
)


StatusCallback = Callable[[str, dict[str, object] | None], None]


@dataclass(frozen=True)
class RunPaths:
    output: Path
    pages: Path
    crops: Path
    figures: Path
    raw: Path
    schemas: Path
    canonical: Path
    checkpoint: Path

    @classmethod
    def from_output(cls, output: str | Path) -> "RunPaths":
        root = Path(output)
        return cls(
            output=root,
            pages=root / "pages",
            crops=root / "crops",
            figures=root / "figures",
            raw=root / "raw",
            schemas=root / "schemas",
            canonical=root / "canonical.json",
            checkpoint=root / "runtime-checkpoint.json",
        )

    def prepare(self) -> None:
        for directory in (
            self.output,
            self.pages,
            self.crops,
            self.figures,
            self.raw,
            self.schemas,
        ):
            directory.mkdir(parents=True, exist_ok=True)
            try:
                directory.chmod(0o700)
            except OSError:
                pass


@dataclass
class RunContext:
    source_path: Path
    paths: RunPaths
    config: AppConfig
    resume: bool
    page_indices: set[int] | None
    config_hash: str
    source_tree_fingerprint: str
    status_callback: StatusCallback | None = None
    timings: dict[str, float] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        pdf_path: str | Path,
        output_dir: str | Path,
        config: AppConfig,
        *,
        resume: bool = False,
        page_indices: set[int] | None = None,
        status_callback: StatusCallback | None = None,
    ) -> "RunContext":
        paths = RunPaths.from_output(output_dir)
        if not resume:
            clean_owned_output(paths.output)
        paths.prepare()
        config_bytes = json.dumps(
            {
                "config": config.model_dump(mode="json"),
                "page_indices": (
                    sorted(page_indices) if page_indices is not None else None
                ),
            },
            sort_keys=True,
        ).encode()
        return cls(
            source_path=Path(pdf_path),
            paths=paths,
            config=config,
            resume=resume,
            page_indices=page_indices,
            config_hash=sha256_bytes(config_bytes),
            source_tree_fingerprint=source_tree_hash(),
            status_callback=status_callback,
        )

    def status(
        self,
        value: str,
        payload: dict[str, object] | None = None,
    ) -> None:
        self.paths.checkpoint.write_text(
            json.dumps(
                {
                    "status": value,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "payload": payload or {},
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        if self.status_callback:
            self.status_callback(value, payload)

    def load_resumable_document(self) -> Document | None:
        if not self.resume or not self.paths.canonical.is_file():
            return None
        cached = Document.model_validate_json(
            self.paths.canonical.read_text(encoding="utf-8")
        )
        if not (
            cached.source.file_hash == sha256_file(self.source_path)
            and cached.processing.config_hash == self.config_hash
            and cached.processing.pipeline_commit == self.source_tree_fingerprint
        ):
            return None
        cached.processing.resumed_from = str(self.paths.canonical)
        cached.processing.retry_count += 1
        write_derived_artifacts(cached, self.paths.output, self.config)
        self.paths.canonical.write_text(
            json.dumps(cached.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.status(cached.quality.status.value, {"resumed": True})
        clean_owned_collision_copies(self.paths.output)
        return cached


__all__ = ["RunContext", "RunPaths", "StatusCallback"]
