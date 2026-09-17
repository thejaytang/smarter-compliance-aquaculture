"""Explicit coordinator adoption of an offline source review, without a routine cycle."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import uuid

import human_operations as h
import source_updater as u
from .workbook_guard import exclusive_process_lock

COORDINATOR = 'Weijie Tang'
CONTRIBUTORS = {'Weijie Tang', 'Ana Jokic', 'Daniel Restad'}
SOURCE_FIELDS = {'official_url', 'retrieval_url', 'issuer', 'version', 'provenance_status',
                 'acquisition_channel', 'applicability_reference', 'inclusion_rationale', 'primary_source_id'}


def review_document(source, cfg=None):
    effective=source.get('effective_selection') or u.selection_from_scores(source)
    if cfg and effective=='INCLUDE':
        from .source_integrity import original_ready
        if not original_ready(cfg,source):effective='PENDING'
    return {'fields': {k: source.get(k) or '' for k in SOURCE_FIELDS},
            'scores': {k: source.get(k) or '' for k in u.SCORE_FIELDS},
            'selection': effective, 'note': '', 'issue_verified': False, 'issue_checks': {}, 'task_checks': {}, 'new_issues': []}


def _review(value):
    value=deepcopy(value)
    if isinstance(value,dict):value.setdefault('issue_checks',{});value.setdefault('task_checks',{});value.setdefault('new_issues',[])
    if not isinstance(value, dict) or set(value) != {'fields', 'scores', 'selection', 'note', 'issue_verified','issue_checks','task_checks','new_issues'}:
        raise ValueError('A complete source review envelope is required.')
    if not isinstance(value['fields'], dict) or set(value['fields']) != SOURCE_FIELDS:
        raise ValueError('Source correction fields do not match the supported field set.')
    if not isinstance(value['scores'], dict) or set(value['scores']) != set(u.SCORE_FIELDS):
        raise ValueError('All five score slots are required; use an empty value for unfinished scores.')
    for key, field in value['fields'].items():
        if not isinstance(field, str) or len(field) > 4000 or field.startswith('='):
            raise ValueError('Invalid source field: '+key)
        if key.endswith('_url') and field:
            from .workbench_bridge import safe_url
            safe_url(field)
    if any(v not in ('', 'HIGH', 'MEDIUM', 'LOW') for v in value['scores'].values()):
        raise ValueError('Scores must be HIGH, MEDIUM, LOW or unfinished.')
    if value['selection'] not in ('INCLUDE', 'PENDING', 'EXCLUDE'):
        raise ValueError('Invalid source selection.')
    if not isinstance(value['note'], str) or len(value['note']) > 12000:
        raise ValueError('A source review note must be text of at most 12000 characters.')
    if type(value['issue_verified']) is not bool:
        raise ValueError('Issue verification requires an explicit boolean.')
    if not isinstance(value['issue_checks'],dict) or any(not isinstance(k,str) or not isinstance(v,str) or len(v)!=64 for k,v in value['issue_checks'].items()):raise ValueError('Invalid issue evidence checks.')
    if not isinstance(value['task_checks'],dict) or any(not isinstance(k,str) or not isinstance(v,str) or len(v)!=64 for k,v in value['task_checks'].items()):raise ValueError('Invalid source task checks.')
    issues=value['new_issues']
    if not isinstance(issues,list) or len(issues)>100 or len({i.get('id') for i in issues if isinstance(i,dict)})!=len(issues):raise ValueError('Invalid new source issues.')
    for issue in issues:
        if set(issue)!={'id','note'} or not isinstance(issue['note'],str) or not issue['note'].strip() or len(issue['note'])>4000:raise ValueError('Describe the source problem.')
        uuid.UUID(issue['id'])
    return value


def collaboration_apply(config_path: Path, request: dict) -> dict:
    """Atomically adopt valid fields and append a durable receipt in the owning store.

    An incomplete score bundle is staged intact, never combined with older scores.
    Receipt lookup precedes source-version checks, so retries after a committed write
    return the same result. Reuse of a request id for different input is rejected.
    """
    actor=request.get('actor')
    allowed=actor==COORDINATOR or (request.get('peer_sync') is True and actor in CONTRIBUTORS)
    if not allowed or request.get('contributor') not in CONTRIBUTORS:
        raise ValueError('Only the coordinator may adopt work from a named reviewer.')
    rid = str(uuid.UUID(request['request_id']))
    submission = str(uuid.UUID(request['submission_id']))
    source_id = request.get('source_id')
    if not isinstance(source_id, str) or not source_id:
        raise ValueError('A source identity is required.')
    digest = hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False,
                                      allow_nan=False).encode()).hexdigest()
    cfg = u.read_config(config_path)
    with exclusive_process_lock(cfg['log_root'] / '.system1-run.lock'), u.registry_lock(cfg, 12):
        wb = u.open_registry(cfg)
        try:
            stamp = u.registry_revision(cfg)
            wb._governance_actor = actor
            ops = wb[h.human_sheet_name(cfg)]
            oh = h.operation_headers(ops)
            prior_ops = []
            opid = 'COLLAB-' + rid
            for row in range(h.HUMAN_DATA_START_ROW, h.last_operation_row(ops, oh) + 1):
                record = h.operation_record(ops, row, oh)
                payload = h.parse_payload(record.get('payload_json'))
                if record.get('operation_id') == opid:
                    receipt = payload.get('collaboration_receipt')
                    if payload.get('request_digest') != digest or not receipt:
                        raise ValueError('Collaboration request identity was reused or its receipt is invalid.')
                    return receipt
                if record.get('source_id') == source_id:
                    prior_ops.append((row, record, payload))
            review, base = _review(request['review']), _review(request['base_review'])
            ws = wb[cfg['sheet_name']]
            sh = u.workbook_headers(ws, int(cfg['header_row']))
            row = h.find_source_row(ws, sh, source_id)
            if row is None:
                raise ValueError('Unknown source; collaboration cannot create sources.')
            source = u.record_from_row(ws, row, sh)
            if request.get('expected_source_revision') != h.source_record_fingerprint(source):
                raise ValueError('STALE: source changed; prepare a new comparison.')
            if request.get('expected_source_hash') != source.get('content_hash'):
                raise ValueError('STALE: source original changed; prepare a new comparison.')
            from .selection_gate import project, pending_include_tasks
            baseline_source={**source,'effective_selection':u.selection_from_scores(source)}
            project([baseline_source],[rec for _,rec,_ in prior_ops if rec.get('program_status') in h.OPEN_STATUSES])
            if base != review_document(baseline_source,cfg):
                raise ValueError('STALE: source review baseline no longer matches the owning record.')
            updates = {key: value for key, value in review['fields'].items() if value != base['fields'][key]}
            score_changed = review['scores'] != base['scores']
            selection_changed = review['selection'] != base['selection']
            complete = all(review['scores'].values())
            reasons = []
            if not complete:
                reasons.append('The five-score bundle is unfinished; scores and selection remain staged.')
            elif score_changed or selection_changed:
                scores, selection = list(review['scores'].values()), review['selection']
                if selection == 'INCLUDE' and scores != ['HIGH'] * 5:
                    raise ValueError('INCLUDE requires a consistent complete five-HIGH score bundle.')
                if 'LOW' in scores and selection != 'EXCLUDE':
                    raise ValueError('A LOW score requires EXCLUDE; resolve the score/selection conflict.')
                if selection in ('PENDING', 'EXCLUDE') and not review['note'].strip():
                    raise ValueError('PENDING or EXCLUDE requires a reason.')
                updates.update(review['scores'])
                updates['operator_selection_decision'] = selection
            issue_ops = [(r, rec, p) for r, rec, p in prior_ops
                         if rec.get('program_status') in h.OPEN_STATUSES
                         and p.get('human_reported_issue') and not p.get('human_reported_issue_resolved')]
            if review['issue_verified'] and not review['note'].strip():
                raise ValueError('Explicit source issue verification requires a note describing the check.')
            from .source_integrity import original_ready
            original_invalid=u.selection_from_scores({**source,**updates})=='INCLUDE' and not original_ready(cfg,source,verify_hash=True)
            if original_invalid:
                reasons.append('The retained original is missing or differs from its registered fingerprint; it must be restored or explicitly replaced.')
            selected_tasks=[]
            for task_id,revision in review['task_checks'].items():
                found=next(((r,rec,p) for r,rec,p in prior_ops if rec['operation_id']==task_id),None)
                if not found or found[1]['operation_type'] not in ('SOURCE_REVIEW','SELECTION_REVIEW') or hashlib.sha256(json.dumps(found[1],sort_keys=True,default=str).encode()).hexdigest()!=revision:raise ValueError('STALE: selected source task changed; compare the current task.')
                selected_tasks.append(found)
            current_time = u.local_now(cfg)
            # Reuse the owning update function, including timestamp and additive notes.
            action = 'APPLY_FIELD_UPDATES' if updates else 'ACKNOWLEDGE_REVIEW'
            operation = {'source_id': source_id, 'operator': actor,
                         'operator_note': review['note']}
            h.apply_source_action(ws, sh, operation, {'action': action, 'updates': updates}, current_time)
            if original_invalid:ws.cell(row,sh['snapshot_status'],'MISSING')
            after = u.record_from_row(ws, row, sh)
            from leader_orchestrator import review_trigger
            effective = u.selection_from_scores(after)
            trigger = review_trigger(after)
            if effective == 'PENDING':
                reasons.append('Source selection remains PENDING under the owning selection gates.')
            if trigger:
                reasons.append('Source acquisition or governance remains unresolved: '+trigger[0])
            unresolved_issues = []
            for issue_row, record, payload in issue_ops:
                issue=payload['human_reported_issue']
                reports=[issue,*issue.get('related_reports',[])];changed=False
                for report in reports:
                    issue_digest=hashlib.sha256(json.dumps(report,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()
                    key=record['operation_id']+':'+issue_digest
                    if review['issue_checks'].get(key)==issue_digest:
                        if not review['note'].strip():raise ValueError('Describe the evidence for this issue check.')
                        changed=True;report['resolved']=True;report['resolution']={'actor':actor,'contributor':request['contributor'],'submission_id':submission,'note':review['note'],'at':current_time.isoformat()}
                closed=all(r.get('resolved') is True for r in reports)
                if changed:
                    payload['human_reported_issue_resolved']=closed
                    h.set_operation_fields(ops,issue_row,oh,{'payload_json':json.dumps(payload,sort_keys=True,ensure_ascii=False),
                        'program_status':'APPLIED' if closed else record['program_status'],
                        'program_note':'Selected reported issues checked; remaining issues stay pending.'})
                if not closed:unresolved_issues.append(record['operation_id'])
            if unresolved_issues:reasons.append('Reported source issues still require specific evidence-bound checks.')
            if review['issue_verified'] and not review['issue_checks']:
                reasons.append('Legacy general issue confirmation retained as evidence only; check individual current issues.')
            for reported in review['new_issues']:
                issue_id='REPORTED-'+reported['id']
                existing=next(((rec,p) for _,rec,p in prior_ops if rec['operation_id']==issue_id),None)
                if existing:
                    if existing[1].get('human_reported_issue',{}).get('reason')!=reported['note']:raise ValueError('Reported issue identity was reused.')
                    if existing[0].get('program_status') in h.OPEN_STATUSES:reasons.append('Reported source problem remains open: '+issue_id)
                    continue
                report={'reason':reported['note'],'action':'Verify this specific source problem.','evidence_id':reported['id'],'reported_by':request['contributor'],'reported_at':current_time.isoformat()}
                h.append_operation(ops,oh,{'operation_id':issue_id,'operation_type':'SOURCE_REVIEW','source_id':source_id,'source_title':source.get('source_title'),'trigger':'HUMAN_REPORTED_ISSUE','decision':'PENDING','program_status':'WAITING_FOR_HUMAN','created_at':current_time,'payload_json':json.dumps({'human_reported_issue':report,'source_fingerprint':h.source_record_fingerprint(after),'action':'APPLY_FIELD_UPDATES'},sort_keys=True)})
                reasons.append('New reported source problem requires verification: '+issue_id)
            if pending_include_tasks(after,[rec for _,rec,_ in prior_ops if rec.get('program_status') in h.OPEN_STATUSES]) and review['selection']=='PENDING':
                reasons.append('Choose Include after re-review, or Exclude to stop using this source.')
            if not reasons:
                for task_row,task,task_payload in selected_tasks:
                    if task.get('program_status') not in h.OPEN_STATUSES:continue
                    task_payload.update(resolved_by_collaboration=opid,contributor=request['contributor'])
                    h.set_operation_fields(ops,task_row,oh,{'program_status':'APPLIED','program_operated_at':current_time,'payload_json':json.dumps(task_payload,sort_keys=True,ensure_ascii=False),'program_note':'Explicit source task check adopted in '+opid})
            from .selection_gate import pending_include_tasks
            remaining=[]
            for pending_row in range(h.HUMAN_DATA_START_ROW,h.last_operation_row(ops,oh)+1):
                pending=h.operation_record(ops,pending_row,oh)
                if pending.get('program_status') in h.OPEN_STATUSES:remaining.append(pending)
            if effective=='INCLUDE' and pending_include_tasks(after,remaining):
                effective='PENDING';reasons.append('Previously included source requires explicit completion of its remaining source review tasks.')
            receipt = {'status': 'saved_partial' if reasons else 'applied', 'request_id': rid,
                       'operation_id': opid, 'source_id': source_id,
                       'source_revision': h.source_record_fingerprint(after),
                       'effective_selection': effective, 'unresolved_reasons': reasons,
                       'submission_id': submission, 'contributor': request['contributor'], 'actor': actor}
            payload = {'action': 'ACKNOWLEDGE_REVIEW', 'updates': {}, 'source_id': source_id,
                       'source_fingerprint': h.source_record_fingerprint(after),
                       'request_digest': digest, 'collaboration_receipt': receipt,
                       'base_review': base, 'adopted_review': review,
                       'adopted_fields': updates, 'issue_operation_ids': [rec['operation_id'] for _, rec, _ in issue_ops]}
            h.append_operation(ops, oh, {'operation_id': opid, 'operation_type': 'SOURCE_REVIEW',
                'source_id': source_id, 'source_title': source.get('source_title'),
                'trigger': 'OFFLINE_COLLABORATION_ADOPTION', 'proposed_action': 'ACKNOWLEDGE_REVIEW',
                'decision': 'PENDING' if reasons else 'ACCEPT', 'operator': actor,
                'operator_note': review['note'], 'checked_at': current_time, 'created_at': current_time,
                'program_status': 'WAITING_FOR_HUMAN' if reasons else 'APPLIED',
                'program_operated_at': current_time,
                'program_note': '; '.join(reasons) if reasons else 'Coordinator adopted the submitted source review.',
                'payload_json': json.dumps(payload, sort_keys=True, ensure_ascii=False)})
            h.prepare_human_workbook(wb, ops, oh)
            u.backup_registry(cfg, current_time)
            u.save_registry(wb, cfg, stamp)
            return receipt
        finally:
            wb.close()
