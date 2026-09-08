from __future__ import annotations

from pdf_extraction.models import (
    Block,
    BlockType,
    BoundingBox,
    Document,
    DocumentQuality,
    DocumentStatus,
    Page,
    ProcessingMetadata,
    Requirement,
    RequirementAction,
    RequirementClause,
    RequirementModality,
    RequirementSemanticFragment,
    RequirementSemanticInput,
    RequirementScopeRef,
    RequirementSourceRegion,
    RequirementStatus,
    RequirementTextAnchor,
    RequirementThreshold,
    SourceMetadata,
)
from pdf_extraction.validate import validate_document


def _document() -> Document:
    return Document(
        document_id="sha256:test",
        source=SourceMetadata(
            file_name="test.pdf",
            file_hash="test",
            file_size=1,
            page_count=1,
            encrypted=False,
        ),
        processing=ProcessingMetadata(
            pipeline_version="test",
            config_hash="config",
        ),
        pages=[
            Page(
                page_index=0,
                width=612,
                height=792,
                rotation=0,
                image_ref="pages/page-0001.png",
                native_text_coverage=1,
                image_coverage=0,
                page_kind="born_digital",
            )
        ],
        root_block_ids=["document"],
        blocks={"document": Block(id="document", type=BlockType.DOCUMENT)},
        quality=DocumentQuality(
            status=DocumentStatus.ACCEPTED,
            input_page_count=1,
            processed_page_count=1,
        ),
    )


def _requirement(status: RequirementStatus = RequirementStatus.ACCEPTED) -> Requirement:
    return Requirement(
        requirement_id="1.2.2",
        status=status,
        requirement_form="audit_matrix",
        source_document="test.pdf",
        source_authority="ASC standard",
        criterion_path=["Principle 1", "Criterion 1.2"],
        language="en",
        indicator_text="The farm shall appoint at least one manager.",
        requirement_value="Yes",
        normative_text=(
            "Indicator: The farm shall appoint at least one manager.\n"
            "Requirement: Yes"
        ),
        normative_subjects=["the farm"],
        applicability=["All"],
        modalities=[
            RequirementModality(
                token="shall", type="obligation", scope="appoint a manager"
            )
        ],
        clauses=[
            RequirementClause(
                clause_id="1.2.2-c1", text="appoint at least one manager"
            )
        ],
        thresholds=[
            RequirementThreshold(
                raw_text="at least one",
                operator="gte",
                normalized_value=1,
                unit="manager",
                applies_to="appointed managers",
                basis="explicit",
                source_segment_ids=["seg-1"],
                scope_ref=RequirementScopeRef(
                    kind="source_span",
                    target="normative_text",
                    anchors=[RequirementTextAnchor(
                        source_segment_id="seg-1",
                        start_char=36,
                        end_char=43,
                        text="manager",
                    )],
                ),
            )
        ],
        client_actions=[
            RequirementAction(
                marker="a",
                text="Keep appointment records.",
                source_segment_ids=["seg-client"],
            )
        ],
        auditor_actions=[
            RequirementAction(
                marker="A",
                text="Verify appointment records.",
                source_segment_ids=["seg-auditor"],
            )
        ],
        source_segments=[
            RequirementSourceRegion(
                segment_id="seg-id",
                page_index=0,
                page_number=1,
                bbox=BoundingBox(x0=10, y0=10, x1=60, y1=19),
                role="requirement_id",
                source_text="1.2.2",
                native_text="1.2.2",
                resolved_text="1.2.2",
                native_object_refs=["native-id"],
            ),
            RequirementSourceRegion(
                segment_id="seg-1",
                page_index=0,
                page_number=1,
                bbox=BoundingBox(x0=10, y0=20, x1=500, y1=80),
                role="normative_text",
                source_text="The farm shall appoint at least one manager.",
                native_text="The farm shall appoint at least one manager.",
                resolved_text="The farm shall appoint at least one manager.",
                native_object_refs=["native-1"],
            ),
            RequirementSourceRegion(
                segment_id="seg-client",
                page_index=0,
                bbox=BoundingBox(x0=10, y0=90, x1=500, y1=120),
                role="client_action",
                source_text="Keep appointment records.",
                ocr_text="Keep appointment records.",
                resolved_text="Keep appointment records.",
                ocr_word_ids=["ocr-1"],
            ),
            RequirementSourceRegion(
                segment_id="seg-auditor",
                page_index=0,
                bbox=BoundingBox(x0=10, y0=130, x1=500, y1=160),
                role="auditor_action",
                source_text="Verify appointment records.",
                native_text="Verify appointment records.",
                resolved_text="Verify appointment records.",
                native_object_refs=["native-auditor"],
            ),
        ],
        semantic_input=RequirementSemanticInput(
            generator_version="role-aware-semantic-input-v1",
            core_fragments=[RequirementSemanticFragment(
                role="normative_text",
                text="The farm shall appoint at least one manager.",
                source_segment_ids=["seg-1"],
            )],
            fingerprint="a" * 64,
        ),
        validation_flags=["client_auditor_separation_checked"],
    )


def test_requirement_v15_round_trip_preserves_semantics_and_inline_provenance() -> None:
    document = _document()
    document.requirements.append(_requirement())

    payload = document.model_dump(mode="json")
    loaded = Document.model_validate(payload)
    requirement = loaded.requirements[0]

    assert loaded.schema_version == "1.5"
    assert requirement.status == RequirementStatus.ACCEPTED
    assert requirement.thresholds[0].normalized_value == 1
    assert requirement.thresholds[0].scope_ref is not None
    assert requirement.thresholds[0].scope_ref.anchors[0].text == "manager"
    assert requirement.client_actions[0].text == "Keep appointment records."
    assert requirement.auditor_actions[0].text == "Verify appointment records."
    source_by_id = {item.segment_id: item for item in requirement.source_segments}
    assert source_by_id["seg-1"].native_object_refs == ["native-1"]
    assert source_by_id["seg-client"].ocr_word_ids == ["ocr-1"]
    assert requirement.semantic_input is not None
    assert requirement.semantic_input.core_fragments[0].source_segment_ids == [
        "seg-1"
    ]
    assert requirement.normative_subject_evidence == []
    assert requirement.applicability_evidence == []


def test_all_requirement_decision_states_are_supported() -> None:
    assert {
        _requirement(status).status
        for status in RequirementStatus
    } == {
        RequirementStatus.ACCEPTED,
        RequirementStatus.REVIEW_REQUIRED,
        RequirementStatus.ABSTAIN,
    }


def test_document_v15_defaults_to_no_requirements() -> None:
    document = _document()
    assert document.schema_version == "1.5"
    assert document.requirements == []


def test_requirement_provenance_passes_canonical_validation() -> None:
    document = _document()
    document.requirements.append(_requirement())
    assert validate_document(document) == []


def test_requirement_scope_anchor_must_match_exact_source_substring() -> None:
    document = _document()
    requirement = _requirement()
    requirement.thresholds[0].scope_ref.anchors[0].text = "managers"
    document.requirements.append(requirement)

    errors = validate_document(document)

    assert (
        "Requirement 1.2.2 threshold scope anchor text mismatch: seg-1"
        in errors
    )


def test_requirement_scope_anchor_rejects_missing_source_region() -> None:
    document = _document()
    requirement = _requirement()
    requirement.thresholds[0].scope_ref.anchors[0].source_segment_id = "missing"
    document.requirements.append(requirement)

    errors = validate_document(document)

    assert (
        "Requirement 1.2.2 threshold scope anchor references missing Requirement "
        "source region: missing" in errors
    )


def _partial_requirement_document() -> Document:
    """One emitted page backed by a three-page source document."""

    document = _document()
    document.source.page_count = 3
    document.quality.input_page_count = 3
    document.processing.processed_page_indices = [2]
    document.pages[0].page_index = 2

    requirement = _requirement()
    for segment in requirement.source_segments:
        segment.page_index = 2
        if segment.page_number is not None:
            segment.page_number = 3
    requirement.source_segments.append(RequirementSourceRegion(
        segment_id="seg-criterion-heading",
        page_index=0,
        page_number=1,
        bbox=BoundingBox(x0=10, y0=20, x1=300, y1=40),
        role="criterion_heading",
        source_text="Criterion 1.2 - Management Systems",
        native_text="Criterion 1.2 - Management Systems",
        resolved_text="Criterion 1.2 - Management Systems",
        native_object_refs=["native-heading"],
    ))
    document.requirements.append(requirement)
    return document


def test_partial_run_allows_source_faithful_out_of_window_hierarchy_support() -> None:
    document = _partial_requirement_document()

    assert validate_document(document) == []


def test_partial_run_allows_linked_out_of_window_footnote_support() -> None:
    document = _partial_requirement_document()
    document.requirements[0].source_segments.append(RequirementSourceRegion(
        segment_id="seg-footnote",
        page_index=0,
        page_number=1,
        bbox=BoundingBox(x0=10, y0=700, x1=300, y1=720),
        role="footnote",
        source_text="[77] Supporting transparency note.",
        native_text="[77] Supporting transparency note.",
        resolved_text="[77] Supporting transparency note.",
        native_object_refs=["native-footnote"],
    ))

    assert validate_document(document) == []


def test_partial_run_still_rejects_out_of_window_direct_requirement_evidence() -> None:
    document = _partial_requirement_document()
    normative = next(
        segment
        for segment in document.requirements[0].source_segments
        if segment.role == "normative_text"
    )
    normative.page_index = 1
    normative.page_number = 2

    errors = validate_document(document)

    assert (
        "Requirement source page is outside processed pages: seg-1"
        in errors
    )


def test_partial_run_rejects_hierarchy_support_outside_source_document() -> None:
    document = _partial_requirement_document()
    heading = next(
        segment
        for segment in document.requirements[0].source_segments
        if segment.role == "criterion_heading"
    )
    heading.page_index = 3
    heading.page_number = 4

    errors = validate_document(document)

    assert (
        "Requirement source page is outside source document: "
        "seg-criterion-heading"
        in errors
    )


def test_document_can_load_v12_json_without_requirements() -> None:
    payload = _document().model_dump(mode="json")
    payload["schema_version"] = "1.2"
    payload.pop("requirements")

    loaded = Document.model_validate(payload)

    assert loaded.schema_version == "1.2"
    assert loaded.requirements == []


def test_document_can_load_v13_requirement_without_semantic_input() -> None:
    document = _document()
    document.requirements.append(_requirement())
    payload = document.model_dump(mode="json")
    payload["schema_version"] = "1.3"
    payload["requirements"][0].pop("semantic_input")

    loaded = Document.model_validate(payload)

    assert loaded.schema_version == "1.3"
    assert loaded.requirements[0].semantic_input is None
