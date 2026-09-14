"""Install explicitly synchronized source facts in the owning registry.

A snapshot does not dispatch imported tasks. Their complete evidence is retained
in the import operation. Existing local open issues/tasks retain their gates.
"""
from pathlib import Path
from hashlib import sha256
import json,uuid
import human_operations as h
import source_updater as u
from .workbook_guard import exclusive_process_lock
from .governance_store import publish_bytes

REVIEWERS={'Weijie Tang','Ana Jokic','Daniel Restad'}

def apply(config_path,request):
 actor=request.get('actor')
 if actor not in REVIEWERS:raise ValueError('Choose a named reviewer before synchronizing.')
 rid=str(uuid.UUID(request['request_id']));opid='SYNC-'+rid;source=request['source'];sid=source.get('source_id')
 if not isinstance(sid,str) or not sid:raise ValueError('Source identity is missing.')
 cfg=u.read_config(config_path)
 digest=sha256(json.dumps(request,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()
 with exclusive_process_lock(cfg['log_root']/'.system1-run.lock'),u.registry_lock(cfg,12):
  wb=u.open_registry(cfg)
  try:
   stamp=u.registry_revision(cfg);wb._governance_actor=actor
   ops=wb[h.human_sheet_name(cfg)];oh=h.operation_headers(ops);index=h.operation_index(ops,oh)
   if opid in index:
    payload=h.parse_payload(h.operation_record(ops,index[opid],oh).get('payload_json'))
    if payload.get('request_digest')!=digest:raise ValueError('Snapshot request identity differs.')
    return payload['receipt']
   ws=wb[cfg['sheet_name']];headers=u.workbook_headers(ws,int(cfg['header_row']));row=h.find_source_row(ws,headers,sid)
   previous=u.record_from_row(ws,row,headers) if row else None
   if (h.source_record_fingerprint(previous) if previous else None)!=request.get('expected_source_revision'):
    raise ValueError('Source changed after the synchronization preview.')
   if source.get('snapshot_status')=='STORED':
    root=Path(request['original_root']).resolve();original=Path(request['original_path']).resolve()
    if not original.is_relative_to(root) or not original.is_file():raise ValueError('Snapshot original is outside its validated package.')
    raw=original.read_bytes()
    if sha256(raw).hexdigest()!=source.get('content_hash'):raise ValueError('Snapshot original fingerprint differs.')
    folder=source.get('folder_code');filename=source.get('stored_filename')
    if any(not isinstance(v,str) or not v or '/' in v or '\\' in v or v in ('.','..') for v in (folder,filename)):raise ValueError('Unsafe original filename.')
    destination=(cfg['source_root']/folder/filename).resolve()
    if not destination.is_relative_to(cfg['source_root'].resolve()):raise ValueError('Original destination leaves managed storage.')
    if destination.exists() and destination.read_bytes()!=raw:
     raise ValueError('An existing original has the same filename but different content. Both originals are retained; reconcile source naming first.')
    destination.parent.mkdir(parents=True,exist_ok=True);publish_bytes(destination,raw)
   if row is None:row=max(int(cfg['data_start_row']),ws.max_row+1)
   updates={k:v for k,v in source.items() if k in headers and k not in {'selection_status','current_snapshot_date','needs_human_action'}}
   if any(not (v is None or isinstance(v,(str,int,float,bool))) for v in updates.values()):raise ValueError('Source values must match the registry field types.')
   if any(isinstance(v,str) and v.startswith('=') for v in updates.values()):raise ValueError('Snapshot fields cannot insert workbook formulas.')
   for field,value in updates.items():ws.cell(row,headers[field]).value=value
   receipt={'status':'synchronized','source_id':sid,'operation_id':opid,'actor':actor,'request_id':rid}
   current_time=u.local_now(cfg)
   h.append_operation(ops,oh,{'operation_id':opid,'operation_type':'SOURCE_REVIEW','source_id':sid,
    'source_title':source.get('source_title'), 'trigger':'PEER_SNAPSHOT_SYNCHRONIZATION','proposed_action':'ACKNOWLEDGE_REVIEW',
    'decision':'ACCEPT','operator':actor,'operator_note':'Imported a version-compared full workspace snapshot.',
    'created_at':current_time,'checked_at':current_time,'program_status':'APPLIED','program_operated_at':current_time,
    'program_note':'Saved source facts. Imported task evidence is retained; no imported task was executed.',
    'payload_json':json.dumps({'request_digest':digest,'receipt':receipt,'before':previous,'incoming':source,
      'source_evidence':request.get('evidence',{}),'snapshot_id':request.get('package_id')},sort_keys=True,ensure_ascii=False,default=str)})
   h.prepare_human_workbook(wb,ops,oh);u.backup_registry(cfg,current_time);u.save_registry(wb,cfg,stamp)
   return receipt
  finally:wb.close()
