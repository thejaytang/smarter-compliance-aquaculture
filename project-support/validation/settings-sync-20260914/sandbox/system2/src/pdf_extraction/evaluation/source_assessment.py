"""Evaluate a bound, exhaustive source-error adjudication, not token bags.

File declarations do not authenticate an independent human review. This entry
produces diagnostic metrics only; the shared-workbench reference receipt and
sample-qualification gates remain necessary for independent acceptance.
"""
from collections import Counter
from ..contracts.hashing import digest

CATEGORIES = frozenset({'text_omission', 'text_error', 'extra_text', 'critical_token',
    'reading_order', 'table_content', 'table_grid', 'footnote_link', 'cross_page_link',
    'source_link', 'heading_hierarchy', 'figure_preservation'})
DIMENSIONS = {'content', 'structure', 'relationships'}


def indexed(values, label):
    result = {}
    for value in values:
        if not isinstance(value, dict) or not isinstance(value.get('id'), str) or not value['id']:
            raise ValueError('invalid_'+label+'_identity')
        if value['id'] in result:
            raise ValueError('duplicate_'+label+'_identity')
        result[value['id']] = value
    return result


def ratio(numerator, denominator):
    return numerator/denominator if denominator else None


def evaluate(reference, assessment, records, verification, *, source_sha256):
    """Return unknown metrics for partial review; reject mismatched evidence.

    Error truth may include original regions with no output or machine finding.
    Only explicitly adjudicated findings detect errors. Unverified scope is a
    separate workload count and never receives automatic recall credit.
    """
    if reference.get('schema') != 'pdf-source-reference/1' or assessment.get('schema') != 'pdf-source-assessment/1':
        raise ValueError('unsupported_reference_or_assessment_schema')
    if assessment.get('evidence_class') not in {'natural', 'seeded', 'synthetic'}:
        raise ValueError('declare_natural_seeded_or_synthetic_evidence')
    if any(value.get('source_sha256') != source_sha256 for value in (reference, assessment, verification)):
        raise ValueError('source_binding_mismatch')
    if assessment.get('reference_sha256') != digest(reference):
        raise ValueError('reference_binding_mismatch')
    if assessment.get('records_sha256') != digest(records) or verification.get('input_sha256') != digest(records):
        raise ValueError('output_binding_mismatch')
    if assessment.get('verification_sha256') != digest(verification):
        raise ValueError('verification_binding_mismatch')
    pages = reference.get('pages', [])
    if (not pages or any(type(p) is not int or p < 0 for p in pages) or len(set(pages)) != len(pages)):
        raise ValueError('invalid_reference_page_scope')
    if len(pages) != 1 or type(verification.get('page_index')) is not int or pages[0] != verification['page_index']:
        raise ValueError('assessment_must_match_the_single_frozen_page_check')
    support = reference.get('supporting_pages', [])
    if any(type(p) is not int or p < 0 or p in pages for p in support) or len(set(support)) != len(support):
        raise ValueError('invalid_supporting_page_scope')
    outputs = indexed(records, 'output')
    regions = indexed(reference.get('regions', []), 'reference_region')
    errors = indexed(assessment.get('errors', []), 'error')
    findings = indexed(verification.get('findings', []), 'finding')
    decisions = indexed(assessment.get('finding_decisions', []), 'finding_decision')
    for region in regions.values():
        b = region.get('bbox')
        if region.get('page_index') not in pages+support or not isinstance(b, list) or len(b) != 4:
            raise ValueError('invalid_reference_region')
        import math
        if (any(type(v) not in (int,float) or not math.isfinite(v) for v in b)
                or not 0 <= b[0] < b[2] or not 0 <= b[1] < b[3]):
            raise ValueError('invalid_reference_region_box')
    for error in errors.values():
        if error.get('category') not in CATEGORIES or error.get('severity') not in {'critical', 'major', 'minor'}:
            raise ValueError('invalid_error_category_or_severity')
        if error['category'] == 'critical_token' and error['severity'] != 'critical':
            raise ValueError('critical_token_cannot_be_downgraded')
        r, o = error.get('region_ids', []), error.get('output_ids', [])
        if not (r or o) or not set(r) <= regions.keys() or not set(o) <= outputs.keys():
            raise ValueError('error_evidence_reference_missing')
        if not any(regions[i]['page_index'] in pages for i in r) and not any(
                ref.get('page_index') in pages for i in o for ref in outputs[i].get('references', [])):
            raise ValueError('error_outside_evaluated_page')
        if not str(error.get('explanation', '')).strip():
            raise ValueError('error_explanation_required')
    if not decisions.keys() <= findings.keys():
        raise ValueError('finding_decision_not_in_frozen_report')
    detected, duplicates = set(), []
    for decision in decisions.values():
        state, ids = decision.get('verdict'), decision.get('error_ids', [])
        if state not in {'matched', 'false_positive', 'duplicate', 'unresolved'}:
            raise ValueError('invalid_finding_verdict')
        if len(ids) != len(set(ids)) or not set(ids) <= errors.keys():
            raise ValueError('invalid_matched_error_identity')
        if state in {'matched', 'duplicate'}:
            if not ids or decision.get('localization') not in {'correct', 'incorrect', 'unverified'}:
                raise ValueError('match_requires_errors_and_localization')
            if state == 'matched':
                if detected.intersection(ids):
                    raise ValueError('one_error_cannot_credit_multiple_findings_use_duplicate')
                detected.update(ids)
            else:
                duplicates.extend(ids)
        elif ids:
            raise ValueError('unmatched_finding_cannot_claim_errors')
    if not set(duplicates) <= detected:
        raise ValueError('duplicate_requires_a_primary_matched_finding')

    incomplete = []
    if reference.get('status') != 'frozen_candidate':incomplete.append('reference_not_frozen')
    survey = reference.get('page_survey', [])
    if (len(survey) != len(pages) or {p.get('page_index') for p in survey} != set(pages)
            or any(p.get('complete') is not True or set(p.get('dimensions', [])) != DIMENSIONS
                   or p.get('unverified_regions') for p in survey)):
        incomplete.append('original_page_survey_incomplete')
    if assessment.get('status') != 'complete':incomplete.append('assessment_not_complete')
    if set(assessment.get('reviewed_region_ids', [])) != regions.keys():incomplete.append('original_region_review_incomplete')
    if set(assessment.get('reviewed_output_ids', [])) != outputs.keys():incomplete.append('output_review_incomplete')
    if set(assessment.get('reviewed_dimensions', [])) != DIMENSIONS:incomplete.append('assessment_dimensions_incomplete')
    if decisions.keys() != findings.keys():incomplete.append('finding_adjudication_incomplete')
    if any(d['verdict'] == 'unresolved' for d in decisions.values()):incomplete.append('finding_adjudication_unresolved')
    if assessment.get('unresolved'):incomplete.append('assessment_has_unresolved_questions')
    report = dict(schema='pdf-source-assessment-report/1', evidence_class=assessment['evidence_class'],
        source_sha256=source_sha256, reference_sha256=digest(reference), assessment_sha256=digest(assessment),
        records_sha256=digest(records), verification_sha256=digest(verification), pages=pages,
        incomplete=incomplete, diagnostic_metrics=None, independent_metrics=None,
        qualification='File declarations do not establish independent human review, sample qualification or release authority.',
        independent_acceptance='not_assessed',
        counts=dict(reference_regions=len(regions), output_records=len(outputs), errors=len(errors), findings=len(findings),
                    unverified_scope_items=len(verification.get('unverified', []))),
        uncertainty=dict(population_generalization='not_established', confidence_interval=None,
                         reason='No independently qualified sampling design or human reference is authenticated by this file-only entry point.'))
    if incomplete:
        return report
    status = Counter(d['verdict'] for d in decisions.values())
    localized = {e for d in decisions.values() if d['verdict'] in {'matched','duplicate'}
                 and d['localization']=='correct' for e in d['error_ids']}
    by_category = {}
    for category in sorted(CATEGORIES):
        ids = {e['id'] for e in errors.values() if e['category'] == category}
        by_category[category] = dict(errors=len(ids), detected=len(ids & detected), missed=len(ids-detected),
                                    recall=ratio(len(ids & detected),len(ids)))
    report['diagnostic_metrics'] = dict(
        finding_relevance_precision=ratio(status['matched']+status['duplicate'],len(findings)),
        actionable_finding_precision=ratio(status['matched'],len(findings)),
        verifier_recall=ratio(len(detected),len(errors)),
        localized_error_recall=ratio(len(localized),len(errors)),
        false_positive_findings=status['false_positive'], duplicate_findings=status['duplicate'],
        missed_error_ids=sorted(errors.keys()-detected),
        critical_error_ids=sorted(e['id'] for e in errors.values() if e['severity']=='critical'),
        critical_miss_ids=sorted(e['id'] for e in errors.values() if e['severity']=='critical' and e['id'] not in detected),
        by_error_category=by_category)
    return report
