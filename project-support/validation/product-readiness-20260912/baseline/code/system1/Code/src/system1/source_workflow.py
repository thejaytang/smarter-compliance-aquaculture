"""Source-only operation previews and append-only human re-review requests."""
import json
import uuid
from .workbook_guard import exclusive_process_lock
from .collaboration_review import _review
import human_operations as h
import source_updater as u


def preview(config_path, request):
    from .workbench_bridge import read
    source=next((s for s in read(config_path)['sources'] if s['source_id']==request['source_id']),None)
    if not source:raise ValueError('Unknown source.')
    if source['source_revision']!=request.get('expected_source_revision'):raise ValueError('Source changed; reopen the review.')
    review=_review(request['source_review']);proposed={**source,**review['fields']}
    if all(review['scores'].values()):proposed.update(review['scores']);proposed['operator_selection_decision']=review['selection']
    else:proposed['operator_selection_decision']='PENDING'
    from leader_orchestrator import review_trigger
    trigger=review_trigger(proposed)
    from .source_integrity import original_ready
    ready=original_ready(u.read_config(config_path),proposed,verify_hash=True)
    effective=u.selection_from_scores(proposed)
    if effective=='INCLUDE' and not ready:effective='PENDING'
    return {'effective_selection':effective,'remaining_reason':trigger[2] if trigger else '' if ready else 'A valid retained original is still required.',
        'original_ready':ready,
        'source_revision':source['source_revision'],'scope':'Preview only; explicit application and source checks still required.'}


def reopen(config_path, request):
    from .workbench_bridge import digest
    if request.get('actor')!='Weijie Tang':raise ValueError('Only the coordinator may start a main source review.')
    rid=str(uuid.UUID(request['request_id']));opid='REOPEN-'+rid
    note=str(request.get('note','')).strip()
    if not note or len(note)>10000:raise ValueError('Record why this source needs another review.')
    cfg=u.read_config(config_path)
    with exclusive_process_lock(cfg['log_root']/'.system1-run.lock'),u.registry_lock(cfg,12):
        wb=u.open_registry(cfg)
        try:
            stamp=u.registry_revision(cfg);wb._governance_actor=request['actor']
            ops=wb[h.human_sheet_name(cfg)];oh=h.operation_headers(ops);index=h.operation_index(ops,oh)
            if opid in index:
                prior=h.parse_payload(h.operation_record(ops,index[opid],oh).get('payload_json'))
                if prior.get('request_digest')!=digest(request):raise ValueError('Request identity conflict.')
                return {'status':'opened','operation_id':opid}
            ws=wb[cfg['sheet_name']];headers=u.workbook_headers(ws,int(cfg['header_row']));row=h.find_source_row(ws,headers,request['source_id'])
            if row is None:raise ValueError('Unknown source.')
            source=u.record_from_row(ws,row,headers)
            if h.source_record_fingerprint(source)!=request.get('expected_source_revision'):raise ValueError('Source changed; reopen the current source record.')
            h.append_operation(ops,oh,{'operation_id':opid,'operation_type':'SOURCE_REVIEW','source_id':request['source_id'],
                'source_title':source.get('source_title'),'trigger':'HUMAN_REVIEW_REQUEST','decision':'PENDING','program_status':'PENDING',
                'created_at':u.local_now(cfg),'operator_note':note,'payload_json':json.dumps({'source_fingerprint':h.source_record_fingerprint(source),
                    'action':'ACKNOWLEDGE_REVIEW','request_digest':digest(request),'requested_by':request['actor'],'reason':note})})
            h.prepare_human_workbook(wb,ops,oh);u.backup_registry(cfg,u.local_now(cfg));u.save_registry(wb,cfg,stamp)
            return {'status':'opened','operation_id':opid}
        finally:wb.close()
