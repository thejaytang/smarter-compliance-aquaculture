"""Real isolated material stores behind peer full-snapshot transport."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json,uuid
import pytest
from local_workbench.collaboration import Collaboration,PackageSourceAdapter
from local_workbench.full_snapshot import FullSnapshot
from pdf_extraction.orchestration.material_service import MaterialService
from pdf_extraction.orchestration.material_collaboration import command as material_command
from pdf_extraction.orchestration.material_sync import command as sync_command
from .test_material_service import register,request

A='Weijie Tang';B='Ana Jokic'
class LocalAdapter:
 def __init__(self,runtime,system1,record,originals):
  self.runtime=Path(runtime);self.root=Path(__file__).resolve().parents[1];self.system1=system1;self.config=None
  self.service=MaterialService(self.runtime,system1)
  self.service.handoff=lambda:SimpleNamespace(records=[record],registry_sha256='a'*64,source_root=originals,assert_current=lambda:None)
 def call(self,command,**kw):
  op=command.removeprefix('material_');req=kw.get('request',{})
  if op in ('sync','sync-validate'):return sync_command(self.service,op,req)
  if op in ('seed','export','validate'):return material_command(self.service,op,req)
  if op=='read':return self.service.read(kw['material_id'],kw.get('revision'))
  if op=='open':return self.service.open(req)
  if op=='list':return self.service.listing(**kw.get('options',{}))
  return self.service.mutate(op,req)

def peer(root,row,originals,reviewer=False):
 root.mkdir();system1=root/'system1';system1.mkdir();config=system1/'config.json';config.write_text(json.dumps({'source_root':str(originals)}))
 main=LocalAdapter(root/'workflow',system1,row,originals)
 app=SimpleNamespace(runtime=root,system2=main,adapter=SimpleNamespace(config=config,call=lambda *a,**k:{'sources':[row],'tasks':[],'history':[]}),snapshot_time=0)
 c=Collaboration(app,reviewer=reviewer);c.adapter=lambda runtime:LocalAdapter(runtime,system1,row,originals)
 if reviewer:app.adapter=PackageSourceAdapter(c,system1)
 return c,FullSnapshot(c)

def test_full_real_material_roundtrip(tmp_path):
 originals=tmp_path/'originals';row=register(originals);row.update(effective_selection='INCLUDE',source_revision='r1')
 c,a=peer(tmp_path/'a',row,originals);d,b=peer(tmp_path/'b',row,originals,True)
 m=c.app.system2.call('material_open',request=request(source_id='TS001'))
 own=c.read_material(A,m['id'])
 blocks=[{'id':'a','type':'text','text':'First edit','source_refs':[{'scope_id':'html:document'}]}, {'id':'b','type':'text','text':'Second','source_refs':[{'scope_id':'html:document'}]}]
 c.material_action(A,'save',request(own,actor=A,blocks=blocks))
 exported=a.export(A,{'request_id':str(uuid.uuid4())});raw=a.download(A,exported['id'])[0]
 assert exported['originals']==1
 p=b.receive(B,raw);assert not p['conflicts'],p['conflicts'];b.apply(B,{'id':p['id'],'explicit_confirmation':True})
 saved=d.read_material(B,m['id']);assert saved['blocks']==blocks;assert saved['confirmation'] is None
 saved=d.material_action(B,'save',request(saved,actor=B,blocks=[dict(blocks[0],text='Peer edit'),blocks[1]]))['material']
 returned=b.export(B,{'request_id':str(uuid.uuid4())});p=a.receive(A,b.download(B,returned['id'])[0]);assert not p['conflicts'],p['conflicts']
 a.apply(A,{'id':p['id'],'explicit_confirmation':True})
 assert c.read_material(A,m['id'])['blocks'][0]['text']=='Peer edit'
 assert len(a.history())==2


def test_any_named_reviewer_archives_and_confirmation_roundtrips(tmp_path):
 originals=tmp_path/'originals';row=register(originals);row.update(effective_selection='INCLUDE',source_revision='r1')
 c,a=peer(tmp_path/'a',row,originals);d,b=peer(tmp_path/'b',row,originals,True)
 c.app.peer_sync=True
 m=c.app.system2.call('material_open',request=request(source_id='TS001'))
 own=c.read_material(B,m['id'])
 block={'id':'a','type':'text','text':'Reviewed text','source_refs':[{'scope_id':'html:document'}]}
 own=c.material_action(B,'save',request(own,actor=B,blocks=[block]))['material']
 req=request(own,actor=B,explicit_confirmation=True,checked_scope=['html:document'],association_reviewed=True,omissions_checked=True,dependencies_checked=True)
 result=c.material_action(B,'confirm',req)
 master=c.app.system2.call('material_read',material_id=m['id'])
 assert master['content_status']=='content_review_complete'
 assert master['confirmation']['actor']==B
 assert c.material_action(B,'confirm',req)==result
 with pytest.raises(ValueError):c.material_action(A,'confirm',dict(req,actor=A))
 exported=a.export(B,{'request_id':str(uuid.uuid4())});raw=a.download(B,exported['id'])[0]
 p=b.receive(A,raw);assert not p['conflicts'];b.apply(A,{'id':p['id'],'explicit_confirmation':True})
 imported=d.app.system2.call('material_read',material_id=m['id'])
 assert imported['confirmation']['actor']==B
 assert imported['confirmation']['at']==master['confirmation']['at']
 # A resulting package must still pass provenance validation after revision remapping.
 exported=b.export(A,{'request_id':str(uuid.uuid4())});a.load(b.download(A,exported['id'])[0])


def test_received_confirmation_does_not_bypass_local_candidate(tmp_path):
 originals=tmp_path/'originals';row=register(originals)
 c,_=peer(tmp_path/'a',row,originals)
 adapter=c.app.system2;m=adapter.call('material_open',request=request(source_id='TS001'))
 confirmed=adapter.call('material_confirm',request=request(m,actor=A,explicit_confirmation=True,checked_scope=['html:document'],association_reviewed=True,omissions_checked=True,dependencies_checked=True))['material']
 origin=adapter.call('material_export',request={'material_id':m['id']});origin.pop('original')
 active=adapter.call('material_extract',request=request(confirmed,actor=A))['material']
 from local_workbench.snapshot_workspace import material_value
 result=adapter.call('material_sync',request=request(active,actor=B,value=material_value(origin['material']),origin=origin,sync_head='test'))
 assert result['material']['confirmation'] is None
 assert result['material']['content_status']!='content_review_complete'


def test_real_parallel_edits_merge_without_losing_either_reviewer(tmp_path):
 originals=tmp_path/'originals';row=register(originals);row.update(effective_selection='INCLUDE',source_revision='r1')
 c,a=peer(tmp_path/'a',row,originals);d,b=peer(tmp_path/'b',row,originals,True)
 m=c.app.system2.call('material_open',request=request(source_id='TS001'));own=c.read_material(A,m['id'])
 blocks=[{'id':i,'type':'text','text':i,'source_refs':[{'scope_id':'html:document'}]} for i in ('a','b')]
 c.material_action(A,'save',request(own,actor=A,blocks=blocks))
 exported=a.export(A,{'request_id':str(uuid.uuid4())});p=b.receive(B,a.download(A,exported['id'])[0]);b.apply(B,{'id':p['id'],'explicit_confirmation':True})
 own=c.read_material(A,m['id']);c.material_action(A,'save',request(own,actor=A,blocks=[dict(blocks[0],text='A changed'),blocks[1]]))
 own=d.read_material(B,m['id']);d.material_action(B,'save',request(own,actor=B,blocks=[blocks[0],dict(blocks[1],text='B changed')]))
 exported=b.export(B,{'request_id':str(uuid.uuid4())});p=a.receive(A,b.download(B,exported['id'])[0]);assert not p['conflicts'],p['conflicts']
 a.apply(A,{'id':p['id'],'explicit_confirmation':True});merged=c.read_material(A,m['id'])
 assert [x['text'] for x in merged['blocks']]==['A changed','B changed'];assert merged['confirmation'] is None
 assert set(next(i for i in p['items'] if i['key'].startswith('material:'))['contributors'])=={A,B}
 # Combined revisions remain self-contained and validate on the other peer.
 exported=a.export(A,{'request_id':str(uuid.uuid4())});b.load(a.download(A,exported['id'])[0])
