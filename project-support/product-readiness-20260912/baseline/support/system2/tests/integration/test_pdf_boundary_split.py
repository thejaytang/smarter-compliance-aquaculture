from copy import deepcopy
import pytest
from pdf_extraction.contracts.hashing import digest
from pdf_extraction.review.browser_view import browser_state
from .test_two_stage_workflow import system,current,decide,unit
from .test_hierarchy_repairs import setup,get
from .test_review_rows import guarded


def prepare(system):
    s,did=setup(system);s.install(did,[unit('note'),unit('reference')],[])
    with s.transaction() as db:
        d=s._load(db,did);by={u['id']:u for u in d['units']};u=by['clause']
        u['original']={'fields':{'body':'First paragraph.\nSecond paragraph.','identifier':'1'},'references':[{'page_index':0,'bbox':[10,20,100,40]},{'page_index':1,'bbox':[10,20,100,40]}],'structure':[]}
        u.update(content_human=False,touched=True,content_relations=[{'role':'notes','target_unit_id':'note'}],relation_dependencies=['note'],dependencies=['coverage','note'])
        by['other'].update(dependencies=['clause'],hierarchy_dependencies=['clause'],hierarchy_edit={'type':'paragraph','parent_id':'clause'})
        by['reference'].update(dependencies=['clause'],relation_dependencies=['clause'],content_relations=[{'role':'reference','target_unit_id':'clause'}])
        s._recompute(db,d,s.policy(db));s._save(db,d)
    return s,did


def request(system):
    return guarded(system,'clause',action='split',note='Restore two original paragraphs',split_spec={
        'parts':[{'text':'First paragraph.\n','type':'paragraph','reference_indices':[0]}, {'text':'Second paragraph.','type':'paragraph','reference_indices':[1]}],
        'fields':{'identifier':[0]},'outgoing':{'0':[1]},
        'incoming':{'other':{'fingerprint':digest(get(system,'other')),'parent':[0]},'reference':{'fingerprint':digest(get(system,'reference')),'links':{'0':[1]}}}})


def children(system):return [u for u in current(system)['units'] if u.get('boundary_created_from') and not u.get('superseded_by')]


def test_split_exact_text_fields_evidence_and_relations_then_restore(system):
    s,did=prepare(system);before=deepcopy(get(system,'clause')['original']);r=request(system);receipt=s.decision(r);assert s.decision(r)==receipt
    a,b=children(system)
    assert a['original']['fields']=={'body':'First paragraph.\n','identifier':'1'}
    assert b['original']['fields']=={'body':'Second paragraph.'}
    assert not a['content_relations'] and b['content_relations'][0]['target_unit_id']=='note'
    assert get(system,'other')['hierarchy_edit']['parent_id']==a['id']
    assert get(system,'reference')['content_relations'][0]['target_unit_id']==b['id']
    assert get(system,'clause')['original']==before
    assert a['original']['references'][0]['page_index']==0 and b['original']['references'][0]['page_index']==1
    assert b['boundary_created_from']['start']==len('First paragraph.\n')
    assert 'clause' not in current(system)['published']
    detail=browser_state(s,'unit',did,a['id']);assert detail['repair_history'][0]['action']=='split'
    s.decision(guarded(system,a['id'],action='restore',restore_request_id=r['request_id'],note='Restore prior boundaries'))
    assert not children(system) and not get(system,'clause').get('superseded_by')
    assert get(system,'reference')['content_relations'][0]['target_unit_id']=='clause'
    assert get(system,'other')['hierarchy_edit']['parent_id']=='clause'
    assert get(system,'clause')['original']==before


@pytest.mark.parametrize('change,match',[
    (lambda s:s['parts'][0].update(text='Changed text.'),'preserve_every_source_character'),
    (lambda s:s['fields'].clear(),'explicit_split_assignment'),
    (lambda s:s['fields'].update(identifier=[0,1]),'explicit_split_assignment'),
    (lambda s:s['outgoing'].clear(),'explicit_split_assignment'),
    (lambda s:s['incoming'].clear(),'stale_or_missing_split_relationship'),
    (lambda s:s['incoming'].update(other=[]),'invalid_split_relationship_assignment'),
    (lambda s:s['parts'][0].update(reference_indices=[]),'explicit_split_assignment'),
])
def test_split_missing_disposition_and_text_changes_do_not_apply(system,change,match):
    s,did=prepare(system);r=request(system);change(r['split_spec'])
    with pytest.raises(ValueError,match=match):s.decision(r)
    assert not children(system) and not get(system,'clause').get('superseded_by')


def test_split_restore_retains_later_edits_and_reopens_delivery(system):
    s,did=prepare(system);r=request(system);s.decision(r);a,b=children(system)
    decide(system,'correct',b['id'],fields={'body':'A later source correction'},note='New comparison')
    with pytest.raises(ValueError,match='restore_conflicts'):
        s.decision(guarded(system,a['id'],action='restore',restore_request_id=r['request_id'],note='Cannot overwrite the later edit'))


def test_split_context_identifies_required_incoming_choices(system):
    s,did=prepare(system);v=browser_state(s,'unit',did,'clause')['split_context']
    assert v['fields']=={'identifier':'1'}
    assert {u['id'] for u in v['incoming']}=={'other','reference'}


def test_split_delivery_navigation_excel_and_restore_are_consistent(system,tmp_path):
    from .test_requirement_workbook import export
    s,did=prepare(system)
    for uid in ['coverage','note','clause']:decide(system,'accept_content',uid)
    decide(system,'classify','clause',classification='requirement')
    assert 'clause' in current(system)['published']
    r=request(system);s.decision(r);a,b=children(system)
    assert 'clause' not in current(system)['published']
    for uid in ['coverage','note',a['id'],b['id']]:decide(system,'accept_content',uid)
    decide(system,'classify',b['id'],classification='requirement')
    assert current(system)['published'][b['id']]['fields']['body']=='Second paragraph.'
    tasks=browser_state(s,'tasks',did,include_reviewed=True)
    assert 'clause' not in {u['id'] for u in tasks['items']}
    _,wb,_=export(system,tmp_path);rows=list(wb['PA001'].iter_rows(min_row=11,values_only=True));wb.close()
    assert any(r[1]=='First paragraph.\n' for r in rows)
    assert any(r[1]=='Second paragraph.' for r in rows)
    assert any(r[1]=='First paragraph.\nSecond paragraph.' and r[5]=='Superseded' for r in rows)
    s.decision(guarded(system,a['id'],action='restore',restore_request_id=r['request_id'],note='Restore original boundaries'))
    assert b['id'] not in current(system)['published']
