"""Full logical ZIP snapshots with preview, explicit apply and resumable receipts.

The workspace adapter owns domain validation and writes. This journal never opens
an imported database, extracts untrusted paths, or enables imported schedules.
"""
from copy import deepcopy
from pathlib import Path
import uuid
from .collaboration import encoded, fingerprint, named, now
from .collaboration_exchange import pack, unpack
from .snapshot_graph import node, tips, preview, validate_graph

PROJECT='aquaculture-requirements'
SCHEMA='full-workspace-snapshot/2'

class FullSnapshot:
 def __init__(self, collaboration, workspace=None):
  self.c=collaboration
  if workspace is None:
   from .snapshot_workspace import SnapshotWorkspace
   workspace=SnapshotWorkspace(collaboration)
  self.w=workspace
 def graph(self):return {n['id']:n for n in self.c.all('sync_node')}
 def capture(self,actor):
  actor=named(actor);nodes=self.graph();heads={};files={};evidence={};guards={}
  # The adapter returns base/current pairs for every saved branch. Empty scopes
  # are valid; unavailable referenced originals fail export instead of omission.
  for item in self.w.capture(actor):
   key=item['key'];base=node(key,item.get('base',item['value']))
   branch=item.get('branch','shared');marker=self.c.get('sync_observed',key+':'+branch)
   matching=tips(nodes,[i for i,n in nodes.items() if n['key']==key and n['value']==base['value']])
   if marker and marker['head'] in nodes:parent=marker['head']
   elif len(matching)==1:parent=matching[0]
   else:
    if matching:base=node(key,base['value'],matching)
    nodes.setdefault(base['id'],base);parent=base['id']
   guards[key+':'+branch]=item.get('guard',fingerprint(item['value']))
   current=nodes[parent]
   evidence_digest=fingerprint(item.get('evidence'))
   evidence_changed=marker and marker.get('evidence_digest') and marker['evidence_digest']!=evidence_digest
   if current['value']!=item['value'] or evidence_changed:
    current=node(key,item['value'],[parent],item.get('actor',actor),item.get('at'));nodes[current['id']]=current
   self.c.put('sync_observed',key+':'+branch,{'head':current['id'],'evidence_digest':evidence_digest})
   heads.setdefault(key,[]).append(current['id'])
   for path,raw in item.get('files',{}).items():
    if path in files and files[path]!=raw:raise ValueError('Different originals have the same snapshot identity.')
    files[path]=raw
   if item.get('evidence') is not None:evidence[current['id']]=item['evidence']
  # Retain received versions/evidence. Export is self-contained even after a
  # sync or when another reviewer has not opened the received material yet.
  for item in self.c.all('sync_head'):
   heads.setdefault(item['key'],[]).extend(item['heads'])
  for item in self.c.all('sync_evidence'):evidence.setdefault(item['id'],item['value'])
  for item in self.c.all('sync_file'):
   raw=(self.c.root/'snapshot-files'/item['id']).read_bytes()
   if fingerprint_bytes(raw)!=item['id']:raise ValueError('A retained snapshot original is corrupt.')
   files.setdefault(item['path'],raw)
  heads={k:tips(nodes,v) for k,v in heads.items()}
  validate_graph(nodes,heads)
  self.c.put_many([('sync_node',i,n) for i,n in nodes.items()]+[('sync_evidence',i,{'id':i,'value':v}) for i,v in evidence.items()])
  original_root=self.c.root/'snapshot-files';original_root.mkdir(exist_ok=True)
  for path,raw in files.items():
   digest=fingerprint_bytes(raw);target=original_root/digest
   if not target.exists():target.write_bytes(raw)
   self.c.put('sync_file',digest,{'id':digest,'path':path})
  return {'nodes':nodes,'heads':heads,'files':files,'evidence':evidence,'guards':guards}
 def history(self):
  return sorted(self.c.all('sync_event'),key=lambda e:(e['at'],e['id']),reverse=True)
 def export(self,actor,request):
  actor=named(actor);rid=str(uuid.UUID(request['request_id']))
  with self.c.lock:
   self.c.claim_request('snapshot-export',rid,'full',actor)
   saved=self.c.get('sync_export',rid)
   if saved:return saved
   current=self.capture(actor)
   metadata={'id':rid,'schema':SCHEMA,'project':PROJECT,'actor':actor,'at':now(),
    'nodes':current['nodes'],'heads':current['heads'],'evidence':current['evidence'],'history':self.history()}
   data=pack('collection',metadata,current['files']);self.c._archive(rid,data)
   result={'id':rid,'filename':'workbench-full-'+rid[:8]+'.zip','bytes':len(data),
    'records':len(current['heads']),'originals':len(current['files']),'versions':len(current['nodes']),
    'history_count':len(metadata['history']),'actor':actor,'at':metadata['at']}
   self.c.put('sync_export',rid,result);return result
 def download(self,actor,identity):
  named(actor);identity=str(uuid.UUID(identity));info=self.c.get('sync_export',identity)
  if not info:raise ValueError('Prepare this full snapshot before downloading it.')
  return (self.c.root/'packages'/(identity+'.zip')).read_bytes(),info['filename']
 def load(self,raw):
  package=unpack(raw);m=package['metadata']
  if package['kind']!='collection' or m.get('schema') not in (SCHEMA,'full-workspace-snapshot/1') or m.get('project')!=PROJECT:
   raise ValueError('Choose a full workbench snapshot. Earlier work/result packages remain in legacy history.')
  if set(m)!={'id','schema','project','actor','at','nodes','heads','evidence','history'}:raise ValueError('Unsupported snapshot fields.')
  named(m['actor']);validate_graph(m['nodes'],m['heads'])
  if not isinstance(m['evidence'],dict) or set(m['evidence'])-set(m['nodes']):raise ValueError('Invalid snapshot evidence inventory.')
  if not isinstance(m['history'],list) or len(m['history'])>100000:raise ValueError('Invalid synchronization history.')
  seen=set()
  for e in m['history']:
   if (not isinstance(e,dict) or set(e)!={'id','actor','at','package_id','sender','items','status'}
       or not isinstance(e['items'],list) or e['status']!='applied'):raise ValueError('Invalid synchronization event.')
   str(uuid.UUID(e['id']));str(uuid.UUID(e['package_id']));named(e['actor']);named(e['sender'])
   if e['id'] in seen:raise ValueError('Duplicate synchronization event.')
   seen.add(e['id'])
   old=self.c.get('sync_event',e['id'])
   if old and old!=e:raise ValueError('A shared synchronization history entry was changed.')
  for path,raw_file in package['files'].items():
   if path!='originals/'+fingerprint_bytes(raw_file):raise ValueError('Original fingerprint or path differs.')
  self.w.validate(m,package['files'])
  return package
 def receive(self,actor,raw):
  actor=named(actor)
  with self.c.lock:
   package=self.load(raw);m=package['metadata'];identity=m['id']
   prior=self.c.get('sync_import',identity)
   if prior and prior['digest']!=package['digest']:raise ValueError('Snapshot identity was reused with different contents.')
   self.c._archive(identity,raw)
   if not prior:self.c.put('sync_import',identity,{'id':identity,'digest':package['digest'],'sender':m['actor']})
   return self.prepare(actor,{'id':identity})
 def prepare(self,actor,request):
  actor=named(actor);identity=str(uuid.UUID(request['id']));key=actor+':'+identity
  with self.c.lock:
   saved=self.c.get('sync_plan',key)
   if saved and saved.get('status') in ('applying','applied'):
    return self.public(saved)
   package=self.load((self.c.root/'packages'/(identity+'.zip')).read_bytes());m=package['metadata']
   local=self.capture(actor);decisions=request.get('decisions',saved.get('decisions',{}) if saved else {})
   result=preview(local['nodes'],local['heads'],m['nodes'],m['heads'],decisions)
   # Domain validation is also required after independently safe field merges.
   errors=[]
   for item in result['items']:
    if item['status']=='conflict':continue
    try:self.w.validate_value(item['key'],result['nodes'][item['head']]['value'])
    except ValueError as exc:errors.append({'key':item['key'],'message':str(exc)})
   for item in result['items']:
    value=result['nodes'][item['head']]['value'];kind,suffix=item['key'].split(':',1)
    item['title']=(value.get('binding',{}).get('source',{}).get('source_id','')+' · '+value.get('binding',{}).get('title','Material')) if kind=='material' else (suffix+' · '+value.get('source_title','Source')) if kind=='source' else suffix+' · '+('Source review' if kind=='review' else 'Review history')
    if kind=='requirements':item['title']='Requirement work · '+value['actor']
    for d in item['conflicts']:d['title']=item['title']
   plan={'id':identity,'actor':actor,'sender':m['actor'],'status':'preview','decisions':decisions,
    'local_fingerprint':fingerprint([local['heads'],local['guards']]),'local_guards':local['guards'],'nodes':result['nodes'],'heads':result['heads'],
    'items':result['items'],'conflicts':result['conflicts'],'validation_errors':errors,'applied_items':[],
    'request_id':saved['request_id'] if saved and saved['status']=='preview' else str(uuid.uuid4()),'at':now()}
   self.c.put('sync_plan',key,plan);return self.public(plan)
 def public(self,plan):
  return {k:deepcopy(v) for k,v in plan.items() if k not in {'nodes','heads','local_fingerprint','local_guards'}}
 def apply(self,actor,request):
  actor=named(actor);identity=str(uuid.UUID(request['id']));key=actor+':'+identity
  if request.get('explicit_confirmation') is not True:raise ValueError('Confirm the displayed synchronization preview.')
  with self.c.lock:
   plan=self.c.get('sync_plan',key)
   if not plan:raise ValueError('Preview the snapshot before applying it.')
   if plan['status']=='applied':return self.public(plan)
   if plan['status']=='needs_recomparison':raise ValueError('Refresh the comparison before continuing this import.')
   if plan['conflicts'] or plan['validation_errors']:raise ValueError('Resolve every conflict before synchronization.')
   package=self.load((self.c.root/'packages'/(identity+'.zip')).read_bytes());m=package['metadata']
   if plan['status']=='preview':
    observed=self.capture(actor)
    if fingerprint([observed['heads'],observed['guards']])!=plan['local_fingerprint']:
     raise ValueError('Saved work changed after this preview. Refresh the comparison before applying.')
    plan['status']='applying';self.c.put('sync_plan',key,plan)
   # Retain validated immutable originals and evidence before any domain writes.
   root=self.c.root/'snapshot-files';root.mkdir(exist_ok=True)
   for path,raw in package['files'].items():
    digest=fingerprint_bytes(raw);target=root/digest
    if target.exists() and target.read_bytes()!=raw:raise ValueError('Retained original differs.')
    if not target.exists():target.write_bytes(raw)
    self.c.put('sync_file',digest,{'id':digest,'path':path})
   self.c.put_many([('sync_node',i,n) for i,n in plan['nodes'].items()])
   self.c.put_many([('sync_evidence',i,{'id':i,'value':v}) for i,v in m['evidence'].items()])
   # Source records precede material records. Each write uses a deterministic
   # request id; a crash after an owning-store commit can be replayed safely.
   items=sorted(plan['items'],key=lambda i:({'source':0,'review':1,'material':2}.get(i['key'].split(':')[0],3),i['key']))
   for item in items:
    record_key=item['key']
    if record_key in plan['applied_items']:continue
    value=plan['nodes'][item['head']]['value']
    try:
     receipt={'status':'unchanged'} if item['status'] in ('unchanged','kept_local') else self.w.apply(actor,record_key,value,{'request_id':str(uuid.uuid5(uuid.UUID(plan['request_id']),record_key)),
         'local_guards':plan['local_guards'],'package':m,'nodes':plan['nodes'],'head':item['head'],'original_root':str(root),'status':item['status']})
    except ValueError as exc:
     plan['status']='needs_recomparison';plan['error']=str(exc)
     self.c.put('sync_attempt',plan['request_id'],self.public(plan));self.c.put('sync_plan',key,plan)
     raise ValueError(str(exc)+' Refresh the comparison to continue from the saved records.') from exc
    self.c.put('sync_head',record_key,{'key':record_key,'heads':[item['head']]})
    self.w.mark_observed(record_key,item['head'],actor)
    item['receipt']=receipt;plan['applied_items'].append(record_key);self.c.put('sync_plan',key,plan)
   event={'id':plan['request_id'],'actor':actor,'sender':m['actor'],'at':now(),'package_id':identity,
    'status':'applied','items':[{'key':i['key'],'title':i.get('title',i['key']),'status':i['status'],'contributors':i['contributors']} for i in items]}
   self.c.put_many([('sync_event',e['id'],e) for e in m['history']]+[('sync_event',event['id'],event)])
   plan['status']='applied';self.c.put('sync_plan',key,plan)
   self.c.app.snapshot_time=0
   return self.public(plan)

def fingerprint_bytes(raw):
 from hashlib import sha256
 return sha256(raw).hexdigest()
