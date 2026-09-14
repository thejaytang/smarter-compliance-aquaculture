"""Engineering-only reference transactions; never independent human labels."""
from copy import deepcopy
import pytest
from pdf_extraction.contracts.hashing import digest
from pdf_extraction.review import source_references as references
from .test_two_stage_workflow import system,current,request


def prepare(system):
    store,did=system
    with store.transaction() as db:
        d=store._load(db,did);d['source']['file_format']='pdf';d['total_pages']=2;store._save(db,d)
    source=current(system)['source']
    def send(action,task=None,**extra):
        req=request(document_id=did,source_sha256=source['content_hash'],action=action,**extra);req['actor']='Engineering validation'
        if task:req.update(reference_id=task['id'],guard=task['guard'])
        result=references.apply(store,req,source=source,dimensions={'0':{'width':600,'height':800},'1':{'width':600,'height':800}},study_origin='engineering_fixture')
        return result,req
    return store,did,source,send


def draft():
    return dict(regions=[dict(id='r1',role='text',page_index=0,bbox=[10,10,200,40],text='Fish farms shall keep records.')],
        relations=[],survey=dict(content=True,structure=True,relationships=True),prior_exposure='seen_outputs',
        assistance='Known synthetic control',unresolved='',note='Engineering transaction control; not human reference acceptance.')


def start(system):
    store,did,source,send=prepare(system)
    result,req=send('create',page_index=0,supporting_pages=[1])
    return store,did,source,send,references.view(store,reference_id=result['reference_id'])


def test_blank_reference_is_source_only_and_does_not_touch_business_results(system):
    store,did,source,send=prepare(system);before=deepcopy(current(system))
    assert references.view(store,document_id=did)=={'items':[]}
    with store.connect() as db:assert not references.exists(db)
    result,req=send('create',page_index=0,supporting_pages=[1]);task=references.view(store,reference_id=result['reference_id'])
    assert task['body']['regions']==[] and task['body']['relations']==[]
    assert task['purpose']=='development' and task['qualification']=='unqualified'
    assert current(system)==before
    assert references.apply(store,req,source=source)==result
    assert len(references.view(store,reference_id=task['id'])['history'])==1


def test_unstaged_draft_survives_restart_and_cannot_be_confirmed(system):
    store,did,source,send,t=start(system);body=draft()
    body['form_draft']={'region_dirty':True,'fields':{'text':'Partially typed original','x0':''}}
    result,_=send('save',t,body=body)
    from pdf_extraction.review.workflow import Workflow
    t=references.view(Workflow(store.root),reference_id=t['id'])
    assert t['body']['form_draft']['fields']['text']=='Partially typed original'
    with pytest.raises(ValueError,match='stage_or_clear'):send('confirm',t,body=body)
    assert references.view(store,reference_id=t['id'])==t


def test_reference_revisions_keep_prior_source_answer_and_history(system):
    store,did,source,send,t=start(system);before=deepcopy(current(system))
    send('confirm',t,body=draft());saved=references.view(store,reference_id=t['id']);old=deepcopy(saved['reference'])
    assert saved['status']=='reference_saved' and saved['reference_sha256']==digest(old)
    assert saved['reference']['origin']=='engineering_fixture'
    with pytest.raises(ValueError,match='new_reference_revision'):send('save',saved,body=draft())
    send('revise',saved,note='Compare a corrected engineering reference version')
    revised=references.view(store,reference_id=t['id']);assert revised['assessment_stale'] and not revised['body']['survey']
    body=draft();body['regions'][0]['text']='Fish farms shall not keep these records.'
    send('confirm',revised,body=body);final=references.view(store,reference_id=t['id'])
    assert final['reference_sha256']!=saved['reference_sha256']
    assert next(e for e in final['history'] if e['action']=='confirm')['after']['reference']==old
    assert current(system)==before


@pytest.mark.parametrize('change,match',[
    (lambda b:b['regions'][0].update(bbox=[0,0,999,20]),'outside_original'),
    (lambda b:b.update(unresolved='Unreadable original area'),'complete_original_survey'),
    (lambda b:b['survey'].update(content=False),'complete_original_survey'),
    (lambda b:b['regions'][0].update(role='unknown'),'resolve_unknown'),
    (lambda b:b['regions'][0].update(text=''),'transcribe_original'),
    (lambda b:b.update(prior_exposure='unknown'),'prior_reference_exposure_before'),
    (lambda b:b['relations'].append(dict(id='link',kind='footnote',from_ids=['r1'],to_ids=['missing'])),'target_missing'),
])
def test_incomplete_or_inconsistent_reference_never_completes(system,change,match):
    store,did,source,send,t=start(system);body=draft();change(body)
    with pytest.raises(ValueError,match=match):send('confirm',t,body=body)
    assert references.view(store,reference_id=t['id'])==t


def test_grid_and_cross_page_note_are_kept_with_original_locations(system):
    store,did,source,send,t=start(system);body=draft()
    body['regions']=[dict(id='table',role='table',page_index=0,bbox=[10,10,200,100],text='',row_count=1,column_count=2),
        dict(id='cell',role='table_cell',page_index=0,bbox=[10,10,200,100],text='Shared value',table_id='table',row=0,column=0,row_span=1,column_span=2),
        dict(id='note',role='footnote',page_index=1,bbox=[10,600,200,630],text='1 The exception applies only at low temperature.')]
    body['relations']=[dict(id='link',kind='footnote',from_ids=['cell'],to_ids=['note'],marker='1',explanation='Known engineering cross-page marker relationship.')]
    send('confirm',t,body=body);t=references.view(store,reference_id=t['id'])
    assert t['reference']['regions'][1]['column_span']==2
    assert t['reference']['relations'][0]['to_ids']==['note'] and t['reference']['supporting_pages']==[1]


def test_owner_guard_and_original_drift_are_atomic(system):
    store,did,source,send,t=start(system)
    req=request(document_id=did,source_sha256=source['content_hash'],action='save',reference_id=t['id'],guard=t['guard'],body=draft());req['actor']='Different test operator'
    with pytest.raises(ValueError,match='another_operator'):references.apply(store,req,source=source)
    send('save',t,body=draft())
    with pytest.raises(ValueError,match='reload_and_compare'):send('save',t,body=draft())
    latest=references.view(store,reference_id=t['id'])
    req.update(request_id=request()['request_id'],actor=t['actor'],guard=latest['guard'])
    def drift():raise ValueError('original_changed_during_save')
    with pytest.raises(ValueError,match='original_changed'):references.apply(store,req,source=source,assert_current=drift)
    assert references.view(store,reference_id=t['id'])==latest


def test_runner_replays_saved_receipt_when_current_original_has_become_unavailable(system):
    store,did,source,send,t=start(system)
    receipt,req=send('save',t,body=draft())
    from pdf_extraction.orchestration.workflow import Runner
    runner=object.__new__(Runner);runner.store=store
    def unavailable():raise AssertionError('Saved receipt replay must not acquire a new original')
    runner.handoff=unavailable
    assert runner.reference_decision(req)==receipt
    req['body']['note']='Different payload'
    with pytest.raises(ValueError,match='different_payload'):runner.reference_decision(req)


@pytest.mark.parametrize('change',[
    lambda b:b.update(regions=[None]),
    lambda b:b.update(relations=[None]),
    lambda b:b.update(relations=[dict(id='l',kind='context',from_ids='r1',to_ids=['r1'])]),
])
def test_malformed_reference_edits_are_definite_rejections_and_preserve_draft(system,change):
    store,did,source,send,t=start(system);body=draft();change(body)
    with pytest.raises(ValueError):send('save',t,body=body)
    assert references.view(store,reference_id=t['id'])==t
