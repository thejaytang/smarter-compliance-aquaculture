"""Negative controls for source-fidelity decisions, on isolated documents only."""
import json

import pytest

from pdf_extraction.config import AppConfig
from pdf_extraction.delivery import write_derived_artifacts
from pdf_extraction.models import (
    DocumentStatus, EvidenceSpan, ResolutionStatus, ReviewItem,
)
from pdf_extraction.review import ReviewDecision, apply_review_decision
from tests.integration.test_scheme3 import _document


def save_document(tmp_path, *, span=False):
    doc = _document(tmp_path, pending_review=True)
    doc.review_items[0].reason = 'unresolved_critical_span' if span else 'critical_text_conflict'
    block = doc.blocks['rule']
    block.quality.issues = [doc.review_items[0].reason]
    if span:
        doc.evidence_spans['span_limit'] = EvidenceSpan(
            id='span_limit', block_id='rule', segment_id='seg_rule', page_index=0,
            bbox=block.segments[0].bbox, native_text='5', ocr_text='S',
            criticality='numeric', resolution_status=ResolutionStatus.AMBIGUOUS,
            confidence=0, requires_human_review=True,
        )
        block.content.resolved_text = None
        block.content.resolution_status = ResolutionStatus.AMBIGUOUS
        block.content.requires_human_review = True
    output = tmp_path / 'out'
    output.mkdir()
    path = output / 'canonical.json'
    path.write_text(doc.model_dump_json())
    return doc, path


@pytest.mark.parametrize('action', ['reject', 'unreadable'])
@pytest.mark.parametrize('kind', ['block', 'span'])
def test_negative_decision_retains_fidelity_blocker(tmp_path, action, kind):
    before, path = save_document(tmp_path, span=kind == 'span')
    result = apply_review_decision(path, ReviewDecision(
        actor='tester', action=action, target_type=kind,
        target_id='rule' if kind == 'block' else 'span_limit',
    ), AppConfig())
    assert result.quality.status == DocumentStatus.REVIEW_REQUIRED
    assert 'rule' in result.review_queue
    assert result.blocks['rule'].quality.requires_review
    assert result.blocks['rule'].content.resolution_status != ResolutionStatus.HUMAN_CONFIRMED
    assert result.audit_events[-1].action == action
    assert result.blocks['rule'].content.native_text == before.blocks['rule'].content.native_text
    report = json.loads((path.parent / 'quality-report.json').read_text())
    assert report['status'] == 'review_required'


def test_text_correction_does_not_close_structure_review(tmp_path):
    doc, path = save_document(tmp_path)
    doc.review_items.append(ReviewItem(
        id='structure', target_id='rule', reason='block_quality:low_table_structure',
        severity='critical',
    ))
    doc.blocks['rule'].quality.issues.append('low_table_structure')
    path.write_text(doc.model_dump_json())
    result = apply_review_decision(path, ReviewDecision(
        actor='tester', action='modify', target_type='block', target_id='rule',
        new_value='The operator shall not exceed 4 mg.',
    ), AppConfig())
    assert next(i for i in result.review_items if i.id == 'structure').status == 'pending'
    assert result.blocks['rule'].quality.requires_review
    assert result.quality.status == DocumentStatus.REVIEW_REQUIRED


def test_export_cannot_promote_failed_document(tmp_path):
    doc = _document(tmp_path)
    doc.quality.status = DocumentStatus.FAILED
    doc.quality.validation_errors = ['retained_source_failure']
    output = tmp_path / 'out'
    write_derived_artifacts(doc, output, AppConfig())
    assert doc.quality.status == DocumentStatus.FAILED
    assert json.loads((output / 'quality-report.json').read_text())['status'] == 'failed'


def test_blank_actor_rejected():
    with pytest.raises(ValueError):
        ReviewDecision(actor='  ', action='accept', target_type='block', target_id='rule')


def test_repeated_span_token_does_not_guess_first_occurrence(tmp_path):
    doc, path = save_document(tmp_path, span=True)
    doc.blocks['rule'].content.native_text = '5 mg for 5 days.'
    path.write_text(doc.model_dump_json())
    result = apply_review_decision(path, ReviewDecision(
        actor='tester', action='modify', target_type='span', target_id='span_limit', new_value='4',
    ), AppConfig())
    assert result.blocks['rule'].content.resolved_text is None
    assert 'rule' in result.review_queue


@pytest.mark.parametrize('action', ['reject', 'unreadable'])
def test_cell_negative_decision_preserves_owner_review(tmp_path, action):
    from pdf_extraction.models import BlockType, TableCell, TableData
    doc, path = save_document(tmp_path)
    block = doc.blocks['rule']
    block.type = BlockType.TABLE
    block.table = TableData(row_count=1, column_count=1, parser_backend='test', cells=[
        TableCell(id='cell', row=0, column=0, bbox=block.segments[0].bbox, content=block.content),
    ])
    block.content = None
    doc.review_items[0].reason = 'table_cell_text_conflict'
    path.write_text(doc.model_dump_json())
    result = apply_review_decision(path, ReviewDecision(
        actor='tester', action=action, target_type='cell', target_id='cell',
    ), AppConfig())
    assert result.quality.status == DocumentStatus.REVIEW_REQUIRED
    assert 'rule' in result.review_queue


def test_text_edit_invalidates_previous_requirement_semantics(tmp_path):
    from pdf_extraction.models import Requirement, RequirementSourceRegion, RequirementStatus
    doc, path = save_document(tmp_path)
    block = doc.blocks['rule']
    doc.requirements = [Requirement(
        requirement_id='1.1', requirement_form='prose_clause', language='en',
        normative_text=block.content.native_text, status=RequirementStatus.ACCEPTED,
        source_segments=[RequirementSourceRegion(
            segment_id='requirement-source', page_index=0, bbox=block.segments[0].bbox,
            role='normative_text', source_text=block.content.native_text,
        )],
    )]
    path.write_text(doc.model_dump_json())
    result = apply_review_decision(path, ReviewDecision(
        actor='tester', action='modify', target_type='block', target_id='rule',
        new_value='The operator shall not exceed 4 mg.',
    ), AppConfig())
    assert result.requirements[0].status == RequirementStatus.REVIEW_REQUIRED
    assert 'requirement:1.1' in result.review_queue


def test_explicit_span_confirmation_updates_linked_conflict(tmp_path):
    from pdf_extraction.models import Conflict
    doc, path = save_document(tmp_path, span=True)
    doc.conflicts = [Conflict(
        id='conflict', block_id='rule', native_value='5', ocr_value='S',
        conflict_type='numeric', severity='critical', status='review_required',
        evidence_span_ids=['span_limit'],
    )]
    path.write_text(doc.model_dump_json())
    result = apply_review_decision(path, ReviewDecision(
        actor='tester', action='modify', target_type='span', target_id='span_limit', new_value='5',
    ), AppConfig())
    assert result.conflicts[0].resolution_status == ResolutionStatus.HUMAN_CONFIRMED
    assert 'rule' not in result.review_queue
