from pdf_extraction.sqlite_support import connect as connect_sqlite
from copy import deepcopy
from pdf_extraction.domains.requirements.pdf_review_scope import localize,pages
from pdf_extraction.domains.requirements.review_groups import group_units
from .test_two_stage_workflow import unit,system,current,decide


def sample():
    a,b,c=[unit(i) for i in ('a','b','cross')]
    for u,pp,h in ((a,[0],'A'),(b,[8],'B'),(c,[0,8],'A')):
        u['original']['references']=[{'page_index':p,'canonical_sha256':h,'bbox':[10,10,30,40]} for p in pp]
        u['dependencies']=['coverage:local:old','covA','covB']
    checks=[]
    for cid,ref in [('coverage:local:old',{'page_index':0}),('covA',{'locator':'PDF pages 1, 2','canonical_sha256':'A'}),('covB',{'locator':'PDF pages 9, 10','canonical_sha256':'B'})]:
        u=unit(cid,'coverage');u['original']['references']=[ref];u['blockers']=[] if cid.startswith('coverage:local:') else ['cross_window_relationship_review_required'];checks.append(u)
    return [a,b,c,*checks]


def test_page_scopes_preserve_findings_without_global_fanout():
    original=sample();scoped=localize(original);by={u['id']:u for u in scoped}
    assert set(by['a']['dependencies'])=={'coverage:pdf-page:0','covA'}
    assert set(by['b']['dependencies'])=={'coverage:pdf-page:8','covB'}
    assert set(by['cross']['dependencies'])=={'coverage:pdf-page:0','coverage:pdf-page:8','covA','covB'}
    for u in original:
        assert by[u['id']]['original']==u['original']
        assert by[u['id']]['blockers']==u['blockers']
    assert localize(scoped)==scoped


def test_unknown_scopes_and_human_findings_are_not_silently_removed():
    original=sample();original[3]['blockers']=['human_omission'];original[3]['original']['references']=[]
    scoped=localize(original)
    assert all('coverage:local:old' in u['dependencies'] for u in scoped if u['kind']!='coverage')


def test_effective_positions_set_page_gates_and_keep_shared_notes():
    original=sample();original[0]['reviewed_references']=[{'page_index':8}]
    original[0]['dependencies'].append('b');original[0]['relation_dependencies']=['b']
    by={u['id']:u for u in localize(original)}
    assert set(by['a']['dependencies'])=={'coverage:pdf-page:8','covB','b'}
    assert pages(by['a'])=={8}


def test_pdf_heading_does_not_merge_unrelated_page_content():
    original=sample()[:3];head=deepcopy(original[0]);head['id']='h';head['kind']='source_heading'
    result=group_units([head,*original]);by={u['id']:u for u in result}
    assert {'h','a','b','cross'}<=set(by)
    assert 'coverage:pdf-page:0' in by['a']['dependencies']
    assert not any(u['id'].startswith('coverage:local:') for u in result)


def test_migration_preserves_history_and_rejects_old_guards(system):
    import sqlite3
    import pytest
    from pdf_extraction.review.migrate_pdf_scope import migrate
    from .test_review_rows import guarded
    s,did=system
    decide(system,'accept_content')
    with s.transaction() as db:
        doc=s._load(db,did);doc['source']['file_format']='pdf';doc['processed_pages']=[0,1]
        doc['units'][1]['original']['references']=[{'page_index':0,'bbox':[10,10,30,30]}]
        s._save(db,doc)
    before=current(system);old=guarded(system,'clause',action='classify',classification='requirement')
    preview=migrate(s.root);assert preview['documents'][0]['new_page_checks']==2
    assert current(system)==before
    receipt=migrate(s.root,True);after=current(system)
    assert after['history']==before['history'] and not after['published']
    assert [u['original'] for u in after['units'][:2]]==[u['original'] for u in before['units']]
    assert any(e['kind']=='suspend' for e in s.feed()['events'])
    with pytest.raises(ValueError,match='stale_unit'):s.decision(old)
    assert migrate(s.root,True)['documents']==[]
    with connect_sqlite(receipt['backup']) as db:
        assert db.execute('select count(*) from review_history').fetchone()[0]==1


def test_page_discovery_includes_empty_unprocessed_and_accepted_content(system):
    from pdf_extraction.review.browser_view import browser_state
    from pdf_extraction.review.migrate_pdf_scope import migrate
    import pytest
    s,did=system
    with s.transaction() as db:
        doc=s._load(db,did);doc['source']['file_format']='pdf';doc['total_pages']=3;doc['processed_pages']=[0,1]
        doc['units'][1]['original']['references']=[{'page_index':0,'bbox':[10,10,30,30]}]
        s._save(db,doc)
    before=current(system)
    summary=browser_state(s,'pages',did)
    assert summary['items']==[{'page_index':0,'processed':True,'mapped_units':1,'accepted_content':1},
        {'page_index':1,'processed':True,'mapped_units':0,'accepted_content':0},
        {'page_index':2,'processed':False,'mapped_units':0,'accepted_content':0}]
    page=browser_state(s,'page',did,page_index=0)
    assert page['total']==1 and page['items'][0]['id']=='clause'
    assert page['items'][0]['regions']==[{'bbox':[10,10,30,30],'coord_origin':'top_left'}]
    assert 'original' not in page['items'][0] and current(system)==before
    with pytest.raises(ValueError,match='out_of_range'):browser_state(s,'page',did,page_index=3)
    migrate(s.root,True)
    assert browser_state(s,'page',did,page_index=1)['coverage']['id']=='coverage:pdf-page:1'
    coverage=browser_state(s,'unit',did,'coverage:pdf-page:0')['coverage']
    assert sum(r['units'] for r in coverage)==1
    assert browser_state(s,'unit',did,'coverage:pdf-page:1')['coverage']==[]


def test_page_discovery_tracks_position_corrections(system):
    from pdf_extraction.review.browser_view import browser_state
    s,did=system
    with s.transaction() as db:
        doc=s._load(db,did);doc['source']['file_format']='pdf';doc['total_pages']=2
        doc['units'][1]['original']['references']=[{'page_index':0,'bbox':[10,10,30,30]}]
        doc['units'][1]['reviewed_references']=[{'page_index':1,'bbox':[20,20,50,50]}]
        s._save(db,doc)
    assert browser_state(s,'page',did,page_index=0)['total']==0
    assert browser_state(s,'page',did,page_index=1)['items'][0]['regions'][0]['bbox']==[20,20,50,50]


def test_position_repair_and_insertion_refresh_actual_page_dependencies(system):
    from pdf_extraction.review.migrate_pdf_scope import migrate
    s,did=system
    with s.transaction() as db:
        doc=s._load(db,did);doc['source']['file_format']='pdf';doc['total_pages']=3;doc['processed_pages']=[0,1,2]
        doc['units'][1]['original']['references']=[{'page_index':0,'bbox':[10,10,30,30]}]
        s._save(db,doc)
    migrate(s.root,True)
    for p in range(3):decide(system,'accept_content','coverage:pdf-page:'+str(p))
    decide(system,'structure',fields={},structure=[{'role':'source_region','locator':'page 2: 10,10,40,40'}],note='Checked moved original location')
    by={u['id']:u for u in current(system)['units']}
    assert 'coverage:pdf-page:1' in by['clause']['dependencies']
    assert 'coverage:pdf-page:0' not in by['clause']['dependencies']
    assert not by['coverage:pdf-page:0']['content_human'] and not by['coverage:pdf-page:1']['content_human']
    assert by['coverage:pdf-page:2']['content_human']
    decide(system,'supplement','coverage:pdf-page:1',fields={'body':'Missing text on another original page'},locator='page 3: 10,10,40,40',note='Checked original')
    by={u['id']:u for u in current(system)['units']};added=next(u for u in by.values() if u['id'].startswith('manual:'))
    assert 'coverage:pdf-page:2' in added['dependencies'] and 'coverage:pdf-page:1' not in added['dependencies']
    assert not by['coverage:pdf-page:2']['content_human']
