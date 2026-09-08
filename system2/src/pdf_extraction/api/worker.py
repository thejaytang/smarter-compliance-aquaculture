from __future__ import annotations

import argparse
import time
from pathlib import Path

from ..config import AppConfig
from ..pipeline import ExtractionPipeline
from .store import Job, JobStore


_PIPELINES: dict[str, ExtractionPipeline] = {}


def run_job(store: JobStore, job: Job) -> Job:
    config = AppConfig.from_yaml(job.config_path)
    pipeline_key = config.model_dump_json()
    pipeline = _PIPELINES.get(pipeline_key)
    if pipeline is None:
        pipeline = ExtractionPipeline(config)
        _PIPELINES[pipeline_key] = pipeline

    def status(value: str, payload: dict[str, object] | None = None) -> None:
        store.update(job.id, value, payload=payload)

    try:
        document = pipeline.run(
            job.input_path, job.output_dir, status_callback=status,
            resume=True,
        )
        return store.update(
            job.id,
            document.quality.status.value,
            payload={"document_id": document.document_id},
        )
    except Exception as exc:
        return store.update(
            job.id, "failed", error=f"{type(exc).__name__}: {exc}",
            payload={"partial_output_preserved": Path(job.output_dir).exists()},
        )


def run_once(store: JobStore) -> Job | None:
    job = store.claim_next()
    return run_job(store, job) if job else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Persistent PDF extraction worker")
    parser.add_argument("--database", default="runtime/jobs.sqlite3")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll-seconds", type=float, default=1.0)
    args = parser.parse_args(argv)
    store = JobStore(args.database)
    while True:
        result = run_once(store)
        if args.once:
            return 0 if result is None or result.status != "failed" else 1
        if result is None:
            time.sleep(max(0.1, args.poll_seconds))
