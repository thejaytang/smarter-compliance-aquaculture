from copy import deepcopy
import pytest
from pdf_extraction.contracts.hashing import digest
from pdf_extraction.review.browser_view import browser_state
from .test_hierarchy_repairs import setup,get
from .test_two_stage_workflow import system,current,decide
from .test_review_rows import guarded


def prepare(system):
    s,did=setup(system)
    with s.transaction() as db:
        d=s._load(db,did);by={u['id']:u for u in d['units']}
        for uid,body in [('heading','PRINCIPLE 2: CONSERVE NATURAL HABITAT, LOCAL'),('clause','BIODIVERSITY AND ECOSYSTEM FUNCTION')]:
            u=by[uid];u['original']['fields']={'body':body};u['content_human']=False;u['touched']=True
        by['other'].update(content_relations=[{'role':'reference','target_unit_id':'clause'}],dependencies=['clause'],hierarchy_edit={'parent_id':'clause','type':'paragraph'})
        s._recompute(db,d,s.policy(db));s._save(db,d)
    return s,did


def request(system,**extra):
    return guarded(system,'heading',action='merge',merge_ids=['heading','clause'],merge_fingerprints={'clause':digest(get(system,'clause'))},hierarchy={'type':'heading','heading_level':1},note='Restore the original two-line heading',**extra)


def test_merge_pending_text_redirects_relationships_and_restores(system):
    s,did=prepare(system);originals={u['id']:deepcopy(u['original']) for u in current(system)['units']}
    req=request(system);receipt=s.decision(req);assert s.decision(req)==receipt
    merged=get(system,'heading');child=get(system,'other')
    assert merged['edits']['body']=='PRINCIPLE 2: CONSERVE NATURAL HABITAT, LOCAL\nBIODIVERSITY AND ECOSYSTEM FUNCTION'
    assert get(system,'clause')['superseded_by']=='heading'
    assert child['hierarchy_edit']['parent_id']=='heading' and child['content_relations'][0]['target_unit_id']=='heading'
    assert not current(system)['published']
    assert {u['id']:u['original'] for u in current(system)['units']}==originals
    assert browser_state(s,'unit',did,'other')['effective']['related_content'][0]['fields']['body']==merged['edits']['body']
    s.decision(guarded(system,'heading',action='restore',restore_request_id=req['request_id'],note='Restore original boundaries'))
    assert not get(system,'clause').get('superseded_by')
    assert get(system,'other')['content_relations'][0]['target_unit_id']=='clause'
    assert not get(system,'heading').get('boundary_sources')


def test_merge_rejects_stale_targets_drafts_and_intervening_content(system):
    s,did=prepare(system);req=request(system)
    decide(system,'draft','clause',draft={'body':'unsubmitted text'})
    with pytest.raises(ValueError,match='stale'):s.decision(req)
    with pytest.raises(ValueError,match='unsubmitted_draft'):s.decision(request(system))
    with s.transaction() as db:
        d=s._load(db,did);by={u['id']:u for u in d['units']};by['clause']['drafts']={}
        by['other']['source_order']='1/2';d['units']=[by[k] for k in ('heading','other','clause','coverage')];s._save(db,d)
    with pytest.raises(ValueError,match='adjacent_content'):s.decision(request(system))


def test_merge_preserves_blockers_and_rejects_later_restore_conflict(system):
    s,did=prepare(system)
    with s.transaction() as db:
        d=s._load(db,did);next(u for u in d['units'] if u['id']=='clause')['blockers']=['human_unreadable'];s._save(db,d)
    req=request(system);s.decision(req)
    assert 'human_unreadable' in get(system,'heading')['blockers']
    with pytest.raises(ValueError,match='explicit_issue'):decide(system,'accept_content','heading')
    decide(system,'correct','other',fields={'body':'A later independent correction'},note='New source comparison')
    with pytest.raises(ValueError,match='restore_conflicts'):
        s.decision(guarded(system,'heading',action='restore',restore_request_id=req['request_id'],note='Do not overwrite later correction'))


def test_retired_fragment_cannot_be_reviewed_as_current(system):
    s,did=prepare(system);s.decision(request(system))
    with pytest.raises(ValueError,match='source_unit_replaced'):decide(system,'accept_content','clause')


def test_merge_delivery_excel_and_current_navigation_agree(system,tmp_path):
    from .test_requirement_workbook import export
    s,did=prepare(system);req=request(system);s.decision(req)
    page=browser_state(s,'tasks',did,include_reviewed=True)
    assert 'clause' not in {u['id'] for u in page['items']}
    outline=browser_state(s,'outline',did)
    assert 'clause' not in {u['id'] for u in outline['items']}
    decide(system,'accept_content','coverage');decide(system,'accept_content','heading')
    decide(system,'accept_content','other');decide(system,'classify','other',classification='requirement')
    published=current(system)['published']['other']
    assert published['ancestors'][0]['id']=='heading'
    assert published['related_content'][0]['fields']['body']==get(system,'heading')['edits']['body']
    _,wb,_=export(system,tmp_path);rows=list(wb['PA001'].iter_rows(min_row=11,values_only=True));wb.close()
    merged=next(r for r in rows if r[1]==get(system,'heading')['edits']['body'])
    assert merged[28]=='source_heading' and merged[31]==1
    assert any(r[5]=='Superseded' and r[1]=='BIODIVERSITY AND ECOSYSTEM FUNCTION' for r in rows)
    s.decision(guarded(system,'heading',action='restore',restore_request_id=req['request_id'],note='Reopen source boundary inspection'))
    assert 'other' not in current(system)['published']


def test_restore_does_not_silently_retarget_later_relationships(system):
    from .test_two_stage_workflow import unit
    s,did=prepare(system);s.install(did,[unit('later')],[])
    req=request(system);s.decision(req)
    s.decision(guarded(system,'later',action='relation',target_unit_id='heading',target_fingerprint=digest(get(system,'heading')),role='reference',mode='attach',note='Later relationship'))
    with pytest.raises(ValueError,match='later_relationships'):
        s.decision(guarded(system,'heading',action='restore',restore_request_id=req['request_id'],note='Would narrow the later reference'))
