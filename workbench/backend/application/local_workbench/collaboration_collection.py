"""Version 2 collections: validate all entries, retain originals, adopt per item."""
from copy import deepcopy
import uuid
from local_workbench.collaboration import named, fingerprint, now
from backend.shared.collaboration_exchange import pack, unpack
from local_workbench.material_queue import MaterialQueue, acceptance_key

TYPES={'source_task_work','inspection_work','source_task_submission','inspection_submission','adoption_receipt'}

class Collection:
 def __init__(self,c):self.c=c
 def catalogue(self,actor):
  actor=named(actor);items=[]
  for p in self.c.all('source_draft'):
   if p['actor']==actor:items.append({'type':'source','key':p['source_id'],'source_id':p['source_id'],'title':p['source_id']+' · source review','revision':p['revision']})
  for p in self.c.all('workspace'):
   if p['actor']==actor:items.append({'type':'material','key':p['material_id'],'source_id':p['source_id'],'title':p['source_id']+' · personal material'})
  for p in self.c.all('source_task_draft'):
   if p['actor']==actor:items.append({'type':'source_task','key':p['task_id'],'source_id':p.get('source_id'),'title':p['task_id']+' · task proposal','revision':p['revision']})
  for p in self.c.all('material_inspection'):
   if p['history'] and p['history'][-1]['actor']==actor:items.append({'type':'inspection','key':p['id'],'title':p['title']+' · spot-check','revision':p['revision'],'status':p['status']})
  return {'items':items,'sent':[p for p in self.c.all('sent_collection') if p['actor']==actor],
   'inbox':self.c.all('collection_item'),'receipts':[*self.c.all('adoption_receipt'),*self.c.all('collection_adoption')],'received_receipts':self.c.all('received_adoption'),'assignment_changes':self.c.all('inspection_assignment_pending')}
 def work_catalogue(self,actor):
  self.c.coordinator(actor)
  return {'items':[{'type':'source','key':s['source_id'],'title':s.get('source_title') or s['source_id']} for s in self.c.source_records()]
   +[{'type':'source_task','key':t['operation_id'],'title':(t.get('source_title') or t['operation_id'])+' · '+t['operation_type']} for t in self.c.app.adapter.call('read')['tasks']]
   +[{'type':'inspection','key':t['id'],'title':t['title']+' · spot-check'} for t in MaterialQueue(self.c).tasks() if t['status'] not in ('passed','resolved','superseded')]}
 def receipt_catalogue(self,actor):
  self.c.coordinator(actor)
  values=[*self.c.all('adoption_receipt'),*self.c.all('collection_adoption')]
  items=[]
  for receipt in values:
   identity=receipt.get('id') or receipt['request_id']
   material=receipt.get('material') or {}
   submission=self.c.get('submission',receipt.get('submission_id','')) or {}
   item=self.c.get('collection_item',receipt.get('item_id','')) or {}
   base=item.get('base') or {};proposal=item.get('proposal') or {}
   source_id=(material.get('source') or {}).get('source_id') or submission.get('source_id') or base.get('source_id')
   title=material.get('title') or base.get('source_title') or base.get('title') or proposal.get('title')
   parts=[str(source_id)] if source_id else []
   if title and title!=source_id:parts.append(str(title)[:120])
   if not parts:parts=['Receipt '+identity]
   contributor=receipt.get('contributor') or submission.get('actor') or item.get('actor')
   if contributor:parts.append(contributor)
   parts.append(receipt['status'])
   if material.get('revision') is not None:parts.append('master revision '+str(material['revision']))
   if receipt.get('at'):parts.append(receipt['at'])
   items.append({'type':'receipt','key':identity,'title':' · '.join(parts),'evidence_id':identity})
  return {'items':items}
 def receipt_export(self,actor,request):
  self.c.coordinator(actor);rid=str(uuid.UUID(request['request_id']));choices=request.get('items',[])
  if not 1<=len(choices)<=100:raise ValueError('Select 1–100 adoption receipts.')
  with self.c.lock:
   self.c.claim_request('receipt-export',rid,fingerprint(request),actor)
   old=self.c.get('sent_collection',rid)
   if old:return (self.c.packages/(rid+'.zip')).read_bytes(),'adoption-receipts-'+rid[:8]+'.zip'
   entries=[];files={}
   for choice in choices:
    identity=str(uuid.UUID(choice['key']));receipt=self.c.get('adoption_receipt',identity) or self.c.get('collection_adoption',identity)
    if not receipt:raise ValueError('Adoption receipt not found.')
    value={'id':str(uuid.uuid5(uuid.UUID(rid),identity)),'actor':actor,'item_type':'adoption_receipt','receipt':receipt}
    path=value['id']+'.zip';files[path]=pack('submission',value,{});entries.append({'id':value['id'],'kind':'submission','path':path})
   metadata={'id':rid,'actor':actor,'at':now(),'collection_version':2,'direction':'receipt','items':entries,'summary':str(request.get('summary','Explicit per-item adoption receipts'))[:4000]}
   blob=pack('collection',metadata,files);self.c._archive(rid,blob);self.c.put('sent_collection',rid,metadata);return blob,'adoption-receipts-'+rid[:8]+'.zip'
 def export(self,actor,request):
  actor=named(actor);kind=request.get('kind','submission');items=request.get('items',[])
  if kind=='receipt':return self.receipt_export(actor,request)
  if kind not in ('work','submission') or not isinstance(items,list) or not 1<=len(items)<=100:raise ValueError('Select 1–100 saved items.')
  if len({(x['type'],x['key']) for x in items})!=len(items):raise ValueError('Choose each item once.')
  if kind=='work':self.c.coordinator(actor)
  rid=str(uuid.UUID(request['request_id']))
  with self.c.lock:
   self.c.claim_request('collection-export',rid,fingerprint(request),actor)
   prior=self.c.get('sent_collection',rid)
   if prior:return (self.c.packages/(rid+'.zip')).read_bytes(),'review-'+kind+'-'+rid[:8]+'.zip'
   entries=[];files={};included_sources=set()
   def add(blob):
    p=unpack(blob);m=p['metadata'];path=m['id']+'.zip';files[path]=blob
    entries.append({'id':m['id'],'kind':p['kind'],'item_type':m.get('item_type','source_material'),'path':path})
   def source_work(sid,mid=None):
    if sid not in included_sources:
     blob,_=self.c.work_export(actor,{'source_id':sid,'material_id':mid});add(blob);included_sources.add(sid)
   for choice in items:
    typ,key=choice['type'],choice['key']
    if typ in ('source','material'):
     if kind=='work':source_work(key)
     else:
      if typ=='source' and not self.c.get('source_draft',actor+':'+key):raise ValueError('Save the source review before submitting it.')
      if typ=='material':
       ws=self.c.get('workspace',actor+':'+key)
       if not ws:raise ValueError('Saved personal material not found.')
       sid=ws['source_id']
      else:sid=key
      blob,_=self.c.submission_export(actor,{'source_id':sid,**({'material_id':key} if typ=='material' else {}),'summary':request.get('summary','')});add(blob)
    elif typ=='source_task':
     if kind=='work':
      task=next((t for t in self.c.app.adapter.call('read')['tasks'] if t['operation_id']==key),None)
      if not task:raise ValueError('Current source task not found.')
      if task.get('source_id'):source_work(task['source_id'])
      metadata={'id':str(uuid.uuid4()),'actor':actor,'item_type':'source_task_work','task':task,'base_digest':fingerprint(task),'at':now()}
     else:
      proposal=self.c.get('source_task_draft',actor+':'+key)
      if not proposal:raise ValueError('Save a personal task proposal first.')
      metadata={'id':str(uuid.uuid4()),'actor':actor,'item_type':'source_task_submission','base':proposal['base_task'],'base_digest':fingerprint(proposal['base_task']),'proposal':proposal,'at':now()}
     self.c.put('task_baseline',metadata['base_digest'],deepcopy(metadata.get('task') or metadata['base']))
     add(pack(kind,metadata,{}))
    elif typ=='inspection':
     task=self.c.get('material_inspection',key)
     if not task:raise ValueError('Inspection not found.')
     if kind=='work':
      material=self.c.app.system2.call('material_read',material_id=task['material_id'],revision=task['archive_revision'])
      source_work(material['source']['source_id'],material['id'])
      metadata={'id':str(uuid.uuid4()),'actor':actor,'item_type':'inspection_work','task':task,'archive':material,'archive_history':[v for v in self.c.app.system2.call('material_export',request={'material_id':material['id']})['history'] if v['revision']<=material['revision']],'base_digest':fingerprint(task),'at':now()}
      self.c.put('inspection_baseline',fingerprint(task),task)
     else:
      baseline=self.c.get('inspection_assigned',key)
      base=baseline['task'] if baseline else self.c.get('inspection_initial',key)
      if not base:raise ValueError('Export an assigned work package before returning this check.')
      if not task['history'] or task['history'][-1]['actor']!=actor:raise ValueError('Save your inspection result first.')
      metadata={'id':str(uuid.uuid4()),'actor':actor,'item_type':'inspection_submission','base':base,'base_digest':fingerprint(base),'proposal':task,'at':now()}
     add(pack(kind,metadata,{}))
    else:raise ValueError('Unknown collection selection.')
   metadata={'id':rid,'actor':actor,'at':now(),'collection_version':2,'direction':kind,'items':entries,'summary':str(request.get('summary',''))[:4000]}
   blob=pack('collection',metadata,files);self.c._archive(rid,blob);self.c.put('sent_collection',rid,metadata)
   return blob,'review-'+kind+'-'+rid[:8]+'.zip'
 def validate_item(self,p):
  m=p['metadata'];typ=m.get('item_type');named(m.get('actor'));uuid.UUID(m['id'])
  if typ not in TYPES:
   if p['kind']=='work':
    if set(p['files'])!=({m['original']} if m.get('original') else set()):raise ValueError('Unrelated work attachments.')
    self.c._import_work(m,p['files'],dry_run=True)
   elif p['kind']=='submission':
    if p['files']:raise ValueError('Return packages cannot replace originals.')
    self.c._import_submission(m,dry_run=True)
   else:raise ValueError('Nested collections are not allowed.')
   return
  if p['files']:raise ValueError('Task results cannot carry files.')
  if typ.endswith('_work')!=(p['kind']=='work'):raise ValueError('Task package direction mismatch.')
  base=m.get('task') if typ.endswith('_work') else m.get('base')
  if typ=='adoption_receipt':
   receipt=m.get('receipt')
   if not isinstance(receipt,dict) or receipt.get('actor')!='Weijie Tang' or not (receipt.get('submission_id') or receipt.get('item_id')):raise ValueError('Invalid adoption receipt.')
   return
  if not isinstance(base,dict) or fingerprint(base)!=m.get('base_digest'):raise ValueError('Task baseline mismatch.')
  if typ.startswith('source_task'):
   if not base.get('operation_id') or not base.get('revision'):raise ValueError('Task identity and revision required.')
  else:
   if not base.get('id') or not base.get('material_id') or not base.get('archive_key'):raise ValueError('Inspection version binding required.')
  if typ=='inspection_work':
   archive=m['archive']
   if archive['id']!=base['material_id'] or archive['revision']!=base['archive_revision'] or acceptance_key(archive)!=base['archive_key']:raise ValueError('Inspection archive mismatch.')
   self.c.app.system2.call('material_validate',request={'material':archive,'history':m.get('archive_history',[])})
  if typ.endswith('_submission'):
   proposal=m.get('proposal')
   if not isinstance(proposal,dict):raise ValueError('Saved proposal missing.')
   history=proposal.get('history',[])
   if not history or history[-1].get('actor')!=m['actor']:raise ValueError('Submission does not end in the contributor’s saved history.')
   if typ=='source_task_submission':
    if proposal.get('actor')!=m['actor'] or proposal.get('base_task')!=base or proposal.get('task_id')!=base['operation_id']:raise ValueError('Task proposal identity mismatch.')
    if history[-1].get('request')!=proposal.get('request'):raise ValueError('Task result differs from saved history.')
   else:
    for key in ('id','material_id','archive_key','archive_revision','source_hash','scope','assignee'):
     if proposal.get(key)!=base.get(key):raise ValueError('Inspection submission changed its assigned scope or original.')
    if not set(proposal.get('checked_scope',[]))<=set(base['scope']):raise ValueError('Inspection checks outside assigned range.')
 def import_collection(self,actor,blob,package):
  actor=named(actor);m=package['metadata'];named(m.get('actor'))
  if m.get('collection_version')!=2 or m.get('direction') not in ('work','submission','receipt'):raise ValueError('Unsupported collection format.')
  items=m.get('items',[])
  if not isinstance(items,list) or not 1<=len(items)<=200 or len({i['id'] for i in items})!=len(items):raise ValueError('Invalid or duplicate collection items.')
  if set(package['files'])!={i['path'] for i in items}:raise ValueError('Collection attachment inventory mismatch.')
  if m['direction']=='work' and self.c.mode!='reviewer':raise ValueError('Import work in an independent reviewer workspace.')
  if m['direction']=='submission':self.c.coordinator(actor)
  decoded=[];total=0
  for item in items:
   raw=package['files'][item['path']];p=unpack(raw);total+=sum(len(x) for x in p['files'].values())+len(str(p['metadata']).encode())
   if total>512*1024*1024:raise ValueError('Collection expanded size exceeds limit.')
   if p['metadata']['id']!=item['id'] or p['kind']!=item['kind'] or p['kind']!=('submission' if m['direction']=='receipt' else m['direction']):raise ValueError('Collection entry identity or direction mismatch.')
   self.validate_item(p);decoded.append((p,raw))
  with self.c.lock:
   old=self.c.get('collection_receipt',m['id'])
   if old:
    if old['digest']!=package['digest']:raise ValueError('Collection identity reused for different contents.')
    return {**old,'status':'already_imported'}
   # Check every immutable item identity before any owning-store import.
   for p,raw in decoded:
    path=self.c.packages/(p['metadata']['id']+'.zip')
    if path.exists() and path.read_bytes()!=raw:raise ValueError('Item identity reused for different contents.')
   self.c._archive(m['id'],blob);receipts=[]
   for p,raw in decoded:
    value=p['metadata'];typ=value.get('item_type');identity=value['id']
    if typ not in TYPES:receipt=self.c.import_package(actor,raw)
    else:
     self.c._archive(identity,raw)
     if typ=='source_task_work':
      self.c.put('source_task_assignment',identity,value);self.c.put('task_baseline',value['base_digest'],value['task'])
     elif typ=='inspection_work':
      assignment_status=self.receive_inspection_assignment(value)
     elif typ=='adoption_receipt':self.c.put('received_adoption',identity,value)
     else:
      known=self.c.get('task_baseline' if typ=='source_task_submission' else 'inspection_baseline',value['base_digest'])
      if not self.c.get('collection_item',identity):self.c.put('collection_item',identity,{**value,'status':'pending' if known else 'unknown_baseline'})
     receipt={'id':identity,'kind':typ,'status':assignment_status if typ=='inspection_work' else 'imported_for_review'}
    receipts.append(receipt)
   result={'id':m['id'],'digest':package['digest'],'status':'imported','items':receipts,'message':'Collection validated and received. Each item requires its own comparison and adoption.'}
   self.c.put('collection_receipt',m['id'],result);return result
 def receive_inspection_assignment(self,value):
  task_id=value['task']['id'];old=self.c.get('inspection_assigned',task_id);local=self.c.get('material_inspection',task_id)
  if (old and old['base_digest']!=value['base_digest']) or (not old and local and local!=value['task']):
   self.c.put('inspection_assignment_pending',value['id'],{**value,'status':'assignment_changed','message':'A different starting version was received for this check. Existing work and its baseline are retained. Return the saved result against its original assignment; ask the coordinator to create a new check for the changed version.'})
   return 'assignment_changed'
  if not old:self.c.put('inspection_assigned',task_id,value)
  self.c.put('inspection_baseline',value['base_digest'],value['task'])
  if not local:self.c.put('material_inspection',task_id,value['task'])
  return 'imported_for_review'
 def preview(self,actor,request):
  self.c.coordinator(actor);item=self.c.get('collection_item',request['item_id'])
  if not item:raise ValueError('Submitted task not found.')
  if item['status']=='unknown_baseline':raise ValueError('Common baseline unavailable. Retain the submission for investigation.')
  if item['item_type']=='source_task_submission':current=next((t for t in self.c.app.adapter.call('read')['tasks'] if t['operation_id']==item['base']['operation_id']),None)
  else:current=self.c.get('material_inspection',item['base']['id'])
  return {'item':item,'base':item['base'],'current':current,'proposed':item['proposal'],'current_digest':fingerprint(current),'conflict':current!=item['base']}
 def adopt(self,actor,request):
  self.c.coordinator(actor);rid=str(uuid.UUID(request['request_id']))
  if request.get('explicit_confirmation') is not True or request.get('choice') not in ('current','incoming'):raise ValueError('Explicitly select current or submitted task result.')
  with self.c.lock:
   self.c.claim_request('collection-adopt',rid,fingerprint(request),actor)
   old=self.c.get('collection_adoption',rid)
   if old:return old
   item=self.c.get('collection_item',request['item_id'])
   if not item:raise ValueError('Task submission not found.')
   if item.get('adoption'):return item['adoption']
   staged=self.c.get('collection_pending',rid)
   if not staged:
    view=self.preview(actor,request)
    if view['current_digest']!=request.get('expected_current_digest'):raise ValueError('Task changed after comparison. Reopen it.')
    if request['choice']=='incoming' and view['conflict']:raise ValueError('Assigned task changed. Keep the current result or start a new task using the submitted evidence.')
    staged=view;self.c.put('collection_pending',rid,staged)
   item=staged['item'];result={'status':'kept_current'}
   if request['choice']=='incoming':
    proposal=item['proposal'];base=item['base'];owner_id=str(uuid.uuid5(uuid.UUID(rid),'owner'))
    if item['item_type']=='source_task_submission':
     from local_workbench.source_workflow import SourceWorkflow
     payload=deepcopy(proposal['request'])
     if payload['action']=='manual':raise ValueError('Returned opinions cannot supply originals. Upload an authorised file in the main source workspace.')
     own=self.c.get('source_task_draft',actor+':'+base['operation_id'])
     payload.update(request_id=owner_id,expected_draft_revision=own['revision'] if own else 0,explicit_confirmation=True)
     payload=staged.get('owner_request') or payload
     staged['owner_request']=payload;self.c.put('collection_pending',rid,staged)
     result=SourceWorkflow(self.c).task(actor,payload,True)
    else:
     action={'passed':'pass','finding_open':'finding','resolved':'resolve'}.get(proposal['status'],'save')
     payload={'task_id':base['id'],'material_id':base['material_id'],'expected_revision':base['revision'],'request_id':owner_id,'action':action,'checked_scope':proposal['checked_scope'],'note':proposal['note'],'explicit_confirmation':action in ('pass','resolve')}
     if action=='resolve':payload['expected_master_revision']=proposal.get('progress_target_revision')
     result=MaterialQueue(self.c).save(actor,payload)
   receipt={'id':rid,'item_id':item['id'],'status':'adopted' if result.get('status') in ('saved','applied','kept_current') else 'pending','choice':request['choice'],'actor':actor,'contributor':item['actor'],'at':now(),'result':result}
   if receipt['status']=='adopted':self.c.put_many([('collection_adoption',rid,receipt),('collection_item',item['id'],dict(item,status='adopted',adoption=receipt))])
   return receipt
