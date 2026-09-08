from __future__ import annotations

import argparse
import json
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

from ..config import AppConfig
from ..review import PageLabelDecision, ReviewDecision, apply_review_decision, correct_page_label
from ..review.transaction import GuardedReviewRequest, ReviewConflict, apply_guarded_review, review_context
from .store import JobStore
from .worker import run_job


class SubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    input_path: str
    output_dir: str
    config_path: str = "config/default.yaml"


def create_app(database: str | Path = "runtime/jobs.sqlite3", ui_dir: str | Path | None = None) -> FastAPI:
    store = JobStore(database)
    app = FastAPI(title="PDF Extraction Product", version="0.3.0")
    app.state.store = store
    static_dir = Path(ui_dir) if ui_dir else Path(__file__).resolve().parents[3] / "ui"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/health")
    def health():
        return {"status": "ok", "version": app.version}

    @app.get("/metrics", response_class=PlainTextResponse)
    def metrics():
        counts = store.status_counts()
        lines = [
            "# HELP pdf_extraction_jobs Jobs by current processing status",
            "# TYPE pdf_extraction_jobs gauge",
        ]
        lines.extend(
            f'pdf_extraction_jobs{{status="{status}"}} {count}'
            for status, count in sorted(counts.items())
        )
        return "\n".join(lines) + "\n"

    def job_or_404(job_id: str):
        try:
            return store.get(job_id)
        except KeyError as exc:
            raise HTTPException(404, "job not found") from exc

    @app.post("/documents", status_code=202)
    def submit(request: SubmitRequest):
        input_path = Path(request.input_path).resolve()
        if not input_path.is_file() or input_path.suffix.lower() != ".pdf":
            raise HTTPException(400, "input_path must identify an existing PDF")
        config_path = Path(request.config_path).resolve()
        if not config_path.is_file():
            raise HTTPException(400, "config_path does not exist")
        job = store.create(str(input_path), str(Path(request.output_dir).resolve()), str(config_path))
        return job.__dict__

    @app.post("/jobs/{job_id}/run")
    def process(job_id: str):
        job = job_or_404(job_id)
        if job.status == "queued":
            job = store.update(job.id, "preflight", payload={"inline": True})
        if job.status != "preflight":
            raise HTTPException(409, f"job cannot run from {job.status}")
        return run_job(store, job).__dict__

    @app.get("/jobs/{job_id}")
    def status(job_id: str):
        job = job_or_404(job_id)
        return {**job.__dict__, "events": store.events(job_id)}

    @app.post("/jobs/{job_id}/retry")
    def retry(job_id: str):
        job = job_or_404(job_id)
        config = AppConfig.from_yaml(job.config_path)
        try:
            return store.retry(job_id, config.runtime.retry_limit).__dict__
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    def json_artifact(job_id: str, name: str):
        job = job_or_404(job_id)
        path = Path(job.output_dir) / name
        if not path.is_file():
            raise HTTPException(404, f"{name} is not available")
        return json.loads(path.read_text(encoding="utf-8"))

    @app.get("/jobs/{job_id}/canonical")
    def canonical(job_id: str):
        return json_artifact(job_id, "canonical.json")

    @app.get("/jobs/{job_id}/quality")
    def quality(job_id: str):
        document = json_artifact(job_id, "canonical.json")
        artifact = document.get('artifacts', {}).get('quality_report')
        if artifact:
            return json.loads(Path(artifact['path']).read_text(encoding='utf-8'))
        return json_artifact(job_id, "quality-report.json")

    @app.get('/jobs/{job_id}/review-context')
    def guarded_context(job_id: str):
        job = job_or_404(job_id)
        return review_context(Path(job.output_dir) / 'canonical.json')

    @app.post('/jobs/{job_id}/reviews/guarded')
    def guarded_review(job_id: str, request: GuardedReviewRequest):
        job = job_or_404(job_id)
        try:
            document = apply_guarded_review(
                Path(job.output_dir) / 'canonical.json', request,
                AppConfig.from_yaml(job.config_path),
            )
        except ReviewConflict as exc:
            raise HTTPException(409, str(exc)) from exc
        except (KeyError, ValueError, IndexError) as exc:
            raise HTTPException(400, str(exc)) from exc
        # A replay can refer to an older revision; job state follows current Canonical.
        current = review_context(Path(job.output_dir) / 'canonical.json')
        store.update(job_id, current['document']['quality']['status'], payload={
            'request_id':str(request.request_id), 'applied_revision':document.revision,
        })
        return {'revision':document.revision, 'status':document.quality.status.value,
                'current_revision':current['revision'],
                'receipt':document.artifacts['review_receipt'].model_dump()}

    @app.get("/jobs/{job_id}/review-queue")
    def review_queue(job_id: str):
        document = json_artifact(job_id, "canonical.json")
        return {"targets": document["review_queue"], "items": document["review_items"]}

    @app.post("/jobs/{job_id}/reviews")
    def review(job_id: str, decision: ReviewDecision):
        job = job_or_404(job_id)
        try:
            document = apply_review_decision(
                Path(job.output_dir) / "canonical.json", decision,
                AppConfig.from_yaml(job.config_path),
            )
        except (KeyError, ValueError) as exc:
            raise HTTPException(400, str(exc)) from exc
        store.update(job_id, document.quality.status.value, payload={"review": decision.model_dump()})
        return {"revision": document.revision, "status": document.quality.status.value}

    @app.post("/jobs/{job_id}/page-labels")
    def page_label(job_id: str, decision: PageLabelDecision):
        job = job_or_404(job_id)
        try:
            document = correct_page_label(
                Path(job.output_dir) / "canonical.json", decision,
                AppConfig.from_yaml(job.config_path),
            )
        except (IndexError, ValueError) as exc:
            raise HTTPException(400, str(exc)) from exc
        return {
            "revision": document.revision,
            "page_index": decision.page_index,
            "label": decision.label,
        }

    @app.get("/jobs/{job_id}/exports/{artifact_name}")
    def export(job_id: str, artifact_name: str):
        document = json_artifact(job_id, "canonical.json")
        artifact = document.get("artifacts", {}).get(artifact_name)
        if not artifact:
            raise HTTPException(404, "artifact not found")
        return FileResponse(artifact["path"], media_type=artifact["media_type"])

    @app.get("/jobs/{job_id}/source")
    def source(job_id: str):
        job = job_or_404(job_id)
        return FileResponse(job.input_path, media_type="application/pdf")

    @app.get("/jobs/{job_id}/pages/{page_index}")
    def page_image(job_id: str, page_index: int):
        document = json_artifact(job_id, "canonical.json")
        pages = document.get("pages", [])
        page = next((item for item in pages if item.get("page_index") == page_index), None)
        if page is None:
            raise HTTPException(404, "page not found")
        return FileResponse(page["image_ref"], media_type="image/png")

    @app.get("/review/{job_id}")
    def review_ui(job_id: str):
        job_or_404(job_id)
        page = static_dir / "review.html"
        if not page.is_file():
            raise HTTPException(404, "review UI is not installed")
        return FileResponse(page, media_type="text/html")

    return app


app = create_app()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="PDF Extraction Product REST API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--database", default="runtime/jobs.sqlite3")
    parser.add_argument("--ui-dir")
    args = parser.parse_args(argv)
    runtime_app = create_app(args.database, args.ui_dir)
    uvicorn.run(runtime_app, host=args.host, port=args.port, reload=False)
