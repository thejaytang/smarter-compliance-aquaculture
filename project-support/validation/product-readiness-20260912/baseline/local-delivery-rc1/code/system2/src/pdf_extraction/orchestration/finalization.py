"""Canonical validation and delivery stage with explicit inputs."""

from __future__ import annotations

import json
import platform
import resource
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..contracts.verification import (
    VerificationDepth,
    VerificationOutcome,
    VerificationReport,
)
from ..delivery import write_derived_artifacts
from ..models import (
    ArtifactReference,
    Document,
    DocumentStatus,
    ProcessingStatus,
)
from ..types import OCRPage
from ..validate import build_quality_report, validate_document, write_schema
from ..verification.evidence_routing import EvidenceRoutingResult
from .context import RunContext
from .runtime import clean_owned_collision_copies, sha256_file


@dataclass(frozen=True)
class FinalizationInput:
    document: Document
    page_ocr_results: list[OCRPage]
    native_manifest_path: Path
    profile_path: Path
    routing_path: Path
    requirement_assembly_path: Path
    requirement_profile_path: Path | None
    requirement_hierarchy_profile_path: Path | None
    evidence_routing: EvidenceRoutingResult
    overall_started: float


class FinalizationStage:
    """Persist final artifacts without owning extraction decisions."""

    def run(self, context: RunContext, inputs: FinalizationInput) -> Document:
        document = inputs.document
        config = context.config
        output = context.paths.output
        raw_dir = context.paths.raw
        processing = document.processing
        context.status("validating")
        processing.status = ProcessingStatus.VALIDATING
        phase_started = time.perf_counter()

        schema_path = write_schema(
            context.paths.schemas / "canonical-document.schema.json"
        )
        ocr_manifest_path = raw_dir / "ocr-manifest.json"
        ocr_manifest_path.write_text(
            json.dumps(
                {
                    "backend": "routed-native-or-ocr",
                    "pages": [
                        {
                            "page_index": page.page_index,
                            "backend": page.backend,
                            "ref": str(page.raw_ref) if page.raw_ref else None,
                        }
                        for page in inputs.page_ocr_results
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        document.artifacts = {
            "schema": ArtifactReference(
                path=str(schema_path), media_type="application/schema+json"
            ),
            "native_evidence": ArtifactReference(
                path=str(inputs.native_manifest_path), media_type="application/json"
            ),
            "ocr_evidence": ArtifactReference(
                path=str(ocr_manifest_path), media_type="application/json"
            ),
            "document_profile": ArtifactReference(
                path=str(inputs.profile_path), media_type="application/json"
            ),
            "text_routing": ArtifactReference(
                path=str(inputs.routing_path), media_type="application/json"
            ),
            "requirement_assembly": ArtifactReference(
                path=str(inputs.requirement_assembly_path),
                media_type="application/json",
            ),
        }
        if inputs.requirement_profile_path is not None:
            document.artifacts["requirement_template_profile"] = ArtifactReference(
                path=str(inputs.requirement_profile_path),
                media_type="application/json",
            )
        if inputs.requirement_hierarchy_profile_path is not None:
            document.artifacts["requirement_hierarchy_profile"] = ArtifactReference(
                path=str(inputs.requirement_hierarchy_profile_path),
                media_type="application/json",
            )

        write_derived_artifacts(document, output, config)
        validation_errors = validate_document(document)
        if validation_errors:
            document.quality.validation_errors = validation_errors
            document.quality.status = DocumentStatus.FAILED

        verification_report = VerificationReport(
            document_id=document.document_id,
            depth=VerificationDepth(config.verification.depth),
            outcome=(
                VerificationOutcome.FAIL
                if document.quality.status == DocumentStatus.FAILED
                else VerificationOutcome.REVIEW
                if document.quality.status == DocumentStatus.REVIEW_REQUIRED
                else VerificationOutcome.PASS
            ),
            assessments=inputs.evidence_routing.assessments,
            automatic_coverage=inputs.evidence_routing.automatic_coverage,
            human_review_count=len(inputs.evidence_routing.review_items),
        )
        verification_report_path = output / "verification-report.json"
        verification_report_path.write_text(
            json.dumps(
                verification_report.model_dump(mode="json"),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        document.artifacts["verification_report"] = ArtifactReference(
            path=str(verification_report_path),
            media_type="application/json",
            sha256=sha256_file(verification_report_path),
        )

        processing.status = {
            DocumentStatus.ACCEPTED: ProcessingStatus.ACCEPTED,
            DocumentStatus.REVIEW_REQUIRED: ProcessingStatus.REVIEW_REQUIRED,
            DocumentStatus.FAILED: ProcessingStatus.FAILED,
        }[document.quality.status]
        context.timings["validation_and_exports"] = (
            time.perf_counter() - phase_started
        ) * 1000
        context.timings["total"] = (
            time.perf_counter() - inputs.overall_started
        ) * 1000
        processing.step_timings_ms = context.timings

        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        peak_mb = peak / (1024 * 1024) if platform.system() == "Darwin" else peak / 1024
        performance_path = output / "performance-report.json"
        performance_path.write_text(
            json.dumps(
                {
                    "document_id": document.document_id,
                    "page_count": len(document.pages),
                    "total_seconds": context.timings["total"] / 1000,
                    "seconds_per_page": (
                        context.timings["total"] / 1000 / max(1, len(document.pages))
                    ),
                    "peak_rss_mb": peak_mb,
                    "page_workers": config.runtime.page_workers,
                    "batch_size": config.runtime.batch_size,
                    "within_budget": (
                        context.timings["total"]
                        / 1000
                        / max(1, len(document.pages))
                        <= config.release.max_seconds_per_page
                        and peak_mb <= config.release.max_peak_memory_mb
                    ),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        document.artifacts["performance_report"] = ArtifactReference(
            path=str(performance_path),
            media_type="application/json",
            sha256=sha256_file(performance_path),
        )

        security_path = output / "security-report.json"
        security_path.write_text(
            json.dumps(
                {
                    "document_id": document.document_id,
                    "input": {
                        "encrypted": document.source.encrypted,
                        "has_javascript": document.source.has_javascript,
                        "embedded_file_count": document.source.embedded_file_count,
                        "external_link_count": document.source.external_link_count,
                    },
                    "policy": document.processing.data_routing,
                    "limits": config.security.model_dump(mode="json"),
                    "output_permissions": "owner_only_requested",
                    "passed": (
                        not document.source.encrypted
                        and not document.source.has_javascript
                        and document.source.embedded_file_count == 0
                    ),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        document.artifacts["security_report"] = ArtifactReference(
            path=str(security_path),
            media_type="application/json",
            sha256=sha256_file(security_path),
        )
        if context.timings["total"] / 1000 > config.security.processing_timeout_seconds:
            raise TimeoutError("processing exceeded configured timeout")
        if peak_mb > config.security.max_memory_mb:
            raise MemoryError("processing exceeded configured memory limit")

        quality_path = output / "quality-report.json"
        quality_path.write_text(
            json.dumps(build_quality_report(document), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        document.artifacts["quality_report"] = ArtifactReference(
            path=str(quality_path),
            media_type="application/json",
            sha256=sha256_file(quality_path),
        )
        for key, artifact in list(document.artifacts.items()):
            artifact_path = Path(artifact.path)
            if artifact_path.exists():
                document.artifacts[key] = artifact.model_copy(
                    update={"sha256": sha256_file(artifact_path)}
                )
        context.paths.canonical.write_text(
            json.dumps(document.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        for artifact in document.artifacts.values():
            try:
                Path(artifact.path).chmod(0o600)
            except OSError:
                pass
        try:
            context.paths.canonical.chmod(0o600)
        except OSError:
            pass
        context.status(
            document.quality.status.value,
            {
                "pages": len(document.pages),
                "blocks": len(document.blocks),
                "review_items": len(document.review_queue),
            },
        )
        for cleanup_pass in range(3):
            clean_owned_collision_copies(output)
            if cleanup_pass < 2:
                time.sleep(0.2)
        return document


__all__ = ["FinalizationInput", "FinalizationStage"]
