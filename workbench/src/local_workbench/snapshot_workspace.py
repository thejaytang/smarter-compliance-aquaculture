"""Domain projection for peer snapshots. Originals and human revisions are retained.

Imported saved work is synchronized into the receiving reviewer's workspace.
Source mirror records preserve remote source evidence; source confirmation still
uses the owning governance rules. Imports do not execute retrieval or parsing.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from local_workbench.sqlite_support import connect as connect_sqlite
import uuid
from .collaboration import source_review, validate_source_review, fingerprint, encoded, now, named
from .collaboration_exchange import segment
from .snapshot_graph import ancestors

REVIEW_KEYS=('checked_scope','review_checks','association_review_required','association_review','review_declarations','confirmation','content_status')

def material_value(m):
 return {'binding':{k:deepcopy(m[k]) for k in ('id','source','scope','title')},
  'blocks':deepcopy(m['blocks']),'issues':deepcopy(m['issues']),
  'review':{k:deepcopy(m[k]) for k in REVIEW_KEYS if k in m}}

def material_ids(adapter):
 path=adapter.runtime/'workflow.sqlite'
 if not path.exists():return []
 with connect_sqlite(path.as_uri()+'?mode=ro',uri=True) as db:
  if not db.execute("SELECT 1 FROM sqlite_master WHERE name='material_documents'").fetchone():return []
  return [r[0] for r in db.execute('SELECT id FROM material_documents ORDER BY id')]

class SnapshotWorkspace:
 def __init__(self,c):self.c=c
 def capture(self,actor):
  c=self.c;source_data=c.app.adapter.call('read');sources={s['source_id']:s for s in c.source_records(source_data)}
  config=json.loads(c.app.adapter.config.read_text()) if c.mode=='coordinator' else None
  source_root=(c.app.adapter.config.parent/config['source_root']).resolve() if config else None
  for sid,source in sources.items():
   files={}
   if source.get('snapshot_status')=='STORED' and source.get('stored_filename'):
    if source_root is not None:
     path=(source_root/segment(source['folder_code'])/segment(source['stored_filename'])).resolve()
     if not path.is_relative_to(source_root):raise ValueError('Original leaves managed source storage.')
    else:path=Path(c.source_original(actor,sid)['path'])
    raw=path.read_bytes()
    if sha256(raw).hexdigest()!=source['content_hash']:raise ValueError('Registered original changed; export was stopped.')
    files['originals/'+sha256(raw).hexdigest()]=raw
   evidence={'tasks':[t for t in source_data.get('tasks',[]) if t.get('source_id')==sid],
    'history':[t for t in source_data.get('history',[]) if t.get('source_id')==sid],
    'issues':c.source_issues(sid,source_data)}
   yield {'key':'source:'+sid,'value':source,'files':files,'evidence':evidence,'guard':{'revision':source.get('source_revision')}}
   base=source_review(source)
   drafts=[p for p in c.all('source_draft') if p['source_id']==sid]
   if not drafts:yield {'key':'review:'+sid,'value':base,'base':base,'branch':actor,'actor':actor}
   for d in drafts:
    yield {'key':'review:'+sid,'value':d['source_review'],'base':source_review(d['base_source']),
     'branch':d['actor'],'actor':d['actor'],'evidence':{'source_draft':d}}
  seen=set()
  for identity in material_ids(c.app.system2):
   exported=c.app.system2.call('material_export',request={'material_id':identity});m=exported['material']
   raw=Path(exported['original']['path']).read_bytes();files={'originals/'+sha256(raw).hexdigest():raw}
   # A locally saved personal branch retains its own base. The original master
   # remains an ancestor, not an additional competing latest record.
   branches=[w for w in c.all('workspace') if w['material_id']==identity]
   yield {'key':'material:'+identity,'value':material_value(m),'files':files,'evidence':self.export_evidence(exported),'branch':'master','guard':{'revision':m['revision']}}
   for branch in branches:
    adapter=c.adapter(c.workspace_runtime(branch));e=adapter.call('material_export',request={'material_id':identity})
    base=material_value(branch['base_material']);value=material_value(e['material']);seen.add(identity)
    yield {'key':'material:'+identity,'base':base,'value':value,'branch':branch['actor'],'actor':branch['actor'],
     'files':files,'evidence':self.export_evidence(e),'guard':{'revision':e['material']['revision']}}
  from .requirement_delivery import Delivery
  yield from Delivery(c).capture()
  # Task/inspection histories travel as immutable evidence. Personal proposals
  # remain separate records and are never executed during synchronization.
  for kind in ('source_task_draft','material_inspection','adoption_receipt','collection_adoption','received_adoption'):
   for record in c.all(kind):
    identity=record.get('id') or record.get('request_id') or fingerprint(record)
    yield {'key':'history:'+kind+':'+identity,'value':record,'actor':record.get('actor',actor)}
 def export_evidence(self,e):return {k:deepcopy(v) for k,v in e.items() if k!='original'}
 def validate_value(self,key,value):
  if key.startswith('source:'):
   if value.get('source_id')!=key[7:]:raise ValueError('Source identity differs.')
   if value.get('snapshot_status')=='STORED':
    segment(value['folder_code']);segment(value['stored_filename'])
    if len(value.get('content_hash',''))!=64:raise ValueError('A stored original needs its fingerprint.')
  elif key.startswith('review:'):validate_source_review(value)
  elif key.startswith('material:'):
   binding=value['binding']
   if binding['id']!=key[9:]:raise ValueError('Material identity differs.')
   # Owning System2 validation is deliberately used through its own interpreter.
   self.c.app.system2.call('material_sync-validate',request={'value':value})
  elif key.startswith('requirements:'):
   from .requirement_delivery import Delivery,key_for
   Delivery(self.c).validate(value)
   if key!=key_for(value['actor']):raise ValueError('Requirement reviewer identity differs.')
  elif not key.startswith('history:'):raise ValueError('Unsupported record in snapshot.')
 def validate(self,m,files):
  for n in m['nodes'].values():self.validate_value(n['key'],n['value'])
  for identity,e in m['evidence'].items():
   n=m['nodes'][identity]
   if n['key'].startswith('material:'):
    self.c.app.system2.call('material_validate',request=e)
    if material_value(e['material'])!=n['value']:raise ValueError('Material evidence differs from its saved version.')
    digest=e['material']['source']['content_hash']
    if 'originals/'+digest not in files:raise ValueError('Snapshot is missing a material original.')
   elif n['key'].startswith('source:'):
    if not isinstance(e,dict) or any(not isinstance(e.get(k,[]),list) for k in ('tasks','history','issues')):
     raise ValueError('Invalid source history evidence.')
  for key,heads in m['heads'].items():
   for head in heads:
    value=m['nodes'][head]['value']
    if key.startswith('source:') and value.get('snapshot_status')=='STORED' and 'originals/'+value['content_hash'] not in files:
     raise ValueError('Full snapshot is missing a registered original.')
    if key.startswith('material:'):
     lineage=ancestors(m['nodes'],head)
     if not any(i in m['evidence'] for i in lineage):raise ValueError('Material has no retained source-bound history.')
 def evidence_for(self,key,context):
  items={e['id']:e['value'] for e in self.c.all('sync_evidence')}
  items.update(context['package']['evidence']);lineage=ancestors(context['nodes'],context['head'])
  found=[(depth,identity,items[identity]) for identity,depth in lineage.items() if identity in items]
  if not found:return None
  return min(found,key=lambda x:(x[0],x[1]))[2]
 def apply(self,actor,key,value,context):
  c=self.c;rid=context['request_id'];old=c.get('sync_domain_receipt',rid)
  if old:return old
  self.validate_value(key,value);e=self.evidence_for(key,context)
  if key.startswith('source:'):
   sid=key[7:];source=deepcopy(value);root=Path(context['original_root'])
   original=source.get('content_hash');target=c.root/'snapshot-sources'/fingerprint(source)
   if source.get('snapshot_status')=='STORED':
    folder=target/segment(source['folder_code']);folder.mkdir(parents=True,exist_ok=True)
    path=folder/segment(source['stored_filename']);raw=(root/original).read_bytes()
    if sha256(raw).hexdigest()!=original:raise ValueError('Retained source original differs.')
    if path.exists() and path.read_bytes()!=raw:raise ValueError('Source mirror cannot overwrite a different original.')
    if not path.exists():path.write_bytes(raw)
   descriptor={'records':[dict(source,selection_status=source.get('effective_selection','PENDING'))],
    'source_root':str(target),'evidence':{'source_open_issues':(e or {}).get('issues',[])}}
   record={'source':source,'offline_source':descriptor,'sync':True,'evidence':e or {}}
   c.put('sync_source',sid,record)
   if c.mode=='reviewer':
    c.put('source_catalog',sid,record);c._write_reviewer_catalog()
    receipt={'status':'synchronized','source_id':sid}
   else:
    pending=c.get('sync_source_pending',rid)
    if not pending:
     current=next((s for s in c.app.adapter.call('read')['sources'] if s['source_id']==sid),None)
     pending={'request_id':rid,'actor':actor,'source':source,'evidence':e or {},
      'expected_source_revision':context.get('local_guards',{}).get(key+':shared',{}).get('revision') if current else None,
      'original_root':str(root),'original_path':str(root/original) if original else '',
      'package_id':context['package']['id']}
     c.put('sync_source_pending',rid,pending)
    receipt=c.app.adapter.call('source_snapshot_apply',request=pending)
  elif key.startswith('review:'):
   sid=key[7:];draft=c.source_draft(actor,sid)
   revision=draft['draft_revision']+1
   record={'actor':actor,'source_id':sid,'base_source':draft['base_source'],'source_review':deepcopy(value),
    'revision':revision,'history':[*draft['history'],{'actor':actor,'at':now(),'revision':revision,'source_review':deepcopy(value),'sync_request_id':rid}]}
   receipt={'status':'saved','source_id':sid,'revision':revision}
   c.put_many([('source_draft',actor+':'+sid,record),('sync_domain_receipt',rid,receipt)])
  elif key.startswith('requirements:'):
   from .requirement_delivery import Delivery
   receipt=Delivery(c).apply(value,rid,context.get('local_guards',{}).get(key+':'+value['actor']))
  elif key.startswith('material:'):
   identity=key[9:]
   if not e:raise ValueError('Cannot synchronize material without retained history.')
   original=Path(context['original_root'])/value['binding']['source']['content_hash']
   if not original.exists():
    original=Path(c.source_original(actor,value['binding']['source']['source_id'])['path'])
   if identity not in material_ids(c.app.system2):
    c.app.system2.call('material_seed',request={**e,'original_path':str(original)})
   # All reviewers can consume a full package. The seed retains original audit
   # history; combining changed content creates a fresh unconfirmed revision.
   if c.mode=='reviewer' and not c.get('material_catalog',identity):
    source=c.source(value['binding']['source']['source_id']);catalog=c.get('source_catalog',source['source_id'])
    wid=str(uuid.uuid5(uuid.UUID(context['package']['id']),identity))
    work={**e,'id':wid,'source_id':source['source_id'],'source':source,'material_id':identity,
     'base_digest':fingerprint({'source':source,'material':e['material']})}
    c.put('work',wid,work);c.put('baseline',work['base_digest'],work);c.put('material_catalog',identity,{'work_id':wid,'offline_source':catalog['offline_source']})
   adapter=c.personal_adapter(actor,identity)
   current=adapter.call('material_read',material_id=identity)
   pending=c.get('sync_domain_pending',rid)
   if not pending:
    pending={'request_id':rid,'actor':actor,'material_id':identity,
     'expected_revision':context.get('local_guards',{}).get(key+':'+actor,{}).get('revision',current['revision']),'value':value,'origin':e,'original_path':str(original),
     'contributors':context['nodes'][context['head']]['actor'],'sync_head':context['head']}
    c.put('sync_domain_pending',rid,pending)
   result=adapter.call('material_sync',request=pending)
   if result.get('status')=='conflict':raise ValueError('Material changed while synchronizing; saved work is retained.')
   shared_pending=c.get('sync_shared_pending',rid)
   if not shared_pending:
    shared=c.app.system2.call('material_read',material_id=identity)
    shared_pending={**pending,'request_id':str(uuid.uuid5(uuid.UUID(rid),'shared')),'expected_revision':context.get('local_guards',{}).get(key+':master',{}).get('revision',shared['revision'])}
    c.put('sync_shared_pending',rid,shared_pending)
   shared_result=c.app.system2.call('material_sync',request=shared_pending)
   if shared_result.get('status')=='conflict':raise ValueError('Shared material changed during synchronization. Saved personal work and the resumable import are retained.')
   c.put('sync_observed',key+':master',{'head':context['head']})
   receipt={'status':'synchronized','material_id':identity,'revision':result['material']['revision']}
  else:
   c.put('sync_shared_record',key,{'key':key,'value':value,'sender':context['package']['actor']})
   receipt={'status':'retained'}
  c.put('sync_domain_receipt',rid,receipt);return receipt
 def mark_observed(self,key,head,actor):
  if key.startswith('requirements:'):
   from .identities import REVIEWERS
   from .requirement_delivery import key_for
   actor=next(a for a in REVIEWERS if key_for(a)==key)
  branch='shared' if key.startswith('source:') else actor
  self.c.put('sync_observed',key+':'+branch,{'head':head})
