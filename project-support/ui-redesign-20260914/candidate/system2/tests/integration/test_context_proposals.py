"""Genre evidence may resolve context, but cannot override operative wording."""
import pytest
from pdf_extraction.domains.requirements.classification import propose

CITATION='Smith, A., Jones, B. and Green, C. 2020. Sediment monitoring. Marine Research Bulletin 12, 10–24. https://example.org/paper'
CONTACT='For any questions regarding the submission process, please contact help@example.org.'


def result(text,**fields):
    return propose(dict(kind='source_text',fields=dict(body=text,**fields),references=[{'page_index':0,'bbox':[1,1,20,20]}]))


@pytest.mark.parametrize('text,category',[(CITATION,'bibliographic_reference'),('10 '+CITATION,'bibliographic_reference'),(CONTACT,'support_contact'),('For queries about this portal, please contact support@example.org','support_contact')])
def test_located_complete_genre(text,category):
    p=result(text);assert p['classification']=='context'
    e=p['context_evidence'][0];assert e['category']==category
    assert text[e['start']:e['end']]==e['text']==text
    assert p['parts'][0]['confidence'] is None


@pytest.mark.parametrize('text',[CITATION+' Farms must retain records.',CONTACT+' Farms should retain records.',CONTACT.replace('please contact','you must contact'),'All farms must contact help@example.org.'])
def test_normative_content_keeps_priority(text):
    assert result(text)['classification']=='requirement'


@pytest.mark.parametrize('text',['Farms retain records.',
    'Contact help@example.org after a spill.',
    'For any questions regarding an incident, please contact help@example.org and submit a report.',
    CONTACT+' Complete the form before inspection.',
    'See '+CITATION,
    CITATION.replace('https://example.org/paper',''),
    CITATION.replace('example.org/paper','example.org/pa per'),
    CITATION+' Complete the inspection.',
    'Smith, A. 2020. Monitoring records due on 12/10/2020. https://example.org/portal'])
def test_incomplete_or_mixed_genres_abstain(text):
    assert result(text)['classification']=='undetermined'


def test_separate_operative_context_keeps_priority():
    assert result(CONTACT,context='Sites shall retain all submitted records.')['classification']=='requirement'
