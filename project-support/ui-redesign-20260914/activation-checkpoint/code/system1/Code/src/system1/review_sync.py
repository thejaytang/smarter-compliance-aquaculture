"""Workbook-owned source issue handoff and machine confidence synchronization."""
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from openpyxl import load_workbook
import human_operations as h
import source_updater as u
from .workbook_guard import exclusive_process_lock
from .source_assessment import sync_confidence_sheet


def confidence(config):
    cfg=u.read_config(config);database=cfg['log_root']/'source-assessments.sqlite'
    if cfg.get('governance_db'):
        from .governance_export import sync
        return sync(cfg)
    if not database.exists():return {'status':'no_assessments'}
    fingerprint=sha256(database.read_bytes()).hexdigest();marker=cfg['log_root']/'confidence-export.json'
    if marker.exists() and json.loads(marker.read_text()).get('fingerprint')==fingerprint:return {'status':'current'}
    with exclusive_process_lock(cfg['log_root']/'.system1-run.lock'):
        with u.registry_lock(cfg,12):
            wb=u.open_registry(cfg);stamp=u.registry_revision(cfg)
            sync_confidence_sheet(wb,database)
            u.backup_registry(cfg,datetime.now())
            u.save_registry(wb,cfg,stamp);wb.close()
            marker.write_text(json.dumps({'fingerprint':fingerprint}))
    return {'status':'applied'}


def source_issue(config, request):
    cfg=u.read_config(config);note=str(request.get('note','')).strip();actor=str(request.get('actor','')).strip()
    import uuid
    rid=str(uuid.UUID(request['request_id']))
    if not note or not actor:raise ValueError('Named reviewer and original problem description required.')
    with exclusive_process_lock(cfg['log_root']/'.system1-run.lock'):
        with u.registry_lock(cfg,12):
            wb=u.open_registry(cfg);stamp=u.registry_revision(cfg)
            ops=wb[h.human_sheet_name(cfg)];headers=h.operation_headers(ops);opid='SYS2-'+rid
            for row in range(3,h.last_operation_row(ops,headers)+1):
                op=h.operation_record(ops,row,headers)
                prior=h.parse_payload(op['payload_json'])
                replay=prior.get('system2_handoffs',{}).get(rid)
                if replay:
                    if replay['digest']!=sha256(json.dumps(request,sort_keys=True).encode()).hexdigest():raise ValueError('Request ID already used with different content.')
                    wb.close();return {'status':'applied','task_id':op['operation_id']}
                if op.get('operation_id')==opid:
                    if prior.get('handoff_digest')!=sha256(json.dumps(request,sort_keys=True).encode()).hexdigest():raise ValueError('Request ID already used with different content.')
                    wb.close();return {'status':'applied','task_id':opid}
            sourcews=wb[cfg['sheet_name']];cols=u.workbook_headers(sourcews,2)
            row=h.find_source_row(sourcews,cols,request['source_id'])
            if row is None:raise ValueError('Registered source not found.')
            source=u.record_from_row(sourcews,row,cols)
            if source.get('content_hash')!=request['source_sha256']:raise ValueError('Original source version changed.')
            issue={'reason':note,'action':'Verify the original or supply a complete replacement.','evidence_id':rid,'operator':actor,'system2_document_id':request['document_id'],'source_sha256':request['source_sha256']}
            payload={'action':'APPLY_FIELD_UPDATES','source_id':request['source_id'],'updates':{},'source_fingerprint':h.source_record_fingerprint(source),'human_reported_issue':issue,'handoff_digest':sha256(json.dumps(request,sort_keys=True).encode()).hexdigest(),'issue_codes':['HUMAN_REPORTED_ISSUE']}
            existing=None
            for rr in range(3,h.last_operation_row(ops,headers)+1):
                op=h.operation_record(ops,rr,headers)
                if op.get('source_id')==request['source_id'] and op.get('operation_type')=='SOURCE_REVIEW' and op.get('program_status') in h.OPEN_STATUSES:
                    existing=(rr,op);break
            if existing:
                rr,op=existing;old=h.parse_payload(op['payload_json']);previous=old.get('human_reported_issue')
                if previous:
                    issue['related_reports']=[{k:v for k,v in previous.items() if k!='related_reports'},*previous.get('related_reports',[])]
                    issue['reason']=note+'\n'+str(previous.get('reason',''))
                old['human_reported_issue']=issue
                old.setdefault('system2_handoffs',{})[rid]={'digest':payload['handoff_digest'],'issue':issue}
                old['issue_codes']=list(dict.fromkeys(old.get('issue_codes',[])+['HUMAN_REPORTED_ISSUE']))
                opid=op['operation_id']
                h.set_operation_fields(ops,rr,headers,{'payload_json':json.dumps(old),'program_note':str(op.get('program_note') or '')+'\n'+note})
            else:
                payload['system2_handoffs']={rid:{'digest':payload['handoff_digest'],'issue':issue}}
                h.append_operation(ops,headers,{'operation_id':opid,'operation_type':'SOURCE_REVIEW','source_id':request['source_id'],'source_title':source['source_title'],'trigger':'HUMAN_REPORTED_ISSUE','proposed_action':issue['action'],'decision':'PENDING','program_status':'PENDING','program_note':note,'created_at':datetime.now(),'payload_json':json.dumps(payload)})
            u.backup_registry(cfg,datetime.now());u.save_registry(wb,cfg,stamp);wb.close()
    return {'status':'applied','task_id':opid}
