"""Scope proposals preserve exceptions without treating examples as rules."""
import pytest
from pdf_extraction.domains.requirements.classification import propose
from pdf_extraction.domains.requirements.applicability import signals

@pytest.mark.parametrize('body,expected', [('These requirements are applicable regardless of site depth.', True), ('These requirements apply to offshore farms.', True), ('The criterion does not apply to closed systems.', True), ('The standards are not applicable to inland farms.', True), ('Farms are exempt from the requirements if all waste is collected.', True), ('A site is not exempt from standards under Criterion 2.1.', True), ('The rule applies when discharge occurs.', True), ('These provisions apply within the defined monitoring zone.', True), ('An example states that these requirements apply to offshore farms.', False), ('Whether these requirements apply to offshore farms remains unresolved.', False), ('Do these requirements apply to offshore farms?', False), ('The report says that these requirements apply to offshore farms.', False), ('Previously these requirements apply to offshore farms.', False), ('These proposed requirements apply to offshore farms.', False), ('The term "requirements apply to offshore farms" illustrates applicability.', False), ('Which requirements apply to offshore farms is unclear.', False), ('These criteria might apply to offshore farms.', False), ('Farms are exempt from fees.', False), ('Requirements are discussed in Appendix A.', False), ('This chapter describes why farms are exempt from the requirements.', False), ('Example:\nThese requirements apply to offshore farms.', False), ('A report describes the previous regime.\nFarms are exempt from the requirements.', False), ('“Applicability. These requirements apply to farms.”', False)])
def test_scope_statement_and_context_counterexamples(body,expected):
    u={'kind':'source_text','fields':{'body':body},'references':[{'page_index':2,'bbox':[10,20,400,80]}]}
    result=propose(u)
    assert (result['classification']=='requirement') is expected
    assert result['parts'][0]['confidence'] is None
    assert result['parts'][0]['evidence']==u['references']
    for e in result['scope_evidence']:
        assert body[e['start']:e['end']]==e['text']
        assert e['text'] in e['clause']


def test_precise_offsets_keep_decimal_and_newline_context():
    body='Section 2.1.\nThese requirements apply to offshore farms.\nFarms are exempt from the standards if waste is collected.'
    spans=signals(body)
    assert len(spans)==2
    assert all(body[e['start']:e['end']]==e['text'] for e in spans)


def test_assembly_keeps_context_even_with_applicability_wording():
    u={'kind':'source_table_assembly','fields':{'body':'These requirements apply to farms.'}}
    assert propose(u)['classification']=='context'


def test_earlier_relative_clause_does_not_hide_explicit_later_scope():
    body='A proxy, which indicates water quality, supports monitoring. These requirements apply to all sites.'
    assert propose({'kind':'source_text','fields':{'body':body}})['classification']=='requirement'


def test_multiline_unresolved_question_does_not_become_a_scope_statement():
    body='Whether\nthese requirements apply to farms remains unresolved.'
    assert propose({'kind':'source_text','fields':{'body':body}})['classification']=='undetermined'
