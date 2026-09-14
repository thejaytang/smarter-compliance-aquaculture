"""Source roles improve candidates without granting business acceptance."""
from copy import deepcopy
import json
import pytest

from pdf_extraction.domains.requirements.classification import propose
from pdf_extraction.domains.requirements.classification_evidence import indicator_row
from pdf_extraction.review.effective import resolve
from .test_two_stage_workflow import system,current,decide
from .test_pdf_repairs import table_units,get


def labelled_table():
    owner,row=table_units()
    table=json.loads(owner['original']['fields']['body'])
    table['row_count']=2
    headers=[]
    for index,c in enumerate(table['cells']):
        c.update(row=1,is_header=False)
        c['content']={'resolved_text':['Presence of a documented response plan','Yes'][index]}
        header=deepcopy(c);header.update(id='header-'+str(index),row=0,is_header=True,bbox=[index*100,0,(index+1)*100,10])
        header['content']={'resolved_text':['Indicator','Requirement'][index]};headers.append(header)
    table['cells']=headers+table['cells']
    owner['original']['fields']['body']=json.dumps(table)
    row['kind']='source_table_row';row['original']['fields']={}
    return owner,row


def row_view():
    owner,row=labelled_table()
    return resolve(row,{owner['id']:owner,row['id']:row})


def test_explicit_table_headers_pair_nominal_indicator_with_value():
    u=row_view();before=deepcopy(u);p=propose(u)
    assert p['classification']=='requirement'
    assert p['table_role_evidence']['requirement_value']=='Yes'
    assert {h['text'] for h in p['table_role_evidence']['headers']}=={'Indicator','Requirement'}
    assert p['parts'][0]['confidence'] is None and u==before
    assert {c['id'] for c in u['table']['cells']}=={'c0','c1'}


@pytest.mark.parametrize('mutate',[
    lambda u:u.pop('source_table_headers'),
    lambda u:u['source_table_headers'][1]['content'].update(resolved_text='Observed result'),
    lambda u:u['source_table_headers'][1].update(column=0),
    lambda u:u['source_table_headers'][1].update(row=2),
    lambda u:u['source_table_headers'][1].pop('bbox'),
    lambda u:u['source_table_headers'].append(deepcopy(u['source_table_headers'][0])),
    lambda u:u['table']['cells'][1]['content'].update(resolved_text=''),
    lambda u:u['table']['cells'][0]['content'].update(resolved_text='1.2.3'),
    lambda u:u['table']['cells'][0].update(column_span=2),
    lambda u:u['table']['cells'][1].update(row_span=2),
    lambda u:u['references'].pop(),
    lambda u:u['table'].pop('selected_row'),
])
def test_arbitrary_or_ambiguous_table_does_not_establish_role(mutate):
    u=row_view();mutate(u)
    assert indicator_row(u) is None
    assert propose(u)['classification']=='undetermined'


@pytest.mark.parametrize('text',[
    'Rationale - Farms must respect local ecosystems because these support healthy production.',
    'Rationale\nFarms shall understand how the policy protects ecosystems.',
    'How do I interpret this requirement? Sites shall retain evidence supporting their chosen method.',
])
def test_explicit_complete_context_does_not_create_formal_item(text):
    p=propose(dict(kind='source_text',fields={'body':text}))
    assert p['classification']=='context'
    assert p['source_role_evidence'] and p['matches']


@pytest.mark.parametrize('text',[
    'The rationale must be documented before approval.',
    'Rationale must be reviewed annually.',
    'Farms shall explain the rationale for their controls.',
])
def test_mentions_of_rationale_are_not_source_section_labels(text):
    assert propose(dict(kind='source_text',fields={'body':text}))['classification']=='requirement'


def test_context_with_separate_formal_clause_stays_uncertain():
    u=dict(kind='source_text',fields={'body':'Rationale\nAn explanation.\n1.2.3 Farms shall retain records.'})
    p=propose(u)
    assert p['classification']=='undetermined' and p['matches']
    u['fields']={'body':'How do I interpret this requirement? Context only.','criteria':'Farms shall retain original records.'}
    assert propose(u)['classification']=='undetermined'
    u['fields']={'body':'Rationale\nContext only.\nRequirement: Farms shall retain records.'}
    assert propose(u)['classification']=='undetermined'


def test_nearest_actual_heading_boundary_prevents_context_leaking():
    u=dict(kind='source_text',fields={'body':'Sites shall preserve the context.'},ancestors=[dict(id='h1',type='heading',title='How do I interpret this requirement?',version=3)])
    assert propose(u)['classification']=='context'
    u['ancestors'].insert(0,dict(id='h2',type='heading',title='Requirements',version=1))
    assert propose(u)['classification']=='requirement'
    u.pop('ancestors')
    assert propose(u)['classification']=='requirement'


def test_existing_workflow_resolves_headers_without_accepting_candidate(system):
    store,doc_id=system;owner,row=labelled_table();original=deepcopy(owner['original'])
    store.install(doc_id,[owner,row],[])
    decide(system,'accept_content','table');decide(system,'accept_content','row')
    current_row=get(system,'row')
    assert current_row['classification']=='requirement'
    assert current_row['requirement_confidence'] is None
    assert current_row['requirement_status']=='pending'
    assert 'row' not in current(system)['published']
    assert get(system,'table')['original']==original
    decide(system,'classify','row',classification='context',note='Isolated explicit human judgment overrides the candidate.')
    assert get(system,'row')['classification']=='context'
    assert get(system,'row')['requirement_human'] is True
