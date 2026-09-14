"""Original note markers are evidence for a located linkage question only."""
from copy import deepcopy
from pdf_extraction.verification.source_comparison import compare


def fixture():
    p=dict(page_index=0,width=600,height=800,lines=[
        dict(text='Farms shall monitor water 7',bbox=[20,20,220,40],engine='native'),
        dict(text='Other original paragraph',bbox=[20,100,220,120],engine='native'),
        dict(text='7',bbox=[20,500,24,506],engine='native'),
        dict(text='Monitoring means weekly sampling.',bbox=[24,500,260,510],engine='native')])
    rows=[]
    for uid,text,bounds in [('parent',p['lines'][0]['text'],p['lines'][0]['bbox']),('other',p['lines'][1]['text'],p['lines'][1]['bbox']),('note','7 Monitoring means weekly sampling.',[20,500,260,510])]:
        rows.append(dict(id=uid,unit_id=uid,text=text,references=[dict(page_index=0,bbox=bounds)]))
    return p,rows


def test_missing_note_link_is_located_from_original_markers():
    p,rows=fixture();r=compare(p,rows)
    f=next(f for f in r['findings'] if f['code']=='source_footnote_relation_missing')
    assert f['note_marker']=='7' and f['output_ids']==['note']
    assert len(f['source_regions'])==3 and f['confidence'] is None
    assert 'semantic scope' in f['unverified_scope']


def test_correct_link_is_clear_and_wrong_owner_is_a_located_conflict():
    p,rows=fixture();owner=dict(rows[0],id='parent:structure',text='',record_kind='structure_only',structure={'schema':'pdf-output-structure/1','related_content':[dict(role='notes',target_unit_id='note',references=rows[-1]['references'])]})
    assert not compare(p,[*rows,owner])['findings']
    owner['references']=rows[1]['references'];owner['unit_id']='other'
    f=next(f for f in compare(p,[*rows,owner])['findings'] if f['code']=='output_relation_target_conflict')
    assert set(f['unit_ids'])=={'note','other'}


def test_no_matching_callout_or_unraised_number_is_not_assumed_a_footnote():
    p,rows=fixture();p['lines'][0]['text']='Farms shall monitor water';rows[0]['text']=p['lines'][0]['text']
    assert not compare(p,rows)['findings']
    p,rows=fixture();p['lines'][2]['bbox'][3]=510
    assert not compare(p,rows)['findings']
