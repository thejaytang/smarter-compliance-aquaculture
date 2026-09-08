"""Thin adapter; native PDF Canonical and compatibility entry stay authoritative."""
from hashlib import sha256
from pathlib import Path
from ..contracts.source import ParseResult, Snapshot
from ..contracts.verification import VerificationReport, VerificationOutcome
from ..intake.registry import read_snapshot
from .router import route_format

def parse_pdf(source: Snapshot, source_root: Path, output: Path, config,
              page_indices: set[int]) -> ParseResult:
    if not page_indices or len(page_indices) > 4 or any(type(p) is not int or p < 0 for p in page_indices):
        raise ValueError('pdf_requires_explicit_1_to_4_page_window')
    # No optional remote models or automatic heavy layout/OCR in this intake route.
    if (config.ocr.backend != 'tesseract' or config.layout.backend != 'heuristic'
        or config.native_extraction.backend not in {'pypdf', 'pdfium', 'docling-parse'}
        or config.security.external_models_enabled or config.precision_review.enabled
        or config.equations.transcription_enabled or config.figures.visual_understanding
        or config.tables.recognition_pipeline_enabled or config.tables.backend != 'native'
        or config.tables.img2table_enabled or config.tables.gmft_enabled):
        raise ValueError('pdf_adapter_requires_local_native_config')
    from .. import extract_pdf
    if output.resolve().is_relative_to(source_root.resolve()):
        raise ValueError('output_must_be_outside_source_root')
    raw = read_snapshot(source, source_root)
    route_format(source.relative_path, source.file_format, raw)
    # Pin verified bytes before pipeline rereads input; avoid source mutation races.
    pinned = output / 'source.pdf'
    with pinned.open('xb') as stream:
        stream.write(raw)
    extract_pdf(pinned, output / 'native', config, page_indices=page_indices)
    canonical = output / 'native' / 'canonical.json'
    from ..models import Document, DocumentStatus
    from ..validate import validate_document
    document = Document.model_validate_json(canonical.read_bytes())
    if document.source.file_hash != source.content_hash:
        raise ValueError('pdf_canonical_source_hash_mismatch')
    verification = output / 'native' / 'verification-report.json'
    reasons = ['pdf_native_review_policy_preserved', 'document_window_only']
    failed = document.quality.status == DocumentStatus.FAILED or bool(document.quality.validation_errors)
    if validate_document(document):
        failed = True
        reasons.append('pdf_canonical_validation_failed')
    if failed:
        reasons.append('pdf_native_failed')
    if verification.is_file():
        report = VerificationReport.model_validate_json(verification.read_bytes())
        if report.document_id != document.document_id:
            raise ValueError('pdf_verification_document_mismatch')
        if report.outcome == VerificationOutcome.FAIL:
            failed = True
            reasons.append('pdf_verification_failed')
    else:
        failed = True
        reasons.append('pdf_verification_missing')
    return ParseResult(source=source, format='pdf', status='failed' if failed else 'review_required',
                       canonical_path='native/canonical.json',
                       canonical_sha256=sha256(canonical.read_bytes()).hexdigest(),
                       canonical_schema_version=document.schema_version,
                       verification_path='native/verification-report.json' if verification.is_file() else None,
                       verification_sha256=sha256(verification.read_bytes()).hexdigest() if verification.is_file() else None,
                       reason_codes=reasons,
                       requirement_status='native_pdf_pipeline')
