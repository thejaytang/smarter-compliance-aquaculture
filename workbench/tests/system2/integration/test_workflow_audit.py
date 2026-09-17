"""Cross-step regressions found during the non-PDF-accuracy workflow audit."""
from .test_two_stage_workflow import system, current, decide, request, unit
import pytest


def test_coverage_instruction_cannot_be_delivered_as_source_requirement(system):
    decide(system,'accept_content','coverage')
    with pytest.raises(ValueError,match='context_only'):
        decide(system,'classify','coverage',classification='requirement')


def test_structure_only_correction_is_supported(system):
    decide(system,'structure',fields={},structure=[{'locator':'cell B2','role':'notes'}],note='Footnote belongs to this source row')
    doc=current(system)
    assert doc['units'][1]['reviewed_structure'][0]['role']=='notes'
    assert not doc['published']


def test_superseded_parent_cannot_be_published_again(system):
    decide(system,'split',split_parts=['Fish farms shall ', 'keep records.'],note='Original item boundaries')
    with pytest.raises(ValueError,match='superseded'):
        decide(system,'classify',classification='requirement')


def test_saved_draft_is_not_an_applied_review_in_history(system):
    decide(system,'draft',draft={'note':'still composing'})
    assert not current(system)['history']
    assert any(e['kind']=='draft' for e in system[0].feed()['events'])
    assert not any(e['kind']=='review' for e in system[0].feed()['events'])


def test_withdrawn_source_is_not_in_current_pending_total(system):
    decide(system,'reject',note='Requires review')
    system[0].reconcile_sources({})
    assert system[0].snapshot()['pending']==0
    assert current(system)['units'] and current(system)['history']


def test_retry_clears_old_failure_message(system):
    store,identity=system
    with store.transaction() as db:
        doc=store._load(db,identity);doc.update(state='failed',error='temporary parser error',parser_complete=False)
        store._save(db,doc)
    doc=current(system)
    store.control(request(document_id=identity,revision=doc['revision'],action='retry'))
    assert not current(system).get('error')


def test_restart_and_pause_resume_keep_unfinished_range(system):
    store,identity=system
    store.install(identity,[unit('coverage-next','coverage',None)],[],complete=False,cursor=3,total_pages=6,pages=[0,1,2])
    doc=current(system);store.control(request(document_id=identity,revision=doc['revision'],action='pause'))
    doc=current(system);store.control(request(document_id=identity,revision=doc['revision'],action='resume'))
    assert current(system)['state']=='queued' and current(system)['cursor']==3
    assert store.feed()['documents'][0]['unparsed_pages']==[4,5,6]


def test_real_parser_local_human_path_reaches_complete(tmp_path,monkeypatch):
    from .test_workflow_formats import fake_runner, req
    from system2.contracts.test_source_intake import source,HTML
    r=fake_runner(tmp_path,monkeypatch,source(),HTML)
    identity=r.start(req(source_ids=['PA001']))['documents'][0]
    assert r.tick()['status']=='processed'
    pair=(r.store,identity)
    for u in current(pair)['units']:
        decide(pair,'resolve_content',u['id'],resolved_issues=u['blockers'],note='Isolated fixture content validation')
    for u in current(pair)['units']:
        c='requirement' if u['original']['fields'].get('identifier')=='1' else 'context'
        decide(pair,'classify',u['id'],classification=c,note='Isolated fixture classification')
    assert current(pair)['complete'] and current(pair)['state']=='complete'
    assert len(current(pair)['published'])==1
    assert r.tick()['status']=='idle'


def test_optional_provider_failures_and_citation_gate(monkeypatch):
    from pdf_extraction.domains.suggestions import Suggestions
    import urllib.request,json,io
    cfg={'enabled':True,'endpoint':'https://example.invalid/suggest','model':'fixture','max_calls':1,'max_bytes':9999,'allowed_capabilities':['requirement_candidates'],'allowed_evidence_ids':['source-1']}
    evidence=[{'id':'source-1','content':'Original text'}]
    class Opener:
        def __init__(self,value):self.value=value
        def open(self,*args,**kwargs):
            if isinstance(self.value,Exception):raise self.value
            return io.BytesIO(self.value)
    for response in [TimeoutError(),b'not json',json.dumps({'suggestions':[{'evidence_ids':['unauthorized']}]}).encode()]:
        monkeypatch.setattr(urllib.request,'build_opener',lambda *args,v=response:Opener(v))
        assert Suggestions(cfg).propose('requirement_candidates',evidence)['mode']=='NO_API_FALLBACK'
    response=json.dumps({'suggestions':[{'evidence_ids':['source-1'],'proposal':'Candidate only'}]}).encode()
    monkeypatch.setattr(urllib.request,'build_opener',lambda *args:Opener(response))
    provider=Suggestions(cfg)
    assert provider.propose('requirement_candidates',evidence)['accepted'] is False
    assert provider.propose('requirement_candidates',evidence)['mode']=='NO_API_FALLBACK'


def test_worker_lock_and_restart_after_running_checkpoint(tmp_path,monkeypatch):
    from .test_workflow_formats import fake_runner, req
    from system2.contracts.test_source_intake import source,HTML
    from pdf_extraction.platform_support import lock_file
    r=fake_runner(tmp_path,monkeypatch,source(),HTML)
    identity=r.start(req(source_ids=['PA001']))['documents'][0]
    with (r.root/'.worker.lock').open('a+b') as lock:
        lock_file(lock)
        assert r.tick()['status']=='busy'
    with r.store.transaction() as db:
        d=r.store._load(db,identity);d['state']='running';r.store._save(db,d)
    assert r.tick()['status']=='processed'
    cursor=r.store.feed()['cursor']
    assert r.tick()['status']=='idle'
    assert not r.store.feed(cursor)['events']


def test_parser_review_findings_are_visible_coverage_blockers(tmp_path):
    from .test_workflow_formats import content_units
    from system2.contracts.test_source_intake import source
    from pdf_extraction.contracts.source import ParseResult
    (tmp_path/'canonical.json').write_text('{"nodes":[]}')
    s=source()
    result=ParseResult(source=s,format='html',status='review_required',canonical_path='canonical.json',reason_codes=['uncalibrated_template_extraction','image_content_not_transcribed'])
    units,_=content_units(tmp_path,result,s)
    assert units[-1]['blockers']==['image_content_not_transcribed']


def test_feed_pages_do_not_hide_current_delivery(system):
    store,identity=system
    with store.transaction() as db:
        for i in range(1002):store._event(db,identity,'test_history',{'index':i})
    first=store.feed()
    assert first['has_more'] and len(first['events'])==1000
    tail=store.feed(first['cursor'])
    assert not tail['has_more']
    assert len(first['current_requirements'])==1
    assert tail['events'][-1]['index']==1001
    assert first['cursor']<tail['cursor']


def test_pdf_job_windows_pause_resume_and_restart_without_accuracy_claim(tmp_path,monkeypatch):
    from .test_workflow_formats import fake_runner,req
    from system2.contracts.test_source_intake import source
    from pypdf import PdfWriter
    from io import BytesIO
    from types import SimpleNamespace
    import json
    import pdf_extraction.orchestration.workflow as module
    pdf=PdfWriter()
    for _ in range(7):pdf.add_blank_page(width=100,height=100)
    buffer=BytesIO();pdf.write(buffer);raw=buffer.getvalue()
    r=fake_runner(tmp_path,monkeypatch,source(raw,'pdf'),raw)
    seen=[]
    def parser(source,source_root,output,configurations,config,pages):
        seen.append(sorted(pages));output.mkdir(parents=True)
        blocks={str(p):{'type':'paragraph','content':{'native_text':'Fixture page '+str(p)},'segments':[{'page_index':p}]} for p in pages}
        (output/'canonical.json').write_text(json.dumps({'blocks':blocks}))
        return SimpleNamespace(canonical_path='canonical.json',format='pdf',reason_codes=[],status='review_required')
    monkeypatch.setattr(module,'run_item',parser)
    identity=r.start(req(source_ids=['PA001']))['documents'][0]
    assert r.tick()['status']=='processed'
    d=r.store.snapshot()['documents'][0]
    r.store.control(req(document_id=identity,revision=d['revision'],action='pause'))
    assert r.tick()['status']=='idle'
    d=r.store.snapshot()['documents'][0]
    r.store.control(req(document_id=identity,revision=d['revision'],action='resume'))
    assert r.tick()['status']=='processed' and r.tick()['status']=='processed'
    d=r.store.snapshot()['documents'][0]
    assert seen==[[0,1,2],[2,3,4,5],[5,6]]
    assert d['processed_pages']==list(range(7)) and d['parser_complete']
    assert not d['complete'] and not d['published']
    assert sum(u.get('evidence_only',False) for u in d['units'])==2
    assert r.tick()['status']=='idle'


def test_interrupted_write_rolls_back_state_and_events(system):
    store,identity=system
    before=store.snapshot();cursor=store.feed()['cursor']
    with pytest.raises(RuntimeError):
        with store.transaction() as db:
            doc=store._load(db,identity);doc['units']=[];store._save(db,doc)
            store._event(db,identity,'partial_write',{})
            raise RuntimeError('simulated crash before commit')
    assert store.snapshot()==before and not store.feed(cursor)['events']


def test_transitive_dependency_correction_requires_fresh_acceptance(system):
    store,identity=system
    decide(system,'accept_content','clause')
    child=unit('child');child['dependencies']=['clause']
    store.install(identity,[child],[])
    decide(system,'accept_content','child');decide(system,'classify','child',classification='requirement')
    decide(system,'correct','coverage',fields={'body':'Changed shared source context'},note='Isolated dependency change')
    assert not current(system)['published']
    assert current(system)['units'][-1]['requirement_status']=='blocked'
    decide(system,'accept_content','coverage')
    assert not current(system)['units'][-1]['requirement_human']
    assert 'child' not in current(system)['published']
