"""Bound workbench error inventories and verifier adjudications.

Named workflow receipts authenticate local submissions, not independent human
truth or sample qualification. No study action changes ordinary A/B results.
"""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json

from ..contracts.hashing import digest, encoded
from ..evaluation.source_assessment import DIMENSIONS, evaluate
from ..verification.source_comparison import METHOD
from . import source_references
from .source_verification_input import comparison_input

INVENTORY_FIELDS = ('errors','reviewed_region_ids','reviewed_output_ids','reviewed_dimensions')
BODY_FIELDS = {*INVENTORY_FIELDS,'finding_decisions','unresolved','note','form_draft'}


def initialize(db):
    db.execute('CREATE TABLE IF NOT EXISTS source_assessment_tasks(id TEXT PRIMARY KEY, reference_id TEXT NOT NULL, data TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS source_assessment_events(sequence INTEGER PRIMARY KEY AUTOINCREMENT, assessment_id TEXT NOT NULL, data TEXT NOT NULL)')


def exists(db):
    return db.execute("SELECT 1 FROM sqlite_master WHERE name='source_assessment_tasks' AND type='table'").fetchone() is not None


def _load(db, identity):
    row=db.execute('SELECT data FROM source_assessment_tasks WHERE id=?',(identity,)).fetchone() if exists(db) else None
    if not row:raise ValueError('assessment_not_found')
    return json.loads(row[0])


def current_problems(store, db, task):
    reference=source_references._load(db,task['reference_id'])
    doc=store._load(db,task['document_id'])
    problems=[]
    if not doc['eligible'] or doc['source']['content_hash']!=task['source']['content_hash']:problems.append('original_changed_or_ineligible')
    if reference['status']!='reference_saved' or reference.get('reference_sha256')!=task['reference_sha256']:problems.append('reference_revision_changed')
    p=task['reference']['pages'][0]
    current=next((u.get('source_verification') for u in doc['units'] if u['id']=='coverage:pdf-page:'+str(p)),None)
    if not current or current.get('stale') or current.get('method')!=METHOD or digest(current)!=task['verification_sha256']:
        problems.append('verification_changed_or_stale')
    if digest(comparison_input(doc,p))!=task['records_sha256']:problems.append('effective_output_changed')
    return problems


def view(store, *, reference_id=None, assessment_id=None):
    with store.connect() as db:
        db.execute('BEGIN')
        if not exists(db):
            if assessment_id:raise ValueError('assessment_not_found')
            return {'items':[]}
        if not assessment_id:
            tasks=[json.loads(r[0]) for r in db.execute('SELECT data FROM source_assessment_tasks WHERE reference_id=? ORDER BY rowid DESC',(reference_id,))]
            return {'items':[dict({k:t[k] for k in ('id','status','actor','revision','created_at','reference_revision','findings_exposed')},
                                  stale_reasons=current_problems(store,db,t)) for t in tasks]}
        task=_load(db,assessment_id)
        result=deepcopy(task)
        result.update(guard=digest(task),stale_reasons=current_problems(store,db,task))
        history=[json.loads(r[0]) for r in db.execute('SELECT data FROM source_assessment_events WHERE assessment_id=? ORDER BY sequence',(assessment_id,))]
        result['history']=[{k:e[k] for k in ('action','actor','at','request_id','revision','body','report')} for e in history]
        # Withhold machine answers until the initial error inventory is frozen.
        # Once exposed, reopening never pretends this is a fresh blind pass.
        if not task['findings_exposed']:
            result.pop('verification',None)
            result['history']=[{k:v for k,v in e.items() if k!='report'} for e in result['history']]
        return result


def diagnostic(task, body, *, complete=False):
    assessment=dict(schema='pdf-source-assessment/1',status='complete' if complete else 'draft',
        evidence_class=task['evidence_class'],source_sha256=task['source']['content_hash'],
        reference_sha256=task['reference_sha256'],records_sha256=task['records_sha256'],
        verification_sha256=task['verification_sha256'],**{k:v for k,v in body.items() if k!='form_draft'})
    return evaluate(task['reference'],assessment,task['records'],task['verification'],source_sha256=task['source']['content_hash'])


def validate_body(body, task):
    if not isinstance(body,dict) or set(body)-BODY_FIELDS:raise ValueError('invalid_assessment_fields')
    body=deepcopy(body)
    for key in (*INVENTORY_FIELDS,'finding_decisions'):
        if not isinstance(body.get(key),list):raise ValueError('invalid_assessment_list')
    for key in ('unresolved','note'):
        if not isinstance(body.get(key),str):raise ValueError('assessment_notes_must_be_text')
    draft=body.get('form_draft',{})
    if not isinstance(draft,dict) or len(encoded(draft))>500000:raise ValueError('invalid_assessment_form_draft')
    if task['status']=='inventory' and body['finding_decisions']:raise ValueError('freeze_error_inventory_before_adjudication')
    if task['status']=='adjudication' and any(body[k]!=task['body'][k] for k in INVENTORY_FIELDS):raise ValueError('reopen_error_inventory_before_editing')
    for decision in body['finding_decisions']:
        if not isinstance(decision,dict) or not isinstance(decision.get('note'),str) or not decision['note'].strip():
            raise ValueError('finding_decision_evidence_required')
    diagnostic(task,body)
    return body


def freeze_input(store, db, reference):
    if reference['status']!='reference_saved':raise ValueError('confirm_source_reference_first')
    doc=store._load(db,reference['document_id']);p=reference['page_index']
    report=next((u.get('source_verification') for u in doc['units'] if u['id']=='coverage:pdf-page:'+str(p)),None)
    if not report or report.get('stale') or report.get('method')!=METHOD:raise ValueError('run_a_current_original_page_check_first')
    artifact=report.get('evidence_artifact',{})
    path=(store.root/artifact.get('path','')).resolve()
    if not path.is_relative_to((store.root/'source-verification').resolve()) or not path.is_file():raise ValueError('verification_evidence_missing')
    raw=path.read_bytes()
    if sha256(raw).hexdigest()!=artifact.get('sha256'):raise ValueError('verification_evidence_changed')
    bundle=json.loads(raw);records=bundle['records']
    if (report['source_sha256']!=reference['source']['content_hash']
            or bundle['original']['source_sha256']!=report['source_sha256']
            or report['page_index']!=p or bundle['original']['page_index']!=p
            or report['input_sha256']!=digest(records) or digest(comparison_input(doc,p))!=digest(records)):
        raise ValueError('reference_output_check_binding_mismatch')
    return deepcopy(records),deepcopy(report)


def apply(store, request, *, source, study_origin='operator_submission', evidence_class='natural', assert_current=lambda:None):
    with store.transaction() as db:
        replay=store._request(db,request)
        if replay is not None:return replay
        action=request['action'];now=datetime.now(timezone.utc).isoformat();before=None
        if action=='create':
            reference=source_references._load(db,request['reference_id'])
            if request.get('reference_guard')!=digest(reference):raise ValueError('reference_changed_reload_and_compare')
            if reference['source']['content_hash']!=source['content_hash'] or reference['document_id']!=request['document_id']:
                raise ValueError('assessment_source_binding_mismatch')
            records,verification=freeze_input(store,db,reference)
            if evidence_class not in {'natural','seeded','synthetic'}:raise ValueError('invalid_study_evidence_class')
            if study_origin!=reference['study_origin']:raise ValueError('reference_study_origin_changed')
            initialize(db)
            task=dict(id='assessment:'+request['request_id'],document_id=request['document_id'],reference_id=reference['id'],
                reference_revision=reference['revision'],reference_sha256=reference['reference_sha256'],reference=deepcopy(reference['reference']),
                source=deepcopy(source),records=records,records_sha256=digest(records),verification=verification,verification_sha256=digest(verification),
                actor=request['actor'],revision=1,status='inventory',created_at=now,study_origin=study_origin,evidence_class=evidence_class,
                qualification='unqualified',findings_exposed=False,
                body=dict(errors=[],reviewed_region_ids=[],reviewed_output_ids=[],reviewed_dimensions=[],finding_decisions=[],unresolved='',note=''),report=None)
        else:
            task=_load(db,request['assessment_id']);before=deepcopy(task)
            if task['actor']!=request['actor']:raise ValueError('assessment_belongs_to_another_operator')
            if request.get('guard')!=digest(task):raise ValueError('assessment_changed_reload_and_compare')
            if task['document_id']!=request['document_id'] or task['source']['content_hash']!=source['content_hash']:raise ValueError('assessment_source_binding_mismatch')
            if action=='reopen_inventory':
                if task['status'] not in {'adjudication','assessment_saved'} or not str(request.get('note','')).strip():raise ValueError('assessment_revision_reason_required')
                task['status']='inventory';task['body']['finding_decisions']=[];task['body']['reviewed_dimensions']=[]
                task['body']['note']=request['note'];task['body'].pop('form_draft',None);task['report']=None
            elif action in {'save','freeze_inventory','confirm'}:
                if task['status']=='assessment_saved':raise ValueError('reopen_inventory_before_editing_saved_assessment')
                task['body']=validate_body(request['body'],task)
                if action in {'freeze_inventory','confirm'}:
                    if any(task['body'].get('form_draft',{}).get(k) for k in ('error_dirty','finding_dirty')):raise ValueError('stage_or_clear_assessment_form_before_confirmation')
                    if not task['body']['note'].strip():raise ValueError('assessment_confirmation_evidence_required')
                if action=='freeze_inventory':
                    if task['status']!='inventory':raise ValueError('error_inventory_already_frozen')
                    body=task['body']
                    if (set(body['reviewed_region_ids'])!={r['id'] for r in task['reference']['regions']}
                            or set(body['reviewed_output_ids'])!={r['id'] for r in task['records']}
                            or set(body['reviewed_dimensions'])!=DIMENSIONS or body['unresolved'].strip()):
                        raise ValueError('complete_original_and_output_inventory_first')
                    task['status']='adjudication';task['findings_exposed']=True;task['inventory_frozen_at']=now
                if action=='confirm':
                    if task['status']!='adjudication':raise ValueError('freeze_error_inventory_before_adjudication')
                    report=diagnostic(task,task['body'],complete=True)
                    if report['incomplete']:raise ValueError('complete_all_finding_adjudications_first')
                    task['status']='assessment_saved';task['report']=report
            else:raise ValueError('unknown_assessment_action')
            task['revision']+=1
        if request['source_sha256']!=source['content_hash'] or source.get('file_format')!='pdf':raise ValueError('assessment_source_binding_mismatch')
        problems=current_problems(store,db,task)
        if problems:raise ValueError('assessment_stale:'+','.join(problems))
        assert_current()
        event=dict(action=action,actor=request['actor'],at=now,request_id=request['request_id'],revision=task['revision'],
                   body=deepcopy(task['body']),report=deepcopy(task['report']),before=before,after=deepcopy(task))
        db.execute('INSERT OR REPLACE INTO source_assessment_tasks VALUES(?,?,?)',(task['id'],task['reference_id'],encoded(task)))
        db.execute('INSERT INTO source_assessment_events(assessment_id,data) VALUES(?,?)',(task['id'],encoded(event)))
        return store._receipt(db,request,dict(status='saved',assessment_id=task['id'],revision=task['revision'],assessment_status=task['status'],
            guard=digest(task),qualification='unqualified',independent_acceptance='not_assessed'))
