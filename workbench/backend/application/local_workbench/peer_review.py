"""Explicit Archive by any named reviewer, with no separate administrator merge."""
from copy import deepcopy
import uuid
from local_workbench.collaboration import body, fingerprint, named
from local_workbench.snapshot_workspace import material_value

def confirm(collaboration,actor,request):
 c=collaboration;actor=named(actor);rid=str(uuid.UUID(request['request_id']))
 with c.lock:
  c.claim_request('peer-confirmation',rid,fingerprint(request),actor)
  prior=c.get('peer_confirmation_receipt',rid)
  if prior:return prior
  pending=c.get('peer_confirmation_pending',rid)
  adapter=c.personal_adapter(actor,request['material_id'])
  if pending and pending.get('processing_progress'):
   current=adapter.call('material_read',material_id=request['material_id'])
   if current['revision']==request['expected_revision']:
    from local_workbench.material_progress import MaterialProgress
    checked=MaterialProgress(c).require_complete(actor,request['material_id'])
    if checked['version']!=pending['processing_progress']['version']:
     raise ValueError('Processing confirmations changed before Archive finished. Start a new Archive request.')
  if not pending:
   from local_workbench.material_progress import MaterialProgress
   processing=MaterialProgress(c).require_complete(actor,request['material_id'])
   workspace=c.workspace(actor,request['material_id']);current=c.app.system2.call('material_read',material_id=request['material_id'])
   personal=adapter.call('material_read',material_id=request['material_id'])
   if any(i['status'] in ('running','ready','partial') for i in current.get('candidates',[])):
    raise ValueError('Resolve the shared extraction candidate before archiving.')
   if body(current)!=body(workspace['base_material']) and body(current)!=body(personal):
    raise ValueError('Another saved shared version differs. Synchronize and resolve its changes before archiving.')
   pending={'confirm_request':dict(request,actor=actor),'shared_revision':current['revision'],'processing_progress':processing}
   c.put('peer_confirmation_pending',rid,pending)
  result=adapter.call('material_confirm',request=pending['confirm_request'])
  if result.get('status')=='conflict':return result
  if not pending.get('shared_request'):
   exported=adapter.call('material_export',request={'material_id':request['material_id']})
   origin={k:v for k,v in exported.items() if k!='original'}
   pending['shared_request']={'actor':actor,'request_id':str(uuid.uuid5(uuid.UUID(rid),'shared')),
    'material_id':request['material_id'],'expected_revision':pending['shared_revision'],
    'value':material_value(exported['material']),'origin':origin,'sync_head':rid,'contributors':actor,
    'original_path':exported['original']['path']}
   c.put('peer_confirmation_pending',rid,pending)
  shared=c.app.system2.call('material_sync',request=pending['shared_request'])
  if shared.get('status')=='conflict':raise ValueError('Shared work changed during confirmation. The personal confirmation is retained; synchronize before retrying Archive.')
  # Record the shared copy as a descendant of the exact personal declaration.
  # Its local revision/check stamps may differ without becoming a competing edit.
  from local_workbench.snapshot_graph import node
  key='material:'+request['material_id'];marker=c.get('sync_observed',key+':'+actor)
  base=node(key,material_value(c.workspace(actor,request['material_id'])['base_material']))
  parent=marker['head'] if marker else base['id']
  personal=node(key,pending['shared_request']['value'],[parent],actor)
  shared_node=node(key,material_value(shared['material']),[personal['id']],actor)
  c.put_many([('sync_node',n['id'],n) for n in (base,personal,shared_node)]+[
   ('sync_observed',key+':'+actor,{'head':personal['id']}),('sync_observed',key+':master',{'head':shared_node['id']})])
  result['material']=c.annotate(actor,result['material'])
  if pending.get('processing_progress'):
   identity=request['material_id']+':'+str(shared['material']['revision'])
   c.put('material_archive_progress',identity,dict(id=identity,material_id=request['material_id'],
    actor=actor,progress=pending['processing_progress']))
  c.put('peer_confirmation_receipt',rid,result)
  return result
