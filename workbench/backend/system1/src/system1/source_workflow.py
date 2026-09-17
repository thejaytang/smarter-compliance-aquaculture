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
    if request.get('actor')!='Weijie Tang' and not (request.get('peer_sync') is True and request.get('actor') in {'Ana Jokic','Daniel Restad'}):raise ValueError('Only the coordinator may start a main source review.')
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


def intake(config_path, request):
    """Stage a named-human candidate in the existing governed operation ledger."""
    from pathlib import Path
    from urllib.parse import urlsplit
    import shutil
    from .workbench_bridge import digest
    if request.get('actor') != 'Weijie Tang' and not (request.get('peer_sync') is True and request.get('actor') in {'Ana Jokic','Daniel Restad'}): raise ValueError('Only the coordinator may stage source intake.')
    generated=set(h.EDITABLE_CANDIDATE_FIELDS)-{'operator_selection_decision','source_status'}
    allowed={'request_id','actor','peer_sync','note','upload_path','upload_hash','upload_root','basic_inspection',*generated}
    if set(request)-allowed: raise ValueError('Unsupported intake fields.')
    rid=str(uuid.UUID(request['request_id'])); opid='INTAKE-'+rid
    fields={k:str(request.get(k) or '').strip() for k in (generated|{'note'})}
    if not fields['source_title']: raise ValueError('Enter the source title.')
    if any(len(v)>4000 or v.startswith('=') for v in fields.values()): raise ValueError('Invalid intake field.')
    for key in ('official_url','retrieval_url'):
        value=fields[key]
        if value:
            url=urlsplit(value)
            if url.scheme not in ('https','http') or not url.hostname or url.username or url.password: raise ValueError('Use a public HTTP or HTTPS source link without credentials.')
    if not fields['official_url'] and not request.get('upload_path'): raise ValueError('Provide a source link or original file.')
    inspection=request.get('basic_inspection')
    if inspection and (not isinstance(inspection,dict) or inspection.get('schema')!='source-basic-inspection/1' or inspection.get('content_hash')!=request.get('upload_hash')):raise ValueError('Inspection does not match the original.')
    cfg=u.read_config(config_path)
    with exclusive_process_lock(cfg['log_root']/'.system1-run.lock'),u.registry_lock(cfg,12):
        wb=u.open_registry(cfg)
        try:
            stamp=u.registry_revision(cfg); wb._governance_actor=request['actor']
            ops=wb[h.human_sheet_name(cfg)]; oh=h.operation_headers(ops); index=h.operation_index(ops,oh)
            if opid in index:
                previous=h.parse_payload(h.operation_record(ops,index[opid],oh).get('payload_json'))
                if previous.get('request_digest')!=digest(request): raise ValueError('Request identity conflict.')
                return previous['intake_receipt']
            for existing_id, row in index.items():
                existing=h.operation_record(ops,row,oh); old=h.parse_payload(existing.get('payload_json'))
                if existing.get('program_status') not in h.OPEN_STATUSES or not old.get('intake_receipt'):continue
                same_file=bool(request.get('upload_hash') and request.get('upload_hash')==old.get('content_hash'))
                same_link=bool(not request.get('upload_path') and fields['official_url'] and fields['official_url'].rstrip('/').lower()==str(old.get('official_url') or '').rstrip('/').lower() and fields['version']==str(old.get('version') or ''))
                if same_file or same_link:
                    if inspection and not old.get('basic_inspection'):
                        for key,value in fields.items():
                            if not old.get(key):old[key]=value
                        old['basic_inspection']=inspection
                        updates={k:v for k,v in fields.items() if k in oh and not existing.get(k)}
                        updates.update(payload_json=json.dumps(old,ensure_ascii=False,sort_keys=True),program_note='Basic inspection added to this pending candidate. Existing human input is retained.')
                        h.set_operation_fields(ops,row,oh,updates);u.backup_registry(cfg,u.local_now(cfg));u.save_registry(wb,cfg,stamp)
                    return {**old['intake_receipt'],'existing_candidate':True}
            ws=wb[cfg['sheet_name']]; headers=u.workbook_headers(ws,int(cfg['header_row']))
            duplicate=''; version_of=''
            for row in range(int(cfg['data_start_row']),ws.max_row+1):
                record=u.record_from_row(ws,row,headers)
                if fields['official_url'] and fields['official_url'].rstrip('/').lower()==str(record.get('official_url') or '').rstrip('/').lower():
                    duplicate=record.get('source_id') or ''
                    if fields['version'] and fields['version']!=str(record.get('version') or ''): version_of=duplicate
                    break
            payload={**fields,'notes':fields.get('source_notes',''),'basic_inspection':inspection,'candidate_origin':'HUMAN_WEB','operator_selection_decision':'PENDING','request_digest':digest(request),'requested_by':request['actor'],'duplicate_source_id':duplicate,'version_of_source_id':version_of}
            if request.get('upload_path'):
                source=Path(request['upload_path']).resolve(); root=Path(request['upload_root']).resolve()
                if source.parent!=root or not source.is_file() or u.sha256_file(source)!=request.get('upload_hash'): raise ValueError('Staged original changed or is outside the upload area.')
                if source.suffix.lower() not in ('.pdf','.html','.htm','.xlsx'): raise ValueError('Unsupported original format.')
                target_root=cfg.get('manual_intake_root')
                if target_root is None: raise ValueError('Manual intake storage is unavailable.')
                target_root=Path(target_root);target_root.mkdir(parents=True,exist_ok=True)
                target=target_root/(rid+source.suffix.lower())
                if target.exists() and u.sha256_file(target)!=request['upload_hash']: raise ValueError('Intake original identity conflict.')
                if not target.exists(): shutil.copy2(source,target)
                payload.update(intake_file=target.name,content_hash=request['upload_hash'],manual_file_format=source.suffix.lower().lstrip('.'),candidate_origin='HUMAN_DROP')
                payload['file_format']=fields['file_format'] or ('html' if source.suffix.lower()=='.htm' else source.suffix.lower().lstrip('.'))
            replacement=bool(duplicate and payload.get('intake_file'))
            receipt={'status':'pending_review','operation_id':opid,'duplicate_source_id':duplicate,'version_of_source_id':version_of}
            payload['intake_receipt']=receipt
            values={k:v for k,v in payload.items() if k in oh}
            values.update(operation_id=opid,operation_type='MANUAL_FILE_REPLACEMENT' if replacement else 'NEW_SOURCE_CANDIDATE',source_id=duplicate,source_title=fields['source_title'],trigger='HUMAN_FILE_REPLACEMENT' if replacement else 'POSSIBLE_DUPLICATE' if duplicate else 'HUMAN_WEB_INTAKE',decision='PENDING',program_status='PENDING',created_at=u.local_now(cfg),operator_note=fields['note'],program_note='Basic content inspection completed; review the generated fields and flagged items.' if inspection else 'Human acceptance and source review are required. No source selection has changed.',payload_json=json.dumps(payload,ensure_ascii=False,sort_keys=True))
            h.append_operation(ops,oh,values)
            h.prepare_human_workbook(wb,ops,oh);u.backup_registry(cfg,u.local_now(cfg));u.save_registry(wb,cfg,stamp)
            return receipt
        finally: wb.close()


def intake_original(config_path, operation_id):
    from pathlib import Path
    cfg=u.read_config(config_path);wb=u.open_registry(cfg)
    try:
        ops=wb[h.human_sheet_name(cfg)];oh=h.operation_headers(ops);index=h.operation_index(ops,oh)
        if operation_id not in index:raise ValueError('Unknown intake task.')
        op=h.operation_record(ops,index[operation_id],oh);payload=h.parse_payload(op.get('payload_json'))
        if op.get('operation_type') not in ('NEW_SOURCE_CANDIDATE','MANUAL_FILE_REPLACEMENT'):raise ValueError('This task has no intake original.')
        root=Path(cfg['manual_intake_root']).resolve();path=(root/str(op.get('intake_file') or payload.get('intake_file') or '')).resolve()
        expected=payload.get('content_hash')
        if path.parent!=root or not path.is_file() or not expected or u.sha256_file(path)!=expected:raise ValueError('The retained intake original is unavailable or changed.')
        return {'path':str(path),'root':str(root),'hash':expected}
    finally:wb.close()
