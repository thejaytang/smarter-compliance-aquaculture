"""Bounded local rules retain ambiguity without promoting a calibrated score."""
from pdf_extraction.verification.source_comparison import compare
from pdf_extraction.domains.requirements.classification import propose
from .test_original_page_verification import page, record


def ordered_records():
    p=page('First original paragraph.')
    p['lines'].append(dict(text='Second original paragraph.',bbox=[20,100,180,120],engine='poppler'))
    records=[]
    for index,line in enumerate(p['lines']):
        r=dict(record(line['text'],line['bbox']),id=str(index),unit_id=str(index))
        records.extend([r,dict(r,id=str(index)+':structure',text='',record_kind='structure_only',structure={'schema':'pdf-output-structure/1','reading_order_key':index})])
    return p,records


def test_reversed_aligned_order_is_located_but_clean_control_remains_clear():
    p,records=ordered_records()
    assert not compare(p,records)['findings']
    records[1]['structure']['reading_order_key']='3/2'
    f=next(f for f in compare(p,records)['findings'] if f['code']=='output_reading_order_conflict')
    assert len(f['source_regions'])==2
    assert f['related_output_ids']==['0:structure','1:structure']
    assert f['confidence'] is None


def test_side_by_side_and_cross_page_order_are_not_guessed():
    p,records=ordered_records(); records[1]['structure']['reading_order_key']=2
    records[3]['references']=[dict(page_index=0,bbox=[300,100,450,120])]
    assert not any(f['code']=='output_reading_order_conflict' for f in compare(p,records)['findings'])
    records[3]['references']=[dict(page_index=1,bbox=[20,100,180,120])]
    assert not any(f['code']=='output_reading_order_conflict' for f in compare(p,records)['findings'])


def test_nested_row_view_does_not_duplicate_parent_order():
    p,records=ordered_records(); records[1]['structure'].update(reading_order_key=2,table_scope='selected_cells')
    assert not any(f['code']=='output_reading_order_conflict' for f in compare(p,records)['findings'])


def test_modal_definition_is_context_but_following_obligation_is_not_removed():
    d={'kind':'source_text','fields':{'body':'“Should” denotes a recommendation.'}}
    assert propose(d)['classification']=='context'
    d['fields']['body']+=' Farms should keep inspection records.'
    assert propose(d)['classification']=='requirement'
    d['fields']['body']='“Must” means an obligation.';d['fields']['context']='Farms must retain the original.'
    assert propose(d)['classification']=='requirement'


def test_bound_heading_keeps_context_and_normative_heading_remains_reviewable():
    u={'kind':'source_text','fields':{'body':'Monitoring procedures'},'references':[{'locator':'html:nth-of-type(1) > body:nth-of-type(1) > h2:nth-of-type(3)'}]}
    assert propose(u)['classification']=='context'
    u['fields']['body']='Farms must monitor discharges'
    assert propose(u)['classification']=='requirement'
    u['fields']['body']='Record discharge measurements';u['references'][0]['locator']='body > p:nth-of-type(3)'
    assert propose(u)['classification']=='undetermined'
    assert propose(u)['parts'][0]['confidence'] is None
