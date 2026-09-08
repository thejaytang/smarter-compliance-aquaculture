from pdf_extraction.domains.requirements.semantics import analyze_requirement_semantics
from pdf_extraction.domains.requirements.canonical import _context_applies_to


def test_explicit_in_cases_where_attaches_to_its_own_sentence():
    text = ('The operator shall keep records (see Section 2.5.1). '
            'In cases where a fault is detected, the operator shall stop the pump.')
    result = analyze_requirement_semantics(text)
    assert len(result.conditions) == 1
    condition = result.conditions[0]
    assert condition.clause.text == 'In cases where a fault is detected'
    assert not condition.ambiguous
    assert _context_applies_to(result, condition) == 'stop the pump'
    assert text[condition.clause.start:condition.clause.end] == condition.clause.text


def test_trailing_condition_still_attaches_to_previous_action():
    result = analyze_requirement_semantics('The operator shall stop the pump when a fault is detected.')
    assert _context_applies_to(result, result.conditions[0]) == 'stop the pump'


def test_relative_where_remains_uncertain():
    result = analyze_requirement_semantics('The operator shall inspect the area where fish are held.')
    assert result.conditions[0].ambiguous


def test_conditional_sentence_clauses_preserve_reference_and_full_source():
    from pdf_extraction.domains.requirements import NativeRequirement, TemplateFamily
    from pdf_extraction.domains.requirements.clauses import build_requirement_clauses
    from tests.domains.requirements.test_canonical_requirement_adapter import _span
    text = ('The operator shall keep records (see Section 2.5.1). '
            'In cases where a fault is detected, the operator shall stop the pump.')
    native = NativeRequirement(
        requirement_id='1.2.3', family=TemplateFamily.SINGLE_COLUMN_INDICATORS,
        normative_text=text, indicator_text=text, source_segments=[_span('normative_text', text)],
    )
    result = build_requirement_clauses(native, text)
    assert len(result.clauses) == 2
    assert ' '.join(c.text for c in result.clauses) == text
    assert all(c.parent_clause_id is None and c.joins_next is None for c in result.clauses)


def test_complete_exemption_sentence_preserves_source_punctuation():
    from pdf_extraction.domains.requirements.canonical import _leading_footnote_exemption
    text = "An exemption applies to sites under Section 2.5.1. Evidence is required."
    span = _leading_footnote_exemption(text, analyze_requirement_semantics(text))
    assert span.text == 'An exemption applies to sites under Section 2.5.1.'
    assert text[span.start:span.end] == span.text


def test_composite_appendix_reference_retains_list_but_not_explanatory_prose():
    text = 'The operator shall use Appendix 7 (7.2.1, 7.3.1, 7.7).'
    result = analyze_requirement_semantics(text)
    assert [r.span.text for r in result.cross_references] == ['Appendix 7 (7.2.1, 7.3.1, 7.7)']
    other = analyze_requirement_semantics('The operator shall use Appendix 7 (for further guidance).')
    assert [r.span.text for r in other.cross_references] == ['Appendix 7']
