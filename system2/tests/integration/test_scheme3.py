from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from reportlab.pdfgen import canvas

from pdf_extraction.api.app import create_app
from pdf_extraction.api.store import JobStore
from pdf_extraction.api.worker import run_once
from pdf_extraction.assemble.paragraph_assembler import assemble_paragraphs
from pdf_extraction.config import AppConfig, SecuritySettings
from pdf_extraction.derived import write_derived_artifacts
from pdf_extraction.ingest.preflight import UnsafePDFError, inspect_pdf_security
from pdf_extraction.models import (
    ArtifactReference, Block, BlockQuality, BlockType, BoundingBox, CodeData, Document,
    DocumentQuality, DocumentStatus, EquationData, EvidenceSpan, Page, ProcessingMetadata,
    ProcessingStatus, Resolution, ResolutionStatus, ReviewItem, Segment, SourceMetadata, TextContent,
)
from pdf_extraction.ontology import map_ir_to_rdf, validate_graph
from pdf_extraction.parsers import parse_code
from pdf_extraction.parsers import PARSER_ROUTES
from pdf_extraction.regulatory_ir import extract_regulatory_ir
from pdf_extraction.release_gate import evaluate_release
from pdf_extraction.review import (
    PageLabelDecision, ReviewDecision, apply_review_decision, correct_page_label,
)
from pdf_extraction.validate import validate_document
from tests.support.paths import PROJECT_ROOT


def _text(value: str) -> TextContent:
    return TextContent(
        native_text=value, ocr_text=value, resolved_text=value,
        resolution=Resolution(selected_source="both", reason="agree", confidence=1),
    )


def _document(tmp_path: Path, *, pending_review: bool = False) -> Document:
    image = tmp_path / "page.png"
    Image.new("RGB", (300, 400), "white").save(image)
    equation_image = tmp_path / "equation.png"
    Image.new("RGB", (100, 30), "white").save(equation_image)
    document_block = Block(id="document", type=BlockType.DOCUMENT, children=["section"])
    section = Block(
        id="section", type=BlockType.SECTION, parent_id="document",
        children=["rule", "code", "equation", "footnote"],
    )
    blocks = {
        "document": document_block,
        "section": section,
        "rule": Block(
            id="rule", type=BlockType.PARAGRAPH, parent_id="section", order_in_parent=0,
            segments=[Segment(id="seg_rule", page_index=0, bbox=BoundingBox(x0=10, y0=10, x1=290, y1=80))],
            content=_text("The operator shall not exceed 5 mg when the alarm is active."),
            quality=BlockQuality(requires_review=pending_review),
        ),
        "code": Block(
            id="code", type=BlockType.CODE, parent_id="section", order_in_parent=1,
            segments=[Segment(id="seg_code", page_index=0, bbox=BoundingBox(x0=10, y0=90, x1=290, y1=160))],
            content=_text("def check(value):\n    return value <= 5"),
            code=CodeData(raw_text="def check(value):\n    return value <= 5", lines=["def check(value):", "    return value <= 5"], language="python"),
        ),
        "equation": Block(
            id="equation", type=BlockType.EQUATION, parent_id="section", order_in_parent=2,
            segments=[Segment(id="seg_eq", page_index=0, bbox=BoundingBox(x0=10, y0=170, x1=290, y1=230))],
            content=_text("x ≤ 5"),
            equation=EquationData(image_ref=str(equation_image), latex=r"x \leq 5", transcription_confidence=.9, backend="test"),
        ),
        "footnote": Block(
            id="footnote", type=BlockType.FOOTNOTE, parent_id="section", order_in_parent=3,
            segments=[Segment(id="seg_foot", page_index=0, bbox=BoundingBox(x0=10, y0=240, x1=290, y1=280))],
            content=_text("1 Local implementation guidance."),
        ),
    }
    review_items = [ReviewItem(
        id="review_rule", target_id="rule", reason="test", severity="warning"
    )] if pending_review else []
    return Document(
        document_id="sha256:test",
        source=SourceMetadata(
            file_name="test.pdf", file_hash="test", file_size=10,
            page_count=1, encrypted=False,
        ),
        processing=ProcessingMetadata(
            pipeline_version="0.3.0", config_hash="test", status=ProcessingStatus.ACCEPTED,
        ),
        pages=[Page(
            page_index=0, width=300, height=400, rotation=0,
            image_ref=str(image), native_text_coverage=.5, image_coverage=0,
            page_kind="born_digital", block_ids=["rule", "code", "equation", "footnote"],
            pdf_page_label="1", page_label_source="pdf", page_label_confidence=.98,
        )],
        root_block_ids=["document"], blocks=blocks,
        review_queue=["rule"] if pending_review else [], review_items=review_items,
        quality=DocumentQuality(
            status=DocumentStatus.REVIEW_REQUIRED if pending_review else DocumentStatus.ACCEPTED,
            input_page_count=1, processed_page_count=1,
            block_counts={kind: 1 for kind in ("document", "section", "paragraph", "code", "equation", "footnote")},
            provenance_anchor_coverage=1, human_review_rate=.1 if pending_review else 0,
        ),
    )


def _pdf(path: Path, pages: int = 1) -> None:
    pdf = canvas.Canvas(str(path), pagesize=(300, 400))
    for index in range(pages):
        pdf.drawString(30, 330, f"Page {index + 1}")
        pdf.drawString(30, 280, "The operator shall keep records for 5 years.")
        pdf.showPage()
    pdf.save()


def test_special_blocks_derived_exports_and_ontology(tmp_path: Path) -> None:
    document = _document(tmp_path)
    code, derived = parse_code("def f(x):\n    return x", True)
    assert code.language == "python" and derived.language == "python"
    assert set(PARSER_ROUTES) == set(BlockType)
    config = AppConfig()
    write_derived_artifacts(document, tmp_path / "out", config)
    expected = {"markdown", "html", "xml", "jsonl", "rag_chunks", "overlay_manifest", "regulatory_ir", "rdf", "shacl_report"}
    assert expected <= set(document.artifacts)
    ir = extract_regulatory_ir(document)
    assert len(ir.statements) == 1
    statement = ir.statements[0]
    assert statement.modality == "shall not"
    assert statement.threshold == "5 mg"
    assert statement.source_block_ids == ["rule"]
    assert statement.source_segment_ids == ["seg_rule"]
    graph = map_ir_to_rdf(ir, config.ontology.namespace)
    assert validate_graph(graph, config.ontology.namespace).conforms
    assert not validate_document(document)


def test_numbered_list_items_are_not_cross_page_paragraphs(tmp_path: Path) -> None:
    pages = [
        Page(page_index=0, width=300, height=400, rotation=0, image_ref="p1.png", native_text_coverage=1, image_coverage=0, page_kind="born_digital", block_ids=["left"]),
        Page(page_index=1, width=300, height=400, rotation=0, image_ref="p2.png", native_text_coverage=1, image_coverage=0, page_kind="born_digital", block_ids=["right"]),
    ]
    section = Block(id="section", type=BlockType.SECTION, children=["left", "right"])
    left = Block(id="left", type=BlockType.LIST, parent_id="section", segments=[Segment(id="sl", page_index=0, bbox=BoundingBox(x0=20, y0=350, x1=280, y1=390))], content=_text("d) Does the rule apply?"))
    right = Block(id="right", type=BlockType.LIST, parent_id="section", segments=[Segment(id="sr", page_index=1, bbox=BoundingBox(x0=20, y0=10, x1=280, y1=40))], content=_text("e) Is the exception valid?"))
    blocks = {block.id: block for block in (section, left, right)}
    assert assemble_paragraphs(blocks, pages, AppConfig().assembly) == []
    assert "left" in blocks and "right" in blocks


def test_review_is_append_only_and_regenerates_outputs(tmp_path: Path) -> None:
    output = tmp_path / "out"
    output.mkdir()
    document = _document(tmp_path, pending_review=True)
    write_derived_artifacts(document, output, AppConfig())
    canonical = output / "canonical.json"
    canonical.write_text(document.model_dump_json(indent=2), encoding="utf-8")
    reviewed = apply_review_decision(canonical, ReviewDecision(
        actor="tester", action="modify", target_type="block", target_id="rule",
        new_value="The operator shall not exceed 4 mg.", reason="verified against source",
    ), AppConfig())
    assert reviewed.revision == 1
    assert reviewed.audit_events[0].previous_value_hash
    assert reviewed.blocks["rule"].content.resolved_text.endswith("4 mg.")
    assert (output / "audit-events.jsonl").read_text().count("audit_00000001") == 1
    assert "4 mg" in (output / "regulatory-ir.json").read_text()
    corrected = correct_page_label(canonical, PageLabelDecision(
        actor="tester", page_index=0, label="A-1", reason="printed label verified",
    ), AppConfig())
    assert corrected.pages[0].page_label_source == "human"
    assert corrected.pages[0].page_label_correction == "A-1"
    assert corrected.audit_events[-1].target_type == "page_label"


def test_span_review_resolves_owner_block(tmp_path: Path) -> None:
    output = tmp_path / "span-output"
    output.mkdir()
    document = _document(tmp_path)
    block = document.blocks["rule"]
    block.content = TextContent(
        native_text="The limit shall be 5 mg.", ocr_text="The limit shall be S mg.",
        resolved_text=None, requires_human_review=True,
        resolution_status=ResolutionStatus.AMBIGUOUS,
        resolution=Resolution(selected_source="none", reason="conflict", confidence=0),
    )
    block.quality.requires_review = True
    block.quality.issues = ["critical_text_conflict"]
    document.evidence_spans = {"span_limit": EvidenceSpan(
        id="span_limit", block_id="rule", segment_id="seg_rule", page_index=0,
        bbox=BoundingBox(x0=100, y0=10, x1=120, y1=30), native_text="5",
        ocr_text="S", resolved_text=None, criticality="numeric",
        resolution_status=ResolutionStatus.AMBIGUOUS, confidence=0,
        requires_human_review=True,
    )}
    document.review_items = [ReviewItem(
        id="review_span", target_id="rule", reason="unresolved_critical_span",
        severity="critical",
    )]
    document.review_queue = ["rule"]
    document.quality.status = DocumentStatus.REVIEW_REQUIRED
    canonical = output / "canonical.json"
    canonical.write_text(document.model_dump_json(indent=2), encoding="utf-8")
    reviewed = apply_review_decision(canonical, ReviewDecision(
        actor="tester", action="modify", target_type="span", target_id="span_limit",
        new_value="5",
    ), AppConfig())
    assert reviewed.blocks["rule"].content.resolution_status == ResolutionStatus.HUMAN_CONFIRMED
    assert reviewed.blocks["rule"].content.resolved_text == "The limit shall be 5 mg."
    assert reviewed.review_queue == []


def test_security_limits_and_persistent_worker(tmp_path: Path) -> None:
    two_pages = tmp_path / "two-pages.pdf"
    _pdf(two_pages, pages=2)
    with pytest.raises(UnsafePDFError, match="page-count"):
        inspect_pdf_security(two_pages, SecuritySettings(max_pages=1))

    one_page = tmp_path / "one-page.pdf"
    _pdf(one_page)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "native_extraction:\n  backend: pypdf\nlayout:\n  backend: heuristic\nocr:\n  backend: tesseract\n",
        encoding="utf-8",
    )
    store = JobStore(tmp_path / "jobs.sqlite3")
    job = store.create(str(one_page), str(tmp_path / "job-output"), str(config_path))
    assert job.status == "queued"
    result = run_once(store)
    assert result and result.status in {"accepted", "review_required"}
    canonical_path = tmp_path / "job-output/canonical.json"
    verification_path = tmp_path / "job-output/verification-report.json"
    assert canonical_path.is_file()
    assert verification_path.is_file()
    canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
    verification = json.loads(verification_path.read_text(encoding="utf-8"))
    assert "verification_report" in canonical["artifacts"]
    assert verification["depth"] == "source"
    assert all(
        assessment["review_threshold"] is not None
        and assessment["disposition"] in {"auto_accept", "human_review"}
        for assessment in verification["assessments"]
    )
    assert {event["status"] for event in store.events(job.id)} >= {"queued", "preflight", "parsing", "validating"}


def test_rest_api_and_release_gate(tmp_path: Path) -> None:
    pdf = tmp_path / "source.pdf"
    _pdf(pdf)
    config_path = tmp_path / "config.yaml"
    config_path.write_text("{}", encoding="utf-8")
    app = create_app(tmp_path / "api.sqlite3", PROJECT_ROOT / "ui")
    client = TestClient(app)
    response = client.post("/documents", json={
        "input_path": str(pdf), "output_dir": str(tmp_path / "api-output"),
        "config_path": str(config_path),
    })
    assert response.status_code == 202
    job_id = response.json()["id"]
    assert client.get(f"/jobs/{job_id}").json()["status"] == "queued"
    assert client.get(f"/review/{job_id}").status_code == 200

    document = _document(tmp_path)
    output = tmp_path / "release"
    write_derived_artifacts(document, output, AppConfig())
    security_report = output / "security-report.json"
    security_report.write_text(json.dumps({
        "passed": True,
        "policy": {"document_content_sent_externally": False},
    }), encoding="utf-8")
    document.artifacts["security_report"] = ArtifactReference(
        path=str(security_report), media_type="application/json"
    )
    report = evaluate_release(
        document, AppConfig(),
        performance={"within_budget": True},
        evaluation={"aggregate": {"accepted_result_precision": 1.0}, "failures": []},
    )
    assert report["passed"], report
