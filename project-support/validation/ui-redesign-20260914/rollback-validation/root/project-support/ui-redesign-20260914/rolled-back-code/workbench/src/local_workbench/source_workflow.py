"""Independent source workspace, personal task proposals and explicit application."""
from copy import deepcopy
from pathlib import Path
import json
import uuid
from .collaboration import named, fingerprint, now, validate_source_review, COORDINATOR

TASK_ACTIONS={'SOURCE_REVIEW':['retry'], 'SELECTION_REVIEW':['retry'],
 'NEW_SOURCE_CANDIDATE':['candidate_accept','candidate_reject','task_defer'],
 'MANUAL_FILE_REPLACEMENT':['replacement_accept','replacement_reject','task_defer'],
 'RANDOM_QA_CHECK':['qa']}

class SourceWorkflow:
 def __init__(self,c):self.c=c
 def snapshot(self,actor):
  actor=named(actor)
  if self.c.mode=='reviewer':
   tasks=[t for p in self.c.all('work') for t in p.get('source_tasks',[])]+[p['task'] for p in self.c.all('source_task_assignment')]
   data={'sources':self.c.source_records(),'tasks':list({t['operation_id']:t for t in tasks}.values()),'history':[t for p in self.c.all('work') for t in p.get('source_history',[])]}
  else:data=self.c.app.adapter.call('read')
  # Receipt projection includes applied reviews even when their source tasks remain open.
  # It does not create a second action ledger or infer completion from selection.
  history=list(data.get('history',[]));sources={s['source_id']:s for s in data.get('sources',[])}
  for receipt in self.c.all('adoption_receipt'):
   if not receipt.get('source_receipt'):continue
   merge=self.c.get('merge',receipt['merge_id'],{})
   sid=merge.get('source_id') or merge.get('source_request',{}).get('source_id')
   history.append({'action_id':receipt['request_id'],'source_id':sid,'source_title':sources.get(sid,{}).get('source_title',sid),
    'action':'APPLY_SOURCE_REVIEW','actor':receipt.get('actor'),'at':receipt.get('at'),
    'result':receipt['source_receipt'].get('effective_selection') or receipt.get('source_status'),
    'receipt':receipt,'source_review':merge.get('source_review')})
  data={**data,'history':history}
  return {**data,'task_actions':TASK_ACTIONS,'can_apply':self.c.mode=='coordinator' and actor==self.c.state(actor)['coordinator'],
   'personal_tasks':[p for p in self.c.all('source_task_draft') if p['actor']==actor]}
 def detail(self,actor,sid):return self.c.source_draft(actor,sid)
 def preview(self,actor,request):
  named(actor);validate_source_review(request['source_review'])
  if self.c.mode=='reviewer':return {'effective_selection':'PROPOSAL','remaining_reason':'Coordinator source rules determine the effective selection after adoption.'}
  return self.c.app.adapter.call('source_review_preview',request=request)
 def save(self,actor,request):
  actor=named(actor);rid=str(uuid.UUID(request['request_id']))
  with self.c.lock:
   self.c.claim_request('source-workflow-save',rid,fingerprint(request),actor)
   old=self.c.get('source_workflow_receipt',rid)
   if old:return old
   result=self.c.save_source(actor,request)
   if result['status']!='conflict':self.c.put('source_workflow_receipt',rid,result)
   return result
 def apply_review(self,actor,request):
  self.c.coordinator(actor)
  if request.get('explicit_confirmation') is not True:raise ValueError('Confirm the displayed source changes explicitly.')
  rid=str(uuid.UUID(request['request_id']))
  with self.c.lock:
   self.c.claim_request('source-review-apply',rid,fingerprint(request),actor)
   old=self.c.get('source_apply_receipt',rid)
   if old:return old
   staged=self.c.get('source_apply_pending',rid)
   if not staged:
    current=self.c.source(request['source_id'])
    if current['source_revision']!=request.get('expected_source_revision'):raise ValueError('Source changed. Reopen and compare before applying.')
    saved=self.c.save_source(actor,request)
    if saved['status']=='conflict':return saved
    preview=self.c.prepare_own(actor,{'source_id':request['source_id'],'summary':'Explicit source review'})
    staged={'merge_id':preview['merge_id'] if 'merge_id' in preview else preview['id']}
    self.c.put('source_apply_pending',rid,staged)
   result=self.c.adopt(actor,{'merge_id':staged['merge_id'],'request_id':str(uuid.uuid5(uuid.UUID(rid),'adopt'))})
   self.c.put('source_apply_receipt',rid,result);return result
 def reopen(self,actor,request):
  self.c.coordinator(actor)
  return self.c.app.adapter.call('workflow_reopen',request={**request,'actor':actor})
 def task(self,actor,request,apply=False):
  actor=named(actor);rid=str(uuid.UUID(request['request_id']))
  if set(request)-{'request_id','task_id','revision','source_revision','action','note','verdict','candidate_fields','explicit_confirmation','upload_id','identity_verified','permission_verified','expected_draft_revision'}:raise ValueError('Unsupported source task fields.')
  if apply:
   self.c.coordinator(actor)
   if request.get('explicit_confirmation') is not True:raise ValueError('Explicitly confirm this source task action.')
  with self.c.lock:
   self.c.claim_request('source-task-apply' if apply else 'source-task-save',rid,fingerprint(request),actor)
   old=self.c.get('source_task_receipt',rid)
   if old:return old
   proposal=self.c.get('source_task_pending',rid) if apply else None
   if not proposal:
    data=self.snapshot(actor);task=next((t for t in data['tasks'] if t['operation_id']==request['task_id']),None)
    if not task or task['revision']!=request.get('revision') or task.get('source_revision','')!=request.get('source_revision',''):raise ValueError('Source task changed. Reload it before proceeding.')
    allowed=TASK_ACTIONS.get(task['operation_type'],[])
    if task.get('source_id') and task['operation_type'] in ('SOURCE_REVIEW','SELECTION_REVIEW'):allowed=[*allowed,'manual']
    if request['action'] not in allowed:raise ValueError('Choose an available action for this task.')
    key=actor+':'+task['operation_id'];prior=self.c.get('source_task_draft',key,{'revision':0,'history':[t for p in self.c.all('work') for t in p.get('source_history',[])]})
    if request.get('expected_draft_revision',0)!=prior['revision']:raise ValueError('Another saved task proposal exists. Reload it before saving.')
    proposal={'id':str(uuid.uuid4()),'actor':actor,'source_id':task.get('source_id'),'task_id':task['operation_id'],
     'base_task':task,'request':deepcopy(request),'revision':prior['revision']+1,'history':[*prior['history'],{'actor':actor,'at':now(),'request':deepcopy(request)}]}
    self.c.put('source_task_draft',key,proposal)
    if apply:self.c.put('source_task_pending',rid,proposal)
   if not apply:
    if request['action'] in ('manual','replacement_accept','replacement_reject','candidate_accept','candidate_reject','retry'):
     proposal['boundary']='Personal opinion only; coordinator performs registration, retrieval and file operations.'
    result={'status':'saved_personal','proposal':proposal}
   else:
    if request.get('explicit_confirmation') is not True:raise ValueError('Explicitly confirm this source task action.')
    payload={k:v for k,v in request.items() if k not in {'upload_id','expected_draft_revision'}};payload['actor']=actor
    if request['action']=='manual':
     uid=str(uuid.UUID(request['upload_id']));root=self.c.app.runtime/'uploads';metadata=json.loads((root/(uid+'.json')).read_text())
     if metadata.get('actor_name')!=actor:raise ValueError('This staged original belongs to another reviewer.')
     payload.update(upload_path=metadata['path'],upload_hash=metadata['hash'],upload_root=str(root))
    result=self.c.app.adapter.call('workflow_apply',request=payload)
    self.c.put('source_task_adoption',rid,{'actor':actor,'contributor':actor,'at':now(),'proposal':proposal,'receipt':result})
    self.c.app.snapshot_time=0
   self.c.put('source_task_receipt',rid,result);return result

 def intake_capabilities(self,actor):
  actor=named(actor)
  return {'can_register':self.c.mode=='coordinator' and actor==COORDINATOR,
   'discovery':{'available':False,'reason':'No discovery provider is connected. Existing Discovery & Intake checks coverage and accepts supplied candidates; it does not search the web.'}}
 def intake(self,actor,request):
  self.c.coordinator(actor)
  allowed={'request_id','source_title','official_url','retrieval_url','issuer','version','folder_code','file_format','note','upload_id'}
  if not isinstance(request,dict) or set(request)-allowed:raise ValueError('Unsupported intake fields.')
  rid=str(uuid.UUID(request['request_id']))
  with self.c.lock:
   self.c.claim_request('source-intake',rid,fingerprint(request),actor)
   old=self.c.get('source_intake_receipt',rid)
   if old:return old
   payload={k:v for k,v in request.items() if k!='upload_id'};payload['actor']=actor
   if request.get('upload_id'):
    uid=str(uuid.UUID(request['upload_id']));root=self.c.app.runtime/'uploads';metadata=json.loads((root/(uid+'.json')).read_text())
    if metadata.get('actor_name')!=actor:raise ValueError('This staged original belongs to another reviewer.')
    payload.update(upload_path=metadata['path'],upload_hash=metadata['hash'],upload_root=str(root))
   result=self.c.app.adapter.call('workflow_intake',request=payload)
   self.c.put('source_intake_receipt',rid,result);self.c.app.snapshot_time=0
   return result
