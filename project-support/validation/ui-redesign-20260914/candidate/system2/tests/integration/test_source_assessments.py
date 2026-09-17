"""Engineering controls for bound study workflow; not human quality labels."""
from copy import deepcopy
from hashlib import sha256
import json
import pytest

from pdf_extraction.contracts.hashing import digest,encoded
from pdf_extraction.review import source_assessments as assessments,source_references as references
from pdf_extraction.review.source_verification_input import comparison_input
from pdf_extraction.verification.source_comparison import METHOD
from .test_two_stage_workflow import system,current,request
from .test_source_references import start,draft


def prepared(system):
    store,did,source,send,ref=start(system)
    body=draft();body['regions'].append(dict(id='omitted',role='text',page_index=0,bbox=[10,60,300,90],text='The exception does not apply.'))
    send('confirm',ref,body=body);ref=references.view(store,reference_id=ref['id'])
    with store.transaction() as db:
        doc=store._load(db,did)
        for u in doc['units']:
            u['original']['references']=[dict(page_index=0,bbox=[10,10,300,40])]
            if u['id']=='coverage':u['id']='coverage:pdf-page:0'
            else:u['dependencies']=['coverage:pdf-page:0']
        records=comparison_input(doc,0)
        raw=encoded(dict(original=dict(source_sha256=source['content_hash'],page_index=0),records=records)).encode()
        evidence=store.root/'source-verification'/'control.json';evidence.parent.mkdir();evidence.write_bytes(raw)
        verification=dict(source_sha256=source['content_hash'],page_index=0,input_sha256=digest(records),method=METHOD,stale=False,
            findings=[dict(id=i,code='engineering_control',message='Known synthetic finding') for i in ('found','repeat','false')],unverified=[],
            evidence_artifact=dict(path=str(evidence.relative_to(store.root)),sha256=sha256(raw).hexdigest()))
        doc['units'][0]['source_verification']=verification
        store._save(db,doc)
    def apply(action,task=None,**extra):
        req=request(document_id=did,source_sha256=source['content_hash'],action=action,**extra);req['actor']='Engineering validation'
        if task:req.update(assessment_id=task['id'],guard=task['guard'])
        result=assessments.apply(store,req,source=source,study_origin='engineering_fixture',evidence_class='synthetic')
        return result,req
    return store,did,source,ref,apply


def case(system):
    store,did,source,ref,apply=prepared(system)
    r,_=apply('create',reference_id=ref['id'],reference_guard=ref['guard'])
    t=assessments.view(store,assessment_id=r['assessment_id'])
    return store,did,source,ref,apply,t


def inventory(t):
    body=deepcopy(t['body'])
    body.update(reviewed_region_ids=[r['id'] for r in t['reference']['regions']],reviewed_output_ids=[r['id'] for r in t['records']],
        reviewed_dimensions=['content','structure','relationships'],note='Known complete engineering inventory; not independent reference acceptance.')
    body['errors']=[dict(id='error',category='text_error',severity='major',region_ids=['r1'],output_ids=[],explanation='Known synthetic error.'),
        dict(id='missed',category='text_omission',severity='critical',region_ids=['omitted'],output_ids=[],explanation='Original-only control without machine alarm.')]
    return body


def adjudication(t):
    body=deepcopy(t['body']);body['finding_decisions']=[
        dict(id='found',verdict='matched',error_ids=['error'],localization='incorrect',note='Known primary error match.'),
        dict(id='repeat',verdict='duplicate',error_ids=['error'],localization='correct',note='Known duplicate improves location only.'),
        dict(id='false',verdict='false_positive',error_ids=[],localization='unverified',note='Known unsupported alarm.')]
    return body


def test_source_first_stage_withholds_findings_and_does_not_touch_business(system):
    store,did,source,ref,apply=prepared(system);before=deepcopy(current(system))
    assert assessments.view(store,reference_id=ref['id'])=={'items':[]}
    with store.connect() as db:assert not assessments.exists(db)
    r,req=apply('create',reference_id=ref['id'],reference_guard=ref['guard']);t=assessments.view(store,assessment_id=r['assessment_id'])
    assert t['status']=='inventory' and not t['findings_exposed'] and 'verification' not in t
    assert assessments.apply(store,req,source=source)==r
    assert current(system)==before
    with pytest.raises(ValueError,match='complete_original_and_output'):apply('freeze_inventory',t,body=dict(t['body'],note='Incomplete'))
    assert assessments.view(store,assessment_id=t['id'])==t


def test_actual_inventory_adjudication_counts_and_revision_keep_exposure(system):
    store,did,source,ref,apply,t=case(system);before=deepcopy(current(system))
    apply('freeze_inventory',t,body=inventory(t));t=assessments.view(store,assessment_id=t['id'])
    assert t['status']=='adjudication' and t['findings_exposed'] and len(t['verification']['findings'])==3
    with pytest.raises(ValueError,match='complete_all_finding'):apply('confirm',t,body=t['body'])
    apply('confirm',t,body=adjudication(t));saved=assessments.view(store,assessment_id=t['id'])
    m=saved['report']['diagnostic_metrics'];assert m['verifier_recall']==.5 and m['localized_error_recall']==.5
    assert m['false_positive_findings']==1 and m['duplicate_findings']==1 and m['critical_miss_ids']==['missed']
    assert saved['report']['independent_metrics'] is None and saved['qualification']=='unqualified'
    apply('reopen_inventory',saved,note='Engineering revision after machine findings were exposed')
    revised=assessments.view(store,assessment_id=t['id'])
    assert revised['findings_exposed'] and 'verification' in revised and revised['report'] is None
    assert revised['body']['finding_decisions']==[] and revised['body']['reviewed_dimensions']==[]
    assert any(e['report']==saved['report'] for e in revised['history'])
    assert current(system)==before


@pytest.mark.parametrize('change,reason',[
    (lambda b:b.update(reviewed_region_ids=[]),'complete_original_and_output'),
    (lambda b:b.update(reviewed_output_ids=[]),'complete_original_and_output'),
    (lambda b:b.update(unresolved='Unclear footnote'),'complete_original_and_output'),
    (lambda b:b.update(form_draft={'error_dirty':True}),'stage_or_clear'),
])
def test_incomplete_inventory_never_advances(system,change,reason):
    store,did,source,ref,apply,t=case(system);body=inventory(t);change(body)
    with pytest.raises(ValueError,match=reason):apply('freeze_inventory',t,body=body)
    assert assessments.view(store,assessment_id=t['id'])==t


def test_inventory_cannot_be_changed_silently_after_revealing_findings(system):
    store,did,source,ref,apply,t=case(system)
    apply('freeze_inventory',t,body=inventory(t));t=assessments.view(store,assessment_id=t['id'])
    body=adjudication(t);body['errors'].pop()
    with pytest.raises(ValueError,match='reopen_error_inventory'):apply('save',t,body=body)
    assert assessments.view(store,assessment_id=t['id'])==t


@pytest.mark.parametrize('kind',['reference','output','report'])
def test_changed_bound_evidence_stales_assessment_without_losing_history(system,kind):
    store,did,source,ref,apply,t=case(system)
    apply('freeze_inventory',t,body=inventory(t));t=assessments.view(store,assessment_id=t['id'])
    if kind=='reference':
        req=request(document_id=did,source_sha256=source['content_hash'],action='revise',reference_id=ref['id'],guard=ref['guard'],note='Engineering reference change');req['actor']='Engineering validation'
        references.apply(store,req,source=source)
    else:
        with store.transaction() as db:
            doc=store._load(db,did)
            if kind=='output':doc['units'][1]['edits']['body']='Different text'
            else:doc['units'][0]['source_verification']['findings'].pop()
            store._save(db,doc)
    stale=assessments.view(store,assessment_id=t['id']);assert stale['stale_reasons']
    with pytest.raises(ValueError,match='assessment_stale'):apply('confirm',stale,body=adjudication(stale))
    assert assessments.view(store,assessment_id=t['id'])==stale


def test_artifact_tampering_and_wrong_reference_guard_fail_before_task_creation(system):
    store,did,source,ref,apply=prepared(system)
    with pytest.raises(ValueError,match='reload_and_compare'):apply('create',reference_id=ref['id'],reference_guard='wrong')
    (store.root/'source-verification/control.json').write_text('{}')
    with pytest.raises(ValueError,match='evidence_changed'):apply('create',reference_id=ref['id'],reference_guard=ref['guard'])
    assert assessments.view(store,reference_id=ref['id'])=={'items':[]}


def test_actor_guard_and_source_loss_replay(system):
    store,did,source,ref,apply,t=case(system)
    result,req=apply('save',t,body=inventory(t))
    with pytest.raises(ValueError,match='reload_and_compare'):apply('save',t,body=inventory(t))
    latest=assessments.view(store,assessment_id=t['id'])
    changed=request(document_id=did,source_sha256=source['content_hash'],action='save',assessment_id=t['id'],guard=latest['guard'],body=inventory(t));changed['actor']='Different engineer'
    with pytest.raises(ValueError,match='another_operator'):assessments.apply(store,changed,source=source)
    from pdf_extraction.orchestration.workflow import Runner
    runner=object.__new__(Runner);runner.store=store
    runner.handoff=lambda:pytest.fail('Replay must not reopen the original')
    assert runner.assessment_decision(req)==result
