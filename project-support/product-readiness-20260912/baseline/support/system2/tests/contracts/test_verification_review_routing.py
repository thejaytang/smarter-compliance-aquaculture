from pdf_extraction.config import VerificationSettings
from pdf_extraction.contracts.verification import (
    AtomicAssessment,
    EvidencePathRecord,
    ReviewDisposition,
)
from pdf_extraction.verification import route_atomic_assessment


def _assessment(**updates) -> AtomicAssessment:
    values = {
        "assessment_id": "assessment_001",
        "target_id": "requirement:2.1.1",
        "field_name": "modality",
        "criticality": "modality",
        "confidence": 0.995,
        "provenance_complete": True,
        "disagreement": False,
        "evidence_paths": [
            EvidencePathRecord(
                path_id="native_001",
                kind="native_object",
                source_refs=["native_word_001"],
                independent_from_generation=False,
            ),
            EvidencePathRecord(
                path_id="visual_001",
                kind="visual_ocr",
                source_refs=["page_001.png"],
                independent_from_generation=True,
            ),
        ],
    }
    values.update(updates)
    return AtomicAssessment(**values)


def test_high_confidence_atomic_judgment_can_be_auto_accepted() -> None:
    routed = route_atomic_assessment(_assessment(), VerificationSettings())

    assert routed.disposition == ReviewDisposition.AUTO_ACCEPT
    assert routed.review_threshold == 0.99
    assert routed.reason_codes == []


def test_low_confidence_is_routed_to_human_at_any_verification_depth() -> None:
    routed = route_atomic_assessment(
        _assessment(confidence=0.98),
        VerificationSettings(depth="internal"),
    )

    assert routed.disposition == ReviewDisposition.HUMAN_REVIEW
    assert "confidence_below_threshold" in routed.reason_codes


def test_disagreement_and_missing_provenance_force_review() -> None:
    routed = route_atomic_assessment(
        _assessment(disagreement=True, provenance_complete=False),
        VerificationSettings(depth="strong"),
    )

    assert routed.disposition == ReviewDisposition.HUMAN_REVIEW
    assert routed.reason_codes == [
        "evidence_disagreement",
        "provenance_incomplete",
    ]


def test_machine_depth_requires_its_promised_evidence_paths() -> None:
    routed = route_atomic_assessment(
        _assessment(evidence_paths=[]),
        VerificationSettings(depth="strong"),
    )

    assert routed.disposition == ReviewDisposition.HUMAN_REVIEW
    assert routed.reason_codes == [
        "source_evidence_missing",
        "independent_evidence_missing",
        "evidence_path_redundancy_missing",
    ]
