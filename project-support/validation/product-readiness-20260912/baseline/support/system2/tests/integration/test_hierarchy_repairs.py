from copy import deepcopy
import json
import pytest
from pdf_extraction.contracts.hashing import digest
from pdf_extraction.review.browser_view import browser_state
from .test_two_stage_workflow import system,current,unit,decide
from .test_review_rows import guarded
from .test_requirement_workbook import export


def setup(system):
    s,did=system;s.install(did,[unit('heading'),unit('other')],[])
    with s.transaction() as db:
        d=s._load(db,did);d['hierarchy_version']='canonical-hierarchy/1'
        items={u['id']:u for u in d['units']};d['units']=[items[k] for k in ('heading','clause','other','coverage')]
        for i,u in enumerate(d['units']):
            u['source_order']=i
            if u['kind']!='coverage':u['source_hierarchy']={'type':'heading' if u['id']=='heading' else 'paragraph','heading_level':2 if u['id']=='heading' else None,'parent_id':None,'origin':'canonical'}
        s._save(db,d)
    return s,did


def get(system,uid):return next(u for u in current(system)['units'] if u['id']==uid)


def test_parent_edit_changes_effective_hierarchy_and_invalidates_context(system,tmp_path):
    s,did=setup(system);original=deepcopy(get(system,'clause')['original'])
    req=guarded(system,'clause',action='hierarchy',hierarchy={'parent_id':'heading'},target_fingerprint=digest(get(system,'heading')),note='Original section checked')
    receipt=s.decision(req);assert s.decision(req)==receipt
    assert 'clause' not in current(system)['published'] and 'other' in current(system)['published']
    view=browser_state(s,'unit',did,'clause')['effective'];assert view['hierarchy']['parent_id']=='heading'
    assert view['ancestors'][0]['id']=='heading' and get(system,'clause')['original']==original
    decide(system,'accept_content','heading');decide(system,'accept_content');decide(system,'classify',classification='requirement')
    assert current(system)['published']['clause']['hierarchy']['parent_id']=='heading'
    _,wb,_=export(system,tmp_path)
    assert 'Parent content' in [c.value for c in wb['PA001'][10]];wb.close()
    decide(system,'correct','heading',fields={'body':'Changed source heading'},note='Checked text')
    assert 'clause' not in current(system)['published']


def test_hierarchy_type_level_cycle_and_stale_target(system):
    s,did=setup(system)
    stale=digest(get(system,'heading'));decide(system,'draft','heading',draft={'text':'Pending'})
    with pytest.raises(ValueError,match='stale_hierarchy_parent'):
        s.decision(guarded(system,'clause',action='hierarchy',hierarchy={'parent_id':'heading'},target_fingerprint=stale,note='Test'))
    s.decision(guarded(system,'clause',action='hierarchy',hierarchy={'type':'heading','heading_level':3,'parent_id':'heading'},target_fingerprint=digest(get(system,'heading')),note='Source heading'))
    assert browser_state(s,'unit',did,'clause')['effective']['kind']=='source_heading'
    with pytest.raises(ValueError,match='cycle'):
        s.decision(guarded(system,'heading',action='hierarchy',hierarchy={'parent_id':'clause'},target_fingerprint=digest(get(system,'clause')),note='Cycle'))
    with pytest.raises(ValueError,match='heading_level'):
        s.decision(guarded(system,'clause',action='hierarchy',hierarchy={'heading_level':0},note='Bad level'))


def test_order_is_effective_restorable_and_source_preserving(system,tmp_path):
    s,did=setup(system);before=[u['id'] for u in current(system)['units']]
    req=guarded(system,'other',action='reading_order',target_unit_id='heading',target_fingerprint=digest(get(system,'heading')),mode='before',note='Original reading order')
    s.decision(req);assert [u['id'] for u in current(system)['units']][:3]==['other','heading','clause']
    _,wb,_=export(system,tmp_path);assert wb['PA001']['A11'].value=='other';wb.close()
    s.decision(guarded(system,'other',action='restore',restore_request_id=req['request_id'],note='Restore prior order'))
    assert [u['id'] for u in current(system)['units']]==before


def test_order_keeps_subtrees_and_detects_parent_after_child(system):
    s,did=setup(system)
    s.decision(guarded(system,'clause',action='hierarchy',hierarchy={'parent_id':'heading'},target_fingerprint=digest(get(system,'heading')),note='Parent'))
    s.decision(guarded(system,'clause',action='reading_order',target_unit_id='heading',target_fingerprint=digest(get(system,'heading')),mode='before',note='Bad source order challenge'))
    assert 'hierarchy_parent_after_child' in get(system,'clause')['blockers']
    with pytest.raises(ValueError,match='repair_parent_or_reading_order'):
        decide(system,'resolve_content',resolved_issues=['hierarchy_parent_after_child'],note='Cannot dismiss a structural defect')
    s.decision(guarded(system,'clause',action='reading_order',target_unit_id='heading',target_fingerprint=digest(get(system,'heading')),mode='after',note='Restore correct source order'))
    assert 'hierarchy_parent_after_child' not in get(system,'clause')['blockers']
    s.decision(guarded(system,'heading',action='reading_order',target_unit_id='other',target_fingerprint=digest(get(system,'other')),mode='after',note='Move source section together'))
    assert [u['id'] for u in current(system)['units']][:3]==['other','heading','clause']


def test_parent_and_note_roles_do_not_erase_each_others_dependency(system):
    s,did=setup(system)
    s.decision(guarded(system,'clause',action='hierarchy',hierarchy={'parent_id':'heading'},target_fingerprint=digest(get(system,'heading')),note='Parent'))
    s.decision(guarded(system,'clause',action='relation',target_unit_id='heading',target_fingerprint=digest(get(system,'heading')),role='context',mode='attach',note='Related source'))
    s.decision(guarded(system,'clause',action='hierarchy',hierarchy={'parent_id':None},note='Root'))
    assert 'heading' in get(system,'clause')['dependencies']


def test_shared_table_evidence_does_not_make_coverage_the_row_parent():
    from pdf_extraction.domains.requirements.review_hierarchy import project
    ref={'canonical_sha256':'sha','block_id':'table'}
    source={'blocks':{'table':{'type':'table','table':{'cells':[]}}}}
    items=[dict(id='owner',kind='context',original={'references':[ref]}),
           dict(id='row',kind='standard_indicator',original={'references':[dict(ref,locator='cell')]}),
           dict(id='check',kind='coverage',original={'references':[ref]})]
    project(items,{'sha':source})
    assert items[1]['source_hierarchy']['parent_id']=='owner'
    assert items[1]['source_hierarchy']['type']=='table_row'
    assert 'source_hierarchy' not in items[2]
